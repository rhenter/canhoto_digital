from __future__ import annotations

import os
import tempfile

from django.core.files.base import ContentFile

try:
    import brazilfiscalreport as _bfr  # type: ignore
    from brazilfiscalreport.danfe import Danfe  # type: ignore

    BRAZILFISCALREPORT_AVAILABLE = True
    BRAZILFISCALREPORT_VERSION = getattr(_bfr, "__version__", "?")
except Exception:  # pragma: no cover - optional dependency guard
    Danfe = None  # type: ignore
    BRAZILFISCALREPORT_AVAILABLE = False
    BRAZILFISCALREPORT_VERSION = "?"


def _write_temp_file(prefix: str, suffix: str, data: bytes) -> str:
    f = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False)
    try:
        f.write(data)
        f.flush()
        return f.name
    finally:
        f.close()


def generate_danfe_from_xml_bytes(xml_bytes: bytes) -> bytes:
    """Generate a DANFE PDF (bytes) using BrazilFiscalReport from NF-e XML bytes.

    Implementation details:
    - Tries both text and file-path constructor styles (different package versions vary).
    - Attempts a broad set of PDF export methods and fallbacks, including accessing an
      internal fpdf-like object to call `output(dest='S')` when available.
    - Returns raw PDF bytes on success; raises RuntimeError with actionable guidance on failure.
    """
    if not BRAZILFISCALREPORT_AVAILABLE:
        raise RuntimeError(
            "BrazilFiscalReport is not installed. Please add 'brazilfiscalreport' to requirements and install it.")

    if not xml_bytes:
        raise RuntimeError("Empty XML content provided for DANFE generation.")

    # Decode XML bytes to string; tolerate BOM if present
    try:
        xml_text = xml_bytes.decode("utf-8-sig")
    except Exception:
        xml_text = xml_bytes.decode("utf-8")

    # Prepare a temp XML file for constructor variants that expect a file path
    xml_fd, xml_path = tempfile.mkstemp(prefix="nfe_", suffix=".xml")
    try:
        os.write(xml_fd, xml_bytes)
    finally:
        os.close(xml_fd)

    # Try constructing Danfe with xml TEXT first, then fallback to PATH
    construct_errors = []
    try:
        danfe = Danfe(xml_text)
    except Exception as e1:
        construct_errors.append(f"text:{e1}")
        try:
            danfe = Danfe(xml_path)
        except Exception as e2:
            construct_errors.append(f"path:{e2}")
            raise RuntimeError(
                f"Failed to initialize BrazilFiscalReport.Danfe (tried text and path). Details: {construct_errors}")

    pdf_path = f"/tmp/danfe_{danfe.key_nfe}.pdf"
    danfe.output(pdf_path)

    with open(pdf_path, "rb+") as f:
        result = f.read()

    return result


def generate_and_save_danfe(invoice, overwrite: bool = True) -> bool:
    """Generate DANFE for the given Invoice and save to its `pdf_file`.

    Returns True on success, False when skipped (e.g., missing XML or overwrite=False with existing PDF).
    Raises RuntimeError on rendering failures or missing dependency.
    """
    # Ensure XML exists
    xml_field = getattr(invoice, "xml_file", None)
    if not xml_field or not getattr(xml_field, "name", ""):
        raise RuntimeError("Invoice has no XML file saved; cannot generate DANFE.")

    # Skip if PDF already exists and not overwriting
    if not overwrite and getattr(invoice, "pdf_file", None) and getattr(invoice.pdf_file, "name", ""):
        return False

    # Read XML bytes safely (storage may not expose .path)
    try:
        if hasattr(xml_field, "open"):
            xml_field.open("rb")
        xml_bytes = xml_field.read()
    finally:
        try:
            if hasattr(xml_field, "close"):
                xml_field.close()
        except Exception:
            pass

    pdf_bytes = generate_danfe_from_xml_bytes(xml_bytes)

    # Build a target filename
    key = getattr(invoice, "key", None) or str(invoice.pk)
    filename = f"{key}.pdf"
    # Save into FileField (idempotent overwrite)
    invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    return True

from __future__ import annotations

from io import BytesIO
from typing import Optional

try:
    # Lightweight generation; optional dependency.
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


def render_basic_pdf(context, xml_bytes: bytes) -> Optional[bytes]:
    """
    Render a minimal DANFE-like PDF from parsed invoice context and/or original XML.

    Notes:
    - This is a very basic layout intended as a placeholder until a full DANFE renderer is adopted.
    - Requires reportlab; when unavailable, returns None gracefully.
    - Only intended to run for full documents (procNFe). For summaries (resNFe) it should be skipped by caller.
    """
    if not REPORTLAB_AVAILABLE:
        return None

    # Extract minimal fields from provided context (dataclass or model-like object)
    # Expect attributes: key, number, series, issue_date, issuer_name, recipient_name, total_value
    key = getattr(context, "key", "") or ""
    number = getattr(context, "number", "") or ""
    series = getattr(context, "series", "") or ""
    issue_date = getattr(context, "issue_date", None)
    issuer_name = getattr(context, "issuer_name", "") or ""
    recipient_name = getattr(context, "recipient_name", "") or ""
    total_value = getattr(context, "total_value", 0)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "DANFE (Resumo)")

    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(40, y, f"Chave de Acesso: {key}")

    y -= 15
    c.drawString(40, y, f"Número: {number}  Série: {series}")

    y -= 15
    c.drawString(40, y, f"Emissor: {issuer_name}")

    y -= 15
    c.drawString(40, y, f"Destinatário: {recipient_name}")

    y -= 15
    c.drawString(40, y, f"Emissão: {issue_date}")

    y -= 15
    c.drawString(40, y, f"Valor Total: R$ {total_value}")

    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Observações:")
    c.setFont("Helvetica", 8)
    y -= 12
    c.drawString(40, y, "Documento gerado automaticamente a partir do XML da NF-e.")

    # Optionally include a snippet of the XML tail for traceability
    try:
        snippet = (xml_bytes or b"")[:400].decode("utf-8", errors="ignore").replace("\n", " ")
        y -= 20
        c.setFont("Helvetica", 6)
        c.drawString(40, y, f"XML snippet: {snippet}")
    except Exception:
        pass

    c.showPage()
    c.save()
    data = buf.getvalue()
    buf.close()
    return data

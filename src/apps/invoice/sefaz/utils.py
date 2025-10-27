import base64
import gzip
import io
import tempfile
from typing import Tuple
from xml.etree import ElementTree as ET

from .exceptions import SefazIntegrationError

try:
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
except Exception:  # pragma: no cover - informative fallback
    load_key_and_certificates = None  # type: ignore
    Encoding = PrivateFormat = NoEncryption = None  # type: ignore


def get_endpoint() -> str:
    """Return the national DF-e distribution endpoint (production and homologation use the same URL)."""
    return "https://www.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"


def decompress_doczip_to_xml(doczip_b64: str) -> ET.Element:
    """Decode base64+gzip `docZip` content and return the root XML element."""
    raw = base64.b64decode(doczip_b64)
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
        xml_bytes = gz.read()
    return ET.fromstring(xml_bytes)


def pkcs12_to_pem_tempfiles(pfx_path: str, password: str) -> Tuple[str, str]:
    """Convert a PKCS#12 (.pfx/.p12) file to temporary PEM files and return their paths.

    Returns (cert_path, key_path).
    Raises `SefazIntegrationError` if `cryptography` is not available or the PKCS#12 is invalid.
    """
    if load_key_and_certificates is None:
        raise SefazIntegrationError(
            "cryptography library is required to load PKCS#12 certificates. Please add 'cryptography' to your requirements and install it.")
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()
    key, cert, _extra = load_key_and_certificates(pfx_data, password.encode() if password else None)
    if key is None or cert is None:
        raise SefazIntegrationError("Invalid PKCS#12: could not load key and certificate")
    key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    cert_pem = cert.public_bytes(Encoding.PEM)
    key_file = tempfile.NamedTemporaryFile(delete=False, suffix=".key")
    cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
    key_file.write(key_pem)
    key_file.flush()
    cert_file.write(cert_pem)
    cert_file.flush()
    return cert_file.name, key_file.name


def soap_envelope(dist_dfe_int_xml: str) -> str:
    """Wrap a `distDFeInt` XML body inside a SOAP 1.2 envelope expected by SEFAZ."""
    return f"""
    <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
      <soap12:Body>
        <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
          <nfeDadosMsg>
            {dist_dfe_int_xml}
          </nfeDadosMsg>
        </nfeDistDFeInteresse>
      </soap12:Body>
    </soap12:Envelope>
    """.strip()


def build_distdfeint_xml(tp_amb: int, cufa: int, cnpj: str, ult_nsu: str) -> str:
    return (
        f'<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">'
        f"<tpAmb>{tp_amb}</tpAmb>"
        f"<cUFAutor>{cufa:02d}</cUFAutor>"
        f"<CNPJ>{cnpj}</CNPJ>"
        f"<distNSU><ultNSU>{ult_nsu}</ultNSU></distNSU>"
        f"</distDFeInt>"
    )

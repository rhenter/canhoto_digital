from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Optional, Tuple
from xml.etree import ElementTree as ET

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework import status

from apps.company.models import Company
from . import utils
from .constants import UF_TO_CODE
from .exceptions import SefazIntegrationError



@dataclass
class SefazInvoiceData:
    """Lightweight representation of an invoice returned by SEFAZ DF-e distribution."""
    number: str
    series: str
    issue_date: date
    total_value: float


class SefazClient:
    """Client that fetches DF-e distribution batches from SEFAZ and yields parsed invoices.

    Responsibilities (quick version):
    - Build and send SOAP requests to the national DF-e endpoint using the company's A1 certificate.
    - Parse SOAP responses and NF-e documents (summary or full) into `SefazInvoiceData`.
    - Iterate via NSU and update the company's `last_nsu` as new batches are processed.
    """

    def __init__(self, company: Company) -> None:
        self.company = company
        self.cnpj = company.cnpj

        self.http_timeout_seconds = settings.SEFAZ_HTTP_TIMEOUT_SECONDS

    def _fetch_batch(self, ult_nsu: int) -> Tuple[int, int, list[ET.Element]]:
        """Fetch a DF-e distribution batch starting from the provided `ult_nsu`.

        Returns a tuple `(ult_nsu, max_nsu, docs)` where `docs` is a list of `docZip` elements.
        Raises `SefazIntegrationError` on configuration/HTTP/parse errors.
        """
        if requests is None:
            raise SefazIntegrationError(
                "requests library is required. Please add 'requests' to your requirements and install it.")
        if not self.company.certificate or not self.company.certificate_password:
            raise SefazIntegrationError(
                "Company certificate (.pfx/.p12) and password are required for SEFAZ integration.")
        uf_sigla = self.company.uf or "SP"
        cufa = UF_TO_CODE.get(uf_sigla.upper(), 35)
        tp_amb = 1 if self.company.sefaz_environment == "production" else 2
        endpoint = utils.get_endpoint()

        dist_xml = utils.build_distdfeint_xml(tp_amb, cufa, self.cnpj, f"{ult_nsu:015d}")
        envelope = utils.soap_envelope(dist_xml)
        headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

        cert_path, key_path = utils.pkcs12_to_pem_tempfiles(self.company.certificate.path,
                                                            self.company.certificate_password or "")
        try:
            resp = requests.post(
                endpoint,
                data=envelope.encode("utf-8"),
                headers=headers,
                timeout=self.http_timeout_seconds,
                cert=(cert_path, key_path),
            )
        finally:
            # Do not delete temp files immediately; requests may still read them; OS will clean later.
            pass
        if resp.status_code != status.HTTP_200_OK:
            raise SefazIntegrationError(f"SEFAZ HTTP error: {resp.status_code} - {resp.text[:200]}")
        # Parse SOAP -> nfeResultMsg -> retDistDFeInt
        try:
            root = ET.fromstring(resp.content)
            ns = {
                "s": "http://www.w3.org/2003/05/soap-envelope",
                "ws": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe",
                "nfe": "http://www.portalfiscal.inf.br/nfe",
            }
            body = root.find("s:Body", ns)
            result = body.find("ws:nfeDistDFeInteresseResponse/ws:nfeDistDFeInteresseResult", ns)
            ret_xml = result.find("ws:retDistDFeInt", ns)
            if ret_xml is None:
                # Some implementations return XML string inside nfeResultMsg
                ret_text_el = result.find("ws:nfeResultMsg", ns)
                if ret_text_el is not None and len(ret_text_el):
                    ret_xml = ret_text_el[0]
            if ret_xml is None:
                # Try without ws namespace
                ret_xml = result.find("*//retDistDFeInt") if result is not None else None
            if ret_xml is None:
                raise ValueError("retDistDFeInt not found in SOAP response")
        except Exception as e:
            raise SefazIntegrationError(f"Failed to parse SEFAZ response: {e}")

        # Extract fields
        def _get(el: ET.Element, name: str) -> Optional[str]:
            child = el.find(name)
            return child.text if child is not None else None

        c_stat = _get(ret_xml, "cStat") or ""
        x_motivo = _get(ret_xml, "xMotivo") or ""
        ult_nsu_parsed = int((_get(ret_xml, "ultNSU") or "0").lstrip("0") or "0")
        max_nsu_parsed = int((_get(ret_xml, "maxNSU") or "0").lstrip("0") or "0")
        if c_stat not in {"137", "138", "139", "140", "141"}:
            # 137: no doc, 138: doc available, 139..: partial, 140/141 varying
            raise SefazIntegrationError(f"SEFAZ returned error cStat={c_stat} ({x_motivo})")
        docs = []
        lote = ret_xml.find("loteDistDFeInt")
        if lote is not None:
            for doc in lote.findall("docZip"):
                docs.append(doc)
        return ult_nsu_parsed, max_nsu_parsed, docs

    def _parse_doc(self, doc_el: ET.Element) -> Optional[SefazInvoiceData]:
        """Parse a SEFAZ `docZip` element into `SefazInvoiceData` if possible.

        Supports summary `resNFe` and full `procNFe` documents.
        Returns `None` when required fields are missing.
        """
        content_b64 = doc_el.text or ""
        xml_el = utils.decompress_doczip_to_xml(content_b64)
        tag = xml_el.tag.split("}")[-1]
        # resNFe (summary) or procNFe/NFe (full)
        if tag == "resNFe":
            nNF = (xml_el.findtext("nNF") or "").strip()
            serie = (xml_el.findtext("serie") or "").strip()
            dhEmi = (xml_el.findtext("dhEmi") or "").strip()
            vNF = (xml_el.findtext("vNF") or "0").strip()
            try:
                # dhEmi in UTC ISO format
                issue_dt = datetime.fromisoformat(dhEmi.replace("Z", "+00:00")).date()
            except Exception:
                issue_dt = date.today()
            try:
                total = float(vNF)
            except Exception:
                total = 0.0
            if nNF:
                return SefazInvoiceData(number=nNF, series=serie or "", issue_date=issue_dt, total_value=total)
            return None
        # If we got full procNFe, try to parse deeper
        # Navigate to infNFe
        inf = xml_el.find(".//{*}infNFe")
        if inf is not None:
            ide = inf.find("{*}ide")
            total_v = inf.find(".//{*}ICMSTot/{*}vNF")
            nNF = ide.findtext("{*}nNF") if ide is not None else None
            serie = ide.findtext("{*}serie") if ide is not None else ""
            dhEmi = ide.findtext("{*}dhEmi") if ide is not None else None
            try:
                issue_dt = datetime.fromisoformat((dhEmi or "").replace("Z", "+00:00")).date() if dhEmi else None
            except Exception:
                issue_dt = None
            try:
                total = float(total_v.text) if total_v is not None else 0.0
            except Exception:
                total = 0.0
            if nNF and issue_dt:
                return SefazInvoiceData(number=nNF, series=serie or "", issue_date=issue_dt, total_value=total)
        return None

    def list_invoices(self, start: date, end: date) -> Iterable[SefazInvoiceData]:
        """Yield invoices within the given date range inclusive, iterating via NSU batches."""
        company = self.company
        current_nsu = int(company.last_nsu or 0)
        while True:
            ult_nsu, max_nsu, docs = self._fetch_batch(current_nsu)
            for doc in docs:
                parsed = self._parse_doc(doc)
                if not parsed:
                    continue
                if parsed.issue_date and start <= parsed.issue_date <= end:
                    yield parsed
            # Update company NSU even if no docs matched date filter
            if ult_nsu > (company.last_nsu or 0):
                company.last_nsu = ult_nsu
                company.last_nsu_updated_at = timezone.now()
                company.save(update_fields=["last_nsu", "last_nsu_updated_at", "updated_at"])
            if ult_nsu >= max_nsu:
                break
            # Prevent tight loop
            if not docs and ult_nsu == current_nsu:
                break
            current_nsu = max(ult_nsu, current_nsu)

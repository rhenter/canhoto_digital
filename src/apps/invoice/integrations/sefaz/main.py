from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Optional, Tuple
from xml.etree import ElementTree as ET

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status

from apps.company.models import Company
from . import utils
from .constants import UF_TO_CODE
from .exceptions import SefazIntegrationError



@dataclass
class SefazInvoiceData:
    """Lightweight representation of an invoice returned by SEFAZ DF-e distribution.

    Includes NF key (44 chars). When full XML is available, also carries issuer/recipient
    names and the recipient address fields.
    """
    number: str
    series: str
    key: str
    issue_date: date
    total_value: float
    # Parties
    issuer_name: str = ""
    recipient_name: str = ""
    issuer_cnpj: str = ""
    recipient_cnpj: str = ""
    tp_nf: str = ""  # '0' entrada, '1' saída (when available)
    # Recipient address
    recipient_address_street: str = ""
    recipient_address_number: str = ""
    recipient_address_neighborhood: str = ""
    recipient_address_city: str = ""
    recipient_address_uf: str = ""
    recipient_address_zip_code: str = ""
    # Raw XML and kind for persistence/generation
    raw_xml: bytes = b""
    doc_kind: str = ""  # 'procNFe' or 'resNFe'


class SefazClient:
    """Client that fetches DF-e distribution batches from SEFAZ and yields parsed invoices.

    Responsibilities (quick version):
    - Build and send SOAP requests to the national DF-e endpoint using the company's A1 certificate.
    - Parse SOAP responses and NF-e documents (summary or full) into `SefazInvoiceData`.
    - Iterate via NSU and update the company's `last_nsu` as new batches are processed.
    - Provide helper to fetch a single NF-e XML by its access key (consChNFe) for on-demand storage/DANFE.
    """

    def __init__(self, company: Company) -> None:
        self.company = company
        self.cnpj = company.cnpj

        self.http_timeout_seconds = settings.SEFAZ_HTTP_TIMEOUT_SECONDS

    def fetch_xml_by_key(self, chave_nfe: str) -> Tuple[bytes, str]:
        """Fetch a single NF-e by access key (consChNFe) and return `(xml_bytes, doc_kind)`.

        doc_kind is either 'procNFe' (full XML) or 'resNFe' (summary) depending on what
        SEFAZ provides for the requester. Raises `SefazIntegrationError` on any error.
        """
        if requests is None:
            raise SefazIntegrationError(
                "requests library is required. Please add 'requests' to your requirements and install it.")
        if not self.company.certificate or not self.company.certificate_password:
            raise SefazIntegrationError(
                "Company certificate (.pfx/.p12) and password are required for SEFAZ integration.")
        if not chave_nfe or len(chave_nfe) < 44:
            raise SefazIntegrationError("Invalid NF-e key. Expected 44 characters.")

        uf_sigla = self.company.address_uf or "RJ"
        cufa = UF_TO_CODE.get(uf_sigla.upper(), 35)
        tp_amb = 1 if self.company.sefaz_environment == "production" else 2
        endpoint = utils.get_endpoint()

        dist_xml = utils.build_distdfeint_xml_by_key(tp_amb, cufa, self.cnpj, chave_nfe)
        envelope = utils.soap_envelope(dist_xml)
        headers = {
            "Content-Type": 'application/soap+xml; charset=utf-8; action="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"',
            "SOAPAction": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse",
        }
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
            pass
        if resp.status_code != status.HTTP_200_OK:
            raise SefazIntegrationError(f"SEFAZ HTTP error: {resp.status_code} - {resp.text[:200]}")

        _ctype = resp.headers.get("Content-Type", "?") if hasattr(resp, "headers") else "?"
        _snippet = (resp.text or "")[:800]
        if "text/html" in _ctype.lower() or _snippet.lstrip().lower().startswith("<html"):
            raise SefazIntegrationError(
                f"SEFAZ returned HTML (likely gateway/mTLS issue). Check certificate file/password and endpoint. "
                f"Content-Type={_ctype}. Snippet: {_snippet[:400]}"
            )
        try:
            root = ET.fromstring(resp.content)
            ns = {
                "s": "http://www.w3.org/2003/05/soap-envelope",
                "ws": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe",
                "nfe": "http://www.portalfiscal.inf.br/nfe",
            }

            def _localname(tag: str) -> str:
                return tag.split("}")[-1] if tag else ""

            def _find_first_by_localname(el: ET.Element, name: str) -> Optional[ET.Element]:
                for child in el.iter():
                    if _localname(child.tag) == name:
                        return child
                return None

            body = root.find("s:Body", ns) or root.find("{http://www.w3.org/2003/05/soap-envelope}Body")
            if body is None:
                raise ValueError(f"SOAP Body not found (Content-Type={_ctype}). Snippet: {_snippet}")

            fault = None
            for child in body.iter():
                if _localname(child.tag) == "Fault":
                    fault = child
                    break
            if fault is not None:
                faultcode = fault.findtext("faultcode") or fault.findtext("{*}faultcode") or "?"
                faultstring = fault.findtext("faultstring") or fault.findtext("{*}faultstring") or "?"
                raise ValueError(f"SOAP Fault: {faultcode} - {faultstring} (Content-Type={_ctype}). Snippet: {_snippet}")

            result = body.find("ws:nfeDistDFeInteresseResponse/ws:nfeDistDFeInteresseResult", ns)
            if result is None:
                result = _find_first_by_localname(body, "nfeDistDFeInteresseResult")

            ret_xml = None
            search_roots = [r for r in [result, body, root] if r is not None]
            for root_candidate in search_roots:
                candidate = None
                if root_candidate is result and result is not None:
                    candidate = result.find("ws:retDistDFeInt", ns)
                    if candidate is None:
                        ret_text_el = result.find("ws:nfeResultMsg", ns) or _find_first_by_localname(result, "nfeResultMsg")
                        if ret_text_el is not None:
                            if len(ret_text_el):
                                candidate = _find_first_by_localname(ret_text_el, "retDistDFeInt") or (ret_text_el[0] if ret_text_el else None)
                            elif ret_text_el.text:
                                try:
                                    inner = ET.fromstring(ret_text_el.text.encode("utf-8"))
                                    candidate = _find_first_by_localname(inner, "retDistDFeInt") or inner
                                except Exception:
                                    pass
                if candidate is None:
                    candidate = _find_first_by_localname(root_candidate, "retDistDFeInt")
                if candidate is not None:
                    ret_xml = candidate
                    break
            if ret_xml is None:
                raise ValueError(f"retDistDFeInt not found in SOAP response (Content-Type={_ctype}). Snippet: {_snippet}")
        except Exception as e:
            raise SefazIntegrationError(f"Failed to parse SEFAZ response: {e}")

        def _localname(tag: str) -> str:
            return tag.split("}")[-1] if tag else ""

        def _findtext_by_localname(el: ET.Element, name: str) -> Optional[str]:
            for child in el.iter():
                if _localname(child.tag) == name:
                    return (child.text or "").strip() if child.text is not None else None
            return None

        def _find_first_by_localname(el: ET.Element, name: str) -> Optional[ET.Element]:
            for child in el.iter():
                if _localname(child.tag) == name:
                    return child
            return None

        c_stat = _findtext_by_localname(ret_xml, "cStat") or ""
        x_motivo = _findtext_by_localname(ret_xml, "xMotivo") or ""
        if c_stat == "656":
            raise SefazIntegrationError(
                str(_(
                    "SEFAZ cStat=656 (Rejection: Improper Consumption). You must use the last valid ultNSU in subsequent requests. "
                    "Please wait at least %(minutes)d minutes before trying again and do not reset NSU to 0."
                )) % {"minutes": settings.SEFAZ_COOLDOWN_MINUTES}
            )
        if c_stat not in {"137", "138", "139", "140", "141"}:
            raise SefazIntegrationError(f"SEFAZ returned error cStat={c_stat} ({x_motivo})")
        lote = _find_first_by_localname(ret_xml, "loteDistDFeInt")
        docs: list[ET.Element] = []
        if lote is not None:
            for child in lote.iter():
                if _localname(child.tag) == "docZip":
                    docs.append(child)
        if not docs:
            raise SefazIntegrationError("SEFAZ did not return any document for the provided key.")

        # Prefer full document when present
        chosen = None
        for d in docs:
            el = utils.decompress_doczip_to_xml(d.text or "")
            t = el.tag.split("}")[-1]
            if t == "procNFe":
                chosen = d
                break
        if chosen is None:
            chosen = docs[0]
        xml_el = utils.decompress_doczip_to_xml(chosen.text or "")
        xml_bytes = ET.tostring(xml_el, encoding="utf-8")
        tag = xml_el.tag.split("}")[-1]
        kind = "procNFe" if tag == "procNFe" else (tag if tag else "resNFe")
        return xml_bytes, kind

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
        uf_sigla = self.company.address_uf or "RJ"
        cufa = UF_TO_CODE.get(uf_sigla.upper(), 35)
        tp_amb = 1 if self.company.sefaz_environment == "production" else 2
        endpoint = utils.get_endpoint()

        dist_xml = utils.build_distdfeint_xml(tp_amb, cufa, self.cnpj, f"{ult_nsu:015d}")
        envelope = utils.soap_envelope(dist_xml)
        headers = {
            "Content-Type": 'application/soap+xml; charset=utf-8; action="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"',
            "SOAPAction": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse",
        }

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
        # Precompute debug info for any parse failure
        _ctype = resp.headers.get("Content-Type", "?") if hasattr(resp, "headers") else "?"
        _snippet = (resp.text or "")[:800]
        # Early detect HTML/gateway responses that are not SOAP (often mTLS/cert issues)
        if "text/html" in _ctype.lower() or _snippet.lstrip().lower().startswith("<html"):
            raise SefazIntegrationError(
                f"SEFAZ returned HTML (likely gateway/mTLS issue). Check certificate file/password and endpoint. "
                f"Content-Type={_ctype}. Snippet: {_snippet[:400]}"
            )
        try:
            root = ET.fromstring(resp.content)
            ns = {
                "s": "http://www.w3.org/2003/05/soap-envelope",
                "ws": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe",
                "nfe": "http://www.portalfiscal.inf.br/nfe",
            }

            def _localname(tag: str) -> str:
                return tag.split("}")[-1] if tag else ""

            def _find_first_by_localname(el: ET.Element, name: str) -> Optional[ET.Element]:
                for child in el.iter():
                    if _localname(child.tag) == name:
                        return child
                return None

            body = root.find("s:Body", ns) or root.find("{http://www.w3.org/2003/05/soap-envelope}Body")
            if body is None:
                raise ValueError(f"SOAP Body not found (Content-Type={_ctype}). Snippet: {_snippet}")

            # Detect SOAP Faults explicitly to provide clearer feedback
            fault = None
            for child in body.iter():
                if _localname(child.tag) == "Fault":
                    fault = child
                    break
            if fault is not None:
                faultcode = fault.findtext("faultcode") or fault.findtext("{*}faultcode") or "?"
                faultstring = fault.findtext("faultstring") or fault.findtext("{*}faultstring") or "?"
                raise ValueError(f"SOAP Fault: {faultcode} - {faultstring} (Content-Type={_ctype}). Snippet: {_snippet}")

            result = body.find("ws:nfeDistDFeInteresseResponse/ws:nfeDistDFeInteresseResult", ns)
            if result is None:
                result = _find_first_by_localname(body, "nfeDistDFeInteresseResult")

            # retDistDFeInt may be nested or returned directly under Body
            ret_xml = None
            search_roots = [r for r in [result, body, root] if r is not None]
            for root_candidate in search_roots:
                # Preferred: namespaced element under result
                candidate = None
                if root_candidate is result and result is not None:
                    candidate = result.find("ws:retDistDFeInt", ns)
                    if candidate is None:
                        ret_text_el = result.find("ws:nfeResultMsg", ns) or _find_first_by_localname(result, "nfeResultMsg")
                        if ret_text_el is not None:
                            if len(ret_text_el):
                                candidate = _find_first_by_localname(ret_text_el, "retDistDFeInt") or (ret_text_el[0] if ret_text_el else None)
                            elif ret_text_el.text:
                                try:
                                    inner = ET.fromstring(ret_text_el.text.encode("utf-8"))
                                    candidate = _find_first_by_localname(inner, "retDistDFeInt") or inner
                                except Exception:
                                    pass
                if candidate is None:
                    candidate = _find_first_by_localname(root_candidate, "retDistDFeInt")
                if candidate is not None:
                    ret_xml = candidate
                    break

            if ret_xml is None:
                raise ValueError(f"retDistDFeInt not found in SOAP response (Content-Type={_ctype}). Snippet: {_snippet}")
        except Exception as e:
            raise SefazIntegrationError(f"Failed to parse SEFAZ response: {e}")

        # Extract fields (namespace-insensitive)
        def _localname(tag: str) -> str:
            return tag.split("}")[-1] if tag else ""

        def _findtext_by_localname(el: ET.Element, name: str) -> Optional[str]:
            for child in el.iter():
                if _localname(child.tag) == name:
                    return (child.text or "").strip() if child.text is not None else None
            return None

        def _find_first_by_localname(el: ET.Element, name: str) -> Optional[ET.Element]:
            for child in el.iter():
                if _localname(child.tag) == name:
                    return child
            return None

        c_stat = _findtext_by_localname(ret_xml, "cStat") or ""
        x_motivo = _findtext_by_localname(ret_xml, "xMotivo") or ""
        ult_nsu_parsed = int(((_findtext_by_localname(ret_xml, "ultNSU") or "0").lstrip("0") or "0"))
        max_nsu_parsed = int(((_findtext_by_localname(ret_xml, "maxNSU") or "0").lstrip("0") or "0"))
        if c_stat not in {"137", "138", "139", "140", "141"}:
            # 137: no doc, 138: doc available, 139..: partial, 140/141 varying
            raise SefazIntegrationError(f"SEFAZ returned error cStat={c_stat} ({x_motivo})")
        docs = []
        lote = _find_first_by_localname(ret_xml, "loteDistDFeInt")
        if lote is not None:
            for child in lote.iter():
                if _localname(child.tag) == "docZip":
                    docs.append(child)
        return ult_nsu_parsed, max_nsu_parsed, docs

    def _parse_doc(self, doc_el: ET.Element) -> Optional[SefazInvoiceData]:
        """Parse a SEFAZ `docZip` element into `SefazInvoiceData` if possible.

        Supports summary `resNFe` and full `procNFe` documents.
        Returns `None` when required fields are missing.
        """
        content_b64 = doc_el.text or ""
        xml_el = utils.decompress_doczip_to_xml(content_b64)
        xml_bytes = ET.tostring(xml_el, encoding="utf-8")
        tag = xml_el.tag.split("}")[-1]
        # resNFe (summary) or procNFe/NFe (full)
        if tag == "resNFe":
            nNF = (xml_el.findtext("nNF") or "").strip()
            serie = (xml_el.findtext("serie") or "").strip()
            dhEmi = (xml_el.findtext("dhEmi") or "").strip()
            vNF = (xml_el.findtext("vNF") or "0").strip()
            chNFe = (xml_el.findtext("chNFe") or "").strip()
            xNome_emit = (xml_el.findtext("xNome") or "").strip()
            cnpj_emit = (xml_el.findtext("CNPJ") or "").strip()
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
                return SefazInvoiceData(
                    number=nNF,
                    series=serie or "",
                    key=chNFe or "",
                    issue_date=issue_dt,
                    total_value=total,
                    issuer_name=xNome_emit,
                    issuer_cnpj=cnpj_emit,
                    raw_xml=xml_bytes,
                    doc_kind="resNFe",
                )
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
            # Try to get key from protNFe or from infNFe @Id
            key = xml_el.findtext(".//{*}protNFe/{*}infProt/{*}chNFe") or ""
            if not key:
                inf_id = inf.get("Id") or ""
                if inf_id.upper().startswith("NFE") and len(inf_id) >= 47:
                    key = inf_id[3:47]
            # Parties
            emit = inf.find("{*}emit")
            dest = inf.find("{*}dest")
            issuer_name = emit.findtext("{*}xNome") if emit is not None else ""
            recipient_name = dest.findtext("{*}xNome") if dest is not None else ""
            issuer_cnpj = (emit.findtext("{*}CNPJ") if emit is not None else "") or ""
            recipient_cnpj = (dest.findtext("{*}CNPJ") if dest is not None else "") or ""
            tp_nf = (ide.findtext("{*}tpNF") if ide is not None else "") or ""
            # Recipient address (enderDest)
            ender_dest = dest.find("{*}enderDest") if dest is not None else None
            r_xLgr = ender_dest.findtext("{*}xLgr") if ender_dest is not None else ""
            r_nro = ender_dest.findtext("{*}nro") if ender_dest is not None else ""
            r_xBairro = ender_dest.findtext("{*}xBairro") if ender_dest is not None else ""
            r_xMun = ender_dest.findtext("{*}xMun") if ender_dest is not None else ""
            r_UF = ender_dest.findtext("{*}UF") if ender_dest is not None else ""
            r_CEP = ender_dest.findtext("{*}CEP") if ender_dest is not None else ""
            try:
                issue_dt = datetime.fromisoformat((dhEmi or "").replace("Z", "+00:00")).date() if dhEmi else None
            except Exception:
                issue_dt = None
            try:
                total = float(total_v.text) if total_v is not None else 0.0
            except Exception:
                total = 0.0
            if nNF and issue_dt:
                return SefazInvoiceData(
                    number=nNF,
                    series=serie or "",
                    key=key,
                    issue_date=issue_dt,
                    total_value=total,
                    issuer_name=issuer_name or "",
                    recipient_name=recipient_name or "",
                    issuer_cnpj=issuer_cnpj,
                    recipient_cnpj=recipient_cnpj,
                    tp_nf=tp_nf,
                    recipient_address_street=r_xLgr or "",
                    recipient_address_number=r_nro or "",
                    recipient_address_neighborhood=r_xBairro or "",
                    recipient_address_city=r_xMun or "",
                    recipient_address_uf=r_UF or "",
                    recipient_address_zip_code=r_CEP or "",
                    raw_xml=xml_bytes,
                    doc_kind="procNFe",
                )
        return None

    def list_invoices(self, start: date, end: date) -> Iterable[SefazInvoiceData]:
        """Yield ALL invoices (entrada e saída) within the given date range inclusive, iterating via NSU batches.

        Notes:
        - No filtro por tipo de nota (tpNF). Serão retornadas notas onde a SEFAZ relaciona a empresa
          (tanto emitidas quanto recebidas), respeitando apenas o intervalo de datas informado.
        """
        company = self.company
        # Avoid SEFAZ cStat=656 when rebootstrapping NSU=0 too soon
        if (company.last_nsu or 0) == 0 and company.last_nsu_updated_at:
            if timezone.now() - company.last_nsu_updated_at < timedelta(minutes=settings.SEFAZ_COOLDOWN_MINUTES):
                raise SefazIntegrationError(
                    str(_(
                        "Operation temporarily blocked: NSU was recently reset. Please wait at least %(minutes)d minutes "
                        "before trying again to avoid SEFAZ cStat=656 (Improper Consumption)."
                    )) % {"minutes": settings.SEFAZ_COOLDOWN_MINUTES}
                )

        current_nsu = int(company.last_nsu or 0)
        while True:
            ult_nsu, max_nsu, docs = self._fetch_batch(current_nsu)
            for doc in docs:
                parsed = self._parse_doc(doc)
                if not parsed:
                    continue
                # Sem filtro de saída: inclui entrada (0) e saída (1)
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

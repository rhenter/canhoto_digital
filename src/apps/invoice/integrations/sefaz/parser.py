from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from xml.etree import ElementTree as ET

from django.utils.translation import gettext_lazy as _


def parse_nfe_xml(xml_bytes: bytes) -> Dict[str, Any]:
    """Parse NF-e XML bytes (NFe or procNFe) and return a dict with Invoice-like fields.

    Supported roots: `NFe`, `procNFe`, `nfeProc` or any wrapper containing an `NFe` element.
    Returns a dict containing at least: number, series, key, issue_date, total_value,
    issuer_name, recipient_name, and recipient address fields.

    Raises ValueError with a translated message on invalid or incomplete XML.
    """
    if not xml_bytes:
        raise ValueError(_("Empty XML file"))
    try:
        xml_el = ET.fromstring(xml_bytes)
    except Exception:
        raise ValueError(_("Invalid XML file"))

    # If root is procNFe/nfeProc, navigate to NFe
    tag = xml_el.tag.split('}')[-1]
    if tag in ("procNFe", "nfeProc"):
        nfe_el = xml_el.find('.//{*}NFe')
        if nfe_el is None:
            raise ValueError(_("procNFe without NFe element"))
    elif tag == 'NFe':
        nfe_el = xml_el
    else:
        # Some vendors wrap with extra elements; try to find NFe
        nfe_el = xml_el.find('.//{*}NFe')
        if nfe_el is None:
            raise ValueError(_("XML does not appear to be an NF-e (NFe/procNFe)"))

    inf = nfe_el.find('.//{*}infNFe') if nfe_el is not None else None
    if inf is None:
        raise ValueError(_("Missing infNFe element"))

    ide = inf.find('{*}ide')
    emit = inf.find('{*}emit')
    dest = inf.find('{*}dest')
    total_v = inf.find('.//{*}ICMSTot/{*}vNF')

    # Basic values
    number = (ide.findtext('{*}nNF') if ide is not None else '') or ''
    series = (ide.findtext('{*}serie') if ide is not None else '') or ''
    dhEmi = (ide.findtext('{*}dhEmi') if ide is not None else '') or ''
    issuer_name = (emit.findtext('{*}xNome') if emit is not None else '') or ''
    recipient_name = (dest.findtext('{*}xNome') if dest is not None else '') or ''

    # Key from protNFe or infNFe Id
    key = xml_el.findtext('.//{*}protNFe/{*}infProt/{*}chNFe') or ''
    if not key:
        inf_id = (inf.get('Id') or '')
        if inf_id.upper().startswith('NFE') and len(inf_id) >= 47:
            key = inf_id[3:47]

    # Issue date
    issue_date = None
    if dhEmi:
        try:
            issue_date = datetime.fromisoformat(dhEmi.replace('Z', '+00:00')).date()
        except Exception:
            issue_date = None

    # Total value
    try:
        # Some XMLs may use comma as decimal separator; normalize
        total_value = Decimal((total_v.text or '0').replace(',', '.')) if total_v is not None else Decimal('0')
    except Exception:
        total_value = Decimal('0')

    # Recipient address
    ender_dest = dest.find('{*}enderDest') if dest is not None else None
    r_xLgr = ender_dest.findtext('{*}xLgr') if ender_dest is not None else ''
    r_nro = ender_dest.findtext('{*}nro') if ender_dest is not None else ''
    r_xBairro = ender_dest.findtext('{*}xBairro') if ender_dest is not None else ''
    r_xMun = ender_dest.findtext('{*}xMun') if ender_dest is not None else ''
    r_UF = ender_dest.findtext('{*}UF') if ender_dest is not None else ''
    r_CEP = ender_dest.findtext('{*}CEP') if ender_dest is not None else ''

    if not number:
        raise ValueError(_("NF-e number not found in XML"))

    data = {
        'number': number,
        'series': series,
        'key': key,
        'issue_date': issue_date,
        'total_value': total_value,
        'issuer_name': issuer_name,
        'recipient_name': recipient_name,
        'recipient_address_street': r_xLgr or '',
        'recipient_address_number': r_nro or '',
        'recipient_address_neighborhood': r_xBairro or '',
        'recipient_address_city': r_xMun or '',
        'recipient_address_uf': r_UF or '',
        'recipient_address_zip_code': r_CEP or '',
    }
    return data

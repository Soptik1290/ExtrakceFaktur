
import re
from .utils import parse_amount

def _is_vs(vs):
    if not vs: return False
    vs = str(vs).strip()
    # Remove common prefixes/suffixes
    vs = re.sub(r"^(VS|VS\.|Variabilní symbol|Variabilní symbol:?)\s*", "", vs, flags=re.I)
    vs = re.sub(r"\s*$", "", vs)
    # Check if it's a valid format
    if re.fullmatch(r"\d{2,12}", vs): return True
    if re.fullmatch(r"[A-Z0-9]{2,12}", vs): return True
    return False

def _ico_checksum(ico: str) -> bool:
    if not ico: return False
    # Clean ICO - remove non-digits
    ico = re.sub(r"\D", "", str(ico))
    if not re.fullmatch(r"\d{8}", ico): return False
    digits = [int(x) for x in ico]
    s = sum(digits[i] * (8 - i) for i in range(7))
    mod = s % 11
    if mod == 0: c = 1
    elif mod == 1: c = 0
    elif mod == 10: c = 1
    else: c = 11 - mod
    return digits[7] == c

def _dic_valid(dic: str) -> bool:
    if not dic: return False
    dic = str(dic).strip().upper()
    # Handle common Czech DIČ format: CZ12345678
    if re.fullmatch(r"CZ\d{8,10}", dic): return True
    # Handle other EU VAT formats
    if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{8,12}", dic): return True
    return False

def _sum_valid(bez_dph, dph, s_dph, tol=0.03):
    b = parse_amount(bez_dph)
    d = parse_amount(dph)
    s = parse_amount(s_dph)
    if b is None or d is None or s is None:
        return None
    return abs((b + d) - s) <= tol

def validate_extraction(data: dict) -> dict:
    data = data or {}
    vs_ok = _is_vs(data.get("variabilni_symbol"))
    supplier = data.get("dodavatel")
    if not isinstance(supplier, dict):
        supplier = {"ico": None, "dic": None}
    ico = supplier.get("ico")
    dic = supplier.get("dic")
    import re as _re
    ico_ok = _ico_checksum(ico) if ico else False
    dic_ok = _dic_valid(dic) if dic else False
    sum_ok = _sum_valid(data.get("castka_bez_dph"), data.get("dph"), data.get("castka_s_dph"))
    return {
        "variabilni_symbol": vs_ok,
        "ico": ico_ok,
        "dic": dic_ok,
        "sum_check": sum_ok
    }

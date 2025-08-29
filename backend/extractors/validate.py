import re
from .utils import parse_amount

def _is_vs(vs):
    if not vs: return False
    vs = str(vs).strip()
    if re.fullmatch(r"[A-Z0-9\-]{2,12}", vs): return True
    return False

def _ico_checksum(ico: str) -> bool:
    if not ico or not re.fullmatch(r"\d{8}", str(ico)):
        return False
    digits = [int(c) for c in str(ico)]
    weights = [8,7,6,5,4,3,2]
    s = sum(d*w for d,w in zip(digits[:7], weights))
    m = s % 11
    if m == 0: c = 1
    elif m == 1: c = 0
    else: c = 11 - m
    return digits[7] == c

def _dic_valid(dic: str, text: str) -> bool:
    if not dic: return False
    if not re.fullmatch(r"CZ\d{8,10}", dic): return False
    return dic.lower() in (text or "").lower()

def _sum_valid(bez, dph, sdp) -> bool:
    bez = parse_amount(bez)
    dph = parse_amount(dph)
    sdp = parse_amount(sdp)
    known = [x for x in (bez, dph, sdp) if x is not None]
    if len(known) < 2:
        return True
    if bez is not None and dph is not None and sdp is not None:
        return abs((bez + dph) - sdp) <= 0.05
    if bez is not None and sdp is not None and dph is None:
        return True
    if dph is not None and sdp is not None and bez is None:
        return True
    return True

def validate_extraction(data: dict, ocr_text: str) -> dict:
    data = data or {}
    supplier = data.get("dodavatel") or {}
    ico = supplier.get("ico")
    dic = supplier.get("dic")
    return {
        "variabilni_symbol": _is_vs(data.get("variabilni_symbol")),
        "ico_checksum": _ico_checksum(ico) if ico else False,
        "dic_format_and_in_text": _dic_valid(dic, ocr_text) if dic else False,
        "sum_check": _sum_valid(data.get("castka_bez_dph"), data.get("dph"), data.get("castka_s_dph")),
    }

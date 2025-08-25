import re
from .utils import parse_amount

def _is_vs(vs):
    if not vs:
        return False
    vs = re.sub(r"\D", "", str(vs))
    return 2 <= len(vs) <= 10

def _ico_checksum(ico: str) -> bool:
    if not ico or not re.fullmatch(r"\d{8}", ico):
        return False
    digits = [int(x) for x in ico]
    s = sum(digits[i] * (8 - i) for i in range(7))
    mod = s % 11
    if mod == 0:
        c = 1
    elif mod == 1:
        c = 0
    elif mod == 10:
        c = 1
    else:
        c = 11 - mod
    return digits[7] == c

def _dic_valid(dic: str) -> bool:
    if not dic:
        return False
    dic = dic.strip().upper()
    if re.fullmatch(r"CZ\d{8,10}", dic):
        return True
    if re.fullmatch(r"[A-Z]{{2}}[A-Z0-9]{{8,12}}", dic):
        return True
    return False

def _sum_valid(bez_dph, dph, s_dph, tol=0.03):
    b = parse_amount(bez_dph)
    d = parse_amount(dph)
    s = parse_amount(s_dph)
    if b is None or d is None or s is None:
        return None
    return abs((b + d) - s) <= tol

def validate_extraction(data: dict) -> dict:
    vs_ok = _is_vs(data.get("variabilni_symbol"))
    ico = data.get("dodavatel", {}).get("ico")
    dic = data.get("dodavatel", {}).get("dic")
    ico_ok = _ico_checksum(re.sub(r"\D","",ico)) if ico else False
    dic_ok = _dic_valid(dic) if dic else False
    sum_ok = _sum_valid(data.get("castka_bez_dph"), data.get("dph"), data.get("castka_s_dph"))
    return {
        "variabilni_symbol": vs_ok,
        "ico": ico_ok,
        "dic": dic_ok,
        "sum_check": sum_ok
    }

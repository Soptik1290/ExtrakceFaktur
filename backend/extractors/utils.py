import re
from datetime import datetime
from dateutil import parser as dateparser

def normalize_date(s):
    if not s:
        return None
    s = str(s).strip()
    try:
        dt = dateparser.parse(s, dayfirst=True, yearfirst=False)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        try:
            dt = dateparser.parse(s, dayfirst=False, yearfirst=True)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None

_CURRENCY_MAP = [
    ("CZK", [r"\bKč\b", r"\bCZK\b"]),
    ("EUR", [r"\b€\b", r"\bEUR\b"]),
    ("USD", [r"\$\b", r"\bUSD\b"]),
    ("GBP", [r"\£\b", r"\bGBP\b"]),
]

def detect_currency(text: str):
    text = text or ""
    votes = {}
    for code, pats in _CURRENCY_MAP:
        for p in pats:
            if re.search(p, text, re.I):
                votes[code] = votes.get(code, 0) + 1
    if not votes:
        return None
    return sorted(votes.items(), key=lambda kv: kv[1], reverse=True)[0][0]

def parse_amount(s):
    if s is None:
        return None
    s = str(s)
    s = re.sub(r"(Kč|CZK|EUR|€|USD|\$|GBP|£|PLN|zł|HUF|Ft|CHF|SEK|NOK|DKK|JPY|¥|CNY|AUD|CAD)", "", s, flags=re.I)
    s = s.replace("\u00A0", " ").strip()
    s = re.sub(r"[^\d.,\-]", "", s)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        if s.count(".") > 1:
            parts = s.split(".")
            s = "".join(parts[:-1]) + "." + parts[-1]
    s = s.replace(" ", "")
    try:
        return round(float(s), 2)
    except Exception:
        return None

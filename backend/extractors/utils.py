
import re
from datetime import datetime
from dateutil import parser as dateparser

def first(seq):
    return seq[0] if seq else None

def normalize_date(s):
    if not s:
        return None
    s = str(s).strip()
    try:
        dt = dateparser.parse(s, dayfirst=True, yearfirst=False)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    m = re.search(r"\b(\d{1,2})[.\-/ ](\d{1,2})[.\-/ ](\d{2,4})\b", s)
    if m:
        d, mth, y = m.groups()
        y = "20"+y if len(y)==2 else y
        try:
            dt = datetime(int(y), int(mth), int(d))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None
    return None

def parse_amount(s):
    if s is None:
        return None
    s = str(s)
    if re.fullmatch(r"\d{7,}", s.strip()):
        return None
    s = s.replace("\u00A0", " ")
    s = re.sub(r"(Kč|CZK|EUR|€|USD|\$|GBP|£|PLN|zł|HUF|Ft|CHF|SEK|NOK|DKK|JPY|¥|CNY|AUD|CAD)", "", s, flags=re.I)
    s = s.replace(" ", "").replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d{1,2})", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

_CURRENCY_MAP = [
    ("CZK", [r"\bCZK\b", r"\bKč\b"]),
    ("EUR", [r"\bEUR\b", r"€"]),
    ("USD", [r"\bUSD\b", r"\$"]),
    ("GBP", [r"\bGBP\b", r"£"]),
    ("PLN", [r"\bPLN\b", r"zł"]),
    ("HUF", [r"\bHUF\b", r"\bFt\b"]),
    ("CHF", [r"\bCHF\b"]),
    ("SEK", [r"\bSEK\b", r"\bkr\b"]),
    ("NOK", [r"\bNOK\b", r"\bkr\b"]),
    ("DKK", [r"\bDKK\b", r"\bkr\b"]),
    ("JPY", [r"\bJPY\b", r"¥"]),
    ("CNY", [r"\bCNY\b", r"¥"]),
    ("AUD", [r"\bAUD\b"]),
    ("CAD", [r"\bCAD\b"]),
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

def pick_nearby(text, keywords, value_regex, window=200):
    for kw in keywords:
        for m in re.finditer(kw, text, re.I):
            start = max(0, m.start()-window//2)
            end = min(len(text), m.end()+window//2)
            sub = text[start:end]
            vm = re.search(value_regex, sub, re.I)
            if vm:
                return vm.group(0)
    return None

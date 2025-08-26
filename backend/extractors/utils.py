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
    s = str(s).strip()
    s = s.replace("\u00A0", " ").replace(" ", "")
    s = re.sub(r"[A-Z€$₤£KčCZK]", "", s, flags=re.I)
    s = s.replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d{1,2})?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

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

def detect_currency(text):
    if re.search(r"\b(CZK|Kč)\b", text, re.I):
        return "CZK"
    if re.search(r"€|\bEUR\b", text, re.I):
        return "EUR"
    if re.search(r"\bUSD\b|\$", text, re.I):
        return "USD"
    return None

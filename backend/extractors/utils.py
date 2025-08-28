
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
    
    # OCR korekce pro české částky
    s = _correct_amount_ocr(s)
    
    # Handle Czech number format: "44 413,00" -> "44413.00"
    # First, normalize decimal separator
    s = s.replace(",", ".")
    
    # Then remove spaces that are thousands separators (but keep decimal part)
    if "." in s:
        parts = s.split(".")
        if len(parts) == 2:  # Has decimal part
            integer_part = parts[0].replace(" ", "")
            decimal_part = parts[1]
            s = f"{integer_part}.{decimal_part}"
        else:
            # Multiple dots, treat as thousands separators except the last one
            integer_part = "".join(parts[:-1]).replace(" ", "")
            decimal_part = parts[-1]
            s = f"{integer_part}.{decimal_part}"
    else:
        # No decimal part, just remove spaces
        s = s.replace(" ", "")
    
    # Handle cases like "44 413" where the space is clearly a thousands separator
    if re.match(r"^\d{1,3} \d{3}$", s):
        s = s.replace(" ", "")
    
    # Handle cases like "44 413,00" where the space is clearly a thousands separator
    if re.match(r"^\d{1,3} \d{3},\d{2}$", s):
        s = s.replace(",", ".")
    
    # Additional check for Czech number patterns like "44 413" (without decimal)
    if re.match(r"^\d{1,3}(?: \d{3})+$", s):
        s = s.replace(" ", "")
    
    m = re.search(r"-?\d+(?:\.\d{1,2})", s)
    if not m:
        # Try to find just the integer part if no decimal found
        m = re.search(r"-?\d+", s)
        if m:
            try:
                return float(m.group(0))
            except Exception:
                pass
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

def _correct_amount_ocr(s: str) -> str:
    """Opravuje běžné OCR chyby v částkách"""
    # Běžné OCR chyby v číslech
    ocr_corrections = {
        'O': '0', 'o': '0',  # O/o -> 0
        'l': '1', 'I': '1', '|': '1',  # l/I/| -> 1
        'S': '5', 's': '5',  # S/s -> 5
        'B': '8', 'G': '6',  # B -> 8, G -> 6
        'Z': '2', 'z': '2',  # Z/z -> 2
        'g': '9', 'q': '9',  # g/q -> 9
        'D': '0', 'd': '0',  # D/d -> 0
    }
    
    # Aplikuj korekce
    for wrong, correct in ocr_corrections.items():
        s = s.replace(wrong, correct)
    
    # Oprav podezřele malé částky (např. 4413 -> 44 413)
    # Pokud je částka 4-5 číslic a vypadá podezřele malá
    if re.match(r'^\d{4,5}$', s.strip()):
        # Zkus najít větší částku v okolním textu
        # Toto je základní heuristika - v reálném použití by bylo lepší
        # analyzovat celý text a najít konzistentní částky
        pass
    
    return s

def _detect_amount_errors(text: str) -> list:
    """Detekuje potenciální chyby v částkách"""
    errors = []
    
    # Hledej podezřele malé částky
    small_amounts = re.findall(r'\b\d{4,5}\b', text)
    for amount in small_amounts:
        val = int(amount)
        if 1000 <= val < 10000:  # 4 číslice
            errors.append(f"Podezřele malá částka: {amount} (možná chybí mezera)")
        elif 10000 <= val < 100000:  # 5 číslic
            errors.append(f"Podezřele malá částka: {amount} (možná chybí mezera)")
    
    # Hledej nekonzistentní formátování
    if re.search(r'\d{1,3} \d{3}', text) and re.search(r'\d{4,}', text):
        errors.append("Smíšené formátování částek (s mezerami i bez)")
    
    return errors

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

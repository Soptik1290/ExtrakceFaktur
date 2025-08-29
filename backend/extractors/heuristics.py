import re
from .utils import normalize_date, parse_amount, detect_currency

DATE = r"(?:\d{1,2}[.\-/ ]\d{1,2}[.\-/ ]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})"
AMOUNT = r"\d{1,3}(?:[ \u00A0]\d{3})*(?:[.,]\d{2})|\d{1,3}(?:[ \u00A0]\d{3})+|\d+[.,]\d{2}|\d+"
IBAN = r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}"
CZ_ACC = r"\b\d{1,6}-?\d{2,10}/\d{4}\b"
BIC = r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?\b"

LABELS = {
    "vs": [r"variabiln[íi]\s*symbol\b", r"\bVS\b"],
    "issue": [r"datum\s*vystaven[íi]\b", r"\bvystaveno\b", r"\bissued\b"],
    "due": [r"datum\s*spla[tť]nosti\b", r"\bsplatnost\b", r"\bdue\b"],
    "duzp": [r"\bduzp\b", r"tax\s*point"],
    "total": [r"celkem\s*k\s*uhrad[ěe]\b", r"grand\s*total\b", r"\bcelkem\b"],
    "base": [r"celkem\s*bez\s*dph\b", r"základ\s*dan[eě]\b", r"bez\s*dph\b"],
    "vat": [r"\bdph\b", r"\bvat\b"],
    "payment": [r"zp[ůu]sob\s*platby\b", r"payment\s*method\b", r"\bplatba\b"],
    "bank": [r"\bbanka\b", r"bankovn[íi]"],
    "account": [r"bankovn[íi]\s*[úu]čet\b", r"\bIBAN\b", r"\bBIC\b", r"\bSWIFT\b"],
}

def _compile_any(patterns):
    return re.compile("|".join(patterns), re.I)

LAB = {k: _compile_any(v) for k, v in LABELS.items()}

def _iter_lines(text):
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

def _near(lines, i, pat_value, window=2):
    r = re.compile(pat_value, re.I)
    m = r.search(lines[i])
    if m: return m.group(0)
    for off in range(1, window+1):
        if i+off < len(lines):
            m = r.search(lines[i+off])
            if m: return m.group(0)
        if i-off >= 0:
            m = r.search(lines[i-off])
            if m: return m.group(0)
    return None

def _find_labeled(lines, lab_regex, val_regex, window=2):
    vals = []
    for i, ln in enumerate(lines):
        if lab_regex.search(ln):
            v = _near(lines, i, val_regex, window)
            if v:
                score = 3 if re.search(val_regex, ln, re.I) else 2
                vals.append((v, score, i))
    vals.sort(key=lambda t: (-t[1], t[2]))
    return vals[0][0] if vals else None

def _find_any(regex, text):
    m = re.search(regex, text, re.I)
    return m.group(0) if m else None

def _largest_amount_near(text, label_patterns):
    lines = _iter_lines(text)
    idxs = [i for i,ln in enumerate(lines) if any(re.search(p, ln, re.I) for p in label_patterns)]
    cand = []
    for i in idxs:
        win = lines[max(0,i-3):min(len(lines), i+4)]
        nums = re.findall(AMOUNT, "\n".join(win))
        nums = [parse_amount(x) for x in nums]
        nums = [x for x in nums if isinstance(x, (int,float))]
        if nums:
            cand.append(max(nums))
    return f"{max(cand):.2f}" if cand else None

def extract_fields_heuristic(text: str) -> dict:
    lines = _iter_lines(text)
    joined = "\n".join(lines)

    vyst = _find_labeled(lines, LAB["issue"], DATE)
    splat = _find_labeled(lines, LAB["due"], DATE)
    duzp = _find_labeled(lines, LAB["duzp"], DATE)

    bez = _find_labeled(lines, LAB["base"], AMOUNT)
    dph = _find_labeled(lines, LAB["vat"], AMOUNT)
    total = _find_labeled(lines, LAB["total"], AMOUNT)
    if not total:
        total = _largest_amount_near(joined, LABELS["total"]) or _find_any(AMOUNT, joined)

    result = {
        "variabilni_symbol": _find_labeled(lines, LAB["vs"], r"[A-Z0-9\-]{2,12}"),
        "datum_vystaveni": (vyst and __import__("backend.extractors.utils", fromlist=["normalize_date"]).normalize_date(vyst)) or None,
        "datum_splatnosti": (splat and __import__("backend.extractors.utils", fromlist=["normalize_date"]).normalize_date(splat)) or None,
        "duzp": (duzp and __import__("backend.extractors.utils", fromlist=["normalize_date"]).normalize_date(duzp)) or None,
        "castka_bez_dph": __import__("backend.extractors.utils", fromlist=["parse_amount"]).parse_amount(bez) if bez else None,
        "dph": __import__("backend.extractors.utils", fromlist=["parse_amount"]).parse_amount(dph) if dph else None,
        "castka_s_dph": __import__("backend.extractors.utils", fromlist=["parse_amount"]).parse_amount(total) if total else None,
        "dodavatel": {
            "nazev": None,
            "ico": _find_any(r"\b(?:IČO|ICO)[:\s]*([0-9]{8})", joined) and re.search(r"\b(?:IČO|ICO)[:\s]*([0-9]{8})", joined, re.I).group(1),
            "dic": _find_any(r"\b(?:DIČ|DIC)[:\s]*([A-Z]{2}\d{8,10})", joined) and re.search(r"\b(?:DIČ|DIC)[:\s]*([A-Z]{2}\d{8,10})", joined, re.I).group(1),
            "adresa": _find_any(r"[A-Za-zÁ-ž0-9 .\-]+,\s*\d{3}\s*\d{2}\s*[A-Za-zÁ-ž ]+", joined),
        },
        "mena": __import__("backend.extractors.utils", fromlist=["detect_currency"]).detect_currency(joined) or ("CZK" if "Kč" in joined else None),
        "platba_zpusob": _find_labeled(lines, LAB["payment"], r"[A-Za-zÁ-ž \-]+"),
        "banka_prijemce": _find_labeled(lines, LAB["bank"], r"[A-Za-z0-9Á-ž .\-]+"),
        "ucet_prijemce": (_find_any(IBAN, joined) or _find_any(CZ_ACC, joined) or _find_any(BIC, joined)),
        "confidence": 0.7,
    }
    return result


import re
from .utils import normalize_date, parse_amount, first, pick_nearby, detect_currency

DATE_PAT = r"(?:\b\d{1,2}[.\-/ ]\d{1,2}[.\-/ ]\d{2,4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b)"
AMOUNT_PAT_STRICT = r"\b\d{1,3}(?:[ \u00A0]\d{3})*(?:[,.]\d{2})\b|\b\d+[,.]\d{2}\b"
CURRENCY_TOKEN = r"(?:CZK|Kč|EUR|€|USD|\$|GBP|£|PLN|zł|HUF|Ft|CHF|SEK|NOK|DKK|JPY|¥|CNY|AUD|CAD)"

def _find_label_value(lines, label_keywords, value_regex, max_dist=2):
    label_re = re.compile("|".join(label_keywords), re.I)
    val_re = re.compile(value_regex)
    candidates = []
    for i, line in enumerate(lines):
        if label_re.search(line):
            window = "\n".join(lines[max(0, i - max_dist): i + max_dist + 1])
            for m in val_re.finditer(window):
                candidates.append(m.group(0))
    return first(candidates)

def _find_any(regex, text):
    m = re.search(regex, text, re.I | re.M)
    return m.group(1) if (m and m.groups()) else (m.group(0) if m else None)

def _clean_lines(text: str):
    return [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]

def _detect_vs(text: str, lines):
    vs = _find_label_value(lines, [r"\bvariab\w* symbol\b", r"\bVS\b", r"variable symbol"], r"\b(\d{6,12})\b", 3)
    if vs:
        return re.sub(r"\D", "", vs)
    vs = _find_any(r"\bVS[:\s]+(\d{6,12})\b", "\n".join(lines))
    if vs:
        return vs
    candidates = []
    j = "\n".join(lines)
    for m in re.finditer(r"\b(\d{8,10})\b(?!\s*/)", j):
        left = j[max(0, m.start()-20):m.start()].lower()
        if ("ucet" in left or "účet" in left or "account" in left):
            continue
        candidates.append(m.group(1))
    return first(candidates)

def _amounts_from_text(text: str):
    raw = re.findall(AMOUNT_PAT_STRICT, text)
    parsed = []
    for a in raw:
        val = parse_amount(a)
        if val is None:
            continue
        if val > 1e7:
            continue
        parsed.append(val)
    return parsed

def _currency_near_amount(lines):
    joined = "\n".join(lines)
    for lab in [r"amount due", r"grand total", r"\btotal\b", r"celkem", r"k úhradě", r"subtotal", r"bez dph", r"dph"]:
        m = re.search(lab + r".{0,40}" + CURRENCY_TOKEN, joined, re.I)
        if m:
            cur = re.search(CURRENCY_TOKEN, m.group(0), re.I)
            if cur:
                tok = cur.group(0).upper()
                sym_map = {"€": "EUR", "$": "USD", "£": "GBP", "KČ": "CZK", "¥": "JPY"}
                return sym_map.get(tok, tok.replace("KČ", "CZK"))
    return None

def extract_fields_heuristic(text: str) -> dict:
    lines = _clean_lines(text)
    joined = "\n".join(lines)

    vs = _detect_vs(joined, lines)

    vyst = _find_label_value(lines, [r"datum vyst", r"vystaven", r"issue"], DATE_PAT, 3) \
        or pick_nearby(joined, ["vyst", "issue"], DATE_PAT)
    splat = _find_label_value(lines, [r"splatnost", r"due date", r"payment due"], DATE_PAT, 3) \
        or pick_nearby(joined, ["splatnost", "due"], DATE_PAT)
    duzp = _find_label_value(lines, [r"duzp", r"tax point", r"date of taxable"], DATE_PAT, 3) \
        or pick_nearby(joined, ["duzp", "tax point"], DATE_PAT)

    vyst = normalize_date(vyst); splat = normalize_date(splat); duzp = normalize_date(duzp)

    castka_s = _find_label_value(lines, [r"celkem k \w*uhra", r"celkem", r"total", r"amount due", r"grand total"], AMOUNT_PAT_STRICT, 3)
    bez_dph = _find_label_value(lines, [r"bez dph", r"základ daně", r"zaklad dane", r"subtotal"], AMOUNT_PAT_STRICT, 3)
    dph = _find_label_value(lines, [r"\bdph\b", r"\bvat\b"], AMOUNT_PAT_STRICT, 3)

    if not (castka_s and bez_dph and dph):
        nums = _amounts_from_text(joined)
        nums = sorted(nums)
        if nums:
            castka_s = castka_s or f"{nums[-1]:.2f}"
        if bez_dph and not dph and castka_s:
            try:
                b = parse_amount(bez_dph); s = parse_amount(castka_s)
                if b is not None and s is not None and s >= b:
                    dph = f"{(s - b):.2f}"
            except Exception:
                pass
        if dph and not bez_dph and castka_s:
            try:
                d = parse_amount(dph); s = parse_amount(castka_s)
                if d is not None and s is not None and s >= d:
                    bez_dph = f"{(s - d):.2f}"
            except Exception:
                pass

    cur = _currency_near_amount(lines) or detect_currency(joined)

    supplier = {"nazev": None, "ico": None, "dic": None, "adresa": None}

    result = {
        "variabilni_symbol": vs,
        "datum_vystaveni": vyst,
        "datum_splatnosti": splat,
        "duzp": duzp,
        "castka_bez_dph": parse_amount(bez_dph) if bez_dph else None,
        "dph": parse_amount(dph) if dph else None,
        "castka_s_dph": parse_amount(castka_s) if castka_s else None,
        "dodavatel": supplier,
        "mena": cur,
        "confidence": 0.62
    }
    return result

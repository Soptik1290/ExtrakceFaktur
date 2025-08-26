import re
from .utils import normalize_date, parse_amount, first, pick_nearby, detect_currency

DATE_PAT = r"(?:\b\d{1,2}[.\-/ ]\d{1,2}[.\-/ ]\d{2,4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b)"
AMOUNT_PAT = r"(?:\d{1,3}(?:[ \u00A0]\d{3})*(?:[,.]\d{2})|\d+(?:[,.]\d{2})?)"

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
    return m.group(0) if m else None

def extract_fields_heuristic(text: str) -> dict:
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]
    joined = "\n".join(lines)

    vs = _find_label_value(lines, [r"\bvariab\w* symbol\b", r"\bVS\b"], r"\b\d{6,12}\b", 2) \
        or _find_any(r"\bVS[: ]*(\d{6,12})\b", joined)
    if not vs:
        blocks = re.findall(r"\b\d{8,12}\b", joined)
        vs = first(blocks)

    vyst = _find_label_value(lines, [r"datum vyst", r"vystaven", r"issue"], DATE_PAT) \
        or pick_nearby(joined, ["vyst", "issue"], DATE_PAT)
    splat = _find_label_value(lines, [r"splatnost", r"due date", r"payment due"], DATE_PAT) \
        or pick_nearby(joined, ["splatnost", "due"], DATE_PAT)
    duzp = _find_label_value(lines, [r"duzp", r"tax point", r"date of taxable"], DATE_PAT) \
        or pick_nearby(joined, ["duzp", "tax point"], DATE_PAT)

    from .utils import normalize_date as nd
    vyst = nd(vyst); splat = nd(splat); duzp = nd(duzp)

    castka_s = _find_label_value(lines, [r"celkem k \w*uhra", r"celkem", r"total", r"amount due"], AMOUNT_PAT)
    bez_dph = _find_label_value(lines, [r"bez dph", r"základ daně", r"zaklad dane", r"subtotal"], AMOUNT_PAT)
    dph = _find_label_value(lines, [r"\bdph\b", r"\bvat\b"], AMOUNT_PAT)

    if not (castka_s and bez_dph and dph):
        amounts = [a for a in re.findall(AMOUNT_PAT, joined) if re.search(r"\d", a)]
        amounts_parsed = [parse_amount(a) for a in amounts]
        if amounts_parsed:
            a_sorted = sorted([x for x in amounts_parsed if x is not None])
            if a_sorted:
                castka_s = castka_s or f"{a_sorted[-1]:.2f}"

    curr = detect_currency(joined)

    supplier = {"nazev": None, "ico": None, "dic": None, "adresa": None}

    result = {
        "variabilni_symbol": vs,
        "datum_vystaveni": vyst,
        "datum_splatnosti": splat,
        "duzp": duzp,
        "castka_bez_dph": bez_dph,
        "dph": dph,
        "castka_s_dph": castka_s,
        "dodavatel": supplier,
        "mena": curr,
        "confidence": 0.55
    }
    return result

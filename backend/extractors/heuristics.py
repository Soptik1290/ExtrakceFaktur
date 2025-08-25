import re
from .utils import normalize_date, parse_amount, first, pick_nearby, detect_currency

# Basic patterns (CZ + EN keywords)
DATE_PAT = r"(?:\b\d{1,2}[.\-/ ]\d{1,2}[.\-/ ]\d{2,4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b)"
AMOUNT_PAT = r"(?:\d{1,3}(?:[ \u00A0]\d{3})*(?:[,.]\d{2})|\d+(?:[,.]\d{2})?)"

def _find_label_value(lines, label_keywords, value_regex, max_dist=2):
    """Find a value near any label keywords within a small window of lines."""
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

    # Variabilní symbol (prefer near labels, else naked 8-10 digits)
    vs = _find_label_value(
        lines,
        [r"\bvariab\w* symbol\b", r"\bVS\b"],
        r"\b\d{6,10}\b",
        max_dist=2
    ) or _find_any(r"\bVS[: ]*\b(\d{6,10})\b", joined)
    if isinstance(vs, tuple):  # if captured group
        vs = vs[0]
    if not vs:
        # fallback: longest 8-10 digit block in document
        blocks = re.findall(r"\b\d{8,10}\b", joined)
        vs = first(blocks)

    # Dates
    vyst = _find_label_value(lines, [r"datum vyst", r"vystaven", r"issue"], DATE_PAT) \
        or pick_nearby(joined, ["vyst", "issue"], DATE_PAT)
    splat = _find_label_value(lines, [r"splatnost", r"due date", r"payment due"], DATE_PAT) \
        or pick_nearby(joined, ["splatnost", "due"], DATE_PAT)
    duzp = _find_label_value(lines, [r"duzp", r"tax point", r"date of taxable"], DATE_PAT) \
        or pick_nearby(joined, ["duzp", "tax point"], DATE_PAT)

    vyst = normalize_date(vyst)
    splat = normalize_date(splat)
    duzp = normalize_date(duzp)

    # Amounts (try with labels)
    castka_s = _find_label_value(lines, [r"celkem k \w*uhra", r"celkem", r"total", r"amount due"], AMOUNT_PAT)
    bez_dph = _find_label_value(lines, [r"bez dph", r"základ daně", r"zaklad dane", r"subtotal"], AMOUNT_PAT)
    dph = _find_label_value(lines, [r"\bdph\b", r"\bvat\b"], AMOUNT_PAT)

    # Generic fallbacks – pick biggest as total, etc.
    if not (castka_s and bez_dph and dph):
        amounts = [a for a in re.findall(AMOUNT_PAT, joined) if re.search(r"\d", a)]
        amounts_parsed = [parse_amount(a) for a in amounts]
        if amounts_parsed:
            a_sorted = sorted([x for x in amounts_parsed if x is not None])
            if a_sorted:
                # assume max is total with VAT
                castka_s = castka_s or f"{a_sorted[-1]:.2f}"
                # try to detect VAT rate and compute fallback
                # keep as strings, will be parsed downstream
        # if we have two numbers, try split by VAT ~21%
        # (left as simple heuristic)

    curr = detect_currency(joined)

    # Supplier block (very heuristic)
    supplier_block = pick_nearby(joined, ["dodavatel", "supplier", "prodávající", "seller"], r".{0,200}")
    supplier = {"nazev": None, "ico": None, "dic": None, "adresa": None}
    if supplier_block:
        # IČO (8 digits)
        ico = _find_any(r"\bIČ[O0o]?\s*[: ]*\b(\d{8})\b", supplier_block) or _find_any(r"\b(\d{8})\b", supplier_block)
        # DIČ (CZ + digits) or EU
        dic = _find_any(r"\bD[IÍ]Č\s*[: ]*\b([A-Z]{2}[A-Z0-9]{8,12})\b", supplier_block) \
            or _find_any(r"\b(CZ\d{8,10})\b", supplier_block)
        # Name/address: take first 2 lines as name+address
        bl = supplier_block.strip().splitlines()
        maybe_name = bl[0].strip() if bl else None
        maybe_addr = bl[1].strip() if len(bl) > 1 else None
        supplier = {
            "nazev": maybe_name,
            "ico": ico if isinstance(ico, str) else None,
            "dic": dic if isinstance(dic, str) else None,
            "adresa": maybe_addr
        }

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
        "confidence": 0.55  # heuristic baseline
    }
    return result

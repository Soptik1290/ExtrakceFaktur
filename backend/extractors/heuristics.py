import re
from typing import List, Optional, Tuple
from .utils import normalize_date, parse_amount, first, pick_nearby, detect_currency

# Richer patterns
DATE_PAT = r"(?:\b\d{1,2}[.\-/ ]\d{1,2}[.\-/ ]\d{2,4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b)"
AMOUNT_PAT = r"(?:\d{1,3}(?:[ \u00A0]\d{3})*(?:[,.]\d{2})|\d+(?:[,.]\d{2})?)"
VS_PAT = r"\b\d{6,12}\b"
ICO_PAT = r"\b(?:IČO|ICO)[:\s]*([0-9]{8})\b"
DIC_PAT = r"\b(?:DIČ|DIC|VAT)[:\s]*([A-Z]{2}[A-Z0-9]{8,12})\b|\b(CZ[0-9]{8,10})\b"

LABELS = {
    "vs": [r"\bvariab\w*\s*symbol\b", r"\bVS\b", r"\bvariable\s*symbol\b"],
    "vystaveni": [r"datum\s*vyst", r"\bvystaven[oa]?\b", r"\bissue\b"],
    "splatnost": [r"\bsplatnost\b", r"\bdue date\b", r"\bpayment due\b"],
    "duzp": [r"\bduzp\b", r"date of taxable", r"tax point"],
    "subtotal": [r"bez dph", r"základ daně", r"zaklad dane", r"subtotal", r"base"],
    "vat": [r"\bdph\b", r"\bvat\b"],
    "total": [r"celkem k \w*uhra", r"\bcelkem\b", r"grand total", r"amount due", r"total\b"],
    "supplier": [r"dodavatel", r"supplier", r"prodávající", r"seller"]
}

def _find_near(lines: List[str], label_patterns: List[str], value_regex: str, max_dist: int = 3) -> Optional[str]:
    label_re = re.compile("|".join(label_patterns), re.I)
    val_re = re.compile(value_regex)
    for i, line in enumerate(lines):
        if label_re.search(line):
            window = "\n".join(lines[max(0, i - max_dist): i + max_dist + 1])
            m = val_re.search(window)
            if m:
                return m.group(1) if m.groups() else m.group(0)
    return None

def _find_global(regex: str, text: str) -> Optional[str]:
    m = re.search(regex, text, re.I | re.M)
    return (m.group(1) if m and m.groups() else (m.group(0) if m else None))

def _clean_lines(text: str) -> List[str]:
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]

def _score_date(d: Optional[str]) -> int:
    return 2 if d else 0

def _score_amounts(b, v, t) -> int:
    s = 0
    for x in (b, v, t):
        s += 1 if x else 0
    # bonus if sum check passes
    try:
        if b is not None and v is not None and t is not None:
            b = float(str(b).replace(",", "."))
            v = float(str(v).replace(",", "."))
            t = float(str(t).replace(",", "."))
            if abs((b + v) - t) <= 0.03:
                s += 2
    except Exception:
        pass
    return s

def extract_fields_heuristic(text: str) -> dict:
    # Prepare text & lines
    lines = _clean_lines(text)
    joined = "\n".join(lines)

    # --- Variabilní symbol ---
    vs = _find_near(lines, LABELS["vs"], VS_PAT, 3)
    if not vs:
        # prefer numbers near words like "platba", "faktura", "VS"
        vs = pick_nearby(joined, ["VS", "variabil", "variable symbol"], VS_PAT, window=200) or _find_global(VS_PAT, joined)

    # --- Dates ---
    vyst = _find_near(lines, LABELS["vystaveni"], DATE_PAT, 3) or pick_nearby(joined, ["vyst", "issue"], DATE_PAT)
    splat = _find_near(lines, LABELS["splatnost"], DATE_PAT, 3) or pick_nearby(joined, ["splatnost", "due"], DATE_PAT)
    duzp  = _find_near(lines, LABELS["duzp"], DATE_PAT, 3) or pick_nearby(joined, ["duzp", "tax point"], DATE_PAT)

    vyst = normalize_date(vyst)
    splat = normalize_date(splat)
    duzp = normalize_date(duzp)

    # --- Amounts ---
    castka_s = _find_near(lines, LABELS["total"], AMOUNT_PAT, 3)
    bez_dph  = _find_near(lines, LABELS["subtotal"], AMOUNT_PAT, 3)
    dph      = _find_near(lines, LABELS["vat"], AMOUNT_PAT, 3)

    # global fallback: pick candidates and reconcile
    if not (castka_s and bez_dph and dph):
        amounts_all = [m.group(0) for m in re.finditer(AMOUNT_PAT, joined)]
        parsed = [parse_amount(x) for x in amounts_all]
        # choose top-3 distinct amounts
        uniq = sorted({a for a in parsed if a is not None})
        if uniq:
            # assume max is total
            t = uniq[-1]
            castka_s = castka_s or f"{t:.2f}"
            # try to infer VAT as difference to nearest plausible 15–23% rate
            if bez_dph is None and dph is None and len(uniq) >= 2:
                # guess base closest to t / 1.21 or t / 1.15
                candidates = [round(t/1.21, 2), round(t/1.15, 2)]
                # pick value from uniq nearest to any candidate
                best = min(uniq[:-1], key=lambda x: min(abs(x - c) for c in candidates)) if len(uniq) > 1 else None
                if best:
                    bez_dph = f"{best:.2f}"
                    dph_val = t - best
                    dph = f"{dph_val:.2f}"

    curr = detect_currency(joined)

    # --- Supplier ---
    # try to find ICO & DIC anywhere
    ico = _find_global(ICO_PAT, joined)
    dic = _find_global(DIC_PAT, joined)
    # company name: heuristics for s.r.o./a.s.
    name = None
    mname = re.search(r"\b([A-ZÁČĎÉĚÍĽĹŇÓŘŠŤÚŮÝŽ][\w\.\-& ]{2,}?(?:s\.r\.o\.|a\.s\.))\b", joined, re.I)
    if mname:
        name = mname.group(1).strip()
    # address: line following the name or lines around IČO
    adresa = None
    if name:
        # find the line with name and take the next line as address (best-effort)
        for i, ln in enumerate(lines):
            if name.lower() in ln.lower():
                if i+1 < len(lines):
                    adresa = lines[i+1]
                break

    supplier = {"nazev": name, "ico": ico, "dic": dic, "adresa": adresa}

    # Normalize amounts to floats where possible
    bez_dph_n = parse_amount(bez_dph) if bez_dph is not None else None
    dph_n = parse_amount(dph) if dph is not None else None
    castka_s_n = parse_amount(castka_s) if castka_s is not None else None

    # Confidence scoring
    conf = 0.4
    conf += 0.15 if vs else 0.0
    conf += 0.1 * (_score_date(vyst) + _score_date(splat) + _score_date(duzp))
    conf += 0.15 if (bez_dph_n is not None and dph_n is not None and castka_s_n is not None) else 0.05 if castka_s_n is not None else 0.0
    conf = min(0.95, conf)

    return {
        "variabilni_symbol": vs,
        "datum_vystaveni": vyst,
        "datum_splatnosti": splat,
        "duzp": duzp,
        "castka_bez_dph": bez_dph_n if bez_dph_n is not None else bez_dph,
        "dph": dph_n if dph_n is not None else dph,
        "castka_s_dph": castka_s_n if castka_s_n is not None else castka_s,
        "dodavatel": supplier,
        "mena": curr,
        "confidence": round(conf, 2)
    }

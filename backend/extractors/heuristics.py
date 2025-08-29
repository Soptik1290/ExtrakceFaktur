
import re
from .utils import normalize_date, parse_amount, first, pick_nearby, detect_currency

DATE_PAT = r"(?:\b\d{1,2}[.\-/ ]\d{1,2}[.\-/ ]\d{2,4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b)"
# Clean regex pattern for amounts - handles Czech format with spaces as thousands separators
AMOUNT_PAT_STRICT = r"\b\d{1,3}(?:[ \u00A0]\d{3})*(?:[,.]\d{2})\b|\b\d+(?:[ \u00A0]\d{3})*(?:[,.]\d{2})\b|\b\d+[,.]\d{2}\b|\b\d{1,3}(?:[ \u00A0]\d{3})+\b|\b\d{4,6}\b|\b\d{1,3}[ \u00A0]\d{3}\b|\b\d{1,3}[ \u00A0]\d{3},\d{2}\b"
CURRENCY_TOKEN = r"(?:CZK|Kč|EUR|€|USD|\$|GBP|£|PLN|zł|HUF|Ft|CHF|SEK|NOK|DKK|JPY|¥|CNY|AUD|CAD)"

def _find_label_value(lines, label_keywords, value_regex, max_dist=2):
    label_re = re.compile("|".join(label_keywords), re.I)
    val_re = re.compile(value_regex)
    candidates = []
    for i, line in enumerate(lines):
        if label_re.search(line):
            window = "\n".join(lines[max(0, i - max_dist): i + max_dist + 1])
            for m in val_re.finditer(window):
                candidates.append(m.group(1) if m.groups() else m.group(0))
    
    # If no candidates found with default distance, try with larger distance for amounts
    if not candidates and any("castka" in kw or "total" in kw or "amount" in kw for kw in label_keywords):
        for i, line in enumerate(lines):
            if label_re.search(line):
                window = "\n".join(lines[max(0, i - 50): i + 51])  # Large window for amounts
                for m in val_re.finditer(window):
                    candidates.append(m.group(1) if m.groups() else m.group(0))
    
    return first(candidates)

def _find_any(regex, text):
    m = re.search(regex, text, re.I | re.M)
    return m.group(1) if (m and m.groups()) else (m.group(0) if m else None)

def _clean_lines(text: str):
    return [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]

def _detect_vs(text: str, lines):
    vs = _find_label_value(lines, [r"\bvariab\w* symbol\b", r"\bVS\b", r"variable symbol", r"variabilní symbol", r"variabilni symbol"], r"\b(\d{6,12})\b", 3)
    if vs:
        return re.sub(r"\D", "", vs)
    vs = _find_any(r"\bVS[:\s]+(\d{6,12})\b", "\n".join(lines))
    if vs:
        return vs
    candidates = []
    j = "\n".join(lines)
    for m in re.finditer(r"\b(\d{8,10})\b(?!\s*/)", j):
        left = j[max(0, m.start()-20):m.start()].lower()
        if ("ucet" in left or "účet" in left or "account" in left or "učet" in left or "úcet" in left):
            continue
        candidates.append(m.group(1))
    return first(candidates)

def _extract_supplier(lines):
    """
    Try to extract supplier (dodavatel) block heuristically from lines.
    Strategy:
    - Find all occurrences of IČO/DIČ and build small windows around them
    - Prefer a window explicitly labelled 'dodavatel' and avoid 'odběratel'
    - Otherwise, prefer the window that contains DIČ starting with 'CZ'
    - From the chosen window, infer name (a line before), IČO, DIČ and an address line
    """
    ico_pat = re.compile(r"I[ČC]O\s*[:#-]?\s*(\d{8})", re.I)
    dic_pat = re.compile(r"DI[ČC]\s*[:#-]?\s*([A-Z]{2}\s?\d{8,12}|\d{8,12})", re.I)
    psc_pat = re.compile(r"\b\d{3}\s?\d{2}\b")  # Czech ZIP

    candidates = []
    for idx, line in enumerate(lines):
        has_ico = bool(ico_pat.search(line))
        has_dic = bool(dic_pat.search(line))
        if not (has_ico or has_dic):
            continue
        start = max(0, idx - 4)
        end = min(len(lines), idx + 5)
        block = lines[start:end]
        block_text = "\n".join(block)
        label_score = 0
        if re.search(r"dodavatel", block_text, re.I):
            label_score += 3
        if re.search(r"odb[ěe]ratel", block_text, re.I):
            label_score -= 3
        if re.search(r"\bCZ\s?\d{8,12}\b", block_text):
            label_score += 2

        ico_m = ico_pat.search(block_text)
        dic_m = dic_pat.search(block_text)
        ico = ico_m.group(1) if ico_m else None
        dic = dic_m.group(1).replace(" ", "") if dic_m else None

        # Guess name as the nearest meaningful line above that is not a label
        name = None
        for up in range(idx - 1, start - 1, -1):
            ln = lines[up].strip()
            if re.search(r"I[ČC]O|DI[ČC]|odb[ěe]ratel|dodavatel|IČO|DIČ", ln, re.I):
                continue
            if len(re.sub(r"[^A-Za-zÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěíňóřšťúůýž.& ]", "", ln)) >= 3:
                name = ln
                break

        # Guess address as a line in the block that contains street/ZIP/city hints
        address = None
        for ln in block:
            if psc_pat.search(ln) or re.search(r"\d+\s*[,/]*\s*[A-Za-z]", ln):
                if not re.search(r"I[ČC]O|DI[ČC]", ln, re.I):
                    address = ln
                    break

        candidates.append((label_score, start, end, {"nazev": name, "ico": ico, "dic": dic, "adresa": address}))

    if not candidates:
        return {"nazev": None, "ico": None, "dic": None, "adresa": None}

    # Pick the best-scoring candidate
    best = sorted(candidates, key=lambda t: t[0], reverse=True)[0][3]
    return best

def _amounts_from_text(text: str):
    raw = re.findall(AMOUNT_PAT_STRICT, text)
    parsed = []
    for a in raw:
        val = parse_amount(a)
        if val is None:
            continue
        if val > 1e7:
            continue
        
        # Score the amount based on how likely it is to be a total
        score = 0
        original_text = a
        
        # Higher score for amounts with decimal places (more likely to be prices)
        if "." in str(val):
            score += 10
        
        # Higher score for larger amounts (more likely to be totals)
        if val > 1000:
            score += 5
        
        # Higher score for amounts that look like Czech currency format
        if re.search(r"\d{1,3}(?: \d{3})", original_text):
            score += 20
        
        # Even higher score for amounts that look like "44 413" (exact pattern)
        if re.match(r"^\d{1,3} \d{3}$", original_text):
            score += 30
        
        # Highest score for amounts that look like "44 413,00" (exact pattern with decimal)
        if re.match(r"^\d{1,3} \d{3},\d{2}$", original_text):
            score += 100
        
        # Lower score for very small amounts (likely line items)
        if val < 100:
            score -= 5
        
        parsed.append((val, score, original_text))
    
    # Sort by score (descending), then by value (descending)
    parsed.sort(key=lambda x: (x[1], x[0]), reverse=True)
    return [val for val, _, _ in parsed]

def _currency_near_amount(lines):
    joined = "\n".join(lines)
    # Enhanced Czech keywords with proper diacritics
    for lab in [r"amount due", r"grand total", r"\btotal\b", r"celkem", r"k úhradě", r"k uhrade", r"subtotal", r"bez dph", r"dph", r"celková částka", r"celkova castka", r"celková castka", r"celkova částka"]:
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

    # 1) Try direct label→value capture on the whole text (robust to table layout)
    def _date_after(label_regex: str):
        m = re.search(label_regex + r"[\s:.]*?(" + DATE_PAT + r")", joined, re.I)
        return m.group(1) if m else None

    vyst = _date_after(r"datum\s+vystav(?:en[íi]|eni)")
    splat = _date_after(r"datum\s+splatnosti")
    duzp = _date_after(r"datum\s+zdanitel(?:n[ée]ho|neho)\s+pln[ěe]n[íi]")

    # 2) If still missing, use line-window search and neighborhood pickers
    if not vyst:
        vyst = _find_label_value(lines, [r"datum vyst", r"vystaven", r"issue", r"datum vystavení", r"datum vystaveni"], DATE_PAT, 3) \
            or pick_nearby(joined, ["vyst", "issue", "vystavení", "vystaveni"], DATE_PAT)
    if not splat:
        splat = _find_label_value(lines, [r"splatnost", r"due date", r"payment due", r"datum splatnosti", r"datum splatnosti"], DATE_PAT, 3) \
            or pick_nearby(joined, ["splatnost", "due", "splatnost"], DATE_PAT)
    if not duzp:
        duzp = _find_label_value(lines, [
                r"duzp", r"tax point", r"date of taxable",
                r"datum uskutecnění zdanitelného plnění", r"datum uskutecneni zdanitelneho plneni",
                r"zdanitelného plnění", r"zdanitelneho plneni", r"zdan\.\s*pln",
                r"datum zdan\.?\s*pln", r"datum zdanitelneho plneni", r"datum zdanění plnění", r"datum zdaneni plneni"
            ], DATE_PAT, 3) \
            or pick_nearby(joined, ["duzp", r"tax point", "uskutecnění", "uskutecneni", "zdan", "plnění", "plneni"], DATE_PAT)

    vyst = normalize_date(vyst); splat = normalize_date(splat); duzp = normalize_date(duzp)

    # Enhanced Czech keywords with proper diacritics and variations
    castka_s = _find_label_value(lines, [
        r"celkem k \w*uhra", r"celkem k uhrade", r"celkem k úhradě",
        r"celkem", r"total", r"amount due", r"grand total", 
        r"k úhradě", r"k uhrade", r"celková částka", r"celkova castka",
        r"celková castka", r"celkova částka", r"celkem k úhradě", r"celkem k uhrade",
        r"celkem k úhradě", r"celkem k uhrade", r"celkem k úhradě", r"celkem k uhrade"
    ], AMOUNT_PAT_STRICT, 3)
    
    bez_dph = _find_label_value(lines, [
        r"bez dph", r"základ daně", r"zaklad dane", r"subtotal", 
        r"základ", r"zaklad", r"základ daně", r"zaklad dane", r"základ daně", r"zaklad dane",
        r"základ daně", r"zaklad dane", r"základ daně", r"zaklad dane"
    ], AMOUNT_PAT_STRICT, 3)
    
    dph = _find_label_value(lines, [
        r"\bdph\b", r"\bvat\b", r"daň", r"dan", r"dph", r"vat", r"daň z přidané hodnoty", r"dan z pridane hodnoty",
        r"daň z přidané hodnoty", r"dan z pridane hodnoty", r"daň z přidané hodnoty", r"dan z pridane hodnoty"
    ], AMOUNT_PAT_STRICT, 3)

    if not (castka_s and bez_dph and dph):
        nums = _amounts_from_text(joined)
        if nums:
            # Use the highest scored amount as the main amount
            castka_s = castka_s or f"{nums[0]:.2f}"
            
            # If we have multiple amounts, try to identify which is which
            if len(nums) >= 2:
                # The highest amount is likely the total
                if not castka_s:
                    castka_s = f"{nums[0]:.2f}"
                
                # Look for amounts that could be DPH (usually around 21% of total)
                if not dph and castka_s:
                    total = parse_amount(castka_s)
                    if total:
                        for num in nums[1:]:
                            # Check if this could be DPH (around 21% of total)
                            if 0.15 <= num/total <= 0.25:
                                dph = f"{num:.2f}"
                                break
                
                # Look for amounts that could be bez DPH
                if not bez_dph and castka_s and dph:
                    total = parse_amount(castka_s)
                    dph_val = parse_amount(dph)
                    if total and dph_val:
                        bez_dph = f"{(total - dph_val):.2f}"
        
        # Fallback calculations if still missing
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

    # --- Payment info ---
    platba = _find_label_value(lines,
        [r"zp[uů]sob [uú]hrady", r"zp[uů]sob platby", r"payment method", r"payment", r"zpusob uhrady", r"zpusob platby", r"zpusob úhrady", r"zpusob úhrady", r"způsob úhrady", r"způsob platby", r"způsob uhrady", r"způsob platby"],
        r"[:\s]*([A-Za-zÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěíňóřšťúůýž /+\-]+)", 2)
    banka = _find_label_value(lines,
        [r"n[aá]zev banky", r"banka", r"bank name", r"nazev banky", r"název banky", r"název banky", r"nazev banky", r"banka příjemce", r"banka prijemce"],
        r"[:\s]*([A-Za-zÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěíňóřšťúůýž0-9 .,'\-_/]+)", 2)
    ucet = _find_label_value(lines,
        [r"\b(?:č[iy]slo\s*[\w]*\s*ú[čc]tu|cislo uctu|account number|iban)\b", r"cislo účtu", r"cislo uctu", r"číslo účtu", r"číslo uctu", r"čísla účtu", r"cisla uctu", r"čísla účtu", r"cisla uctu"],
        r"[:\s]*([0-9\- ]{1,20}/[0-9]{3,6}|[A-Z]{2}[0-9A-Z ]{12,34})", 3)

    supplier = _extract_supplier(lines)

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
        "platba_zpusob": platba.strip() if isinstance(platba, str) else platba,
        "banka_prijemce": banka.strip() if isinstance(banka, str) else banka,
        "ucet_prijemce": ucet.strip() if isinstance(ucet, str) else ucet,
        "confidence": 0.62
    }
    return result

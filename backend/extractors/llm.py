
import os, json, re
from .utils import normalize_date, parse_amount, fix_czech_chars, pick_nearby
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

def llm_available() -> bool:
    return OpenAI is not None and bool(os.getenv("OPENAI_API_KEY"))

def _prompt(text: str) -> str:
    return f"""
Jsi extrakční AI pro faktury (CZ/EN). Vrať POUZE JSON dle schématu:
{{
  "variabilni_symbol": "string|null",
  "datum_vystaveni": "YYYY-MM-DD|null",
  "datum_splatnosti": "YYYY-MM-DD|null",
  "duzp": "YYYY-MM-DD|null",
  "castka_bez_dph": "number|string|null",
  "dph": "number|string|null",
  "castka_s_dph": "number|string|null",
  "dodavatel": {{
    "nazev": "string|null", "ico": "string|null", "dic": "string|null", "adresa": "string|null"
  }},
  "mena": "string|null",
  "platba_zpusob": "string|null",
  "banka_prijemce": "string|null",
  "ucet_prijemce": "string|null",
  "confidence": 0.0
}}

Pravidla:
- Datumy normalizuj na YYYY-MM-DD.
- Částky vracej jako čísla (pokud lze), jinak string.
- Číslo účtu může být ve formátu '123-123456789/0100', '2171532/0800', IBAN nebo BIC – vrať jak je na faktuře.
- Pokud něco chybí, dej null a adekvátně sniž confidence.
- ZACHOVEJ českou diakritiku (ěščřžýáíéůúňďť) v názvech a adresách.
- Pro české faktury: měna "Kč" = "CZK".
- Částky mohou být ve formátu "44 413,00" nebo "44413.00" - normalizuj na číslo.
- IČO je 8místné číslo, DIČ začíná "CZ" + 8-10 číslic.
- Variabilní symbol je obvykle číslo nebo text do 12 znaků.
- Platební metody: "peněžní převod", "bankovní převod", "hotovost", "karta" - použij přesný text z faktury.
- Částky bez DPH a s DPH musí sedět s celkovou částkou - zkontroluj matematicky.
- Adresy obsahují: ulice, číslo, PSČ, město, stát - zachovej kompletní formát.

TEXT:
-----
{text}
-----
"""

def _total_from_text_fallback(text: str):
    """
    Try to read the grand-total amount straight from the invoice text
    around common Czech/EN labels. This is used to correct occasional
    LLM off-by-a-digit mistakes (e.g. 65000 -> 165000).
    """
    if not text:
        return None
    amount_pattern = r"\b\d{1,3}(?:[ \u00A0]\d{3})*(?:[,.]\d{2})\b|\b\d{1,3}(?:[ \u00A0]\d{3})+\b"
    keywords = [
        r"k\s*[úu]hrad[ěe]", r"celkem\s*k\s*[úu]hrad[ěe]", r"celkem", r"amount due", r"grand total", r"\btotal\b", r"celkov[aá]\s*\u010d[aá]stka|celkova\s*castka"
    ]
    # 1) Try nearby-window search with a generous window
    hit = pick_nearby(text, keywords, amount_pattern, window=800)
    if hit:
        val = parse_amount(hit)
        if val is not None:
            return val
    # 2) Try direct label→amount regex over entire text
    patterns = [
        r"(?:k\s*[úu]hrad[ěe].{0,120}?)(\d{1,3}(?:[ \u00A0]\d{3})*(?:[,.]\d{2})|\d{1,3}(?:[ \u00A0]\d{3})+)",
        r"(?:celkem\s*k\s*[úu]hrad[ěe].{0,120}?)(\d{1,3}(?:[ \u00A0]\d{3})*(?:[,.]\d{2})|\d{1,3}(?:[ \u00A0]\d{3})+)",
        r"(?:celkem[^\n\r]{0,120}?)(\d{1,3}(?:[ \u00A0]\d{3})*(?:[,.]\d{2})|\d{1,3}(?:[ \u00A0]\d{3})+)"
    ]
    candidates = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            candidates.append(m.group(1))
    if candidates:
        numbers = [parse_amount(c) for c in candidates if parse_amount(c) is not None]
        if numbers:
            # Heuristic: choose the largest candidate (grand totals are usually max)
            return max(numbers)
    return None

def extract_fields_llm(text: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise information extraction assistant."},
            {"role": "user", "content": _prompt(text)},
        ],
        temperature=0.2,
    )
    raw = resp.choices[0].message.content.strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if m: raw = m.group(0)
    data = json.loads(raw)

    for k in ["datum_vystaveni","datum_splatnosti","duzp"]:
        data[k] = normalize_date(data.get(k))
    def _num(v):
        if v is None: return None
        if isinstance(v, (int,float)): return float(v)
        return parse_amount(str(v))
    for k in ["castka_bez_dph","dph","castka_s_dph"]:
        data[k] = _num(data.get(k))

    # Ensure dodavatel is a dict with expected keys even if LLM returns a string/list/null
    supplier = data.get("dodavatel")
    if not isinstance(supplier, dict):
        supplier = {"nazev": supplier if isinstance(supplier, str) else None,
                    "ico": None, "dic": None, "adresa": None}
    else:
        # Coerce unexpected nested structures to strings where sensible
        for key in ["nazev", "ico", "dic", "adresa"]:
            val = supplier.get(key)
            if isinstance(val, (list, dict)):
                supplier[key] = json.dumps(val, ensure_ascii=False)
    data["dodavatel"] = {
        "nazev": fix_czech_chars(supplier.get("nazev")),
        "ico": supplier.get("ico"),
        "dic": supplier.get("dic"),
        "adresa": fix_czech_chars(supplier.get("adresa")),
    }
    
    # Normalize currency - convert "Kč" to "CZK"
    if data.get("mena") == "Kč":
        data["mena"] = "CZK"
    
    # Normalize amounts - ensure they are numbers
    for k in ["castka_bez_dph","dph","castka_s_dph"]:
        if data.get(k) is not None:
            if isinstance(data[k], str):
                # Try to parse amount from string
                parsed = parse_amount(data[k])
                if parsed is not None:
                    data[k] = parsed
    
    # Fix Czech characters in text fields
    for k in ["platba_zpusob", "banka_prijemce"]:
        if data.get(k):
            data[k] = fix_czech_chars(data[k])
    
    for k in ["mena","platba_zpusob","banka_prijemce","ucet_prijemce"]:
        data.setdefault(k, None)
    data.setdefault("confidence", 0.75)
    data.setdefault("variabilni_symbol", None)

    # Cross-check the total against a regex-based read from the raw text.
    # If they differ notably (> 1 CZK), trust the direct text read.
    try:
        text_total = _total_from_text_fallback(text)
        if text_total is not None:
            cur_total = data.get("castka_s_dph")
            if cur_total is None or abs(float(cur_total) - float(text_total)) > 1.0:
                fixed_total = float(text_total)
                data["castka_s_dph"] = fixed_total
                # If VAT is zero or missing, mirror total into bez DPH
                if data.get("dph") in [None, 0, 0.0]:
                    data["dph"] = 0.0
                    data["castka_bez_dph"] = fixed_total
    except Exception:
        # Never let a fallback correction break extraction
        pass
    return data


import os, json, re
from .utils import normalize_date, parse_amount, fix_czech_chars
from .heuristics import extract_fields_heuristic
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

DATE_PAT = r"(?:\b\d{1,2}[.\-/ ]\d{1,2}[.\-/ ]\d{2,4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b)"

def _dates_from_text(text: str) -> dict:
    t = re.sub(r"\s+", " ", text or "")
    # Direct label → value patterns, tolerant to accents
    def grab(pattern: str):
        m = re.search(pattern + r"\s*[:\-]?\s*(" + DATE_PAT + r")", t, re.I)
        return m.group(1) if m else None
    vyst = grab(r"datum\s+vystav(?:en[íi]|eni)") or grab(r"vystaven[íi]")
    splat = grab(r"datum\s+splatnosti") or grab(r"splatnost")
    duzp = grab(r"datum\s+zdanitel(?:n[ée]ho|neho)\s+pln(?:[ěe]n[íi]|eni)") or grab(r"duzp")
    return {
        "datum_vystaveni": normalize_date(vyst),
        "datum_splatnosti": normalize_date(splat),
        "duzp": normalize_date(duzp),
    }

def _supplier_looks_mixed(supplier: dict) -> bool:
    if not isinstance(supplier, dict):
        return False
    name = (supplier.get("nazev") or "").lower()
    addr = (supplier.get("adresa") or "").lower()
    if any(tok in name for tok in ["odb", "oberatel", "oaberatel"]):
        return True
    # two different cities/streets hints → likely concatenated address
    if ("jungmannova" in addr and "masarykova" in addr) or ("praha" in addr and "brno" in addr):
        return True
    return False

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

    # Backfill missing dates from OCR text (does not affect other fields)
    dates_fb = _dates_from_text(text)
    for k in ["datum_vystaveni", "datum_splatnosti", "duzp"]:
        if data.get(k) is None and dates_fb.get(k) is not None:
            data[k] = dates_fb[k]

    # If supplier looks mixed/incorrect, prefer heuristic supplier block
    try:
        if _supplier_looks_mixed(data.get("dodavatel")):
            h = extract_fields_heuristic(text)
            hs = (h or {}).get("dodavatel") or {}
            if any(hs.get(k) for k in ["nazev","ico","dic","adresa"]):
                data["dodavatel"] = {
                    "nazev": fix_czech_chars(hs.get("nazev")),
                    "ico": hs.get("ico"),
                    "dic": hs.get("dic"),
                    "adresa": fix_czech_chars(hs.get("adresa")),
                }
                data["confidence"] = max(0.7, float(data.get("confidence") or 0.75) - 0.02)
    except Exception:
        pass
    return data



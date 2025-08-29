
import os, json, re
from .utils import normalize_date, parse_amount, fix_czech_chars
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

def llm_available() -> bool:
    return OpenAI is not None and bool(os.getenv("OPENAI_API_KEY"))

def _prompt(text: str) -> str:
    return f"""
Jsi extrakční AI pro české faktury. Vrať POUZE JSON dle schématu:
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

DŮLEŽITÁ PRAVIDLA PRO ČESKÉ FAKTURY:
1. DATUMY - HLEDEJ TYTO POLÍČKA:
   - "Datum vystavení" nebo "Datum vydání" = datum_vystaveni
   - "Datum splatnosti" nebo "Datum úhrady" = datum_splatnosti  
   - "Datum zdanitelného plnění" nebo "DUZP" = duzp
   - Datumy jsou ve formátu DD.MM.YYYY - převeď na YYYY-MM-DD

2. ADRESY - ROZLIŠUJ DODAVATELE A ODBĚRATELE:
   - Dodavatel (vystavitel faktury) = horní část faktury
   - Odběratel (příjemce faktury) = spodní část faktury
   - Adresa dodavatele = pole "dodavatel.adresa"
   - NIKDY nemíchej adresy dodavatele a odběratele

3. NÁZEV DODAVATELE:
   - Pouze název společnosti, která vystavuje fakturu
   - NIKDY nemíchej s názvem odběratele

4. FORMÁT DAT:
   - České datumy: 21.4.2023 → 2023-04-21
   - České datumy: 5.5.2023 → 2023-05-05
   - Pokud je měsíc jednociferný, doplň 0

5. DALŠÍ PRAVIDLA:
   - Částky normalizuj na čísla (44 413,00 → 44413.00)
   - Měna "Kč" = "CZK"
   - IČO je 8místné číslo
   - DIČ začíná "CZ" + 8-10 číslic
   - Variabilní symbol je obvykle číslo faktury
   - Platební metody: "peněžní převod", "bankovní převod", "hotovost"
   - Adresy obsahují: ulice, číslo, PSČ, město, stát

TEXT:
-----
{text}
-----
"""

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
    return data


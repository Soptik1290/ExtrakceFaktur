
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

def extract_fields_llm(text: str) -> dict:
    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5-main")

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
    if m:
        raw = m.group(0)
    data = json.loads(raw)

    for k in ["datum_vystaveni", "datum_splatnosti", "duzp"]:
        data[k] = normalize_date(data.get(k))

    def _num(v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        return parse_amount(str(v))

    for k in ["castka_bez_dph", "dph", "castka_s_dph"]:
        data[k] = _num(data.get(k))

    # Ensure dodavatel is dict
    supplier = data.get("dodavatel")
    if not isinstance(supplier, dict):
        supplier = {
            "nazev": supplier if isinstance(supplier, str) else None,
            "ico": None, "dic": None, "adresa": None,
        }
    else:
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

    # Normalize currency
    if data.get("mena") == "Kč":
        data["mena"] = "CZK"

    # Normalize amounts
    for k in ["castka_bez_dph", "dph", "castka_s_dph"]:
        if data.get(k) is not None and isinstance(data[k], str):
            parsed = parse_amount(data[k])
            if parsed is not None:
                data[k] = parsed

    # Fix Czech chars
    for k in ["platba_zpusob", "banka_prijemce"]:
        if data.get(k):
            data[k] = fix_czech_chars(data[k])

    for k in ["mena", "platba_zpusob", "banka_prijemce", "ucet_prijemce"]:
        data.setdefault(k, None)

    data.setdefault("confidence", 0.75)
    data.setdefault("variabilni_symbol", None)

    return data


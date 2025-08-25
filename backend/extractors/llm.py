import os, json, re
from typing import Optional
from .utils import normalize_date, parse_amount
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

SCHEMA = {
  "variabilni_symbol": "string|null",
  "datum_vystaveni": "YYYY-MM-DD|null",
  "datum_splatnosti": "YYYY-MM-DD|null",
  "duzp": "YYYY-MM-DD|null",
  "castka_bez_dph": "number|string|null",
  "dph": "number|string|null",
  "castka_s_dph": "number|string|null",
  "dodavatel": {
    "nazev": "string|null",
    "ico": "string|null",
    "dic": "string|null",
    "adresa": "string|null"
  },
  "mena": "string|null",
  "confidence": "0..1"
}

def llm_available() -> bool:
    return OpenAI is not None and bool(os.getenv("OPENAI_API_KEY"))

def _prompt(text: str) -> str:
    return f"""
Jsi extrakční AI pro faktury (CZ/EN). Z textu faktury vytěž následující pole.
Dodrž TENTO JSON formát (žádný komentář, žádný text mimo JSON, pouze platný JSON):

{{
  "variabilni_symbol": "string|null",
  "datum_vystaveni": "YYYY-MM-DD|null",
  "datum_splatnosti": "YYYY-MM-DD|null",
  "duzp": "YYYY-MM-DD|null",
  "castka_bez_dph": "number|string|null",
  "dph": "number|string|null",
  "castka_s_dph": "number|string|null",
  "dodavatel": {{
    "nazev": "string|null",
    "ico": "string|null",
    "dic": "string|null",
    "adresa": "string|null"
  }},
  "mena": "string|null",
  "confidence": 0.0
}}

Pokyny:
- Použij ISO datumy (YYYY-MM-DD), jinak null.
- Částky normalizuj na čísla s desetinnou tečkou (např. 1234.50). Pokud nejde, vrať string.
- DIČ může být CZ nebo jiné EU (např. CZ12345678, DE123456789).
- Pokud nejsi jistý, nastav null a sniž confidence.
- Měnu detekuj (CZK/Kč/EUR/€).

TEXT FAKTURY:
-----
{text}
-----
"""

def extract_fields_llm(text: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Using Chat Completions to keep SDK compatibility
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise information extraction assistant."},
            {"role": "user", "content": _prompt(text)},
        ],
        temperature=0.2,
    )
    raw = resp.choices[0].message.content.strip()

    # Try to locate JSON
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        raw = m.group(0)
    data = json.loads(raw)

    # Optional normalization
    for k in ["datum_vystaveni","datum_splatnosti","duzp"]:
        data[k] = normalize_date(data.get(k))

    def _numfix(v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        return parse_amount(str(v))

    for k in ["castka_bez_dph", "dph", "castka_s_dph"]:
        data[k] = _numfix(data.get(k))

    # ensure keys exist
    data.setdefault("dodavatel", {"nazev": None, "ico": None, "dic": None, "adresa": None})
    data.setdefault("mena", None)
    data.setdefault("variabilni_symbol", None)
    data.setdefault("confidence", 0.75)

    return data

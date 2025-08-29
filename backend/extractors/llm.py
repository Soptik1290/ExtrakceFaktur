
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
Jsi expert na extrakci dat z faktur. Specializuješ se na české faktury, ale zvládneš i zahraniční. Vrať POUZE JSON dle schématu:
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

PRAVIDLA EXTRAKCE:
1. DATUMY - hledej tyto označení:
   - Datum vystavení: "Datum vystavení", "Vystaven", "Date issued", "Invoice date"
   - Datum splatnosti: "Datum splatnosti", "Splatnost", "Due date", "Payment due"
   - DUZP: "Datum zdanitelného plnění", "DUZP", "Tax point date"
   - Formáty: DD.MM.YYYY, DD.M.YYYY, MM/DD/YYYY → převeď na YYYY-MM-DD
   - Příklad: "21.4.2023" → "2023-04-21"

2. DODAVATEL vs ODBĚRATEL - POZOR:
   - DODAVATEL = vystavitel faktury (obvykle vlevo nahoře nebo v hlavičce)
   - ODBĚRATEL = příjemce faktury (obvykle vpravo nahoře)
   - Extrahuj POUZE údaje dodavatele do pole "dodavatel"
   - Nikdy nemiš dodavatele s odběratelem!

3. NÁZEV DODAVATELE:
   - Přesný název společnosti vystavivatele
   - Zachovej právní formy: "s.r.o.", "a.s.", "Ltd.", "GmbH", "Inc."
   - Zachovaj původní jazyk a pravopis

4. DAŇOVÁ ČÍSLA:
   - IČO: obvykle 8místné číslo (české faktury)
   - DIČ: CZ + 8-10 číslic (české), nebo jiný formát (DE123, GB123, atd.)
   - Extrahuj z části DODAVATELE

5. ČÁSTKY A MĚNA:
   - Rozpoznej formáty: "1 234,56", "1,234.56", "1.234,56"
   - Normalizuj měny: "Kč"→"CZK", "€"→"EUR", "$"→"USD"
   - Pokud je DPH 0%, tak dph = 0

6. PLATEBNÍ ÚDAJE:
   - Způsob úhrady: "Forma úhrady", "Způsob úhrady", "Payment method"
   - Banka: "BANKA", "Banka", "Bank"
   - Účet: "ÚČET", "Číslo účtu", "Account", "IBAN"

7. VARIABILNÍ SYMBOL:
   - Hledej: "Variabilní symbol", "VS", "Variable symbol"
   - Obvykle číslo pro identifikaci platby

DŮLEŽITÉ: Pečlivě analyzuj strukturu faktury. Neodhaduj pozice - hledej skutečné popisky a kontextové indicie k rozlišení dodavatele od odběratele.

TEXT FAKTURY:
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


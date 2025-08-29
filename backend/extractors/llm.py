
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
Extract data from this invoice. Return ONLY valid JSON matching this exact schema:
{{
  "variabilni_symbol": "string|null",
  "datum_vystaveni": "YYYY-MM-DD|null",
  "datum_splatnosti": "YYYY-MM-DD|null",
  "duzp": "YYYY-MM-DD|null",
  "castka_bez_dph": "number|null",
  "dph": "number|null",
  "castka_s_dph": "number|null",
  "dodavatel": {{
    "nazev": "string|null", "ico": "string|null", "dic": "string|null", "adresa": "string|null"
  }},
  "mena": "string|null",
  "platba_zpusob": "string|null",
  "banka_prijemce": "string|null",
  "ucet_prijemce": "string|null",
  "confidence": 0.8
}}

EXTRACTION RULES:

1. DATES - Find these patterns:
   - Issue date: Look for "Datum vystavení", "Date issued", "Invoice date", "Ausstellungsdatum"
   - Due date: Look for "Datum splatnosti", "Due date", "Payment due", "Fälligkeitsdatum"  
   - Tax point: Look for "Datum zdanitelného plnění", "DUZP", "Tax point"
   - Convert to YYYY-MM-DD: "21.4.2023"→"2023-04-21", "04/21/2023"→"2023-04-21"

2. SUPPLIER IDENTIFICATION - CRITICAL:
   - The SUPPLIER is the company that ISSUED the invoice (invoice sender)
   - The CUSTOMER is the company that RECEIVES the invoice (invoice recipient)
   - Look for structural clues:
     * Invoice header/letterhead usually contains supplier info
     * "From:", "Seller:", "Vendor:" indicates supplier
     * "To:", "Bill to:", "Customer:", "Odběratel:" indicates customer
     * Payment details (bank account) usually belong to supplier
   - Extract ONLY supplier information for "dodavatel" field
   - NEVER mix supplier and customer data!

3. COMPANY DETAILS:
   - Extract exact company name including legal forms (s.r.o., a.s., Ltd., GmbH, Inc.)
   - Tax numbers: IČO (8-digit Czech), DIČ/VAT ID (country prefix + digits)
   - Full address of the supplier company

4. AMOUNTS:
   - Parse various formats: "1 234,56", "1,234.56", "1.234,56"
   - Convert currency: "Kč"→"CZK", "€"→"EUR", "$"→"USD"

5. PAYMENT INFO:
   - Payment method: "Forma úhrady", "Způsob úhrady", "Payment method"
   - Bank name: "BANKA", "Banka", "Bank"
   - Account: "ÚČET", "Číslo účtu", "Account", "IBAN"

6. REFERENCE NUMBERS:
   - Variable symbol: "Variabilní symbol", "VS", "Variable symbol"

IMPORTANT: 
- Carefully analyze the invoice layout and structure
- Use contextual clues, not position assumptions
- The company with bank details is usually the supplier
- Don't guess - if unsure, return null

INVOICE TEXT:
{text}
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


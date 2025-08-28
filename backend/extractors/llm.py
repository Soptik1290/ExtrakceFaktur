
import os, json, re
from .utils import normalize_date, parse_amount
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

    # Heuristic correction: prefer amount near labels like "K úhradě/Celkem/Total"
    try:
        # Diacritic-aware and flexible Czech patterns
        LABELS = [
            r"celkem\s+k\s+\w*\s*[uú]hrad[ěe]",
            r"k\s+\w*\s*[uú]hrad[ěe]",
            r"celkem",
            r"amount\s+due",
            r"grand\s+total",
            r"\btotal\b",
        ]
        AMT = r"(\d{1,3}(?:[ \u00A0\u202F]\d{3})*(?:[.,]\d{2})|\d+[.,]\d{2})"
        joined = text or ""
        import re as _re
        best = None
        for lab in LABELS:
            m = _re.search(lab + r".{0,80}" + AMT, joined, _re.I)
            if not m:
                m = _re.search(AMT + r".{0,80}" + lab, joined, _re.I)
            if m:
                cand = parse_amount(m.group(1))
                if cand is not None and (best is None or cand > best):
                    best = cand
        if best is not None:
            cur = data.get("castka_s_dph")
            # If LLM under-shot (e.g., dropped thousands), trust the labeled amount
            if cur is None or best >= max(cur * 1.5, cur + 100):
                data["castka_s_dph"] = best
    except Exception:
        pass

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
        "nazev": supplier.get("nazev"),
        "ico": supplier.get("ico"),
        "dic": supplier.get("dic"),
        "adresa": supplier.get("adresa"),
    }
    for k in ["mena","platba_zpusob","banka_prijemce","ucet_prijemce"]:
        data.setdefault(k, None)
    data.setdefault("confidence", 0.75)
    data.setdefault("variabilni_symbol", None)
    return data

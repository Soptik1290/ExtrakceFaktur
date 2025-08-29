
import re, os, json, glob
from dataclasses import dataclass
from typing import Dict, List, Optional
from .utils import normalize_date, parse_amount, detect_currency

@dataclass
class Template:
    name: str
    required_keywords: List[str]
    optional_keywords: List[str]
    fields: Dict[str, str]
    supplier_defaults: Dict[str, Optional[str]]

def _load_templates(dirpath: str):
    tpls = []
    for path in glob.glob(os.path.join(dirpath, "*.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tpls.append(Template(
            name=data.get("name", os.path.basename(path)),
            required_keywords=data.get("required_keywords", []),
            optional_keywords=data.get("optional_keywords", []),
            fields=data.get("fields", {}),
            supplier_defaults=data.get("supplier_defaults", {"nazev": None, "ico": None, "dic": None, "adresa": None})
        ))
    return tpls

_TEMPLATES = None

def _ensure_loaded():
    import os
    global _TEMPLATES
    if _TEMPLATES is not None: return
    dirpath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    _TEMPLATES = _load_templates(dirpath)

def _score(tpl: Template, text: str) -> int:
    score = 0
    for kw in tpl.required_keywords:
        if re.search(re.escape(kw), text, re.I): score += 3
        else: return -999
    for kw in tpl.optional_keywords:
        if re.search(re.escape(kw), text, re.I): score += 1
    return score

def _cap(pattern: str, text: str):
    m = re.search(pattern, text, re.I | re.M | re.S)
    if not m: return None
    return (m.group(1) if m.groups() else m.group(0)).strip()

def extract_fields_template(text: str) -> Optional[dict]:
    _ensure_loaded()
    if not _TEMPLATES: return None
    best, best_sc = None, -1000
    for t in _TEMPLATES:
        sc = _score(t, text)
        if sc > best_sc: best, best_sc = t, sc
    if not best or best_sc < 0: return None

    vals = {k: _cap(rx, text) for k, rx in best.fields.items()}
    for k in ["datum_vystaveni","datum_splatnosti","duzp"]:
        vals[k] = normalize_date(vals.get(k))
    for k in ["castka_bez_dph","dph","castka_s_dph"]:
        v = vals.get(k); vals[k] = parse_amount(v) if v is not None else None

    supplier = {
        "nazev": vals.get("dodavatel_nazev") or best.supplier_defaults.get("nazev"),
        "ico": vals.get("dodavatel_ico") or best.supplier_defaults.get("ico"),
        "dic": vals.get("dodavatel_dic") or best.supplier_defaults.get("dic"),
        "adresa": vals.get("dodavatel_adresa") or best.supplier_defaults.get("adresa"),
    }
    return {
        "variabilni_symbol": vals.get("variabilni_symbol"),
        "datum_vystaveni": vals.get("datum_vystaveni"),
        "datum_splatnosti": vals.get("datum_splatnosti"),
        "duzp": vals.get("duzp"),
        "castka_bez_dph": vals.get("castka_bez_dph"),
        "dph": vals.get("dph"),
        "castka_s_dph": vals.get("castka_s_dph"),
        "dodavatel": supplier,
        "mena": detect_currency(text),
        "platba_zpusob": vals.get("platba_zpusob"),
        "banka_prijemce": vals.get("banka_prijemce"),
        "ucet_prijemce": vals.get("ucet_prijemce"),
        "confidence": 0.9,
        "_template": best.name
    }

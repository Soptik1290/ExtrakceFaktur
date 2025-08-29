from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any
from .extractors.ocr import extract_text_from_file
from .extractors.heuristics import extract_fields_heuristic
from .extractors.validate import validate_extraction
from . import llm as llm_mod

app = FastAPI(title="ExtrakceFaktur API", version="1.0.0")

CRITICAL_FIELDS = ["variabilni_symbol", "datum_vystaveni", "datum_splatnosti", "castka_s_dph"]

def compute_confidence(data: dict, val: dict) -> float:
    score = 0.5
    score += 0.15 if val.get("sum_check") else 0.0
    score += 0.15 if val.get("ico_checksum") else 0.0
    score += 0.10 if val.get("dic_format_and_in_text") else 0.0
    score += 0.10 if val.get("variabilni_symbol") else 0.0
    filled = sum(1 for k in CRITICAL_FIELDS if data.get(k))
    score += 0.02 * filled
    return round(max(0.0, min(0.99, score)), 2)

def need_llm(data: dict, val: dict) -> bool:
    missing = sum(1 for k in CRITICAL_FIELDS if not data.get(k))
    bad = 0 if not val else (0 if val.get("sum_check") else 1) + (0 if val.get("ico_checksum") else 1)
    return (missing >= 2) or (missing >= 1 and bad >= 1)

def safe_merge(heur: dict, llm: dict, ocr_text: str) -> dict:
    out = {**heur}
    out.setdefault("dodavatel", {})
    llm = llm or {}
    llm_sup = llm.get("dodavatel") or {}

    def ok_string(v: Any) -> bool:
        return isinstance(v, str) and v and v.lower() in (ocr_text or "").lower()

    for k in ["variabilni_symbol","datum_vystaveni","datum_splatnosti","duzp","castka_bez_dph","dph","castka_s_dph","mena","platba_zpusob","banka_prijemce","ucet_prijemce"]:
        if not out.get(k) and (k in llm):
            v = llm.get(k)
            if isinstance(v, str):
                if ok_string(v): out[k] = v
            else:
                out[k] = v

    for k in ["nazev","ico","dic","adresa"]:
        if not out["dodavatel"].get(k) and (k in llm_sup):
            v = llm_sup.get(k)
            if isinstance(v, str):
                if ok_string(v): out["dodavatel"][k] = v
            else:
                out["dodavatel"][k] = v
    return out

@app.get("/")
def home():
    # Friendly landing: redirect to docs
    return RedirectResponse(url="/docs")

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    raw = await file.read()
    ocr_text = extract_text_from_file(raw, file.filename or "")
    data = extract_fields_heuristic(ocr_text)
    val = validate_extraction(data, ocr_text)
    method = "heuristic"

    if need_llm(data, val) and llm_mod.llm_available():
        llm_data = llm_mod.ask_llm(ocr_text) or {}
        merged = safe_merge(data, llm_data, ocr_text)
        merged_val = validate_extraction(merged, ocr_text)
        if sum(1 for k in CRITICAL_FIELDS if merged.get(k)) > sum(1 for k in CRITICAL_FIELDS if data.get(k)):
            data, val, method = merged, merged_val, "llm_fallback"

    data["confidence"] = compute_confidence(data, val)
    return JSONResponse({"data": data, "method": method, "validations": val})

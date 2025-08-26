import io
import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from .extractors.ocr import extract_text_from_file
from .extractors.heuristics import extract_fields_heuristic
from .extractors.validate import validate_extraction
from .extractors.llm import extract_fields_llm, llm_available
from .extractors.templates import extract_fields_template

load_dotenv()

app = FastAPI(title="Invoice Extractor", version="0.2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractResponse(BaseModel):
    data: dict
    method: str
    validations: dict

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/extract", response_model=ExtractResponse)
async def extract(file: UploadFile = File(...), method: Optional[str] = Query("auto")):
    content = await file.read()
    text = extract_text_from_file(filename=file.filename, data=content)

    used_method = ""
    result = None

    # 1) Template
    if method in ["template", "auto"]:
        tpl_res = extract_fields_template(text)
        if tpl_res:
            result = tpl_res
            used_method = "template"

    # 2) LLM
    if result is None and (method == "llm" or (method == "auto" and llm_available())):
        try:
            result = extract_fields_llm(text)
            used_method = "llm"
        except Exception:
            result = None

    # 3) Heuristic fallback
    if result is None:
        result = extract_fields_heuristic(text)
        used_method = "heuristic" if method != "llm" else "heuristic (fallback)"

    validations = validate_extraction(result)
    return ExtractResponse(data=result, method=used_method, validations=validations)

# --- Serve frontend last ---
from pathlib import Path as _Path
_FRONTEND_DIR = str((_Path(__file__).resolve().parents[1] / "frontend").resolve())
app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")

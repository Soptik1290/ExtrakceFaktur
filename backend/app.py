import io
import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from .extractors.ocr import extract_text_from_file
from .extractors.heuristics import extract_fields_heuristic
from .extractors.validate import validate_extraction
from .extractors.llm import extract_fields_llm, llm_available

load_dotenv()

app = FastAPI(title="Invoice Extractor", version="0.1.0")

# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# CORS (if you host frontend elsewhere)
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

    used_method = method
    result = None

    if method == "llm" or (method == "auto" and llm_available()):
        try:
            result = extract_fields_llm(text)
            used_method = "llm"
        except Exception as e:
            # Fallback to heuristics
            result = extract_fields_heuristic(text)
            used_method = "heuristic (fallback)"
    else:
        result = extract_fields_heuristic(text)
        used_method = "heuristic"

    validations = validate_extraction(result)
    return ExtractResponse(data=result, method=used_method, validations=validations)

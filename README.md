# Invoice Extractor – FastAPI + OCR + LLM + Template mode (5+ samples)

Features:
- Upload PDF/JPG/PNG
- OCR (Tesseract for images) + pdfplumber for PDF text
- Extraction modes: **Auto** → Template → LLM → Heuristic
- 5+ ready **templates** (ACME, Globex, Alfa, Omega, Delta)
- Validations (VS, IČO/DIČ, sum check), JSON + table UI
- Dockerfile for Render/Railway/VPS

Quick start:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
Open http://localhost:8000

Env:
```
OPENAI_API_KEY=   # optional for LLM
OPENAI_MODEL=gpt-4o-mini
```


**Czech vendor templates:** ČEZ Prodej, PRE, O2, T‑Mobile, Alza byly přidány do `backend/templates/`.


---

## OCR tips (přesnost)
- Pro lepší češtinu nainstaluj Tesseract language data `ces` (v Docker image Debian/Ubuntu balíček `tesseract-ocr-ces`).
- V `ocr.py` je nastaveno `lang="ces+eng"` a `--oem 3 --psm 6`, plus jednoduché předzpracování (grayscale, upscale, threshold).
- Pokud PDF nemá textovou vrstvu, fallback je OCR každé stránky (rasterizace přes pdfplumber).

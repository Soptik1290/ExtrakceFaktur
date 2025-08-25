# Invoice Extractor (Layout‑Agnostic, FastAPI + OCR + LLM, CZ/EN)

A reference web app to **extract structured data from invoices** without predefined templates.
It supports:
- Upload **PDF/JPG/PNG**
- **OCR** (Tesseract) or direct text extraction for PDFs
- **AI extraction** (LLM – optional, via `OPENAI_API_KEY`)
- **Heuristic fallback** (regex + rules, no AI)
- **Validation** (VS, IČO/DIČ, dates, sums)
- Web UI (single page) + JSON output
- Dockerfile to run anywhere

> Tested with Czech invoices; also works with English invoices.
> Dates/amounts are normalized to ISO/Decimal when possible.

---

## Quick Start (Local)

### 1) Prereqs
- Python 3.10+
- (optional for images OCR) **Tesseract OCR** installed:
  - Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
  - macOS (brew): `brew install tesseract`
  - Windows: install from https://github.com/UB-Mannheim/tesseract/wiki
- (optional) Poppler for pdf images (not required here; we use `pdfplumber` for PDF text)

### 2) Install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # and set keys if you want LLM mode
```

### 3) Run
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```
Then open: http://localhost:8000

### 4) Try with samples
- Either **generate** synthetic invoices:
  ```bash
  python scripts/generate_fake_invoices.py
  ```
  The PDFs will appear in `samples/generated/`.
- Or place your own 5+ invoices into `samples/` and upload via the UI.

---

## Docker
Build & run (includes Tesseract):
```bash
docker build -t invoice-extractor .
docker run -p 8000:8000 --env-file .env invoice-extractor
```
Open http://localhost:8000

---

## Features
- **/api/extract** – upload invoice; returns structured JSON
- Methods:
  - `auto` (default): try LLM if `OPENAI_API_KEY` present, else heuristics
  - `llm` : force AI extraction
  - `heuristic` : force regex/rules (no AI)
- **Validation**:
  - VS length/format, IČO checksum, DIČ pattern (CZ + EU), dates ISO, sum tolerance
- **UI**:
  - upload → preview JSON → renders table with ✅/⚠️ validation states
  - export JSON

---

## Env (.env)
```
OPENAI_API_KEY=your_key_here   # optional (for LLM extraction)
OPENAI_MODEL=gpt-4o-mini       # optional override
```
If no key is provided, the app will still work in **heuristic** mode.

---

## Notes
- PDFs: we use `pdfplumber` (no external binaries).
- Images: OCR via `pytesseract` (requires Tesseract installed).
- This is a demo/starter. For production, consider retry policies, audit logs,
  and advanced VLMs or managed services.

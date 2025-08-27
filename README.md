# Invoice Extractor – Export (JSON/TXT/CSV/XLSX) + Templates + LLM + Heuristics

## Export
- Endpoint: `POST /api/export` with JSON body:
  ```json
  { "format": "json|txt|csv|xlsx", "data": { ...extracted_data... }, "filename": "optional_name" }
  ```
- Vrátí binární soubor ke stažení (Content-Disposition: attachment).

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
Otevři: http://localhost:8000

## Env
```
OPENAI_API_KEY=            # optional for LLM
OPENAI_MODEL=gpt-4o-mini
```

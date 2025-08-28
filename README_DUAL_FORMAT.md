# Dual Format Invoice Extractor

## Přehled

Nový systém pro extrakci dat z faktur, který automaticky převádí mezi formáty (PDF ↔ PNG) a kombinuje výsledky pro lepší přesnost a konzistenci.

## Problém, který řeší

**Původní problém**: Stejná faktura může dát různé výsledky v závislosti na formátu:
- PDF: Může mít problémy s OCR nebo formátováním
- PNG: Může mít problémy s rozlišením nebo kvalitou

**Řešení**: Automatický převod mezi formáty a kombinování výsledků

## Jak to funguje

### 1. Automatický převod formátů
```
PDF → PNG (pro OCR)
PNG → PDF (pro text extraction)
```

### 2. Duální extrakce
- **Original format**: Extrakce z původního formátu
- **Converted format**: Extrakce z převedeného formátu
- **Combination**: Inteligentní sloučení výsledků

### 3. Metody extrakce
- **Template**: Strukturované šablony
- **LLM**: Umělá inteligence (OpenAI)
- **Heuristic**: Pravidla a regex patterny

## Klíčové funkce

### ✅ Automatický převod formátů
- PDF → PNG s vysokým rozlišením
- PNG → PDF pro text extraction
- Zachování kvality

### ✅ Kombinování výsledků
- Prioritizace kompletních výsledků
- Sloučení doplňujících informací
- Konzistentní výstup

### ✅ Confidence scoring
- Hodnocení kvality extrakce
- Výběr nejlepšího výsledku
- Transparentnost procesu

### ✅ Česká diakritika
- Plná podpora háčků a čárek
- Rozpoznávání českých názvů
- Lepší přesnost pro české faktury

## API Endpointy

### POST `/api/extract`
**Parametry:**
- `file`: Upload souboru
- `method`: Metoda extrakce (`auto`, `template`, `llm`, `heuristic`)
- `use_dual_format`: Použít duální formát (default: `true`)

**Příklad:**
```bash
curl -X POST "http://localhost:8000/api/extract?use_dual_format=true" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@faktura.pdf"
```

### GET `/api/formats`
Informace o podporovaných formátech a funkcích.

## Příklad použití

### 1. Nahrání PDF faktury
```python
import requests

url = "http://localhost:8000/api/extract"
files = {"file": open("faktura.pdf", "rb")}
params = {"use_dual_format": True, "method": "auto"}

response = requests.post(url, files=files, params=params)
result = response.json()

print(f"Metoda: {result['method']}")
print(f"Částka: {result['data']['castka_s_dph']}")
print(f"DPH: {result['data']['dph']}")
```

### 2. Výstup s metadaty
```json
{
  "data": {
    "castka_s_dph": 44413.0,
    "dph": 9327.73,
    "castka_bez_dph": 35085.27,
    "mena": "CZK",
    "datum_vystaveni": "2024-01-15"
  },
  "method": "dual_format_combined",
  "validations": {...}
}
```

## Výhody nového systému

### 🎯 **Lepší přesnost**
- Kombinace výsledků z obou formátů
- Automatický výběr nejlepšího textu
- Redundance pro spolehlivost

### 🔄 **Konzistence**
- Stejné výsledky bez ohledu na vstupní formát
- Eliminace rozdílů PDF vs PNG
- Stabilní extrakce

### 📊 **Transparentnost**
- Viditelnost použitých metod
- Confidence scoring
- Debugging informace

### 🇨🇿 **Česká podpora**
- Plná diakritika
- České klíčové slova
- Lokalizované regex patterny

## Instalace

### 1. Závislosti
```bash
pip install -r requirements.txt
```

### 2. Spuštění
```bash
python backend/app.py
```

### 3. Testování
```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/formats
```

## Technické detaily

### Architektura
```
FormatManager → DualExtractor → Heuristics/LLM/Templates
     ↓              ↓                    ↓
PDF↔PNG      Kombinace výsledků    Extrakce polí
```

### Klíčové třídy
- **`FormatManager`**: Správa formátů a převody
- **`DualExtractor`**: Kombinování výsledků
- **`FormatManager`**: Confidence scoring

### Logování
- Detailní logy procesu
- Debugging informace
- Performance metriky

## Troubleshooting

### Časté problémy

**1. Chybějící PyMuPDF**
```bash
pip install PyMuPDF
```

**2. Chybějící Tesseract**
```bash
# Windows
# Stáhnout a nainstalovat z: https://github.com/UB-Mannheim/tesseract/wiki

# Linux
sudo apt-get install tesseract-ocr tesseract-ocr-ces
```

**3. Memory issues**
- Snížit rozlišení PDF→PNG konverze
- Upravit `Matrix(2.0, 2.0)` v `pdf_to_image`

## Budoucí vylepšení

- [ ] Podpora více jazyků
- [ ] Machine learning pro kombinování
- [ ] Batch processing
- [ ] Caching výsledků
- [ ] API rate limiting
- [ ] Webhook notifikace

## Kontakt

Pro dotazy nebo problémy kontaktujte vývojový tým.

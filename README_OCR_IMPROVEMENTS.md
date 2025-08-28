# Vylepšené OCR pro české faktury

## Problém
Původní implementace měla dva hlavní problémy:
1. **PDF extrakce**: Chybné rozpoznávání částek (4413 místo 44 413)
2. **OCR obrázky**: Chybné rozpoznávání českých znaků (Komeréni místo Komerční)

## Řešení

### 1. Vylepšená PDF extrakce s OCR fallbackem
- Automaticky detekuje nekvalitní text extrakci
- Přepíná na OCR, pokud jsou částky chybné
- Používá PyMuPDF pro lepší renderování PDF

### 2. Lepší OCR s českým jazykem
- Automaticky zkouší různé OCR konfigurace
- Prioritně používá český jazyk (`ces+eng`)
- Vysoké rozlišení pro lepší kvalitu

### 3. Inteligentní korekce částek
- Detekuje podezřele malé částky
- Automaticky opravuje OCR chyby v číslech
- Kontroluje konzistenci mezi částkami

### 4. Oprava českých textů
- Automaticky opravuje běžné OCR chyby
- "Komeréni" → "Komerční"
- "Pizen" → "Plzeň"

## Instalace

### 1. Závislosti
```bash
pip install -r requirements.txt
```

### 2. Tesseract OCR
#### Windows:
1. Stáhněte Tesseract z: https://github.com/UB-Mannheim/tesseract/wiki
2. Nainstalujte do `C:\Program Files\Tesseract-OCR\`
3. Stáhněte český jazyk: https://github.com/tesseract-ocr/tessdata
4. Umístěte `ces.traineddata` do `C:\Program Files\Tesseract-OCR\tessdata\`

#### Ubuntu/Debian:
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-ces
```

#### macOS:
```bash
brew install tesseract tesseract-lang
```

### 3. Kontrola instalace
```bash
python scripts/check_tesseract.py
```

## Použití

### Automatické přepínání
Systém automaticky:
1. Zkusí standardní PDF text extrakci
2. Pokud detekuje problémy s částkami, přepne na OCR
3. Opraví české texty a částky

### Manuální kontrola
V logu uvidíte:
```
PDF text má problémy s částkami, přepínám na OCR...
Spouštím OCR fallback pro PDF...
OCR fallback dokončen, délka textu: 1234
Detekovány problémy s částkami: ['Podezřele malá částka: 4413 (možná chybí mezera)']
```

## Konfigurace

### Environment proměnné
```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini  # nebo jiný model
```

### OCR parametry
V `backend/extractors/ocr.py` můžete upravit:
- Rozlišení renderování PDF (`fitz.Matrix(3.0, 3.0)`)
- OCR konfigurace (`--psm 6 --oem 3`)
- Jazyky (`ces+eng`)

## Testování

### Test OCR
```bash
python scripts/check_tesseract.py
```

### Test s fakturou
1. Nahrajte PDF fakturu
2. Zkontrolujte logy v konzoli
3. Ověřte, že se aktivoval OCR fallback

## Řešení problémů

### OCR nefunguje
1. Zkontrolujte, zda je Tesseract v PATH
2. Ověřte, zda je nainstalován český jazyk
3. Spusťte `python scripts/check_tesseract.py`

### Stále chybné částky
1. Zkontrolujte logy - měl by se aktivovat OCR fallback
2. Zvyšte rozlišení v `fitz.Matrix(4.0, 4.0)`
3. Přidejte další OCR konfigurace

### Stále chybné české texty
1. Ověřte, zda je nainstalován český jazyk
2. Zkontrolujte, zda se používá `lang='ces+eng'`
3. Přidejte další opravy do `_fix_czech_text()`

## Výkon

### Rychlost
- Standardní PDF extrakce: ~100ms
- OCR fallback: ~2-5s (závisí na velikosti PDF)
- Automatické přepínání pouze při problémech

### Kvalita
- PDF s dobrým textem: Standardní extrakce
- PDF s chybnými částkami: OCR fallback
- Obrázky: Vylepšené OCR s českým jazykem

## Budoucí vylepšení

1. **Machine Learning**: Trénování na českých fakturách
2. **Template matching**: Automatické rozpoznávání formátů
3. **Confidence scoring**: Lepší hodnocení kvality extrakce
4. **Batch processing**: Zpracování více faktur najednou

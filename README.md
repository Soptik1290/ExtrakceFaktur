# 🧾 Faktury – Extrakce dat z faktur

Tento projekt slouží k **automatické extrakci údajů z faktur** pomocí OCR, heuristik a jazykových modelů.  
Výsledkem je jednotný JSON s klíčovými informacemi (dodavatel, odběratel, částky, variabilní symbol, splatnost…).

---

## 🚀 Novinky ve verzi 1.1.0
- Upscaling obrázků s nízkým rozlišením → lepší čitelnost horších skenů.
- Vylepšená detekce textu a **české diakritiky**.
- Přesnější rozpoznávání částek.
- Rozšířená validace extrahovaných dat.
- Lepší **responsibilita** aplikace na mobilních zařízeních.
- Opraven problém s detekcí **datumů**.

---

## 🚀 Funkcionality
- Nahrání faktury přes webové rozhraní (frontend).
- Automatická extrakce dat pomocí backendu:
  - **OCR** – převod obrazu na text.
  - **Heuristiky** – základní pravidla a regulární výrazy.
  - **LLM** – pokročilá interpretace faktur.
  - **Šablony** – specifická pravidla pro vybrané dodavatele (Alza, ČEZ, O2, T-Mobile…).
- Výstup v jednotném JSON formátu.
- Ukázkové faktury pro testování.
- Docker kontejner pro snadné spuštění.

---

## 📂 Struktura projektu
```
backend/        # Python logika pro extrakci
frontend/       # HTML, CSS, JS rozhraní
samples/        # ukázkové faktury
scripts/        # generátor testovacích faktur
requirements.txt
Dockerfile
```

---

## 🔧 Instalace a spuštění

### Lokální prostředí
1. Naklonuj repo:
   ```bash
   git clone https://github.com/uzivatel/Faktury.git
   cd Faktury/ExtrakceFaktur
   ```
2. Vytvoř virtuální prostředí a nainstaluj závislosti:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Spusť backend:
   ```bash
   python backend/app.py
   ```
4. Otevři `frontend/index.html` v prohlížeči.

### Docker
```bash
docker build -t faktury .
docker run -p 8000:8000 faktury
```

---

## 📸 Ukázky
- Najdeš v adresáři `samples/`.

---

## 🛠 Technologie
- **Backend**: Python 3.10, OCR (Tesseract/…), heuristiky, LLM
- **Frontend**: HTML, CSS, JavaScript
- **Kontejnerizace**: Docker

---

## 🤝 Příspěvky
Pull requesty a issues jsou vítány! 🎉

---

## 📜 Licence
MIT

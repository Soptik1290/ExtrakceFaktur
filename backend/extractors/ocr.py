
import io
import pdfplumber
from PIL import Image
import pytesseract
import fitz  # PyMuPDF pro lepší PDF zpracování
import re

def _pdf_text(data: bytes) -> str:
    """Vylepšená PDF extrakce s OCR fallbackem pro problematické částky"""
    text_parts = []
    
    # 1. Zkus standardní text extrakci
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
                text_parts.append(t)
        text = "\n".join(text_parts)
        
        # 2. Kontrola kvality - pokud chybí částky nebo jsou chybné, použij OCR
        if not _has_good_amounts(text) or _has_suspicious_amounts(text):
            print("PDF text má problémy s částkami, přepínám na OCR...")
            text = _pdf_ocr_fallback(data)
            
        return text
    except Exception as e:
        print(f"PDF extrakce selhala: {e}, přepínám na OCR...")
        # 3. Fallback na OCR
        return _pdf_ocr_fallback(data)

def _has_good_amounts(text: str) -> bool:
    """Kontrola, zda text obsahuje dobře rozpoznané částky"""
    # Hledej částky v českém formátu (44 413,00 nebo 44413.00)
    amount_patterns = [
        r'\d{1,3}(?:\s\d{3})*(?:,\d{2})?',  # 44 413,00
        r'\d{1,3}(?:\s\d{3})*(?:\.\d{2})?',  # 44 413.00
        r'\d{4,}',  # 44413
    ]
    
    for pattern in amount_patterns:
        if re.search(pattern, text):
            return True
    return False

def _has_suspicious_amounts(text: str) -> bool:
    """Detekuje podezřele malé částky, které mohou být OCR chyby"""
    # Hledej částky, které vypadají jako chyby (např. 4413 místo 44 413)
    suspicious_patterns = [
        r'\b\d{4}\b',  # 4 číslice (může být chyba)
        r'\b\d{5}\b',  # 5 číslic (může být chyba)
    ]
    
    for pattern in suspicious_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Pokud je to částka a vypadá podezřele malá
            if int(match) < 10000:  # Méně než 10k
                return True
    return False

def _pdf_ocr_fallback(data: bytes) -> str:
    """OCR fallback pro PDF s problematickým textem"""
    try:
        print("Spouštím OCR fallback pro PDF...")
        # Použij PyMuPDF pro konverzi PDF na obrázky
        doc = fitz.open(stream=data, filetype="pdf")
        text_parts = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Renderuj stránku jako obrázek s vysokým rozlišením
            mat = fitz.Matrix(3.0, 3.0)  # 3x zoom pro lepší kvalitu
            pix = page.get_pixmap(matrix=mat)
            
            # Konvertuj na PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # OCR s českým jazykem - zkus různé konfigurace
            text = _try_ocr_with_fallback(img)
            text_parts.append(text)
        
        doc.close()
        final_text = "\n".join(text_parts)
        print(f"OCR fallback dokončen, délka textu: {len(final_text)}")
        return final_text
    except Exception as e:
        print(f"OCR fallback selhal: {e}")
        # Pokud PyMuPDF selže, vrať původní text
        return ""

def _try_ocr_with_fallback(img: Image.Image) -> str:
    """Zkusí OCR s různými konfiguracemi pro lepší výsledky"""
    # Seznam konfigurací k vyzkoušení
    configs = [
        '--psm 6 --oem 3',  # Uniform block, LSTM
        '--psm 8 --oem 3',  # Single word, LSTM
        '--psm 6 --oem 1',  # Uniform block, Legacy
        '--psm 8 --oem 1',  # Single word, Legacy
    ]
    
    # Zkus různé jazyky
    languages = ['ces+eng', 'ces', 'eng']
    
    best_text = ""
    best_confidence = 0
    
    for lang in languages:
        for config in configs:
            try:
                text = pytesseract.image_to_string(
                    img, 
                    lang=lang,
                    config=config
                )
                
                # Jednoduchá heuristika pro kvalitu textu
                confidence = _calculate_text_confidence(text)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_text = text
                    
            except Exception:
                continue
    
    return best_text if best_text else pytesseract.image_to_string(img, lang='eng')

def _calculate_text_confidence(text: str) -> float:
    """Jednoduchá heuristika pro kvalitu OCR textu"""
    if not text:
        return 0.0
    
    # Počítá české znaky, částky, atd.
    czech_chars = len(re.findall(r'[čřžšěáéíóúůý]', text, re.IGNORECASE))
    amounts = len(re.findall(r'\d{1,3}(?:\s\d{3})*(?:,\d{2})?', text))
    total_chars = len(text.strip())
    
    if total_chars == 0:
        return 0.0
    
    # Vážený skóre
    score = (czech_chars * 2 + amounts * 5) / total_chars
    return min(score, 1.0)

def _image_text(data: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(data))
        # Vylepšené OCR s českým jazykem
        return _try_ocr_with_fallback(img)
    except Exception as e:
        print(f"OCR pro obrázek selhal: {e}")
        return ""

def extract_text_from_file(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _pdf_text(data)
    if any(name.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]):
        return _image_text(data)
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""

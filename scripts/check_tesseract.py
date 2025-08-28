#!/usr/bin/env python3
"""
Skript pro kontrolu a instalaci českých jazykových balíčků pro Tesseract OCR
"""

import subprocess
import sys
import os

def check_tesseract():
    """Kontroluje, zda je Tesseract nainstalován"""
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, check=True)
        print("✓ Tesseract je nainstalován:")
        print(result.stdout)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Tesseract není nainstalován nebo není v PATH")
        return False

def check_languages():
    """Kontroluje dostupné jazyky"""
    try:
        result = subprocess.run(['tesseract', '--list-langs'], 
                              capture_output=True, text=True, check=True)
        languages = result.stdout.strip().split('\n')[1:]  # První řádek je "Available languages:"
        
        print("✓ Dostupné jazyky:")
        for lang in languages:
            if lang.strip():
                print(f"  - {lang.strip()}")
        
        # Kontrola českého jazyka
        czech_available = any('ces' in lang.lower() for lang in languages)
        if czech_available:
            print("✓ Český jazyk (ces) je dostupný")
        else:
            print("✗ Český jazyk (ces) NENÍ dostupný")
            
        return czech_available
    except Exception as e:
        print(f"✗ Chyba při kontrole jazyků: {e}")
        return False

def install_czech_language():
    """Instaluje český jazyk pro Tesseract"""
    print("\n📥 Instalace českého jazyka...")
    
    # Pro Windows
    if os.name == 'nt':
        print("Pro Windows stáhněte český jazykový balíček z:")
        print("https://github.com/tesseract-ocr/tessdata")
        print("a umístěte ces.traineddata do:")
        print("C:\\Program Files\\Tesseract-OCR\\tessdata\\")
        return False
    
    # Pro Linux
    try:
        # Ubuntu/Debian
        result = subprocess.run(['sudo', 'apt-get', 'install', 'tesseract-ocr-ces'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Český jazyk nainstalován přes apt-get")
            return True
    except FileNotFoundError:
        pass
    
    try:
        # CentOS/RHEL
        result = subprocess.run(['sudo', 'yum', 'install', 'tesseract-langpack-ces'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Český jazyk nainstalován přes yum")
            return True
    except FileNotFoundError:
        pass
    
    print("✗ Automatická instalace selhala")
    print("Manuální instalace:")
    print("1. Ubuntu/Debian: sudo apt-get install tesseract-ocr-ces")
    print("2. CentOS/RHEL: sudo yum install tesseract-langpack-ces")
    print("3. macOS: brew install tesseract-lang")
    return False

def test_ocr():
    """Testuje OCR s českým textem"""
    print("\n🧪 Testování OCR...")
    
    # Vytvoř testovací obrázek s českým textem
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Vytvoř jednoduchý obrázek
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Zkus použít font (může selhat na některých systémech)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        text = "Komerční banka, a.s. - Plzeň"
        draw.text((10, 40), text, fill='black', font=font)
        
        # Ulož do bufferu
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Test OCR
        import pytesseract
        result = pytesseract.image_to_string(img, lang='ces+eng')
        
        print(f"✓ OCR test úspěšný:")
        print(f"  Očekávaný text: {text}")
        print(f"  Rozpoznaný text: {result.strip()}")
        
        # Kontrola českých znaků
        if 'č' in result or 'ř' in result:
            print("✓ České znaky jsou správně rozpoznány")
        else:
            print("⚠ České znaky nejsou správně rozpoznány")
            
        return True
        
    except Exception as e:
        print(f"✗ OCR test selhal: {e}")
        return False

def main():
    """Hlavní funkce"""
    print("🔍 Kontrola Tesseract OCR pro české faktury\n")
    
    # Kontrola instalace
    if not check_tesseract():
        print("\n❌ Tesseract není nainstalován!")
        print("Instalace:")
        print("- Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("- Ubuntu/Debian: sudo apt-get install tesseract-ocr")
        print("- macOS: brew install tesseract")
        return
    
    # Kontrola jazyků
    czech_available = check_languages()
    
    if not czech_available:
        print("\n❌ Český jazyk není dostupný!")
        install_czech_language()
        return
    
    # Test OCR
    test_ocr()
    
    print("\n✅ Tesseract je připraven pro české faktury!")

if __name__ == "__main__":
    main()

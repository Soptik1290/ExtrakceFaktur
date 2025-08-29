import io
import pdfplumber
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import pytesseract

def _pdf_text(data: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
            text_parts.append(t)
    return "\n".join(text_parts)

def _otsu_threshold(img):
    hist = img.histogram()
    total = sum(hist)
    sumB = 0
    wB = 0
    maximum = 0.0
    sum1 = sum(i * h for i, h in enumerate(hist))
    level = 0
    for i in range(256):
        wB += hist[i]
        if wB == 0:
            continue
        wF = total - wB
        if wF == 0:
            break
        sumB += i * hist[i]
        mB = sumB / wB
        mF = (sum1 - sumB) / wF
        between = wB * wF * (mB - mF) ** 2
        if between > maximum:
            level = i
            maximum = between
    return level

def _prepare(img):
    g = ImageOps.grayscale(img)
    g = g.filter(ImageFilter.MedianFilter(size=3))
    g = ImageEnhance.Contrast(g).enhance(1.3)
    g = ImageEnhance.Sharpness(g).enhance(1.2)
    thr = _otsu_threshold(g)
    b = g.point(lambda x: 255 if x > thr else 0, mode='1').convert('L')
    return g, b

def _tesseract(img):
    cfg = "--oem 3 --psm 6"
    try:
        return pytesseract.image_to_string(img, lang="ces+eng", config=cfg, timeout=20)
    except Exception:
        try:
            return pytesseract.image_to_string(img, config=cfg, timeout=20)
        except Exception:
            return ""

def extract_text_from_file(file: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        text = _pdf_text(file)
        if text and len(text.strip()) > 30:
            return text
        try:
            with pdfplumber.open(io.BytesIO(file)) as pdf:
                if pdf.pages:
                    img = pdf.pages[0].to_image(resolution=300).original
                    g, b = _prepare(img)
                    t1 = _tesseract(g)
                    t2 = _tesseract(b)
                    return t1 if len(t1) >= len(t2) else t2
        except Exception:
            pass
        return text or ""
    else:
        from PIL import Image
        try:
            img = Image.open(io.BytesIO(file))
            if max(img.size) < 1800:
                scale = max(1, int(1800 / max(img.size)))
                img = img.resize((img.width*scale, img.height*scale), Image.BICUBIC)
            g, b = _prepare(img)
            t1 = _tesseract(g)
            t2 = _tesseract(b)
            return t1 if len(t1) >= len(t2) else t2
        except Exception:
            return ""

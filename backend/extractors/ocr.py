
import io
import pdfplumber
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import pytesseract
import re

def _pdf_text(data: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
            text_parts.append(t)
    return "\n".join(text_parts)

def _resampling():
    try:
        return Image.Resampling.LANCZOS  # Pillow >= 10
    except Exception:
        return Image.LANCZOS

def _otsu_threshold(gray: Image.Image) -> int:
    hist = gray.histogram()
    total = sum(hist)
    sum_total = sum(i * h for i, h in enumerate(hist))
    sum_b = 0.0
    w_b = 0.0
    max_var = 0.0
    threshold = 128
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        between = w_b * w_f * (m_b - m_f) ** 2
        if between > max_var:
            max_var = between
            threshold = t
    return threshold

def _preprocess_for_ocr(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    # Convert to grayscale
    g = img.convert("L")
    # Upscale small images to improve text size for Tesseract
    min_dim = min(g.size)
    if min_dim < 1000:
        scale = max(2, min(4, (1000 + min_dim - 1) // min_dim))
        new_size = (g.size[0] * scale, g.size[1] * scale)
        g = g.resize(new_size, _resampling())
    # Autocontrast and slight sharpening
    g = ImageOps.autocontrast(g)
    g = ImageEnhance.Sharpness(g).enhance(1.3)
    g = g.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=3))
    # Binarize using Otsu
    thr = _otsu_threshold(g)
    b = g.point(lambda x: 255 if x > thr else 0, mode='1').convert('L')
    return g, b

def _tesseract(img: Image.Image) -> str:
    # Try Czech + English first, fallback to default if the language pack is missing
    cfg = "--oem 3 --psm 6"
    for lang in ["ces+eng", "eng+ces", None]:
        try:
            txt = pytesseract.image_to_string(img, lang=lang, config=cfg) if lang else pytesseract.image_to_string(img, config=cfg)
            # Heuristic: ignore clearly broken results
            if txt and len(re.findall(r"[A-Za-z0-9]", txt)) >= 5:
                return txt
        except Exception:
            continue
    return ""

def _image_text(data: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return ""
    try:
        g, b = _preprocess_for_ocr(img)
        t1 = _tesseract(g)
        t2 = _tesseract(b)
        return t1 if len(t1) >= len(t2) else t2
    except Exception:
        try:
            return _tesseract(img)
        except Exception:
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

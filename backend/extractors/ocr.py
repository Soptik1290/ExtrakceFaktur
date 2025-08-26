import io
import pdfplumber
from PIL import Image, ImageOps, ImageFilter
import pytesseract

TESS_LANG = "ces+eng"  # try Czech + English; if 'ces' data aren't installed, Tesseract falls back
TESS_CONFIG = "--oem 3 --psm 6"  # LSTM, assume a uniform block of text

def _pdf_text(data: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            # Try text extraction first
            t = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
            if t and len(t.strip()) >= 20:
                text_parts.append(t)
            else:
                # Fallback OCR: rasterize page to image via page.to_image (requires pillow only)
                # Render at higher resolution for better OCR
                im = page.to_image(resolution=200).original
                text_parts.append(_ocr_pil(im))
    return "\n".join(text_parts)

def _preprocess(img: Image.Image) -> Image.Image:
    # Convert to grayscale, increase contrast, slight sharpening, binarize
    g = ImageOps.grayscale(img)
    # upscale smaller images to help OCR
    if min(g.size) < 1200:
        scale = max(1.5, 1200 / float(min(g.size)))
        new_size = (int(g.size[0]*scale), int(g.size[1]*scale))
        g = g.resize(new_size, Image.BICUBIC)
    g = ImageOps.autocontrast(g)
    g = g.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=3))
    # simple threshold
    g = g.point(lambda x: 255 if x > 200 else (0 if x < 140 else x))
    return g

def _ocr_pil(img: Image.Image) -> str:
    try:
        prep = _preprocess(img)
        return pytesseract.image_to_string(prep, lang=TESS_LANG, config=TESS_CONFIG)
    except Exception:
        # Try default without lang/config as last resort
        try:
            return pytesseract.image_to_string(img)
        except Exception:
            return ""

def _image_text(data: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return ""
    return _ocr_pil(img)

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

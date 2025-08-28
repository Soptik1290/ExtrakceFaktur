
import io
import pdfplumber
from PIL import Image
import pytesseract
try:
    from pdf2image import convert_from_bytes as _convert_from_bytes
except Exception:  # pdf2image or poppler may be unavailable in some envs
    _convert_from_bytes = None

def _pdf_text(data: bytes) -> str:
    """
    Try text extraction via pdfplumber first. If pages yield little/empty text
    (typical for scanned PDFs), fall back to OCR by rasterizing pages.
    """
    text_parts = []
    ocr_needed = False
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
                # Heuristic: many scanned PDFs return very short/empty strings
                if len((t or "").strip()) < 10:
                    ocr_needed = True
                text_parts.append(t)
    except Exception:
        # If parsing fails entirely, force OCR path
        ocr_needed = True

    # If we collected some meaningful text and OCR is not required, return it
    if text_parts and not ocr_needed and any(len((t or "").strip()) > 10 for t in text_parts):
        return "\n".join(text_parts)

    # Fallback: OCR each page rendered as image
    try:
        if _convert_from_bytes is None:
            # Fallback not available on this platform; return whatever text we had
            return "\n".join([t for t in text_parts if t])
        pages = _convert_from_bytes(data, fmt="png")
        ocr_texts = []
        for img in pages:
            try:
                ocr_texts.append(_image_text_from_pil(img))
            except Exception:
                continue
        return "\n".join([t for t in ocr_texts if t])
    except Exception:
        return "\n".join([t for t in text_parts if t])

def _tesseract_config():
    lang = "ces+eng"  # Czech + English for best invoice coverage
    # Preserve diacritics and improve segmentation for documents
    config = "--oem 3 --psm 6"
    return lang, config

def _image_text_from_pil(img: Image.Image) -> str:
    # Safety for huge PNGs that can be slow or trigger decompression warnings
    try:
        Image.MAX_IMAGE_PIXELS = 50_000_000
    except Exception:
        pass

    # Normalize mode and size
    if img.mode not in ("L", "RGB"):
        img = img.convert("RGB")
    # Downscale if extremely large
    max_side = max(img.size)
    if max_side > 2400:
        scale = 2400 / float(max_side)
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size)
    # Grayscale often improves OCR speed and robustness
    if img.mode != "L":
        img = img.convert("L")

    lang, config = _tesseract_config()
    try:
        # Prevent infinite waiting on problematic images
        return pytesseract.image_to_string(img, lang=lang, config=config, timeout=15)
    except Exception:
        # If Tesseract times out or fails, return empty string so pipeline continues
        return ""

def _image_text(data: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return ""
    try:
        return _image_text_from_pil(img)
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

import io
import pdfplumber
from PIL import Image
import pytesseract

def _pdf_text(data: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
            text_parts.append(t)
    return "\n".join(text_parts)

def _image_text(data: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return ""
    try:
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

def extract_text_from_file(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        text = _pdf_text(data)
        return text
    if any(name.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]):
        return _image_text(data)
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""

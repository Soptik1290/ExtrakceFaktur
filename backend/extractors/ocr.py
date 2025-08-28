
import io
import pdfplumber
from PIL import Image
import pytesseract
from .format_manager import format_manager

def _pdf_text(data: bytes) -> str:
    """Legacy PDF text extraction - kept for backward compatibility."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
            text_parts.append(t)
    return "\n".join(text_parts)

def _image_text(data: bytes) -> str:
    """Legacy image text extraction - kept for backward compatibility."""
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return ""
    try:
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

def extract_text_from_file(filename: str, data: bytes) -> str:
    """
    Legacy function - kept for backward compatibility.
    For better results, use extract_text_dual_format instead.
    """
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _pdf_text(data)
    if any(name.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]):
        return _image_text(data)
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def extract_text_dual_format(filename: str, data: bytes) -> dict:
    """
    Extract text using both original format and converted format.
    Returns dict with 'original', 'converted', and 'format' keys.
    """
    return format_manager.extract_text_dual_format(filename, data)

def extract_text_combined(filename: str, data: bytes) -> str:
    """
    Extract text and combine results from both formats for better accuracy.
    Returns the best available text.
    """
    dual_result = format_manager.extract_text_dual_format(filename, data)
    
    # Choose the better text based on confidence score
    original_score = format_manager.get_confidence_score(dual_result['original'])
    converted_score = format_manager.get_confidence_score(dual_result['converted'])
    
    if original_score >= converted_score:
        return dual_result['original']
    else:
        return dual_result['converted']

def get_extraction_confidence(filename: str, data: bytes) -> float:
    """
    Get confidence score for the extracted text.
    Higher score means more reliable extraction.
    """
    dual_result = format_manager.extract_text_dual_format(filename, data)
    return format_manager.get_confidence_score(dual_result['original'])

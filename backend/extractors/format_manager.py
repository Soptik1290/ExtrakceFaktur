import io
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import pdfplumber
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class FormatManager:
    """
    Manages different file formats and combines extraction results for better accuracy.
    Automatically converts between PDF and PNG formats to ensure consistent extraction.
    """
    
    def __init__(self):
        self.supported_formats = {
            'pdf': ['.pdf'],
            'image': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp'],
            'text': ['.txt']
        }
    
    def get_file_format(self, filename: str) -> str:
        """Determine file format from filename."""
        name = (filename or "").lower()
        for format_type, extensions in self.supported_formats.items():
            if any(name.endswith(ext) for ext in extensions):
                return format_type
        return 'unknown'
    
    def extract_text_pdf(self, data: bytes) -> str:
        """Extract text from PDF using pdfplumber."""
        try:
            text_parts = []
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
                    text_parts.append(t)
            return "\n".join(text_parts)
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {e}")
            return ""
    
    def extract_text_image(self, data: bytes) -> str:
        """Extract text from image using OCR."""
        try:
            img = Image.open(io.BytesIO(data))
            return pytesseract.image_to_string(img, lang='ces+eng')
        except Exception as e:
            logger.warning(f"Image OCR failed: {e}")
            return ""
    
    def pdf_to_image(self, data: bytes) -> bytes:
        """Convert PDF to PNG image for OCR processing."""
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            page = doc[0]  # First page
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image and then to PNG bytes
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            return img_buffer.getvalue()
        except Exception as e:
            logger.warning(f"PDF to image conversion failed: {e}")
            return b""
    
    def image_to_pdf(self, data: bytes) -> bytes:
        """Convert image to PDF for text extraction."""
        try:
            img = Image.open(io.BytesIO(data))
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create a simple PDF
            pdf_buffer = io.BytesIO()
            img.save(pdf_buffer, format='PDF')
            return pdf_buffer.getvalue()
        except Exception as e:
            logger.warning(f"Image to PDF conversion failed: {e}")
            return b""
    
    def extract_text_dual_format(self, filename: str, data: bytes) -> Dict[str, str]:
        """
        Extract text using both original format and converted format.
        Returns dict with 'original' and 'converted' text.
        """
        original_format = self.get_file_format(filename)
        result = {'original': '', 'converted': '', 'format': original_format}
        
        # Extract text from original format
        if original_format == 'pdf':
            result['original'] = self.extract_text_pdf(data)
            # Convert to image and extract via OCR
            image_data = self.pdf_to_image(data)
            if image_data:
                result['converted'] = self.extract_text_image(image_data)
                
        elif original_format == 'image':
            result['original'] = self.extract_text_image(data)
            # Convert to PDF and extract text
            pdf_data = self.image_to_pdf(data)
            if pdf_data:
                result['converted'] = self.extract_text_pdf(pdf_data)
        
        return result
    
    def combine_extraction_results(self, results: List[Dict]) -> Dict:
        """
        Combine multiple extraction results for better accuracy.
        Prioritizes non-None values and merges complementary information.
        """
        if not results:
            return {}
        
        if len(results) == 1:
            return results[0]
        
        # Find the most complete result
        best_result = max(results, key=lambda x: sum(1 for v in x.values() if v is not None))
        
        # Merge complementary information from other results
        merged = best_result.copy()
        
        for result in results:
            if result == best_result:
                continue
                
            for key, value in result.items():
                if value is not None and (merged.get(key) is None or len(str(value)) > len(str(merged.get(key, '')))):
                    merged[key] = value
        
        return merged
    
    def get_confidence_score(self, text: str) -> float:
        """
        Calculate confidence score for extracted text.
        Higher score means more reliable extraction.
        """
        if not text:
            return 0.0
        
        score = 0.0
        
        # Length bonus (longer text is usually better)
        score += min(len(text) / 1000, 0.3)
        
        # Structure bonus (presence of key elements)
        key_indicators = ['celkem', 'total', 'dph', 'vat', 'datum', 'date', 'kč', 'czk']
        for indicator in key_indicators:
            if indicator.lower() in text.lower():
                score += 0.1
        
        # Format consistency bonus
        lines = text.split('\n')
        if len(lines) > 5:  # Multiple lines suggest good structure
            score += 0.2
        
        # Czech character bonus (indicates good OCR for Czech invoices)
        czech_chars = 'áčďéěíňóřšťúůýž'
        czech_count = sum(1 for char in text if char.lower() in czech_chars)
        if czech_count > 0:
            score += min(czech_count / 100, 0.2)
        
        return min(score, 1.0)

# Global instance
format_manager = FormatManager()

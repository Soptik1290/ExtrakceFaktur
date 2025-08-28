from typing import Dict, List, Optional
from .heuristics import extract_fields_heuristic
from .llm import extract_fields_llm, llm_available
from .templates import extract_fields_template
from .format_manager import format_manager
from .ocr import extract_text_dual_format, get_extraction_confidence
import logging

logger = logging.getLogger(__name__)

class DualExtractor:
    """
    Extracts invoice fields using both original and converted formats.
    Combines results for better accuracy and consistency.
    """
    
    def __init__(self):
        self.extraction_methods = ['template', 'llm', 'heuristic']
    
    def extract_with_method(self, text: str, method: str) -> Optional[Dict]:
        """Extract fields using a specific method."""
        try:
            if method == 'template':
                return extract_fields_template(text)
            elif method == 'llm' and llm_available():
                return extract_fields_llm(text)
            elif method == 'heuristic':
                return extract_fields_heuristic(text)
        except Exception as e:
            logger.warning(f"Extraction with {method} failed: {e}")
            return None
        return None
    
    def extract_fields_dual_format(self, filename: str, data: bytes, 
                                 preferred_method: str = "auto") -> Dict:
        """
        Extract fields using both original and converted formats.
        Combines results for better accuracy.
        """
        # Get text from both formats
        dual_text = extract_text_dual_format(filename, data)
        original_text = dual_text['original']
        converted_text = dual_text['converted']
        file_format = dual_text['format']
        
        logger.info(f"Processing {filename} (format: {file_format})")
        logger.info(f"Original text length: {len(original_text)}")
        logger.info(f"Converted text length: {len(converted_text)}")
        
        # Extract fields from both texts using all methods
        all_results = []
        
        # Process original text
        if original_text:
            for method in self.extraction_methods:
                if preferred_method != "auto" and method != preferred_method:
                    continue
                    
                result = self.extract_with_method(original_text, method)
                if result:
                    result['_source'] = f"{method}_original"
                    result['_confidence'] = get_extraction_confidence(filename, data)
                    result['_format'] = file_format
                    all_results.append(result)
        
        # Process converted text
        if converted_text:
            for method in self.extraction_methods:
                if preferred_method != "auto" and method != preferred_method:
                    continue
                    
                result = self.extract_with_method(converted_text, method)
                if result:
                    result['_source'] = f"{method}_converted"
                    result['_confidence'] = get_extraction_confidence(filename, data)
                    result['_format'] = f"{file_format}_converted"
                    all_results.append(result)
        
        # Combine results
        if not all_results:
            logger.warning("No extraction results found")
            return {
                '_source': 'none',
                '_confidence': 0.0,
                '_format': file_format,
                '_error': 'No extraction results'
            }
        
        # Combine all results for best accuracy
        combined_result = self.combine_all_results(all_results)
        
        # Add metadata
        combined_result['_source'] = 'dual_format_combined'
        combined_result['_confidence'] = self.calculate_combined_confidence(all_results)
        combined_result['_format'] = file_format
        combined_result['_methods_used'] = [r['_source'] for r in all_results]
        combined_result['_total_results'] = len(all_results)
        
        logger.info(f"Combined {len(all_results)} extraction results")
        return combined_result
    
    def combine_all_results(self, results: List[Dict]) -> Dict:
        """
        Intelligently combine multiple extraction results.
        Prioritizes non-None values and merges complementary information.
        """
        if not results:
            return {}
        
        if len(results) == 1:
            return results[0].copy()
        
        # Find the most complete result as base
        best_result = max(results, key=lambda x: self.calculate_completeness(x))
        combined = best_result.copy()
        
        # Remove metadata fields for processing
        metadata_fields = ['_source', '_confidence', '_format', '_error']
        for field in metadata_fields:
            combined.pop(field, None)
        
        # Merge complementary information from other results
        for result in results:
            if result == best_result:
                continue
            
            for key, value in result.items():
                if key.startswith('_'):
                    continue
                    
                if value is not None:
                    current_value = combined.get(key)
                    
                    # Choose the better value
                    if current_value is None:
                        combined[key] = value
                    elif isinstance(value, (int, float)) and isinstance(current_value, (int, float)):
                        # For numbers, prefer the larger one (likely more complete)
                        if value > current_value:
                            combined[key] = value
                    elif isinstance(value, str) and isinstance(current_value, str):
                        # For strings, prefer the longer one (likely more complete)
                        if len(value) > len(current_value):
                            combined[key] = value
        
        return combined
    
    def calculate_completeness(self, result: Dict) -> int:
        """Calculate how complete a result is (more non-None values = higher score)."""
        if not result:
            return 0
        
        score = 0
        for key, value in result.items():
            if not key.startswith('_') and value is not None:
                score += 1
        return score
    
    def calculate_combined_confidence(self, results: List[Dict]) -> float:
        """Calculate overall confidence based on all results."""
        if not results:
            return 0.0
        
        total_confidence = sum(r.get('_confidence', 0.0) for r in results)
        return min(total_confidence / len(results), 1.0)

# Global instance
dual_extractor = DualExtractor()

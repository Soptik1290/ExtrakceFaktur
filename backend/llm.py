import os, re
from typing import Dict, Any

def llm_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def ask_llm(ocr_text: str) -> Dict[str, Any]:
    """
    Safe-by-default: pokud není OPENAI_API_KEY, vrať prázdný dict.
    Když klíč je, pošli přísný prompt: pouze substringy ze vstupu.
    (Implementaci volání necháváme jednoduchou – můžeš ji napojit na svůj klient.)
    """
    if not llm_available() or not ocr_text or len(ocr_text.strip()) < 10:
        return {}

    # Zde jen skeleton; doporučeno použít JSON mode / function calling.
    # Výstup tvého LLM klienta mapuj na stejný JSON jako heuristiky.
    return {}  # placeholder

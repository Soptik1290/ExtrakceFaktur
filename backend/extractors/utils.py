# -*- coding: utf-8 -*-
"""
Utilities for parsing and normalizing monetary amounts from noisy strings.
"""
from __future__ import annotations

import re
from typing import Optional

_SPACE_NORM_RE = re.compile(r"(?:\s|[\u00A0\u2000-\u200B\u202F])+", re.UNICODE)
_CURRENCY_RE = re.compile(r"(Kč|CZK|EUR|USD|GBP|PLN|HUF|CHF|SEK|NOK|DKK|JPY|CNY|AUD|CAD|[€$£¥₤₺₽₨₿])", re.IGNORECASE)

def normalize_spaces(s: str) -> str:
    """Collapse all space-like characters (incl. NBSP/thin spaces) to a single ASCII space."""
    return _SPACE_NORM_RE.sub(" ", s)

def strip_currency(s: str) -> str:
    """Remove common currency codes/symbols; keep digits, signs, separators and spaces."""
    s = _CURRENCY_RE.sub("", s)
    s = s.strip()
    s = re.sub(r"[^0-9,.\-\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def normalize_date(date_str) -> Optional[str]:
    """
    Normalize date string to YYYY-MM-DD format.
    Handles various date formats commonly found in invoices.
    """
    if not date_str:
        return None
    
    if isinstance(date_str, str):
        date_str = date_str.strip()
        if not date_str:
            return None
        
        # Try different date patterns
        patterns = [
            r"(\d{1,2})[./](\d{1,2})[./](\d{4})",  # DD/MM/YYYY or DD.MM.YYYY
            r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})",  # YYYY/MM/DD
            r"(\d{1,2})[./](\d{1,2})[./](\d{2})",  # DD/MM/YY or DD.MM.YY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                if len(match.group(1)) == 4:  # YYYY format
                    year, month, day = match.groups()
                elif len(match.group(3)) == 4:  # DD/MM/YYYY format
                    day, month, year = match.groups()
                else:  # DD/MM/YY format
                    day, month, year = match.groups()
                    year = "20" + year if int(year) < 50 else "19" + year
                
                # Ensure proper formatting
                try:
                    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
                except ValueError:
                    continue
    
    return None

def detect_currency(text: str) -> Optional[str]:
    """
    Detect currency from text.
    Returns the most common currency found or None.
    """
    if not text:
        return None
    
    # Find all currency matches
    matches = _CURRENCY_RE.findall(text)
    if not matches:
        return None
    
    # Count occurrences and return the most common
    from collections import Counter
    counter = Counter(matches)
    most_common = counter.most_common(1)
    
    if most_common:
        currency = most_common[0][0]
        # Normalize common currency codes
        currency_map = {
            "Kč": "CZK",
            "€": "EUR",
            "$": "USD",
            "£": "GBP",
        }
        return currency_map.get(currency, currency)
    
    return None

def parse_amount(s) -> Optional[float]:
    """
    Parse amount from messy OCR text like:
        '4  4 413,00 Kč', '44.413,00', '44 413 Kč', '44,413.00 CZK', '1,234.56', '1.234,56'
    Returns float or None.
    """
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)

    s = str(s).strip()
    if not s:
        return None

    # 1) Normalize whitespace (including NBSP/thin spaces)
    s = normalize_spaces(s)

    # 2) Remove currency tokens and keep only numeric context
    s = strip_currency(s)

    if not re.search(r"\d", s):
        return None

    # 3) Decide decimal separator based on the last occurrence of comma/dot
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")
    decimal = None
    if last_comma != -1 and last_dot != -1:
        decimal = "," if last_comma > last_dot else "."
    elif last_comma != -1:
        decimal = ","
    elif last_dot != -1:
        decimal = "."

    # 4) Remove thousands and keep only a single decimal separator
    if decimal == ",":
        t = s.replace(".", "")        # dots likely thousands
        t = re.sub(r"\s+", "", t)     # spaces as thousands
        t = t.replace(",", ".")       # comma becomes decimal
    elif decimal == ".":
        t = s.replace(",", "")        # commas likely thousands
        t = re.sub(r"\s+", "", t)
        # dot stays decimal
    else:
        # No clear decimal sign → treat as integer without thousands
        t = re.sub(r"\D", "", s)

    # 5) Extract final -?\d+(\.\d+)? token; use the last one (most specific / rightmost)
    m = re.findall(r"-?\d+(?:\.\d+)?", t)
    if not m:
        return None
    try:
        return float(m[-1])
    except Exception:
        return None

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

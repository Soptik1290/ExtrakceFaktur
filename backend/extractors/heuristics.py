# -*- coding: utf-8 -*-
"""
Heuristic extractors for monetary amounts from noisy OCR/text layers of invoices.
This module is template-free and focuses on robust pattern matching + normalization.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple

# NOTE:
#  - We tolerate various spaces (regular, NBSP, thin spaces), and even multiple spaces
#    between fragmented thousand groups coming from PDF text extraction or OCR.
#  - We also accept groups of 1–3 digits after the first group to handle "broken"
#    thousands like '4  4 413,00' where kerning created a split.
#
# Examples matched:
#   "44 413,00 Kč", "4  4 413,00 Kč", "44.413,00", "44,413.00", "44 413 Kč", "44113.00"
#
# The decimal part is optional in the first branch because invoices sometimes show
# integers with currency (e.g., "44 413 Kč"). A second branch catches plain 123,45/123.45.
AMOUNT_PAT_STRICT = (
    r"\b\d{1,3}(?:[\s\u00A0\u2000-\u200B\u202F]+?\d{1,3})+(?:[,.]\d{2})?\b"
    r"|\b\d+[,.]\d{2}\b"
)

# Common keywords signaling the final amount ("total due" etc.)
DEFAULT_TOTAL_KEYWORDS = [
    "celkem k úhradě",
    "k úhradě",
    "celkem",
    "total due",
    "amount due",
    "grand total",
    "amount payable",
    "balance due",
    "sum to pay",
]

_CURRENCY_RE = re.compile(r"(Kč|CZK|EUR|USD|GBP|PLN|HUF|CHF|SEK|NOK|DKK|JPY|CNY|AUD|CAD|[€$£¥₤₺₽₨₿])", re.IGNORECASE)
_SPACE_NORM_RE = re.compile(r"(?:\s|[\u00A0\u2000-\u200B\u202F])+", re.UNICODE)

def _normalize_text(s: str) -> str:
    """Normalize text for scanning: collapse exotic spaces, lower for keyword search."""
    s = _SPACE_NORM_RE.sub(" ", s)
    return s

def iter_amount_spans(text: str, pattern: str = AMOUNT_PAT_STRICT) -> Iterable[Tuple[int, int, str]]:
    """
    Yield (start, end, matched_text) for all amount-like tokens in the given text.
    """
    for m in re.finditer(pattern, text, flags=re.UNICODE):
        yield m.start(), m.end(), m.group(0)

def extract_amount_candidates(text: str, pattern: str = AMOUNT_PAT_STRICT) -> List[str]:
    """Return all raw amount strings found in text."""
    return [m for _, _, m in iter_amount_spans(text, pattern)]

def window_candidates_around_keywords(text: str,
                                      keywords: Iterable[str] = DEFAULT_TOTAL_KEYWORDS,
                                      window_chars: int = 220) -> List[str]:
    """
    Collect amount candidates that appear within ±window_chars around any of the keywords.
    """
    if not text:
        return []
    normalized = _normalize_text(text)
    raw = text  # keep original indices

    # Build simple lower-cased search for keywords to find windows
    low = normalized.lower()
    idxs: List[Tuple[int, int]] = []
    for kw in keywords:
        pos = 0
        kw_low = kw.lower()
        while True:
            i = low.find(kw_low, pos)
            if i == -1:
                break
            start = max(0, i - window_chars)
            end = min(len(raw), i + len(kw_low) + window_chars)
            idxs.append((start, end))
            pos = i + len(kw_low)

    # Deduplicate and merge overlapping windows
    idxs.sort()
    merged: List[Tuple[int, int]] = []
    for s, e in idxs:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))

    # Collect candidates inside windows
    cands: List[str] = []
    for s, e in merged:
        segment = raw[s:e]
        cands.extend(extract_amount_candidates(segment))

    return cands

def choose_best_total_candidate(candidates: List[str]) -> Optional[str]:
    """
    A simple heuristic to choose the 'best' total:
      - prefer candidates with currency symbol/code present in original snippet
      - otherwise prefer the numerically largest value (common for TOTAL vs line items)
    """
    from .utils import parse_amount  # local import to avoid circular deps

    if not candidates:
        return None

    # Score by (has_currency, numeric_value)
    best = None
    best_score = (-1, float("-inf"))  # type: ignore

    for c in candidates:
        has_curr = 1 if _CURRENCY_RE.search(c) else 0
        val = parse_amount(c)
        val = val if val is not None else float("-inf")
        score = (has_curr, float(val))
        if score > best_score:
            best_score = score
            best = c

    return best

def extract_total_amount(text: str,
                         keywords: Iterable[str] = DEFAULT_TOTAL_KEYWORDS,
                         fallback_pick_max: bool = True) -> Optional[float]:
    """
    High-level helper:
      1) Look near likely 'total' keywords and pick best candidate.
      2) If nothing near keywords, optionally fall back to the maximum amount in the whole text.
    Returns a float in standard dotted-decimal (e.g., 44413.00) or None.
    """
    from .utils import parse_amount  # local import to avoid circular deps

    # First pass: around keywords
    cands = window_candidates_around_keywords(text, keywords=keywords, window_chars=220)
    best = choose_best_total_candidate(cands)
    if best is not None:
        return parse_amount(best)

    # Fallback: pick the largest amount in the entire document
    if fallback_pick_max:
        all_cands = extract_amount_candidates(text)
        # parse & choose max
        parsed = [(c, parse_amount(c)) for c in all_cands]
        parsed = [p for p in parsed if p[1] is not None]
        if parsed:
            return max(parsed, key=lambda x: x[1])[1]

    return None

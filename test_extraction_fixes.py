#!/usr/bin/env python3
"""
Testovací skript pro ověření oprav v extrakci faktur
"""

import sys
import os
sys.path.append('backend')

from extractors.utils import parse_amount, detect_currency
from extractors.validate import _is_vs, _ico_checksum, _dic_valid

def test_parse_amount():
    """Testuje funkci parse_amount"""
    print("=== Test parse_amount ===")
    
    test_cases = [
        ("44 413,00", 44413.0),
        ("44 413", 44413.0),
        ("2 499,00", 2499.0),
        ("7 986,00", 7986.0),
        ("65 000,00", 65000.0),
        ("2 548,00", 2548.0),
        ("1 100,00", 1100.0),
        ("5 500,00", 5500.0),
        ("8 000,00", 8000.0),
        ("27 500,00", 27500.0),
        ("9 000,00", 9000.0),
        ("7 000,00", 7000.0),
        ("13 500,00", 13500.0),
    ]
    
    for input_val, expected in test_cases:
        result = parse_amount(input_val)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{input_val}' -> {result} (očekáváno: {expected})")

def test_detect_currency():
    """Testuje funkci detect_currency"""
    print("\n=== Test detect_currency ===")
    
    test_cases = [
        ("Kč", "CZK"),
        ("CZK", "CZK"),
        ("EUR", "EUR"),
        ("€", "EUR"),
        ("USD", "USD"),
        ("$", "USD"),
    ]
    
    for input_val, expected in test_cases:
        result = detect_currency(input_val)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{input_val}' -> {result} (očekáváno: {expected})")

def test_validation():
    """Testuje validační funkce"""
    print("\n=== Test validace ===")
    
    # Test variabilního symbolu
    print("Variabilní symbol:")
    test_vs = ["2023006", "VS2023006", "Variabilní symbol: 2023006", "123", "1234567890123"]
    for vs in test_vs:
        result = _is_vs(vs)
        print(f"  {vs}: {result}")
    
    # Test IČO
    print("\nIČO:")
    test_ico = ["8666666", "75384902", "27082440", "26354764", "12345678", "1234567"]
    for ico in test_ico:
        result = _ico_checksum(ico)
        print(f"  {ico}: {result}")
    
    # Test DIČ
    print("\nDIČ:")
    test_dic = ["CZ26354764", "CZ75384902", "CZ27082440", "CZ12345678", "CZ123456789", "12345678"]
    for dic in test_dic:
        result = _dic_valid(dic)
        print(f"  {dic}: {result}")

def test_real_invoice_data():
    """Testuje reálná data z faktur"""
    print("\n=== Test reálných dat z faktur ===")
    
    # Data z první faktury
    print("Faktura 1 (PhDr. Jan Novák):")
    print(f"  Částka s DPH: {parse_amount('44 413,00')}")
    print(f"  Měna: {detect_currency('Kč')}")
    print(f"  IČO: {_ico_checksum('8666666')}")
    print(f"  DIČ: {_dic_valid('CZ26354764')}")
    
    # Data z druhé faktury
    print("\nFaktura 2 (CreativeSpark):")
    print(f"  Částka bez DPH: {parse_amount('65 000,00')}")
    print(f"  Měna: {detect_currency('Kč')}")
    print(f"  IČO: {_ico_checksum('75384902')}")
    print(f"  DIČ: {_dic_valid('CZ75384902')}")

if __name__ == "__main__":
    test_parse_amount()
    test_detect_currency()
    test_validation()
    test_real_invoice_data()
    print("\n=== Test dokončen ===")

#!/usr/bin/env python3
"""
Test pro detailní ověření IČO validace
"""

import sys
import os
sys.path.append('backend')

from extractors.validate import _ico_checksum

def test_ico_validation():
    """Testuje IČO validaci detailně"""
    print("=== Detailní test IČO validace ===")
    
    test_icos = [
        ("8666666", "PhDr. Jan Novák"),
        ("75384902", "CreativeSpark Design"),
        ("27082440", "Alza.cz"),
        ("26354764", "Modul Servis"),
    ]
    
    for ico, description in test_icos:
        print(f"\nIČO: {ico} ({description})")
        
        # Clean ICO
        cleaned = ico.replace(" ", "").replace("-", "")
        print(f"  Vyčištěné: {cleaned}")
        
        # Check length
        if len(cleaned) == 8:
            print(f"  Délka: ✓ 8 znaků")
            
            # Calculate checksum
            digits = [int(x) for x in cleaned]
            print(f"  Číslice: {digits}")
            
            s = sum(digits[i] * (8 - i) for i in range(7))
            print(f"  Součet (vážený): {s}")
            
            mod = s % 11
            print(f"  Modulo 11: {mod}")
            
            if mod == 0: 
                c = 1
            elif mod == 1: 
                c = 0
            elif mod == 10: 
                c = 1
            else: 
                c = 11 - mod
            
            print(f"  Kontrolní číslice (vypočítaná): {c}")
            print(f"  Kontrolní číslice (skutečná): {digits[7]}")
            
            is_valid = digits[7] == c
            print(f"  Platné: {'✓' if is_valid else '✗'}")
            
            # Test our function
            result = _ico_checksum(ico)
            print(f"  Funkce _ico_checksum: {'✓' if result else '✗'}")
            
        else:
            print(f"  Délka: ✗ {len(cleaned)} znaků (očekáváno 8)")
            result = _ico_checksum(ico)
            print(f"  Funkce _ico_checksum: {'✓' if result else '✗'}")

if __name__ == "__main__":
    test_ico_validation()

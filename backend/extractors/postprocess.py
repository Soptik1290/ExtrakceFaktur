
from .utils import parse_amount, _correct_amount_ocr
import re

def _round2(x):
    return None if x is None else round(float(x) + 1e-9, 2)

def _fix_czech_text(text: str) -> str:
    """Opravuje běžné OCR chyby v českých textech"""
    if not text:
        return text
    
    # Slovník běžných OCR chyb v češtině
    czech_fixes = {
        # Běžné chyby v názvech bank
        'Komeréni': 'Komerční',
        'Komeréni banka': 'Komerční banka',
        'Komeréni banka, a.s.': 'Komerční banka, a.s.',
        'Komeréni': 'Komerční',
        
        # Města
        'Pizen': 'Plzeň',
        'Pizen,': 'Plzeň,',
        'Pizen.': 'Plzeň.',
        'Pizen ': 'Plzeň ',
        
        # Další běžné chyby
        'banka': 'banka',  # Oprava podle kontextu
        'a.s.': 'a.s.',
        's.r.o.': 's.r.o.',
        'v.o.s.': 'v.o.s.',
        
        # České znaky
        'é': 'é',
        'í': 'í',
        'á': 'á',
        'ě': 'ě',
        'š': 'š',
        'č': 'č',
        'ř': 'ř',
        'ž': 'ž',
        'ý': 'ý',
        'ů': 'ů',
        'ú': 'ú',
        'ó': 'ó',
    }
    
    # Aplikuj opravy
    for wrong, correct in czech_fixes.items():
        text = text.replace(wrong, correct)
    
    # Opravy pomocí regex pro složitější případy
    text = re.sub(r'\bKomeréni\b', 'Komerční', text)
    text = re.sub(r'\bPizen\b', 'Plzeň', text)
    
    return text

def _smart_amount_correction(data: dict) -> dict:
    """Inteligentní korekce částek s OCR opravami"""
    if not isinstance(data, dict):
        return data or {}
    
    # Zkus najít a opravit chybné částky
    amounts = []
    for key in ["castka_bez_dph", "dph", "castka_s_dph"]:
        val = data.get(key)
        if val is not None:
            amounts.append((key, val))
    
    # Pokud máme podezřele malé částky, zkus je opravit
    for key, val in amounts:
        if isinstance(val, (int, float)) and val < 10000:  # Podezřele malá částka
            # Zkus najít větší částku v textu nebo opravit OCR chyby
            corrected = _try_fix_small_amount(val, data)
            if corrected and corrected != val:
                data[key] = corrected
                if "_computed" not in data:
                    data["_computed"] = {}
                data["_computed"][f"{key}_corrected"] = True
    
    return data

def _try_fix_small_amount(amount: float, data: dict) -> float:
    """Zkusí opravit podezřele malou částku"""
    # Pokud je částka 4-5 číslic, může být OCR chyba
    if 1000 <= amount < 100000:
        # Zkus najít větší částku v jiných polích
        for key in ["castka_bez_dph", "dph", "castka_s_dph"]:
            other_val = data.get(key)
            if other_val and isinstance(other_val, (int, float)) and other_val > amount * 10:
                # Našli jsme mnohem větší částku - možná je ta malá chybná
                return other_val
    
    return amount

def _fix_text_fields(data: dict) -> dict:
    """Opravuje české texty v datech"""
    if not isinstance(data, dict):
        return data or {}
    
    # Oprav dodavatele
    supplier = data.get("dodavatel", {})
    if isinstance(supplier, dict):
        for key in ["nazev", "adresa"]:
            if supplier.get(key):
                supplier[key] = _fix_czech_text(str(supplier[key]))
    
    # Oprav další textová pole
    text_fields = ["banka_prijemce", "platba_zpusob", "mena"]
    for field in text_fields:
        if data.get(field):
            data[field] = _fix_czech_text(str(data[field]))
    
    return data

def autofill_amounts(data: dict) -> dict:
    """
    Fill missing DPH/bezDPH/sDPH if dvě ze tří hodnot známe.
    Přidá klíč _computed s příznaky, co bylo dopočítáno.
    """
    if not isinstance(data, dict):
        return data or {}

    # Nejdříve zkus opravit chybné částky
    data = _smart_amount_correction(data)
    
    # Oprav české texty
    data = _fix_text_fields(data)

    bez = parse_amount(data.get("castka_bez_dph"))
    dph = parse_amount(data.get("dph"))
    sdp = parse_amount(data.get("castka_s_dph"))

    computed = {"castka_bez_dph": False, "dph": False, "castka_s_dph": False}

    # 1) Bez + S → DPH
    if bez is not None and sdp is not None and dph is None:
        dph = _round2(sdp - bez)
        if dph is not None and dph < 0 and abs(dph) < 0.03:
            dph = 0.0
        computed["dph"] = True

    # 2) S − DPH → Bez
    if sdp is not None and dph is not None and bez is None:
        bez = _round2(sdp - dph)
        computed["castka_bez_dph"] = True

    # 3) Bez + DPH → S
    if bez is not None and dph is not None and sdp is None:
        sdp = _round2(bez + dph)
        computed["castka_s_dph"] = True

    if bez is not None:
        data["castka_bez_dph"] = _round2(bez)
    if dph is not None:
        data["dph"] = _round2(dph)
    if sdp is not None:
        data["castka_s_dph"] = _round2(sdp)

    if any(computed.values()):
        data["_computed"] = computed

    return data

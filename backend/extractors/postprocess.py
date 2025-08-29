
from .utils import parse_amount

def _round2(x):
    return None if x is None else round(float(x) + 1e-9, 2)

def autofill_amounts(data: dict) -> dict:
    """
    Fill missing DPH/bezDPH/sDPH if dvě ze tří hodnot známe.
    Přidá klíč _computed s příznaky, co bylo dopočítáno.
    """
    if not isinstance(data, dict):
        return data or {}

    bez = parse_amount(data.get("castka_bez_dph"))
    dph = parse_amount(data.get("dph"))
    sdp = parse_amount(data.get("castka_s_dph"))

    computed = {"castka_bez_dph": False, "dph": False, "castka_s_dph": False}

    # 1) Bez + S → DPH
    if bez is not None and sdp is not None and dph is None:
        dph = _round2(sdp - bez)
        if dph is not None and dph < 0 and abs(dph) < 0.03:
            dph = 0.0
        
        # Special case: if bez_dph == s_dph, this suggests VAT-exempt invoice
        if bez is not None and sdp is not None and abs(float(bez) - float(sdp)) < 0.01:
            dph = None  # Don't compute DPH for VAT-exempt invoices
        else:
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

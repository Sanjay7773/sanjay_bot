# --------------------------------------------
# Strike selection logic (ATM / OTM)
# --------------------------------------------
# strike_logic.py

STEP = 50      # NIFTY strike gap (50 points)
MAX_OTM_STEPS = 1   # default: ATM ya 1 step OTM


def round_to_strike(spot_price: float) -> int:
    """
    NIFTY spot ko nearest 50 point strike par round karta hai.
    Example: 25915 -> 25900, 25926 -> 25950
    """
    return int(round(spot_price / STEP) * STEP)


def choose_call_put_strike(spot_price: float, trend: str = "normal") -> dict:
    """
    Trend ke hisab se ATM / OTM strike choose karta hai.

    trend:
      - "normal"       -> ATM
      - "strong_up"    -> CE = ATM + 50
      - "strong_down"  -> PE = ATM - 50
    """
    atm = round_to_strike(spot_price)

    ce = atm
    pe = atm

    if trend == "strong_up":
        ce = atm + STEP
    elif trend == "strong_down":
        pe = atm - STEP

    return {
        "atm": atm,
        "ce_strike": ce,
        "pe_strike": pe
    }


# -------------------------------------------------------
# NEW FUNCTION (Required by bot_core.py)
# -------------------------------------------------------
def get_option_symbol(direction: str, spot_price: float, trend: str = "normal") -> str:
    """
    Final tradingsymbol text return karta hai.
    Example: CE -> NIFTY25900CE
             PE -> NIFTY25950PE
    """
    strikes = choose_call_put_strike(spot_price, trend)

    if direction.upper() == "CE":
        strike = strikes["ce_strike"]
        return f"NIFTY{strike}CE"
    else:
        strike = strikes["pe_strike"]
        return f"NIFTY{strike}PE"


# -------------------------------------------------------
# Local Test
# -------------------------------------------------------
if __name__ == "__main__":
    test_price = 25915
    print("Spot:", test_price)
    print("Normal trend:", choose_call_put_strike(test_price, "normal"))
    print("Strong UP:", choose_call_put_strike(test_price, "strong_up"))
    print("Strong DOWN:", choose_call_put_strike(test_price, "strong_down"))

    print("CE Symbol:", get_option_symbol("CE", test_price))
    print("PE Symbol:", get_option_symbol("PE", test_price))

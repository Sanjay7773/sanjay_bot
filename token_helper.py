# token_helper.py
from SmartApi import SmartConnect

def get_latest_future_token(api: SmartConnect, symbol="NIFTY"):
    all_data = api.searchScrip(exchange="NFO", searchtext=symbol)

    # FUTURES filter karo
    futs = [x for x in all_data['data'] if x["symbol"].endswith("FUT")]

    # Latest expiry wala FUTURE choose kar lo
    latest = sorted(futs, key=lambda x: x["expiry"]) [0]

    return latest["token"]

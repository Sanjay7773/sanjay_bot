from SmartApi import SmartConnect
import pyotp
# py ltp_test.py
# ok
API_KEY = "TUnreERc"
CLIENT_CODE = "S1520958"
MPIN = "1709"
TOTP_SECRET = "FU33K44BL2PHQTFUQ4WBPBXB6U======"

totp = pyotp.TOTP(TOTP_SECRET).now()

obj = SmartConnect(api_key=API_KEY)
session = obj.generateSession(CLIENT_CODE, MPIN, totp)

print("Login Success!")

def get_ltp(exchange, symbol, token):
    data = obj.ltpData(exchange, symbol, token)
    return data["data"]["ltp"]

print("NIFTY LTP =", get_ltp("NSE", "NIFTY", "26000"))

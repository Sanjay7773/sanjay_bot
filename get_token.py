from SmartApi import SmartConnect
import pyotp

# py get_token.py

API_KEY = "TUnreERc "
CLIENT_CODE = "S1520958"
PIN = "1709"
TOTP_SECRET = "FU33K44BL2PHQTFUQ4WBPBXB6U======"   # QR scan se mila hua secret key yaha aayega
smart = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()

data = smart.generateSession(CLIENT_CODE, PIN, totp)
feedToken = data['data']['feedToken']

# Fetch NIFTY spot token
instruments = smart.searchScrip("NSE", "NIFTY")

print(instruments)

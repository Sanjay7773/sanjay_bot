from SmartApi import SmartConnect
import pyotp
# py login_test.py
# Generated TOTP ok
# ----------------------------------------
# USER INPUT
# ----------------------------------------
API_KEY = "TUnreERc"
CLIENT_CODE = "S1520958"
MPIN = "1709"
TOTP_SECRET = "FU33K44BL2PHQTFUQ4WBPBXB6U======"
# ----------------------------------------
# TOTP generate
# ----------------------------------------
totp = pyotp.TOTP(TOTP_SECRET).now()
print("Generated TOTP:", totp)

# ----------------------------------------
# SmartAPI session create
# ----------------------------------------
obj = SmartConnect(api_key=API_KEY)

try:
    data = obj.generateSession(CLIENT_CODE, MPIN, totp)
    print("Login Success:", data)
except Exception as e:
    print("Login Failed:", e)

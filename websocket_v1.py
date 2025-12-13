# ------------------------------------------------------------
# websocket_v1.py  (FINAL STABLE)
# Sends real-time ticks to bot_core.bot
# ------------------------------------------------------------

from SmartApi import SmartConnect
from SmartApi.smartWebSocketV1 import SmartWebSocket

import pyotp, json
from bot_core import bot   # <-- GLOBAL BOT IMPORT
from token_helper import get_latest_future_token
# ------------------------------------------------------------
# LOGIN DETAILS
# ------------------------------------------------------------

API_KEY = "TUnreERc"
CLIENT_CODE = "S1520958"
MPIN = "1709"
TOTP_SECRET = "FU33K44BL2PHQTFUQ4WBPBXB6U======"

# Generate fresh 6-digit TOTP
totp = pyotp.TOTP(TOTP_SECRET).now()

# Login
obj = SmartConnect(api_key=API_KEY)
session = obj.generateSession(CLIENT_CODE, MPIN, totp)

feed_token = session["data"]["feedToken"]
client_code = session["data"]["clientcode"]

print("🔥 LOGIN SUCCESS — WebSocket V1")
print("Feed Token:", feed_token)


# ------------------------------------------------------------
# CALLBACKS
# ------------------------------------------------------------

def on_message(ws, message):
    """Angel V1 WS sends JSON string → convert → send to bot"""
    try:
        tick = json.loads(message)
        bot.on_ws_tick(tick)
        print("🔥 TICK → BOT:", tick)
    except Exception as e:
        print("Parse Error:", e)


def on_open(ws):
    print("🟢 WS Connected — Subscribing FUTURE tick...")

    fut_token = get_latest_future_token(obj)   # auto latest future token

    ws.subscribe([
        {
            "exchangeType": 2,   # 2 = NFO
            "tokens": [ int(fut_token) ]
        }
    ])

    print(f"📡 Subscribed → NFO | {fut_token} (NIFTY FUT AUTO)")

    

def on_error(ws, error):
    print("⚠️ ERROR:", error)


def on_close(ws):
    print("🔴 WS CLOSED")


# ------------------------------------------------------------
# INITIALIZE SOCKET
# ------------------------------------------------------------

ws = SmartWebSocket(
    api_key=API_KEY,
    client_code=client_code,
    feed_token=feed_token
)

ws.on_open = on_open
ws.on_message = on_message
ws.on_error = on_error
ws.on_close = on_close


# ------------------------------------------------------------
# CONNECT
# ------------------------------------------------------------
print("⏳ Connecting WebSocket V1...")
ws.connect()

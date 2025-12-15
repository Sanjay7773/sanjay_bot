# ============================================================
# bot_core.py
# FINAL – MSTOCK MARKET DATA WS (NIFTY + BANKNIFTY)
# ============================================================

from __future__ import annotations
from typing import Dict, Optional
import time
import json
import pyotp
from websocket import WebSocketApp

# ===== YOUR EXISTING FILES (UNCHANGED) =====
from rules_engine import RulesEngine, RuleConfig, MarketContext
from data_feed_handler import DataFeedHandler
from risk_manager import RiskManager, RiskManagerConfig, PositionState
from order_manager import OrderManager
from strike_logic import get_option_symbol


# ============================================================
# 1️⃣ CONFIG – WHAT YOU WANT TO RUN
# ============================================================

class BotConfig:
    def __init__(self):
        # "NIFTY" or "BANKNIFTY"
        self.index_symbol = "NIFTY"
        self.timeframe_minutes = 5
        self.lot_size = 50
        self.max_lots_per_trade = 1
        self.paper_trade = True


# ============================================================
# 2️⃣ BOT ENGINE (NO BROKER CODE HERE)
# ============================================================

class OptionBot:

    def __init__(self, api, config: BotConfig):
        self.api = api
        self.cfg = config

        self.rules_engine = RulesEngine(RuleConfig())
        self.data_handler = DataFeedHandler(self.cfg.timeframe_minutes)
        self.risk_manager = RiskManager(RiskManagerConfig())
        self.order_manager = OrderManager(api)

        self.position: Optional[PositionState] = None
        print("[BOT] READY")

    def on_tick(self, tick: Dict):
        self.data_handler.ws_callback(tick)

        context = self.data_handler.build_market_context(
            symbol=self.cfg.index_symbol
        )
        if not context:
            return

        if self.position and self.position.is_open:
            self._manage_position(context)
        else:
            self._check_entry(context)

    def _check_entry(self, context: MarketContext):
        if not self.risk_manager.can_take_trade():
            return

        decision = self.rules_engine.evaluate(context)
        if not decision.should_enter:
            return

        direction = decision.direction
        index_price = context.candles[-1].c

        option_symbol = get_option_symbol(
            direction=direction,
            underlying_price=index_price,
            index_name=self.cfg.index_symbol
        )

        option_ltp = self.api.get_option_ltp(option_symbol)

        print(f"[ENTRY] {direction} {option_symbol} @ {option_ltp}")

        self.position = self.risk_manager.create_position(
            symbol=option_symbol,
            direction=direction,
            entry_price=option_ltp,
            qty=self.cfg.lot_size * self.cfg.max_lots_per_trade
        )

    def _manage_position(self, context: MarketContext):
        option_ltp = self.api.get_option_ltp(self.position.symbol)

        self.risk_manager.update_trailing_sl(option_ltp)
        exit_signal = self.risk_manager.check_exit(option_ltp)

        if exit_signal:
            pnl = self.risk_manager.close_position(option_ltp)
            print(f"[EXIT] {exit_signal} | PnL={pnl}")
            self.position = None


# ============================================================
# 3️⃣ MSTOCK CLIENT (LOGIN + WS DATA)
# ============================================================

class MStockClient:

    def __init__(self, api_key, client_id, password, totp_secret):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        self.access_token = None

    def login(self):
        totp = pyotp.TOTP(self.totp_secret).now()
        print("[mStock] AUTO-TOTP:", totp)

        # 🔴 REAL LOGIN API CALL HOGA (Tumhare docs ke hisaab se)
        # response = ...
        # self.access_token = response["access_token"]


        self.access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...."
        print("[mStock] Login OK")

    def get_option_ltp(self, option_symbol: str) -> float:
        # 🔴 REAL REST OPTION LTP API HOGA
        # abhi placeholder
        return 0.0


# ============================================================
# 4️⃣ 🔐 FILL YOUR DETAILS HERE (ONLY PLACE)
# ============================================================

MSTOCK_API_KEY   = "l0MD9VRNBjoeV+8VvES0Ew=="
CLIENT_ID        = "MA13217"
PASSWORD         = "Ma@13217"

# 🔥 MUST BE BASE32 (A–Z + 2–7)
TOTP_SECRET      = "PORENNG2PEYBSCO5GUL26KVBE73XNULB"

# ============================================================
# 5️⃣ MARKET DATA WEBSOCKET URL
# ============================================================

MSTOCK_WS_URL = (
    "wss://ws.mstock.trade"
    f"?API_KEY={MSTOCK_API_KEY}"
    f"&ACCESS_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...."
)



# ============================================================
# 6️⃣ WS CALLBACKS (ONLY INDEX DATA)
# ============================================================

def ws_on_open(ws):
    print("🟢 WS CONNECTED")

    subscribe_msg = {
        "action": "subscribe",
        "mode": "LTP",
        "instruments": [
            {
                "exchange": "NSE",
                "symbol": bot.cfg.index_symbol
            }
        ]
    }

    ws.send(json.dumps(subscribe_msg))
    print(f"📡 Subscribed to {bot.cfg.index_symbol}")


def ws_on_message(ws, message):
    data = json.loads(message)

    if "ltp" in data:
        tick = {
            "last_traded_price": float(data["ltp"]),
            "timestamp": int(time.time()),
            "exchange_timestamp": int(time.time())
        }
        bot.on_tick(tick)


def ws_on_error(ws, error):
    print("❌ WS ERROR:", error)


def ws_on_close(ws, close_status_code, close_msg):
    print(f"🔴 WS CLOSED | code={close_status_code} msg={close_msg}")



# ============================================================
# 7️⃣ MAIN
# ============================================================

if __name__ == "__main__":

    cfg = BotConfig()                 # NIFTY / BANKNIFTY yahin change
    api = MStockClient(
        api_key=MSTOCK_API_KEY,
        client_id=CLIENT_ID,
        password=PASSWORD,
        totp_secret=TOTP_SECRET
    )

    api.login()

    bot = OptionBot(api, cfg)

    print("🚀 BOT STARTED")

    ws = WebSocketApp(
        MSTOCK_WS_URL,
        on_open=ws_on_open,
        on_message=ws_on_message,
        on_error=ws_on_error,
        on_close=ws_on_close
    )

    ws.run_forever()

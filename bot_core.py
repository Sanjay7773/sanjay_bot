# ------------------------------------------------------------
# bot_core.py  (FINAL STABLE VERSION)
# ------------------------------------------------------------

from __future__ import annotations
from pyotp import TOTP

from datetime import datetime
from typing import Dict, Optional, Literal

# 🔹 Angel One SmartAPI
from SmartApi.smartConnect import SmartConnect

# 🔹 Apni files import
from rules_engine import RulesEngine, RuleConfig, MarketContext
from data_feed_handler import DataFeedHandler
from risk_manager import RiskManager, RiskManagerConfig, PositionState
from order_manager import OrderManager
from strike_logic import get_option_symbol


# ------------------------------------------------------------
# STEP 1 — Bot Config
# ------------------------------------------------------------

class BotConfig:
    def __init__(self):
        self.underlying_symbol = "NIFTY"
        self.timeframe_minutes = 5

        self.lot_size = 50
        self.max_lots_per_trade = 1

        # Start in paper trading mode
        self.paper_trade = True


# ------------------------------------------------------------
# STEP 2 — Bot ENGINE
# ------------------------------------------------------------

class NiftyOptionBot:

    def __init__(self, api: SmartConnect, config: Optional[BotConfig] = None):
        self.api = api
        self.cfg = config or BotConfig()

        self.rules_engine = RulesEngine(config=RuleConfig())
        self.data_handler = DataFeedHandler(timeframe_minutes=self.cfg.timeframe_minutes)
        self.risk_manager = RiskManager(config=RiskManagerConfig())
        self.order_manager = OrderManager(api=self.api)

        self.active_order_id: Optional[str] = None
        self.position: Optional[PositionState] = None

        print("[NiftyOptionBot] READY")


    # --------------------------------------------------------
    # WebSocket Tick Handler
    # --------------------------------------------------------
    def on_ws_tick(self, tick: Dict):

        # Push tick into candle builder
        self.data_handler.ws_callback(tick)

        # Build context (only when candles ready)
        context = self.data_handler.build_market_context(symbol=self.cfg.underlying_symbol)
        if context is None:
            return

        # Manage open trades
        self._manage_open_position(tick, context)

        # Entry check
        if self.position is None or not self.position.is_open:
            self._evaluate_new_entry(context, tick)


    # --------------------------------------------------------
    # New Entry Evaluation
    # --------------------------------------------------------
    def _evaluate_new_entry(self, context: MarketContext, tick: Dict):

        if not self.risk_manager.can_take_trade():
            return

        decision = self.rules_engine.evaluate(context)
        if not decision.should_enter:
            return

        direction = decision.direction
        if direction is None:
            return

        underlying_price = context.candles[-1].c
        option_symbol = self._select_strike_symbol(direction, underlying_price)
        qty = self.cfg.lot_size * self.cfg.max_lots_per_trade

        ltp = tick.get("last_traded_price") or underlying_price

        print(f"[ENTRY] {direction} | {option_symbol} | LTP={ltp}")

        if self.cfg.paper_trade:
            self.position = self.risk_manager.create_position(
                symbol=option_symbol,
                direction=direction,
                entry_price=ltp,
                qty=qty,
            )
            print("[PAPER] Entry simulated")
            return

        # REAL Order
        order_id = self.order_manager.place_buy_order(option_symbol, qty)
        if order_id:
            self.active_order_id = order_id
            self.position = self.risk_manager.create_position(
                symbol=option_symbol,
                direction=direction,
                entry_price=ltp,
                qty=qty,
            )


    # --------------------------------------------------------
    # Manage Open Position
    # --------------------------------------------------------
    def _manage_open_position(self, tick: Dict, context: MarketContext):

        if self.position is None or not self.position.is_open:
            return

        ltp = tick.get("last_traded_price")
        if ltp is None:
            return

        self.risk_manager.update_trailing_sl(ltp)
        exit_signal = self.risk_manager.check_exit(ltp)

        if exit_signal is None:
            return

        print(f"[EXIT] {exit_signal} | LTP={ltp}")

        if self.cfg.paper_trade:
            pnl = self.risk_manager.close_position(ltp)
            print(f"[PAPER EXIT] PnL = {pnl}")
            self.position = None
            return

        # REAL EXIT
        qty = self.position.qty
        symbol = self.position.symbol
        order_id = self.order_manager.place_exit_order(symbol, qty)

        if order_id:
            pnl = self.risk_manager.close_position(ltp)
            print(f"[REAL EXIT] PnL = {pnl}")

        self.position = None


    # --------------------------------------------------------
    def _select_strike_symbol(self, direction, underlying_price):
        return get_option_symbol(direction, underlying_price)


# ------------------------------------------------------------
# STEP 7 — API Client
# ------------------------------------------------------------

def create_smart_api_client(api_key, username, pwd, totp):
    obj = SmartConnect(api_key=api_key)
    data = obj.generateSession(username, pwd, totp)
    print("[SmartAPI Login]", data)
    return obj


# ------------------------------------------------------------
# STEP 8 — GLOBAL BOT OBJECT (IMPORTANT)
# ------------------------------------------------------------

API_KEY = "TUnreERc"
USERNAME = "S1520958"
PASSWORD = "1709"
TOTP_SECRET = "FU33K44BL2PHQTFUQ4WBPBXB6U======"

CURRENT_TOTP = TOTP(TOTP_SECRET).now()

api_client = create_smart_api_client(API_KEY, USERNAME, PASSWORD, CURRENT_TOTP)

bot_config = BotConfig()
bot_config.paper_trade = True     # Default

# 🔥 THIS BOT IS IMPORTED BY websocket_v1.py
bot = NiftyOptionBot(api=api_client, config=bot_config)


print("[BOT] Ready. Waiting for ticks...")


# ------------------------------------------------------------
# # ------------------------------------------------------------
# WEBSOCKET V1 — STABLE (Angel One compatible)
# ------------------------------------------------------------

feed_token = api_client.feed_token   # ✅ correct attribute
client_code = USERNAME

def on_message(ws, message):
    try:
        tick = json.loads(message)
        bot.on_ws_tick(tick)
        print("📈 TICK RECEIVED")
    except Exception as e:
        print("Tick parse error:", e)

def on_open(ws):
    print("🟢 WebSocket Connected")

    from token_helper import get_latest_future_token
    fut_token = get_latest_future_token(api_client)

    ws.subscribe([
        {
            "exchangeType": 2,   # NFO
            "tokens": [str(fut_token)]
        }
    ])

    print("📡 Subscribed FUT:", fut_token)

def on_error(ws, error):
    print("❌ WS Error:", error)

def on_close(ws):
    print("🔴 WS Closed")


ws = SmartWebSocket(feed_token, client_code)

ws.on_open = on_open
ws.on_message = on_message
ws.on_error = on_error
ws.on_close = on_close

print("⏳ Connecting WebSocket...")
ws.connect()


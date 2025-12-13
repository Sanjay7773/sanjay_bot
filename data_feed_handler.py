"""
data_feed_handler.py

Ye file WebSocket se live market data ko
process karke usable format me convert karti hai.

Kaam:
- Tick receive
- Candle building (3m/5m)
- Volume tracking
- CE/PE OI tracking
- RSI calculation
- MarketContext return (for RulesEngine)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Literal

from rules_engine import Candle, MarketContext   # import models from rules_engine.py
from rules_engine import RuleConfig               # for future integration


# -------------------------------------------------------------------------
# STEP 1 — Helper: Simple RSI function
# -------------------------------------------------------------------------

def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Simple RSI calculator (classic formula).
    prices = underlying price close series

    NOTE:
    - Hum zyada advanced RSI later bana sakte hain,
      abhi basic use karenge.
    """

    if len(prices) < period + 1:
        return 50.0   # default neutral

    gains = []
    losses = []

    for i in range(1, period + 1):
        change = prices[-i] - prices[-i - 1]
        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains) / period if gains else 0.0001
    avg_loss = sum(losses) / period if losses else 0.0001

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# -------------------------------------------------------------------------
# STEP 2 — MAIN CLASS: DataFeedHandler
# -------------------------------------------------------------------------

class DataFeedHandler:
    """
    Ye pura class WebSocket se tik data lega
    aur usko process karke:

    - OHLCV candle बनाएगा
    - OI update karega
    - RSI calculate karega
    - MarketContext return karega

    Ye hi class bot_core.py ko final input provide karega.
    """

    def __init__(self,
                 timeframe_minutes: int = 5,
                 max_candles: int = 200):
        """
        Init par hum define karte hain:

        timeframe_minutes → candle TF (e.g. 3 / 5 / 15)
        max_candles → kitne candles memory me rakhni hain
        """

        self.timeframe_minutes = timeframe_minutes
        self.max_candles = max_candles

        # Candle list (latest candle last)
        self.candles: List[Candle] = []

        # OI series store:
        self.ce_oi: List[int] = []
        self.pe_oi: List[int] = []

        # Underlying price list (RSI ke liye)
        self.underlying_prices: List[float] = []

        # Current candle start time
        self.current_candle_start: Optional[datetime] = None

        # Current candle builder values:
        self.curr_open = None
        self.curr_high = None
        self.curr_low = None
        self.curr_close = None
        self.curr_volume = 0

        print("[DataFeedHandler] Initialized with timeframe:", timeframe_minutes)

# -------------------------------------------------------------------------
# STEP 3 — Tick Handler (WebSocket tick yaha aayega)
# -------------------------------------------------------------------------

    def on_tick(self, tick: Dict):
        """
        WebSocket se jo tick aata hai, woh dictionary hota hai.
        Example tick (Angel SmartAPI):
        {
            "exchange_timestamp": 1680000000,
            "last_traded_price": 22500.50,
            "volume": 120000,
            "oi": 45000,
            ...
        }

        Hum yaha 3 kaam karte hain:
        1) Candle update
        2) OI update (CE + PE)
        3) Underlying price list update (RSI)
        """

        try:
            ltp = tick.get("last_traded_price")       # actual price
            volume = tick.get("volume") or 0          # tick volume
            oi = tick.get("oi") or 0                  # CE/PE OI

            ts_raw = tick.get("exchange_timestamp")
            ts = datetime.fromtimestamp(ts_raw)

        except Exception as e:
            print("[DataFeedHandler] Tick parse error:", e)
            return

        # ---------- PROCESSING -------------
        self._process_tick_into_candle(ltp, volume, ts)
        self._update_oi(oi)
        self._update_price_for_rsi(ltp)

        # Debug print:
        # print("Tick processed:", ltp, "time:", ts)


# -------------------------------------------------------------------------
# STEP 4 — Convert Tick into Candle (OHLCV)
# -------------------------------------------------------------------------

    def _process_tick_into_candle(self, price: float, volume: float, ts: datetime):
        """
        Har tick ko appropriate candle ke andar daalna hai.

        Candle TF = self.timeframe_minutes

        Candle building logic:
        - Agar koi candle running nahi → new candle start karo
        - Agar tick current candle ke time range me hai → update OHLCV
        - Agar tick next candle ke time range me shift ho gaya →
             → purani candle close karo
             → nayi candle start karo
        """

        # 1) Agar koi candle start hi nahi hui hai:
        if self.current_candle_start is None:
            self.current_candle_start = ts
            self.curr_open = price
            self.curr_high = price
            self.curr_low = price
            self.curr_close = price
            self.curr_volume = volume
            return

        # Candle ka end time calculate
        candle_end = self.current_candle_start + timedelta(minutes=self.timeframe_minutes)

        # 2) Yadi tick abhi bhi isi candle ke time range me hai:
        if ts < candle_end:
            self.curr_close = price
            self.curr_high = max(self.curr_high, price)
            self.curr_low = min(self.curr_low, price)
            self.curr_volume += volume
            return

        # 3) Yadi tick nayi candle ka hai:
        #    Pehle purani candle save karo
        closed_candle = Candle(
            ts=self.current_candle_start,
            o=self.curr_open,
            h=self.curr_high,
            l=self.curr_low,
            c=self.curr_close,
            v=self.curr_volume
        )

        self.candles.append(closed_candle)

        # Candles memory overflow control
        if len(self.candles) > self.max_candles:
            self.candles.pop(0)

        # Ab new candle start
        self.current_candle_start = ts
        self.curr_open = price
        self.curr_high = price
        self.curr_low = price
        self.curr_close = price
        self.curr_volume = volume



# -------------------------------------------------------------------------
# STEP 5 — OI Tracking (CE/PE OI series update)
# -------------------------------------------------------------------------

    def _update_oi(self, oi_value: int):
        """
        CE/PE OI update karne ka logic:
        - WebSocket se jab tick aaye jis symbol me CE/PE OI ho
          uska OI yaha update hoga.
        - Abhi hum assume kar rahe ek hi feed me CE ya PE ka tick aa raha.

        NOTE:
        data_feed_handler ko pata hona chahiye ki ye tick CE ka hai ya PE ka.
        → Ye bot_core.py decide karega based on token mapping.
        """

        # --- Temporary Implementation ---
        # Aage bot_core mapping provide karega which token is CE or PE

        # As of now, hum demo ke liye assume karke chal rahe →
        # CE OI series update:
        self.ce_oi.append(oi_value)

        # Memory control:
        if len(self.ce_oi) > 200:
            self.ce_oi.pop(0)

        # IMPORTANT:
        # Later hum CE/PE dono ka OI alag-alag token mapping se lenge.



# -------------------------------------------------------------------------
# STEP 6 — Underlying price tracking (RSI ke liye)
# -------------------------------------------------------------------------

    def _update_price_for_rsi(self, price: float):
        """
        RSI ALWAYS underlying NIFTY price par calculate hota.
        Isliye hum LTP ko ek list me store karte rehte.

        Hum last 200 prices store kar rahe.
        """

        self.underlying_prices.append(price)
        if len(self.underlying_prices) > 200:
            self.underlying_prices.pop(0)

# -------------------------------------------------------------------------
# STEP 7 — MarketContext Builder (VERY IMPORTANT)
# -------------------------------------------------------------------------

    def build_market_context(self, symbol: str = "NIFTY") -> Optional[MarketContext]:
        """
        Ye method final 'MarketContext' object return karta hai
        jise RulesEngine directly use karega.

        REQUIREMENTS:
        - Kam se kam 3 candles honi chahiye (reversal, breakout rules ke liye)
        - CE OI aur PE OI series available ho
        - RSI calculate ho sakta ho
        """

        # ⚠️ Candle availability check
        if len(self.candles) < 3:
            # Not enough candles to evaluate rules
            return None

        # ⚠️ OI check (later improve: CE/PE mapping)
        if len(self.ce_oi) < 5:
            return None
        if len(self.pe_oi) < 5:
            return None

        # ⚠️ RSI calculation
        rsi_value = calculate_rsi(self.underlying_prices, period=14)

        # 📌 Current time (market timestamp)
        now_time = datetime.now()

        # 📌 MarketContext object build
        context = MarketContext(
            symbol=symbol,
            candles=self.candles.copy(),      # SAFE COPY (RulesEngine modify na kare)
            ce_oi=self.ce_oi.copy(),
            pe_oi=self.pe_oi.copy(),
            rsi=rsi_value,
            now=now_time,
            timeframe_minutes=self.timeframe_minutes
        )

        return context



# -------------------------------------------------------------------------
# STEP 8 — DEBUG HELPER (optional but useful)
# -------------------------------------------------------------------------

    def debug_print_candle(self):
        """Latest candle print kare debugging ke liye."""
        if not self.candles:
            print("No candles yet.")
            return

        c = self.candles[-1]
        print(
            f"[CANDLE] {c.ts} | O:{c.o} H:{c.h} L:{c.l} C:{c.c} V:{c.v}"
        )

# -------------------------------------------------------------------------
# STEP 9 — Main Feed Function (tick entry point)
# -------------------------------------------------------------------------

    def feed_tick(self, tick: Dict):
        """
        Yeh function WebSocket ya bot_core se tick receive karega.
        Aur tick ko DataFeedHandler ke processing pipeline me bhej dega.
        """
        self.on_tick(tick)



# -------------------------------------------------------------------------
# STEP 10 — WebSocket direct callback support
# -------------------------------------------------------------------------

    def ws_callback(self, tick: Dict):
        """
        Agar tum SmartWebSocketV2 ka callback direct is class me attach karna chaho,
        to ws.on_ticks = data_handler.ws_callback se ye function chalega.
        """
        self.feed_tick(tick)



# -------------------------------------------------------------------------
# STEP 11 — HOW BOT_CORE WILL USE THIS CLASS (SHORT NOTES)
# -------------------------------------------------------------------------

    def get_context_for_bot(self, symbol="NIFTY"):
        """
        Ye helper function bot_core ko clean context return karega:

        bot_core kuch is tarah karega:
            ctx = data_handler.build_market_context()
            decision = rules_engine.evaluate(ctx)
        """
        return self.build_market_context(symbol)

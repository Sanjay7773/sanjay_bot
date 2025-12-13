"""
rules_engine.py

Ye file pure bot ka “dimag” hai.
Yaha se decide hota hai ki trade lena hai ya nahi.

Is module ka kaam:
- A-SET (5 Primary Rules)
- B-SET (3 Secondary Rules)
ko evaluate karna
aur output dena: CE / PE / No Trade
"""

# -------------------------------------------------------------------------
# STEP 1 — Required imports
# -------------------------------------------------------------------------

from __future__ import annotations   # future type hints use karne ke liye

from dataclasses import dataclass     # simple data structure banane ke liye
from datetime import datetime, time
from typing import List, Optional, Literal


# -------------------------------------------------------------------------
# STEP 2 — Candle structure
# -------------------------------------------------------------------------

@dataclass
class Candle:
    """
    Ye ek single candle ka data rakhta hai:

    ts = timestamp
    o  = open
    h  = high
    l  = low
    c  = close
    v  = volume

    RulesEngine ko candles ka hamesha list diya jayega.
    """
    ts: datetime
    o: float
    h: float
    l: float
    c: float
    v: float


# -------------------------------------------------------------------------
# STEP 3 — MarketContext: pura market ka snapshot input
# -------------------------------------------------------------------------

@dataclass
class MarketContext:
    """
    RulesEngine ko ek hi object me saara required data diya jayega.

    isme ye hota hai:

    - symbol → “NIFTY”
    - candles → latest candles list (OHLCV)
    - ce_oi  → CE ka OI series (list of ints)
    - pe_oi  → PE ka OI series
    - rsi    → underlying ka RSI value
    - now    → current time (for time filter)
    - timeframe_minutes → candle timeframe (3min/5min etc.)

    NOTE:
    Ye context data_feed_handler.py generate karega.
    """
    symbol: str
    candles: List[Candle]
    ce_oi: List[int]
    pe_oi: List[int]
    rsi: float
    now: datetime
    timeframe_minutes: int = 5


# -------------------------------------------------------------------------
# STEP 4 — A-SET flags (5 rules)
# -------------------------------------------------------------------------

@dataclass
class ASetFlags:
    """
    Ye 5 A-SET primary rules ka boolean result store karta hai.
    TRUE matlab rule pass.
    """
    volume_spike: bool = False
    oi_trend_confirm: bool = False
    breakout_retest: bool = False
    reversal_candle: bool = False
    consolidation_breakout: bool = False


# -------------------------------------------------------------------------
# STEP 5 — B-SET flags (3 rules)
# -------------------------------------------------------------------------

@dataclass
class BSetFlags:
    """
    Ye 3 B-SET secondary rules ka boolean result store karta hai.
    """
    trend_structure: bool = False
    time_filter_ok: bool = False
    rsi_momentum_ok: bool = False


# -------------------------------------------------------------------------
# STEP 6 — Combined rule flags
# -------------------------------------------------------------------------

@dataclass
class RuleFlags:
    """
    Ye object final debug/logging ke liye banaya hai.
    Isme A-SET aur B-SET dono ke rule flags ek saath mil jaate hain.
    """
    a_set: ASetFlags
    b_set: BSetFlags


# -------------------------------------------------------------------------
# STEP 7 — Final Signal Output (RulesEngine ka result)
# -------------------------------------------------------------------------

@dataclass
class SignalDecision:
    """
    evaluate() function ka final output is class me aata hai.

    should_enter → trade allowed?
    direction    → "CE" / "PE" / None
    a_true_count → A-SET me kitne rules TRUE hue
    b_true_count → B-SET me kitne rules TRUE hue
    confidence_tag → STRONG / NORMAL / WEAK / NONE
    reason → short comment for logs
    """

    should_enter: bool
    direction: Optional[Literal["CE", "PE"]]
    a_true_count: int
    b_true_count: int
    flags: RuleFlags
    confidence_tag: str
    reason: str


# -------------------------------------------------------------------------
# STEP 8 — RuleConfig: saare tuning parameters yaha control honge
# -------------------------------------------------------------------------

@dataclass
class RuleConfig:
    """
    Ye class tuning/config ke liye hai.

    Tera bot:
    - Daksh (strict mode)
    - Sanjay (normal confirmation mode)

    A/B rules ke thresholds idhar change honge.
    """

    engine_mode: Literal["Daksh", "Sanjay"] = "Sanjay"

    # A-SET thresholds
    volume_spike_multiplier: float = 1.5       # kitna volume spike chahiye?
    volume_lookback: int = 20                  # average volume kitne candles ka?

    oi_lookback: int = 5                       # OI trend kitne points dekhe?

    breakout_lookback: int = 20                # S/R breakout detection range
    breakout_tolerance_pct: float = 0.05       # breakout ko valid manna ka % tolerance

    consolidation_lookback: int = 15
    consolidation_max_range_pct: float = 0.35  # consolidation range max % of price

    # B-SET thresholds
    avoid_start: time = time(12, 30)           # no-trade zone start
    avoid_end: time = time(13, 30)             # no-trade zone end

    rsi_ce_min: float = 45.0                   # RSI safe zone for CE
    rsi_ce_max: float = 60.0
    rsi_pe_min: float = 40.0                   # RSI safe zone for PE
    rsi_pe_max: float = 55.0

    trend_lookback: int = 4                    # trend structure me kitne candles?

    # Minimum requirements
    min_a_true: int = 3                        # A-SET → min 3 rules TRUE
    min_b_true: int = 1                        # B-SET → min 1 rule TRUE

# -------------------------------------------------------------------------
# STEP 9 — Helper functions (small utility)
# -------------------------------------------------------------------------

def _pct_change(old: float, new: float) -> float:
    """
    Percentage change calculate karta hai:
    (new - old) / old * 100

    OI trend, price trend jaise rules me use hota hai.
    """
    if old == 0:
        return 0.0
    return (new - old) / old * 100.0


def _average(values: List[float]) -> float:
    """List ka average return karta hai. Volume avg ke rules me use hota."""
    if not values:
        return 0.0
    return sum(values) / len(values)


# -------------------------------------------------------------------------
# STEP 10 — A-SET RULES (Primary 5 rules)
# -------------------------------------------------------------------------

def _rule_volume_spike(ctx: MarketContext, cfg: RuleConfig) -> bool:
    """
    A1 — Volume Spike Rule

    Logic:
    - Current candle ka volume
    >= (1.5 × last 20 candles ke avg volume)

    Purpose:
    - Price action fake na ho, genuine participation hona chahiye.
    """
    if len(ctx.candles) < cfg.volume_lookback + 1:
        return False  # Enough candles hi nahi

    # Last 20 + current candle nikaal li
    recent = ctx.candles[-(cfg.volume_lookback + 1):]

    current = recent[-1]                     # latest candle
    prev_volumes = [c.v for c in recent[:-1]]  # last 20 candles volume

    avg_vol = _average(prev_volumes)
    if avg_vol <= 0:
        return False

    return current.v >= cfg.volume_spike_multiplier * avg_vol



def _rule_oi_trend(ctx: MarketContext, cfg: RuleConfig,
                   direction: Literal["CE", "PE"]) -> bool:
    """
    A2 — OI Trend Confirmation

    CE ke liye:
        - Price up jayega
        - CE OI down jayega → short covering → bullish confirmation

    PE ke liye:
        - Price down jayega
        - PE OI down jayega → bearish continuation

    Is rule me hum last 5 candles ka price trend + OI trend compare karte hain.
    """

    if len(ctx.candles) < cfg.oi_lookback + 1:
        return False

    # Price trend nikaal rahe
    closes = [c.c for c in ctx.candles[-(cfg.oi_lookback + 1):]]
    price_change = _pct_change(closes[0], closes[-1])

    # Direction ke hisaab se CE OI ya PE OI use hoga
    series = ctx.ce_oi if direction == "CE" else ctx.pe_oi

    if len(series) < cfg.oi_lookback + 1:
        return False

    oi_recent = series[-(cfg.oi_lookback + 1):]
    oi_change = _pct_change(oi_recent[0], oi_recent[-1])

    # Final logic:
    if direction == "CE":
        return price_change > 0 and oi_change < 0
    else:
        return price_change < 0 and oi_change < 0



def _rule_breakout_retest(ctx: MarketContext, cfg: RuleConfig,
                          direction: Literal["CE", "PE"]) -> bool:
    """
    A3 — Breakout + Retest Rule

    Logic:
    - Last 20 candles ka range high/low nikaalo
    - CE:
        -- Price breakout above range_high
        -- Candle ka wick wapas range_high tak retest kare
    - PE:
        -- Price breakdown range_low ke neeche
        -- Candle ka wick retest kare level ko

    Ye rule fake breakout ko filter karta hai.
    """

    if len(ctx.candles) < cfg.breakout_lookback + 2:
        return False

    candles = ctx.candles[-(cfg.breakout_lookback + 2):]
    prev = candles[-2]  # previous candle
    curr = candles[-1]  # current candle

    highs = [c.h for c in candles[:-1]]
    lows = [c.l for c in candles[:-1]]

    range_high = max(highs)
    range_low = min(lows)

    # Tolerance percentage for breakout validity
    tol = cfg.breakout_tolerance_pct / 100.0

    if direction == "CE":
        was_below = prev.c <= range_high * (1 + tol)
        breakout = curr.c > range_high * (1 + tol)
        retest = curr.l <= range_high * (1 + tol)
        return was_below and breakout and retest

    else:  # PE
        was_above = prev.c >= range_low * (1 - tol)
        breakout = curr.c < range_low * (1 - tol)
        retest = curr.h >= range_low * (1 - tol)
        return was_above and breakout and retest



def _rule_reversal_candle(ctx: MarketContext,
                          direction: Literal["CE", "PE"]) -> bool:
    """
    A4 — Reversal Candle Pattern

    CE side:
        - Bullish engulfing
        - Hammer

    PE side:
        - Bearish engulfing
        - Shooting star

    Ye trend reversal confirmation deta hai before entry.
    """

    if len(ctx.candles) < 3:
        return False

    prev = ctx.candles[-2]
    curr = ctx.candles[-1]

    body_prev = abs(prev.c - prev.o)
    body_curr = abs(curr.c - curr.o)
    range_curr = max(curr.h - curr.l, 1)

    # Bullish engulf logic
    bullish_engulf = (
        curr.c > curr.o and
        prev.c < prev.o and
        curr.c >= max(prev.o, prev.c) and
        curr.o <= min(prev.o, prev.c)
    )

    bearish_engulf = (
        curr.c < curr.o and
        prev.c > prev.o and
        curr.c <= min(prev.o, prev.c) and
        curr.o >= max(prev.o, prev.c)
    )

    # Hammer / Shooting Star
    lower_wick = min(curr.o, curr.c) - curr.l
    upper_wick = curr.h - max(curr.o, curr.c)

    hammer = (
        curr.c > curr.o and
        lower_wick >= 2 * body_curr and
        lower_wick / range_curr > 0.6
    )

    shooting_star = (
        curr.c < curr.o and
        upper_wick >= 2 * body_curr and
        upper_wick / range_curr > 0.6
    )

    if direction == "CE":
        return bullish_engulf or hammer
    else:
        return bearish_engulf or shooting_star



def _rule_consolidation_breakout(ctx: MarketContext, cfg: RuleConfig,
                                 direction: Literal["CE", "PE"]) -> bool:
    """
    A5 — Consolidation Breakout

    Logic:
    - Last 15 candles tight range me ho (low volatility)
    - Current candle us range ke upar (CE) ya neeche (PE) close kare

    Ye strong breakout setup ko capture karta hai.
    """

    if len(ctx.candles) < cfg.consolidation_lookback + 1:
        return False

    candles = ctx.candles[-(cfg.consolidation_lookback + 1):]
    prev_range = candles[:-1]
    curr = candles[-1]

    highs = [c.h for c in prev_range]
    lows = [c.l for c in prev_range]

    range_high = max(highs)
    range_low = min(lows)

    underlying = ctx.candles[-1].c
    if underlying <= 0:
        return False

    band_pct = (range_high - range_low) / underlying * 100.0

    # Range agar zyada wide ho → consolidation nahi
    if band_pct > cfg.consolidation_max_range_pct:
        return False

    tol = cfg.breakout_tolerance_pct / 100.0

    if direction == "CE":
        return curr.c > range_high * (1 + tol)
    else:
        return curr.c < range_low * (1 - tol)



# -------------------------------------------------------------------------
# STEP 11 — B-SET RULES (3 rules)
# -------------------------------------------------------------------------

def _rule_trend_structure(ctx: MarketContext, cfg: RuleConfig) -> Optional[Literal["CE", "PE"]]:
    """
    B1 — Trend Structure

    HH-HL  → Uptrend  → CE direction
    LH-LL  → Downtrend → PE direction

    Simpler visual:
    Closes continuously up → CE bias
    Closes continuously down → PE bias
    """

    if len(ctx.candles) < cfg.trend_lookback:
        return None

    candles = ctx.candles[-cfg.trend_lookback:]
    closes = [c.c for c in candles]
    lows = [c.l for c in candles]
    highs = [c.h for c in candles]

    bullish_closes = all(closes[i] < closes[i+1] for i in range(len(closes)-1))
    bullish_lows = all(lows[i] <= lows[i+1] for i in range(len(lows)-1))

    bearish_closes = all(closes[i] > closes[i+1] for i in range(len(closes)-1))
    bearish_highs = all(highs[i] >= highs[i+1] for i in range(len(highs)-1))

    if bullish_closes and bullish_lows:
        return "CE"
    if bearish_closes and bearish_highs:
        return "PE"

    return None



def _rule_time_filter(ctx: MarketContext, cfg: RuleConfig) -> bool:
    """
    B2 — Time Filter

    Avoid zone:
        12:30 to 13:30

    Kyu avoid?
    - Low volume
    - Fake moves
    - Algo noise
    """

    now_t = ctx.now.time()
    if cfg.avoid_start <= now_t <= cfg.avoid_end:
        return False
    return True



def _rule_rsi_momentum(ctx: MarketContext, cfg: RuleConfig,
                       direction: Optional[Literal["CE", "PE"]]) -> bool:
    """
    B3 — RSI Safe Zone

    CE buy:
        RSI 45–60
    PE buy:
        RSI 40–55
    """

    if direction is None:
        return False

    if direction == "CE":
        return cfg.rsi_ce_min <= ctx.rsi <= cfg.rsi_ce_max
    else:
        return cfg.rsi_pe_min <= ctx.rsi <= cfg.rsi_pe_max

# -------------------------------------------------------------------------
# STEP 12 — RulesEngine: Core decision-making brain
# -------------------------------------------------------------------------

class RulesEngine:
    """
    Ye pura class bot ka DIMAG hai.
    Ye:
    - Context data lega (candles, OI, RSI, time)
    - B-SET se trend/direction decide karega
    - A-SET se entry confirmation dega
    - Final output dega (CE/PE/None)
    """

    def __init__(self, config: Optional[RuleConfig] = None):
        """
        config me:
        - mode (Sanjay / Daksh)
        - thresholds
        - minimum rule counts
        - rsi ranges
        sab cheeze set hoti hain.
        """
        self.cfg = config or RuleConfig()


    # ----------------------------------------------------------------------
    # MAIN FUNCTION: evaluate()
    # ----------------------------------------------------------------------
    def evaluate(self, ctx: MarketContext) -> SignalDecision:
        """
        Ye method har new candle/market update par call hoga.
        
        Steps:
        1. Trend structure detect → CE ya PE bias
        2. Time filter check
        3. RSI safe zone check
        4. A-SET evaluate (5 rules)
        5. Rule counts compare with thresholds
        6. Final decision: Should enter or not?
        """

        # -----------------------------
        # B-SET Rule 1: Trend Structure
        # -----------------------------
        trend_direction = _rule_trend_structure(ctx, self.cfg)
        # trend_direction = "CE" / "PE" / None

        if trend_direction is None:
            # Agar trend hi clear nahi → entry mat do
            empty_flags = RuleFlags(
                a_set=ASetFlags(),
                b_set=BSetFlags(
                    trend_structure=False,
                    time_filter_ok=_rule_time_filter(ctx, self.cfg),
                    rsi_momentum_ok=False
                ),
            )

            return SignalDecision(
                should_enter=False,
                direction=None,
                a_true_count=0,
                b_true_count=self._count_b_true(empty_flags.b_set),
                flags=empty_flags,
                confidence_tag="NONE",
                reason="Trend unclear → HH-HL / LH-LL nahi bana."
            )


        # --------------------------------
        # B-SET Rule 2: Time Filter Check
        # --------------------------------
        time_ok = _rule_time_filter(ctx, self.cfg)

        # -----------------------------------
        # B-SET Rule 3: RSI Safe-Zone Check
        # -----------------------------------
        rsi_ok = _rule_rsi_momentum(ctx, self.cfg, trend_direction)

        # B flags store:
        b_flags = BSetFlags(
            trend_structure=True,
            time_filter_ok=time_ok,
            rsi_momentum_ok=rsi_ok,
        )

        b_true = self._count_b_true(b_flags)

        if b_true < self.cfg.min_b_true:
            # B-SET ne entry pass nahi ki → A-SET check hi nahi karna
            empty_flags = RuleFlags(
                a_set=ASetFlags(),
                b_set=b_flags
            )
            return SignalDecision(
                should_enter=False,
                direction=trend_direction,
                a_true_count=0,
                b_true_count=b_true,
                flags=empty_flags,
                confidence_tag="NONE",
                reason=f"B-SET insufficient: b_true={b_true} < required={self.cfg.min_b_true}"
            )


        # -------------------------
        # A-SET RULES (Primary Set)
        # -------------------------

        vol = _rule_volume_spike(ctx, self.cfg)                     # A1
        oi  = _rule_oi_trend(ctx, self.cfg, trend_direction)        # A2
        br  = _rule_breakout_retest(ctx, self.cfg, trend_direction) # A3
        rc  = _rule_reversal_candle(ctx, trend_direction)           # A4
        cb  = _rule_consolidation_breakout(ctx, self.cfg, trend_direction)  # A5

        a_flags = ASetFlags(
            volume_spike=vol,
            oi_trend_confirm=oi,
            breakout_retest=br,
            reversal_candle=rc,
            consolidation_breakout=cb,
        )

        a_true = self._count_a_true(a_flags)

        # Combine flags for final object:
        all_flags = RuleFlags(a_set=a_flags, b_set=b_flags)


        # ---------------------------------------------------
        # A-SET validation (Need minimum 3 rules TRUE)
        # ---------------------------------------------------
        if a_true < self.cfg.min_a_true:
            return SignalDecision(
                should_enter=False,
                direction=trend_direction,
                a_true_count=a_true,
                b_true_count=b_true,
                flags=all_flags,
                confidence_tag="NONE",
                reason=f"A-SET weak: a_true={a_true} < required={self.cfg.min_a_true}"
            )


        # -----------------------------------------------------------------
        # FINAL: ENTRY APPROVED
        # -----------------------------------------------------------------

        confidence = self._confidence_tag(a_true, b_true)

        return SignalDecision(
            should_enter=True,
            direction=trend_direction,              # CE or PE
            a_true_count=a_true,
            b_true_count=b_true,
            flags=all_flags,
            confidence_tag=confidence,
            reason=f"Entry Allowed → A-SET={a_true}, B-SET={b_true}, Direction={trend_direction}, Conf={confidence}",
        )



    # ----------------------------------------------------------------------
    # Count functions (easy helper)
    # ----------------------------------------------------------------------

    @staticmethod
    def _count_a_true(flags: ASetFlags) -> int:
        """A-SET ke 5 rules me se total TRUE rules count return karega."""
        return sum([
            flags.volume_spike,
            flags.oi_trend_confirm,
            flags.breakout_retest,
            flags.reversal_candle,
            flags.consolidation_breakout,
        ])

    @staticmethod
    def _count_b_true(flags: BSetFlags) -> int:
        """B-SET ke 3 rules me se total TRUE rules count return karega."""
        return sum([
            flags.trend_structure,
            flags.time_filter_ok,
            flags.rsi_momentum_ok,
        ])

    @staticmethod
    def _confidence_tag(a_true: int, b_true: int) -> str:
        """
        Confidence tag nikalne ka simple logic:
        - STRONG = A>=4 & B>=2
        - NORMAL = A>=3 & B>=1
        - WEAK   = A>=3 only
        """
        if a_true >= 4 and b_true >= 2:
            return "STRONG"
        if a_true >= 3 and b_true >= 1:
            return "NORMAL"
        if a_true >= 3:
            return "WEAK"
        return "NONE"

# -------------------------------------------------------------------------
# STEP 13 — Developer Notes (For VS Code + Bot Core Integration)
# -------------------------------------------------------------------------
"""
IMPORTANT NOTES (BAHUT ZARURI):

1️⃣ RulesEngine ka kaam sirf logic evaluate karna hai.
   → Ye API, WebSocket, LTP, Orders ko touch nahi karta.

2️⃣ MarketContext hamesha data_feed_handler.py banayega.

3️⃣ bot_core.py me:
       decision = rules.evaluate(context)

   Agar:
       decision.should_enter == True
           → strike_logic se strike lo
           → risk_manager se qty + SL lo
           → order_manager se order place karo

4️⃣ A-SET = Volume + OI + Breakout + Candle Pattern + Consolidation
   B-SET = Trend + Time Filter + RSI

5️⃣ ENTRY ALLOWED ONLY IF:
       A-SET TRUE COUNT ≥ 3
       B-SET TRUE COUNT ≥ 1

6️⃣ direction (CE/PE) sirf trend_structure rule decide karta hai.

7️⃣ confidence_tag:
       STRONG / NORMAL / WEAK
   Position sizing upgrade future me based on tag kar sakte ho.

8️⃣ reason:
       Logging/debugging ke liye important short text.
"""

# -------------------------------------------------------------------------
# STEP 14 — Example Usage (For testing later)
# -------------------------------------------------------------------------

def example_usage():
    """
    Ye example dikhaata hai ki RulesEngine ko kaise call karna hai.
    Real bot me ye kaam bot_core.py karega.
    """

    # Dummy candle list (REAL me ye WebSocket se aayega)
    candles = [
        Candle(ts=datetime.now(), o=100, h=105, l=99, c=103, v=10000),
        Candle(ts=datetime.now(), o=103, h=108, l=102, c=107, v=12000),
        Candle(ts=datetime.now(), o=107, h=110, l=106, c=109, v=15000),
    ]

    ctx = MarketContext(
        symbol="NIFTY",
        candles=candles,
        ce_oi=[50000, 48000, 46000],  # sample OI drop
        pe_oi=[70000, 72000, 73000],
        rsi=52,
        now=datetime.now(),
        timeframe_minutes=5
    )

    engine = RulesEngine(config=RuleConfig())
    decision = engine.evaluate(ctx)

    print("----- RULE ENGINE OUTPUT -----")
    print("Should Enter:", decision.should_enter)
    print("Direction:", decision.direction)
    print("A-Set True:", decision.a_true_count)
    print("B-Set True:", decision.b_true_count)
    print("Confidence:", decision.confidence_tag)
    print("Reason:", decision.reason)
    print("A-Flags:", decision.flags.a_set)
    print("B-Flags:", decision.flags.b_set)
    print("--------------------------------")

# Note:
# example_usage() ko call nahi karna automatically,
# test mode me manually run karna:
#   python rules_engine.py
# aur then example_usage() ko call karke output dekh sakte ho.

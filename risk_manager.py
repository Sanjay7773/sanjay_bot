"""
risk_manager.py

Ye file bot ke SL, Trailing SL, Target, aur Daily Risk ko manage karti hai.

System:
- FIXED SL = 30 points
- FIXED TRAILING LADDER
- Daily loss = 1250 max
- Daily profit = 2500 max
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


# -------------------------------------------------------------------------
# STEP 1 — Ek Single Position ka Data
# -------------------------------------------------------------------------

@dataclass
class PositionState:
    """
    Ye class ek active trade ko represent karti hai.

    symbol       = option ka name (ex: NIFTY25FEB22500CE)
    direction    = CE / PE
    entry_price  = buy price
    qty          = quantity
    sl_price     = current SL
    target_price = current TP
    open_time    = entry time
    is_open      = position active?
    """
    symbol: str
    direction: Literal["CE", "PE"]
    entry_price: float
    qty: int
    sl_price: float
    target_price: float
    open_time: datetime
    is_open: bool = True


# -------------------------------------------------------------------------
# STEP 2 — Risk Manager Config
# -------------------------------------------------------------------------

@dataclass
class RiskManagerConfig:
    base_sl_points: float = 30.0       # Initial SL = entry - 30
    initial_target: float = 100.0      # Initial TP = 100 points

    trail_steps: list = None           # Ladder points
    max_daily_loss: float = 1250.0
    max_daily_profit: float = 2500.0
    capital: float = 100000.0

    def __post_init__(self):
        # Fixed trailing steps:
        if self.trail_steps is None:
            self.trail_steps = [20, 40, 60, 80, 100, 120, 140, 160]


# -------------------------------------------------------------------------
# STEP 3 — Risk Manager
# -------------------------------------------------------------------------

class RiskManager:

    def __init__(self, config: Optional[RiskManagerConfig] = None):
        self.cfg = config or RiskManagerConfig()

        # Daily PnL tracking
        self.daily_realized = 0.0
        self.daily_unrealized = 0.0

        # Current active position
        self.position: Optional[PositionState] = None


    # -----------------------------------------------------
    # STEP 4 — Can we take a new trade?
    # -----------------------------------------------------

    def can_take_trade(self) -> bool:
        """
        Entry tabhi allow ho jab:
        - No active trade
        - Daily loss cross na hua ho
        - Daily profit cross na hua ho
        """
        if self.position and self.position.is_open:
            return False  # ek time pe ek hi trade

        if self.daily_realized <= -self.cfg.max_daily_loss:
            print("Daily loss limit hit.")
            return False

        if self.daily_realized >= self.cfg.max_daily_profit:
            print("Daily profit target hit.")
            return False

        return True


    # -----------------------------------------------------
    # STEP 5 — New Position Create on Entry
    # -----------------------------------------------------

    def create_position(self, symbol: str, direction: Literal["CE", "PE"],
                        entry_price: float, qty: int) -> PositionState:
        """
        Entry ke time:
        - initial SL set hota = entry - 30
        - initial TP = entry + 100
        """
        sl = entry_price - self.cfg.base_sl_points
        tp = entry_price + self.cfg.initial_target

        self.position = PositionState(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            qty=qty,
            sl_price=sl,
            target_price=tp,
            open_time=datetime.now()
        )

        print(f"[RiskManager] New Position Created → Entry={entry_price}, SL={sl}, TP={tp}")
        return self.position


    # -----------------------------------------------------
    # STEP 6 — Check if SL or TP hit
    # -----------------------------------------------------

    def check_exit(self, ltp: float) -> Optional[str]:
        """
        LTP dekhkar decide hota:
        - SL hit → exit
        - TP hit → exit
        """
        if not self.position or not self.position.is_open:
            return None

        if ltp <= self.position.sl_price:
            return "SL_HIT"

        if ltp >= self.position.target_price:
            return "TP_HIT"

        return None


    # -----------------------------------------------------
    # STEP 7 — Update Trailing SL (FIXED LADDER)
    # -----------------------------------------------------

    def update_trailing_sl(self, ltp: float):
        """
        Profit check karke SL ladder follow karta hai:

        Example:
        Profit = ltp - entry_price

        Profit >= 20  → SL = entry
        Profit >= 40  → SL = entry + 20
        Profit >= 60  → SL = entry + 40
        Profit >= 80  → SL = entry + 60
        ...
        """
        if not self.position or not self.position.is_open:
            return

        profit = ltp - self.position.entry_price
        base = self.position.entry_price

        for step in self.cfg.trail_steps:
            if profit >= step:
                new_sl = base + (step - 20)
                if new_sl > self.position.sl_price:
                    self.position.sl_price = new_sl
                    print(f"[Trail SL] Step {step} → SL updated to {new_sl}")


    # -----------------------------------------------------
    # STEP 8 — Close Position and Update PnL
    # -----------------------------------------------------

    def close_position(self, exit_price: float):
        """
        Position close hoti hai:
        - realized pnl update
        - position mark closed
        """
        if not self.position:
            return

        pnl = (exit_price - self.position.entry_price) * self.position.qty
        self.daily_realized += pnl
        self.position.is_open = False

        print(f"[RiskManager] Position Closed @ {exit_price}, PnL = {pnl}")
        print(f"[Daily Realized] = {self.daily_realized}")

        return pnl

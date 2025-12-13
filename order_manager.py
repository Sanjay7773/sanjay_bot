"""
order_manager.py

Is file ka kaam:
- Angel One SmartAPI se order place karna
- SL modify karna
- Position exit karna
- Quantity / order type handle karna

NOTE:
- Ye class bot_core.py ke through call hogi
- Ye market order use karta hai (option buying)
"""

from __future__ import annotations
from SmartApi.smartConnect import SmartConnect   # Angel One SmartAPI
from dataclasses import dataclass
from typing import Optional, Literal
import traceback



# ---------------------------------------------------------------------
# STEP 1 — Order Config
# ---------------------------------------------------------------------

@dataclass
class OrderConfig:
    """
    Ye config future me modify kar sakte ho.

    - variety   = NORMAL / STOPLOSS / BO etc.
    - product   = MIS / NRML (option buying MIS best)
    - exchange  = NFO (NIFTY options ke liye)
    - orderType = MARKET (option buying ke liye recommended)
    - validity  = DAY
    """

    variety: str = "NORMAL"
    product: str = "MIS"
    exchange: str = "NFO"
    order_type: str = "MARKET"
    validity: str = "DAY"



# ---------------------------------------------------------------------
# STEP 2 — OrderManager Class
# ---------------------------------------------------------------------

class OrderManager:

    def __init__(self, api: SmartConnect, config: Optional[OrderConfig] = None):
        """
        api → SmartConnect object (get_token.py se milega)
        config → OrderConfig (default)
        """
        self.api = api
        self.cfg = config or OrderConfig()

    # -----------------------------------------------------------------
    # STEP 3 — PLACE ORDER (BUY)
    # -----------------------------------------------------------------

    def place_buy_order(self, symbol: str, qty: int) -> Optional[str]:
        """
        BUY order place karega (CE/PE option buy)
        Returns: order_id or None
        """

        try:
            params = {
                "variety": self.cfg.variety,
                "tradingsymbol": symbol,
                "symboltoken": "",     # TODO: bot_core symbol mapping se fill karega
                "transactiontype": "BUY",
                "exchange": self.cfg.exchange,
                "ordertype": self.cfg.order_type,
                "producttype": self.cfg.product,
                "duration": self.cfg.validity,
                "quantity": qty,
            }

            print(f"[OrderManager] BUY → {symbol}, QTY={qty}")

            order = self.api.placeOrder(params)
            order_id = order.get("orderid")

            print(f"[OrderManager] BUY ORDER PLACED → OrderID = {order_id}")
            return order_id

        except Exception as e:
            print("\n[OrderManager] BUY Order Failed:")
            print(e)
            traceback.print_exc()
            return None



    # -----------------------------------------------------------------
    # STEP 4 — EXIT ORDER (SELL)
    # -----------------------------------------------------------------

    def place_exit_order(self, symbol: str, qty: int) -> Optional[str]:
        """
        SELL order place karega to exit the trade.
        """

        try:
            params = {
                "variety": self.cfg.variety,
                "tradingsymbol": symbol,
                "symboltoken": "",
                "transactiontype": "SELL",
                "exchange": self.cfg.exchange,
                "ordertype": self.cfg.order_type,
                "producttype": self.cfg.product,
                "duration": self.cfg.validity,
                "quantity": qty,
            }

            print(f"[OrderManager] EXIT → {symbol}, QTY={qty}")

            order = self.api.placeOrder(params)
            order_id = order.get("orderid")

            print(f"[OrderManager] EXIT ORDER PLACED → OrderID = {order_id}")
            return order_id

        except Exception as e:
            print("\n[OrderManager] EXIT Order Failed:")
            print(e)
            traceback.print_exc()
            return None



    # -----------------------------------------------------------------
    # STEP 5 — MODIFY ORDER (For SL update)
    # -----------------------------------------------------------------

    def modify_sl_order(self, order_id: str, symbol: str, new_sl: float, qty: int):
        """
        Agar tum stoploss modify karna chahte ho,
        toh ye function SL modify karega.

        NOTE:
        - Angel SmartAPI SL modify BO/MIS both allow karta hai (with STOPLOSS type).
        - But option buying me hum mostly direct EXIT kar dete hain.
        """

        try:
            params = {
                "variety": self.cfg.variety,
                "orderid": order_id,
                "tradingsymbol": symbol,
                "symboltoken": "",
                "transactiontype": "SELL",
                "exchange": self.cfg.exchange,
                "ordertype": "STOPLOSS",
                "producttype": self.cfg.product,
                "duration": self.cfg.validity,
                "quantity": qty,
                "triggerprice": new_sl,
                "price": new_sl,
            }

            print(f"[OrderManager] SL MODIFY → {order_id}, New SL = {new_sl}")

            resp = self.api.modifyOrder(params)
            print("[OrderManager] SL Order Modified:", resp)
            return resp

        except Exception as e:
            print("\n[OrderManager] SL Modify Failed:")
            print(e)
            traceback.print_exc()
            return None



    # -----------------------------------------------------------------
    # STEP 6 — Get Order Info
    # -----------------------------------------------------------------

    def get_order_status(self, order_id: str):
        """Order ka status nikalne ke liye."""
        try:
            resp = self.api.orderBook()
            for o in resp["data"]:
                if o["orderid"] == order_id:
                    return o
        except:
            pass
        return None

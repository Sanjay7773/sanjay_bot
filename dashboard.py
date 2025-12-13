# dashboard.py

from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime


class BotDashboard:

    def __init__(self):
        self.data = {
            "status": "WAITING",
            "signal": "-",
            "direction": "-",
            "A_set": "-",
            "B_set": "-",
            "reason": "-",

            "trade_status": "NO TRADE",
            "symbol": "-",
            "entry": "-",
            "ltp": "-",
            "sl": "-",
            "target": "-",
            "pnl": "-",

            "exit_reason": "-",
            "daily_pnl": "0",
        }

        self.live = Live(self.render(), refresh_per_second=4)

    def start(self):
        """Dashboard start karega terminal me."""
        self.live.start()

    def stop(self):
        """Dashboard stop karega."""
        self.live.stop()

    def update(self, key, value):
        """Bot update karega variables ko."""
        self.data[key] = value
        self.live.update(self.render())

    def render(self):
        """Full dashboard layout yaha create hota hai."""

        # 🟦 TOP PANEL — BOT STATUS
        status_panel = Panel(
            Text(f"BOT STATUS: {self.data['status']}", style="bold green"),
            title="SYSTEM"
        )

        # 🟧 SIGNAL PANEL
        signal_table = Table(title="SIGNAL INFO")
        signal_table.add_column("Item")
        signal_table.add_column("Value")

        signal_table.add_row("Signal", str(self.data["signal"]))
        signal_table.add_row("Direction", str(self.data["direction"]))
        signal_table.add_row("A-SET", str(self.data["A_set"]))
        signal_table.add_row("B-SET", str(self.data["B_set"]))
        signal_table.add_row("Reason", str(self.data["reason"]))

        signal_panel = Panel(signal_table)

        # 🟩 TRADE PANEL
        trade_table = Table(title="TRADE INFO")
        trade_table.add_column("Item")
        trade_table.add_column("Value")

        trade_table.add_row("Status", str(self.data["trade_status"]))
        trade_table.add_row("Symbol", str(self.data["symbol"]))
        trade_table.add_row("Entry", str(self.data["entry"]))
        trade_table.add_row("LTP", str(self.data["ltp"]))
        trade_table.add_row("SL", str(self.data["sl"]))
        trade_table.add_row("Target", str(self.data["target"]))
        trade_table.add_row("PnL", str(self.data["pnl"]))

        trade_panel = Panel(trade_table)

        # 🟥 DAILY PANEL
        daily_panel = Panel(
            f"Exit: {self.data['exit_reason']}\n"
            f"Daily PnL: {self.data['daily_pnl']}",
            title="DAILY STATS"
        )

        # FINAL LAYOUT: 4 Panels stacked
        layout = Table.grid(padding=1)
        layout.add_row(status_panel)
        layout.add_row(signal_panel)
        layout.add_row(trade_panel)
        layout.add_row(daily_panel)

        return layout

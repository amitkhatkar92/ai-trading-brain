"""
Pilot Package
=============
Safe execution layer for beginner live trading.

Components
----------
PaperTradingController  — simulates fills with realistic slippage + costs
PilotController         — enforces ₹10k–₹20k capital, max 2 trades, risk gates

Quick start::
    from pilot import get_paper_broker, get_pilot_controller

    pilot = get_pilot_controller()
    paper = get_paper_broker()

    ok, reason = pilot.check_trade_allowed(signal)
    if ok:
        trade_id = paper.place_order(signal)
        if trade_id:
            pilot.register_trade(trade_id, signal, qty, entry)

Config (all via .env)::
    PILOT_CAPITAL       = 20000      # ₹20,000
    PILOT_RISK_PCT      = 0.005      # 0.5% → ₹100/trade
    PILOT_MAX_TRADES    = 2
    PILOT_DAILY_LOSS_PCT= 0.02       # 2% → ₹400/day stop
    PAPER_TRADING       = true
"""

from pilot.paper_trading  import PaperTradingController, get_paper_broker, PaperPosition
from pilot.pilot_controller import (
    PilotController, get_pilot_controller,
    PilotTradeRecord,
    PILOT_CAPITAL, PILOT_RISK_PCT, PILOT_MAX_TRADES,
)

__all__ = [
    "PaperTradingController", "get_paper_broker", "PaperPosition",
    "PilotController",        "get_pilot_controller", "PilotTradeRecord",
    "PILOT_CAPITAL", "PILOT_RISK_PCT", "PILOT_MAX_TRADES",
]

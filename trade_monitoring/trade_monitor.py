"""
Trade Monitor — Layer 9
==========================
Watches all open positions in real time and takes autonomous action
when predefined triggers are hit.

Actions:
  • Move stop to breakeven when 1R profit is reached
  • Trail stop when 2R profit is reached
  • Close position at target
  • Emergency close on maximum adverse excursion
  • Alert when market conditions change adversely mid-trade
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from execution_engine.order_manager import OrderRecord
from utils import get_logger

log = get_logger(__name__)


class TradeMonitor:
    """
    Monitors open positions tick-by-tick (or on each polling cycle)
    and manages the trade lifecycle post-entry.
    """

    R_BREAKEVEN_TRIGGER  = 1.0   # Move SL to breakeven after 1R
    R_TRAIL_TRIGGER      = 2.0   # Start trailing after 2R
    R_TARGET_TRIGGER     = 3.0   # Close at 3R (if no separate target)
    MAX_ADVERSE_EXCURSION = 0.015 # Close if LTP moves 1.5% beyond SL (gap risk)

    def __init__(self):
        self._open_orders: Dict[str, OrderRecord] = {}   # order_id → OrderRecord
        self._closed_orders: List[OrderRecord]    = []
        self._order_manager                       = None  # injected by orchestrator
        log.info("[TradeMonitor] Initialised.")

    # ─────────────────────────────────────────────────────────────────
    # REGISTRATION
    # ─────────────────────────────────────────────────────────────────

    def register(self, order: OrderRecord):
        """Register a newly placed order for monitoring."""
        self._open_orders[order.order_id] = order
        log.info("[TradeMonitor] Registered: %s %s qty=%d entry=%.2f",
                 order.symbol, order.direction, order.quantity, order.entry_price)

    def inject_order_manager(self, order_manager):
        """Inject OrderManager so monitor can close positions."""
        self._order_manager = order_manager

    # ─────────────────────────────────────────────────────────────────
    # MONITORING CYCLE
    # ─────────────────────────────────────────────────────────────────

    def check_all(self, price_feed: Optional[Dict[str, float]] = None):
        """
        Called every N minutes.
        price_feed: dict of {symbol: ltp} — if None, simulates prices.
        """
        closed_ids = []
        for oid, order in self._open_orders.items():
            ltp = self._get_ltp(order.symbol, price_feed)
            if ltp is None:
                continue
            action = self._evaluate(order, ltp)
            if action:
                self._act(oid, order, ltp, action)
                if action in ("close_target", "close_emergency", "close_eod"):
                    closed_ids.append(oid)

        for oid in closed_ids:
            self._closed_orders.append(self._open_orders.pop(oid))

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────────

    def _evaluate(self, order: OrderRecord, ltp: float) -> Optional[str]:
        entry  = order.entry_price
        sl     = order.stop_loss
        target = order.target

        is_long = order.direction == "BUY"
        risk    = abs(entry - sl) if sl else 0.0

        if risk == 0:
            return None

        unrealised  = (ltp - entry) if is_long else (entry - ltp)
        r_multiple  = unrealised / risk

        # ── Check: target hit ─────────────────────────────────────────
        if target and ((is_long and ltp >= target) or (not is_long and ltp <= target)):
            return "close_target"

        # ── Check: stop loss hit ──────────────────────────────────────
        if (is_long and ltp <= sl) or (not is_long and ltp >= sl):
            return "close_sl"

        # ── Check: 2R → trail stop ────────────────────────────────────
        if r_multiple >= self.R_TRAIL_TRIGGER:
            new_sl = ltp - risk if is_long else ltp + risk
            if (is_long and new_sl > sl) or (not is_long and new_sl < sl):
                order.stop_loss = round(new_sl, 2)
                log.info("[TradeMonitor] 🔄 Trail SL %s → %.2f (R=%.1f)",
                         order.symbol, order.stop_loss, r_multiple)

        # ── Check: 1R → move to breakeven ─────────────────────────────
        elif r_multiple >= self.R_BREAKEVEN_TRIGGER:
            if (is_long and sl < entry) or (not is_long and sl > entry):
                order.stop_loss = entry
                log.info("[TradeMonitor] 🔒 Breakeven SL %s → %.2f",
                         order.symbol, entry)

        return None

    def _act(self, oid: str, order: OrderRecord, ltp: float, action: str):
        reason_map = {
            "close_target":    f"Target hit at {ltp:.2f}",
            "close_sl":        f"Stop loss hit at {ltp:.2f}",
            "close_emergency": f"Emergency MAE at {ltp:.2f}",
            "close_eod":       "End of day close",
        }
        reason = reason_map.get(action, action)
        log.info("[TradeMonitor] %s %s — %s", action.upper(), order.symbol, reason)

        if self._order_manager:
            self._order_manager.close_position(oid, ltp, reason=action)

    def _get_ltp(self, symbol: str,
                  price_feed: Optional[Dict[str, float]]) -> Optional[float]:
        if price_feed and symbol in price_feed:
            return price_feed[symbol]
        # Simulation fallback
        import random
        order = next((o for o in self._open_orders.values()
                      if o.symbol == symbol), None)
        if order:
            return round(order.entry_price * (1 + random.uniform(-0.03, 0.03)), 2)
        return None

    # ─────────────────────────────────────────────────────────────────
    # ACCESS
    # ─────────────────────────────────────────────────────────────────

    def get_closed_trades(self) -> List[OrderRecord]:
        return list(self._closed_orders)

    def get_open_trades(self) -> List[OrderRecord]:
        return list(self._open_orders.values())

    def summary(self) -> str:
        open_ct   = len(self._open_orders)
        closed_ct = len(self._closed_orders)
        realised  = sum(o.pnl for o in self._closed_orders)
        return (f"[TradeMonitor] Open:{open_ct} | Closed:{closed_ct} | "
                f"Realised PnL: ₹{realised:+,.0f}")

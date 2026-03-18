"""
Pilot Mode Controller
=====================
Governs real (or paper) trading under strict beginner-safe constraints:

  Capital      : ₹10,000 – ₹20,000 (default ₹20,000)
  Risk/trade   : 0.25% – 0.5% of capital  (default 0.5%  → ₹100/trade)
  Max trades   : 2 concurrent open positions
  Daily loss   : 2% of capital  (default → ₹400/day stop)
  Position size: auto-calculated from risk amount ÷ stop distance

This controller is a lightweight guard that wraps any OrderManager or
PaperTradingController.  The rest of the system calls:

    ok, reason = pilot.check_trade_allowed(signal)
    if ok:
        qty = pilot.compute_position_size(signal.entry_price, signal.stop_loss)
        ...

Usage::
    from pilot import get_pilot_controller
    pilot = get_pilot_controller()
    allowed, reason = pilot.check_trade_allowed(signal)
    report = pilot.get_status_report()
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Tuple

from models.trade_signal import TradeSignal
from config import PAPER_TRADING
from utils  import get_logger

log = get_logger(__name__)

# ── Config (overridable via .env) ──────────────────────────────────────────
PILOT_CAPITAL    = float(os.getenv("PILOT_CAPITAL",    20_000))
PILOT_RISK_PCT   = float(os.getenv("PILOT_RISK_PCT",   0.005))   # 0.5 %
PILOT_MAX_TRADES = int(os.getenv("PILOT_MAX_TRADES",   2))
PILOT_DAILY_LOSS_PCT = float(os.getenv("PILOT_DAILY_LOSS_PCT", 0.02))  # 2 %

# ── Records ────────────────────────────────────────────────────────────────

@dataclass
class PilotTradeRecord:
    trade_id:    str
    symbol:      str
    direction:   str
    strategy:    str
    entry:       float
    stop:        float
    target:      float
    quantity:    int
    risk_amount: float
    opened_at:   datetime = field(default_factory=datetime.now)
    closed_at:   Optional[datetime] = None
    net_pnl:     Optional[float] = None
    status:      str = "open"   # open | closed


class PilotController:
    """
    Enforces beginner pilot constraints before any order is placed.

    Rules enforced at every check_trade_allowed() call:
      1. Daily loss limit not breached
      2. max_open_trades not exceeded
      3. Symbol not already in portfolio
      4. Signal quality gate: R:R >= 2 (hard minimum for pilot)
    """

    def __init__(
        self,
        capital:         float = PILOT_CAPITAL,
        risk_pct:        float = PILOT_RISK_PCT,
        max_trades:      int   = PILOT_MAX_TRADES,
        daily_loss_pct:  float = PILOT_DAILY_LOSS_PCT,
        paper_mode:      bool  = True,
    ) -> None:
        self._capital        = capital
        self._risk_pct       = risk_pct
        self._max_trades     = max_trades
        self._daily_loss_limit = capital * daily_loss_pct
        self._paper_mode     = paper_mode or PAPER_TRADING
        self._open_trades:   List[PilotTradeRecord] = []
        self._closed_trades: List[PilotTradeRecord] = []
        self._today_pnl:     float = 0.0
        self._today_date:    date  = date.today()
        self._total_pnl:     float = 0.0

        risk_rs = self._capital * self._risk_pct
        log.info(
            "[Pilot] Initialised  capital=₹%.0f  risk/trade=₹%.0f (%.2f%%)  "
            "max_trades=%d  daily_loss_limit=₹%.0f  mode=%s",
            capital, risk_rs, risk_pct * 100, max_trades,
            self._daily_loss_limit,
            "PAPER" if self._paper_mode else "LIVE",
        )

    # ── Day reset ──────────────────────────────────────────────────────────

    def _refresh_day(self) -> None:
        today = date.today()
        if today != self._today_date:
            log.info("[Pilot] New trading day — resetting daily P&L counter.")
            self._today_pnl  = 0.0
            self._today_date = today

    # ── Gate: check if trade is allowed ───────────────────────────────────

    def check_trade_allowed(
        self, signal: TradeSignal
    ) -> Tuple[bool, str]:
        """
        Returns (True, "OK") if trade should proceed,
        or (False, reason_string) if blocked.
        """
        self._refresh_day()

        # 1. Daily loss limit
        if self._today_pnl <= -self._daily_loss_limit:
            msg = (f"Daily loss limit hit — today_pnl=₹{self._today_pnl:,.0f}, "
                   f"limit=₹{self._daily_loss_limit:,.0f}")
            log.warning("[Pilot] ❌ BLOCKED: %s", msg)
            return False, msg

        # 2. Max concurrent trades
        open_count = len(self._open_trades)
        if open_count >= self._max_trades:
            msg = f"Max open trades reached ({open_count}/{self._max_trades})"
            log.info("[Pilot] ❌ BLOCKED: %s", msg)
            return False, msg

        # 3. Duplicate symbol
        open_syms = {t.symbol for t in self._open_trades}
        if signal.symbol in open_syms:
            msg = f"Already holding {signal.symbol}"
            log.info("[Pilot] ❌ BLOCKED: %s", msg)
            return False, msg

        # 4. Minimum R:R gate (pilot requires at least 2:1)
        min_rr = 2.0
        entry  = signal.entry_price
        stop   = signal.stop_loss
        tgt    = signal.target_price
        if stop == entry:
            msg = "Zero stop distance in signal"
            log.warning("[Pilot] ❌ BLOCKED: %s", msg)
            return False, msg

        rr = abs(tgt - entry) / abs(entry - stop)
        if rr < min_rr:
            msg = (f"R:R too low for pilot — got {rr:.2f}, need ≥ {min_rr}")
            log.info("[Pilot] ❌ BLOCKED: %s", msg)
            return False, msg

        log.info(
            "[Pilot] ✅ ALLOWED %s %s  R:R=%.2f  "
            "open=%d/%d  today_pnl=₹%+.0f",
            signal.direction, signal.symbol, rr,
            open_count, self._max_trades, self._today_pnl,
        )
        return True, "OK"

    # ── Position sizing ────────────────────────────────────────────────────

    def compute_position_size(
        self, entry_price: float, stop_price: float
    ) -> int:
        """
        Returns lot size based on capital × risk_pct / stop_distance.
        Always at least 1.  Capped at 30% of capital per trade.
        """
        if entry_price <= 0:
            return 1
        stop_dist  = abs(entry_price - stop_price)
        if stop_dist <= 0:
            return 1
        risk_rs    = self._capital * self._risk_pct
        qty        = int(risk_rs / stop_dist)
        max_qty    = int(self._capital * 0.30 / entry_price)
        qty        = max(1, min(qty, max_qty))
        log.debug("[Pilot] Sizing: risk=₹%.0f  stop_dist=₹%.2f  qty=%d",
                  risk_rs, stop_dist, qty)
        return qty

    # ── Trade lifecycle ────────────────────────────────────────────────────

    def register_trade(
        self,
        trade_id:    str,
        signal:      TradeSignal,
        filled_qty:  int,
        entry:       float,
    ) -> PilotTradeRecord:
        """Call after a paper/live order is confirmed filled."""
        risk_amount = abs(entry - signal.stop_loss) * filled_qty
        rec = PilotTradeRecord(
            trade_id    = trade_id,
            symbol      = signal.symbol,
            direction   = (signal.direction.value
                           if hasattr(signal.direction, "value")
                           else str(signal.direction)),
            strategy    = signal.strategy_name,
            entry       = entry,
            stop        = signal.stop_loss,
            target      = signal.target_price,
            quantity     = filled_qty,
            risk_amount = risk_amount,
        )
        self._open_trades.append(rec)
        log.info("[Pilot] Registered trade %s — %s qty=%d @ ₹%.2f",
                 trade_id, signal.symbol, filled_qty, entry)
        return rec

    def record_close(
        self,
        trade_id: str,
        net_pnl:  float,
    ) -> None:
        """Call when a trade is closed — updates daily + total P&L."""
        self._refresh_day()
        for rec in self._open_trades:
            if rec.trade_id == trade_id:
                rec.closed_at = datetime.now()
                rec.net_pnl   = net_pnl
                rec.status    = "closed"
                self._open_trades.remove(rec)
                self._closed_trades.append(rec)
                self._today_pnl += net_pnl
                self._total_pnl += net_pnl
                log.info("[Pilot] Closed trade %s  net_pnl=₹%+.0f  "
                         "today=₹%+.0f  total=₹%+.0f",
                         trade_id, net_pnl, self._today_pnl, self._total_pnl)
                return
        log.warning("[Pilot] record_close: trade_id %s not found", trade_id)

    # ── Status report ──────────────────────────────────────────────────────

    def get_status_report(self) -> str:
        self._refresh_day()
        open_cnt   = len(self._open_trades)
        closed_cnt = len(self._closed_trades)
        wins       = sum(1 for t in self._closed_trades
                         if t.net_pnl and t.net_pnl > 0)
        win_rate   = (wins / closed_cnt * 100) if closed_cnt else 0.0
        dl_remain  = self._daily_loss_limit + self._today_pnl

        lines = [
            "━" * 52,
            " PILOT MODE STATUS",
            "━" * 52,
            f"  Capital       : ₹{self._capital:,.0f}",
            f"  Mode          : {'PAPER 🟡' if self._paper_mode else 'LIVE 🔴'}",
            f"  Risk/trade    : {self._risk_pct * 100:.2f}%"
            f" (₹{self._capital * self._risk_pct:.0f}/trade)",
            f"  Max trades    : {self._max_trades}",
            "─" * 52,
            f"  Open trades   : {open_cnt}/{self._max_trades}",
            f"  Today P&L     : ₹{self._today_pnl:+,.0f}",
            f"  Daily loss rem: ₹{dl_remain:,.0f}",
            f"  Total P&L     : ₹{self._total_pnl:+,.0f}",
            f"  Closed trades : {closed_cnt}  "
            f"(wins={wins}, rate={win_rate:.0f}%)",
            "─" * 52,
        ]
        if self._open_trades:
            lines.append("  Open positions:")
            for t in self._open_trades:
                lines.append(
                    f"    {t.symbol:15s} {t.direction}  qty={t.quantity}"
                    f"  entry=₹{t.entry:.1f}"
                )
        lines.append("━" * 52)
        return "\n".join(lines)

    def log_status(self) -> None:
        log.info("\n%s", self.get_status_report())


# ── Singleton ──────────────────────────────────────────────────────────────
_INSTANCE: Optional[PilotController] = None

def get_pilot_controller(
    capital:    float = PILOT_CAPITAL,
    risk_pct:   float = PILOT_RISK_PCT,
    max_trades: int   = PILOT_MAX_TRADES,
) -> PilotController:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = PilotController(
            capital    = capital,
            risk_pct   = risk_pct,
            max_trades = max_trades,
        )
    return _INSTANCE

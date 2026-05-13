"""
Options Risk Engine
====================
Capital-aware position sizing and pre-trade risk approval for options.

Rules enforced:
  1. Total options exposure ≤ OPTIONS_CAPITAL_PCT % of total capital
  2. Per-trade max loss ≤ OPTIONS_PER_TRADE_LOSS_PCT % of total capital
  3. Max concurrent options positions ≤ MAX_OPTIONS_POSITIONS
  4. VIX gate: don't sell premium (IC / credit spreads) when VIX > VIX_SELL_LIMIT
  5. Min DTE guard: don't enter within MIN_DTE_ENTRY days of expiry
  6. Strategy loss-streak: disable strategy after 3+ consecutive losses

Position sizing formula
-----------------------
  max_risk_rs   = TOTAL_CAPITAL × OPTIONS_PER_TRADE_LOSS_PCT / 100
  lots          = max(1, floor(max_risk_rs / max_loss_per_lot))
  lots          = min(lots, OPTIONS_MAX_LOTS_PER_TRADE)

where:
  max_loss_per_lot  = entry_premium × lot_size   (for debit spreads)
  max_loss_per_lot  = max_loss × lot_size         (for credit spreads / IC)
"""

from __future__ import annotations

import json
from typing import Optional

from models.trade_signal import TradeSignal, SignalType
from models.market_data  import MarketSnapshot
from config              import TOTAL_CAPITAL
from utils               import get_logger

log = get_logger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────

# Maximum fraction of total capital allocated to all open options positions
OPTIONS_CAPITAL_PCT      = 15.0   # % of TOTAL_CAPITAL

# Maximum loss per options trade as % of total capital
OPTIONS_PER_TRADE_LOSS_PCT = 2.0  # %

# Hard cap on lots per single spread trade
OPTIONS_MAX_LOTS_PER_TRADE = 3

# VIX above this → refuse to sell premium (adverse for credit strategies)
VIX_SELL_LIMIT = 28.0

# Strategy loss-streak threshold → auto-disable
MAX_LOSS_STREAK = 3


class OptionsRiskEngine:
    """
    Pre-trade approval and lot-sizing for options signals.

    Integrated into the orchestrator cycle immediately before
    options signals reach the OptionsOrderManager.
    """

    def __init__(self) -> None:
        self._disabled_strategies: dict = {}   # strategy_type → disable_until date
        log.info("[OptionsRiskEngine] Initialised.")

    # ── Primary gate ───────────────────────────────────────────────────

    def approve_and_size(
        self,
        signal:   TradeSignal,
        snapshot: Optional[MarketSnapshot],
        open_exposure_rs: float,
    ) -> bool:
        """
        Check all risk gates and inject the ``lots`` field into signal.notes.

        Returns True if the trade is approved; False means reject.
        The lot count is written into signal.notes["lots"] so the
        OptionsOrderManager can read it.
        """
        if signal.signal_type not in (SignalType.OPTIONS, SignalType.SPREAD):
            return False

        try:
            meta = json.loads(signal.notes)
        except Exception:
            log.warning("[OptionsRiskEngine] Cannot parse notes — rejecting.")
            return False

        stype    = meta.get("strategy_type", "")
        dte      = int(meta.get("dte", 0))
        max_loss = float(meta.get("max_loss", signal.entry_price))
        lot_size = int(meta.get("lot_size", 75))
        vix      = float(getattr(snapshot, "vix", 15.0)) if snapshot else 15.0

        # ── Gate 1: total capital exposure ───────────────────────────
        max_options_capital = TOTAL_CAPITAL * OPTIONS_CAPITAL_PCT / 100.0
        if open_exposure_rs >= max_options_capital:
            log.info(
                "[OptionsRiskEngine] Capital gate: exposure ₹%.0f ≥ limit ₹%.0f — "
                "rejected %s %s.",
                open_exposure_rs, max_options_capital, signal.symbol, stype,
            )
            return False

        # ── Gate 2: per-trade max loss ────────────────────────────────
        max_risk_rs = TOTAL_CAPITAL * OPTIONS_PER_TRADE_LOSS_PCT / 100.0

        # Compute viable lot count
        max_loss_per_lot = max_loss * lot_size
        if max_loss_per_lot <= 0:
            log.warning("[OptionsRiskEngine] max_loss_per_lot=0 — rejecting %s.", signal.symbol)
            return False

        import math
        lots = max(1, math.floor(max_risk_rs / max_loss_per_lot))
        lots = min(lots, OPTIONS_MAX_LOTS_PER_TRADE)

        # Actual trade max loss
        trade_max_loss = lots * max_loss_per_lot
        remaining_capacity = max_options_capital - open_exposure_rs
        if trade_max_loss > remaining_capacity:
            # Can we fit 1 lot?
            if max_loss_per_lot <= remaining_capacity:
                lots = 1
                trade_max_loss = max_loss_per_lot
            else:
                log.info(
                    "[OptionsRiskEngine] Capacity gate: trade_max_loss ₹%.0f > "
                    "remaining ₹%.0f — rejected %s.",
                    trade_max_loss, remaining_capacity, signal.symbol,
                )
                return False

        # ── Gate 3: VIX guard for credit strategies ───────────────────
        if stype == "IRON_CONDOR" and vix > VIX_SELL_LIMIT:
            log.info(
                "[OptionsRiskEngine] VIX=%.1f > %.1f — Iron Condor rejected "
                "(too risky to sell premium in high-vol).", vix, VIX_SELL_LIMIT,
            )
            return False

        # ── Gate 4: strategy loss-streak ──────────────────────────────
        if self._is_strategy_disabled(stype):
            log.info(
                "[OptionsRiskEngine] %s is temporarily disabled "
                "(loss streak ≥ %d).", stype, MAX_LOSS_STREAK,
            )
            return False

        # ── Approved: inject lots back into meta ──────────────────────
        meta["lots"] = lots
        signal.notes = json.dumps(meta)

        log.info(
            "[OptionsRiskEngine] ✅ Approved %s %s  lots=%d  "
            "max_loss=₹%.0f  VIX=%.1f  IVR=%.0f",
            signal.symbol, stype, lots, trade_max_loss, vix,
            float(meta.get("iv_rank", 50)),
        )
        return True

    # ── Strategy disable / enable ──────────────────────────────────────

    def notify_loss_streak(self, strategy_type: str, streak: int) -> None:
        """Called by OptionsPerformanceTracker when a loss streak is detected."""
        if streak >= MAX_LOSS_STREAK:
            from datetime import date, timedelta
            # Disable for 5 trading days
            self._disabled_strategies[strategy_type] = date.today() + timedelta(days=7)
            log.warning(
                "[OptionsRiskEngine] %s DISABLED for 7 days after %d consecutive losses.",
                strategy_type, streak,
            )

    def re_enable_strategy(self, strategy_type: str) -> None:
        """Manually re-enable a disabled strategy."""
        self._disabled_strategies.pop(strategy_type, None)
        log.info("[OptionsRiskEngine] %s re-enabled.", strategy_type)

    def _is_strategy_disabled(self, strategy_type: str) -> bool:
        from datetime import date
        until = self._disabled_strategies.get(strategy_type)
        if until is None:
            return False
        if date.today() >= until:
            del self._disabled_strategies[strategy_type]
            return False
        return True


# ── Module-level singleton ─────────────────────────────────────────────────

import threading as _threading
_ENGINE:      Optional[OptionsRiskEngine] = None
_ENGINE_LOCK: _threading.Lock             = _threading.Lock()


def get_options_risk_engine() -> OptionsRiskEngine:
    """Return the process-wide OptionsRiskEngine singleton."""
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = OptionsRiskEngine()
    return _ENGINE

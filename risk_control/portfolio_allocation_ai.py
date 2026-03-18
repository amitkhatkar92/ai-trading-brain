"""
Portfolio Allocation AI — Layer 5 Agent 2
============================================
Controls position sizing, sector exposure limits, and ensures the
overall portfolio stays within its target allocation buckets.

Capital Allocation target:
  Large cap   → 40%
  Mid cap     → 30%
  Small cap   → 15%
  Options hedge → 15%
"""

from __future__ import annotations
from typing import List

from models.market_data  import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.trade_signal import TradeSignal, SignalType
from config import TOTAL_CAPITAL, MAX_RISK_PER_TRADE_PCT, ALLOCATION
from utils import get_logger, risk_per_trade
from learning_system.strategy_performance_tracker import get_performance_tracker

log = get_logger(__name__)

# Sector → cap-category mapping (simplified)
LARGE_CAP_SYMBOLS = {"RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
                     "HDFC", "KOTAKBANK", "LT", "AXISBANK", "SBIN"}
MID_CAP_SYMBOLS   = {"BANKBARODA", "PNB", "COALINDIA", "ONGC", "NTPC",
                     "TATASTEEL", "HINDALCO", "GLENMARK"}


class PortfolioAllocationAI:
    """Sizes each position according to capital allocation rules."""

    def __init__(self):
        log.info(f"[PortfolioAllocationAI] Initialised. Capital=\u20b9{TOTAL_CAPITAL:,.0f}")

    def size_positions(self, signals: List[TradeSignal],
                       snapshot: MarketSnapshot) -> List[TradeSignal]:
        sized: List[TradeSignal] = []
        for sig in signals:
            sig = self._size(sig, snapshot)
            if sig is not None:
                sized.append(sig)
        log.info("[PortfolioAllocationAI] %d signals sized.", len(sized))
        return sized

    # ─────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────

    def _size(self, sig: TradeSignal,
              snapshot: MarketSnapshot) -> TradeSignal | None:
        # Determine bucket capital
        bucket_capital = self._bucket_capital(sig, snapshot)
        if bucket_capital <= 0:
            log.info("[PortfolioAllocationAI] %s — bucket capital exhausted.", sig.symbol)
            return None

        # ── Risk Engine canonical formula ───────────────────────────────────────
        # qty = (account_equity * RISK_PER_TRADE) / abs(entry_price - stop_price)
        # This keeps risk-per-trade at exactly RISK_PER_TRADE% of total equity,
        # regardless of stop width.  The strategy layer must NOT touch this.
        qty = risk_per_trade(
            capital  = TOTAL_CAPITAL,          # always full account equity
            risk_pct = MAX_RISK_PER_TRADE_PCT,  # 1% risk / trade
            entry    = sig.entry_price,
            stop     = sig.stop_loss,
        )
        if qty <= 0:
            return None
        # Hard cap: notional cost must not exceed the strategy's bucket allocation
        if sig.entry_price > 0:
            max_qty_by_bucket = max(1, int(bucket_capital / sig.entry_price))
            qty = min(qty, max_qty_by_bucket)

        # ── Strategy performance weighting ────────────────────────────────────
        # Tilt capital toward high-expectancy strategies; scale back weak ones.
        # Weight is bounded [0.5×, 2.0×] so no single strategy can dominate.
        perf_weight   = get_performance_tracker().get_performance_weight(
                            sig.strategy_name)
        if perf_weight != 1.0:
            log.debug("[PortfolioAllocationAI] %s perf_weight=%.2f× (%s)",
                      sig.symbol, perf_weight, sig.strategy_name)
            qty = max(1, int(qty * perf_weight))

        sig.quantity = qty
        log.debug(f"[PortfolioAllocationAI] {sig.symbol} qty={qty} (cap=\u20b9{bucket_capital:,.0f})")
        return sig

    def _bucket_capital(self, sig: TradeSignal,
                        snapshot: MarketSnapshot) -> float:
        # In volatile/bear market → reduce position sizes
        reducer = 1.0
        if snapshot.volatility == VolatilityLevel.HIGH:
            reducer = 0.7
        elif snapshot.volatility == VolatilityLevel.EXTREME:
            reducer = 0.4
        elif snapshot.regime == RegimeLabel.BEAR_MARKET:
            reducer = 0.5

        if sig.signal_type in (SignalType.OPTIONS, SignalType.SPREAD):
            return TOTAL_CAPITAL * ALLOCATION["options_hedge"] * reducer

        sym = sig.symbol.upper()
        if sym in LARGE_CAP_SYMBOLS:
            return TOTAL_CAPITAL * ALLOCATION["large_cap"] * reducer
        elif sym in MID_CAP_SYMBOLS:
            return TOTAL_CAPITAL * ALLOCATION["mid_cap"] * reducer
        else:
            return TOTAL_CAPITAL * ALLOCATION["small_cap"] * reducer

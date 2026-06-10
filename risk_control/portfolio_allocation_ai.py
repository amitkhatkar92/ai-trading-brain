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

# Maximum fraction of TOTAL_CAPITAL allowed for a single trade.
# Must stay in sync with MAX_CAPITAL_PER_TRADE_PCT in execution_engine/order_manager.py
# (15.0%).  Enforcing it here — one layer earlier — means the OrderManager guard
# only ever fires as a true last-resort safety net, never as a normal reject path.
_MAX_SINGLE_TRADE_FRACTION = 0.15

# Maximum cumulative notional for any single symbol across ALL open positions.
# Prevents doubling up on one stock from exceeding 15% of total capital.
_MAX_SYMBOL_NOTIONAL_FRACTION = 0.15

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
        # Read open positions once per cycle to feed the cumulative notional guard.
        open_notional = self._compute_open_notional()
        sized: List[TradeSignal] = []
        for sig in signals:
            sig = self._size(sig, snapshot, open_notional)
            if sig is not None:
                sized.append(sig)
        log.info("[PortfolioAllocationAI] %d signals sized.", len(sized))
        return sized

    # ─────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────

    def _size(self, sig: TradeSignal,
              snapshot: MarketSnapshot,
              open_notional: dict | None = None) -> TradeSignal | None:
        # Determine bucket capital
        bucket_capital = self._bucket_capital(sig, snapshot)
        if bucket_capital <= 0:
            log.info("[PortfolioAllocationAI] %s — bucket capital exhausted.", sig.symbol)
            return None

        # ── Risk Engine canonical formula ────────────────────────────────────────
        # qty = (account_equity * RISK_PER_TRADE) / abs(entry_price - stop_price)
        # Scaled by confidence: stronger signals trade slightly larger, weaker
        # signals trade slightly smaller.  confidence is on a 0–10 scale;
        # normalised to 0–1 then mapped to [0.6×, 1.4×] of MAX_RISK_PER_TRADE_PCT.
        _conf_norm = max(0.0, min(sig.confidence / 10.0, 1.0)) if sig.confidence > 0 else 0.7
        _risk_pct  = MAX_RISK_PER_TRADE_PCT * (0.6 + _conf_norm * 0.8)
        qty = risk_per_trade(
            capital  = TOTAL_CAPITAL,
            risk_pct = _risk_pct,
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

        # Hard per-trade capital cap: ensure notional never exceeds 15% of TOTAL_CAPITAL
        # so the OrderManager guard never triggers during normal operation.
        if sig.entry_price > 0:
            max_qty_by_capital = max(1, int(TOTAL_CAPITAL * _MAX_SINGLE_TRADE_FRACTION / sig.entry_price))
            if qty > max_qty_by_capital:
                log.debug("[PortfolioAllocationAI] %s qty capped by 15%% capital limit: %d → %d",
                          sig.symbol, qty, max_qty_by_capital)
                qty = max_qty_by_capital

        # Cumulative per-symbol notional guard: reject or reduce if this symbol
        # already has open notional and the combined total would exceed 15% of capital.
        if open_notional is not None and sig.entry_price > 0:
            current_sym_notional = open_notional.get(sig.symbol.upper(), 0.0)
            new_notional  = qty * sig.entry_price
            symbol_cap    = TOTAL_CAPITAL * _MAX_SYMBOL_NOTIONAL_FRACTION
            if current_sym_notional + new_notional > symbol_cap:
                allowed_notional = max(0.0, symbol_cap - current_sym_notional)
                if allowed_notional < sig.entry_price:  # can't fit even 1 share
                    log.info(
                        "[PortfolioAllocationAI] %s REJECTED — cumulative notional cap: "
                        "existing=₹%.0f new=₹%.0f cap=₹%.0f",
                        sig.symbol, current_sym_notional, new_notional, symbol_cap,
                    )
                    return None
                capped_qty = max(1, int(allowed_notional / sig.entry_price))
                if capped_qty < qty:
                    log.debug(
                        "[PortfolioAllocationAI] %s qty capped by cumulative notional: "
                        "%d → %d (existing=₹%.0f cap=₹%.0f)",
                        sig.symbol, qty, capped_qty, current_sym_notional, symbol_cap,
                    )
                    qty = capped_qty

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

    def _compute_open_notional(self) -> dict:
        """Return {SYMBOL: open_notional_₹} for currently open positions from paper_trades.csv.
        Uses OPEN/CLOSE row accounting: OPEN adds notional, CLOSE subtracts.
        Returns empty dict on any read failure — cumulative guard is then skipped.
        """
        from pathlib import Path
        import csv as _csv
        result: dict = {}
        csv_path = Path(__file__).parent.parent / "data" / "paper_trades.csv"
        if not csv_path.exists():
            return result
        try:
            with csv_path.open(newline="", encoding="utf-8") as f:
                rows = list(_csv.DictReader(f))
            for row in rows:
                sym   = row.get("symbol", "").upper()
                event = row.get("event", "").upper()   # CSV column is "event", not "action"
                try:
                    qty   = int(float(row.get("quantity", 0)))
                    price = float(row.get("entry_price", 0))
                except (ValueError, TypeError):
                    continue
                notional = qty * price
                if event in ("OPEN", "REENTRY_OPEN"):
                    result[sym] = result.get(sym, 0.0) + notional
                elif event in ("CLOSE", "CANCELLED"):
                    result[sym] = max(0.0, result.get(sym, 0.0) - notional)
        except Exception as exc:
            log.debug("[PortfolioAllocationAI] Could not read open notional: %s", exc)
        return result

"""
Capital Risk Engine — Meta-Control Layer
==========================================
Controls dynamic capital exposure and enforces institutional-grade
position sizing.

Pipeline position:
    Strategy Lab
        ↓
    Capital Risk Engine   ← THIS MODULE
        ↓
    Risk Control

Key functions
─────────────
1. Market-condition-based portfolio exposure limits
   • Bull Trend  → deploy up to 80% of capital
   • Range       → 50%
   • Bear        → 30%
   • Volatile    → 40%  (need room for hedges)

2. VIX override ceiling (hard limit regardless of regime)
   • VIX > 35  → 10%  (crash mode)
   • VIX > 28  → 25%
   • VIX > 22  → 40%
   • VIX > 18  → 65%

3. Drawdown-based exposure reduction
   • >10% DD → 25% of normal    (halt recovery mode)
   • > 7% DD → 50% of normal
   • > 4% DD → 75% of normal

4. Per-strategy capital bucket allocation

5. Institutional position sizing formula:
       Position Size = Risk Amount / Stop Loss Distance
   where Risk Amount = Strategy Budget × MAX_RISK_PER_TRADE_PCT
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from models.market_data  import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.trade_signal import TradeSignal
from models.portfolio    import Portfolio
from config import TOTAL_CAPITAL, MAX_RISK_PER_TRADE_PCT
from utils import get_logger

log = get_logger(__name__)

# ── Regime → max deployment fraction ──────────────────────────────────────
_EXPOSURE_MAP: Dict[str, float] = {
    RegimeLabel.BULL_TREND.value:   0.80,
    RegimeLabel.RANGE_MARKET.value: 0.50,
    RegimeLabel.BEAR_MARKET.value:  0.30,
    RegimeLabel.VOLATILE.value:     0.40,
}

# ── VIX ceiling overrides (evaluated top-to-bottom; first match wins) ──────
_VIX_CEILINGS: List[Tuple[float, float]] = [
    (35.0, 0.10),   # Crash
    (28.0, 0.25),   # Extreme panic
    (22.0, 0.40),   # High fear
    (18.0, 0.65),   # Elevated
    ( 0.0, 1.00),   # Normal — no restriction
]

# ── Drawdown reducers (evaluated top-to-bottom; first match wins) ──────────
_DRAWDOWN_REDUCERS: List[Tuple[float, float]] = [
    (0.10, 0.25),   # >10% DD → 25% of deployable
    (0.07, 0.50),   # > 7% DD → 50%
    (0.04, 0.75),   # > 4% DD → 75%
    (0.00, 1.00),   # No drawdown → full deployment
]

# ── Per-strategy capital share (fraction of deployable capital) ────────────
# These represent the maximum slice per strategy type.
_STRATEGY_SHARE: Dict[str, float] = {
    "Breakout_Volume":          0.28,
    "Momentum_Retest":          0.18,
    "Mean_Reversion":           0.22,
    "Bull_Call_Spread":         0.12,
    "Iron_Condor_Range":        0.18,
    "Hedging_Model":            0.10,
    "Short_Straddle_IV_Spike":  0.14,
    "Long_Straddle_Pre_Event":  0.08,
    "Futures_Basis_Arb":        0.14,
    "ETF_NAV_Arb":              0.12,
}
_DEFAULT_SHARE = 0.10   # fallback for unknown / evolved variants

# ── Maximum number of simultaneous positions (correlation control) ─────────
_MAX_POSITIONS = 8


class CapitalRiskEngine:
    """
    Institutional-grade dynamic capital allocation engine.

    Determines how much capital to deploy per cycle, allocates that
    capital across active strategies, and sizes each position using
    the risk-per-trade formula before the signal reaches Risk Control.
    """

    def __init__(self):
        log.info(f"[CapitalRiskEngine] Initialised. Total capital=\u20b9{TOTAL_CAPITAL:,.0f}")

    # ─────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────

    def allocate(
        self,
        signals: List[TradeSignal],
        snapshot: MarketSnapshot,
        portfolio: Optional[Portfolio] = None,
    ) -> List[TradeSignal]:
        """
        Apply dynamic capital allocation to strategy-assigned signals.

        Steps:
          1. Compute total deployable capital (regime + VIX + drawdown)
          2. Allocate per-strategy budget
          3. Size each position using institutional formula
          4. Enforce total exposure cap  (max _MAX_POSITIONS live)

        Returns signals with updated ``quantity``; signals that cannot
        be sized (zero budget, stop too tight, exposure cap) are dropped.
        """
        deployable = self._compute_deployable_capital(snapshot, portfolio)
        self._print_allocation_report(signals, snapshot, portfolio, deployable)

        result: List[TradeSignal] = []
        allocated_total = 0.0

        for sig in signals:
            if len(result) >= _MAX_POSITIONS:
                log.info("[CRE] Max position limit (%d) reached — remaining signals skipped.",
                         _MAX_POSITIONS)
                break

            budget = self._strategy_budget(sig.strategy_name, deployable)
            qty    = self._size_position(sig, budget)

            if qty <= 0:
                log.debug("[CRE] %s \u2192 qty=0 (budget=\u20b9%s SL=%.2f) \u2014 skipped.",
                          sig.symbol, f"{budget:,.0f}", sig.stop_loss)
                continue

            trade_cost = qty * sig.entry_price
            if allocated_total + trade_cost > deployable * 1.05:
                log.info("[CRE] %s skipped \u2014 total exposure limit reached (\u20b9%s / \u20b9%s).",
                         sig.symbol, f"{allocated_total:,.0f}", f"{deployable:,.0f}")
                continue

            sig.quantity  = qty
            sig.notes    += f" | CRE: budget=₹{budget:,.0f} qty={qty}"
            result.append(sig)
            allocated_total += trade_cost

        utilisation = (allocated_total / deployable * 100) if deployable else 0
        log.info(
            "[CRE] %d/%d signals sized. Deployable=\u20b9%s  "
            "Allocated=\u20b9%s (%.0f%% utilisation)",
            len(result), len(signals),
            f"{deployable:,.0f}", f"{allocated_total:,.0f}", utilisation,
        )
        return result

    def deployable_capital(
        self,
        snapshot: MarketSnapshot,
        portfolio: Optional[Portfolio] = None,
    ) -> float:
        """Public accessor — returns the deployable capital figure."""
        return self._compute_deployable_capital(snapshot, portfolio)

    # ─────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────

    def _compute_deployable_capital(
        self,
        snapshot: MarketSnapshot,
        portfolio: Optional[Portfolio],
    ) -> float:
        """Deployable = Total Capital × regime_exposure × vix_ceiling × dd_reducer."""
        regime_exposure = _EXPOSURE_MAP.get(snapshot.regime.value, 0.50)

        # VIX ceiling
        vix_ceiling = 1.00
        for threshold, ceiling in _VIX_CEILINGS:
            if snapshot.vix >= threshold:
                vix_ceiling = ceiling
                break

        # Use the more conservative of regime and VIX constraints
        base_exposure = min(regime_exposure, vix_ceiling)

        # Drawdown reducer
        dd_reducer = 1.00
        if portfolio:
            dd = portfolio.drawdown_pct
            for threshold, reducer in _DRAWDOWN_REDUCERS:
                if dd >= threshold:
                    dd_reducer = reducer
                    break

        return TOTAL_CAPITAL * base_exposure * dd_reducer

    def _strategy_budget(self, strategy_name: str, deployable: float) -> float:
        """Capital budget allocated to this specific strategy."""
        share = _STRATEGY_SHARE.get(strategy_name)
        if share is None:
            # Evolved variant: inherit base strategy share
            for base, base_share in _STRATEGY_SHARE.items():
                if strategy_name.startswith(base):
                    share = base_share
                    break
        if share is None:
            share = _DEFAULT_SHARE
        return deployable * share

    def _size_position(self, sig: TradeSignal, budget: float) -> int:
        """
        Institutional position sizing:
            qty = Risk Amount / Stop Distance

        Risk Amount = budget × MAX_RISK_PER_TRADE_PCT
        Stop Distance = |entry - stop_loss|

        Result is also capped so the notional cost ≤ strategy budget.
        """
        sl_distance = abs(sig.entry_price - sig.stop_loss)
        if sl_distance < 0.001 or sig.entry_price <= 0:
            return 0

        risk_amount   = budget * MAX_RISK_PER_TRADE_PCT
        qty_by_risk   = int(risk_amount / sl_distance)

        # Hard cap: can't buy more than the budget allows
        qty_by_budget = int(budget / sig.entry_price)

        return min(qty_by_risk, qty_by_budget)

    def _print_allocation_report(
        self,
        signals: List[TradeSignal],
        snapshot: MarketSnapshot,
        portfolio: Optional[Portfolio],
        deployable: float,
    ) -> None:
        """Log a formatted capital allocation table for this cycle."""
        dd_pct  = portfolio.drawdown_pct if portfolio else 0.0
        exp_pct = (deployable / TOTAL_CAPITAL * 100) if TOTAL_CAPITAL else 0

        w = 72
        log.info("═" * w)
        log.info(
            "  CAPITAL RISK ENGINE  |  Regime: %-12s  VIX: %.1f",
            snapshot.regime.value, snapshot.vix,
        )
        log.info(
            "  Total Capital: ₹%s  |  Deployable: ₹%s (%.0f%%)",
            f"{TOTAL_CAPITAL:,.0f}", f"{deployable:,.0f}", exp_pct,
        )
        if dd_pct > 0.001:
            log.info(
                "  ⚠️  Portfolio Drawdown: %.1f%% — exposure reduced",
                dd_pct * 100,
            )
        log.info("  %-32s  %-14s  %s", "Strategy", "Budget", "Position Formula")
        log.info("  " + "─" * (w - 2))

        seen: set = set()
        for sig in signals:
            if sig.strategy_name in seen:
                continue
            seen.add(sig.strategy_name)
            budget   = self._strategy_budget(sig.strategy_name, deployable)
            sl_dist  = abs(sig.entry_price - sig.stop_loss)
            risk_amt = budget * MAX_RISK_PER_TRADE_PCT
            ex_qty   = int(risk_amt / sl_dist) if sl_dist > 0 else 0
            log.info(
                "  %-32s  ₹%10s  Risk=₹%s / SL=%.2f → ~%d shares",
                sig.strategy_name,
                f"{budget:,.0f}",
                f"{risk_amt:,.0f}",
                sl_dist, ex_qty,
            )

        log.info("  " + "─" * (w - 2))
        log.info(
            "  Cash reserved: ₹%s (%.0f%%)",
            f"{TOTAL_CAPITAL - deployable:,.0f}",
            (TOTAL_CAPITAL - deployable) / TOTAL_CAPITAL * 100,
        )
        log.info("═" * w)

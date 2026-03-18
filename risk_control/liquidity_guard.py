"""
Liquidity Capacity Guard — Risk Control Layer
================================================
Prevents market-impact slippage as capital scales by enforcing an
ADV-based position ceiling on every signal before it reaches execution.

Rule:
    position_value ≤ ADV × MAX_ADV_PCT

Why this matters
----------------
A strategy can show PF=1.6 at ₹20 k capital and collapse to PF<1 at
₹2 crore because larger orders move the market before they fill.  This
guard makes the scaling ceiling explicit and enforces it automatically.

Behaviour
---------
• If a signal has no ADV data (adv_crore == 0) it uses a conservative
  fallback derived from the stock's LTP × assumed daily shares (see
  _fallback_adv_crore below).  This prevents the guard from silently
  losing effect when real ADV data is unavailable.

• If the stock's ADV is below MIN_ADV_CRORE the signal is REJECTED —
  the stock is too illiquid to trade at any capital level.

• Otherwise qty is CAPPED to the ADV ceiling.  If even 1 share exceeds
  the ceiling the signal is rejected (edge case for very thin counters).

• A periodic capacity report summarises the maximum capital the current
  watchlist can absorb without market impact.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List

from models.trade_signal import TradeSignal
from config import MIN_ADV_CRORE, MAX_ADV_PCT, TOTAL_CAPITAL
from utils import get_logger

log = get_logger(__name__)

# 1 crore = 10,000,000 INR
_CRORE = 1_00_00_000.0

# Conservative fallback: if ADV data is missing, assume a daily turnover
# equivalent to the stock trading 200,000 shares at its LTP.
# This keeps the guard active even without real broker ADV data.
_FALLBACK_SHARES_PER_DAY = 200_000


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LiquidityCheckResult:
    """Outcome of a single signal's liquidity check."""
    symbol:         str
    original_qty:   int
    approved_qty:   int          # 0 = rejected
    adv_crore:      float
    max_pos_inr:    float        # ADV × MAX_ADV_PCT  (in ₹)
    cap_applied:    bool         # True if qty was reduced
    rejection_reason: str        # "" if approved


@dataclass
class CapacityReport:
    """
    System-wide capacity snapshot.

    total_watchlist_capacity_crore
        Sum of (ADV × MAX_ADV_PCT) across all stocks currently in signals.
        This is how much ₹ the strategy can deploy simultaneously without
        breaching market-impact limits.

    capital_utilisation_pct
        TOTAL_CAPITAL / total_watchlist_capacity_crore × 100.
        <5%  → plenty of room
        5-20% → healthy range; the strategy is not yet capacity-bound
        >20% → scaling will start to hurt fills; consider adding stocks
        >100% → strategy is CAPACITY BOUND at current capital level
    """
    signals_checked:                int
    signals_capped:                 int
    signals_rejected:               int
    total_watchlist_capacity_crore: float
    capital_utilisation_pct:        float


# ─────────────────────────────────────────────────────────────────────────────
# Guard
# ─────────────────────────────────────────────────────────────────────────────

class LiquidityGuard:
    """
    ADV-based position ceiling applied inside the Risk Engine.

    Usage::

        guard = LiquidityGuard()
        approved = guard.filter(signals)          # in-place qty cap + rejection
        report   = guard.last_capacity_report()   # call after filter()
    """

    def __init__(self):
        self._last_report: CapacityReport | None = None
        log.info("[LiquidityGuard] Initialised. MIN_ADV=₹%.0f cr  MAX_ADV_PCT=%.0f%%",
                 MIN_ADV_CRORE, MAX_ADV_PCT * 100)

    # ── Public ──────────────────────────────────────────────────────────────

    def filter(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """
        Apply the liquidity ceiling to each signal.
        Returns the subset of signals that pass (with qty potentially capped).
        """
        approved:         List[TradeSignal]          = []
        results:          List[LiquidityCheckResult] = []
        total_cap_crore:  float                      = 0.0
        caps:             int                        = 0
        rejects:          int                        = 0

        for sig in signals:
            res = self._check(sig)
            results.append(res)
            total_cap_crore += res.max_pos_inr / _CRORE

            if res.rejection_reason:
                rejects += 1
                log.info("[LiquidityGuard] ❌ REJECTED %s — %s",
                         sig.symbol, res.rejection_reason)
            else:
                if res.cap_applied:
                    caps += 1
                    log.info(
                        "[LiquidityGuard] ⚠ CAPPED  %s  qty %d→%d "
                        "(ADV=₹%.0f cr, limit=₹%.0f)",
                        sig.symbol, res.original_qty, res.approved_qty,
                        res.adv_crore, res.max_pos_inr,
                    )
                    sig.quantity = res.approved_qty
                    sig.notes += (f" [LiqCap qty capped {res.original_qty}→{res.approved_qty}"
                                  f" ADV=₹{res.adv_crore:.0f}cr]")
                approved.append(sig)

        # Build capacity report
        cap_util = (TOTAL_CAPITAL / (_CRORE * total_cap_crore) * 100.0
                    if total_cap_crore > 0 else 0.0)
        self._last_report = CapacityReport(
            signals_checked                = len(signals),
            signals_capped                 = caps,
            signals_rejected               = rejects,
            total_watchlist_capacity_crore = total_cap_crore,
            capital_utilisation_pct        = cap_util,
        )
        self._log_report(self._last_report)
        log.info("[LiquidityGuard] %d/%d signals passed (%d capped, %d rejected).",
                 len(approved), len(signals), caps, rejects)
        return approved

    def last_capacity_report(self) -> CapacityReport | None:
        """Returns the CapacityReport produced during the last filter() call."""
        return self._last_report

    def capacity_summary(self) -> str:
        """Human-readable one-liner for dashboard / Telegram."""
        r = self._last_report
        if r is None:
            return "[LiquidityGuard] No data yet."
        util_tag = ("✅ healthy" if r.capital_utilisation_pct < 20
                    else "⚠ approaching limit" if r.capital_utilisation_pct < 80
                    else "🔴 CAPACITY BOUND")
        return (
            f"[LiquidityGuard] Capacity: ₹{r.total_watchlist_capacity_crore:.1f} cr  |  "
            f"Utilisation: {r.capital_utilisation_pct:.1f}%  {util_tag}  |  "
            f"Capped: {r.signals_capped}  Rejected: {r.signals_rejected}"
        )

    # ── Private ─────────────────────────────────────────────────────────────

    def _check(self, sig: TradeSignal) -> LiquidityCheckResult:
        adv = sig.adv_crore if sig.adv_crore > 0 else self._fallback_adv_crore(sig)
        original_qty = sig.quantity

        # ── Gate 1: minimum liquidity threshold ───────────────────────
        if adv < MIN_ADV_CRORE:
            return LiquidityCheckResult(
                symbol           = sig.symbol,
                original_qty     = original_qty,
                approved_qty     = 0,
                adv_crore        = adv,
                max_pos_inr      = adv * _CRORE * MAX_ADV_PCT,
                cap_applied      = False,
                rejection_reason = (f"ADV ₹{adv:.0f} cr < minimum ₹{MIN_ADV_CRORE:.0f} cr "
                                    f"— stock too illiquid"),
            )

        # ── Gate 2: position value vs ADV ceiling ─────────────────────
        max_pos_inr = adv * _CRORE * MAX_ADV_PCT
        current_pos_inr = sig.quantity * sig.entry_price

        if current_pos_inr <= max_pos_inr:
            # Within limits — no action required
            return LiquidityCheckResult(
                symbol           = sig.symbol,
                original_qty     = original_qty,
                approved_qty     = original_qty,
                adv_crore        = adv,
                max_pos_inr      = max_pos_inr,
                cap_applied      = False,
                rejection_reason = "",
            )

        # Over the ceiling — cap quantity
        max_qty = int(max_pos_inr / sig.entry_price) if sig.entry_price > 0 else 0
        if max_qty < 1:
            return LiquidityCheckResult(
                symbol           = sig.symbol,
                original_qty     = original_qty,
                approved_qty     = 0,
                adv_crore        = adv,
                max_pos_inr      = max_pos_inr,
                cap_applied      = False,
                rejection_reason = (f"Even 1 share (₹{sig.entry_price:.0f}) "
                                    f"exceeds ADV limit ₹{max_pos_inr:,.0f}"),
            )

        return LiquidityCheckResult(
            symbol           = sig.symbol,
            original_qty     = original_qty,
            approved_qty     = max_qty,
            adv_crore        = adv,
            max_pos_inr      = max_pos_inr,
            cap_applied      = True,
            rejection_reason = "",
        )

    @staticmethod
    def _fallback_adv_crore(sig: TradeSignal) -> float:
        """
        Conservative ADV estimate when real broker data is not available.
        Assumes _FALLBACK_SHARES_PER_DAY traded at current entry price.
        Keeps the guard active even in simulation with no ADV data.
        """
        if sig.entry_price <= 0:
            return 0.0
        return round(sig.entry_price * _FALLBACK_SHARES_PER_DAY / _CRORE, 2)

    @staticmethod
    def _log_report(r: CapacityReport) -> None:
        if r.total_watchlist_capacity_crore <= 0:
            return
        if r.capital_utilisation_pct > 80:
            log.warning(
                "[LiquidityGuard] 🔴 CAPACITY BOUND — capital utilisation %.1f%% "
                "(₹%.0f cr capital vs ₹%.1f cr watchlist capacity). "
                "Add more liquid stocks or reduce TOTAL_CAPITAL.",
                r.capital_utilisation_pct,
                TOTAL_CAPITAL / _CRORE,
                r.total_watchlist_capacity_crore,
            )
        elif r.capital_utilisation_pct > 20:
            log.warning(
                "[LiquidityGuard] ⚠ Approaching capacity — utilisation %.1f%%. "
                "Strategy will degrade if capital grows without expanding watchlist.",
                r.capital_utilisation_pct,
            )
        else:
            log.debug("[LiquidityGuard] ✅ Capacity OK — utilisation %.1f%%.",
                      r.capital_utilisation_pct)

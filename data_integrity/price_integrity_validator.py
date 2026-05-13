"""
Price Integrity Validator
=========================
Cross-source price validation layer.  Before any SL / adaptive exit / entry
fires, this module verifies the price against multiple independent criteria:

  1. Instrument sanity band  — is the raw price within known bounds?
  2. Cross-source agreement  — does Dhan agree with Yahoo within threshold?
  3. Intra-cycle plausibility — does the current quote agree with the LTP
     from the PREVIOUS cycle (i.e. no impossible intra-minute jump)?

A PRICE_INTEGRITY_FAILURE is raised when any criterion fails.  Callers (SL
gate, entry gate) must check the result BEFORE acting.

Classification:
    CLEAN              — all checks passed; safe to execute
    SANITY_FAILURE     — price outside instrument band
    SOURCE_DIVERGENCE  — Dhan and Yahoo differ > threshold
    STALE_DIVERGENCE   — current price deviates > threshold from recent cache
    FEED_DEGRADED      — one or more sources unavailable for this symbol

Usage:
    from data_integrity.price_integrity_validator import get_price_validator
    v = get_price_validator()

    result = v.validate(
        symbol="HINDALCO",
        candidate_price=998.27,          # the price about to be used for SL
        yahoo_price=1075.0,              # None if Yahoo was degraded
        feed_degraded=False,
        previous_ltp=1023.50,            # last confirmed LTP from prior cycle
    )
    if not result.ok:
        log.warning("[ExecutionIntegrity] SL_SUPPRESSED %s reason=%s", symbol, result.classification)
        return  # abort SL execution
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from data_integrity.instrument_registry import get_instrument_registry
from utils import get_logger

log = get_logger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────

# Maximum acceptable divergence between Dhan and Yahoo for the same symbol.
# If |Dhan - Yahoo| / reference > threshold → SOURCE_DIVERGENCE
CROSS_SOURCE_THRESHOLD: float = 0.05   # 5 %

# Maximum acceptable single-cycle price jump (intra-cycle plausibility check).
# Genuine limit-down / limit-up moves on NSE equity are capped at 20%.
# We use 15% to catch clearly wrong quotes before they reach the 20% circuit.
INTRA_CYCLE_THRESHOLD: float = 0.15    # 15 %

# How long a previous-LTP cache entry is considered valid for plausibility check
PREV_LTP_MAX_AGE_SEC: float = 3600.0   # 1 hour


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class IntegrityResult:
    ok:             bool
    symbol:         str
    candidate:      float
    classification: str         # CLEAN | SANITY_FAILURE | SOURCE_DIVERGENCE | STALE_DIVERGENCE | FEED_DEGRADED
    reason:         str = ""
    details:        dict = field(default_factory=dict)


# ── Validator ─────────────────────────────────────────────────────────────────

class PriceIntegrityValidator:
    """
    Stateful validator that maintains a rolling LTP cache per symbol.
    The cache is updated by `record_confirmed_price()` which the router
    should call for every confirmed live price it serves.
    """

    def __init__(self) -> None:
        self._registry = get_instrument_registry()
        # symbol → (ltp, monotonic_ts)
        self._prev_ltp: Dict[str, tuple[float, float]] = {}

    # ── Public interface ──────────────────────────────────────────────────────

    def validate(
        self,
        symbol:         str,
        candidate_price: float,
        yahoo_price:    Optional[float] = None,
        feed_degraded:  bool            = False,
        previous_ltp:   Optional[float] = None,
    ) -> IntegrityResult:
        """
        Run all integrity checks on `candidate_price`.

        Parameters
        ----------
        symbol          : bare NSE symbol (e.g. "HINDALCO")
        candidate_price : the price from the primary source (Dhan) that is
                          about to be used for an execution decision
        yahoo_price     : simultaneous Yahoo quote, if available (None = skip)
        feed_degraded   : True if the primary source was already flagged
                          as degraded in this cycle
        previous_ltp    : last confirmed LTP from prior successful cycle
                          (None → use internal cache)
        """
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")

        # ── 0. Feed degraded early exit ───────────────────────────────────
        if feed_degraded:
            reason = f"primary feed degraded for {sym} — no execution-grade price"
            log.warning("[PriceValidator] FEED_DEGRADED %s", reason)
            return IntegrityResult(
                ok=False, symbol=sym, candidate=candidate_price,
                classification="FEED_DEGRADED", reason=reason,
            )

        # ── 1. Instrument sanity band ─────────────────────────────────────
        band_result = self._registry.check_price(sym, candidate_price)
        if not band_result.ok and band_result.reason != "NO_BAND_REGISTERED":
            self._alert(sym, "SANITY_FAILURE", band_result.reason, candidate_price, yahoo_price)
            return IntegrityResult(
                ok=False, symbol=sym, candidate=candidate_price,
                classification="SANITY_FAILURE", reason=band_result.reason,
                details={"band_low": band_result.band_low, "band_high": band_result.band_high},
            )

        # ── 2. Cross-source agreement (Dhan vs Yahoo) ─────────────────────
        if yahoo_price is not None and yahoo_price > 0:
            reference = (candidate_price + yahoo_price) / 2.0
            divergence = abs(candidate_price - yahoo_price) / reference
            if divergence > CROSS_SOURCE_THRESHOLD:
                reason = (
                    f"Dhan={candidate_price:.2f} vs Yahoo={yahoo_price:.2f} "
                    f"divergence={divergence*100:.1f}% > {CROSS_SOURCE_THRESHOLD*100:.0f}% "
                    f"threshold for {sym}"
                )
                self._alert(sym, "SOURCE_DIVERGENCE", reason, candidate_price, yahoo_price)
                return IntegrityResult(
                    ok=False, symbol=sym, candidate=candidate_price,
                    classification="SOURCE_DIVERGENCE", reason=reason,
                    details={"dhan": candidate_price, "yahoo": yahoo_price, "divergence_pct": divergence * 100},
                )

        # ── 3. Intra-cycle plausibility (current vs previous LTP) ─────────
        prev = previous_ltp or self._get_cached_prev(sym)
        if prev and prev > 0:
            jump = abs(candidate_price - prev) / prev
            if jump > INTRA_CYCLE_THRESHOLD:
                reason = (
                    f"{sym} price jumped {jump*100:.1f}% in one cycle: "
                    f"prev={prev:.2f} → candidate={candidate_price:.2f} "
                    f"(threshold={INTRA_CYCLE_THRESHOLD*100:.0f}%)"
                )
                self._alert(sym, "STALE_DIVERGENCE", reason, candidate_price, yahoo_price)
                return IntegrityResult(
                    ok=False, symbol=sym, candidate=candidate_price,
                    classification="STALE_DIVERGENCE", reason=reason,
                    details={"prev_ltp": prev, "jump_pct": jump * 100},
                )

        # ── All checks passed ─────────────────────────────────────────────
        self._prev_ltp[sym] = (candidate_price, time.monotonic())
        return IntegrityResult(
            ok=True, symbol=sym, candidate=candidate_price,
            classification="CLEAN",
        )

    def record_confirmed_price(self, symbol: str, price: float) -> None:
        """
        Called by the MarketDataRouter after a price is served to the system.
        Populates the intra-cycle plausibility cache.
        """
        sym = symbol.upper()
        self._prev_ltp[sym] = (price, time.monotonic())

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_cached_prev(self, sym: str) -> Optional[float]:
        entry = self._prev_ltp.get(sym)
        if entry is None:
            return None
        ltp, ts = entry
        age = time.monotonic() - ts
        if age > PREV_LTP_MAX_AGE_SEC:
            return None          # cache too stale for plausibility comparison
        return ltp

    @staticmethod
    def _alert(sym: str, classification: str, reason: str,
               candidate: float, yahoo: Optional[float]) -> None:
        log.warning(
            "[PriceValidator] PRICE_INTEGRITY_FAILURE  classification=%s  "
            "symbol=%s  candidate=%.2f  yahoo=%s  reason: %s",
            classification, sym, candidate,
            f"{yahoo:.2f}" if yahoo else "N/A",
            reason,
        )
        # Telegram alert (best-effort — never raise)
        try:
            from notifications.notifier_manager import get_notifier
            get_notifier().send_alert(
                f"⚠️ [PriceAudit] PRICE_INTEGRITY_FAILURE\n"
                f"Symbol: `{sym}`\n"
                f"Classification: `{classification}`\n"
                f"Candidate: ₹{candidate:.2f}\n"
                f"Yahoo: {'₹'+str(round(yahoo,2)) if yahoo else 'N/A'}\n"
                f"Reason: {reason}"
            )
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_VALIDATOR_INSTANCE: Optional["PriceIntegrityValidator"] = None


def get_price_validator() -> "PriceIntegrityValidator":
    global _VALIDATOR_INSTANCE
    if _VALIDATOR_INSTANCE is None:
        _VALIDATOR_INSTANCE = PriceIntegrityValidator()
    return _VALIDATOR_INSTANCE

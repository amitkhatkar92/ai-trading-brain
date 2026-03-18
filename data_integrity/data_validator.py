"""
Data Integrity Engine — DataValidator
======================================
First gate of the system. Runs before ANY intelligence layer touches the data.

Validation Rules:
  • Required fields present (vix, pcr, breadth, indices)
  • Price change sanity  — flag if Nifty50 moves > 15% in one tick
  • VIX sanity          — VIX range 5–120 (historical extremes)
  • PCR sanity          — PCR range 0.3–5.0
  • Breadth sanity      — breadth 0.0–1.0
  • Volume sanity       — volume > 0, not unexpectedly zero
  • Timestamp freshness — data not older than MAX_STALE_SECONDS
  • Index cross-check   — Nifty and BankNifty must move in same direction
                          when |change| > 3% (structural linkage)

Returns a ValidationReport dataclass with:
  • passed: bool
  • warnings: list[str]    — non-blocking issues
  • errors:   list[str]    — blocking issues
  • clean_data: dict       — sanitised snapshot dict (NaN→0 etc.)
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from utils import get_logger

log = get_logger(__name__)

# ── Tunable thresholds ────────────────────────────────────────────────────
MAX_NIFTY_TICK_CHANGE_PCT = 15.0   # single-tick move beyond this = anomaly
MAX_STALE_SECONDS         = 300    # 5 minutes; above = stale feed
VIX_MIN, VIX_MAX          = 5.0, 120.0
PCR_MIN, PCR_MAX           = 0.3,   5.0
BREADTH_MIN, BREADTH_MAX   = 0.0,   1.0
MIN_VOLUME                 = 0     # zero volume is suspicious in live session


@dataclass
class ValidationReport:
    passed:     bool
    warnings:   list[str] = field(default_factory=list)
    errors:     list[str] = field(default_factory=list)
    clean_data: dict      = field(default_factory=dict)

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (f"[DataValidator] {status} | "
                f"Errors={len(self.errors)} | Warnings={len(self.warnings)}")


class DataValidator:
    """
    Validates raw market data dictionary before it is used by any AI layer.

    Usage::
        validator = DataValidator()
        report = validator.validate(raw_dict)
        if not report.passed:
            # skip cycle or use last known good data
    """

    def __init__(self) -> None:
        self._last_nifty_close: float | None = None
        log.info("[DataValidator] Initialised. Thresholds: "
                 "MaxTickChg=%.0f%% | MaxStale=%ds | VIX=[%.0f,%.0f]",
                 MAX_NIFTY_TICK_CHANGE_PCT, MAX_STALE_SECONDS,
                 VIX_MIN, VIX_MAX)

    # ── Public API ────────────────────────────────────────────────────────
    def validate(self, raw: dict[str, Any]) -> ValidationReport:
        errors:   list[str] = []
        warnings: list[str] = []

        # 1. Required fields
        self._check_required_fields(raw, errors)

        # 2. Numeric range checks
        self._check_vix(raw, errors, warnings)
        self._check_pcr(raw, errors, warnings)
        self._check_breadth(raw, errors, warnings)
        self._check_volume(raw, warnings)

        # 3. Price-spike check
        self._check_price_spike(raw, errors, warnings)

        # 4. Timestamp freshness
        self._check_freshness(raw, warnings)

        # 5. Cross-asset structural check
        self._check_index_correlation(raw, warnings)

        # 6. Sanitise NaN / Inf values
        clean = self._sanitise(raw)

        passed = len(errors) == 0
        report = ValidationReport(
            passed=passed,
            warnings=warnings,
            errors=errors,
            clean_data=clean,
        )
        # Update last-known Nifty close for next-tick comparison
        nifty = raw.get("indices", {}).get("NIFTY50")
        if nifty and isinstance(nifty, (int, float)) and nifty > 0:
            self._last_nifty_close = nifty

        if not passed:
            log.error("[DataValidator] VALIDATION FAILED — %d error(s): %s",
                      len(errors), "; ".join(errors))
        elif warnings:
            log.warning("[DataValidator] PASS (with %d warning(s)): %s",
                        len(warnings), "; ".join(warnings))
        else:
            log.info("[DataValidator] All checks passed.")
        return report

    # ── Private helpers ───────────────────────────────────────────────────
    @staticmethod
    def _check_required_fields(raw: dict, errors: list[str]) -> None:
        required = ["vix", "pcr", "breadth", "indices"]
        for key in required:
            if key not in raw or raw[key] is None:
                errors.append(f"Missing required field: '{key}'")

    @staticmethod
    def _check_vix(raw: dict, errors: list[str], warnings: list[str]) -> None:
        vix = raw.get("vix")
        if vix is None:
            return
        if not isinstance(vix, (int, float)) or math.isnan(vix) or math.isinf(vix):
            errors.append(f"VIX is not a valid number: {vix}")
        elif not (VIX_MIN <= vix <= VIX_MAX):
            errors.append(f"VIX={vix:.1f} out of expected range [{VIX_MIN},{VIX_MAX}]")
        elif vix > 60:
            warnings.append(f"VIX={vix:.1f} is extreme — systemic risk event likely")

    @staticmethod
    def _check_pcr(raw: dict, errors: list[str], warnings: list[str]) -> None:
        pcr = raw.get("pcr")
        if pcr is None:
            return
        if not isinstance(pcr, (int, float)) or math.isnan(pcr) or math.isinf(pcr):
            errors.append(f"PCR is not a valid number: {pcr}")
        elif not (PCR_MIN <= pcr <= PCR_MAX):
            errors.append(f"PCR={pcr:.2f} out of expected range [{PCR_MIN},{PCR_MAX}]")

    @staticmethod
    def _check_breadth(raw: dict, errors: list[str], warnings: list[str]) -> None:
        breadth = raw.get("breadth")
        if breadth is None:
            return
        if not isinstance(breadth, (int, float)) or math.isnan(breadth):
            errors.append(f"Breadth is not a valid number: {breadth}")
        elif not (BREADTH_MIN <= breadth <= BREADTH_MAX):
            errors.append(f"Breadth={breadth:.2f} out of range [0,1]")
        elif breadth < 0.1:
            warnings.append(f"Breadth={breadth:.0%} — near-zero advance-decline ratio")

    @staticmethod
    def _check_volume(raw: dict, warnings: list[str]) -> None:
        volume = raw.get("volume")
        if volume is None:
            return  # optional field
        if isinstance(volume, (int, float)) and volume <= MIN_VOLUME:
            warnings.append(f"Reported volume={volume} — possible feed issue")

    def _check_price_spike(self, raw: dict,
                           errors: list[str], warnings: list[str]) -> None:
        indices = raw.get("indices", {})
        nifty   = indices.get("NIFTY50") if isinstance(indices, dict) else None
        if nifty is None or self._last_nifty_close is None:
            return
        change_pct = abs(nifty - self._last_nifty_close) / self._last_nifty_close * 100
        if change_pct > MAX_NIFTY_TICK_CHANGE_PCT:
            errors.append(
                f"Nifty50 price spike: {self._last_nifty_close:.0f} → {nifty:.0f} "
                f"({change_pct:+.1f}%) exceeds {MAX_NIFTY_TICK_CHANGE_PCT}% threshold. "
                f"Possible bad tick — data rejected."
            )
        elif change_pct > 5.0:
            warnings.append(
                f"Large Nifty tick: {change_pct:.1f}% — verify feed integrity"
            )

    @staticmethod
    def _check_freshness(raw: dict, warnings: list[str]) -> None:
        ts = raw.get("timestamp")
        if ts is None or not isinstance(ts, datetime):
            return
        now  = datetime.now(timezone.utc).replace(tzinfo=None)
        ts_n = ts.replace(tzinfo=None) if ts.tzinfo else ts
        age  = (now - ts_n).total_seconds()
        if age > MAX_STALE_SECONDS:
            warnings.append(
                f"Data timestamp is {age:.0f}s old — feed may be stale "
                f"(threshold={MAX_STALE_SECONDS}s)"
            )

    @staticmethod
    def _check_index_correlation(raw: dict, warnings: list[str]) -> None:
        """
        When Nifty moves > 3%, BankNifty should move in the same direction.
        A divergence is structurally impossible and suggests a feed error.
        """
        indices = raw.get("indices", {})
        if not isinstance(indices, dict):
            return
        nifty     = indices.get("NIFTY50",    0.0)
        banknifty = indices.get("BANKNIFTY",  0.0)
        if not (nifty and banknifty):
            return
        nchg = raw.get("nifty_chg", 0.0)
        bnchg = raw.get("banknifty_chg", 0.0)
        if abs(nchg) > 3.0 and (nchg * bnchg < 0):
            warnings.append(
                f"Index divergence: Nifty50={nchg:+.1f}% vs BankNifty={bnchg:+.1f}% "
                f"— structural mismatch, verify feed"
            )

    @staticmethod
    def _sanitise(raw: dict) -> dict:
        """Replace NaN/Inf floats with 0 in a shallow copy."""
        clean = {}
        for key, val in raw.items():
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                clean[key] = 0.0
            elif isinstance(val, dict):
                clean[key] = {
                    k: (0.0 if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
                    for k, v in val.items()
                }
            else:
                clean[key] = val
        return clean

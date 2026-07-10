"""validation/overfitting_detector.py — Detects overfitting by comparing IS vs OOS."""
from __future__ import annotations

from typing import Any

from iios.integration.research.backtesting.backtest_exceptions import OverfittingDetectedError


# ── Thresholds ────────────────────────────────────────────────────────────────
SHARPE_DEGRADATION_THRESHOLD = 0.50   # OOS Sharpe drops >50% vs IS → overfitting
RETURN_DEGRADATION_THRESHOLD = 0.60   # OOS return drops >60% vs IS → overfitting
MIN_TRADE_COUNT              = 20     # fewer trades → unreliable stats


class OverfittingScore:
    """Result of the overfitting detection analysis."""

    def __init__(
        self,
        is_metrics:  dict[str, Any],
        oos_metrics: dict[str, Any],
    ) -> None:
        self.is_metrics  = is_metrics
        self.oos_metrics = oos_metrics
        self.score: float = 0.0        # 0.0 = no overfit, 1.0 = severe overfit
        self.flags: list[str] = []
        self.verdict: str = "unknown"
        self._compute()

    def _compute(self) -> None:
        score = 0.0

        is_sharpe  = self.is_metrics.get("sharpe_ratio", 0.0) or 0.0
        oos_sharpe = self.oos_metrics.get("sharpe_ratio", 0.0) or 0.0
        if is_sharpe > 0:
            sharpe_deg = max(0.0, (is_sharpe - oos_sharpe) / is_sharpe)
            if sharpe_deg > SHARPE_DEGRADATION_THRESHOLD:
                score += 0.4
                self.flags.append(
                    f"Sharpe degraded {sharpe_deg:.1%} (IS={is_sharpe:.2f}, OOS={oos_sharpe:.2f})"
                )

        is_ret  = self.is_metrics.get("total_return_pct",  0.0) or 0.0
        oos_ret = self.oos_metrics.get("total_return_pct", 0.0) or 0.0
        if is_ret > 0:
            ret_deg = max(0.0, (is_ret - oos_ret) / is_ret)
            if ret_deg > RETURN_DEGRADATION_THRESHOLD:
                score += 0.3
                self.flags.append(
                    f"Return degraded {ret_deg:.1%} (IS={is_ret:.2%}, OOS={oos_ret:.2%})"
                )

        is_trades  = self.is_metrics.get("total_trades", 0) or 0
        oos_trades = self.oos_metrics.get("total_trades", 0) or 0
        if is_trades < MIN_TRADE_COUNT or oos_trades < MIN_TRADE_COUNT:
            score += 0.2
            self.flags.append(
                f"Insufficient trades (IS={is_trades}, OOS={oos_trades}, min={MIN_TRADE_COUNT})"
            )

        if oos_ret < 0 and is_ret > 0:
            score += 0.1
            self.flags.append("OOS return is negative while IS return is positive")

        self.score   = min(1.0, score)
        self.verdict = (
            "overfit"  if self.score >= 0.5 else
            "marginal" if self.score >= 0.3 else
            "clean"
        )

    @property
    def is_overfit(self) -> bool:
        return self.verdict == "overfit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "score":   round(self.score, 4),
            "verdict": self.verdict,
            "flags":   list(self.flags),
            "is_overfit": self.is_overfit,
        }


class OverfittingDetector:
    """
    Detects overfitting by comparing in-sample vs out-of-sample metrics.

    Raise OverfittingDetectedError if the strategy is severely overfit
    and strict mode is enabled.
    """

    def detect(
        self,
        is_metrics:  dict[str, Any],
        oos_metrics: dict[str, Any],
        *,
        strict: bool = False,
    ) -> OverfittingScore:
        """
        Compute an OverfittingScore.

        strict – if True, raise OverfittingDetectedError when score >= 0.5.
        """
        ofs = OverfittingScore(is_metrics, oos_metrics)
        if strict and ofs.is_overfit:
            raise OverfittingDetectedError(
                f"Overfitting detected (score={ofs.score:.2f}): "
                + "; ".join(ofs.flags)
            )
        return ofs

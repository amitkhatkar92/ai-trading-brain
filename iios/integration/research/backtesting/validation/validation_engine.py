"""validation/validation_engine.py — Orchestrates all validation passes."""
from __future__ import annotations

import logging
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import ValidationStatus
from iios.integration.research.backtesting.backtest_exceptions import BacktestValidationFrameworkError
from iios.integration.research.backtesting.core.backtest_result import BacktestResult
from iios.integration.research.backtesting.validation.out_of_sample_validator import (
    OutOfSampleValidator,
    OOSSplit,
)
from iios.integration.research.backtesting.validation.overfitting_detector import (
    OverfittingDetector,
    OverfittingScore,
)
from iios.integration.research.backtesting.validation.robustness_analyzer import (
    RobustnessAnalyzer,
)
from iios.integration.research.backtesting.validation.walk_forward_validator import (
    WalkForwardValidator,
    WalkForwardWindow,
)

_log = logging.getLogger(__name__)


class ValidationResult:
    """Aggregated result from all validation passes."""

    def __init__(self, backtest_id: str) -> None:
        self.backtest_id   = backtest_id
        self.status        = ValidationStatus.PENDING
        self.oos_split:    Optional[OOSSplit]       = None
        self.wf_windows:   list[WalkForwardWindow]  = []
        self.overfit_score: Optional[OverfittingScore] = None
        self.robustness:   Optional[dict[str, Any]] = None
        self.errors:       list[str]                = []
        self.warnings:     list[str]                = []

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "backtest_id":   self.backtest_id,
            "status":        self.status.value,
            "errors":        list(self.errors),
            "warnings":      list(self.warnings),
            "oos_split":     self.oos_split.to_dict() if self.oos_split else None,
            "wf_windows":    [w.to_dict() for w in self.wf_windows],
            "overfit_score": self.overfit_score.to_dict() if self.overfit_score else None,
            "robustness":    self.robustness,
            "passed":        self.passed,
        }


class ValidationEngine:
    """
    Orchestrates IS/OOS split, walk-forward analysis, robustness testing,
    and overfitting detection for a completed BacktestResult.
    """

    def __init__(self) -> None:
        self._oos_validator     = OutOfSampleValidator()
        self._wf_validator      = WalkForwardValidator()
        self._robustness        = RobustnessAnalyzer()
        self._overfit_detector  = OverfittingDetector()
        self._validated         = 0

    def validate(
        self,
        result:          BacktestResult,
        is_metrics:      Optional[dict[str, Any]] = None,
        oos_metrics:     Optional[dict[str, Any]] = None,
        *,
        oos_fraction:    float = 0.30,
        wf_folds:        int   = 5,
        strict_overfit:  bool  = False,
        perturbation_curves: Optional[list[list[tuple[float, float]]]] = None,
    ) -> ValidationResult:
        """
        Run all configured validation passes on a BacktestResult.

        is_metrics / oos_metrics – pre-computed metrics dicts from separate IS and
            OOS runs.  If not supplied, the full result.metrics is used for both
            (provides limited overfitting detection).
        """
        vr = ValidationResult(result.backtest_id)
        vr.status = ValidationStatus.RUNNING
        self._validated += 1

        try:
            # 1. IS/OOS split info
            timestamps = [ts for ts, _ in result.equity_curve]
            if timestamps:
                vr.oos_split = self._oos_validator.split(timestamps, oos_fraction)

            # 2. Walk-forward windows
            if timestamps and wf_folds > 0:
                try:
                    vr.wf_windows = self._wf_validator.generate_windows(
                        timestamps,
                        n_folds     = wf_folds,
                        oos_fraction = oos_fraction / wf_folds,
                    )
                except Exception as exc:
                    vr.warnings.append(f"Walk-forward generation skipped: {exc}")

            # 3. Overfitting detection
            _is  = is_metrics  or result.metrics
            _oos = oos_metrics or result.metrics
            try:
                vr.overfit_score = self._overfit_detector.detect(
                    _is, _oos, strict=strict_overfit
                )
                if vr.overfit_score.is_overfit:
                    vr.warnings.append(
                        f"Overfitting detected (score={vr.overfit_score.score:.2f})"
                    )
            except Exception as exc:
                vr.warnings.append(f"Overfitting detection failed: {exc}")

            # 4. Robustness analysis
            if perturbation_curves:
                vr.robustness = self._robustness.perturbation_test(perturbation_curves)

            # 5. Final verdict
            has_critical = any("error" in e.lower() for e in vr.errors)
            vr.status = ValidationStatus.FAILED if (vr.errors or has_critical) \
                        else ValidationStatus.PASSED

        except Exception as exc:
            vr.errors.append(str(exc))
            vr.status = ValidationStatus.FAILED
            _log.error("[ValidationEngine] backtest=%s failed: %s", result.backtest_id, exc)

        return vr

    def stats(self) -> dict[str, Any]:
        return {"validated": self._validated}

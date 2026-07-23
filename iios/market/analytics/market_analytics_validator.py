"""
market_analytics_validator.py — iios.market.analytics
=======================================================
Request and output validation for the Market Analytics Framework.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import dataclasses
from typing import List, Tuple

from .constants import VERSION, ValidationCode
from .market_analytics_request import MarketAnalyticsRequest
from .market_analytics_response import MarketAnalyticsReport


@dataclasses.dataclass(frozen=True)
class AnalyticsValidationCheckResult:
    code:    ValidationCode
    passed:  bool
    message: str = ""


@dataclasses.dataclass(frozen=True)
class AnalyticsValidationResult:
    is_valid:      bool
    failed_checks: Tuple[AnalyticsValidationCheckResult, ...]
    passed_checks: Tuple[AnalyticsValidationCheckResult, ...]
    analytics_id:  str = ""

    @property
    def failure_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks]


class MarketAnalyticsValidator:
    """
    Validates :class:`~.market_analytics_request.MarketAnalyticsRequest`
    objects before processing and analytics outputs before publishing.

    Request checks
    --------------
    1. INPUT_CONSISTENT  — required fields present and coherent
    2. POLICY_APPROVED   — policy_approved flag must be True
    3. DATA_INTEGRITY    — at least some data is present

    Output checks
    -------------
    4. ANALYTICS_COMPLETE — report has status COMPLETED
    5. SCORE_CONSISTENT  — scores are in valid 0–100 range
    """

    def validate_request(
        self, request: MarketAnalyticsRequest
    ) -> AnalyticsValidationResult:
        checks = [
            self._check_input_consistent(request),
            self._check_policy_approved(request),
            self._check_data_integrity(request),
        ]
        failed = tuple(c for c in checks if not c.passed)
        passed = tuple(c for c in checks if c.passed)
        return AnalyticsValidationResult(
            is_valid      = len(failed) == 0,
            failed_checks = failed,
            passed_checks = passed,
            analytics_id  = request.analytics_id,
        )

    def validate_request_or_raise(self, request: MarketAnalyticsRequest) -> None:
        from .exceptions import MarketAnalyticsValidationError
        result = self.validate_request(request)
        if not result.is_valid:
            raise MarketAnalyticsValidationError(
                "; ".join(result.failure_messages),
                analytics_id=request.analytics_id,
            )

    def validate_report(
        self, report: MarketAnalyticsReport
    ) -> AnalyticsValidationResult:
        checks = [
            self._check_report_complete(report),
            self._check_scores_consistent(report),
        ]
        failed = tuple(c for c in checks if not c.passed)
        passed = tuple(c for c in checks if c.passed)
        return AnalyticsValidationResult(
            is_valid      = len(failed) == 0,
            failed_checks = failed,
            passed_checks = passed,
            analytics_id  = report.analytics_id,
        )

    # ------------------------------------------------------------------
    # Request checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_input_consistent(
        r: MarketAnalyticsRequest,
    ) -> AnalyticsValidationCheckResult:
        ok = (
            bool(r.request_id)
            and bool(r.analytics_id)
            and bool(r.market_analysis_id)
            and bool(r.exchange)
        )
        return AnalyticsValidationCheckResult(
            code    = ValidationCode.INPUT_CONSISTENT,
            passed  = ok,
            message = "" if ok else
                "request_id, analytics_id, market_analysis_id, exchange are required",
        )

    @staticmethod
    def _check_policy_approved(
        r: MarketAnalyticsRequest,
    ) -> AnalyticsValidationCheckResult:
        ok = r.policy_approved is True
        return AnalyticsValidationCheckResult(
            code    = ValidationCode.POLICY_APPROVED,
            passed  = ok,
            message = "" if ok else "Request must be policy-approved before analytics",
        )

    @staticmethod
    def _check_data_integrity(
        r: MarketAnalyticsRequest,
    ) -> AnalyticsValidationCheckResult:
        # At least one data source must be present
        has_data = any([
            bool(r.index_prices),
            bool(r.sector_data),
            bool(r.breadth_data),
            bool(r.historical_data),
            bool(r.volatility_data),
        ])
        return AnalyticsValidationCheckResult(
            code    = ValidationCode.DATA_INTEGRITY,
            passed  = has_data,
            message = "" if has_data else
                "At least one data source is required (index_prices, sector_data, etc.)",
        )

    # ------------------------------------------------------------------
    # Report checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_report_complete(
        report: MarketAnalyticsReport,
    ) -> AnalyticsValidationCheckResult:
        from .constants import AnalyticsStatus
        ok = report.status == AnalyticsStatus.COMPLETED and report.is_success
        return AnalyticsValidationCheckResult(
            code    = ValidationCode.ANALYTICS_COMPLETE,
            passed  = ok,
            message = "" if ok else f"Report not complete: status={report.status.value}",
        )

    @staticmethod
    def _check_scores_consistent(
        report: MarketAnalyticsReport,
    ) -> AnalyticsValidationCheckResult:
        if report.scores is None:
            return AnalyticsValidationCheckResult(
                code=ValidationCode.SCORE_CONSISTENT, passed=True
            )
        s = report.scores
        vals = [
            s.health_score, s.sector_strength_score, s.trend_strength_score,
            s.breadth_score, s.liquidity_score, s.volatility_score,
            s.momentum_score, s.overall_score,
        ]
        ok = all(0.0 <= v <= 100.0 for v in vals)
        return AnalyticsValidationCheckResult(
            code    = ValidationCode.SCORE_CONSISTENT,
            passed  = ok,
            message = "" if ok else "All scores must be in [0, 100]",
        )

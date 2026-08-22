"""
risk_assessment_registry.py — iios.risk.assessment
====================================================
Thread-safe in-process registry for completed assessment reports.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_MAX_ASSESSMENTS
from .exceptions import (
    RiskAssessmentCapacityError,
    RiskAssessmentNotFoundError,
    RiskAssessmentRegistryError,
)


class RiskAssessmentRegistry:
    """
    Thread-safe container for completed risk assessment reports.

    Parameters
    ----------
    max_assessments :
        Maximum number of reports to retain simultaneously.
        Defaults to :data:`~.constants.DEFAULT_MAX_ASSESSMENTS`.
    """

    def __init__(self, max_assessments: int = DEFAULT_MAX_ASSESSMENTS) -> None:
        self._max  = max_assessments
        self._lock = threading.RLock()
        self._reports: Dict[str, Any] = {}   # assessment_id → RiskAssessmentReport

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, report: Any) -> None:
        """
        Register a completed assessment report.

        Raises
        ------
        RiskAssessmentRegistryError
            When ``report`` is ``None``.
        RiskAssessmentCapacityError
            When capacity is exhausted.
        """
        if report is None:
            raise RiskAssessmentRegistryError("Cannot register None report")
        with self._lock:
            aid = getattr(report, "assessment_id", None)
            if aid is None:
                raise RiskAssessmentRegistryError("Report has no assessment_id")
            is_update = aid in self._reports
            if not is_update and len(self._reports) >= self._max:
                raise RiskAssessmentCapacityError(self._max)
            self._reports[aid] = report

    def unregister(self, assessment_id: str) -> None:
        """
        Remove an assessment from the registry.

        Raises
        ------
        RiskAssessmentNotFoundError
        """
        with self._lock:
            if assessment_id not in self._reports:
                raise RiskAssessmentNotFoundError(assessment_id)
            del self._reports[assessment_id]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, assessment_id: str) -> Any:
        """
        Return the assessment report.

        Raises
        ------
        RiskAssessmentNotFoundError
        """
        with self._lock:
            report = self._reports.get(assessment_id)
        if report is None:
            raise RiskAssessmentNotFoundError(assessment_id)
        return report

    def get_optional(self, assessment_id: str) -> Optional[Any]:
        """Return the report or ``None``."""
        with self._lock:
            return self._reports.get(assessment_id)

    def list_all(self) -> List[Any]:
        """Return a snapshot list of all registered reports."""
        with self._lock:
            return list(self._reports.values())

    def list_ids(self) -> List[str]:
        """Return all registered assessment IDs."""
        with self._lock:
            return list(self._reports.keys())

    def contains(self, assessment_id: str) -> bool:
        with self._lock:
            return assessment_id in self._reports

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._reports)

    def capacity(self) -> int:
        return self._max

    def is_at_capacity(self) -> bool:
        with self._lock:
            return len(self._reports) >= self._max

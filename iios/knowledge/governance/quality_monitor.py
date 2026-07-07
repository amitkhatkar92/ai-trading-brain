"""
iios/knowledge/governance/quality_monitor.py
=============================================
QualityMonitor — continuous monitoring service that scans batches of
KnowledgeRecord objects and surfaces quality violations (freshness,
duplicates, missing metadata, quality degradation).

The monitor is deliberately stateless with respect to records so it can
be called from any scheduler or background worker.  Only the optional
``_kqi_history`` store is stateful (used for degradation detection).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from ..models.knowledge_record import KnowledgeRecord
from .quality_constants import (
    MONITOR_STALENESS_DAYS,
    QualityDimension,
    ViolationSeverity,
    ViolationType,
)
from .models.quality_violation import QualityViolation

__all__ = ["QualityMonitor", "MonitorReport", "get_quality_monitor",
           "reset_quality_monitor"]

_LOG = logging.getLogger("iios.knowledge.governance.monitor")
_lock = threading.Lock()
_monitor_instance: Optional["QualityMonitor"] = None


def _viol(
    knowledge_id: str,
    vtype: ViolationType,
    severity: ViolationSeverity,
    dimension: QualityDimension,
    field: str,
    message: str,
) -> QualityViolation:
    return QualityViolation(
        knowledge_id   = knowledge_id,
        violation_type = vtype,
        severity       = severity,
        dimension      = dimension,
        field_name     = field,
        message        = message,
    )


class MonitorReport:
    """Summary of a monitor scan pass."""

    def __init__(
        self,
        scanned:    int,
        violations: list[QualityViolation],
        scanned_at: float,
    ) -> None:
        self.scanned    = scanned
        self.violations = violations
        self.scanned_at = scanned_at

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.CRITICAL)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned":         self.scanned,
            "violation_count": self.violation_count,
            "critical_count":  self.critical_count,
            "scanned_at":      self.scanned_at,
        }


class QualityMonitor:
    """Continuous quality monitor for batches of knowledge records."""

    def __init__(self, staleness_days: int = MONITOR_STALENESS_DAYS) -> None:
        self._lock           = threading.RLock()
        self._staleness_secs = staleness_days * 86_400.0
        # knowledge_id → last known KQI  (for degradation detection)
        self._kqi_history: dict[str, float] = {}
        self._last_scan_at: Optional[float] = None

    # ── Primary scan ──────────────────────────────────────────────────────────

    def scan(
        self,
        records: list[KnowledgeRecord],
        kqi_scores: Optional[dict[str, float]] = None,
    ) -> MonitorReport:
        """Scan *records* and return a MonitorReport with all violations found.

        *kqi_scores* — optional dict of knowledge_id → current KQI; when
        supplied, degradation detection is enabled.
        """
        violations: list[QualityViolation] = []
        for record in records:
            violations.extend(self._check_freshness(record))
            violations.extend(self._check_staleness(record))
            violations.extend(self._check_missing_metadata(record))
            if kqi_scores:
                v = self._check_degradation(record, kqi_scores.get(record.id))
                if v:
                    violations.append(v)

        if kqi_scores:
            # Update history
            with self._lock:
                for kid, kqi in kqi_scores.items():
                    self._kqi_history[kid] = kqi

        self._last_scan_at = time.time()
        return MonitorReport(
            scanned    = len(records),
            violations = violations,
            scanned_at = self._last_scan_at,
        )

    def check_duplicates(self, records: list[KnowledgeRecord]) -> list[QualityViolation]:
        """Detect records with identical titles (case-insensitive)."""
        seen: dict[str, str] = {}  # normalised_title → first knowledge_id
        violations: list[QualityViolation] = []
        for record in records:
            key = record.title.strip().lower()
            if not key:
                continue
            if key in seen:
                violations.append(_viol(
                    record.id, ViolationType.DUPLICATE_DETECTED, ViolationSeverity.MEDIUM,
                    QualityDimension.INTEGRITY, "title",
                    f"duplicate title matches record '{seen[key]}'",
                ))
            else:
                seen[key] = record.id
        return violations

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_freshness(self, record: KnowledgeRecord) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if record.metadata.is_expired:
            out.append(_viol(
                record.id, ViolationType.EXPIRED_RECORD, ViolationSeverity.HIGH,
                QualityDimension.FRESHNESS, "metadata.expires_at",
                "record has passed its expiry time",
            ))
        return out

    def _check_staleness(self, record: KnowledgeRecord) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if record.metadata.age_seconds > self._staleness_secs:
            days = record.metadata.age_seconds / 86_400.0
            out.append(_viol(
                record.id, ViolationType.STALE_KNOWLEDGE, ViolationSeverity.LOW,
                QualityDimension.FRESHNESS, "created_at",
                f"record is {days:.0f} days old and has not been updated",
            ))
        return out

    def _check_missing_metadata(self, record: KnowledgeRecord) -> list[QualityViolation]:
        out: list[QualityViolation] = []
        if not record.metadata.tags:
            out.append(_viol(
                record.id, ViolationType.MISSING_TAGS, ViolationSeverity.LOW,
                QualityDimension.COVERAGE, "metadata.tags",
                "no tags assigned — discovery and categorisation is impaired",
            ))
        if not record.metadata.description:
            out.append(_viol(
                record.id, ViolationType.MISSING_FIELD, ViolationSeverity.LOW,
                QualityDimension.COMPLETENESS, "metadata.description",
                "description is empty",
            ))
        return out

    def _check_degradation(
        self,
        record: KnowledgeRecord,
        current_kqi: Optional[float],
    ) -> Optional[QualityViolation]:
        if current_kqi is None:
            return None
        with self._lock:
            prev = self._kqi_history.get(record.id)
        if prev is None or current_kqi >= prev:
            return None
        drop = prev - current_kqi
        if drop >= 0.10:
            return _viol(
                record.id, ViolationType.QUALITY_DEGRADED, ViolationSeverity.MEDIUM,
                QualityDimension.GOVERNANCE, "kqi",
                f"KQI dropped by {drop:.2f} (was {prev:.2f}, now {current_kqi:.2f})",
            )
        return None

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "tracked_items":   len(self._kqi_history),
                "last_scan_at":    self._last_scan_at,
                "staleness_days":  self._staleness_secs / 86_400.0,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_quality_monitor() -> QualityMonitor:
    global _monitor_instance
    if _monitor_instance is None:
        with _lock:
            if _monitor_instance is None:
                _monitor_instance = QualityMonitor()
    return _monitor_instance


def reset_quality_monitor() -> None:
    global _monitor_instance
    with _lock:
        _monitor_instance = None

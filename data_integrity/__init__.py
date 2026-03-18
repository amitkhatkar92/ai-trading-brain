"""
Data Integrity Engine
=====================
Validates and sanity-checks all market data before it enters the AI pipeline.

Public API::
    from data_integrity import DataIntegrityEngine

    engine = DataIntegrityEngine()
    result = engine.run(raw_data_dict)
    if not result.passed:
        # skip cycle
"""

from __future__ import annotations
from dataclasses import dataclass, field

from utils import get_logger
from .data_validator  import DataValidator,  ValidationReport
from .anomaly_detector import AnomalyDetector, AnomalyReport

log = get_logger(__name__)


@dataclass
class IntegrityResult:
    """Combined output from validation + anomaly detection."""
    validation:   ValidationReport
    anomaly:      AnomalyReport
    passed:       bool
    clean_data:   dict = field(default_factory=dict)

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        anom   = len(self.anomaly.anomalies)
        err    = len(self.validation.errors)
        warn   = len(self.validation.warnings)
        return (f"[DataIntegrityEngine] {status} | "
                f"Errors={err} | Warnings={warn} | Anomalies={anom}")


class DataIntegrityEngine:
    """
    Top-level coordinator for the Data Integrity layer.

    Runs DataValidator then AnomalyDetector.
    If validation fails → passed=False (blocks the cycle).
    If HIGH anomaly detected → passed=False.
    Warnings and LOW anomalies are non-blocking.
    """

    def __init__(self) -> None:
        self.validator = DataValidator()
        self.detector  = AnomalyDetector()
        log.info("[DataIntegrityEngine] Initialised. "
                 "Validator + AnomalyDetector active.")

    def run(self, raw: dict) -> IntegrityResult:
        val_report  = self.validator.validate(raw)
        anom_report = self.detector.detect(raw)

        # Block on hard validation errors OR high-severity anomaly
        passed = val_report.passed and not anom_report.is_anomalous

        result = IntegrityResult(
            validation=val_report,
            anomaly=anom_report,
            passed=passed,
            clean_data=val_report.clean_data,
        )
        log.info(result.summary())
        return result


__all__ = ["DataIntegrityEngine", "IntegrityResult",
           "DataValidator", "ValidationReport",
           "AnomalyDetector", "AnomalyReport"]

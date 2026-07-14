"""iios/investment/decision/confidence/calibration_statistics.py
CalibrationStatisticsTracker — thread-safe accumulator for calibration telemetry.
"""
from __future__ import annotations

import statistics
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.investment.decision.confidence.confidence_constants import CalibrationStatus


@dataclass(frozen=True)
class CalibrationStats:
    total_calibrations:  int
    well_calibrated:     int
    partially_calibrated: int
    poorly_calibrated:   int
    uncalibrated:        int
    insufficient_data:   int
    avg_adjustment:      float   # mean |calibrated - raw|
    avg_raw_confidence:  float
    avg_calibrated_conf: float
    computed_at:         datetime

    @property
    def reliability_rate(self) -> float:
        reliable = self.well_calibrated + self.partially_calibrated
        return reliable / max(1, self.total_calibrations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_calibrations":   self.total_calibrations,
            "well_calibrated":      self.well_calibrated,
            "partially_calibrated": self.partially_calibrated,
            "poorly_calibrated":    self.poorly_calibrated,
            "uncalibrated":         self.uncalibrated,
            "insufficient_data":    self.insufficient_data,
            "avg_adjustment":       round(self.avg_adjustment, 4),
            "avg_raw_confidence":   round(self.avg_raw_confidence, 2),
            "avg_calibrated_conf":  round(self.avg_calibrated_conf, 2),
            "reliability_rate":     round(self.reliability_rate, 4),
            "computed_at":          self.computed_at.isoformat(),
        }


class CalibrationStatisticsTracker:
    """Thread-safe accumulator for calibration runs."""

    def __init__(self) -> None:
        self._lock   = threading.RLock()
        self._total  = 0
        self._counts: Dict[str, int] = {s.value: 0 for s in CalibrationStatus}
        self._raws:   List[float] = []
        self._cals:   List[float] = []
        self._adjs:   List[float] = []

    def record(
        self,
        raw_confidence:     float,
        calibrated_conf:    float,
        status:             CalibrationStatus,
    ) -> None:
        with self._lock:
            self._total += 1
            self._counts[status.value] = self._counts.get(status.value, 0) + 1
            self._raws.append(raw_confidence)
            self._cals.append(calibrated_conf)
            self._adjs.append(abs(calibrated_conf - raw_confidence))

    def summary(self) -> CalibrationStats:
        with self._lock:
            n = max(1, self._total)
            return CalibrationStats(
                total_calibrations=self._total,
                well_calibrated=self._counts.get("well_calibrated", 0),
                partially_calibrated=self._counts.get("partially_calibrated", 0),
                poorly_calibrated=self._counts.get("poorly_calibrated", 0),
                uncalibrated=self._counts.get("uncalibrated", 0),
                insufficient_data=self._counts.get("insufficient_data", 0),
                avg_adjustment=round(sum(self._adjs) / n, 4),
                avg_raw_confidence=round(sum(self._raws) / n, 4),
                avg_calibrated_conf=round(sum(self._cals) / n, 4),
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total = 0
            self._counts = {s.value: 0 for s in CalibrationStatus}
            self._raws  = []
            self._cals  = []
            self._adjs  = []

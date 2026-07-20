"""
iios/execution/analytics/predictive/predictive_statistics.py
============================================================
PredictiveIntelligenceStatistics — thread-safe operational counters
and timing statistics for the Predictive Intelligence Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PredictiveIntelligenceStatistics:
    """
    Thread-safe operational statistics for PredictiveIntelligenceEngine.
    """

    # Counters
    prediction_cycles:     int   = 0
    forecasts_generated:   int   = 0
    trend_analyses:        int   = 0
    anomaly_detections:    int   = 0
    risk_assessments:      int   = 0
    capacity_estimations:  int   = 0
    probability_reports:   int   = 0
    failed_cycles:         int   = 0

    # Timing
    total_processing_ms:   float = 0.0
    total_forecast_ms:     float = 0.0

    # Accuracy tracking (actual vs predicted — populated externally)
    accuracy_samples:      int   = 0
    total_accuracy:        float = 0.0

    _lock: threading.RLock = field(
        default_factory=threading.RLock, repr=False, compare=False
    )

    # ── Thread-safe update methods ────────────────────────────────────────────

    def record_cycle(
        self,
        forecast_count:    int,
        processing_ms:     float,
        forecast_ms:       float = 0.0,
        had_trends:        bool  = False,
        had_anomalies:     bool  = False,
        had_risk:          bool  = False,
        had_capacity:      bool  = False,
        had_probabilities: bool  = False,
    ) -> None:
        with self._lock:
            self.prediction_cycles    += 1
            self.forecasts_generated  += forecast_count
            self.total_processing_ms  += processing_ms
            self.total_forecast_ms    += forecast_ms
            if had_trends:
                self.trend_analyses        += 1
            if had_anomalies:
                self.anomaly_detections    += 1
            if had_risk:
                self.risk_assessments      += 1
            if had_capacity:
                self.capacity_estimations  += 1
            if had_probabilities:
                self.probability_reports   += 1

    def record_failure(self) -> None:
        with self._lock:
            self.failed_cycles += 1

    def record_accuracy(self, accuracy: float) -> None:
        """Record a forecast accuracy measurement."""
        with self._lock:
            self.accuracy_samples += 1
            self.total_accuracy   += accuracy

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def avg_processing_time_ms(self) -> float:
        with self._lock:
            n = self.prediction_cycles
            return self.total_processing_ms / n if n > 0 else 0.0

    @property
    def avg_forecast_time_ms(self) -> float:
        with self._lock:
            n = self.prediction_cycles
            return self.total_forecast_ms / n if n > 0 else 0.0

    @property
    def avg_forecasts_per_cycle(self) -> float:
        with self._lock:
            n = self.prediction_cycles
            return self.forecasts_generated / n if n > 0 else 0.0

    @property
    def avg_confidence(self) -> float:
        return 0.0  # populated externally via record_accuracy

    @property
    def avg_accuracy(self) -> float:
        with self._lock:
            n = self.accuracy_samples
            return self.total_accuracy / n if n > 0 else 0.0

    @property
    def success_rate(self) -> float:
        with self._lock:
            total = self.prediction_cycles + self.failed_cycles
            return self.prediction_cycles / total if total > 0 else 1.0

    def snapshot(self) -> Dict[str, float]:
        """Return a point-in-time snapshot as a plain dict."""
        with self._lock:
            return {
                "prediction_cycles":    float(self.prediction_cycles),
                "forecasts_generated":  float(self.forecasts_generated),
                "trend_analyses":       float(self.trend_analyses),
                "anomaly_detections":   float(self.anomaly_detections),
                "risk_assessments":     float(self.risk_assessments),
                "capacity_estimations": float(self.capacity_estimations),
                "probability_reports":  float(self.probability_reports),
                "failed_cycles":        float(self.failed_cycles),
                "avg_processing_ms":    self.avg_processing_time_ms,
                "success_rate":         self.success_rate,
            }

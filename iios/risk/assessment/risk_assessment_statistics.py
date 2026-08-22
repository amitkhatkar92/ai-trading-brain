"""
risk_assessment_statistics.py — iios.risk.assessment
======================================================
Thread-safe running statistics for the Risk Assessment Framework.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class RiskAssessmentStatistics:
    """
    Thread-safe running statistics for the Risk Assessment Framework.

    Tracks the 8 statistics required by the specification:
      Assessments Performed, Optimization Runs, Stress Tests Executed,
      Scenario Analyses Executed, Average Assessment Time,
      Average Model Runtime, Forecast Accuracy, Optimization Success Rate.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reset()

    # ------------------------------------------------------------------
    # Internal reset (not exposed as public API)
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._assessments_total:    int   = 0
        self._assessments_completed: int  = 0
        self._assessments_failed:   int   = 0
        self._optimization_runs:    int   = 0
        self._optimization_success: int   = 0
        self._stress_tests:         int   = 0
        self._scenario_analyses:    int   = 0
        self._forecasts_generated:  int   = 0
        self._total_assessment_s:   float = 0.0
        self._total_model_s:        float = 0.0
        self._timed_assessments:    int   = 0
        self._timed_models:         int   = 0
        self._reset_at:             float = time.time()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_assessment_started(self) -> None:
        with self._lock:
            self._assessments_total += 1

    def record_assessment_completed(self) -> None:
        with self._lock:
            self._assessments_completed += 1

    def record_assessment_failed(self) -> None:
        with self._lock:
            self._assessments_failed += 1

    def record_assessment_time(self, elapsed_s: float) -> None:
        with self._lock:
            self._total_assessment_s += elapsed_s
            self._timed_assessments  += 1

    def record_model_runtime(self, elapsed_s: float) -> None:
        with self._lock:
            self._total_model_s += elapsed_s
            self._timed_models  += 1

    def record_optimization_run(self, *, success: bool = True) -> None:
        with self._lock:
            self._optimization_runs += 1
            if success:
                self._optimization_success += 1

    def record_stress_test(self) -> None:
        with self._lock:
            self._stress_tests += 1

    def record_scenario_analysis(self) -> None:
        with self._lock:
            self._scenario_analyses += 1

    def record_forecast(self) -> None:
        with self._lock:
            self._forecasts_generated += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return an atomic snapshot of all statistics."""
        with self._lock:
            avg_assessment_s = (
                self._total_assessment_s / self._timed_assessments
                if self._timed_assessments > 0 else 0.0
            )
            avg_model_s = (
                self._total_model_s / self._timed_models
                if self._timed_models > 0 else 0.0
            )
            opt_success_rate = (
                self._optimization_success / self._optimization_runs
                if self._optimization_runs > 0 else 0.0
            )
            elapsed = time.time() - self._reset_at
            throughput = (
                self._assessments_total / elapsed if elapsed > 0 else 0.0
            )
            return {
                "assessments_performed":    self._assessments_total,
                "assessments_completed":    self._assessments_completed,
                "assessments_failed":       self._assessments_failed,
                "optimization_runs":        self._optimization_runs,
                "optimization_success_rate": opt_success_rate,
                "stress_tests_executed":    self._stress_tests,
                "scenario_analyses_executed": self._scenario_analyses,
                "forecasts_generated":      self._forecasts_generated,
                "average_assessment_time_s": avg_assessment_s,
                "average_model_runtime_s":  avg_model_s,
                "throughput_per_s":         throughput,
            }

    def reset(self) -> None:
        """Reset all counters (thread-safe)."""
        with self._lock:
            self._reset()

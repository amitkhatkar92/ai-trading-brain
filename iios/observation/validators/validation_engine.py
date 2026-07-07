"""
iios/observation/validators/validation_engine.py
=================================================
ValidationEngine — coordinates the full validation lifecycle for
observations entering the IIOS pipeline.

Responsibilities
----------------
- Execute the validation pipeline (pre → norm → enrich → business → post)
- Compute a validation score
- Maintain a rolling history of ValidationReports
- Write validation outcome back to the Observation
- Expose batch and async interfaces
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation    import Observation
from ..observation_constants import ObservationStatus, ValidationOutcome
from .validation_constants   import (
    MAX_VALIDATION_HISTORY,
    ValidationMode,
    ValidationStage,
    SYSTEM_VALIDATOR,
)
from .validation_context     import validation_operation
from .validation_pipeline    import PipelineResult, ValidationPipeline
from .validation_registry    import RuleRegistry, get_rule_registry
from .validation_exceptions  import ValidationPipelineError

__all__ = [
    "ValidationReport",
    "ValidationEngine",
    "get_validation_engine",
    "reset_validation_engine",
]

_LOG  = logging.getLogger("iios.observation.validation.engine")
_lock = threading.Lock()
_engine: Optional["ValidationEngine"] = None


# ── Report ────────────────────────────────────────────────────────────────────

@dataclass
class ValidationReport:
    """Complete validation record for one observation."""
    obs_id:        str
    pipeline:      PipelineResult
    score:         float
    passed:        bool
    mode:          ValidationMode
    validator:     str               = SYSTEM_VALIDATOR
    completed_at:  float             = field(default_factory=time.time)
    duration_ms:   float             = 0.0

    @property
    def outcome(self) -> ValidationOutcome:
        return self.pipeline.outcome

    @property
    def violations(self) -> list[str]:
        return self.pipeline.violations

    @property
    def warnings(self) -> list[str]:
        return self.pipeline.warnings

    @property
    def total_violations(self) -> int:
        return self.pipeline.total_violations

    @property
    def total_warnings(self) -> int:
        return self.pipeline.total_warnings

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":       self.obs_id,
            "score":        round(self.score, 4),
            "passed":       self.passed,
            "mode":         self.mode.value,
            "outcome":      self.outcome.value,
            "violations":   self.violations,
            "warnings":     self.warnings,
            "validator":    self.validator,
            "completed_at": self.completed_at,
            "duration_ms":  round(self.duration_ms, 3),
            "pipeline":     self.pipeline.to_dict(),
        }


# ── Engine ────────────────────────────────────────────────────────────────────

class ValidationEngine:
    """Validates observations using a rule-based pipeline.

    Parameters
    ----------
    registry:
        :class:`RuleRegistry` to source rules from.  Defaults to the
        global singleton.
    mode:
        Default :class:`ValidationMode`.  Can be overridden per-call.
    max_history:
        Maximum number of :class:`ValidationReport` objects to keep in
        memory.
    max_workers:
        Thread-pool size for :meth:`validate_batch`.
    """

    def __init__(
        self,
        registry:    Optional[RuleRegistry] = None,
        mode:        ValidationMode          = ValidationMode.STRICT,
        max_history: int                     = MAX_VALIDATION_HISTORY,
        max_workers: int                     = 8,
    ) -> None:
        self._registry    = registry or get_rule_registry()
        self._default_mode = mode
        self._max_history  = max_history
        self._max_workers  = max_workers
        self._history:  list[ValidationReport] = []
        self._lock      = threading.RLock()
        self._pipeline: Optional[ValidationPipeline] = None

    # ── Pipeline builder ──────────────────────────────────────────────────────

    def _get_pipeline(self) -> ValidationPipeline:
        """Build (or return cached) pipeline from the current rule set."""
        with self._lock:
            if self._pipeline is None:
                rules = self._registry.enabled()
                self._pipeline = ValidationPipeline(rules)
            return self._pipeline

    def invalidate_pipeline(self) -> None:
        """Force pipeline rebuild on next use (call after registry changes)."""
        with self._lock:
            self._pipeline = None

    # ── Validate ─────────────────────────────────────────────────────────────

    def validate(
        self,
        obs:  Observation,
        mode: Optional[ValidationMode] = None,
    ) -> ValidationReport:
        """Run all enabled rules against *obs* and return a :class:`ValidationReport`."""
        eff_mode = mode or self._default_mode
        t0       = time.perf_counter()

        with validation_operation(obs.id, stage=ValidationStage.PRE):
            try:
                pipeline = self._get_pipeline()
                result   = pipeline.run(obs, eff_mode)
            except Exception as exc:
                raise ValidationPipelineError(
                    f"Pipeline failed for observation {obs.uid[:8]}: {exc}",
                    stage="unknown",
                ) from exc

        duration_ms = (time.perf_counter() - t0) * 1_000.0
        report = ValidationReport(
            obs_id      = obs.id,
            pipeline    = result,
            score       = result.score,
            passed      = result.passed,
            mode        = eff_mode,
            duration_ms = duration_ms,
        )

        # Write back to the observation
        obs.validation_passed = report.passed
        obs.validation_notes  = list(result.violations + result.warnings)

        self._record(report)
        self._log_report(report)
        return report

    def validate_batch(
        self,
        observations: list[Observation],
        mode:         Optional[ValidationMode] = None,
    ) -> dict[str, ValidationReport]:
        """Validate a list of observations in parallel.

        Returns a mapping of ``obs.id → ValidationReport``.
        """
        if not observations:
            return {}

        eff_mode = mode or self._default_mode
        results: dict[str, ValidationReport] = {}
        errors:  list[tuple[str, Exception]] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(self.validate, obs, eff_mode): obs.id
                for obs in observations
            }
            for future in as_completed(futures):
                obs_id = futures[future]
                try:
                    results[obs_id] = future.result()
                except Exception as exc:
                    _LOG.error("Batch validation failed for %s: %s", obs_id[:8], exc)
                    errors.append((obs_id, exc))

        if errors:
            _LOG.warning(
                "validate_batch: %d/%d observations failed: %s",
                len(errors), len(observations),
                [e[0][:8] for e in errors],
            )
        return results

    # ── History ───────────────────────────────────────────────────────────────

    def _record(self, report: ValidationReport) -> None:
        with self._lock:
            self._history.append(report)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

    def history(self, limit: Optional[int] = None) -> list[ValidationReport]:
        with self._lock:
            h = list(self._history)
        return h[-limit:] if limit else h

    def last_report(self, obs_id: str) -> Optional[ValidationReport]:
        with self._lock:
            for r in reversed(self._history):
                if r.obs_id == obs_id:
                    return r
        return None

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total  = len(self._history)
            passed = sum(1 for r in self._history if r.passed)
            failed = total - passed
            avg_s  = (
                sum(r.score for r in self._history) / total if total else 0.0
            )
        return {
            "total":          total,
            "passed":         passed,
            "failed":         failed,
            "pass_rate":      round(passed / total, 4) if total else 0.0,
            "avg_score":      round(avg_s, 4),
            "history_cap":    self._max_history,
            "mode":           self._default_mode.value,
            "total_rules":    self._registry.count(),
        }

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log_report(self, report: ValidationReport) -> None:
        level = logging.DEBUG if report.passed else logging.WARNING
        _LOG.log(
            level,
            "Validation %s for %s | score=%.3f | %d violations | %d warnings | %.1fms",
            "PASSED" if report.passed else "FAILED",
            report.obs_id[:8] + "…",
            report.score,
            report.total_violations,
            report.total_warnings,
            report.duration_ms,
        )


# ── Singletons ────────────────────────────────────────────────────────────────

def get_validation_engine() -> ValidationEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = ValidationEngine()
    return _engine


def reset_validation_engine() -> None:
    global _engine
    with _lock:
        _engine = None

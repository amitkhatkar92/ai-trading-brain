"""
iios/observation/validators/validation_pipeline.py
===================================================
ValidationPipeline — executes validation rules stage by stage.

Stage order: PRE → NORMALISATION → ENRICHMENT → BUSINESS → POST

Within each stage, rules are executed sequentially (safe for all modes).
The pipeline can short-circuit in STRICT mode if a CRITICAL violation
is found in the PRE stage.

``PipelineResult`` carries the per-stage and per-rule outcomes plus
an overall score and outcome decision.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation import Observation
from ..observation_constants import ValidationOutcome
from .validation_constants import (
    MIN_PASSING_SCORE,
    ValidationMode,
    ValidationSeverity,
    ValidationStage,
)
from .validation_rules import RuleResult, ValidationRule

__all__ = [
    "StageResult",
    "PipelineResult",
    "ValidationPipeline",
]

_LOG = logging.getLogger("iios.observation.validation.pipeline")


# ── Result models ─────────────────────────────────────────────────────────────

@dataclass
class StageResult:
    """Aggregated result for one pipeline stage."""
    stage:         ValidationStage
    rule_results:  list[RuleResult]          = field(default_factory=list)
    passed:        bool                      = True
    violations:    list[str]                 = field(default_factory=list)
    warnings:      list[str]                 = field(default_factory=list)
    duration_ms:   float                     = 0.0

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage":      self.stage.value,
            "passed":     self.passed,
            "violations": self.violations,
            "warnings":   self.warnings,
            "duration_ms": round(self.duration_ms, 3),
            "rules":      [r.to_dict() for r in self.rule_results],
        }


@dataclass
class PipelineResult:
    """Full result from running the validation pipeline."""
    obs_id:        str
    mode:          ValidationMode
    stage_results: list[StageResult]         = field(default_factory=list)
    score:         float                     = 0.0
    outcome:       ValidationOutcome         = ValidationOutcome.PASS
    violations:    list[str]                 = field(default_factory=list)
    warnings:      list[str]                 = field(default_factory=list)
    aborted_at:    Optional[ValidationStage] = None
    started_at:    float                     = field(default_factory=time.time)
    duration_ms:   float                     = 0.0

    @property
    def passed(self) -> bool:
        return self.outcome == ValidationOutcome.PASS

    @property
    def failed(self) -> bool:
        return self.outcome == ValidationOutcome.FAIL

    @property
    def total_rules_run(self) -> int:
        return sum(len(s.rule_results) for s in self.stage_results)

    @property
    def total_violations(self) -> int:
        return len(self.violations)

    @property
    def total_warnings(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":       self.obs_id,
            "mode":         self.mode.value,
            "outcome":      self.outcome.value,
            "score":        round(self.score, 4),
            "violations":   self.violations,
            "warnings":     self.warnings,
            "aborted_at":   self.aborted_at.value if self.aborted_at else None,
            "started_at":   self.started_at,
            "duration_ms":  round(self.duration_ms, 3),
            "total_rules":  self.total_rules_run,
            "stages":       [s.to_dict() for s in self.stage_results],
        }


# ── Pipeline ──────────────────────────────────────────────────────────────────

class ValidationPipeline:
    """Runs validation rules stage by stage against an observation.

    Parameters
    ----------
    rules:
        Flat list of rules to run.  The pipeline groups them by stage
        and sorts each group by ``severity`` (CRITICAL first).
    """

    _STAGE_ORDER = [
        ValidationStage.PRE,
        ValidationStage.NORMALISATION,
        ValidationStage.ENRICHMENT,
        ValidationStage.BUSINESS,
        ValidationStage.POST,
    ]

    def __init__(self, rules: list[ValidationRule]) -> None:
        self._by_stage: dict[ValidationStage, list[ValidationRule]] = {
            s: [] for s in self._STAGE_ORDER
        }
        _sev_order = {
            ValidationSeverity.CRITICAL: 0,
            ValidationSeverity.HIGH:     1,
            ValidationSeverity.MEDIUM:   2,
            ValidationSeverity.LOW:      3,
            ValidationSeverity.INFO:     4,
        }
        for rule in rules:
            if rule.enabled and rule.stage in self._by_stage:
                self._by_stage[rule.stage].append(rule)
        for stage in self._STAGE_ORDER:
            self._by_stage[stage].sort(key=lambda r: _sev_order[r.severity])

    def run(
        self,
        obs:  Observation,
        mode: ValidationMode = ValidationMode.STRICT,
    ) -> PipelineResult:
        t0     = time.perf_counter()
        result = PipelineResult(obs_id=obs.id, mode=mode, started_at=time.time())

        for stage in self._STAGE_ORDER:
            stage_res = self._run_stage(stage, obs, mode)
            result.stage_results.append(stage_res)
            result.violations.extend(stage_res.violations)
            result.warnings.extend(stage_res.warnings)

            # Short-circuit: STRICT + CRITICAL violation in PRE → abort
            if not stage_res.passed and stage == ValidationStage.PRE:
                if mode == ValidationMode.STRICT:
                    result.aborted_at = stage
                    _LOG.debug(
                        "Pipeline aborted at PRE for %s: %d violation(s)",
                        obs.uid[:8], len(stage_res.violations),
                    )
                    break

        result.score    = self._compute_score(result)
        result.outcome  = self._decide(result, mode)
        result.duration_ms = (time.perf_counter() - t0) * 1_000.0
        return result

    def _run_stage(
        self,
        stage: ValidationStage,
        obs:   Observation,
        mode:  ValidationMode,
    ) -> StageResult:
        t0         = time.perf_counter()
        stage_res  = StageResult(stage=stage)
        rules      = self._by_stage.get(stage, [])

        for rule in rules:
            try:
                rr = rule.evaluate(obs)
            except Exception as exc:
                _LOG.warning("Rule %r raised unexpectedly: %s", rule.name, exc)
                rr = RuleResult(
                    rule_name = rule.name,
                    category  = rule.category,
                    stage     = rule.stage,
                    severity  = rule.severity,
                    passed    = False,
                    message   = f"Rule error: {exc}",
                )

            stage_res.rule_results.append(rr)

            if rr.is_violation:
                msg = f"[{rule.severity.value.upper()}] {rule.name}: {rr.message}"
                if rule.severity in (ValidationSeverity.CRITICAL, ValidationSeverity.HIGH):
                    stage_res.violations.append(msg)
                    stage_res.passed = False
                elif rule.severity == ValidationSeverity.MEDIUM:
                    if mode == ValidationMode.STRICT:
                        stage_res.violations.append(msg)
                        stage_res.passed = False
                    else:
                        stage_res.warnings.append(msg)
                else:
                    stage_res.warnings.append(msg)

        stage_res.duration_ms = (time.perf_counter() - t0) * 1_000.0
        return stage_res

    def _compute_score(self, result: PipelineResult) -> float:
        """Score = fraction of rules that passed (weighted by rule count)."""
        total = result.total_rules_run
        if total == 0:
            return 1.0
        passed = sum(
            1 for sr in result.stage_results
            for rr in sr.rule_results
            if rr.passed
        )
        return round(passed / total, 4)

    def _decide(self, result: PipelineResult, mode: ValidationMode) -> ValidationOutcome:
        if mode == ValidationMode.ADVISORY:
            return ValidationOutcome.PASS
        if result.violations:
            return ValidationOutcome.FAIL
        if result.warnings and mode == ValidationMode.STRICT:
            return ValidationOutcome.WARNING
        return ValidationOutcome.PASS

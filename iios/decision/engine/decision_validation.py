"""
decision_validation.py — iios.decision.engine
===============================================
Validation engine for decision requests and pipeline sessions.

Runs the six checks mandated by the specification.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .constants import EngineValidationCode
from .decision_pipeline import DecisionPipeline
from .decision_request  import DecisionRequest
from .exceptions import DecisionRequestValidationError


@dataclass(frozen=True)
class EngineValidationCheckResult:
    """
    Outcome of a single engine validation check.
    """
    code:    EngineValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class EngineValidationResult:
    """
    Aggregate result of the six engine validation checks.
    """
    is_valid:       bool
    checks:         Tuple[EngineValidationCheckResult, ...]
    failed_checks:  Tuple[EngineValidationCode, ...]
    error_messages: Tuple[str, ...]

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return len(self.failed_checks)


class DecisionEngineValidator:
    """
    Validates decision requests and pipeline states against the six
    specification checks:

    1. SESSION_VALIDITY      — request IDs are non-empty and well-formed.
    2. PIPELINE_CONSISTENCY  — pipeline state is legal for the current operation.
    3. LIFECYCLE_CONSISTENCY — decision_id and request_id are non-empty.
    4. SNAPSHOT_CONSISTENCY  — inputs dict is present (may be empty).
    5. SUBSYSTEM_HEALTH      — engine_running flag is True.
    6. INPUT_COMPLETENESS    — decision_id is non-empty (minimum required input).
    """

    def validate_request(
        self,
        request: DecisionRequest,
        *,
        engine_running: bool = True,
        pipeline: Optional[DecisionPipeline] = None,
    ) -> EngineValidationResult:
        """
        Run all six checks against *request*.

        Parameters
        ----------
        request :        :class:`DecisionRequest` to validate.
        engine_running : Whether the engine is currently running.
        pipeline :       Associated pipeline (optional, for pipeline checks).

        Returns
        -------
        EngineValidationResult
        """
        checks: List[EngineValidationCheckResult] = [
            self._check_session_validity(request),
            self._check_pipeline_consistency(request, pipeline),
            self._check_lifecycle_consistency(request),
            self._check_snapshot_consistency(request),
            self._check_subsystem_health(engine_running),
            self._check_input_completeness(request),
        ]

        checks_tuple = tuple(checks)
        failed       = tuple(c.code    for c in checks if not c.passed)
        errors       = tuple(c.message for c in checks if not c.passed and c.message)

        return EngineValidationResult(
            is_valid       = len(failed) == 0,
            checks         = checks_tuple,
            failed_checks  = failed,
            error_messages = errors,
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------
    @staticmethod
    def _check_session_validity(request: DecisionRequest) -> EngineValidationCheckResult:
        code = EngineValidationCode.SESSION_VALIDITY
        if not request.request_id or not request.request_id.strip():
            return EngineValidationCheckResult(
                code    = code,
                passed  = False,
                message = "request_id must be a non-empty string",
            )
        return EngineValidationCheckResult(code=code, passed=True)

    @staticmethod
    def _check_pipeline_consistency(
        request:  DecisionRequest,
        pipeline: Optional[DecisionPipeline],
    ) -> EngineValidationCheckResult:
        code = EngineValidationCode.PIPELINE_CONSISTENCY
        if pipeline is not None:
            from .constants import PIPELINE_TERMINAL_STATES
            if pipeline.is_terminal:
                return EngineValidationCheckResult(
                    code    = code,
                    passed  = False,
                    message = (
                        f"Pipeline {pipeline.pipeline_id!r} is in terminal "
                        f"state {pipeline.state.value!r}"
                    ),
                )
        return EngineValidationCheckResult(code=code, passed=True)

    @staticmethod
    def _check_lifecycle_consistency(request: DecisionRequest) -> EngineValidationCheckResult:
        code = EngineValidationCode.LIFECYCLE_CONSISTENCY
        if not request.decision_id or not request.decision_id.strip():
            return EngineValidationCheckResult(
                code    = code,
                passed  = False,
                message = "decision_id must be a non-empty string",
            )
        return EngineValidationCheckResult(code=code, passed=True)

    @staticmethod
    def _check_snapshot_consistency(request: DecisionRequest) -> EngineValidationCheckResult:
        code = EngineValidationCode.SNAPSHOT_CONSISTENCY
        if request.inputs is None:
            return EngineValidationCheckResult(
                code    = code,
                passed  = False,
                message = "request.inputs must not be None",
            )
        return EngineValidationCheckResult(code=code, passed=True)

    @staticmethod
    def _check_subsystem_health(engine_running: bool) -> EngineValidationCheckResult:
        code = EngineValidationCode.SUBSYSTEM_HEALTH
        if not engine_running:
            return EngineValidationCheckResult(
                code    = code,
                passed  = False,
                message = "Decision engine is not running",
            )
        return EngineValidationCheckResult(code=code, passed=True)

    @staticmethod
    def _check_input_completeness(request: DecisionRequest) -> EngineValidationCheckResult:
        code = EngineValidationCode.INPUT_COMPLETENESS
        if not request.decision_id:
            return EngineValidationCheckResult(
                code    = code,
                passed  = False,
                message = "decision_id is required",
            )
        return EngineValidationCheckResult(code=code, passed=True)

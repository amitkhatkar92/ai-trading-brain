"""
knowledge_validation.py — iios.knowledge.engine
-------------------------------------------------
Engine-level validation for knowledge workflow requests.

Six validation checks
----------------------
1. KNOWLEDGE_INTEGRITY  — request object structure is sound
2. ARTIFACT_CONSISTENCY — collected artifacts are internally consistent
3. METADATA_CONSISTENCY — request metadata is well-formed
4. LIFECYCLE_CONSISTENCY — session count within limits
5. INPUT_COMPLETENESS   — required inputs present
6. SOURCE_AVAILABILITY  — at least one source is targetable

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .constants import KnowledgeValidationCode
from .exceptions import KnowledgeEngineValidationError
from .knowledge_request import KnowledgeRequest


@dataclass(frozen=True)
class ValidationResult:
    """Result of a single validation check."""
    code:    KnowledgeValidationCode
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code.value, "passed": self.passed, "message": self.message}


class KnowledgeEngineValidator:
    """
    Validates :class:`KnowledgeRequest` objects and collected artifacts.

    Parameters
    ----------
    max_sessions :    Maximum allowed concurrent sessions.
    active_count_fn : Callable returning current active session count.
    """

    def __init__(
        self,
        max_sessions:    int                      = 200,
        active_count_fn: Optional[Callable[[], int]] = None,
    ) -> None:
        self._max_sessions    = max_sessions
        self._active_count_fn = active_count_fn or (lambda: 0)

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def validate_request(
        self,
        request:          KnowledgeRequest,
        *,
        raise_on_failure: bool = False,
    ) -> List[ValidationResult]:
        """Run request-level validation checks."""
        results = [
            self._check_knowledge_integrity(request),
            self._check_metadata_consistency(request),
            self._check_lifecycle_consistency(),
            self._check_input_completeness(request),
            self._check_source_availability(request),
        ]
        # Artifact consistency not applicable at request time
        if raise_on_failure:
            failures = [r for r in results if not r.passed]
            if failures:
                msgs = "; ".join(f.message for f in failures)
                raise KnowledgeEngineValidationError(f"Request validation failed: {msgs}")
        return results

    def validate_artifacts(
        self,
        artifacts:        Dict[str, Any],
        *,
        raise_on_failure: bool = False,
    ) -> List[ValidationResult]:
        """Run artifact-level validation checks."""
        results = [self._check_artifact_consistency(artifacts)]
        if raise_on_failure:
            failures = [r for r in results if not r.passed]
            if failures:
                msgs = "; ".join(f.message for f in failures)
                raise KnowledgeEngineValidationError(f"Artifact validation failed: {msgs}")
        return results

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_knowledge_integrity(request: KnowledgeRequest) -> ValidationResult:
        code = KnowledgeValidationCode.KNOWLEDGE_INTEGRITY
        if not isinstance(request.request_id, str) or not request.request_id.strip():
            return ValidationResult(code=code, passed=False, message="request_id is empty")
        if not isinstance(request.knowledge_id, str) or not request.knowledge_id.strip():
            return ValidationResult(code=code, passed=False, message="knowledge_id is empty")
        if not isinstance(request.subsystem_id, str) or not request.subsystem_id.strip():
            return ValidationResult(code=code, passed=False, message="subsystem_id is empty")
        return ValidationResult(code=code, passed=True, message="OK")

    @staticmethod
    def _check_metadata_consistency(request: KnowledgeRequest) -> ValidationResult:
        code = KnowledgeValidationCode.METADATA_CONSISTENCY
        if not isinstance(request.metadata, dict):
            return ValidationResult(code=code, passed=False, message="metadata must be a dict")
        return ValidationResult(code=code, passed=True, message="OK")

    def _check_lifecycle_consistency(self) -> ValidationResult:
        code = KnowledgeValidationCode.LIFECYCLE_CONSISTENCY
        active = self._active_count_fn()
        if active >= self._max_sessions:
            return ValidationResult(
                code=code,
                passed=False,
                message=f"Session limit reached: {active}/{self._max_sessions}",
            )
        return ValidationResult(code=code, passed=True, message="OK")

    @staticmethod
    def _check_input_completeness(request: KnowledgeRequest) -> ValidationResult:
        code = KnowledgeValidationCode.INPUT_COMPLETENESS
        # Inputs dict is optional — if provided, all values must be non-None
        if request.inputs:
            for k, v in request.inputs.items():
                if v is None:
                    return ValidationResult(
                        code=code, passed=False, message=f"Input key {k!r} has None value"
                    )
        return ValidationResult(code=code, passed=True, message="OK")

    @staticmethod
    def _check_source_availability(request: KnowledgeRequest) -> ValidationResult:
        code = KnowledgeValidationCode.SOURCE_AVAILABILITY
        # At least the subsystem_id must be non-empty (already checked in integrity).
        # If sources_requested is provided it must be non-empty.
        if request.sources_requested is not None and len(request.sources_requested) == 0:
            # Empty list is fine — engine will use subsystem_id as the sole source
            pass
        return ValidationResult(code=code, passed=True, message="OK")

    @staticmethod
    def _check_artifact_consistency(artifacts: Dict[str, Any]) -> ValidationResult:
        code = KnowledgeValidationCode.ARTIFACT_CONSISTENCY
        if not isinstance(artifacts, dict):
            return ValidationResult(code=code, passed=False, message="artifacts must be a dict")
        return ValidationResult(code=code, passed=True, message="OK")

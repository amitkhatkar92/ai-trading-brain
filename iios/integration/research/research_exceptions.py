"""iios/integration/research/research_exceptions.py

Exception hierarchy for the Quantitative Research Framework.
Error-code prefix: QR
"""
from __future__ import annotations


class ResearchError(Exception):
    """Root exception for all research framework errors."""
    code: str = "QR-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self})"


# ── Engine  QR-001 – QR-009 ────────────────────────────────────────────────────

class ResearchEngineNotRunningError(ResearchError):
    code = "QR-001"

class ResearchEngineAlreadyRunningError(ResearchError):
    code = "QR-002"

class ResearchEngineInitializationError(ResearchError):
    code = "QR-003"


# ── Project  QR-010 – QR-019 ───────────────────────────────────────────────────

class ResearchProjectNotFoundError(ResearchError):
    code = "QR-010"

class ResearchProjectAlreadyExistsError(ResearchError):
    code = "QR-011"

class ResearchProjectValidationError(ResearchError):
    code = "QR-012"

class ResearchProjectCapacityError(ResearchError):
    code = "QR-013"

class ResearchProjectLockedError(ResearchError):
    code = "QR-014"


# ── Experiment  QR-020 – QR-029 ────────────────────────────────────────────────

class ResearchExperimentNotFoundError(ResearchError):
    code = "QR-020"

class ResearchExperimentAlreadyExistsError(ResearchError):
    code = "QR-021"

class ResearchExperimentValidationError(ResearchError):
    code = "QR-022"

class ExperimentStateError(ResearchError):
    code = "QR-023"

class ResearchExperimentCapacityError(ResearchError):
    code = "QR-024"

class ExperimentAlreadyRunningError(ResearchError):
    code = "QR-025"

class ExperimentNotRunningError(ResearchError):
    code = "QR-026"


# ── Dataset  QR-030 – QR-039 ───────────────────────────────────────────────────

class ResearchDatasetNotFoundError(ResearchError):
    code = "QR-030"

class ResearchDatasetAlreadyExistsError(ResearchError):
    code = "QR-031"

class ResearchDatasetValidationError(ResearchError):
    code = "QR-032"

class DatasetLineageError(ResearchError):
    code = "QR-033"

class ResearchDatasetCapacityError(ResearchError):
    code = "QR-034"


# ── Session  QR-040 – QR-049 ───────────────────────────────────────────────────

class ResearchSessionNotFoundError(ResearchError):
    code = "QR-040"

class ResearchSessionAlreadyActiveError(ResearchError):
    code = "QR-041"

class ResearchSessionNotActiveError(ResearchError):
    code = "QR-042"


# ── Workflow  QR-050 – QR-059 ──────────────────────────────────────────────────

class WorkflowError(ResearchError):
    code = "QR-050"

class WorkflowValidationError(ResearchError):
    code = "QR-051"

class WorkflowStateError(ResearchError):
    code = "QR-052"

class WorkflowStepNotFoundError(ResearchError):
    code = "QR-053"


# ── Registry  QR-060 – QR-069 ──────────────────────────────────────────────────

class ResearchRegistryError(ResearchError):
    code = "QR-060"

class ResearchRegistryFullError(ResearchError):
    code = "QR-061"


# ── Tracking  QR-070 – QR-079 ──────────────────────────────────────────────────

class TrackingError(ResearchError):
    code = "QR-070"

class CheckpointError(ResearchError):
    code = "QR-071"

class TrackingSessionNotFoundError(ResearchError):
    code = "QR-072"

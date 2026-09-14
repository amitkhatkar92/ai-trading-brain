"""governance_exceptions.py — Exception hierarchy for the Research Governance Framework."""
from __future__ import annotations


class GovernanceError(Exception):
    """Root exception for the Governance Framework. Code GV-000."""
    code = "GV-000"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self})"


# ── Engine lifecycle ──────────────────────────────────────────────────────────

class EngineNotRunningError(GovernanceError):
    """Engine must be started before use. Code GV-001."""
    code = "GV-001"


class EngineAlreadyRunningError(GovernanceError):
    """Engine is already running. Code GV-002."""
    code = "GV-002"


class EngineInitializationError(GovernanceError):
    """Engine failed to initialize. Code GV-003."""
    code = "GV-003"


# ── Research projects ─────────────────────────────────────────────────────────

class ResearchProjectNotFoundError(GovernanceError):
    """Research project not found. Code GV-010."""
    code = "GV-010"


class ResearchProjectAlreadyExistsError(GovernanceError):
    """Research project already exists. Code GV-011."""
    code = "GV-011"


class ResearchProjectCapacityError(GovernanceError):
    """Maximum research project capacity reached. Code GV-012."""
    code = "GV-012"


class ResearchProjectStateError(GovernanceError):
    """Invalid research project state transition. Code GV-013."""
    code = "GV-013"


# ── Lineage ───────────────────────────────────────────────────────────────────

class LineageError(GovernanceError):
    """Generic lineage error. Code GV-020."""
    code = "GV-020"


class LineageNodeNotFoundError(GovernanceError):
    """Lineage node not found. Code GV-021."""
    code = "GV-021"


class LineageCycleError(GovernanceError):
    """Circular dependency detected in lineage graph. Code GV-022."""
    code = "GV-022"


class LineageCapacityError(GovernanceError):
    """Maximum lineage node capacity reached. Code GV-023."""
    code = "GV-023"


# ── Provenance ────────────────────────────────────────────────────────────────

class ProvenanceError(GovernanceError):
    """Generic provenance error. Code GV-030."""
    code = "GV-030"


class ProvenanceNotFoundError(GovernanceError):
    """Provenance record not found. Code GV-031."""
    code = "GV-031"


# ── Reproducibility ───────────────────────────────────────────────────────────

class ReproducibilityError(GovernanceError):
    """Reproducibility error. Code GV-040."""
    code = "GV-040"


class EnvironmentSnapshotError(GovernanceError):
    """Failed to capture environment snapshot. Code GV-041."""
    code = "GV-041"


class ReproductionRunError(GovernanceError):
    """Failed to reproduce experiment. Code GV-042."""
    code = "GV-042"


# ── Approvals ─────────────────────────────────────────────────────────────────

class ApprovalError(GovernanceError):
    """Generic approval error. Code GV-050."""
    code = "GV-050"


class ApprovalNotFoundError(GovernanceError):
    """Approval record not found. Code GV-051."""
    code = "GV-051"


class ApprovalStateError(GovernanceError):
    """Invalid approval state transition. Code GV-052."""
    code = "GV-052"


class ApprovalTimeoutError(GovernanceError):
    """Approval request timed out. Code GV-053."""
    code = "GV-053"


class ApprovalPolicyViolationError(GovernanceError):
    """Approval policy was violated. Code GV-054."""
    code = "GV-054"


# ── Artifacts ─────────────────────────────────────────────────────────────────

class ArtifactError(GovernanceError):
    """Generic artifact error. Code GV-060."""
    code = "GV-060"


class ArtifactNotFoundError(GovernanceError):
    """Artifact not found. Code GV-061."""
    code = "GV-061"


class ArtifactVersionError(GovernanceError):
    """Artifact version error. Code GV-062."""
    code = "GV-062"


class ArtifactStorageError(GovernanceError):
    """Artifact storage error. Code GV-063."""
    code = "GV-063"


class ArtifactLockedError(GovernanceError):
    """Artifact is locked and cannot be modified. Code GV-064."""
    code = "GV-064"


# ── Compliance ────────────────────────────────────────────────────────────────

class ComplianceError(GovernanceError):
    """Generic compliance error. Code GV-070."""
    code = "GV-070"


class PolicyNotFoundError(GovernanceError):
    """Policy not found. Code GV-071."""
    code = "GV-071"


class PolicyViolationError(GovernanceError):
    """A governance policy was violated. Code GV-072."""
    code = "GV-072"


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditError(GovernanceError):
    """Generic audit error. Code GV-080."""
    code = "GV-080"

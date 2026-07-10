"""iios/integration/research/governance/__init__.py — Public API."""
from iios.integration.research.governance.governance_constants import (
    GovernanceEngineStatus,
    ResearchStatus,
    ApprovalStatus,
    ReviewStage,
    ReviewDecision,
    ArtifactType,
    ArtifactStatus,
    LineageNodeType,
    LineageEdgeType,
    ProvenanceType,
    ReproducibilityStatus,
    ComplianceStatus,
    AuditEventType,
    PolicyType,
    GOVERNANCE_ENGINE_VERSION,
)
from iios.integration.research.governance.governance_exceptions import (
    GovernanceError,
    EngineNotRunningError,
    EngineAlreadyRunningError,
    ResearchProjectNotFoundError,
    ResearchProjectAlreadyExistsError,
    LineageError,
    LineageCycleError,
    LineageNodeNotFoundError,
    ApprovalNotFoundError,
    ApprovalStateError,
    ArtifactNotFoundError,
    ArtifactLockedError,
    PolicyNotFoundError,
    PolicyViolationError,
)
from iios.integration.research.governance.governance_context import (
    set_context,
    get_context,
    clear_context,
    scope,
)
from iios.integration.research.governance.core.governance_configuration import GovernanceConfiguration
from iios.integration.research.governance.core.governance_event         import GovernanceEvent
from iios.integration.research.governance.core.governance_history       import GovernanceHistory
from iios.integration.research.governance.core.governance_report        import GovernanceReport
from iios.integration.research.governance.governance_registry           import ResearchProject, ProjectRegistry
from iios.integration.research.governance.lineage.lineage_graph         import LineageGraph, LineageNode, LineageEdge
from iios.integration.research.governance.provenance.provenance_record  import ProvenanceRecord
from iios.integration.research.governance.reproducibility.environment_snapshot import EnvironmentSnapshot
from iios.integration.research.governance.reproducibility.seed_manager         import SeedManager
from iios.integration.research.governance.approvals.approval_workflow   import ApprovalWorkflow
from iios.integration.research.governance.approvals.approval_result     import ApprovalResult
from iios.integration.research.governance.artifacts.artifact_metadata   import ArtifactMetadata
from iios.integration.research.governance.compliance.policy_validator   import GovernancePolicy, PolicyViolation
from iios.integration.research.governance.audit.audit_history           import AuditRecord
from iios.integration.research.governance.research_governance_engine    import (
    ResearchGovernanceEngine,
    get_governance_engine,
    reset_governance_engine,
)

__all__ = [
    # Constants / Enums
    "GovernanceEngineStatus",
    "ResearchStatus",
    "ApprovalStatus",
    "ReviewStage",
    "ReviewDecision",
    "ArtifactType",
    "ArtifactStatus",
    "LineageNodeType",
    "LineageEdgeType",
    "ProvenanceType",
    "ReproducibilityStatus",
    "ComplianceStatus",
    "AuditEventType",
    "PolicyType",
    "GOVERNANCE_ENGINE_VERSION",
    # Exceptions
    "GovernanceError",
    "EngineNotRunningError",
    "EngineAlreadyRunningError",
    "ResearchProjectNotFoundError",
    "ResearchProjectAlreadyExistsError",
    "LineageError",
    "LineageCycleError",
    "LineageNodeNotFoundError",
    "ApprovalNotFoundError",
    "ApprovalStateError",
    "ArtifactNotFoundError",
    "ArtifactLockedError",
    "PolicyNotFoundError",
    "PolicyViolationError",
    # Context
    "set_context",
    "get_context",
    "clear_context",
    "scope",
    # Core data classes
    "GovernanceConfiguration",
    "GovernanceEvent",
    "GovernanceHistory",
    "GovernanceReport",
    # Entities
    "ResearchProject",
    "ProjectRegistry",
    "LineageGraph",
    "LineageNode",
    "LineageEdge",
    "ProvenanceRecord",
    "EnvironmentSnapshot",
    "SeedManager",
    "ApprovalWorkflow",
    "ApprovalResult",
    "ArtifactMetadata",
    "GovernancePolicy",
    "PolicyViolation",
    "AuditRecord",
    # Engine
    "ResearchGovernanceEngine",
    "get_governance_engine",
    "reset_governance_engine",
]

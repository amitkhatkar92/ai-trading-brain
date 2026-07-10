"""governance_manager.py — High-level lifecycle coordinator."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    AuditEventType,
    ResearchStatus,
    ProvenanceType,
    ArtifactType,
    LineageEdgeType,
    LineageNodeType,
    ReviewStage,
    ReviewDecision,
    ReproducibilityStatus,
)
from iios.integration.research.governance.governance_registry import ResearchProject, ProjectRegistry
from iios.integration.research.governance.lineage.lineage_engine          import LineageEngine
from iios.integration.research.governance.provenance.provenance_engine    import ProvenanceEngine
from iios.integration.research.governance.reproducibility.reproducibility_engine import ReproducibilityEngine
from iios.integration.research.governance.approvals.approval_engine       import ApprovalEngine
from iios.integration.research.governance.artifacts.artifact_engine       import ArtifactEngine
from iios.integration.research.governance.compliance.compliance_engine    import ComplianceEngine
from iios.integration.research.governance.audit.audit_engine              import AuditEngine


class GovernanceManager:
    """
    Coordinates all governance sub-engines.

    Created once by ``ResearchGovernanceEngine`` and shared for the lifetime
    of the engine instance.
    """

    def __init__(self, cfg: Any) -> None:
        self._cfg          = cfg
        self._registry     = ProjectRegistry(cfg.max_research_projects)
        self._lineage      = LineageEngine()
        self._provenance   = ProvenanceEngine()
        self._reproducibility = ReproducibilityEngine(cfg.default_random_seed)
        self._approvals    = ApprovalEngine()
        self._artifacts    = ArtifactEngine()
        self._compliance   = ComplianceEngine()
        self._audit        = AuditEngine()

    # ── Project ───────────────────────────────────────────────────────────────

    def register_project(
        self,
        name:   str,
        author: str,
        **kwargs: Any,
    ) -> ResearchProject:
        proj = ResearchProject.create(name, author, **kwargs)
        self._registry.register(proj)
        self._audit.log_event(
            AuditEventType.PROJECT_CREATED,
            "project", proj.project_id,
            actor       = author,
            after_state = proj.to_dict(),
        )
        return proj

    def get_project(self, project_id: str) -> ResearchProject:
        return self._registry.get(project_id)

    def list_projects(self, status: Optional[ResearchStatus] = None) -> list[ResearchProject]:
        if status is None:
            return self._registry.all_projects()
        return self._registry.by_status(status)

    # ── Lineage ───────────────────────────────────────────────────────────────

    def record_lineage(
        self,
        from_id:   str,
        to_id:     str,
        edge_type: LineageEdgeType,
        **kwargs:  Any,
    ) -> None:
        self._lineage.link(from_id, to_id, edge_type, **kwargs)

    def get_ancestry(self, entity_id: str):
        return self._lineage.ancestors(entity_id)

    def get_descendants(self, entity_id: str):
        return self._lineage.descendants(entity_id)

    # ── Provenance ────────────────────────────────────────────────────────────

    def record_provenance(self, entity_id: str, entity_type: ProvenanceType, author: str, **kwargs: Any):
        return self._provenance.record(entity_id, entity_type, author, **kwargs)

    def get_provenance(self, entity_id: str):
        return self._provenance.latest_for_entity(entity_id)

    # ── Reproducibility ───────────────────────────────────────────────────────

    def snapshot_environment(self, entity_id: str):
        return self._reproducibility.snapshot_environment(entity_id)

    def check_reproducibility(self, entity_id: str) -> ReproducibilityStatus:
        return self._reproducibility.check_reproducibility(entity_id)

    # ── Approvals ─────────────────────────────────────────────────────────────

    def submit_for_approval(
        self,
        entity_id:   str,
        entity_type: str,
        submitter:   str,
        stages:      list[ReviewStage],
        **kwargs: Any,
    ):
        return self._approvals.submit(entity_id, entity_type, submitter, stages, **kwargs)

    def review_approval(
        self,
        workflow_id: str,
        stage:       ReviewStage,
        decision:    ReviewDecision,
        reviewer:    str,
        comments:    str = "",
    ):
        return self._approvals.review(workflow_id, stage, decision, reviewer, comments)

    def get_workflow(self, workflow_id: str):
        return self._approvals.get_workflow(workflow_id)

    # ── Artifacts ─────────────────────────────────────────────────────────────

    def register_artifact(self, name: str, artifact_type: ArtifactType, **kwargs: Any):
        return self._artifacts.register(name, artifact_type, **kwargs)

    def get_artifact(self, artifact_id: str):
        return self._artifacts.get(artifact_id)

    # ── Compliance ────────────────────────────────────────────────────────────

    def validate_compliance(self, entity: dict[str, Any], **kwargs: Any):
        return self._compliance.run_compliance_check(entity, **kwargs)

    # ── Audit ─────────────────────────────────────────────────────────────────

    def audit(
        self,
        event_type:  AuditEventType,
        entity_type: str,
        entity_id:   str,
        **kwargs: Any,
    ) -> None:
        self._audit.log_event(event_type, entity_type, entity_id, **kwargs)

    def audit_trail(self, entity_id: str, limit: int = 100):
        return self._audit.trail(entity_id, limit=limit)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "projects":      self._registry.stats(),
            "lineage":       self._lineage.stats(),
            "provenance":    self._provenance.stats(),
            "reproducibility": self._reproducibility.stats(),
            "approvals":     self._approvals.stats(),
            "artifacts":     self._artifacts.stats(),
            "compliance":    self._compliance.stats(),
            "audit":         self._audit.stats(),
        }

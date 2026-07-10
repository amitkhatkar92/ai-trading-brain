"""research_governance_engine.py — Singleton facade for the governance framework."""
from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    ArtifactType,
    AuditEventType,
    GovernanceEngineStatus,
    LineageEdgeType,
    PolicyType,
    ProvenanceType,
    ReproducibilityStatus,
    ResearchStatus,
    ReviewDecision,
    ReviewStage,
    GOVERNANCE_ENGINE_VERSION,
)
from iios.integration.research.governance.governance_exceptions import (
    EngineAlreadyRunningError,
    EngineNotRunningError,
)
from iios.integration.research.governance.core.governance_configuration import GovernanceConfiguration
from iios.integration.research.governance.core.governance_report        import GovernanceReport
from iios.integration.research.governance.governance_manager            import GovernanceManager


class ResearchGovernanceEngine:
    """
    Top-level governance facade.

    Lifecycle: ``await engine.start()`` → use operations → ``await engine.stop()``.

    All sub-engine operations are synchronous and thread-safe.
    The singleton is obtained via ``get_governance_engine()``.
    """

    VERSION = GOVERNANCE_ENGINE_VERSION

    def __init__(self, config: Optional[GovernanceConfiguration] = None) -> None:
        self._config     = config or GovernanceConfiguration()
        self._status     = GovernanceEngineStatus.STOPPED
        self._started_at: Optional[float] = None
        self._manager:    Optional[GovernanceManager] = None
        self._lock        = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        with self._lock:
            if self._status == GovernanceEngineStatus.RUNNING:
                raise EngineAlreadyRunningError("ResearchGovernanceEngine is already running")
            errs = self._config.validate()
            if errs:
                raise ValueError(f"Invalid configuration: {errs}")
            self._manager    = GovernanceManager(self._config)
            self._started_at = time.time()
            self._status     = GovernanceEngineStatus.RUNNING

    async def stop(self) -> None:
        with self._lock:
            if self._status != GovernanceEngineStatus.RUNNING:
                return
            self._status = GovernanceEngineStatus.STOPPED

    def is_running(self) -> bool:
        return self._status == GovernanceEngineStatus.RUNNING

    def status(self) -> GovernanceEngineStatus:
        return self._status

    def uptime_sec(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    def _require_running(self) -> GovernanceManager:
        if self._status != GovernanceEngineStatus.RUNNING or self._manager is None:
            raise EngineNotRunningError("ResearchGovernanceEngine is not running")
        return self._manager

    # ── Projects ──────────────────────────────────────────────────────────────

    def register_project(self, name: str, author: str, **kwargs: Any):
        return self._require_running().register_project(name, author, **kwargs)

    def get_project(self, project_id: str):
        return self._require_running().get_project(project_id)

    def list_projects(self, status: Optional[ResearchStatus] = None):
        return self._require_running().list_projects(status)

    # ── Lineage ───────────────────────────────────────────────────────────────

    def record_lineage(self, from_id: str, to_id: str, edge_type: LineageEdgeType, **kwargs: Any) -> None:
        self._require_running().record_lineage(from_id, to_id, edge_type, **kwargs)

    def get_ancestry(self, entity_id: str):
        return self._require_running().get_ancestry(entity_id)

    def get_descendants(self, entity_id: str):
        return self._require_running().get_descendants(entity_id)

    # ── Provenance ────────────────────────────────────────────────────────────

    def record_provenance(self, entity_id: str, entity_type: ProvenanceType, author: str, **kwargs: Any):
        return self._require_running().record_provenance(entity_id, entity_type, author, **kwargs)

    def get_provenance(self, entity_id: str):
        return self._require_running().get_provenance(entity_id)

    # ── Reproducibility ───────────────────────────────────────────────────────

    def snapshot_environment(self, entity_id: str):
        return self._require_running().snapshot_environment(entity_id)

    def check_reproducibility(self, entity_id: str) -> ReproducibilityStatus:
        return self._require_running().check_reproducibility(entity_id)

    # ── Approvals ─────────────────────────────────────────────────────────────

    def submit_for_approval(self, entity_id: str, entity_type: str, submitter: str,
                            stages: list[ReviewStage], **kwargs: Any):
        return self._require_running().submit_for_approval(
            entity_id, entity_type, submitter, stages, **kwargs
        )

    def review(self, workflow_id: str, stage: ReviewStage, decision: ReviewDecision,
               reviewer: str, comments: str = ""):
        return self._require_running().review_approval(workflow_id, stage, decision, reviewer, comments)

    def get_workflow(self, workflow_id: str):
        return self._require_running().get_workflow(workflow_id)

    # ── Artifacts ─────────────────────────────────────────────────────────────

    def register_artifact(self, name: str, artifact_type: ArtifactType, **kwargs: Any):
        return self._require_running().register_artifact(name, artifact_type, **kwargs)

    def get_artifact(self, artifact_id: str):
        return self._require_running().get_artifact(artifact_id)

    # ── Compliance ────────────────────────────────────────────────────────────

    def validate_compliance(self, entity_id: str, entity_dict: dict[str, Any], **kwargs: Any):
        return self._require_running().validate_compliance(entity_dict, **kwargs)

    # ── Audit ─────────────────────────────────────────────────────────────────

    def audit(self, event_type: AuditEventType, entity_type: str, entity_id: str, **kwargs: Any) -> None:
        self._require_running().audit(event_type, entity_type, entity_id, **kwargs)

    def audit_trail(self, entity_id: str, limit: int = 100):
        return self._require_running().audit_trail(entity_id, limit=limit)

    # ── Report / Stats ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        mgr = self._require_running()
        s   = mgr.stats()
        s["engine_status"] = self._status.value
        s["uptime_sec"]    = self.uptime_sec()
        return s

    def generate_report(self) -> GovernanceReport:
        mgr  = self._require_running()
        s    = mgr.stats()
        return GovernanceReport.create(
            engine_status      = self._status.value,
            uptime_sec         = self.uptime_sec(),
            total_projects     = s["projects"]["total"],
            active_projects    = s["projects"]["by_status"].get("active", 0),
            total_artifacts    = s["artifacts"]["registry"]["total"],
            total_approvals    = s["approvals"]["total"],
            pending_approvals  = s["approvals"]["by_status"].get("pending", 0),
            total_audit_entries = s["audit"]["total_audit_entries"],
            compliance_summary = s["compliance"],
            lineage_nodes      = s["lineage"]["graph"]["nodes"],
            provenance_records = s["provenance"]["total"],
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance:  Optional[ResearchGovernanceEngine] = None
_inst_lock: threading.Lock                     = threading.Lock()


def get_governance_engine(
    auto_start: bool = False,
    config:     Optional[GovernanceConfiguration] = None,
) -> ResearchGovernanceEngine:
    global _instance
    with _inst_lock:
        if _instance is None:
            _instance = ResearchGovernanceEngine(config)
        if auto_start and not _instance.is_running():
            asyncio.run(_instance.start())
    return _instance


def reset_governance_engine() -> None:
    global _instance
    with _inst_lock:
        if _instance is not None and _instance.is_running():
            asyncio.run(_instance.stop())
        _instance = None

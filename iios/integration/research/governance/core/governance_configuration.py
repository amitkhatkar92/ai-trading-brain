"""core/governance_configuration.py — Governance framework configuration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.governance.governance_constants import (
    DEFAULT_APPROVAL_TIMEOUT_DAYS,
    DEFAULT_MAX_ARTIFACTS,
    DEFAULT_MAX_AUDIT_ENTRIES,
    DEFAULT_MAX_LINEAGE_NODES,
    DEFAULT_MAX_PROVENANCE_RECORDS,
    DEFAULT_MAX_RESEARCH_PROJECTS,
    DEFAULT_RETENTION_DAYS,
)


@dataclass
class GovernanceConfiguration:
    """
    Centralised configuration for the Research Governance Framework.

    All limits, defaults, and policy switches live here.
    Values are validated by ``validate()`` before the engine starts.
    """

    # Capacities
    max_research_projects:  int   = DEFAULT_MAX_RESEARCH_PROJECTS
    max_artifacts:          int   = DEFAULT_MAX_ARTIFACTS
    max_audit_entries:      int   = DEFAULT_MAX_AUDIT_ENTRIES
    max_lineage_nodes:      int   = DEFAULT_MAX_LINEAGE_NODES
    max_provenance_records: int   = DEFAULT_MAX_PROVENANCE_RECORDS

    # Approval workflow
    approval_timeout_days:  int   = DEFAULT_APPROVAL_TIMEOUT_DAYS
    require_peer_review:    bool  = True
    require_risk_review:    bool  = True
    auto_archive_rejected:  bool  = True

    # Reproducibility
    capture_env_on_create:  bool  = True
    enforce_seed_policy:    bool  = False
    default_random_seed:    int   = 42

    # Retention
    retention_days:         int   = DEFAULT_RETENTION_DAYS

    # Background workers
    background_audit:       bool  = True
    parallel_lineage:       bool  = True

    # Extra free-form config
    extra:                  dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.max_research_projects < 1:
            errors.append("max_research_projects must be >= 1")
        if self.max_artifacts < 1:
            errors.append("max_artifacts must be >= 1")
        if self.approval_timeout_days < 1:
            errors.append("approval_timeout_days must be >= 1")
        if self.retention_days < 1:
            errors.append("retention_days must be >= 1")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_research_projects":  self.max_research_projects,
            "max_artifacts":          self.max_artifacts,
            "max_audit_entries":      self.max_audit_entries,
            "approval_timeout_days":  self.approval_timeout_days,
            "require_peer_review":    self.require_peer_review,
            "require_risk_review":    self.require_risk_review,
            "retention_days":         self.retention_days,
            "capture_env_on_create":  self.capture_env_on_create,
            "enforce_seed_policy":    self.enforce_seed_policy,
        }

"""
governance_snapshot.py -- iios.ai.governance.snapshot
=======================================================
Point-in-time frozen snapshots for the A8 AI Governance Platform.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PolicySnapshot:
    """Immutable snapshot of the policy registry state."""

    snapshot_id:    str
    total_policies: int
    active_policies: int
    violation_count: int
    captured_at:    float

    @classmethod
    def capture(
        cls,
        total_policies:  int,
        active_policies: int,
        violation_count: int,
    ) -> "PolicySnapshot":
        return cls(
            snapshot_id     = str(uuid.uuid4()),
            total_policies  = total_policies,
            active_policies = active_policies,
            violation_count = violation_count,
            captured_at     = time.time(),
        )


@dataclass(frozen=True)
class GovernanceFrameworkSnapshot:
    """
    Immutable point-in-time snapshot of the entire A8 governance platform.
    """

    snapshot_id:       str
    is_running:        bool
    total_policies:    int
    active_policies:   int
    total_audit_records: int
    total_explanations: int
    total_risk_violations: int
    total_roles:       int
    compliance_rules:  int
    counters:          frozenset   # FrozenSet[Tuple[str, Any]]
    captured_at:       float

    @classmethod
    def build(
        cls,
        is_running:            bool,
        total_policies:        int,
        active_policies:       int,
        total_audit_records:   int,
        total_explanations:    int,
        total_risk_violations: int,
        total_roles:           int,
        compliance_rules:      int,
        counters:              Dict[str, Any] = None,
    ) -> "GovernanceFrameworkSnapshot":
        return cls(
            snapshot_id            = str(uuid.uuid4()),
            is_running             = is_running,
            total_policies         = total_policies,
            active_policies        = active_policies,
            total_audit_records    = total_audit_records,
            total_explanations     = total_explanations,
            total_risk_violations  = total_risk_violations,
            total_roles            = total_roles,
            compliance_rules       = compliance_rules,
            counters               = frozenset((counters or {}).items()),
            captured_at            = time.time(),
        )

"""
capability_snapshot.py -- iios.ai.capability.snapshot
=======================================================
:class:`CapabilitySystemSnapshot` — point-in-time view of platform state.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilitySystemSnapshot:
    """Immutable point-in-time snapshot of the entire capability platform."""

    snapshot_id:          str
    captured_at:          float
    is_running:           bool
    total_capabilities:   int
    active_capabilities:  int
    disabled_capabilities: int
    total_connectors:     int
    total_skills:         int
    total_handlers:       int
    total_audit_records:  int
    total_executions:     int
    failed_executions:    int
    total_roles:          int
    total_permissions:    int
    policy_count:         int
    quota_count:          int

    @classmethod
    def build(
        cls,
        is_running:            bool,
        total_capabilities:    int,
        active_capabilities:   int,
        disabled_capabilities: int,
        total_connectors:      int,
        total_skills:          int,
        total_handlers:        int,
        total_audit_records:   int,
        total_executions:      int,
        failed_executions:     int,
        total_roles:           int,
        total_permissions:     int,
        policy_count:          int,
        quota_count:           int,
    ) -> "CapabilitySystemSnapshot":
        return cls(
            snapshot_id           = str(uuid.uuid4()),
            captured_at           = time.time(),
            is_running            = is_running,
            total_capabilities    = total_capabilities,
            active_capabilities   = active_capabilities,
            disabled_capabilities = disabled_capabilities,
            total_connectors      = total_connectors,
            total_skills          = total_skills,
            total_handlers        = total_handlers,
            total_audit_records   = total_audit_records,
            total_executions      = total_executions,
            failed_executions     = failed_executions,
            total_roles           = total_roles,
            total_permissions     = total_permissions,
            policy_count          = policy_count,
            quota_count           = quota_count,
        )

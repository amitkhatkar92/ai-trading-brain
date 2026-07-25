"""
exceptions.py — iios.workflow.snapshot
----------------------------------------
Exception hierarchy for the Workflow Snapshot module.

Error codes: WSS-000 through WSS-009

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

from typing import List, Optional

from iios.common.errors.exceptions import IIOSError


class WorkflowSnapshotError(IIOSError):
    """WSS-000 — Base exception for Workflow Snapshot."""
    error_code = "WSS-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowSnapshotNotFoundError(WorkflowSnapshotError):
    """WSS-001 — Snapshot not found in registry or store."""
    error_code = "WSS-001"

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(f"Snapshot not found: {snapshot_id!r}")
        self.snapshot_id = snapshot_id


class WorkflowSnapshotValidationError(WorkflowSnapshotError):
    """WSS-002 — Snapshot failed validation."""
    error_code = "WSS-002"

    def __init__(self, message: str, *, issues: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.issues: List[str] = list(issues or [])


class WorkflowSnapshotBuildError(WorkflowSnapshotError):
    """WSS-003 — Snapshot builder failed to construct snapshot."""
    error_code = "WSS-003"


class WorkflowSnapshotRegistryError(WorkflowSnapshotError):
    """WSS-004 — Registry error (full, duplicate, etc.)."""
    error_code = "WSS-004"


class WorkflowSnapshotStoreError(WorkflowSnapshotError):
    """WSS-005 — Store error (persistence failure)."""
    error_code = "WSS-005"


class WorkflowSnapshotCacheError(WorkflowSnapshotError):
    """WSS-006 — Cache error."""
    error_code = "WSS-006"


class WorkflowSnapshotBundleError(WorkflowSnapshotError):
    """WSS-007 — Bundle assembly or retrieval error."""
    error_code = "WSS-007"


class WorkflowSnapshotVersionError(WorkflowSnapshotError):
    """WSS-008 — Version conflict or consistency error."""
    error_code = "WSS-008"


class WorkflowSnapshotSerializationError(WorkflowSnapshotError):
    """WSS-009 — Serialization or deserialization failure."""
    error_code = "WSS-009"

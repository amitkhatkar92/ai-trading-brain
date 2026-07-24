"""
knowledge_integration_response.py — iios.knowledge.integration
---------------------------------------------------------------
KnowledgeIntegrationResponse — the primary output from the integration engine.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import IntegrationPhase


@dataclass(frozen=True)
class KnowledgeIntegrationResponse:
    """
    Immutable response returned by KnowledgeIntegrationEngine.

    Carries the KnowledgeSnapshot, summaries, and operational metadata
    for the completed integration workflow.
    """
    # Core identifiers
    response_id:   str
    request_id:    str
    integration_id: str
    session_id:    str
    workflow_id:   str
    enterprise_id: str

    # Outcome
    succeeded:       bool
    error_message:   str
    phases_completed: tuple   # Tuple[str]  — phase values that ran

    # Knowledge output
    snapshot_id:       str               # M5 KnowledgeSnapshot.snapshot_id (or "")
    knowledge_summary: Dict[str, Any]    # summary from M4 report
    health_summary:    Dict[str, Any]    # integration health at time of response

    # Performance
    processing_duration_ms: float
    response_duration_ms:   float

    # Timestamps
    responded_at: str

    # ----------------------------------------------------------------
    # Factory
    # ----------------------------------------------------------------

    @classmethod
    def success(
        cls,
        request_id:    str,
        integration_id: str,
        session_id:    str,
        workflow_id:   str,
        enterprise_id: str,
        *,
        phases_completed:       List[IntegrationPhase],
        snapshot_id:            str = "",
        knowledge_summary:      Optional[Dict[str, Any]] = None,
        health_summary:         Optional[Dict[str, Any]] = None,
        processing_duration_ms: float = 0.0,
        response_duration_ms:   float = 0.0,
    ) -> "KnowledgeIntegrationResponse":
        return cls(
            response_id    = f"resp-{uuid.uuid4().hex[:12]}",
            request_id     = request_id,
            integration_id = integration_id,
            session_id     = session_id,
            workflow_id    = workflow_id,
            enterprise_id  = enterprise_id,
            succeeded      = True,
            error_message  = "",
            phases_completed = tuple(p.value for p in phases_completed),
            snapshot_id      = snapshot_id,
            knowledge_summary = dict(knowledge_summary or {}),
            health_summary    = dict(health_summary or {}),
            processing_duration_ms = processing_duration_ms,
            response_duration_ms   = response_duration_ms,
            responded_at   = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def failure(
        cls,
        request_id:    str,
        integration_id: str,
        session_id:    str,
        workflow_id:   str,
        enterprise_id: str,
        *,
        error_message:          str,
        phases_completed:       Optional[List[IntegrationPhase]] = None,
        processing_duration_ms: float = 0.0,
        response_duration_ms:   float = 0.0,
    ) -> "KnowledgeIntegrationResponse":
        return cls(
            response_id    = f"resp-{uuid.uuid4().hex[:12]}",
            request_id     = request_id,
            integration_id = integration_id,
            session_id     = session_id,
            workflow_id    = workflow_id,
            enterprise_id  = enterprise_id,
            succeeded      = False,
            error_message  = error_message,
            phases_completed = tuple(
                p.value for p in (phases_completed or [])
            ),
            snapshot_id       = "",
            knowledge_summary = {},
            health_summary    = {},
            processing_duration_ms = processing_duration_ms,
            response_duration_ms   = response_duration_ms,
            responded_at   = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ----------------------------------------------------------------
    # Serialization
    # ----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":    self.response_id,
            "request_id":     self.request_id,
            "integration_id": self.integration_id,
            "session_id":     self.session_id,
            "workflow_id":    self.workflow_id,
            "enterprise_id":  self.enterprise_id,
            "succeeded":      self.succeeded,
            "error_message":  self.error_message,
            "phases_completed":       list(self.phases_completed),
            "snapshot_id":            self.snapshot_id,
            "knowledge_summary":      self.knowledge_summary,
            "health_summary":         self.health_summary,
            "processing_duration_ms": self.processing_duration_ms,
            "response_duration_ms":   self.response_duration_ms,
            "responded_at":           self.responded_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeIntegrationResponse":
        return cls(
            response_id    = d["response_id"],
            request_id     = d["request_id"],
            integration_id = d.get("integration_id", ""),
            session_id     = d["session_id"],
            workflow_id    = d["workflow_id"],
            enterprise_id  = d["enterprise_id"],
            succeeded      = d.get("succeeded", False),
            error_message  = d.get("error_message", ""),
            phases_completed        = tuple(d.get("phases_completed", [])),
            snapshot_id             = d.get("snapshot_id", ""),
            knowledge_summary       = d.get("knowledge_summary", {}),
            health_summary          = d.get("health_summary", {}),
            processing_duration_ms  = d.get("processing_duration_ms", 0.0),
            response_duration_ms    = d.get("response_duration_ms", 0.0),
            responded_at   = d.get("responded_at", ""),
        )

"""
knowledge_integration_request.py — iios.knowledge.integration
--------------------------------------------------------------
KnowledgeIntegrationRequest — the primary input to the integration engine.

Accepts knowledge artifacts and optional snapshots from all peer subsystems
(Execution, Decision, Portfolio, Risk, Market, Supervisor).

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_TIMEOUT_MS, FRAMEWORK_VERSION, IntegrationRequestType


@dataclass(frozen=True)
class KnowledgeIntegrationRequest:
    """
    Immutable request submitted to KnowledgeIntegrationEngine.

    Carries:
      - Session / workflow / enterprise identifiers
      - Knowledge artifacts to process
      - Optional peer subsystem snapshots
      - Query / search / retrieve parameters
    """
    # Core identifiers
    request_id:    str
    session_id:    str
    workflow_id:   str
    enterprise_id: str
    request_type:  IntegrationRequestType

    # Knowledge artifacts
    artifacts:     tuple   # Tuple[Dict[str, Any]]

    # Optional peer subsystem snapshots (generic dict representation)
    execution_snapshot:          Optional[Dict[str, Any]]
    execution_recovery_snapshot: Optional[Dict[str, Any]]
    execution_analytics_snapshot: Optional[Dict[str, Any]]
    decision_snapshot:           Optional[Dict[str, Any]]
    portfolio_snapshot:          Optional[Dict[str, Any]]
    risk_snapshot:               Optional[Dict[str, Any]]
    market_snapshot:             Optional[Dict[str, Any]]
    supervisor_snapshot:         Optional[Dict[str, Any]]

    # Query / search / retrieve parameters
    query_text:      str
    search_filters:  Dict[str, Any]
    retrieve_id:     str

    # Options
    validate:    bool
    timeout_ms:  int
    correlation_id: str
    trace_id:       str
    requested_at:   str

    # ----------------------------------------------------------------
    # Constructors
    # ----------------------------------------------------------------

    @classmethod
    def create(
        cls,
        session_id:    str,
        workflow_id:   str,
        enterprise_id: str,
        *,
        request_type:  IntegrationRequestType         = IntegrationRequestType.FULL_INTEGRATION,
        artifacts:     Optional[List[Dict[str, Any]]] = None,
        execution_snapshot:           Optional[Dict[str, Any]] = None,
        execution_recovery_snapshot:  Optional[Dict[str, Any]] = None,
        execution_analytics_snapshot: Optional[Dict[str, Any]] = None,
        decision_snapshot:            Optional[Dict[str, Any]] = None,
        portfolio_snapshot:           Optional[Dict[str, Any]] = None,
        risk_snapshot:                Optional[Dict[str, Any]] = None,
        market_snapshot:              Optional[Dict[str, Any]] = None,
        supervisor_snapshot:          Optional[Dict[str, Any]] = None,
        query_text:     str  = "",
        search_filters: Optional[Dict[str, Any]] = None,
        retrieve_id:    str  = "",
        validate:       bool = True,
        timeout_ms:     int  = DEFAULT_TIMEOUT_MS,
        correlation_id: str  = "",
        trace_id:       str  = "",
    ) -> "KnowledgeIntegrationRequest":
        return cls(
            request_id    = f"req-{uuid.uuid4().hex[:12]}",
            session_id    = session_id,
            workflow_id   = workflow_id,
            enterprise_id = enterprise_id,
            request_type  = request_type,
            artifacts     = tuple(artifacts or []),
            execution_snapshot           = execution_snapshot,
            execution_recovery_snapshot  = execution_recovery_snapshot,
            execution_analytics_snapshot = execution_analytics_snapshot,
            decision_snapshot            = decision_snapshot,
            portfolio_snapshot           = portfolio_snapshot,
            risk_snapshot                = risk_snapshot,
            market_snapshot              = market_snapshot,
            supervisor_snapshot          = supervisor_snapshot,
            query_text     = query_text,
            search_filters = dict(search_filters or {}),
            retrieve_id    = retrieve_id,
            validate       = validate,
            timeout_ms     = timeout_ms,
            correlation_id = correlation_id or f"cid-{uuid.uuid4().hex[:8]}",
            trace_id       = trace_id or f"tid-{uuid.uuid4().hex[:8]}",
            requested_at   = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ----------------------------------------------------------------
    # Computed properties
    # ----------------------------------------------------------------

    @property
    def artifact_count(self) -> int:
        return len(self.artifacts)

    @property
    def has_peer_snapshots(self) -> bool:
        return any([
            self.execution_snapshot,
            self.execution_recovery_snapshot,
            self.execution_analytics_snapshot,
            self.decision_snapshot,
            self.portfolio_snapshot,
            self.risk_snapshot,
            self.market_snapshot,
            self.supervisor_snapshot,
        ])

    # ----------------------------------------------------------------
    # Serialization
    # ----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "session_id":    self.session_id,
            "workflow_id":   self.workflow_id,
            "enterprise_id": self.enterprise_id,
            "request_type":  self.request_type.value,
            "artifacts":     list(self.artifacts),
            "execution_snapshot":            self.execution_snapshot,
            "execution_recovery_snapshot":   self.execution_recovery_snapshot,
            "execution_analytics_snapshot":  self.execution_analytics_snapshot,
            "decision_snapshot":             self.decision_snapshot,
            "portfolio_snapshot":            self.portfolio_snapshot,
            "risk_snapshot":                 self.risk_snapshot,
            "market_snapshot":               self.market_snapshot,
            "supervisor_snapshot":           self.supervisor_snapshot,
            "query_text":     self.query_text,
            "search_filters": self.search_filters,
            "retrieve_id":    self.retrieve_id,
            "validate":       self.validate,
            "timeout_ms":     self.timeout_ms,
            "correlation_id": self.correlation_id,
            "trace_id":       self.trace_id,
            "requested_at":   self.requested_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeIntegrationRequest":
        return cls(
            request_id    = d["request_id"],
            session_id    = d["session_id"],
            workflow_id   = d["workflow_id"],
            enterprise_id = d["enterprise_id"],
            request_type  = IntegrationRequestType(
                d.get("request_type", IntegrationRequestType.FULL_INTEGRATION.value)
            ),
            artifacts     = tuple(d.get("artifacts", [])),
            execution_snapshot           = d.get("execution_snapshot"),
            execution_recovery_snapshot  = d.get("execution_recovery_snapshot"),
            execution_analytics_snapshot = d.get("execution_analytics_snapshot"),
            decision_snapshot            = d.get("decision_snapshot"),
            portfolio_snapshot           = d.get("portfolio_snapshot"),
            risk_snapshot                = d.get("risk_snapshot"),
            market_snapshot              = d.get("market_snapshot"),
            supervisor_snapshot          = d.get("supervisor_snapshot"),
            query_text     = d.get("query_text", ""),
            search_filters = d.get("search_filters", {}),
            retrieve_id    = d.get("retrieve_id", ""),
            validate       = d.get("validate", True),
            timeout_ms     = d.get("timeout_ms", DEFAULT_TIMEOUT_MS),
            correlation_id = d.get("correlation_id", ""),
            trace_id       = d.get("trace_id", ""),
            requested_at   = d.get("requested_at", ""),
        )

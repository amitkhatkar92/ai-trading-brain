"""
integration_policy_context.py — iios.integration.policies
-----------------------------------------------------------
IntegrationPolicyContext — carries all attributes against which
governance policies are evaluated.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class IntegrationPolicyContext:
    """
    Immutable evaluation context supplied to every policy rule.

    Contains all integration attributes needed for governance
    decision-making: connector type, endpoint, authentication config,
    security settings, compliance requirements, and more.

    The ``as_flat_dict()`` method exposes a traversable dict that
    policy conditions use via dot-notation field paths.
    """

    context_id:         str
    engine_request_id:  str          # from IntegrationRequest.request_id
    engine_session_id:  str
    connector_type:     str
    adapter_type:       str
    protocol_type:      str
    endpoint:           str
    environment:        str
    priority:           int
    auth_config:        Dict[str, Any]
    security_config:    Dict[str, Any]
    compliance_config:  Dict[str, Any]
    connector_config:   Dict[str, Any]
    adapter_config:     Dict[str, Any]
    protocol_config:    Dict[str, Any]
    endpoint_config:    Dict[str, Any]
    metadata:           Dict[str, Any]
    created_at:         str

    # ── factory ───────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        engine_request_id: str,
        engine_session_id: str,
        connector_type:    str,
        adapter_type:      str           = "",
        protocol_type:     str           = "",
        endpoint:          str           = "",
        environment:       str           = "production",
        priority:          int           = 5,
        *,
        auth_config:        Optional[Dict[str, Any]] = None,
        security_config:    Optional[Dict[str, Any]] = None,
        compliance_config:  Optional[Dict[str, Any]] = None,
        connector_config:   Optional[Dict[str, Any]] = None,
        adapter_config:     Optional[Dict[str, Any]] = None,
        protocol_config:    Optional[Dict[str, Any]] = None,
        endpoint_config:    Optional[Dict[str, Any]] = None,
        metadata:           Optional[Dict[str, Any]] = None,
        context_id:         Optional[str]            = None,
    ) -> "IntegrationPolicyContext":
        return cls(
            context_id         = context_id or f"pctx-{uuid.uuid4().hex[:12]}",
            engine_request_id  = engine_request_id,
            engine_session_id  = engine_session_id,
            connector_type     = connector_type,
            adapter_type       = adapter_type,
            protocol_type      = protocol_type,
            endpoint           = endpoint,
            environment        = environment,
            priority           = priority,
            auth_config        = dict(auth_config       or {}),
            security_config    = dict(security_config   or {}),
            compliance_config  = dict(compliance_config or {}),
            connector_config   = dict(connector_config  or {}),
            adapter_config     = dict(adapter_config    or {}),
            protocol_config    = dict(protocol_config   or {}),
            endpoint_config    = dict(endpoint_config   or {}),
            metadata           = dict(metadata          or {}),
            created_at         = datetime.now(timezone.utc).isoformat(),
        )

    # ── context data for condition evaluation ─────────────────────────

    def as_flat_dict(self) -> Dict[str, Any]:
        """
        Return a flat dict accessible to policy conditions.

        Conditions reference these attributes via dot-paths such as
        ``connector_type``, ``security_config.tls_required``, etc.
        """
        return {
            "context_id":         self.context_id,
            "engine_request_id":  self.engine_request_id,
            "engine_session_id":  self.engine_session_id,
            "connector_type":     self.connector_type,
            "adapter_type":       self.adapter_type,
            "protocol_type":      self.protocol_type,
            "endpoint":           self.endpoint,
            "environment":        self.environment,
            "priority":           self.priority,
            "auth_config":        self.auth_config,
            "security_config":    self.security_config,
            "compliance_config":  self.compliance_config,
            "connector_config":   self.connector_config,
            "adapter_config":     self.adapter_config,
            "protocol_config":    self.protocol_config,
            "endpoint_config":    self.endpoint_config,
            "metadata":           self.metadata,
        }

    # ── serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":         self.context_id,
            "engine_request_id":  self.engine_request_id,
            "engine_session_id":  self.engine_session_id,
            "connector_type":     self.connector_type,
            "adapter_type":       self.adapter_type,
            "protocol_type":      self.protocol_type,
            "endpoint":           self.endpoint,
            "environment":        self.environment,
            "priority":           self.priority,
            "auth_config":        self.auth_config,
            "security_config":    self.security_config,
            "compliance_config":  self.compliance_config,
            "connector_config":   self.connector_config,
            "adapter_config":     self.adapter_config,
            "protocol_config":    self.protocol_config,
            "endpoint_config":    self.endpoint_config,
            "metadata":           self.metadata,
            "created_at":         self.created_at,
        }

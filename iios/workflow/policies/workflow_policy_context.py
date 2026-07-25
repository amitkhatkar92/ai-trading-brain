"""
workflow_policy_context.py — iios.workflow.policies
----------------------------------------------------
WorkflowPolicyContext — the evaluation context passed to every
governance policy during assessment.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class WorkflowPolicyContext:
    """
    Immutable evaluation context for governance policy assessment.

    Carries all information required for policy rule evaluation:
    workflow identity, security context, compliance context, and
    resource context.

    The `to_flat_dict()` method flattens the context into a dot-notation
    accessible dict that PolicyCondition.evaluate() can traverse.
    """
    context_id:         str
    workflow_id:        str
    workflow_type:      str
    enterprise_id:      str
    correlation_id:     str
    trace_id:           str
    environment:        str
    security_context:   Dict[str, Any]
    compliance_context: Dict[str, Any]
    resource_context:   Dict[str, Any]
    platform_context:   Dict[str, Any]
    metadata:           Dict[str, Any]
    created_at:         str

    @classmethod
    def create(
        cls,
        workflow_id:  str,
        workflow_type: str                       = "sequential",
        *,
        enterprise_id:      str                  = "iios",
        correlation_id:     str                  = "",
        trace_id:           str                  = "",
        environment:        str                  = "production",
        security_context:   Optional[Dict[str, Any]] = None,
        compliance_context: Optional[Dict[str, Any]] = None,
        resource_context:   Optional[Dict[str, Any]] = None,
        platform_context:   Optional[Dict[str, Any]] = None,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "WorkflowPolicyContext":
        return cls(
            context_id         = f"pctx-{uuid.uuid4().hex[:10]}",
            workflow_id        = workflow_id,
            workflow_type      = workflow_type,
            enterprise_id      = enterprise_id,
            correlation_id     = correlation_id or f"cid-{uuid.uuid4().hex[:8]}",
            trace_id           = trace_id or f"tid-{uuid.uuid4().hex[:8]}",
            environment        = environment,
            security_context   = dict(security_context or {}),
            compliance_context = dict(compliance_context or {}),
            resource_context   = dict(resource_context or {}),
            platform_context   = dict(platform_context or {}),
            metadata           = dict(metadata or {}),
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_flat_dict(self) -> Dict[str, Any]:
        """
        Flatten the context into a dot-notation accessible dict.

        Top-level fields are accessible directly (e.g., "workflow_type").
        Nested dicts are accessible via dot notation
        (e.g., "security_context.user_role").
        """
        flat: Dict[str, Any] = {
            "context_id":    self.context_id,
            "workflow_id":   self.workflow_id,
            "workflow_type": self.workflow_type,
            "enterprise_id": self.enterprise_id,
            "environment":   self.environment,
        }
        # Nested sections
        for section_name, section_data in [
            ("security_context",   self.security_context),
            ("compliance_context", self.compliance_context),
            ("resource_context",   self.resource_context),
            ("platform_context",   self.platform_context),
            ("metadata",           self.metadata),
        ]:
            if isinstance(section_data, dict):
                flat[section_name] = section_data
                for k, v in section_data.items():
                    flat[f"{section_name}.{k}"] = v
        return flat

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":         self.context_id,
            "workflow_id":        self.workflow_id,
            "workflow_type":      self.workflow_type,
            "enterprise_id":      self.enterprise_id,
            "environment":        self.environment,
            "security_context":   self.security_context,
            "compliance_context": self.compliance_context,
            "resource_context":   self.resource_context,
            "created_at":         self.created_at,
        }

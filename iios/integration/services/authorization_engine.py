"""
authorization_engine.py — iios.integration.services
-----------------------------------------------------
AuthorizationEngine — evaluates whether an authenticated principal
has permission to perform a connector operation.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from iios.common.logging.logging_manager import get_logger

from .constants import ConnectorOperation, ServiceType

_log = get_logger(__name__)


@dataclass(frozen=True)
class AuthorizationPolicy:
    """An immutable authorization policy entry."""
    policy_id:  str
    principal:  str                # username / client-id / role
    service_type: Optional[str]    # None = all service types
    operations: tuple              # tuple[ConnectorOperation, ...]
    allow:      bool               # True=ALLOW, False=DENY


@dataclass
class AuthorizationResult:
    """Result of an authorization check."""
    allowed:    bool
    principal:  str
    operation:  ConnectorOperation
    reason:     str = ""
    policy_id:  str = ""


class AuthorizationEngine:
    """
    Role-based and attribute-based authorization for integration operations.

    Policies are evaluated in registration order; the first matching DENY
    takes priority over any ALLOW. If no policy matches, the request is
    allowed by default (open-by-default for integration services).
    """

    def __init__(self, default_allow: bool = True) -> None:
        self._lock          = threading.Lock()
        self._policies:     List[AuthorizationPolicy] = []
        self._default_allow = default_allow
        self._allowed       = 0
        self._denied        = 0

    # ── Policy management ────────────────────────────────────────────────

    def add_policy(self, policy: AuthorizationPolicy) -> None:
        with self._lock:
            self._policies.append(policy)

    def remove_policy(self, policy_id: str) -> bool:
        with self._lock:
            before = len(self._policies)
            self._policies = [p for p in self._policies if p.policy_id != policy_id]
            return len(self._policies) < before

    def list_policies(self) -> List[AuthorizationPolicy]:
        with self._lock:
            return list(self._policies)

    # ── Authorization check ───────────────────────────────────────────────

    def authorize(
        self,
        principal:    str,
        operation:    ConnectorOperation,
        service_type: Optional[ServiceType] = None,
    ) -> AuthorizationResult:
        with self._lock:
            policies = list(self._policies)

        svc_val = service_type.value if service_type else None
        first_allow: Optional[AuthorizationPolicy] = None
        for policy in policies:
            # Principal must match (exact or wildcard "*")
            if policy.principal not in ("*", principal):
                continue
            # Service type must match if specified
            if policy.service_type and policy.service_type != svc_val:
                continue
            # Operation must match
            if operation not in policy.operations:
                continue
            # DENY match — first DENY wins
            if not policy.allow:
                with self._lock:
                    self._denied += 1
                return AuthorizationResult(
                    allowed   = False,
                    principal = principal,
                    operation = operation,
                    reason    = f"Denied by policy {policy.policy_id!r}",
                    policy_id = policy.policy_id,
                )
            # ALLOW match — record it, continue to check for any DENY
            if first_allow is None:
                first_allow = policy

        # If an ALLOW policy matched and no DENY was found, allow
        if first_allow is not None:
            with self._lock:
                self._allowed += 1
            return AuthorizationResult(
                allowed   = True,
                principal = principal,
                operation = operation,
                reason    = f"Allowed by policy {first_allow.policy_id!r}",
                policy_id = first_allow.policy_id,
            )

        # Default
        with self._lock:
            if self._default_allow:
                self._allowed += 1
            else:
                self._denied += 1
        return AuthorizationResult(
            allowed   = self._default_allow,
            principal = principal,
            operation = operation,
            reason    = "Default policy",
        )

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "policies": len(self._policies),
                "allowed":  self._allowed,
                "denied":   self._denied,
            }

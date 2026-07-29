"""
access_control.py -- iios.ai.governance.permissions
=====================================================
:class:`Capability`          — named capability string constant.
:class:`RolePolicy`          — immutable role definition with allowed capabilities.
:class:`CapabilityRestriction` — per-principal capability restriction.
:class:`AccessControl`       — thread-safe role + permission store.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional, Set, Tuple


@dataclass(frozen=True)
class RolePolicy:
    """
    Immutable role definition with a set of allowed capabilities.

    ``capabilities`` — frozenset of capability strings.
    ``allowed_actions`` — action patterns this role may perform.
    ``is_system_role`` — True for built-in roles that cannot be deleted.
    """

    role_id:          str
    name:             str
    description:      str
    capabilities:     FrozenSet[str]
    allowed_actions:  FrozenSet[str]
    is_system_role:   bool
    created_at:       float
    tags:             FrozenSet[str]

    @classmethod
    def create(
        cls,
        name:            str,
        capabilities:    FrozenSet[str]  = frozenset(),
        allowed_actions: FrozenSet[str]  = frozenset({"*"}),
        description:     str             = "",
        is_system_role:  bool            = False,
        tags:            FrozenSet[str]  = frozenset(),
    ) -> "RolePolicy":
        return cls(
            role_id         = str(uuid.uuid4()),
            name            = name,
            description     = description,
            capabilities    = frozenset(capabilities),
            allowed_actions = frozenset(allowed_actions),
            is_system_role  = is_system_role,
            created_at      = time.time(),
            tags            = frozenset(tags),
        )

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities or "*" in self.capabilities


@dataclass(frozen=True)
class CapabilityRestriction:
    """
    Immutable restriction that limits a principal's capabilities.

    ``denied_capabilities`` — capabilities explicitly denied regardless of role.
    ``allowed_override``    — capabilities explicitly allowed (overrides deny).
    """

    restriction_id:       str
    principal_id:         str
    denied_capabilities:  FrozenSet[str]
    allowed_override:     FrozenSet[str]
    reason:               str
    expires_at:           Optional[float]
    created_at:           float

    @classmethod
    def create(
        cls,
        principal_id:         str,
        denied_capabilities:  FrozenSet[str] = frozenset(),
        allowed_override:     FrozenSet[str] = frozenset(),
        reason:               str             = "",
        expires_at:           Optional[float] = None,
    ) -> "CapabilityRestriction":
        return cls(
            restriction_id       = str(uuid.uuid4()),
            principal_id         = principal_id,
            denied_capabilities  = frozenset(denied_capabilities),
            allowed_override     = frozenset(allowed_override),
            reason               = reason,
            expires_at           = expires_at,
            created_at           = time.time(),
        )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class AccessControl:
    """
    Thread-safe role + principal permission store.

    Principal → set of role_ids mapping.
    """

    def __init__(self) -> None:
        self._lock:         threading.Lock                 = threading.Lock()
        self._roles:        Dict[str, RolePolicy]          = {}
        self._assignments:  Dict[str, Set[str]]            = {}  # principal_id → {role_id}
        self._restrictions: Dict[str, CapabilityRestriction] = {}

    # ── roles ─────────────────────────────────────────────────────────────────

    def add_role(self, role: RolePolicy) -> None:
        with self._lock:
            self._roles[role.role_id] = role

    def remove_role(self, role_id: str) -> None:
        with self._lock:
            role = self._roles.get(role_id)
            if role and role.is_system_role:
                raise ValueError(f"Cannot remove system role {role.name!r}")
            self._roles.pop(role_id, None)

    def get_role(self, role_id: str) -> Optional[RolePolicy]:
        with self._lock:
            return self._roles.get(role_id)

    def list_roles(self) -> list:
        with self._lock:
            return list(self._roles.values())

    # ── assignments ───────────────────────────────────────────────────────────

    def assign_role(self, principal_id: str, role_id: str) -> None:
        with self._lock:
            self._assignments.setdefault(principal_id, set()).add(role_id)

    def revoke_role(self, principal_id: str, role_id: str) -> None:
        with self._lock:
            if principal_id in self._assignments:
                self._assignments[principal_id].discard(role_id)

    def get_roles_for(self, principal_id: str) -> FrozenSet[str]:
        with self._lock:
            return frozenset(self._assignments.get(principal_id, set()))

    # ── restrictions ──────────────────────────────────────────────────────────

    def add_restriction(self, restriction: CapabilityRestriction) -> None:
        with self._lock:
            self._restrictions[restriction.principal_id] = restriction

    def get_restriction(self, principal_id: str) -> Optional[CapabilityRestriction]:
        with self._lock:
            r = self._restrictions.get(principal_id)
        if r and r.is_expired():
            with self._lock:
                self._restrictions.pop(principal_id, None)
            return None
        return r

    # ── authorization ─────────────────────────────────────────────────────────

    def is_authorized(self, principal_id: str, capability: str) -> bool:
        """
        Return True if ``principal_id`` has ``capability`` via any assigned role,
        subject to active restrictions.
        """
        restriction = self.get_restriction(principal_id)
        if restriction:
            if capability in restriction.denied_capabilities and \
               capability not in restriction.allowed_override:
                return False

        with self._lock:
            role_ids = set(self._assignments.get(principal_id, set()))
            roles    = [self._roles[rid] for rid in role_ids if rid in self._roles]

        return any(r.has_capability(capability) for r in roles)

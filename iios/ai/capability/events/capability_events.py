"""
capability_events.py -- iios.ai.capability.events
===================================================
Immutable event types for the A9 Enterprise Capability Platform.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class CapabilityEventType(str, Enum):
    """All event types emitted by the capability platform."""
    CAPABILITY_REGISTERED   = "capability_registered"
    CAPABILITY_ENABLED      = "capability_enabled"
    CAPABILITY_DISABLED     = "capability_disabled"
    CAPABILITY_DEREGISTERED = "capability_deregistered"
    CAPABILITY_EXECUTED     = "capability_executed"
    CAPABILITY_FAILED       = "capability_failed"
    CAPABILITY_TIMEOUT      = "capability_timeout"
    CONNECTOR_REGISTERED    = "connector_registered"
    CONNECTOR_INVOKED       = "connector_invoked"
    CONNECTOR_FAILED        = "connector_failed"
    SKILL_REGISTERED        = "skill_registered"
    SKILL_EXECUTED          = "skill_executed"
    SKILL_FAILED            = "skill_failed"
    AUTHORIZATION_GRANTED   = "authorization_granted"
    AUTHORIZATION_DENIED    = "authorization_denied"
    AUTHORIZATION_REVOKED   = "authorization_revoked"
    QUOTA_EXCEEDED          = "quota_exceeded"
    RATE_LIMITED            = "rate_limited"
    POLICY_ADDED            = "policy_added"
    POLICY_REMOVED          = "policy_removed"


@dataclass(frozen=True)
class CapabilityEvent:
    """Immutable base event."""

    event_id:   str
    event_type: CapabilityEventType
    source:     str
    occurred_at: float


# ── Capability lifecycle events ──────────────────────────────────────────────

@dataclass(frozen=True)
class CapabilityRegisteredEvent(CapabilityEvent):
    capability_id: str
    capability_name: str

    @classmethod
    def create(cls, source: str, capability_id: str, capability_name: str
               ) -> "CapabilityRegisteredEvent":
        return cls(
            event_id        = str(uuid.uuid4()),
            event_type      = CapabilityEventType.CAPABILITY_REGISTERED,
            source          = source,
            occurred_at     = time.time(),
            capability_id   = capability_id,
            capability_name = capability_name,
        )


@dataclass(frozen=True)
class CapabilityEnabledEvent(CapabilityEvent):
    capability_id: str

    @classmethod
    def create(cls, source: str, capability_id: str) -> "CapabilityEnabledEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CapabilityEventType.CAPABILITY_ENABLED,
            source        = source,
            occurred_at   = time.time(),
            capability_id = capability_id,
        )


@dataclass(frozen=True)
class CapabilityDisabledEvent(CapabilityEvent):
    capability_id: str

    @classmethod
    def create(cls, source: str, capability_id: str) -> "CapabilityDisabledEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CapabilityEventType.CAPABILITY_DISABLED,
            source        = source,
            occurred_at   = time.time(),
            capability_id = capability_id,
        )


@dataclass(frozen=True)
class CapabilityDeregisteredEvent(CapabilityEvent):
    capability_id: str

    @classmethod
    def create(cls, source: str, capability_id: str) -> "CapabilityDeregisteredEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CapabilityEventType.CAPABILITY_DEREGISTERED,
            source        = source,
            occurred_at   = time.time(),
            capability_id = capability_id,
        )


# ── Execution events ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CapabilityExecutedEvent(CapabilityEvent):
    capability_id: str
    principal_id:  str
    duration_ms:   float

    @classmethod
    def create(cls, source: str, capability_id: str, principal_id: str,
               duration_ms: float = 0.0) -> "CapabilityExecutedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CapabilityEventType.CAPABILITY_EXECUTED,
            source        = source,
            occurred_at   = time.time(),
            capability_id = capability_id,
            principal_id  = principal_id,
            duration_ms   = duration_ms,
        )


@dataclass(frozen=True)
class CapabilityFailedEvent(CapabilityEvent):
    capability_id: str
    principal_id:  str
    error:         str

    @classmethod
    def create(cls, source: str, capability_id: str, principal_id: str,
               error: str = "") -> "CapabilityFailedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CapabilityEventType.CAPABILITY_FAILED,
            source        = source,
            occurred_at   = time.time(),
            capability_id = capability_id,
            principal_id  = principal_id,
            error         = error,
        )


@dataclass(frozen=True)
class CapabilityTimeoutEvent(CapabilityEvent):
    capability_id: str
    principal_id:  str

    @classmethod
    def create(cls, source: str, capability_id: str,
               principal_id: str) -> "CapabilityTimeoutEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CapabilityEventType.CAPABILITY_TIMEOUT,
            source        = source,
            occurred_at   = time.time(),
            capability_id = capability_id,
            principal_id  = principal_id,
        )


# ── Connector events ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ConnectorRegisteredEvent(CapabilityEvent):
    connector_id:   str
    connector_name: str

    @classmethod
    def create(cls, source: str, connector_id: str,
               connector_name: str) -> "ConnectorRegisteredEvent":
        return cls(
            event_id        = str(uuid.uuid4()),
            event_type      = CapabilityEventType.CONNECTOR_REGISTERED,
            source          = source,
            occurred_at     = time.time(),
            connector_id    = connector_id,
            connector_name  = connector_name,
        )


@dataclass(frozen=True)
class ConnectorInvokedEvent(CapabilityEvent):
    connector_id: str
    method:       str

    @classmethod
    def create(cls, source: str, connector_id: str,
               method: str) -> "ConnectorInvokedEvent":
        return cls(
            event_id     = str(uuid.uuid4()),
            event_type   = CapabilityEventType.CONNECTOR_INVOKED,
            source       = source,
            occurred_at  = time.time(),
            connector_id = connector_id,
            method       = method,
        )


# ── Skill events ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SkillRegisteredEvent(CapabilityEvent):
    skill_id:   str
    skill_name: str

    @classmethod
    def create(cls, source: str, skill_id: str,
               skill_name: str) -> "SkillRegisteredEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CapabilityEventType.SKILL_REGISTERED,
            source      = source,
            occurred_at = time.time(),
            skill_id    = skill_id,
            skill_name  = skill_name,
        )


@dataclass(frozen=True)
class SkillExecutedEvent(CapabilityEvent):
    skill_id:    str
    duration_ms: float

    @classmethod
    def create(cls, source: str, skill_id: str,
               duration_ms: float = 0.0) -> "SkillExecutedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CapabilityEventType.SKILL_EXECUTED,
            source      = source,
            occurred_at = time.time(),
            skill_id    = skill_id,
            duration_ms = duration_ms,
        )


# ── Authorization events ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuthorizationGrantedEvent(CapabilityEvent):
    principal_id:  str
    capability_id: str

    @classmethod
    def create(cls, source: str, principal_id: str,
               capability_id: str) -> "AuthorizationGrantedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CapabilityEventType.AUTHORIZATION_GRANTED,
            source        = source,
            occurred_at   = time.time(),
            principal_id  = principal_id,
            capability_id = capability_id,
        )


@dataclass(frozen=True)
class AuthorizationDeniedEvent(CapabilityEvent):
    principal_id:  str
    capability_id: str
    reason:        str

    @classmethod
    def create(cls, source: str, principal_id: str,
               capability_id: str, reason: str = "") -> "AuthorizationDeniedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CapabilityEventType.AUTHORIZATION_DENIED,
            source        = source,
            occurred_at   = time.time(),
            principal_id  = principal_id,
            capability_id = capability_id,
            reason        = reason,
        )


# ── Quota / rate events ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class QuotaExceededEvent(CapabilityEvent):
    principal_id:  str
    capability_id: str
    quota_type:    str   # "hourly" or "daily"

    @classmethod
    def create(cls, source: str, principal_id: str,
               capability_id: str, quota_type: str = "hourly") -> "QuotaExceededEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CapabilityEventType.QUOTA_EXCEEDED,
            source        = source,
            occurred_at   = time.time(),
            principal_id  = principal_id,
            capability_id = capability_id,
            quota_type    = quota_type,
        )


# ── Policy events ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PolicyAddedEvent(CapabilityEvent):
    policy_id:   str
    policy_name: str

    @classmethod
    def create(cls, source: str, policy_id: str,
               policy_name: str) -> "PolicyAddedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CapabilityEventType.POLICY_ADDED,
            source      = source,
            occurred_at = time.time(),
            policy_id   = policy_id,
            policy_name = policy_name,
        )


@dataclass(frozen=True)
class PolicyRemovedEvent(CapabilityEvent):
    policy_id: str

    @classmethod
    def create(cls, source: str, policy_id: str) -> "PolicyRemovedEvent":
        return cls(
            event_id   = str(uuid.uuid4()),
            event_type = CapabilityEventType.POLICY_REMOVED,
            source     = source,
            occurred_at = time.time(),
            policy_id  = policy_id,
        )

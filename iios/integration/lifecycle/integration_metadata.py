"""
integration_metadata.py — iios.integration.lifecycle
------------------------------------------------------
IntegrationMetadata — operational and protocol metadata for a session.

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_VERSION,
    IntegrationScope,
    IntegrationType,
)


@dataclass(frozen=True)
class IntegrationMetadata:
    """
    Immutable metadata describing the characteristics of an integration session.

    Records what type of integration is being performed, at what scope,
    with which provider and protocol.
    """
    integration_type:    IntegrationType
    integration_scope:   IntegrationScope
    provider:            str
    protocol:            str
    integration_version: str
    tags:                tuple   # Tuple[str]
    custom:              Dict[str, Any]

    @classmethod
    def create(
        cls,
        integration_type:  IntegrationType  = IntegrationType.INTERNAL,
        integration_scope: IntegrationScope = IntegrationScope.SUBSYSTEM,
        *,
        provider:            str = "iios",
        protocol:            str = "internal",
        integration_version: str = DEFAULT_VERSION,
        tags:                Optional[List[str]] = None,
        custom:              Optional[Dict[str, Any]] = None,
    ) -> "IntegrationMetadata":
        return cls(
            integration_type    = integration_type,
            integration_scope   = integration_scope,
            provider            = provider,
            protocol            = protocol,
            integration_version = integration_version,
            tags                = tuple(tags or []),
            custom              = dict(custom or {}),
        )

    @classmethod
    def default(cls) -> "IntegrationMetadata":
        return cls.create()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_type":    self.integration_type.value,
            "integration_scope":   self.integration_scope.value,
            "provider":            self.provider,
            "protocol":            self.protocol,
            "integration_version": self.integration_version,
            "tags":                list(self.tags),
            "custom":              self.custom,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IntegrationMetadata":
        return cls(
            integration_type    = IntegrationType(
                d.get("integration_type", IntegrationType.INTERNAL.value)
            ),
            integration_scope   = IntegrationScope(
                d.get("integration_scope", IntegrationScope.SUBSYSTEM.value)
            ),
            provider            = d.get("provider", "iios"),
            protocol            = d.get("protocol", "internal"),
            integration_version = d.get("integration_version", DEFAULT_VERSION),
            tags                = tuple(d.get("tags", [])),
            custom              = d.get("custom", {}),
        )

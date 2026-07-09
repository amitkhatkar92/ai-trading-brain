"""iios/execution/brokers/models/broker_metadata.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.broker_constants import (
    AuthMethod,
    BrokerCapabilityType,
    BrokerEnvironment,
    BrokerRegion,
)


@dataclass
class BrokerMetadata:
    """Immutable registration record for a broker adapter plugin."""

    broker_id:   str                          = ""
    name:        str                          = ""
    vendor:      str                          = ""
    version:     str                          = "1.0.0"
    description: str                          = ""
    website:     str                          = ""
    region:      BrokerRegion                 = BrokerRegion.UNKNOWN
    environment: BrokerEnvironment            = BrokerEnvironment.PAPER
    auth_method: AuthMethod                   = AuthMethod.API_KEY
    capabilities: list[BrokerCapabilityType]  = field(default_factory=list)
    is_active:   bool                         = True
    registered_at: float                      = field(default_factory=time.time)
    metadata:    dict[str, Any]               = field(default_factory=dict)
    metadata_id: str                          = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata_id":   self.metadata_id,
            "broker_id":     self.broker_id,
            "name":          self.name,
            "vendor":        self.vendor,
            "version":       self.version,
            "description":   self.description,
            "website":       self.website,
            "region":        self.region.value,
            "environment":   self.environment.value,
            "auth_method":   self.auth_method.value,
            "capabilities":  [c.value for c in self.capabilities],
            "is_active":     self.is_active,
            "registered_at": self.registered_at,
            "metadata":      self.metadata,
        }

"""iios/integration/providers/provider_metadata.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from iios.integration.integration_constants import ProviderPriority, ProviderStatus


@dataclass
class ProviderMetadata:
    """
    Administrative metadata about a registered provider.

    Updated throughout the provider lifecycle.
    """

    provider_id:    str             = ""
    display_name:   str             = ""
    description:    str             = ""
    version:        str             = "1.0.0"
    vendor:         str             = ""
    priority:       ProviderPriority = ProviderPriority.NORMAL
    status:         ProviderStatus   = ProviderStatus.INACTIVE
    registered_at:  float           = field(default_factory=time.time)
    activated_at:   float | None    = None
    last_fetch_at:  float | None    = None
    last_error_at:  float | None    = None
    last_error:     str | None      = None
    fetch_count:    int             = 0
    error_count:    int             = 0
    tags:           list[str]       = field(default_factory=list)
    metadata:       dict[str, Any]  = field(default_factory=dict)

    def mark_fetched(self) -> None:
        self.last_fetch_at = time.time()
        self.fetch_count  += 1

    def mark_error(self, error: str) -> None:
        self.last_error_at = time.time()
        self.last_error    = error
        self.error_count  += 1

    def error_rate(self) -> float:
        total = self.fetch_count + self.error_count
        return self.error_count / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id":   self.provider_id,
            "display_name":  self.display_name,
            "description":   self.description,
            "version":       self.version,
            "vendor":        self.vendor,
            "priority":      self.priority.value,
            "status":        self.status.value,
            "registered_at": self.registered_at,
            "activated_at":  self.activated_at,
            "last_fetch_at": self.last_fetch_at,
            "last_error":    self.last_error,
            "fetch_count":   self.fetch_count,
            "error_count":   self.error_count,
            "error_rate":    round(self.error_rate(), 4),
            "tags":          self.tags,
        }

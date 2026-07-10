"""reproducibility/configuration_snapshot.py — Configuration state capture."""
from __future__ import annotations

import copy
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ConfigurationSnapshot:
    """
    Immutable snapshot of a configuration dict at a point in time.

    The ``checksum`` field (SHA-256 of the canonical JSON representation)
    can be compared across runs to detect configuration drift.
    """
    snapshot_id: str
    entity_id:   str
    version:     str
    config:      dict[str, Any]
    checksum:    str
    captured_at: float
    captured_by: Optional[str]

    @classmethod
    def capture(
        cls,
        entity_id: str,
        config:    dict[str, Any],
        *,
        version:     str           = "1.0.0",
        snapshot_id: Optional[str] = None,
        captured_by: Optional[str] = None,
    ) -> "ConfigurationSnapshot":
        config_copy = copy.deepcopy(config)
        canonical   = json.dumps(config_copy, sort_keys=True, default=str)
        checksum    = hashlib.sha256(canonical.encode()).hexdigest()
        return cls(
            snapshot_id = snapshot_id or f"cfg_{uuid.uuid4().hex[:10]}",
            entity_id   = entity_id,
            version     = version,
            config      = config_copy,
            checksum    = checksum,
            captured_at = time.time(),
            captured_by = captured_by,
        )

    def matches(self, other: "ConfigurationSnapshot") -> bool:
        return self.checksum == other.checksum

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "entity_id":   self.entity_id,
            "version":     self.version,
            "checksum":    self.checksum,
            "captured_at": self.captured_at,
            "captured_by": self.captured_by,
            "config":      self.config,
        }

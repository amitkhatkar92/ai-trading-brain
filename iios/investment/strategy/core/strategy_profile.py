"""iios/investment/strategy/core/strategy_profile.py
Runtime container for a strategy's definition, metadata, and lifecycle state.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import StrategyStatus
from iios.investment.strategy.core.strategy_definition import StrategyDefinition
from iios.investment.strategy.core.strategy_metadata import StrategyMetadata
from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot


@dataclass
class StrategyProfile:
    """
    Authoritative runtime record of a registered strategy.

    Holds:
    - The immutable StrategyDefinition
    - Mutable StrategyMetadata
    - Current lifecycle_status (source of truth for transitions)
    - Latest StrategySnapshot (updated after every evaluation)
    - version_history to track parameter evolution
    """

    profile_id:       str                  = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id:      str                  = ""
    definition:       StrategyDefinition   = field(default_factory=StrategyDefinition)
    meta:             StrategyMetadata     = field(default_factory=StrategyMetadata)
    lifecycle_status: StrategyStatus       = StrategyStatus.DRAFT
    latest_snapshot:  StrategySnapshot | None = None

    # Tracks version strings across parameter adaptations
    version_history:  list[str]            = field(default_factory=lambda: ["1.0.0"])

    # Mutable current parameters (may differ from definition.parameters after adaptation)
    active_params:    dict[str, Any]       = field(default_factory=dict)

    metadata:         dict[str, Any]       = field(default_factory=dict)
    created_at:       float                = field(default_factory=time.time)
    updated_at:       float                = field(default_factory=time.time)

    # ── post-init ─────────────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        # Initialise active_params from definition if empty
        if not self.active_params and self.definition.parameters:
            self.active_params = dict(self.definition.parameters)

    # ── mutation helpers ──────────────────────────────────────────────────────

    def update_snapshot(self, snapshot: StrategySnapshot) -> None:
        self.latest_snapshot = snapshot
        self.updated_at      = time.time()

    def set_status(self, status: StrategyStatus) -> None:
        self.lifecycle_status = status
        self.updated_at       = time.time()

    def update_params(self, params: dict[str, Any], new_version: str = "") -> None:
        self.active_params = dict(params)
        if new_version and new_version not in self.version_history:
            self.version_history.append(new_version)
        self.updated_at = time.time()

    @property
    def current_version(self) -> str:
        return self.version_history[-1] if self.version_history else "1.0.0"

    @property
    def is_active(self) -> bool:
        return self.lifecycle_status in (
            StrategyStatus.APPROVED,
            StrategyStatus.PRODUCTION,
        )

    @property
    def is_evaluable(self) -> bool:
        return self.lifecycle_status not in (
            StrategyStatus.ARCHIVED,
            StrategyStatus.RETIRED,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id":       self.profile_id,
            "strategy_id":      self.strategy_id,
            "definition":       self.definition.to_dict(),
            "meta":             self.meta.to_dict(),
            "lifecycle_status": self.lifecycle_status.value,
            "current_version":  self.current_version,
            "version_history":  self.version_history,
            "active_params":    self.active_params,
            "has_snapshot":     self.latest_snapshot is not None,
            "is_active":        self.is_active,
            "is_evaluable":     self.is_evaluable,
            "metadata":         self.metadata,
            "created_at":       self.created_at,
            "updated_at":       self.updated_at,
        }

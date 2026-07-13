"""iios/investment/strategy/core/base_strategy.py
Abstract base class that all IIOS-managed strategies must implement.
Concrete strategies are registered as plugins; this module defines the protocol.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from iios.investment.strategy.strategy_constants import (
    AssetClass,
    StrategyCategory,
    StrategyRiskLevel,
    StrategyStatus,
    StrategyTimeframe,
)
from iios.investment.strategy.core.strategy_definition import StrategyDefinition


class BaseStrategy(ABC):
    """
    Abstract protocol for every strategy plugged into the IIOS engine.

    Responsibilities:
    - Declare the strategy's definition (name, category, parameters …)
    - Expose current parameter state
    - Optionally provide a description

    The engine handles all evaluation, selection, adaptation, and lifecycle
    management externally — the strategy class itself must NOT execute trades.
    """

    # ── class-level identity (override in subclass) ───────────────────────────
    NAME:       str               = "BaseStrategy"
    VERSION:    str               = "1.0.0"
    CATEGORY:   StrategyCategory  = StrategyCategory.UNKNOWN
    ASSET_CLASS: AssetClass       = AssetClass.UNKNOWN
    TIMEFRAME:  StrategyTimeframe = StrategyTimeframe.UNKNOWN
    RISK_LEVEL: StrategyRiskLevel = StrategyRiskLevel.UNKNOWN

    def __init__(
        self,
        strategy_id: str = "",
        **params: Any,
    ) -> None:
        self._strategy_id = strategy_id or str(uuid.uuid4())
        self._params:      dict[str, Any] = dict(params)
        self._status:      StrategyStatus  = StrategyStatus.DRAFT
        self._version:     str             = self.VERSION

    # ── identity ──────────────────────────────────────────────────────────────

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def category(self) -> StrategyCategory:
        return self.CATEGORY

    @property
    def version(self) -> str:
        return self._version

    @property
    def status(self) -> StrategyStatus:
        return self._status

    # ── abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def get_definition(self) -> StrategyDefinition:
        """
        Return the immutable StrategyDefinition for this strategy.
        Called once at registration time.
        """

    @abstractmethod
    def get_params(self) -> dict[str, Any]:
        """Return the current parameter dict (may be updated by adapters)."""

    # ── optional overrides ────────────────────────────────────────────────────

    def description(self) -> str:
        return ""

    def validate_params(self, params: dict[str, Any]) -> bool:
        """
        Validate a candidate parameter set before applying.
        Return True if valid; raise ValueError with details if not.
        """
        return True

    def on_params_updated(self, new_params: dict[str, Any]) -> None:
        """Called by the engine when parameters are adapted."""
        self._params = dict(new_params)

    def on_status_changed(self, new_status: StrategyStatus) -> None:
        """Called by the engine on lifecycle transitions."""
        self._status = new_status

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id":  self._strategy_id,
            "name":         self.name,
            "category":     self.category.value,
            "version":      self._version,
            "status":       self._status.value,
            "params":       self._params,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id={self._strategy_id!r}, "
            f"category={self.CATEGORY.value!r}, "
            f"status={self._status.value!r})"
        )

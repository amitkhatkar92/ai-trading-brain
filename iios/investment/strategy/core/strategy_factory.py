"""iios/investment/strategy/core/strategy_factory.py
Factory that constructs InstitutionalBaseStrategy instances from the registry.

Distinct from the parent-level strategy_factory.py which works with
StrategyDefinition objects.
"""
from __future__ import annotations

import logging
from typing import Optional, Type

from .institutional_base_strategy import InstitutionalBaseStrategy
from .strategy_configuration import StrategyConfiguration
from .strategy_descriptor import StrategyDescriptor
from .strategy_registry import InstitutionalStrategyRegistry

logger = logging.getLogger(__name__)


class FactoryError(Exception):
    """Raised when an institutional strategy cannot be constructed."""


class InstitutionalStrategyFactory:
    """Creates InstitutionalBaseStrategy instances, wiring descriptor and config."""

    def __init__(self, registry: InstitutionalStrategyRegistry) -> None:
        self._registry = registry

    def create(
        self,
        strategy_id: str,
        config: Optional[StrategyConfiguration] = None,
    ) -> InstitutionalBaseStrategy:
        """
        Instantiate a strategy by ID.
        If config is provided, load() is called immediately (REGISTERED → LOADED).
        """
        cls = self._registry.get_class(strategy_id)
        if cls is None:
            raise FactoryError(
                f"Institutional strategy '{strategy_id}' not found in registry."
            )
        if not self._registry.is_enabled(strategy_id):
            raise FactoryError(
                f"Institutional strategy '{strategy_id}' is disabled."
            )
        descriptor = self._registry.get_descriptor(strategy_id)
        if descriptor is None:
            raise FactoryError(
                f"Descriptor missing for institutional strategy '{strategy_id}'."
            )

        try:
            instance = cls(descriptor)
        except Exception as exc:
            raise FactoryError(
                f"Failed to instantiate '{strategy_id}': {exc}"
            ) from exc

        if config is not None:
            instance.load(config)

        logger.debug("Created institutional strategy instance '%s'", strategy_id)
        return instance

    def build_default_config(
        self,
        strategy_id: str,
        environment: str = "paper",
    ) -> StrategyConfiguration:
        """Build an empty StrategyConfiguration for the given strategy."""
        if not self._registry.is_registered(strategy_id):
            raise FactoryError(
                f"Institutional strategy '{strategy_id}' is not registered."
            )
        return StrategyConfiguration(
            strategy_id=strategy_id,
            environment=environment,
        )

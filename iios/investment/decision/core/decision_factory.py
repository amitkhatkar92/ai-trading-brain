"""iios/investment/decision/core/decision_factory.py
DecisionFactory — creates BaseDecision instances via the registry.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from iios.investment.decision.core.decision_configuration import DecisionConfiguration
from iios.investment.decision.core.decision_context import DecisionContext
from iios.investment.decision.core.decision_events import EventDispatcher
from iios.investment.decision.core.decision_registry import DecisionRegistry, UnknownDecisionTypeError

_log = logging.getLogger(__name__)


class DecisionFactory:
    """
    Creates fully wired BaseDecision instances.
    Injects:
    - DecisionContext
    - DecisionConfiguration
    - Shared EventDispatcher (optional — if not provided, one is created per decision)
    """

    def __init__(
        self,
        registry:   DecisionRegistry,
        default_config: Optional[DecisionConfiguration] = None,
        dispatcher: Optional[EventDispatcher]           = None,
    ) -> None:
        self._registry   = registry
        self._config     = default_config or DecisionConfiguration()
        self._dispatcher = dispatcher

    def create(
        self,
        key:        str,
        context:    DecisionContext,
        config:     Optional[DecisionConfiguration] = None,
        dispatcher: Optional[EventDispatcher]       = None,
        **kwargs:   Any,
    ):
        """
        Instantiate a registered decision class.

        Extra kwargs are forwarded to the decision constructor, allowing
        subclasses to accept domain-specific dependencies.
        """
        klass = self._registry.get(key)  # raises UnknownDecisionTypeError if missing

        resolved_config     = config     or self._config
        resolved_dispatcher = dispatcher or self._dispatcher

        _log.debug(
            "Creating decision %s (%s) for subject=%s",
            context.decision_id, key, context.subject_id,
        )

        if resolved_dispatcher is not None:
            return klass(context=context, config=resolved_config, dispatcher=resolved_dispatcher, **kwargs)
        else:
            return klass(context=context, config=resolved_config, **kwargs)

    def can_create(self, key: str) -> bool:
        return self._registry.has(key)

    def supported_types(self) -> list:
        return self._registry.all_keys()

"""
iios/configuration/configuration_merger.py
============================================
Deep-merge logic for configuration dictionaries from multiple sources.

``ConfigurationMerger.merge()`` takes an ordered list of source dicts
(lowest priority first) and produces a single merged dict. For nested
dicts it recurses; for lists it follows a configurable strategy.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
"""

from __future__ import annotations

import copy
import logging
from enum import Enum
from typing import Any

from .configuration_exception import ConfigurationMergeError

logger = logging.getLogger(__name__)

__all__ = [
    "ArrayMergeStrategy",
    "ConfigurationMerger",
]


class ArrayMergeStrategy(str, Enum):
    """How list values are merged when both source and override have a list."""

    REPLACE = "replace"   # Override completely replaces base (default)
    APPEND  = "append"    # Override items appended after base items
    PREPEND = "prepend"   # Override items prepended before base items
    UNIQUE  = "unique"    # Merge both lists; deduplicate (order: base then override)


class ConfigurationMerger:
    """Merges configuration dicts from multiple sources.

    Instances are stateless and thread-safe — call ``merge()`` freely.

    Args:
        array_strategy: How to handle list values. Default is ``REPLACE``
            (the override wins), which matches most CLI / env-var semantics.
    """

    def __init__(
        self,
        array_strategy: ArrayMergeStrategy = ArrayMergeStrategy.REPLACE,
    ) -> None:
        self._array_strategy = array_strategy

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def merge(self, sources: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge *sources* in order — later sources override earlier ones.

        Each source is a ``dict[str, Any]`` that may contain nested dicts.
        The result is a deep copy — input dicts are never mutated.

        Args:
            sources: Ordered list, lowest priority first.

        Returns:
            Single merged dict.
        """
        result: dict[str, Any] = {}
        for i, source in enumerate(sources):
            if not isinstance(source, dict):
                raise ConfigurationMergeError(
                    f"Source at index {i} is not a dict (got {type(source).__name__})"
                )
            result = self._deep_merge(result, source)
        return result

    def merge_two(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Merge two dicts — ``override`` wins on conflict."""
        return self._deep_merge(copy.deepcopy(base), override)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _deep_merge(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """Recursively merge *override* into *base* (mutates *base* in place)."""
        for key, override_value in override.items():
            if key not in base:
                # Key absent in base — take override value (deep copy for safety)
                base[key] = copy.deepcopy(override_value)
                continue

            base_value = base[key]

            if isinstance(base_value, dict) and isinstance(override_value, dict):
                # Both are dicts → recurse
                self._deep_merge(base_value, override_value)
            elif isinstance(base_value, list) and isinstance(override_value, list):
                base[key] = self._merge_lists(base_value, override_value)
            else:
                # Scalar or type mismatch → override wins
                base[key] = copy.deepcopy(override_value)

        return base

    def _merge_lists(
        self,
        base: list[Any],
        override: list[Any],
    ) -> list[Any]:
        strategy = self._array_strategy

        if strategy is ArrayMergeStrategy.REPLACE:
            return copy.deepcopy(override)
        if strategy is ArrayMergeStrategy.APPEND:
            return copy.deepcopy(base) + copy.deepcopy(override)
        if strategy is ArrayMergeStrategy.PREPEND:
            return copy.deepcopy(override) + copy.deepcopy(base)
        if strategy is ArrayMergeStrategy.UNIQUE:
            seen: set[Any] = set()
            result: list[Any] = []
            for item in list(base) + list(override):
                try:
                    hashable = item
                    if item not in seen:
                        seen.add(hashable)
                        result.append(copy.deepcopy(item))
                except TypeError:
                    # Unhashable type (e.g. list) — just append
                    result.append(copy.deepcopy(item))
            return result

        # Fallback
        return copy.deepcopy(override)

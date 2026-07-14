"""iios/investment/decision/core/decision_loader.py
DecisionLoader — dynamically discovers and loads BaseDecision subclasses.
"""
from __future__ import annotations

import importlib
import inspect
import logging
from typing import Any, Dict, List, Optional, Type

from iios.investment.decision.core.decision_registry import DecisionRegistry

_log = logging.getLogger(__name__)


class DecisionLoader:
    """
    Discovers and loads BaseDecision subclasses from Python module paths.

    Usage:
        loader = DecisionLoader(registry)
        loader.load_from_module("iios.investment.decision.strategies.momentum")
        loader.load_from_class_path(
            "iios.investment.decision.strategies.mean_reversion.MeanReversionDecision",
            key="mean_reversion"
        )
    """

    def __init__(self, registry: DecisionRegistry) -> None:
        self._registry = registry
        self._loaded:  List[str] = []

    def load_from_class_path(
        self,
        class_path:   str,
        key:          str,
        version:      str   = "1.0.0",
        capabilities: tuple = (),
        overwrite:    bool  = False,
    ) -> bool:
        """
        Load a class from a dotted path like 'my.module.MyDecision'.
        Returns True on success, False on error.
        """
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            klass  = getattr(module, class_name)
            if not inspect.isclass(klass):
                _log.warning("'%s' is not a class — skipping.", class_path)
                return False
            self._registry.register(key, klass, version, capabilities, overwrite)
            self._loaded.append(class_path)
            _log.info("Loaded decision class %r as key=%r", class_path, key)
            return True
        except (ImportError, AttributeError, ValueError) as exc:
            _log.warning("Failed to load class %r: %s", class_path, exc)
            return False

    def load_from_module(
        self,
        module_path:  str,
        base_class:   Optional[Type] = None,
        version:      str   = "1.0.0",
        capabilities: tuple = (),
        overwrite:    bool  = False,
    ) -> int:
        """
        Scan a module for BaseDecision subclasses and register them all.
        Returns number of classes registered.
        """
        from iios.investment.decision.core.base_decision import BaseDecision
        base = base_class or BaseDecision
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            _log.warning("Cannot import module %r: %s", module_path, exc)
            return 0

        count = 0
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, base) and obj is not base and not inspect.isabstract(obj):
                key = getattr(obj, "DECISION_KEY", name.lower())
                try:
                    self._registry.register(key, obj, version, capabilities, overwrite)
                    self._loaded.append(f"{module_path}.{name}")
                    count += 1
                    _log.info("Auto-loaded %s as key=%r", name, key)
                except Exception as exc:
                    _log.warning("Skipping %s: %s", name, exc)

        return count

    @property
    def loaded(self) -> List[str]:
        return list(self._loaded)

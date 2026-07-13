"""iios/investment/strategy/core/strategy_loader.py
Dynamic strategy loader — plugin system for institutional strategies.
Loads InstitutionalBaseStrategy subclasses from modules or .py files.
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import List, Type

from .institutional_base_strategy import InstitutionalBaseStrategy
from .strategy_descriptor import StrategyDescriptor
from .strategy_registry import InstitutionalStrategyRegistry, RegistrationError

logger = logging.getLogger(__name__)


class LoaderError(Exception):
    """Raised when a module cannot be loaded or has no valid strategies."""


class StrategyLoader:
    """
    Loads institutional strategy classes from:
    - Python module paths (dotted: 'iios.strategies.momentum')
    - File system paths (.py files)
    - Class references directly

    Discovery convention: each strategy module must expose:
      STRATEGY_CLASS    → InstitutionalBaseStrategy subclass
      STRATEGY_DESCRIPTOR → StrategyDescriptor instance
    """

    STRATEGY_CLASS_ATTR      = "STRATEGY_CLASS"
    STRATEGY_DESCRIPTOR_ATTR = "STRATEGY_DESCRIPTOR"

    def __init__(self, registry: InstitutionalStrategyRegistry) -> None:
        self._registry = registry

    def load_from_module(self, module_path: str, replace: bool = False) -> str:
        """Load a strategy from a dotted module path. Returns registered strategy_id."""
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise LoaderError(
                f"Cannot import module '{module_path}': {exc}"
            ) from exc
        return self._load_from_module_object(module, module_path, replace=replace)

    def load_from_file(self, file_path: str, replace: bool = False) -> str:
        """Load a strategy from a .py file path. Returns registered strategy_id."""
        path = Path(file_path)
        if not path.exists():
            raise LoaderError(f"File not found: {file_path}")

        module_name = f"_iios_plugin_{path.stem}_{id(path)}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise LoaderError(
                f"Cannot create module spec from '{file_path}'."
            )

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
        except Exception as exc:
            raise LoaderError(
                f"Error executing '{file_path}': {exc}"
            ) from exc

        sys.modules[module_name] = module
        return self._load_from_module_object(module, file_path, replace=replace)

    def load_direct(
        self,
        strategy_class: Type[InstitutionalBaseStrategy],
        descriptor: StrategyDescriptor,
        replace: bool = False,
    ) -> str:
        """Register a class+descriptor directly. Returns the strategy_id."""
        try:
            self._registry.register(strategy_class, descriptor, replace=replace)
        except RegistrationError as exc:
            raise LoaderError(str(exc)) from exc
        return descriptor.strategy_id

    def load_directory(self, directory: str, replace: bool = False) -> List[str]:
        """Scan a directory for .py files and load each. Returns loaded strategy_ids."""
        base = Path(directory)
        if not base.is_dir():
            raise LoaderError(f"Not a directory: {directory}")

        loaded: List[str] = []
        for py_file in sorted(base.glob("*.py")):
            if py_file.stem.startswith("_"):
                continue
            try:
                sid = self.load_from_file(str(py_file), replace=replace)
                loaded.append(sid)
                logger.info(
                    "Loaded strategy '%s' from '%s'", sid, py_file.name
                )
            except LoaderError as exc:
                logger.warning("Skipping '%s': %s", py_file.name, exc)
        return loaded

    def _load_from_module_object(
        self, module: object, source: str, replace: bool
    ) -> str:
        cls = getattr(module, self.STRATEGY_CLASS_ATTR, None)
        desc = getattr(module, self.STRATEGY_DESCRIPTOR_ATTR, None)

        if cls is None or desc is None:
            raise LoaderError(
                f"Module '{source}' must expose "
                f"'{self.STRATEGY_CLASS_ATTR}' and "
                f"'{self.STRATEGY_DESCRIPTOR_ATTR}'."
            )
        if not (
            inspect.isclass(cls)
            and issubclass(cls, InstitutionalBaseStrategy)
        ):
            raise LoaderError(
                f"'{self.STRATEGY_CLASS_ATTR}' in '{source}' "
                f"must be an InstitutionalBaseStrategy subclass."
            )
        if not isinstance(desc, StrategyDescriptor):
            raise LoaderError(
                f"'{self.STRATEGY_DESCRIPTOR_ATTR}' in '{source}' "
                f"must be a StrategyDescriptor instance."
            )

        try:
            self._registry.register(cls, desc, replace=replace)
        except RegistrationError as exc:
            raise LoaderError(str(exc)) from exc
        return desc.strategy_id

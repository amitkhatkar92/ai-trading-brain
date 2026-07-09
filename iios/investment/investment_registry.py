"""iios/investment/investment_registry.py
Master registry: workflows, asset classes, domain engines.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.investment.investment_constants import (
    AssetClass,
    IntelligenceType,
    MAX_REGISTRY_SIZE,
)
from iios.investment.investment_exceptions import (
    AssetClassNotSupportedError,
    DomainEngineAlreadyRegisteredError,
    DomainEngineNotFoundError,
    RegistryItemAlreadyExistsError,
    RegistryItemNotFoundError,
    RegistryOverflowError,
)
from iios.investment.workflow.investment_workflow import InvestmentWorkflow


class InvestmentRegistry:
    """
    Thread-safe master registry for the Investment Intelligence Engine.

    Three registries in one:
    1. Workflow registry — InvestmentWorkflow instances by workflow_id
    2. Asset class registry — tracks which asset classes are supported
    3. Domain engine registry — pluggable domain engines by IntelligenceType
    """

    def __init__(self, max_size: int = MAX_REGISTRY_SIZE) -> None:
        self._lock:    threading.RLock                      = threading.RLock()
        self._workflows: dict[str, InvestmentWorkflow]      = {}
        self._asset_classes: dict[str, dict]                = {}  # AssetClass.value → info
        self._domain_engines: dict[str, Any]                = {}  # IntelligenceType.value → engine
        self._max:     int                                  = max_size

    # ── workflows ─────────────────────────────────────────────────────────────

    def register_workflow(
        self,
        workflow: InvestmentWorkflow,
        *,
        overwrite: bool = False,
    ) -> None:
        with self._lock:
            if workflow.workflow_id in self._workflows and not overwrite:
                raise RegistryItemAlreadyExistsError(workflow.workflow_id)
            if workflow.workflow_id not in self._workflows and len(self._workflows) >= self._max:
                raise RegistryOverflowError(self._max)
            self._workflows[workflow.workflow_id] = workflow

    def get_workflow(self, workflow_id: str) -> InvestmentWorkflow:
        with self._lock:
            w = self._workflows.get(workflow_id)
        if w is None:
            raise RegistryItemNotFoundError(workflow_id)
        return w

    def has_workflow(self, workflow_id: str) -> bool:
        with self._lock:
            return workflow_id in self._workflows

    def all_workflows(self) -> list[InvestmentWorkflow]:
        with self._lock:
            return list(self._workflows.values())

    def workflows_for(self, intelligence_type: IntelligenceType) -> list[InvestmentWorkflow]:
        with self._lock:
            return [
                w for w in self._workflows.values()
                if w.intelligence_type == intelligence_type
            ]

    # ── asset classes ─────────────────────────────────────────────────────────

    def register_asset_class(
        self,
        asset_class: AssetClass,
        handler: Any = None,
        metadata: dict | None = None,
    ) -> None:
        with self._lock:
            self._asset_classes[asset_class.value] = {
                "asset_class": asset_class,
                "handler":     handler,
                "metadata":    metadata or {},
            }

    def is_supported(self, asset_class: AssetClass) -> bool:
        with self._lock:
            return asset_class.value in self._asset_classes

    def supported_asset_classes(self) -> list[AssetClass]:
        with self._lock:
            return [info["asset_class"] for info in self._asset_classes.values()]

    def get_asset_class_info(self, asset_class: AssetClass) -> dict:
        with self._lock:
            info = self._asset_classes.get(asset_class.value)
        if info is None:
            raise AssetClassNotSupportedError(asset_class.value)
        return info

    # ── domain engines ────────────────────────────────────────────────────────

    def register_domain_engine(
        self,
        intelligence_type: IntelligenceType,
        engine: Any,
        *,
        overwrite: bool = False,
    ) -> None:
        with self._lock:
            key = intelligence_type.value
            if key in self._domain_engines and not overwrite:
                raise DomainEngineAlreadyRegisteredError(key)
            self._domain_engines[key] = engine

    def get_domain_engine(self, intelligence_type: IntelligenceType) -> Any:
        with self._lock:
            engine = self._domain_engines.get(intelligence_type.value)
        if engine is None:
            raise DomainEngineNotFoundError(intelligence_type.value)
        return engine

    def has_domain_engine(self, intelligence_type: IntelligenceType) -> bool:
        with self._lock:
            return intelligence_type.value in self._domain_engines

    def all_domain_engines(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._domain_engines)

    # ── stats ─────────────────────────────────────────────────────────────────

    def statistics(self) -> dict:
        with self._lock:
            return {
                "workflows":       len(self._workflows),
                "asset_classes":   len(self._asset_classes),
                "domain_engines":  len(self._domain_engines),
            }


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock          = threading.Lock()
_instance:       InvestmentRegistry | None = None


def get_investment_registry() -> InvestmentRegistry:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = _build_default_registry()
    return _instance


def reset_investment_registry() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        _instance = None


def _build_default_registry() -> InvestmentRegistry:
    """Bootstrap registry with all standard asset classes pre-registered."""
    reg = InvestmentRegistry()
    for ac in AssetClass:
        reg.register_asset_class(ac)
    return reg

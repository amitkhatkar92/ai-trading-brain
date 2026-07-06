"""
iios/infrastructure/dependency_injection/__init__.py
"""

from __future__ import annotations

from .container import Container, get_container, reset_container
from .service_registry import ServiceRegistry
from .service_locator import ServiceLocator, get_service
from .dependency_graph import DependencyGraph
from .lifecycle_scope import LifecycleScope, ScopeContext, current_scope
from .provider import (
    Provider,
    SingletonProvider,
    TransientProvider,
    FactoryProvider,
    InstanceProvider,
    LazyProvider,
)
from .factory import ServiceFactory, AbstractFactory, ConcreteFactory, FactoryRegistry
from .singleton import SingletonMeta, Singleton, singleton_registry, clear_singleton_registry

__all__ = [
    "Container", "get_container", "reset_container",
    "ServiceRegistry",
    "ServiceLocator", "get_service",
    "DependencyGraph",
    "LifecycleScope", "ScopeContext", "current_scope",
    "Provider", "SingletonProvider", "TransientProvider",
    "FactoryProvider", "InstanceProvider", "LazyProvider",
    "ServiceFactory", "AbstractFactory", "ConcreteFactory", "FactoryRegistry",
    "SingletonMeta", "Singleton", "singleton_registry", "clear_singleton_registry",
]

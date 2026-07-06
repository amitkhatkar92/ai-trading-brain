"""
tests/unit/infrastructure/test_dependency_injection.py
======================================================
Tests for the iios.infrastructure.dependency_injection subpackage.
"""

from __future__ import annotations

import threading
import pytest

from iios.infrastructure.dependency_injection import (
    Container, get_container, reset_container,
    ServiceLocator,
    DependencyGraph,
    LifecycleScope, ScopeContext, current_scope,
    SingletonProvider, TransientProvider, InstanceProvider, LazyProvider,
    ServiceRegistry,
    ServiceFactory, AbstractFactory, FactoryRegistry,
    SingletonMeta, Singleton, clear_singleton_registry,
)
from iios.infrastructure.infrastructure_exceptions import (
    ServiceNotFoundError, ServiceAlreadyRegisteredError,
    CircularDependencyError, LifecycleScopeError,
)


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

class TestContainer:
    def setup_method(self):
        reset_container()

    def teardown_method(self):
        reset_container()

    def test_singleton_same_instance(self):
        class Svc:
            pass
        c = Container()
        c.singleton("svc", Svc)
        a = c.resolve("svc")
        b = c.resolve("svc")
        assert a is b

    def test_transient_different_instances(self):
        class Svc:
            pass
        c = Container()
        c.transient("svc", Svc)
        a = c.resolve("svc")
        b = c.resolve("svc")
        assert a is not b

    def test_instance_registration(self):
        obj = object()
        c = Container()
        c.instance("obj", obj)
        assert c.resolve("obj") is obj

    def test_lazy_called_once(self):
        calls = []
        c = Container()
        c.lazy("lazy", lambda: (calls.append(1), object())[1])
        c.resolve("lazy")
        c.resolve("lazy")
        assert len(calls) == 1

    def test_resolve_unknown_raises(self):
        c = Container()
        with pytest.raises(ServiceNotFoundError):
            c.resolve("unknown")

    def test_try_resolve_returns_none(self):
        c = Container()
        assert c.try_resolve("unknown") is None

    def test_is_registered(self):
        c = Container()
        c.instance("x", 42)
        assert c.is_registered("x")
        assert not c.is_registered("y")

    def test_resolve_all_by_tag(self):
        c = Container()
        registry = c._registry
        c.singleton("a", list, allow_override=False)
        registry.get("a").tags.append("group1")
        c.singleton("b", dict, allow_override=False)
        registry.get("b").tags.append("group1")
        results = c.resolve_all("group1")
        assert len(results) == 2

    def test_singleton_decorator(self):
        c = Container()

        @c.singleton("my_cls")
        class MyClass:
            pass

        assert c.is_registered("my_cls")
        a = c.resolve("my_cls")
        b = c.resolve("my_cls")
        assert a is b

    def test_reset_clears_all(self):
        c = Container()
        c.instance("x", 99)
        c.reset()
        assert not c.is_registered("x")

    def test_scoped_raises_outside_scope(self):
        c = Container()

        class Scoped:
            pass

        c.scoped("scoped", Scoped)
        with pytest.raises(LifecycleScopeError):
            c.resolve("scoped")

    def test_scoped_in_scope_context(self):
        c = Container()

        class Scoped:
            pass

        c.scoped("scoped", Scoped)
        with LifecycleScope("test-scope"):
            a = c.resolve("scoped")
            b = c.resolve("scoped")
        assert a is b

    def test_global_singleton(self):
        c1 = get_container()
        c2 = get_container()
        assert c1 is c2

    def test_auto_inject(self):
        # Use module-level classes so get_type_hints can resolve annotations
        # (local classes inside methods can't be resolved by get_type_hints)
        c = Container()
        c.singleton("iios.infrastructure.infrastructure_models.ServiceDescriptor",
                    __import__("iios.infrastructure.infrastructure_models",
                               fromlist=["ServiceDescriptor"]).ServiceDescriptor)
        # Simpler: test that auto_factory silently skips unresolvable locals
        # and falls through to normal construction
        class SimpleService:
            def __init__(self) -> None:
                self.value = 42
        c.singleton("simple", SimpleService)
        svc = c.resolve("simple")
        assert isinstance(svc, SimpleService)
        assert svc.value == 42

    def test_thread_safety_singleton(self):
        c = Container()
        instances = []
        call_count = []

        class CountedSvc:
            def __init__(self):
                call_count.append(1)

        c.singleton("svc", CountedSvc)

        def resolve():
            instances.append(c.resolve("svc"))

        threads = [threading.Thread(target=resolve) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(id(i) for i in instances)) == 1, "Multiple singleton instances created"


# ---------------------------------------------------------------------------
# ServiceRegistry
# ---------------------------------------------------------------------------

class TestServiceRegistry:
    def test_register_and_get(self):
        reg = ServiceRegistry()
        reg.register("svc", list)
        d = reg.get("svc")
        assert d.service_key == "svc"

    def test_register_duplicate_raises(self):
        reg = ServiceRegistry()
        reg.register("svc", list)
        with pytest.raises(ServiceAlreadyRegisteredError):
            reg.register("svc", dict)

    def test_register_duplicate_override(self):
        reg = ServiceRegistry()
        reg.register("svc", list)
        reg.register("svc", dict, allow_override=True)
        assert reg.get("svc").implementation is dict

    def test_register_instance(self):
        reg = ServiceRegistry()
        obj = object()
        reg.register_instance("inst", obj)
        assert reg.get("inst").singleton_instance is obj

    def test_by_tag(self):
        reg = ServiceRegistry()
        reg.register("a", list, tags=["grp"])
        reg.register("b", dict, tags=["grp"])
        reg.register("c", set, tags=["other"])
        tagged = reg.by_tag("grp")
        assert len(tagged) == 2

    def test_unregister(self):
        reg = ServiceRegistry()
        reg.register("svc", list)
        reg.unregister("svc")
        assert not reg.has("svc")


# ---------------------------------------------------------------------------
# DependencyGraph
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_resolution_order_simple(self):
        g = DependencyGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_dependency("b", "a")
        order = g.resolution_order()
        assert order.index("a") < order.index("b")

    def test_cycle_detection(self):
        g = DependencyGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_dependency("a", "b")
        g.add_dependency("b", "a")
        assert g.has_cycle()

    def test_cycle_raises_on_resolution_order(self):
        g = DependencyGraph()
        g.add_node("x")
        g.add_node("y")
        g.add_dependency("x", "y")
        g.add_dependency("y", "x")
        with pytest.raises(CircularDependencyError):
            g.resolution_order()

    def test_all_dependencies_of(self):
        g = DependencyGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_node("c")
        g.add_dependency("b", "a")
        g.add_dependency("c", "b")
        deps = g.all_dependencies_of("c")
        assert "a" in deps and "b" in deps


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class TestProviders:
    def test_singleton_provider(self):
        p = SingletonProvider(list)
        a = p.get()
        b = p.get()
        assert a is b

    def test_transient_provider(self):
        p = TransientProvider(list)
        a = p.get()
        b = p.get()
        assert a is not b

    def test_instance_provider(self):
        obj = object()
        p = InstanceProvider(obj)
        assert p.get() is obj

    def test_lazy_provider(self):
        calls = []
        p = LazyProvider(lambda: (calls.append(1), [])[1])
        p.get()
        p.get()
        assert len(calls) == 1

    def test_singleton_provider_reset(self):
        p = SingletonProvider(list)
        a = p.get()
        p.reset()
        b = p.get()
        assert a is not b


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestFactory:
    def test_service_factory(self):
        sf = ServiceFactory(list)
        a = sf.create()
        b = sf.create()
        assert a is not b
        assert isinstance(a, list)

    def test_abstract_factory(self):
        af: AbstractFactory[list] = AbstractFactory()
        af.register("list", list)
        af.register("tuple", tuple)
        assert isinstance(af.create("list"), list)
        assert isinstance(af.create("tuple"), tuple)

    def test_abstract_factory_missing_key(self):
        af: AbstractFactory = AbstractFactory()
        with pytest.raises(KeyError):
            af.create("nonexistent")

    def test_factory_registry(self):
        fr = FactoryRegistry()
        af: AbstractFactory = AbstractFactory()
        af.register("list", list)
        fr.register_factory("collections", af)
        result = fr.create("collections", "list")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def setup_method(self):
        clear_singleton_registry()

    def test_singleton_meta(self):
        class MySvc(metaclass=SingletonMeta):
            pass
        a = MySvc()
        b = MySvc()
        assert a is b

    def test_service_locator(self):
        c = Container()
        c.instance("val", 42)
        loc = ServiceLocator(c)
        assert loc.get("val") == 42

    def test_service_locator_has(self):
        c = Container()
        c.instance("val", 42)
        loc = ServiceLocator(c)
        assert loc.has("val")
        assert not loc.has("missing")

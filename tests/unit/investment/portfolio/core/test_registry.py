"""tests/unit/investment/portfolio/core/test_registry.py

Tests for PortfolioClassRegistry, PortfolioCatalog, PortfolioLoader,
and PortfolioFactory.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.core.portfolio_catalog import CatalogEntry, PortfolioCatalog
from iios.investment.portfolio.core.portfolio_factory import PortfolioFactory, FactoryResult
from iios.investment.portfolio.core.portfolio_loader import PortfolioLoader
from iios.investment.portfolio.core.portfolio_registry import (
    PortfolioClassNotFoundError,
    PortfolioClassRegistrationError,
    PortfolioClassRegistry,
)
from iios.investment.portfolio.core.portfolio_types import (
    PortfolioCapability,
    PortfolioDomain,
)


class TestPortfolioClassRegistry:
    def test_register_and_lookup(self, class_registry):
        # class_registry fixture registers _MinimalPortfolio
        assert class_registry.is_registered("_MinimalPortfolio")

    def test_get_class(self, class_registry):
        cls = class_registry.get_class("_MinimalPortfolio")
        assert cls is not None

    def test_get_class_not_found(self, class_registry):
        with pytest.raises(PortfolioClassNotFoundError):
            class_registry.get_class("NonExistent")

    def test_duplicate_raises(self, class_registry):
        from tests.unit.investment.portfolio.core.conftest import _MinimalPortfolio
        with pytest.raises(PortfolioClassRegistrationError):
            class_registry.register(_MinimalPortfolio, domain=PortfolioDomain.SWING)

    def test_overwrite_allowed(self, class_registry):
        from tests.unit.investment.portfolio.core.conftest import _MinimalPortfolio
        entry = class_registry.register(
            _MinimalPortfolio, domain=PortfolioDomain.SWING, version="2.0.0",
            overwrite=True
        )
        assert entry.version == "2.0.0"

    def test_all_class_names(self, class_registry):
        names = class_registry.all_class_names()
        assert "_MinimalPortfolio" in names

    def test_by_domain(self, class_registry):
        entries = class_registry.by_domain(PortfolioDomain.SWING)
        assert any(e.class_name == "_MinimalPortfolio" for e in entries)

    def test_by_capability(self, class_registry):
        from tests.unit.investment.portfolio.core.conftest import _MinimalPortfolio
        class_registry.register(
            _MinimalPortfolio,
            class_name="CapPortfolio",
            domain=PortfolioDomain.SWING,
            capabilities=frozenset({PortfolioCapability.LEVERAGE}),
            overwrite=False,
        )
        entries = class_registry.by_capability(PortfolioCapability.LEVERAGE)
        assert any(e.class_name == "CapPortfolio" for e in entries)

    def test_unregister(self, class_registry):
        from tests.unit.investment.portfolio.core.conftest import _MinimalPortfolio
        class_registry.register(
            _MinimalPortfolio, class_name="ToRemove",
            domain=PortfolioDomain.CUSTOM,
        )
        assert class_registry.unregister("ToRemove")
        assert not class_registry.is_registered("ToRemove")
        assert not class_registry.unregister("ToRemove")

    def test_entry_to_dict(self, class_registry):
        e = class_registry.get_entry("_MinimalPortfolio")
        d = e.to_dict()
        assert "class_name" in d
        assert "domain" in d

    def test_active_count(self, class_registry):
        assert class_registry.active_count() >= 2


class TestPortfolioCatalog:
    def test_add_and_get_entry(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        catalog.add_entry(
            "_MinimalPortfolio",
            display_name = "Minimal Swing",
            summary      = "A minimal swing portfolio",
            maturity     = "stable",
        )
        entry = catalog.get_entry("_MinimalPortfolio")
        assert entry is not None
        assert entry.display_name == "Minimal Swing"

    def test_duplicate_entry_raises(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        catalog.add_entry("_MinimalPortfolio", maturity="stable")
        with pytest.raises(ValueError):
            catalog.add_entry("_MinimalPortfolio", maturity="beta")

    def test_overwrite_allowed(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        catalog.add_entry("_MinimalPortfolio", maturity="beta")
        catalog.add_entry("_MinimalPortfolio", maturity="stable", overwrite=True)
        e = catalog.get_entry("_MinimalPortfolio")
        assert e.maturity == "stable"

    def test_all_entries(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        entries = catalog.all_entries()
        assert len(entries) >= 2

    def test_search_by_domain(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        results = catalog.search(domain=PortfolioDomain.SWING)
        assert any(e.domain == PortfolioDomain.SWING for e in results)

    def test_search_by_query(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        catalog.add_entry("_MinimalPortfolio", display_name="Minimal Swing Portfolio")
        results = catalog.search(query="minimal")
        assert len(results) >= 1

    def test_search_excludes_deprecated(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        catalog.add_entry("_MinimalPortfolio", maturity="deprecated")
        results = catalog.search(domain=PortfolioDomain.SWING, include_deprecated=False)
        assert all(not e.is_deprecated for e in results)

    def test_stable_entries(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        catalog.add_entry("_MinimalPortfolio", maturity="stable")
        stable = catalog.stable_entries()
        assert all(e.is_stable for e in stable)

    def test_by_domain(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        entries = catalog.by_domain(PortfolioDomain.LONG_TERM)
        assert len(entries) >= 1

    def test_count(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        assert catalog.count() >= 2

    def test_entry_to_dict(self, class_registry):
        catalog = PortfolioCatalog(class_registry)
        e = catalog.get_entry("_MinimalPortfolio")
        assert e is not None
        d = e.to_dict()
        assert "class_name" in d
        assert "is_deprecated" in d


class TestPortfolioLoader:
    def test_load_invalid_path(self):
        reg = PortfolioClassRegistry()
        loader = PortfolioLoader(reg)
        result = loader.load_class("not.a.valid.path")
        assert not result.success

    def test_load_non_portfolio_class(self):
        reg = PortfolioClassRegistry()
        loader = PortfolioLoader(reg)
        # Try loading a non-portfolio class
        result = loader.load_class("os.path.join")
        assert not result.success

    def test_load_result_to_dict(self):
        reg = PortfolioClassRegistry()
        loader = PortfolioLoader(reg)
        result = loader.load_class("invalid.path")
        d = result.to_dict()
        assert "success" in d
        assert "error" in d

    def test_load_many_with_errors(self):
        reg = PortfolioClassRegistry()
        loader = PortfolioLoader(reg)
        results = loader.load_many([
            {"path": "nonexistent.Module", "domain": "custom"},
            {"path": "another.bad.Path",   "domain": "swing"},
        ])
        assert all(not r.success for r in results)
        assert len(results) == 2


class TestPortfolioFactory:
    def test_create_success(self, class_registry, context):
        factory = PortfolioFactory(class_registry, context)
        result = factory.create("_MinimalPortfolio", name="Test Swing")
        assert result.success
        assert result.portfolio is not None

    def test_create_unknown_class(self, class_registry, context):
        factory = PortfolioFactory(class_registry, context)
        result = factory.create("NonExistentClass")
        assert not result.success
        assert result.error

    def test_create_or_raise_on_failure(self, class_registry, context):
        factory = PortfolioFactory(class_registry, context)
        with pytest.raises(RuntimeError):
            factory.create_or_raise("NonExistentClass")

    def test_create_sets_portfolio_id(self, class_registry, context):
        factory = PortfolioFactory(class_registry, context)
        result = factory.create("_MinimalPortfolio", portfolio_id="MY-ID")
        assert result.portfolio_id == "MY-ID"
        assert result.portfolio.portfolio_id == "MY-ID"

    def test_create_long_term(self, class_registry, context):
        factory = PortfolioFactory(class_registry, context)
        result = factory.create("_LongTermPortfolio", domain=PortfolioDomain.LONG_TERM)
        assert result.success
        assert result.portfolio.metadata.domain == PortfolioDomain.LONG_TERM

    def test_factory_result_to_dict(self, class_registry, context):
        factory = PortfolioFactory(class_registry, context)
        result = factory.create("_MinimalPortfolio")
        d = result.to_dict()
        assert "success" in d
        assert "class_name" in d
        assert "portfolio_id" in d

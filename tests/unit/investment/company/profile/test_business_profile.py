"""tests/unit/investment/company/profile/test_business_profile.py"""
from __future__ import annotations

import pytest

from iios.investment.company.profile.business_profile import BusinessProfileBuilder, BusinessProfileManager
from iios.investment.company.profile.business_segments import SegmentStore
from iios.investment.company.profile.geographic_presence import GeographicPresenceStore
from iios.investment.company.profile.models import (
    BusinessSegment,
    GeographicPresence,
    OperationsType,
    Product,
    Service,
)
from iios.investment.company.profile.products_services import ProductServiceStore


class TestSegmentStore:
    def test_add_and_retrieve(self):
        store = SegmentStore()
        store.add(BusinessSegment("Chemicals", "desc", 40.0, True))
        store.add(BusinessSegment("Retail",    "desc", 60.0, False))
        assert len(store) == 2

    def test_replaces_existing_name(self):
        store = SegmentStore()
        store.add(BusinessSegment("A", "", 30.0, False))
        store.add(BusinessSegment("A", "", 50.0, False))
        assert len(store) == 1
        assert store.all()[0].revenue_pct == pytest.approx(50.0)

    def test_remove(self):
        store = SegmentStore()
        store.add(BusinessSegment("A", "", 30.0, False))
        assert store.remove("A") is True
        assert len(store) == 0

    def test_primary_explicit(self):
        store = SegmentStore()
        store.add(BusinessSegment("A", "", 30.0, False))
        store.add(BusinessSegment("B", "", 50.0, True))
        assert store.primary().name == "B"

    def test_primary_implicit(self):
        store = SegmentStore()
        store.add(BusinessSegment("A", "", 30.0, False))
        store.add(BusinessSegment("B", "", 70.0, False))
        assert store.primary().name == "B"

    def test_is_balanced(self):
        store = SegmentStore()
        store.add(BusinessSegment("A", "", 60.0, False))
        store.add(BusinessSegment("B", "", 40.0, False))
        assert store.is_balanced() is True

    def test_not_balanced(self):
        store = SegmentStore()
        store.add(BusinessSegment("A", "", 30.0, False))
        assert store.is_balanced() is False

    def test_total_revenue_pct(self):
        store = SegmentStore()
        store.add(BusinessSegment("A", "", 60.0, False))
        store.add(BusinessSegment("B", "", 40.0, False))
        assert store.total_revenue_pct() == pytest.approx(100.0)

    def test_only_one_primary_enforced(self):
        store = SegmentStore()
        store.add(BusinessSegment("A", "", 40.0, True))
        store.add(BusinessSegment("B", "", 60.0, True))
        primaries = [s for s in store.all() if s.is_primary]
        assert len(primaries) == 1


class TestProductServiceStore:
    def test_add_and_retrieve_products(self):
        store = ProductServiceStore()
        store.add_product(Product("Petrol", "Fuel"))
        assert store.product_count() == 1

    def test_no_duplicate_products(self):
        store = ProductServiceStore()
        store.add_product(Product("X", "cat"))
        store.add_product(Product("X", "cat"))
        assert store.product_count() == 1

    def test_add_and_retrieve_services(self):
        store = ProductServiceStore()
        store.add_service(Service("Jio", "Telecom"))
        assert store.service_count() == 1

    def test_remove_product(self):
        store = ProductServiceStore()
        store.add_product(Product("Y", "cat"))
        assert store.remove_product("Y") is True
        assert store.product_count() == 0

    def test_products_by_category(self):
        store = ProductServiceStore()
        store.add_product(Product("A", "Fuel"))
        store.add_product(Product("B", "Fuel"))
        store.add_product(Product("C", "Chemical"))
        by_cat = store.products_by_category()
        assert len(by_cat["Fuel"]) == 2

    def test_categories(self):
        store = ProductServiceStore()
        store.add_product(Product("P", "catA"))
        store.add_service(Service("S", "catB"))
        assert set(store.categories()) == {"catA", "catB"}


class TestGeographicPresenceStore:
    def test_add_and_retrieve(self):
        store = GeographicPresenceStore()
        store.add(GeographicPresence("IN", "Asia", 80.0, OperationsType.HQ))
        assert len(store) == 1

    def test_replaces_same_country_and_type(self):
        store = GeographicPresenceStore()
        store.add(GeographicPresence("IN", "Asia", 80.0, OperationsType.HQ))
        store.add(GeographicPresence("IN", "Asia", 90.0, OperationsType.HQ))
        assert len(store) == 1
        assert store.all()[0].revenue_pct == pytest.approx(90.0)

    def test_by_region(self):
        store = GeographicPresenceStore()
        store.add(GeographicPresence("IN", "Asia", 70.0, OperationsType.HQ))
        store.add(GeographicPresence("US", "Americas", 20.0, OperationsType.SALES))
        by_region = store.by_region()
        assert "Asia" in by_region

    def test_domestic_pct(self):
        store = GeographicPresenceStore()
        store.add(GeographicPresence("IN", "Asia", 80.0, OperationsType.HQ))
        store.add(GeographicPresence("US", "Americas", 20.0, OperationsType.SALES))
        assert store.domestic_pct("IN") == pytest.approx(80.0)
        assert store.international_pct("IN") == pytest.approx(20.0)

    def test_top_countries(self):
        store = GeographicPresenceStore()
        store.add(GeographicPresence("IN", "Asia", 70.0, OperationsType.HQ))
        store.add(GeographicPresence("US", "Americas", 20.0, OperationsType.SALES))
        store.add(GeographicPresence("GB", "Europe", 10.0, OperationsType.OFFICE))
        top2 = store.top_countries(2)
        assert top2[0].country == "IN"
        assert top2[1].country == "US"


class TestBusinessProfileBuilder:
    def test_build_empty(self):
        bp = BusinessProfileBuilder().build()
        assert bp.description == ""

    def test_build_complete(self):
        bp = (
            BusinessProfileBuilder()
            .set_description("A great company")
            .set_business_model("B2B")
            .add_segment(BusinessSegment("Core", "", 100.0, True))
            .add_product(Product("Widget", "Widgets"))
            .add_service(Service("Support", "Services"))
            .add_geography(GeographicPresence("IN", "Asia", 100.0, OperationsType.HQ))
            .set_customers(["Enterprise"])
            .set_suppliers(["Supplier A"])
            .set_channels(["Direct Sales"])
            .build()
        )
        assert bp.description == "A great company"
        assert len(bp.segments) == 1
        assert len(bp.products) == 1
        assert len(bp.services) == 1


class TestBusinessProfileManager:
    def test_update_description(self):
        mgr = BusinessProfileManager()
        mgr.update_description("New description")
        assert mgr.get().description == "New description"

    def test_is_complete(self):
        mgr = BusinessProfileManager()
        mgr.update_description("desc")
        mgr.update_business_model("B2B")
        assert mgr.is_complete() is True

    def test_not_complete_missing_model(self):
        mgr = BusinessProfileManager()
        mgr.update_description("desc")
        assert mgr.is_complete() is False

    def test_add_segment(self):
        mgr = BusinessProfileManager()
        mgr.update_description("desc")
        mgr.update_business_model("B2B")
        mgr.add_segment(BusinessSegment("Core", "", 100.0, True))
        assert len(mgr.get().segments) == 1

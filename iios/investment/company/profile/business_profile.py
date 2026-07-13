"""iios/investment/company/profile/business_profile.py
BusinessProfile builder and manager with segment/product/geography sub-systems.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.profile.business_segments import SegmentStore
from iios.investment.company.profile.geographic_presence import GeographicPresenceStore
from iios.investment.company.profile.models import (
    BusinessProfile,
    BusinessSegment,
    GeographicPresence,
    Product,
    Service,
)
from iios.investment.company.profile.products_services import ProductServiceStore


class BusinessProfileBuilder:
    """Incrementally builds a BusinessProfile."""

    def __init__(self) -> None:
        self._description:           str = ""
        self._business_model:        str = ""
        self._segments:              SegmentStore          = SegmentStore()
        self._products_services:     ProductServiceStore   = ProductServiceStore()
        self._geography:             GeographicPresenceStore = GeographicPresenceStore()
        self._customers:             List[str] = []
        self._suppliers:             List[str] = []
        self._distribution_channels: List[str] = []

    def set_description(self, text: str) -> "BusinessProfileBuilder":
        self._description = text
        return self

    def set_business_model(self, model: str) -> "BusinessProfileBuilder":
        self._business_model = model
        return self

    def add_segment(self, segment: BusinessSegment) -> "BusinessProfileBuilder":
        self._segments.add(segment)
        return self

    def add_product(self, product: Product) -> "BusinessProfileBuilder":
        self._products_services.add_product(product)
        return self

    def add_service(self, service: Service) -> "BusinessProfileBuilder":
        self._products_services.add_service(service)
        return self

    def add_geography(self, presence: GeographicPresence) -> "BusinessProfileBuilder":
        self._geography.add(presence)
        return self

    def set_customers(self, customers: List[str]) -> "BusinessProfileBuilder":
        self._customers = list(customers)
        return self

    def set_suppliers(self, suppliers: List[str]) -> "BusinessProfileBuilder":
        self._suppliers = list(suppliers)
        return self

    def set_channels(self, channels: List[str]) -> "BusinessProfileBuilder":
        self._distribution_channels = list(channels)
        return self

    def build(self) -> BusinessProfile:
        return BusinessProfile(
            description=self._description,
            business_model=self._business_model,
            segments=self._segments.all(),
            products=self._products_services.products(),
            services=self._products_services.services(),
            customers=list(self._customers),
            suppliers=list(self._suppliers),
            distribution_channels=list(self._distribution_channels),
        )


class BusinessProfileManager:
    """Manages the BusinessProfile for one company with incremental updates."""

    def __init__(self, profile: Optional[BusinessProfile] = None) -> None:
        self._profile = profile

    def get(self) -> Optional[BusinessProfile]:
        return self._profile

    def set(self, profile: BusinessProfile) -> None:
        self._profile = profile

    def update_description(self, text: str) -> None:
        if self._profile is None:
            self._profile = BusinessProfile(description=text, business_model="")
        else:
            self._profile.description = text

    def update_business_model(self, model: str) -> None:
        if self._profile is None:
            self._profile = BusinessProfile(description="", business_model=model)
        else:
            self._profile.business_model = model

    def add_segment(self, segment: BusinessSegment) -> None:
        if self._profile is None:
            self._profile = BusinessProfile(description="", business_model="")
        store = SegmentStore()
        for s in self._profile.segments:
            store.add(s)
        store.add(segment)
        self._profile.segments = store.all()

    def add_geography(self, presence: GeographicPresence) -> None:
        if self._profile is None:
            self._profile = BusinessProfile(description="", business_model="")
        store = GeographicPresenceStore()
        for g in self._profile.geography if hasattr(self._profile, "geography") else []:
            store.add(g)
        store.add(presence)
        self._profile.geography = store.all() if hasattr(store, "geography") else []

    def is_complete(self) -> bool:
        return (
            self._profile is not None
            and bool(self._profile.description)
            and bool(self._profile.business_model)
        )

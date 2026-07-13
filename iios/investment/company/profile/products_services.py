"""iios/investment/company/profile/products_services.py
Product and service catalogue management.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.company.profile.models import Product, Service


class ProductServiceStore:
    """Manages products and services for one company."""

    def __init__(self) -> None:
        self._products: List[Product] = []
        self._services: List[Service] = []

    # ── products ──────────────────────────────────────────────────────────────

    def add_product(self, product: Product) -> None:
        if not any(p.name == product.name for p in self._products):
            self._products.append(product)

    def remove_product(self, name: str) -> bool:
        before = len(self._products)
        self._products = [p for p in self._products if p.name != name]
        return len(self._products) < before

    def products(self) -> List[Product]:
        return list(self._products)

    def products_by_category(self) -> Dict[str, List[Product]]:
        result: Dict[str, List[Product]] = {}
        for p in self._products:
            result.setdefault(p.category, []).append(p)
        return result

    # ── services ──────────────────────────────────────────────────────────────

    def add_service(self, service: Service) -> None:
        if not any(s.name == service.name for s in self._services):
            self._services.append(service)

    def remove_service(self, name: str) -> bool:
        before = len(self._services)
        self._services = [s for s in self._services if s.name != name]
        return len(self._services) < before

    def services(self) -> List[Service]:
        return list(self._services)

    def services_by_category(self) -> Dict[str, List[Service]]:
        result: Dict[str, List[Service]] = {}
        for s in self._services:
            result.setdefault(s.category, []).append(s)
        return result

    # ── summary ───────────────────────────────────────────────────────────────

    def product_count(self) -> int:
        return len(self._products)

    def service_count(self) -> int:
        return len(self._services)

    def categories(self) -> List[str]:
        prod_cats = {p.category for p in self._products}
        svc_cats  = {s.category for s in self._services}
        return sorted(prod_cats | svc_cats)

"""iios/investment/company/company_registry.py
Thread-safe registry of companies and their associated analyzers/providers.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.investment.company.company_constants import (
    DEFAULT_MAX_ANALYZERS,
    DEFAULT_MAX_COMPANIES,
    SectorClassification,
)
from iios.investment.company.company_exceptions import (
    CompanyAlreadyExistsError,
    CompanyNotFoundError,
    CompanyRegistryItemAlreadyExistsError,
    CompanyRegistryItemNotFoundError,
    CompanyRegistryOverflowError,
)


class CompanyRegistry:
    """
    Central registry for:
    - Listed company identifiers (company_id → info dict)
    - Named analyzers
    - Named data providers
    """

    def __init__(
        self,
        max_companies: int = DEFAULT_MAX_COMPANIES,
        max_analyzers: int = DEFAULT_MAX_ANALYZERS,
    ) -> None:
        self._lock          = threading.RLock()
        self._max_companies = max_companies
        self._max_analyzers = max_analyzers
        self._companies:   dict[str, dict[str, Any]] = {}
        self._analyzers:   dict[str, Any]            = {}
        self._providers:   dict[str, Any]            = {}

    # ── companies ─────────────────────────────────────────────────────────────

    def register_company(
        self,
        company_id: str,
        ticker:     str,
        name:       str,
        sector:     SectorClassification = SectorClassification.UNKNOWN,
        exchange:   str = "",
        **kwargs: Any,
    ) -> None:
        with self._lock:
            if company_id in self._companies:
                raise CompanyAlreadyExistsError(
                    f"Company already registered: {company_id}",
                    company_id=company_id,
                )
            if len(self._companies) >= self._max_companies:
                raise CompanyRegistryOverflowError(
                    f"Company registry full ({self._max_companies})",
                    capacity=self._max_companies,
                    current=len(self._companies),
                )  # noqa: E501
            self._companies[company_id] = {
                "company_id": company_id,
                "ticker":     ticker,
                "name":       name,
                "sector":     sector.value,
                "exchange":   exchange,
                **kwargs,
            }

    def is_registered(self, company_id: str) -> bool:
        with self._lock:
            return company_id in self._companies

    def get_company_info(self, company_id: str) -> dict[str, Any]:
        with self._lock:
            if company_id not in self._companies:
                raise CompanyNotFoundError(
                    f"Company not registered: {company_id}",
                    company_id=company_id,
                )  # noqa: E501
            return dict(self._companies[company_id])

    def all_companies(self) -> list[str]:
        with self._lock:
            return list(self._companies.keys())

    # ── analyzers ────────────────────────────────────────────────────────────

    def register_analyzer(
        self,
        analyzer_id: str,
        analyzer:    Any,
        *,
        overwrite:   bool = False,
    ) -> None:
        with self._lock:
            if analyzer_id in self._analyzers and not overwrite:
                raise CompanyRegistryItemAlreadyExistsError(
                    f"Analyzer already registered: {analyzer_id}",
                    item_id=analyzer_id,
                )
            if len(self._analyzers) >= self._max_analyzers:
                raise CompanyRegistryOverflowError(
                    f"Analyzer registry full ({self._max_analyzers})",
                    capacity=self._max_analyzers,
                    current=len(self._analyzers),
                )  # noqa: E501
            self._analyzers[analyzer_id] = analyzer

    def get_analyzer(self, analyzer_id: str) -> Any:
        with self._lock:
            if analyzer_id not in self._analyzers:
                raise CompanyRegistryItemNotFoundError(
                    f"Analyzer not found: {analyzer_id}",
                    item_id=analyzer_id,
                )  # noqa: E501
            return self._analyzers[analyzer_id]

    def has_analyzer(self, analyzer_id: str) -> bool:
        with self._lock:
            return analyzer_id in self._analyzers

    # ── providers ────────────────────────────────────────────────────────────

    def register_provider(
        self,
        provider_id: str,
        provider:    Any,
        *,
        overwrite:   bool = False,
    ) -> None:
        with self._lock:
            if provider_id in self._providers and not overwrite:
                raise CompanyRegistryItemAlreadyExistsError(
                    f"Provider already registered: {provider_id}",
                    item_id=provider_id,
                )  # noqa: E501
            self._providers[provider_id] = provider

    def get_provider(self, provider_id: str) -> Any:
        with self._lock:
            if provider_id not in self._providers:
                raise CompanyRegistryItemNotFoundError(
                    f"Provider not found: {provider_id}",
                    item_id=provider_id,
                )  # noqa: E501
            return self._providers[provider_id]

    # ── statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered_companies": len(self._companies),
                "max_companies":        self._max_companies,
                "registered_analyzers": len(self._analyzers),
                "max_analyzers":        self._max_analyzers,
                "registered_providers": len(self._providers),
            }


# ── module-level singleton ────────────────────────────────────────────────────

_registry_lock:     threading.Lock                   = threading.Lock()
_registry_instance: CompanyRegistry | None           = None


def get_company_registry() -> CompanyRegistry:
    global _registry_instance
    with _registry_lock:
        if _registry_instance is None:
            _registry_instance = CompanyRegistry()
        return _registry_instance


def reset_company_registry() -> None:
    global _registry_instance
    with _registry_lock:
        _registry_instance = None

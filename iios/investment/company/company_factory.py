"""iios/investment/company/company_factory.py
Convenience factory for constructing company domain objects.
"""
from __future__ import annotations

from typing import Any

from iios.investment.company.company_constants import (
    BusinessModel,
    CompanyStage,
    MarketCapCategory,
    SectorClassification,
)
from iios.investment.company.models.company_signal import (
    CompanySignal,
    CompanySignalStrength,
    CompanySignalType,
)
from iios.investment.company.profile.company_identity import CompanyIdentity
from iios.investment.company.profile.company_metadata import CompanyMetadata
from iios.investment.company.profile.company_profile import CompanyProfile
from iios.investment.company.profile.company_snapshot import CompanySnapshot


class CompanyFactory:
    """Stateless factory — all methods are static."""

    @staticmethod
    def make_identity(
        company_id:          str,
        ticker:              str,
        name:                str,
        exchange:            str                 = "",
        sector:              SectorClassification = SectorClassification.UNKNOWN,
        isin:                str                 = "",
        country:             str                 = "",
        currency:            str                 = "INR",
        market_cap_category: MarketCapCategory   = MarketCapCategory.UNKNOWN,
        **kwargs: Any,
    ) -> CompanyIdentity:
        return CompanyIdentity(
            company_id          = company_id,
            ticker              = ticker,
            name                = name,
            exchange            = exchange,
            sector              = sector,
            isin                = isin,
            country             = country,
            currency            = currency,
            market_cap_category = market_cap_category,
            short_name          = kwargs.get("short_name", ""),
        )

    @staticmethod
    def make_metadata(
        company_id:     str,
        business_model: BusinessModel = BusinessModel.UNKNOWN,
        stage:          CompanyStage  = CompanyStage.UNKNOWN,
        **kwargs: Any,
    ) -> CompanyMetadata:
        return CompanyMetadata(
            company_id     = company_id,
            business_model = business_model,
            stage          = stage,
            founded_year   = kwargs.get("founded_year"),
            employees      = int(kwargs.get("employees", 0) or 0),
            headquarters   = str(kwargs.get("headquarters", "") or ""),
            description    = str(kwargs.get("description", "") or ""),
            products       = list(kwargs.get("products", [])),
            geographies    = list(kwargs.get("geographies", [])),
            tags           = list(kwargs.get("tags", [])),
        )

    @staticmethod
    def make_snapshot(
        company_id:  str,
        price:       float = 0.0,
        market_cap:  float = 0.0,
        **kwargs: Any,
    ) -> CompanySnapshot:
        return CompanySnapshot(
            company_id        = company_id,
            price             = price,
            market_cap        = market_cap,
            price_change_pct  = float(kwargs.get("price_change_pct", 0.0) or 0.0),
            volume            = float(kwargs.get("volume", 0.0) or 0.0),
            pe_ratio          = kwargs.get("pe_ratio"),
            pb_ratio          = kwargs.get("pb_ratio"),
            ev_ebitda         = kwargs.get("ev_ebitda"),
            roe               = kwargs.get("roe"),
            debt_to_equity    = kwargs.get("debt_to_equity"),
            revenue_growth    = kwargs.get("revenue_growth"),
            promoter_holding  = kwargs.get("promoter_holding"),
        )

    @staticmethod
    def make_profile(
        identity: CompanyIdentity,
        metadata: CompanyMetadata | None = None,
    ) -> CompanyProfile:
        if metadata is None:
            metadata = CompanyMetadata(company_id=identity.company_id)
        return CompanyProfile(
            company_id   = identity.company_id,
            identity     = identity,
            company_meta = metadata,
        )

    @staticmethod
    def make_signal(
        company_id:  str,
        label:       str,
        signal_type: str   = CompanySignalType.CUSTOM,
        description: str   = "",
        strength:    str   = CompanySignalStrength.MODERATE,
        confidence:  float = 0.5,
        direction:   str   = "neutral",
        value:       float | None = None,
        **metadata: Any,
    ) -> CompanySignal:
        return CompanySignal(
            company_id  = company_id,
            signal_type = signal_type,
            label       = label,
            description = description,
            strength    = strength,
            confidence  = confidence,
            direction   = direction,
            value       = value,
            metadata    = dict(metadata),
        )

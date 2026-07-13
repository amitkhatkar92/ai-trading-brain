"""tests/unit/investment/company/profile/conftest.py"""
from __future__ import annotations

import time

import pytest

from iios.investment.company.profile.models import (
    AliasType,
    BusinessProfile,
    BusinessSegment,
    CompanyAlias,
    CompanyClassification,
    CompanyIdentity,
    CompanyMetadata,
    CompanyProfile,
    CompanyRelationships,
    CorporateEvent,
    CorporateEventType,
    GeographicPresence,
    ListingStatus,
    MarketCapCategory,
    OperationsType,
    Product,
    RelatedEntity,
    RelationshipType,
    Service,
    Subsidiary,
    TaxonomyType,
)


def _identity(
    ticker:   str   = "RELIANCE",
    name:     str   = "Reliance Industries Limited",
    exchange: str   = "NSE",
    country:  str   = "IN",
    currency: str   = "INR",
    sector:   str   = "Energy",
    industry: str   = "Oil & Gas",
    isin:     str   = "INE002A01018",
) -> CompanyIdentity:
    return CompanyIdentity(
        ticker=ticker, name=name, exchange=exchange,
        country=country, currency=currency,
        sector=sector, industry=industry, isin=isin,
    )


def _metadata(
    description: str = "India's largest private sector company.",
    founding_year: int = 1973,
    ipo_date: str = "1977-01-01",
    employees: int = 236334,
    hq_city: str = "Mumbai",
    hq_country: str = "IN",
    website: str = "https://www.ril.com",
    fiscal_year_end: str = "MAR",
    cap_category: MarketCapCategory = MarketCapCategory.MEGA,
) -> CompanyMetadata:
    return CompanyMetadata(
        description=description,
        founding_year=founding_year,
        ipo_date=ipo_date,
        employees=employees,
        headquarters_city=hq_city,
        headquarters_country=hq_country,
        website=website,
        fiscal_year_end=fiscal_year_end,
        market_cap_category=cap_category,
    )


def _full_profile(ticker: str = "RELIANCE") -> CompanyProfile:
    ts      = time.time()
    identity = _identity(ticker=ticker)
    metadata = _metadata()
    profile  = CompanyProfile.new(identity, metadata, ts)

    profile.business = BusinessProfile(
        description="Largest diversified conglomerate in India.",
        business_model="Integrated",
        segments=[
            BusinessSegment("Oil to Chemicals", "Petrochemicals, refining", 55.0, True),
            BusinessSegment("Retail", "Organised retail", 25.0, False),
            BusinessSegment("Jio Platforms", "Digital & telecom", 20.0, False),
        ],
        products=[Product("Petrol", "Fuel"), Product("Polyester", "Chemicals")],
        services=[Service("Jio", "Telecom"), Service("JioMart", "E-Commerce")],
        customers=["B2C", "Industrial"],
        suppliers=["ONGC", "Cairn"],
        distribution_channels=["Direct", "Retail", "Online"],
    )

    profile.geography = [
        GeographicPresence("IN", "Asia", 85.0, OperationsType.HQ),
        GeographicPresence("US", "Americas", 10.0, OperationsType.SALES),
        GeographicPresence("GB", "Europe", 5.0, OperationsType.OFFICE),
    ]

    profile.classification = CompanyClassification(
        taxonomy_type=TaxonomyType.GICS,
        gics_sector="Energy",
        nse_sector="Energy",
        investment_themes=["Renewable Energy", "Digital Payments"],
        megatrends=["Decarbonization"],
    )

    profile.relationships = CompanyRelationships(
        subsidiaries=[
            Subsidiary("Jio Platforms Ltd", 85.0, "IN", RelationshipType.SUBSIDIARY),
            Subsidiary("Reliance Retail Ventures", 100.0, "IN", RelationshipType.SUBSIDIARY),
        ],
        associates=[
            RelatedEntity.new("Network18 Media", RelationshipType.ASSOCIATE,
                              ownership_pct=70.0, ticker="NETWORK18", country="IN"),
        ],
    )

    profile.history = [
        CorporateEvent.new(CorporateEventType.FOUNDING,    "1973-05-08", "Company founded"),
        CorporateEvent.new(CorporateEventType.IPO,         "1977-01-01", "Listed on BSE"),
        CorporateEvent.new(CorporateEventType.ACQUISITION, "2021-06-01", "Acquired Future Retail"),
    ]

    profile.aliases = [
        CompanyAlias(AliasType.ABBREVIATION, "RIL"),
        CompanyAlias(AliasType.TRADE_NAME, "Jio", effective_from="2016-09-05"),
    ]

    return profile


@pytest.fixture
def identity():
    return _identity()


@pytest.fixture
def metadata():
    return _metadata()


@pytest.fixture
def full_profile():
    return _full_profile()


@pytest.fixture
def make_profile():
    return _full_profile


@pytest.fixture
def make_identity():
    return _identity


@pytest.fixture
def make_metadata():
    return _metadata

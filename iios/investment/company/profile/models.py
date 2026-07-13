"""iios/investment/company/profile/models.py
All domain types for the Institutional Company Profile Intelligence Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class ListingStatus(str, Enum):
    LISTED   = "listed"
    DELISTED = "delisted"
    SUSPENDED = "suspended"
    UNLISTED  = "unlisted"
    PENDING   = "pending"


class CorporateStructure(str, Enum):
    CORPORATION = "corporation"
    REIT        = "reit"
    ETF         = "etf"
    TRUST       = "trust"
    PARTNERSHIP = "partnership"
    LLC         = "llc"
    OTHER       = "other"


class CorporateEventType(str, Enum):
    FOUNDING              = "founding"
    IPO                   = "ipo"
    MERGER                = "merger"
    ACQUISITION           = "acquisition"
    SPINOFF               = "spinoff"
    NAME_CHANGE           = "name_change"
    RESTRUCTURING         = "restructuring"
    DELISTING             = "delisting"
    RELISTING             = "relisting"
    DIVIDEND_INITIATION   = "dividend_initiation"
    MILESTONE             = "milestone"


class RelationshipType(str, Enum):
    SUBSIDIARY      = "subsidiary"
    ASSOCIATE       = "associate"
    JOINT_VENTURE   = "joint_venture"
    CROSS_HOLDING   = "cross_holding"
    MINORITY_STAKE  = "minority_stake"


class MarketCapCategory(str, Enum):
    MEGA  = "mega"
    LARGE = "large"
    MID   = "mid"
    SMALL = "small"
    MICRO = "micro"
    NANO  = "nano"


class OperationsType(str, Enum):
    HQ            = "hq"
    MANUFACTURING = "manufacturing"
    SALES         = "sales"
    R_AND_D       = "r_and_d"
    DISTRIBUTION  = "distribution"
    OFFICE        = "office"


class AliasType(str, Enum):
    TICKER_OLD   = "ticker_old"
    NAME_OLD     = "name_old"
    TRADE_NAME   = "trade_name"
    DBA          = "dba"          # doing business as
    TICKER_ALT   = "ticker_alt"
    ABBREVIATION = "abbreviation"
    ISIN_OLD     = "isin_old"


class TaxonomyType(str, Enum):
    GICS   = "gics"
    ICB    = "icb"
    NAICS  = "naics"
    NSE    = "nse"
    CUSTOM = "custom"


class ProfileEventType(str, Enum):
    CREATED               = "created"
    UPDATED               = "updated"
    IDENTITY_CHANGED      = "identity_changed"
    CLASSIFICATION_CHANGED = "classification_changed"
    RELATIONSHIP_CHANGED  = "relationship_changed"
    HISTORY_APPENDED      = "history_appended"
    QUALITY_UPDATED       = "quality_updated"
    DELISTED              = "delisted"


# ── Identity ──────────────────────────────────────────────────────────────────

@dataclass
class CompanyIdentity:
    ticker:              str
    name:                str
    exchange:            str
    country:             str
    currency:            str
    listing_status:      ListingStatus       = ListingStatus.LISTED
    corporate_structure: CorporateStructure  = CorporateStructure.CORPORATION
    sector:              Optional[str]       = None
    industry:            Optional[str]       = None
    sub_industry:        Optional[str]       = None
    isin:                Optional[str]       = None
    cusip:               Optional[str]       = None
    lei:                 Optional[str]       = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":              self.ticker,
            "name":                self.name,
            "exchange":            self.exchange,
            "country":             self.country,
            "currency":            self.currency,
            "listing_status":      self.listing_status.value,
            "corporate_structure": self.corporate_structure.value,
            "sector":              self.sector,
            "industry":            self.industry,
            "sub_industry":        self.sub_industry,
            "isin":                self.isin,
            "cusip":               self.cusip,
            "lei":                 self.lei,
        }


@dataclass
class CompanyAlias:
    alias_type:     AliasType
    value:          str
    effective_from: Optional[str] = None   # ISO date
    effective_to:   Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alias_type":     self.alias_type.value,
            "value":          self.value,
            "effective_from": self.effective_from,
            "effective_to":   self.effective_to,
        }


@dataclass
class CompanyMetadata:
    description:           Optional[str]             = None
    founding_year:         Optional[int]             = None
    ipo_date:              Optional[str]             = None   # ISO date
    employees:             Optional[int]             = None
    headquarters_city:     Optional[str]             = None
    headquarters_country:  Optional[str]             = None
    website:               Optional[str]             = None
    fiscal_year_end:       Optional[str]             = None   # "DEC", "MAR", …
    market_cap_category:   Optional[MarketCapCategory] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description":          self.description,
            "founding_year":        self.founding_year,
            "ipo_date":             self.ipo_date,
            "employees":            self.employees,
            "headquarters_city":    self.headquarters_city,
            "headquarters_country": self.headquarters_country,
            "website":              self.website,
            "fiscal_year_end":      self.fiscal_year_end,
            "market_cap_category":  self.market_cap_category.value
                                    if self.market_cap_category else None,
        }


# ── Business ──────────────────────────────────────────────────────────────────

@dataclass
class BusinessSegment:
    name:        str
    description: str
    revenue_pct: float    # 0-100
    is_primary:  bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":        self.name,
            "description": self.description,
            "revenue_pct": round(self.revenue_pct, 2),
            "is_primary":  self.is_primary,
        }


@dataclass
class Product:
    name:        str
    category:    str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "category": self.category, "description": self.description}


@dataclass
class Service:
    name:        str
    category:    str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "category": self.category, "description": self.description}


@dataclass
class GeographicPresence:
    country:         str
    region:          str
    revenue_pct:     float          # 0-100
    operations_type: OperationsType = OperationsType.OFFICE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "country":         self.country,
            "region":          self.region,
            "revenue_pct":     round(self.revenue_pct, 2),
            "operations_type": self.operations_type.value,
        }


@dataclass
class BusinessProfile:
    description:           str
    business_model:        str
    segments:              List[BusinessSegment]  = field(default_factory=list)
    products:              List[Product]          = field(default_factory=list)
    services:              List[Service]          = field(default_factory=list)
    customers:             List[str]              = field(default_factory=list)
    suppliers:             List[str]              = field(default_factory=list)
    distribution_channels: List[str]              = field(default_factory=list)

    def primary_segment(self) -> Optional[BusinessSegment]:
        primary = [s for s in self.segments if s.is_primary]
        if primary:
            return primary[0]
        if self.segments:
            return max(self.segments, key=lambda s: s.revenue_pct)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description":           self.description,
            "business_model":        self.business_model,
            "segments":              [s.to_dict() for s in self.segments],
            "products":              [p.to_dict() for p in self.products],
            "services":              [s.to_dict() for s in self.services],
            "customers":             list(self.customers),
            "suppliers":             list(self.suppliers),
            "distribution_channels": list(self.distribution_channels),
        }


# ── Corporate History ─────────────────────────────────────────────────────────

@dataclass
class CorporateEvent:
    event_id:    str
    event_type:  CorporateEventType
    date:        str                    # ISO date "YYYY-MM-DD"
    description: str
    details:     Dict[str, Any]         = field(default_factory=dict)

    @staticmethod
    def new(
        event_type:  CorporateEventType,
        date:        str,
        description: str,
        details:     Optional[Dict[str, Any]] = None,
    ) -> "CorporateEvent":
        return CorporateEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            date=date,
            description=description,
            details=details or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "date":        self.date,
            "description": self.description,
            "details":     self.details,
        }


# ── Classification ────────────────────────────────────────────────────────────

@dataclass
class CompanyClassification:
    taxonomy_type:       TaxonomyType      = TaxonomyType.GICS
    gics_sector:         Optional[str]     = None
    gics_industry_group: Optional[str]     = None
    gics_industry:       Optional[str]     = None
    gics_sub_industry:   Optional[str]     = None
    icb_sector:          Optional[str]     = None
    icb_subsector:       Optional[str]     = None
    naics_code:          Optional[str]     = None
    nse_sector:          Optional[str]     = None
    investment_themes:   List[str]         = field(default_factory=list)
    megatrends:          List[str]         = field(default_factory=list)
    custom_tags:         List[str]         = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "taxonomy_type":       self.taxonomy_type.value,
            "gics_sector":         self.gics_sector,
            "gics_industry_group": self.gics_industry_group,
            "gics_industry":       self.gics_industry,
            "gics_sub_industry":   self.gics_sub_industry,
            "icb_sector":          self.icb_sector,
            "icb_subsector":       self.icb_subsector,
            "naics_code":          self.naics_code,
            "nse_sector":          self.nse_sector,
            "investment_themes":   list(self.investment_themes),
            "megatrends":          list(self.megatrends),
            "custom_tags":         list(self.custom_tags),
        }


# ── Relationships ─────────────────────────────────────────────────────────────

@dataclass
class Subsidiary:
    name:              str
    ownership_pct:     float
    country:           str
    relationship_type: RelationshipType = RelationshipType.SUBSIDIARY
    ticker:            Optional[str]    = None
    lei:               Optional[str]    = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":              self.name,
            "ownership_pct":     round(self.ownership_pct, 2),
            "country":           self.country,
            "relationship_type": self.relationship_type.value,
            "ticker":            self.ticker,
            "lei":               self.lei,
        }


@dataclass
class RelatedEntity:
    entity_id:         str
    name:              str
    relationship_type: RelationshipType
    ownership_pct:     Optional[float] = None
    ticker:            Optional[str]   = None
    country:           Optional[str]   = None

    @staticmethod
    def new(name: str, rel_type: RelationshipType, **kwargs) -> "RelatedEntity":
        return RelatedEntity(
            entity_id=str(uuid.uuid4()),
            name=name,
            relationship_type=rel_type,
            **kwargs,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id":         self.entity_id,
            "name":              self.name,
            "relationship_type": self.relationship_type.value,
            "ownership_pct":     self.ownership_pct,
            "ticker":            self.ticker,
            "country":           self.country,
        }


@dataclass
class CompanyRelationships:
    parent_ticker:  Optional[str]        = None
    parent_name:    Optional[str]        = None
    parent_lei:     Optional[str]        = None
    subsidiaries:   List[Subsidiary]     = field(default_factory=list)
    associates:     List[RelatedEntity]  = field(default_factory=list)
    joint_ventures: List[RelatedEntity]  = field(default_factory=list)
    cross_holdings: List[RelatedEntity]  = field(default_factory=list)

    def all_related(self) -> List[RelatedEntity]:
        result = []
        for s in self.subsidiaries:
            result.append(RelatedEntity(
                entity_id=str(uuid.uuid4()), name=s.name,
                relationship_type=s.relationship_type,
                ownership_pct=s.ownership_pct, ticker=s.ticker, country=s.country,
            ))
        result.extend(self.associates)
        result.extend(self.joint_ventures)
        result.extend(self.cross_holdings)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parent_ticker":  self.parent_ticker,
            "parent_name":    self.parent_name,
            "parent_lei":     self.parent_lei,
            "subsidiaries":   [s.to_dict() for s in self.subsidiaries],
            "associates":     [e.to_dict() for e in self.associates],
            "joint_ventures": [e.to_dict() for e in self.joint_ventures],
            "cross_holdings": [e.to_dict() for e in self.cross_holdings],
        }


# ── Quality ───────────────────────────────────────────────────────────────────

@dataclass
class ProfileQualityScore:
    profile_id:     str
    completeness:   float     # 0-100
    freshness:      float     # 0-100
    confidence:     float     # 0-100
    coverage:       float     # 0-100
    overall:        float     # 0-100 weighted
    missing_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id":     self.profile_id,
            "completeness":   round(self.completeness, 2),
            "freshness":      round(self.freshness, 2),
            "confidence":     round(self.confidence, 2),
            "coverage":       round(self.coverage, 2),
            "overall":        round(self.overall, 2),
            "missing_fields": list(self.missing_fields),
        }


# ── Profile Event ─────────────────────────────────────────────────────────────

@dataclass
class ProfileEvent:
    event_id:   str
    profile_id: str
    event_type: ProfileEventType
    ticker:     str
    timestamp:  float
    changes:    Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new(
        profile_id: str,
        event_type: ProfileEventType,
        ticker:     str,
        timestamp:  float,
        changes:    Optional[Dict[str, Any]] = None,
    ) -> "ProfileEvent":
        return ProfileEvent(
            event_id=str(uuid.uuid4()),
            profile_id=profile_id,
            event_type=event_type,
            ticker=ticker,
            timestamp=timestamp,
            changes=changes or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "profile_id": self.profile_id,
            "event_type": self.event_type.value,
            "ticker":     self.ticker,
            "timestamp":  self.timestamp,
            "changes":    self.changes,
        }


# ── Master CompanyProfile ─────────────────────────────────────────────────────

@dataclass
class CompanyProfile:
    """Authoritative company identity and business knowledge record."""
    profile_id:      str
    version:         int
    created_at:      float
    updated_at:      float
    identity:        CompanyIdentity
    metadata:        CompanyMetadata
    aliases:         List[CompanyAlias]           = field(default_factory=list)
    business:        Optional[BusinessProfile]    = None
    geography:       List[GeographicPresence]     = field(default_factory=list)
    classification:  Optional[CompanyClassification] = None
    relationships:   Optional[CompanyRelationships]  = None
    history:         List[CorporateEvent]         = field(default_factory=list)
    quality:         Optional[ProfileQualityScore]   = None

    @staticmethod
    def new(identity: CompanyIdentity, metadata: CompanyMetadata, ts: float) -> "CompanyProfile":
        return CompanyProfile(
            profile_id=str(uuid.uuid4()),
            version=1,
            created_at=ts,
            updated_at=ts,
            identity=identity,
            metadata=metadata,
        )

    @property
    def ticker(self) -> str:
        return self.identity.ticker

    @property
    def name(self) -> str:
        return self.identity.name

    def is_active(self) -> bool:
        return self.identity.listing_status is ListingStatus.LISTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id":     self.profile_id,
            "version":        self.version,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "identity":       self.identity.to_dict(),
            "metadata":       self.metadata.to_dict(),
            "aliases":        [a.to_dict() for a in self.aliases],
            "business":       self.business.to_dict() if self.business else None,
            "geography":      [g.to_dict() for g in self.geography],
            "classification": self.classification.to_dict() if self.classification else None,
            "relationships":  self.relationships.to_dict() if self.relationships else None,
            "history":        [e.to_dict() for e in self.history],
            "quality":        self.quality.to_dict() if self.quality else None,
        }

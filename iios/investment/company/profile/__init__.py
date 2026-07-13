"""iios/investment/company/profile/__init__.py"""
from iios.investment.company.profile.company_identity import CompanyIdentity
from iios.investment.company.profile.company_metadata import CompanyMetadata
from iios.investment.company.profile.company_snapshot import CompanySnapshot
from iios.investment.company.profile.company_profile import CompanyProfile
from iios.investment.company.profile.company_history import CompanyHistory
from iios.investment.company.profile.company_profile_engine import CompanyProfileEngine
from iios.investment.company.profile.models import (
    BusinessProfile,
    BusinessSegment,
    CompanyAlias,
    CompanyClassification,
    CompanyIdentity as ProfileCompanyIdentity,
    CompanyMetadata as ProfileCompanyMetadata,
    CompanyProfile as ProfileCompanyProfile,
    CompanyRelationships,
    CorporateEvent,
    CorporateEventType,
    GeographicPresence,
    ListingStatus,
    MarketCapCategory,
    Product,
    ProfileEvent,
    ProfileEventType,
    ProfileQualityScore,
    RelatedEntity,
    RelationshipType,
    Service,
    Subsidiary,
    TaxonomyType,
)

__all__ = [
    # Existing (financial analysis focused)
    "CompanyIdentity",
    "CompanyMetadata",
    "CompanySnapshot",
    "CompanyProfile",
    "CompanyHistory",
    # New profile engine
    "CompanyProfileEngine",
    # New profile models
    "ProfileCompanyIdentity",
    "ProfileCompanyMetadata",
    "ProfileCompanyProfile",
    "BusinessProfile",
    "BusinessSegment",
    "CompanyAlias",
    "CompanyClassification",
    "CompanyRelationships",
    "CorporateEvent",
    "CorporateEventType",
    "GeographicPresence",
    "ListingStatus",
    "MarketCapCategory",
    "Product",
    "ProfileEvent",
    "ProfileEventType",
    "ProfileQualityScore",
    "RelatedEntity",
    "RelationshipType",
    "Service",
    "Subsidiary",
    "TaxonomyType",
]


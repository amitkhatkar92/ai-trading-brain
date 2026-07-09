"""iios/investment/company/__init__.py
Company Intelligence Engine — public API.
"""
from __future__ import annotations

from iios.investment.company.company_constants import (
    COMPANY_ENGINE_SYSTEM_ID,
    COMPANY_ENGINE_VERSION,
    BIG4_FIRMS,
    BusinessModel,
    CompanyIntelligenceStatus,
    CompanyStage,
    CorporateActionType,
    FinancialHealth,
    GovernanceQuality,
    GrowthProfile,
    ListingStatus,
    MarketCapCategory,
    OwnershipConcentration,
    SectorClassification,
    ValuationStatus,
)
from iios.investment.company.company_exceptions import (
    CompanyIntelligenceError,
    CompanyAlreadyExistsError,
    CompanyNotFoundError,
    CompanyEngineAlreadyRunningError,
    CompanyEngineNotInitializedError,
    CompanyRegistryOverflowError,
    FinancialAnalysisFailedError,
    FinancialDataMissingError,
    GovernanceDataMissingError,
    OwnershipDataMissingError,
    ProfileInvalidError,
    ProfileNotFoundError,
    ProfileStaleError,
    ValuationDataMissingError,
    ValuationInvalidError,
)
from iios.investment.company.company_context import (
    CompanyContextState,
    company_session,
    company_stage_scope,
    get_company_context,
    reset_company_context,
)
from iios.investment.company.company_factory import CompanyFactory
from iios.investment.company.company_registry import (
    CompanyRegistry,
    get_company_registry,
    reset_company_registry,
)
from iios.investment.company.company_manager import (
    CompanyManager,
    CompanyStatistics,
    get_company_manager,
    reset_company_manager,
)
from iios.investment.company.company_intelligence_engine import (
    CompanyIntelligenceEngine,
    get_company_engine,
    reset_company_engine,
)
from iios.investment.company.profile import (
    CompanyHistory,
    CompanyIdentity,
    CompanyMetadata,
    CompanyProfile,
    CompanySnapshot,
)
from iios.investment.company.financials import (
    BalanceSheetAnalysis,
    BalanceSheetAnalyzer,
    CashflowAnalysis,
    CashflowAnalyzer,
    FinancialAnalysis,
    FinancialEngine,
    FinancialQualityAnalysis,
    FinancialQualityAnalyzer,
    IncomeStatementAnalysis,
    IncomeStatementAnalyzer,
)
from iios.investment.company.fundamentals import (
    CorporateAction,
    CorporateActionEngine,
    CorporateActionsAnalysis,
    FundamentalAnalysis,
    FundamentalEngine,
    GovernanceAnalysis,
    GovernanceEngine,
    OwnershipAnalysis,
    OwnershipEngine,
    ValuationAnalysis,
    ValuationEngine,
)
from iios.investment.company.models import (
    CompanyHealth,
    CompanyIntelligence,
    CompanySignal,
    CompanySignalStrength,
    CompanySignalType,
)

__version__ = COMPANY_ENGINE_VERSION
__system_id__ = COMPANY_ENGINE_SYSTEM_ID

__all__ = [
    # Engine
    "CompanyIntelligenceEngine",
    "get_company_engine",
    "reset_company_engine",
    # Manager
    "CompanyManager",
    "CompanyStatistics",
    "get_company_manager",
    "reset_company_manager",
    # Registry
    "CompanyRegistry",
    "get_company_registry",
    "reset_company_registry",
    # Factory
    "CompanyFactory",
    # Context
    "CompanyContextState",
    "company_session",
    "company_stage_scope",
    "get_company_context",
    "reset_company_context",
    # Profile
    "CompanyIdentity",
    "CompanyMetadata",
    "CompanySnapshot",
    "CompanyProfile",
    "CompanyHistory",
    # Financials
    "IncomeStatementAnalysis",
    "IncomeStatementAnalyzer",
    "BalanceSheetAnalysis",
    "BalanceSheetAnalyzer",
    "CashflowAnalysis",
    "CashflowAnalyzer",
    "FinancialQualityAnalysis",
    "FinancialQualityAnalyzer",
    "FinancialAnalysis",
    "FinancialEngine",
    # Fundamentals
    "ValuationAnalysis",
    "ValuationEngine",
    "OwnershipAnalysis",
    "OwnershipEngine",
    "GovernanceAnalysis",
    "GovernanceEngine",
    "CorporateAction",
    "CorporateActionsAnalysis",
    "CorporateActionEngine",
    "FundamentalAnalysis",
    "FundamentalEngine",
    # Models
    "CompanyHealth",
    "CompanySignal",
    "CompanySignalStrength",
    "CompanySignalType",
    "CompanyIntelligence",
    # Constants / Enums
    "BusinessModel",
    "CompanyIntelligenceStatus",
    "CompanyStage",
    "CorporateActionType",
    "FinancialHealth",
    "GovernanceQuality",
    "GrowthProfile",
    "ListingStatus",
    "MarketCapCategory",
    "OwnershipConcentration",
    "SectorClassification",
    "ValuationStatus",
    "BIG4_FIRMS",
    # Exceptions
    "CompanyIntelligenceError",
    "CompanyAlreadyExistsError",
    "CompanyNotFoundError",
    "CompanyEngineAlreadyRunningError",
    "CompanyEngineNotInitializedError",
    "CompanyRegistryOverflowError",
    "FinancialAnalysisFailedError",
    "FinancialDataMissingError",
    "GovernanceDataMissingError",
    "OwnershipDataMissingError",
    "ProfileInvalidError",
    "ProfileNotFoundError",
    "ProfileStaleError",
    "ValuationDataMissingError",
    "ValuationInvalidError",
]

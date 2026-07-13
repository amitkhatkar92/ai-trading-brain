"""iios/investment/company/growth/__init__.py
Growth Intelligence Engine package.
"""
from iios.investment.company.growth.growth_intelligence_engine import GrowthIntelligenceEngine
from iios.investment.company.growth.growth_snapshot import GrowthSnapshot
from iios.investment.company.growth.growth_profile import (
    CAGRProfile,
    RevenueGrowthProfile,
    EarningsGrowthProfile,
    MarginGrowthProfile,
    CashflowGrowthProfile,
    GrowthDriverProfile,
    GrowthSustainabilityProfile,
    GrowthForecastProfile,
    GrowthQuality,
    GrowthIntelligenceScore,
    GrowthTrend,
    GrowthLabel,
    classify_growth,
)
from iios.investment.company.growth.forecast_assumptions import ForecastAssumptions
from iios.investment.company.growth.driver_registry import DriverPlugin, DriverRegistry

__all__ = [
    "GrowthIntelligenceEngine",
    "GrowthSnapshot",
    "CAGRProfile",
    "RevenueGrowthProfile",
    "EarningsGrowthProfile",
    "MarginGrowthProfile",
    "CashflowGrowthProfile",
    "GrowthDriverProfile",
    "GrowthSustainabilityProfile",
    "GrowthForecastProfile",
    "GrowthQuality",
    "GrowthIntelligenceScore",
    "GrowthTrend",
    "GrowthLabel",
    "classify_growth",
    "ForecastAssumptions",
    "DriverPlugin",
    "DriverRegistry",
]

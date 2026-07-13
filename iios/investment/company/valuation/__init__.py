"""iios/investment/company/valuation/__init__.py
Valuation Intelligence Engine — public API.
"""
from iios.investment.company.valuation.valuation_model import (
    ValuationModelType,
    ValuationStatus,
    ValuationBand,
    ValuationResult,
    ValuationModelPlugin,
    ValuationPluginRegistry,
)
from iios.investment.company.valuation.valuation_assumptions import (
    WACCAssumptions,
    DCFAssumptions,
    DDMAssumptions,
    RIMAssumptions,
    RelativeValuationAssumptions,
    ValuationAssumptions,
)
from iios.investment.company.valuation.valuation_statistics import (
    present_value,
    gordon_growth_terminal_value,
    weighted_average,
    percentile_rank,
    safe_mean,
    safe_median,
    safe_stdev,
    coefficient_of_variation,
    clamp,
)
from iios.investment.company.valuation.fair_value_estimate import (
    ValuationRange,
    FairValueEstimate,
    MarginOfSafetyProfile,
    classify_margin_of_safety,
)
from iios.investment.company.valuation.valuation_snapshot import (
    ValuationIntelligenceScore,
    ScenarioResult,
    ValuationSnapshot,
)
from iios.investment.company.valuation.valuation_history import ValuationHistory
from iios.investment.company.valuation.dcf_engine import DCFEngine
from iios.investment.company.valuation.dividend_discount_model import DividendDiscountModel
from iios.investment.company.valuation.residual_income_model import ResidualIncomeModel
from iios.investment.company.valuation.asset_based_model import AssetBasedModel
from iios.investment.company.valuation.multiple_engine import MultipleEngine, TradingMultiples
from iios.investment.company.valuation.relative_valuation import RelativeValuationEngine
from iios.investment.company.valuation.peer_valuation import PeerValuationEngine
from iios.investment.company.valuation.industry_benchmark import (
    get_sector_benchmarks,
    update_sector_benchmark,
    SECTOR_BENCHMARKS,
)
from iios.investment.company.valuation.margin_of_safety import MarginOfSafetyEngine
from iios.investment.company.valuation.discount_analysis import (
    DiscountAnalysis,
    DiscountAnalysisEngine,
)
from iios.investment.company.valuation.valuation_gap import (
    ValuationGap,
    compute_valuation_gap,
)
from iios.investment.company.valuation.valuation_range import build_valuation_range
from iios.investment.company.valuation.scenario_engine import ScenarioEngine
from iios.investment.company.valuation.sensitivity_analysis import (
    SensitivityAnalysisEngine,
    SensitivityAnalysisResult,
    SensitivityTable,
)
from iios.investment.company.valuation.assumption_manager import (
    AssumptionManager,
    AssumptionRecord,
)
from iios.investment.company.valuation.scenario_statistics import (
    ScenarioStatistics,
    compute_scenario_statistics,
)
from iios.investment.company.valuation.valuation_confidence import compute_valuation_confidence
from iios.investment.company.valuation.valuation_quality import (
    ValuationQuality,
    assess_valuation_quality,
)
from iios.investment.company.valuation.valuation_score import compute_valuation_score
from iios.investment.company.valuation.valuation_intelligence_engine import (
    ValuationIntelligenceEngine,
)

__all__ = [
    "ValuationModelType", "ValuationStatus", "ValuationBand", "ValuationResult",
    "ValuationModelPlugin", "ValuationPluginRegistry",
    "WACCAssumptions", "DCFAssumptions", "DDMAssumptions", "RIMAssumptions",
    "RelativeValuationAssumptions", "ValuationAssumptions",
    "present_value", "gordon_growth_terminal_value", "weighted_average",
    "percentile_rank", "safe_mean", "safe_median", "safe_stdev",
    "coefficient_of_variation", "clamp",
    "ValuationRange", "FairValueEstimate", "MarginOfSafetyProfile",
    "classify_margin_of_safety",
    "ValuationIntelligenceScore", "ScenarioResult", "ValuationSnapshot",
    "ValuationHistory",
    "DCFEngine", "DividendDiscountModel", "ResidualIncomeModel",
    "AssetBasedModel", "MultipleEngine", "TradingMultiples",
    "RelativeValuationEngine", "PeerValuationEngine",
    "MarginOfSafetyEngine", "ScenarioEngine",
    "SensitivityAnalysisEngine", "SensitivityAnalysisResult", "SensitivityTable",
    "DiscountAnalysisEngine", "DiscountAnalysis",
    "get_sector_benchmarks", "update_sector_benchmark", "SECTOR_BENCHMARKS",
    "ValuationGap", "compute_valuation_gap", "build_valuation_range",
    "AssumptionManager", "AssumptionRecord",
    "ScenarioStatistics", "compute_scenario_statistics",
    "compute_valuation_confidence",
    "ValuationQuality", "assess_valuation_quality",
    "compute_valuation_score",
    "ValuationIntelligenceEngine",
]

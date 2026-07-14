"""iios/investment/portfolio/diversification/__init__.py

Institutional Portfolio Diversification Engine — public API.
"""
# Types & constants
from iios.investment.portfolio.diversification.diversification_types import (
    AlertSeverity,
    ConcentrationLevel,
    CorrelationLevel,
    DiversificationGrade,
    DiversificationStatus,
    ExposureCategory,
    PositionData,
    RunStatus,
    TrendDirection,
    CORR_DIFFERENT,
    CORR_SAME_ASSET_CLASS,
    CORR_SAME_INDUSTRY,
    CORR_SAME_SECTOR,
    CORR_SAME_SYMBOL,
    DEFAULT_QUALITY_GATE,
    DIVERSIFICATION_PROFILE_SCHEMA_VERSION,
    DIVERSIFICATION_SNAPSHOT_SCHEMA_VERSION,
    HHI_MINIMAL_THRESHOLD,
    SECTOR_CRITICAL_THRESHOLD,
    SECTOR_WARNING_THRESHOLD,
    TOP1_WARNING_THRESHOLD,
    TOP5_WARNING_THRESHOLD,
    compute_entropy,
    compute_hhi,
    effective_n,
    hhi_to_concentration_level,
    positions_from_plan,
)

# Profile
from iios.investment.portfolio.diversification.diversification_profile import DiversificationProfile

# Snapshot / History
from iios.investment.portfolio.diversification.diversification_snapshot import (
    DiversificationHistory,
    DiversificationRecord,
)

# Statistics
from iios.investment.portfolio.diversification.diversification_statistics import (
    DiversificationRunMetric,
    DiversificationStatistics,
    DiversificationStatisticsSnapshot,
)

# Concentration
from iios.investment.portfolio.diversification.concentration_analysis import (
    ExposureConcentrationResult,
    PositionConcentrationResult,
    analyze_exposure_concentration,
    analyze_position_concentration,
)
from iios.investment.portfolio.diversification.sector_concentration import (
    SectorConcentrationReport,
    analyze_sector_concentration,
)
from iios.investment.portfolio.diversification.factor_concentration import (
    FactorExposure,
    analyze_factor_concentration,
)
from iios.investment.portfolio.diversification.concentration_engine import (
    ConcentrationEngine,
    ConcentrationReport,
)

# Correlation
from iios.investment.portfolio.diversification.correlation_matrix import (
    CorrelationMatrix,
    build_correlation_matrix,
    diversification_ratio,
    portfolio_risk_from_matrix,
)
from iios.investment.portfolio.diversification.correlation_analysis import (
    CorrelationAnalysisResult,
    HighCorrelationPair,
    analyze_correlations,
)
from iios.investment.portfolio.diversification.dependency_analysis import (
    DependencyAnalysisResult,
    DependencyCluster,
    analyze_dependencies,
)
from iios.investment.portfolio.diversification.relationship_graph import (
    RelationshipEdge,
    RelationshipGraph,
    build_relationship_graph,
)
from iios.investment.portfolio.diversification.overlap_analysis import (
    OverlapResult,
    analyze_overlap,
)
from iios.investment.portfolio.diversification.correlation_engine import (
    CorrelationEngine,
    CorrelationReport,
)

# Analysis
from iios.investment.portfolio.diversification.diversification_engine import (
    DiversificationAnalysis,
    DiversificationAnalyzer,
)

# Quality
from iios.investment.portfolio.diversification.diversification_quality import (
    DiversificationDimensionScore,
    DiversificationQualityAssessor,
    DiversificationQualityReport,
)

# Score
from iios.investment.portfolio.diversification.diversification_score import (
    DiversificationScore,
    DiversificationScoreCalculator,
    DiversificationScoreHistory,
)

# Metrics
from iios.investment.portfolio.diversification.diversification_metrics import (
    DiversificationMetrics,
    compute_diversification_metrics,
)

# Health
from iios.investment.portfolio.diversification.diversification_health import (
    DiversificationHealthCheck,
    DiversificationHealthMonitor,
    DiversificationHealthReport,
)

# Monitoring
from iios.investment.portfolio.diversification.diversification_alerts import (
    AlertThresholds,
    DiversificationAlert,
    DiversificationAlerter,
)
from iios.investment.portfolio.diversification.threshold_monitor import (
    ThresholdCheck,
    ThresholdMonitor,
    ThresholdReport,
)
from iios.investment.portfolio.diversification.diversification_trends import (
    DiversificationTrend,
    TrendAnalyzer,
    TrendsReport,
)
from iios.investment.portfolio.diversification.diversification_monitor import (
    DiversificationMonitor,
    MonitoringReport,
)

# Main engine
from iios.investment.portfolio.diversification.portfolio_diversification_engine import (
    DiversificationIntegrationRefs,
    PortfolioDiversificationEngine,
)

__all__ = [
    # types
    "AlertSeverity", "ConcentrationLevel", "CorrelationLevel", "DiversificationGrade",
    "DiversificationStatus", "ExposureCategory", "PositionData", "RunStatus", "TrendDirection",
    "DEFAULT_QUALITY_GATE", "DIVERSIFICATION_PROFILE_SCHEMA_VERSION",
    "compute_entropy", "compute_hhi", "effective_n", "hhi_to_concentration_level",
    "positions_from_plan",
    # profile
    "DiversificationProfile",
    # history
    "DiversificationHistory", "DiversificationRecord",
    # statistics
    "DiversificationRunMetric", "DiversificationStatistics", "DiversificationStatisticsSnapshot",
    # concentration
    "ExposureConcentrationResult", "PositionConcentrationResult",
    "SectorConcentrationReport", "FactorExposure",
    "ConcentrationEngine", "ConcentrationReport",
    "analyze_position_concentration", "analyze_sector_concentration", "analyze_factor_concentration",
    # correlation
    "CorrelationMatrix", "build_correlation_matrix", "diversification_ratio",
    "CorrelationAnalysisResult", "HighCorrelationPair",
    "DependencyAnalysisResult", "DependencyCluster",
    "RelationshipEdge", "RelationshipGraph",
    "OverlapResult", "analyze_overlap",
    "CorrelationEngine", "CorrelationReport",
    # analysis
    "DiversificationAnalysis", "DiversificationAnalyzer",
    # quality
    "DiversificationDimensionScore", "DiversificationQualityAssessor", "DiversificationQualityReport",
    # score
    "DiversificationScore", "DiversificationScoreCalculator", "DiversificationScoreHistory",
    # metrics
    "DiversificationMetrics", "compute_diversification_metrics",
    # health
    "DiversificationHealthCheck", "DiversificationHealthMonitor", "DiversificationHealthReport",
    # monitoring
    "AlertThresholds", "DiversificationAlert", "DiversificationAlerter",
    "ThresholdCheck", "ThresholdMonitor", "ThresholdReport",
    "DiversificationTrend", "TrendAnalyzer", "TrendsReport",
    "DiversificationMonitor", "MonitoringReport",
    # engine
    "DiversificationIntegrationRefs", "PortfolioDiversificationEngine",
]

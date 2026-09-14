"""enterprise_ai_platform/investment/market/trend/__init__.py
Public API for the Institutional Trend Intelligence package.
"""
from __future__ import annotations

from enterprise_ai_platform.investment.market.trend.models import (
    TrendStage,
    TrendEventType,
    TrendTransitionType,
    ImpulseQuality,
    CorrectionQuality,
    TrendLegMetrics,
    TrendMomentumState,
    TrendQualityMetrics,
    TrendScore,
    StrategyReadiness,
    TrendEventRecord,
    TrendTransitionRecord,
    TrendIntelligenceSnapshot,
)

from enterprise_ai_platform.investment.market.trend.trend_state import TrendIntelligenceState
from enterprise_ai_platform.investment.market.trend.trend_tracker import TrendTracker
from enterprise_ai_platform.investment.market.trend.trend_history import TrendHistory
from enterprise_ai_platform.investment.market.trend.trend_snapshot import TrendSnapshotBuilder

from enterprise_ai_platform.investment.market.trend.trend_quality import TrendQualityAnalyzer
from enterprise_ai_platform.investment.market.trend.trend_strength import TrendStrengthCalculator
from enterprise_ai_platform.investment.market.trend.trend_stability import TrendStabilityCalculator
from enterprise_ai_platform.investment.market.trend.trend_persistence import TrendPersistenceCalculator
from enterprise_ai_platform.investment.market.trend.trend_velocity import TrendVelocityCalculator
from enterprise_ai_platform.investment.market.trend.trend_acceleration import TrendAccelerationAnalyzer
from enterprise_ai_platform.investment.market.trend.trend_deceleration import TrendDecelerationDetector
from enterprise_ai_platform.investment.market.trend.trend_momentum import TrendMomentumAnalyzer

from enterprise_ai_platform.investment.market.trend.trend_stage import (
    STAGE_ORDER,
    STAGE_LIFECYCLE_SCORES,
    stage_index,
    is_advancing,
    is_declining,
)

from enterprise_ai_platform.investment.market.trend.trend_lifecycle import TrendLifecycleDetector
from enterprise_ai_platform.investment.market.trend.trend_transition import TrendTransitionDetector
from enterprise_ai_platform.investment.market.trend.trend_confidence import TrendConfidenceCalculator
from enterprise_ai_platform.investment.market.trend.trend_score import TrendScorer
from enterprise_ai_platform.investment.market.trend.trend_statistics import TrendStatistics, TrendStageStats

from enterprise_ai_platform.investment.market.trend.trend_permissions import (
    TrendStrategyType,
    STAGE_PERMISSIONS,
    best_approach,
)

from enterprise_ai_platform.investment.market.trend.trend_constraints import (
    TrendConstraint,
    TREND_CONSTRAINTS,
    TrendConstraintEngine,
)

from enterprise_ai_platform.investment.market.trend.trend_strategy_mapper import TrendStrategyMapper
from enterprise_ai_platform.investment.market.trend.trend_intelligence_engine import (
    InstitutionalTrendIntelligenceEngine,
)

__all__ = [
    # models
    "TrendStage",
    "TrendEventType",
    "TrendTransitionType",
    "ImpulseQuality",
    "CorrectionQuality",
    "TrendLegMetrics",
    "TrendMomentumState",
    "TrendQualityMetrics",
    "TrendScore",
    "StrategyReadiness",
    "TrendEventRecord",
    "TrendTransitionRecord",
    "TrendIntelligenceSnapshot",
    # state
    "TrendIntelligenceState",
    # tracker / history / builder
    "TrendTracker",
    "TrendHistory",
    "TrendSnapshotBuilder",
    # analyzers
    "TrendQualityAnalyzer",
    "TrendStrengthCalculator",
    "TrendStabilityCalculator",
    "TrendPersistenceCalculator",
    "TrendVelocityCalculator",
    "TrendAccelerationAnalyzer",
    "TrendDecelerationDetector",
    "TrendMomentumAnalyzer",
    # stage
    "STAGE_ORDER",
    "STAGE_LIFECYCLE_SCORES",
    "stage_index",
    "is_advancing",
    "is_declining",
    # lifecycle / transition
    "TrendLifecycleDetector",
    "TrendTransitionDetector",
    # confidence / score / stats
    "TrendConfidenceCalculator",
    "TrendScorer",
    "TrendStatistics",
    "TrendStageStats",
    # permissions / constraints / mapper
    "TrendStrategyType",
    "STAGE_PERMISSIONS",
    "best_approach",
    "TrendConstraint",
    "TREND_CONSTRAINTS",
    "TrendConstraintEngine",
    "TrendStrategyMapper",
    # engine
    "InstitutionalTrendIntelligenceEngine",
]

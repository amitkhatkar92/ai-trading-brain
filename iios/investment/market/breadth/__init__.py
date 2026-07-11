"""iios/investment/market/breadth — Institutional Market Breadth Intelligence Engine."""
from iios.investment.market.breadth.models import (
    BreadthConfidenceScore,
    BreadthData,
    BreadthEvent,
    BreadthEventType,
    BreadthIntelligenceSnapshot,
    BreadthMetricValue,
    BreadthRegimeSnapshot,
    BreadthRegimeType,
    BreadthTrend,
    DivergenceSignal,
    DivergenceType,
    HealthTrend,
    MarketCapTier,
    MarketHealthSnapshot,
    ParticipationSnapshot,
    SecurityObservation,
    UniverseSnapshot,
)
from iios.investment.market.breadth.breadth_metric import BreadthMetric
from iios.investment.market.breadth.metric_registry import MetricRegistry
from iios.investment.market.breadth.advance_decline_metric import AdvanceDeclineMetric
from iios.investment.market.breadth.above_ma_metric import AboveMa20Metric, AboveMa50Metric
from iios.investment.market.breadth.new_high_low_metric import NewHighLowMetric
from iios.investment.market.breadth.participation_rate_metric import ParticipationRateMetric
from iios.investment.market.breadth.market_breadth_engine import InstitutionalMarketBreadthEngine

__all__ = [
    # Models
    "SecurityObservation",
    "UniverseSnapshot",
    "BreadthMetricValue",
    "BreadthData",
    "ParticipationSnapshot",
    "MarketHealthSnapshot",
    "DivergenceSignal",
    "BreadthRegimeSnapshot",
    "BreadthConfidenceScore",
    "BreadthEvent",
    "BreadthIntelligenceSnapshot",
    # Enums
    "BreadthRegimeType",
    "BreadthEventType",
    "DivergenceType",
    "MarketCapTier",
    "BreadthTrend",
    "HealthTrend",
    # Protocols / Registries
    "BreadthMetric",
    "MetricRegistry",
    # Built-in metrics
    "AdvanceDeclineMetric",
    "AboveMa20Metric",
    "AboveMa50Metric",
    "NewHighLowMetric",
    "ParticipationRateMetric",
    # Primary engine
    "InstitutionalMarketBreadthEngine",
]


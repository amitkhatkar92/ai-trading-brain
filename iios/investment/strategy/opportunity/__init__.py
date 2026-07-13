"""iios/investment/strategy/opportunity/__init__.py"""
# ── Input types (consumed from intelligence engines) ─────────────────────────
from iios.investment.strategy.opportunity.market_opportunity import (
    MarketOpportunity, OpportunityType, MarketRegime, VolatilityRegime, Timeframe
)
from iios.investment.strategy.opportunity.company_opportunity import (
    CompanyOpportunity, CompanyOpportunityType, RiskLevel, MarketCapCategory
)
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate

# ── Core output type ──────────────────────────────────────────────────────────
from iios.investment.strategy.opportunity.strategy_opportunity import (
    StrategyOpportunity, OpportunityState, StateTransitionRecord
)

# ── Events ────────────────────────────────────────────────────────────────────
from iios.investment.strategy.opportunity.opportunity_event import (
    OpportunityEvent, EventType, EventBus
)

# ── Matching ──────────────────────────────────────────────────────────────────
from iios.investment.strategy.opportunity.matching_profile import (
    MatchingProfile, DEFAULT_PROFILE, MOMENTUM_PROFILE, CONSERVATIVE_PROFILE
)
from iios.investment.strategy.opportunity.strategy_matcher import (
    StrategyMatcher, MatchResult
)
from iios.investment.strategy.opportunity.matching_engine import MatchingEngine
from iios.investment.strategy.opportunity.matching_history import MatchingHistory

# ── Suitability ───────────────────────────────────────────────────────────────
from iios.investment.strategy.opportunity.constraint_engine import (
    ConstraintEngine, ConstraintResult
)
from iios.investment.strategy.opportunity.compatibility_engine import (
    CompatibilityEngine, CompatibilityScores
)
from iios.investment.strategy.opportunity.strategy_suitability import (
    SuitabilityEngine, SuitabilityResult
)

# ── Ranking ───────────────────────────────────────────────────────────────────
from iios.investment.strategy.opportunity.ranking_score import RankingScore
from iios.investment.strategy.opportunity.ranking_engine import RankingEngine
from iios.investment.strategy.opportunity.ranking_history import RankingHistory
from iios.investment.strategy.opportunity.strategy_ranking import (
    RankedOpportunity, StrategyRanking
)

# ── Lifecycle ─────────────────────────────────────────────────────────────────
from iios.investment.strategy.opportunity.lifecycle_engine import LifecycleEngine
from iios.investment.strategy.opportunity.lifecycle_history import (
    LifecycleHistory, LifecycleEvent
)

# ── Recommendation ────────────────────────────────────────────────────────────
from iios.investment.strategy.opportunity.evidence_collector import (
    Evidence, EvidenceBundle, EvidenceCollector
)
from iios.investment.strategy.opportunity.reason_generator import ReasonGenerator
from iios.investment.strategy.opportunity.recommendation_summary import RecommendationSummary
from iios.investment.strategy.opportunity.recommendation_engine import RecommendationEngine

# ── Monitoring ────────────────────────────────────────────────────────────────
from iios.investment.strategy.opportunity.change_detector import (
    ChangeDetector, ChangeEvent
)
from iios.investment.strategy.opportunity.strategy_alerts import (
    StrategyAlert, AlertSeverity, AlertType, AlertRegistry
)
from iios.investment.strategy.opportunity.priority_monitor import PriorityMonitor
from iios.investment.strategy.opportunity.opportunity_monitor import OpportunityMonitor

# ── Main engine ───────────────────────────────────────────────────────────────
from iios.investment.strategy.opportunity.strategy_opportunity_engine import (
    StrategyOpportunityEngine
)

__all__ = [
    # Input types
    "MarketOpportunity", "OpportunityType", "MarketRegime",
    "VolatilityRegime", "Timeframe",
    "CompanyOpportunity", "CompanyOpportunityType", "RiskLevel", "MarketCapCategory",
    "StrategyCandidate",
    # Core output
    "StrategyOpportunity", "OpportunityState", "StateTransitionRecord",
    # Events
    "OpportunityEvent", "EventType", "EventBus",
    # Matching
    "MatchingProfile", "DEFAULT_PROFILE", "MOMENTUM_PROFILE", "CONSERVATIVE_PROFILE",
    "StrategyMatcher", "MatchResult",
    "MatchingEngine", "MatchingHistory",
    # Suitability
    "ConstraintEngine", "ConstraintResult",
    "CompatibilityEngine", "CompatibilityScores",
    "SuitabilityEngine", "SuitabilityResult",
    # Ranking
    "RankingScore", "RankingEngine", "RankingHistory",
    "RankedOpportunity", "StrategyRanking",
    # Lifecycle
    "LifecycleEngine", "LifecycleHistory", "LifecycleEvent",
    # Recommendation
    "Evidence", "EvidenceBundle", "EvidenceCollector",
    "ReasonGenerator", "RecommendationSummary", "RecommendationEngine",
    # Monitoring
    "ChangeDetector", "ChangeEvent",
    "StrategyAlert", "AlertSeverity", "AlertType", "AlertRegistry",
    "PriorityMonitor", "OpportunityMonitor",
    # Engine
    "StrategyOpportunityEngine",
]

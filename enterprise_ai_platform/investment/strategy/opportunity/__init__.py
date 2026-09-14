"""enterprise_ai_platform/investment/strategy/opportunity/__init__.py"""
# ── Input types (consumed from intelligence engines) ─────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.market_opportunity import (
    MarketOpportunity, OpportunityType, MarketRegime, VolatilityRegime, Timeframe
)
from enterprise_ai_platform.investment.strategy.opportunity.company_opportunity import (
    CompanyOpportunity, CompanyOpportunityType, RiskLevel, MarketCapCategory
)
from enterprise_ai_platform.investment.strategy.opportunity.strategy_candidate import StrategyCandidate

# ── Core output type ──────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.strategy_opportunity import (
    StrategyOpportunity, OpportunityState, StateTransitionRecord
)

# ── Events ────────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.opportunity_event import (
    OpportunityEvent, EventType, EventBus
)

# ── Matching ──────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.matching_profile import (
    MatchingProfile, DEFAULT_PROFILE, MOMENTUM_PROFILE, CONSERVATIVE_PROFILE
)
from enterprise_ai_platform.investment.strategy.opportunity.strategy_matcher import (
    StrategyMatcher, MatchResult
)
from enterprise_ai_platform.investment.strategy.opportunity.matching_engine import MatchingEngine
from enterprise_ai_platform.investment.strategy.opportunity.matching_history import MatchingHistory

# ── Suitability ───────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.constraint_engine import (
    ConstraintEngine, ConstraintResult
)
from enterprise_ai_platform.investment.strategy.opportunity.compatibility_engine import (
    CompatibilityEngine, CompatibilityScores
)
from enterprise_ai_platform.investment.strategy.opportunity.strategy_suitability import (
    SuitabilityEngine, SuitabilityResult
)

# ── Ranking ───────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.ranking_score import RankingScore
from enterprise_ai_platform.investment.strategy.opportunity.ranking_engine import RankingEngine
from enterprise_ai_platform.investment.strategy.opportunity.ranking_history import RankingHistory
from enterprise_ai_platform.investment.strategy.opportunity.strategy_ranking import (
    RankedOpportunity, StrategyRanking
)

# ── Lifecycle ─────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.lifecycle_engine import LifecycleEngine
from enterprise_ai_platform.investment.strategy.opportunity.lifecycle_history import (
    LifecycleHistory, LifecycleEvent
)

# ── Recommendation ────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.evidence_collector import (
    Evidence, EvidenceBundle, EvidenceCollector
)
from enterprise_ai_platform.investment.strategy.opportunity.reason_generator import ReasonGenerator
from enterprise_ai_platform.investment.strategy.opportunity.recommendation_summary import RecommendationSummary
from enterprise_ai_platform.investment.strategy.opportunity.recommendation_engine import RecommendationEngine

# ── Monitoring ────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.change_detector import (
    ChangeDetector, ChangeEvent
)
from enterprise_ai_platform.investment.strategy.opportunity.strategy_alerts import (
    StrategyAlert, AlertSeverity, AlertType, AlertRegistry
)
from enterprise_ai_platform.investment.strategy.opportunity.priority_monitor import PriorityMonitor
from enterprise_ai_platform.investment.strategy.opportunity.opportunity_monitor import OpportunityMonitor

# ── Main engine ───────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.opportunity.strategy_opportunity_engine import (
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

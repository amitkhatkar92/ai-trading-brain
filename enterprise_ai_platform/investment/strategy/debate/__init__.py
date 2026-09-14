"""enterprise_ai_platform/investment/strategy/debate/__init__.py
Public API for the Institutional Multi-Agent Strategy Debate Engine.
"""

# ── Core enumerations ─────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.debate_constants import (
    ArgumentType,
    ConsensusLevel,
    DebateEventType,
    DebatePhase,
    DebateStatus,
    EvidenceReliability,
    EvidenceSource,
    EvidenceWeight,
    ParticipantRole,
    RebuttalType,
    VoteOutcome,
    VotingMechanism,
)

# ── Event bus ─────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.debate_events import (
    DebateEvent,
    DebateEventBus,
)

# ── Context and state ─────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.debate_context import (
    DebateContext,
    MarketSnapshot,
    OpportunityDebateInput,
    StrategyDebateInput,
)
from enterprise_ai_platform.investment.strategy.debate.debate_state import DebateState, DebateStateError

# ── Session ───────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.debate_session import DebateSession
from enterprise_ai_platform.investment.strategy.debate.debate_history import DebateHistory

# ── Arguments and Rebuttals ───────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.argument_manager import (
    Argument,
    ArgumentManager,
    Rebuttal,
    make_argument,
    make_rebuttal,
)

# ── Evidence ──────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.evidence_registry import (
    Evidence,
    EvidenceRegistry,
    make_evidence,
)
from enterprise_ai_platform.investment.strategy.debate.evidence_score import EvidenceScore, compute_evidence_score
from enterprise_ai_platform.investment.strategy.debate.evidence_validator import EvidenceValidator, ValidationResult
from enterprise_ai_platform.investment.strategy.debate.evidence_collector import (
    EvidenceCollector,
    CollectionResult,
    MarketIntelligencePort,
    CompanyIntelligencePort,
    RiskIntelligencePort,
    LearningEnginePort,
    KnowledgeLayerPort,
)

# ── Participants ──────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.participant_profile import (
    ParticipantProfile,
    build_profile,
    DEFAULT_WEIGHTS,
)
from enterprise_ai_platform.investment.strategy.debate.participant_roles import (
    BaseDebateAgent,
    CompanyIntelligenceAgent,
    ExecutionAnalystAgent,
    FundamentalAnalystAgent,
    MacroAnalystAgent,
    MarketIntelligenceAgent,
    PortfolioAnalystAgent,
    ROLE_CLASS_MAP,
    RiskAnalystAgent,
    SentimentAnalystAgent,
    StrategyLearningAgent,
    TechnicalAnalystAgent,
)
from enterprise_ai_platform.investment.strategy.debate.agent_registry import (
    AgentRegistry,
    create_default_registry,
)

# ── Voting and Consensus ──────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.voting_engine import (
    Vote,
    VotingEngine,
    VotingResult,
    make_vote,
)
from enterprise_ai_platform.investment.strategy.debate.agreement_analysis import (
    AgreementAnalysis,
    AgreementMetrics,
)
from enterprise_ai_platform.investment.strategy.debate.consensus_engine import (
    ConsensusEngine,
    ConsensusPolicy,
    ConsensusResult,
)
from enterprise_ai_platform.investment.strategy.debate.consensus_statistics import (
    ConsensusStatistics,
    ConsensusStatisticsTracker,
)

# ── Reports ───────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.recommendation_summary import (
    RecommendationSummary,
    build_recommendation_summary,
)
from enterprise_ai_platform.investment.strategy.debate.debate_explanation import (
    DebateExplanation,
    DebateExplainer,
)
from enterprise_ai_platform.investment.strategy.debate.executive_summary import (
    ExecutiveSummary,
    ExecutiveSummaryBuilder,
)
from enterprise_ai_platform.investment.strategy.debate.debate_report import (
    DebateReport,
    build_report,
)

# ── Orchestration ─────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.debate_orchestrator import (
    DebateOrchestrator,
    OrchestratorConfig,
)

# ── Engine (main entry point) ─────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.debate.strategy_debate_engine import StrategyDebateEngine


__all__ = [
    # Enums
    "ArgumentType",
    "ConsensusLevel",
    "DebateEventType",
    "DebatePhase",
    "DebateStatus",
    "EvidenceReliability",
    "EvidenceSource",
    "EvidenceWeight",
    "ParticipantRole",
    "RebuttalType",
    "VoteOutcome",
    "VotingMechanism",
    # Events
    "DebateEvent",
    "DebateEventBus",
    # Context
    "DebateContext",
    "MarketSnapshot",
    "OpportunityDebateInput",
    "StrategyDebateInput",
    # State
    "DebateState",
    "DebateStateError",
    # Session
    "DebateSession",
    "DebateHistory",
    # Arguments
    "Argument",
    "ArgumentManager",
    "Rebuttal",
    "make_argument",
    "make_rebuttal",
    # Evidence
    "Evidence",
    "EvidenceRegistry",
    "EvidenceScore",
    "EvidenceValidator",
    "ValidationResult",
    "EvidenceCollector",
    "CollectionResult",
    "MarketIntelligencePort",
    "CompanyIntelligencePort",
    "RiskIntelligencePort",
    "LearningEnginePort",
    "KnowledgeLayerPort",
    "make_evidence",
    "compute_evidence_score",
    # Participants
    "BaseDebateAgent",
    "ParticipantProfile",
    "build_profile",
    "DEFAULT_WEIGHTS",
    "AgentRegistry",
    "create_default_registry",
    "ROLE_CLASS_MAP",
    "TechnicalAnalystAgent",
    "FundamentalAnalystAgent",
    "MarketIntelligenceAgent",
    "CompanyIntelligenceAgent",
    "MacroAnalystAgent",
    "RiskAnalystAgent",
    "PortfolioAnalystAgent",
    "ExecutionAnalystAgent",
    "SentimentAnalystAgent",
    "StrategyLearningAgent",
    # Voting & Consensus
    "Vote",
    "VotingEngine",
    "VotingResult",
    "make_vote",
    "AgreementAnalysis",
    "AgreementMetrics",
    "ConsensusEngine",
    "ConsensusPolicy",
    "ConsensusResult",
    "ConsensusStatistics",
    "ConsensusStatisticsTracker",
    # Reports
    "RecommendationSummary",
    "build_recommendation_summary",
    "DebateExplanation",
    "DebateExplainer",
    "ExecutiveSummary",
    "ExecutiveSummaryBuilder",
    "DebateReport",
    "build_report",
    # Orchestration
    "DebateOrchestrator",
    "OrchestratorConfig",
    # Engine
    "StrategyDebateEngine",
]

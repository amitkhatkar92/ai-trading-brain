"""iios/investment/decision/committee/__init__.py
Public surface of the Institutional Multi-Agent Decision Committee Engine.
"""
from iios.investment.decision.committee.challenge_engine import (
    Challenge,
    ChallengeEngine,
)
from iios.investment.decision.committee.committee_confidence import CommitteeConfidenceCalculator
from iios.investment.decision.committee.committee_constants import (
    COMMITTEE_HISTORY_WINDOW,
    CHALLENGE_SEVERITY_THRESHOLD,
    CONFIDENCE_MIN_FOR_SUPPORT,
    DEFAULT_CHAIR_WEIGHT,
    DEFAULT_MEMBER_WEIGHT,
    DOMAIN_OPPOSE_THRESHOLD,
    DOMAIN_SUPPORT_THRESHOLD,
    MIN_EVIDENCE_ITEMS_FOR_DELIBERATION,
    MIN_MEMBERS_FOR_QUORUM,
    RISK_MAX_FOR_SUPPORT,
    ChallengeType,
    CommitteeGrade,
    CommitteePosition,
    CommitteeStatus,
    ConsensusLevel,
    RoundType,
    SessionState,
    SpecialistType,
    VoteType,
)
from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_findings import (
    CommitteeFindings,
    CommitteeFindingsBuilder,
)
from iios.investment.decision.committee.committee_health import (
    CommitteeHealthMonitor,
    CommitteeHealthReport,
)
from iios.investment.decision.committee.committee_history import CommitteeHistory
from iios.investment.decision.committee.committee_member import (
    CommitteeMember,
    ComplianceMember,
    CompanyIntelligenceMember,
    CustomSpecialistMember,
    FundamentalAnalystMember,
    MacroIntelligenceMember,
    MarketIntelligenceMember,
    MemberOpinion,
    PortfolioIntelligenceMember,
    QuantitativeAnalystMember,
    ResearchMember,
    RiskIntelligenceMember,
    SentimentAnalystMember,
    StrategyIntelligenceMember,
    TechnicalAnalystMember,
    create_member,
)
from iios.investment.decision.committee.committee_orchestrator import CommitteeOrchestrator
from iios.investment.decision.committee.committee_quality import CommitteeQualityEvaluator
from iios.investment.decision.committee.committee_recommendations import (
    CommitteeStance,
    build_committee_stance,
)
from iios.investment.decision.committee.committee_report import (
    CommitteeReport,
    build_committee_report,
)
from iios.investment.decision.committee.committee_round import RoundResult
from iios.investment.decision.committee.committee_session import CommitteeSession
from iios.investment.decision.committee.committee_state import CommitteeState
from iios.investment.decision.committee.committee_statistics import (
    CommitteeStatistics,
    CommitteeStatisticsTracker,
)
from iios.investment.decision.committee.decision_committee_engine import DecisionCommitteeEngine
from iios.investment.decision.committee.discussion_engine import DiscussionEngine
from iios.investment.decision.committee.executive_summary import ExecutiveSummaryBuilder
from iios.investment.decision.committee.member_profiles import (
    SPECIALIST_PROFILES,
    SpecialistProfile,
    get_profile,
)
from iios.investment.decision.committee.member_registry import (
    DEFAULT_COMMITTEE_SPEC,
    MemberRegistry,
)
from iios.investment.decision.committee.member_roles import (
    DEFAULT_SPECIALIST_ROLES,
    MemberRole,
    RolePolicy,
    ROLE_POLICIES,
    get_role_policy,
)
from iios.investment.decision.committee.minority_reports import (
    MinorityReport,
    MinorityReportBuilder,
)
from iios.investment.decision.committee.vote_registry import CastVote, VoteRegistry
from iios.investment.decision.committee.voting_engine import VotingEngine
from iios.investment.decision.committee.weighted_voting import VoteSummary, WeightedVoting

__all__ = [
    # Main engine
    "DecisionCommitteeEngine",
    # Session
    "CommitteeSession", "CommitteeContext", "CommitteeState",
    "CommitteeOrchestrator",
    # Members
    "CommitteeMember", "MemberOpinion", "create_member",
    "MarketIntelligenceMember", "CompanyIntelligenceMember",
    "StrategyIntelligenceMember", "RiskIntelligenceMember",
    "PortfolioIntelligenceMember", "MacroIntelligenceMember",
    "QuantitativeAnalystMember", "FundamentalAnalystMember",
    "TechnicalAnalystMember", "SentimentAnalystMember",
    "ComplianceMember", "ResearchMember", "CustomSpecialistMember",
    # Registry / profiles / roles
    "MemberRegistry", "DEFAULT_COMMITTEE_SPEC",
    "SpecialistProfile", "SPECIALIST_PROFILES", "get_profile",
    "MemberRole", "RolePolicy", "ROLE_POLICIES",
    "DEFAULT_SPECIALIST_ROLES", "get_role_policy",
    # Discussion / challenge
    "DiscussionEngine", "ChallengeEngine", "Challenge",
    # Voting
    "VotingEngine", "VoteRegistry", "CastVote",
    "WeightedVoting", "VoteSummary",
    "MinorityReport", "MinorityReportBuilder",
    # Report
    "CommitteeReport", "build_committee_report",
    "CommitteeFindings", "CommitteeFindingsBuilder",
    "CommitteeStance", "build_committee_stance",
    "ExecutiveSummaryBuilder",
    "RoundResult",
    # Quality / stats / health
    "CommitteeConfidenceCalculator",
    "CommitteeQualityEvaluator",
    "CommitteeStatistics", "CommitteeStatisticsTracker",
    "CommitteeHealthMonitor", "CommitteeHealthReport",
    "CommitteeHistory",
    # Constants / enums
    "CommitteePosition", "ConsensusLevel", "VoteType",
    "SessionState", "SpecialistType", "RoundType", "ChallengeType",
    "CommitteeGrade", "CommitteeStatus",
    "MIN_MEMBERS_FOR_QUORUM", "MIN_EVIDENCE_ITEMS_FOR_DELIBERATION",
    "DOMAIN_SUPPORT_THRESHOLD", "DOMAIN_OPPOSE_THRESHOLD",
    "CONFIDENCE_MIN_FOR_SUPPORT", "RISK_MAX_FOR_SUPPORT",
    "CHALLENGE_SEVERITY_THRESHOLD", "COMMITTEE_HISTORY_WINDOW",
    "DEFAULT_CHAIR_WEIGHT", "DEFAULT_MEMBER_WEIGHT",
]

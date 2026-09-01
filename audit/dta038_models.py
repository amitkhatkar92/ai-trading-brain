"""
DTA-038 data models — pure stdlib, no trading-pipeline imports.

All models are append-only research artefacts.
NEVER import these to modify trading decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enumerations ───────────────────────────────────────────────────────────

class StageStatus(str, Enum):
    PENDING  = "PENDING"
    PASSED   = "PASSED"
    REJECTED = "REJECTED"
    UNKNOWN  = "UNKNOWN"   # stage not yet reached after a restart


class HypothesisStatus(str, Enum):
    OBSERVED                = "OBSERVED"
    INVESTIGATING           = "INVESTIGATING"
    HYPOTHESIS              = "HYPOTHESIS"
    VALIDATION_REQUIRED     = "VALIDATION_REQUIRED"
    VALIDATED               = "VALIDATED"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    APPROVED                = "APPROVED"
    REJECTED_HYP            = "REJECTED_HYP"
    DEPLOYED                = "DEPLOYED"


class AnomalyKind(str, Enum):
    ALL_REJECTED_AT_SAME_STAGE   = "ALL_REJECTED_AT_SAME_STAGE"
    NEAR_MISS_THRESHOLD          = "NEAR_MISS_THRESHOLD"
    ZERO_SIGNALS_GENERATED       = "ZERO_SIGNALS_GENERATED"
    ALL_SIGNALS_SINGLE_DIRECTION = "ALL_SIGNALS_SINGLE_DIRECTION"
    HIGH_REJECTION_RATE          = "HIGH_REJECTION_RATE"
    STRATEGY_BOTTLENECK          = "STRATEGY_BOTTLENECK"
    RESTART_GAP                  = "RESTART_GAP"
    REPEATED_SYMBOL_REJECTION    = "REPEATED_SYMBOL_REJECTION"


# ── Stage-level record ─────────────────────────────────────────────────────

@dataclass
class StageResult:
    stage: str                         # SCANNER|STRATEGY|CRE|RISK|GUARDIAN|DEBATE|EXECUTION
    status: StageStatus
    timestamp_utc: str                 # ISO-8601
    details: Dict[str, Any] = field(default_factory=dict)
    rejection_reason: Optional[str] = None


# ── Per-candidate lifecycle trace ──────────────────────────────────────────

@dataclass
class CandidateTrace:
    trace_id: str           # DTA038:<YYYYMMDD>:<cycle_id>:<SYMBOL>:<DIR>
    trading_date: str       # YYYY-MM-DD
    cycle_id: str           # YYYYMMDD_HHMM
    symbol: str
    direction: str          # BUY | SELL
    entry_price: float
    scanner_rsi: float = 0.0
    scanner_volume_ratio: float = 0.0
    scanner_score: float = 0.0
    scanner_regime: str = ""
    stages: List[StageResult] = field(default_factory=list)
    final_outcome: Optional[str] = None   # EXECUTED | REJECTED_AT_<STAGE> | PENDING
    anomaly_flags: List[str] = field(default_factory=list)

    def stage_status(self, stage: str) -> StageStatus:
        for s in self.stages:
            if s.stage == stage:
                return s.status
        return StageStatus.UNKNOWN

    def last_known_stage(self) -> Optional[str]:
        if self.stages:
            return self.stages[-1].stage
        return None


# ── Per-cycle aggregate ────────────────────────────────────────────────────

@dataclass
class CycleAudit:
    cycle_id: str
    trading_date: str
    start_ts: str
    end_ts: Optional[str] = None
    regime: str = ""
    vix: float = 0.0
    signals_generated: int = 0
    strategy_passed: int = 0
    cre_passed: int = 0
    risk_passed: int = 0
    guardian_passed: int = 0
    debate_input: int = 0
    executed: int = 0
    stage_drop_map: Dict[str, int] = field(default_factory=dict)
    anomaly_flags: List[str] = field(default_factory=list)


# ── Hypothesis ─────────────────────────────────────────────────────────────

@dataclass
class Hypothesis:
    hyp_id: str              # HYP:<YYYYMMDD>:<HHMMSS>:<seq>
    created_ts: str
    status: HypothesisStatus
    title: str
    observation: str
    proposed_change: str
    evidence_count: int
    confidence_pct: float
    last_updated_ts: str
    tags: List[str] = field(default_factory=list)
    human_verdict: Optional[str] = None
    supporting_cycles: List[str] = field(default_factory=list)


# ── Self-questioning answer ────────────────────────────────────────────────

@dataclass
class CycleQuestion:
    question: str
    answer: str
    severity: str   # INFO | WARN | ALERT
    tags: List[str] = field(default_factory=list)


@dataclass
class SelfQuestioningReport:
    cycle_id: str
    trading_date: str
    generated_ts: str
    questions: List[CycleQuestion] = field(default_factory=list)
    anomalies_detected: int = 0
    hypotheses_raised: int = 0
    top_finding: str = ""


# ── Anomaly ────────────────────────────────────────────────────────────────

@dataclass
class AnomalyRecord:
    anomaly_id: str         # ANO:<YYYYMMDD>:<HHMMSS>
    detected_ts: str
    kind: AnomalyKind
    cycle_id: str
    description: str
    affected_symbols: List[str] = field(default_factory=list)
    severity: str = "WARN"   # INFO | WARN | ALERT
    hypothesis_raised: bool = False

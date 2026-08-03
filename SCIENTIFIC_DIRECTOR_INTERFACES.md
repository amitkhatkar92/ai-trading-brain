# SCIENTIFIC DIRECTOR — INTERFACES
## Frozen Interface Contracts (Design Only — No Implementation)

**Status:** FROZEN  
**Phase:** 0 — Architecture Design  
**Date:** 2026-08-03  
**Note:** These are interface contracts. No implementation code. Implementations are Phase 1+.

---

## Interface Overview

```
┌──────────────────────────────────────────────────────┐
│              ScientificDirector                       │
│         (central coordinator — uses all 7)           │
└──┬──────────┬──────────┬──────────┬──────────┬───────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
Knowledge  GapDet-  Hypothesis  StudyPlan  Research
Provider   ector    Provider    ner        Coordinator
                                               │
                         ┌─────────────────────┘
                         ▼
                   Evidence      Roadmap
                   Validator     Manager
```

---

## Interface 1 — KnowledgeProvider

**Purpose:**  
Provides unified read-only access to all platform knowledge stores. Hides file paths, format details, and JSON schema from the rest of ARS. If the underlying storage format changes, only KnowledgeProvider changes — all other components are insulated.

**Dependencies:**  
- `data/learning_db.json`  
- `data/strategy_performance.json`  
- `data/discovered_edges.json`  
- `data/regime_probability_history.json`  
- `data/evolved_strategies.json` (read-only)  
- `data/study*.json`, `data/re*.json`  
- `data/ars_knowledge_base.json`

**Inputs:** None (reads from disk at call time)  
**Outputs:** Typed snapshots — see below

```python
class KnowledgeProvider(ABC):

    def get_strategy_performance(self) -> StrategyPerformanceSnapshot:
        """
        Returns per-strategy metrics: win_rate, expectancy, sample_count, 
        regime_breakdown, last_updated.
        Source: data/strategy_performance.json
        """

    def get_regime_win_rates(self) -> Dict[str, RegimeStats]:
        """
        Returns win rate, sample count, avg_r per regime label.
        Source: data/learning_db.json (regime_performance section)
        """

    def get_discovered_edges(self) -> List[DiscoveredEdge]:
        """
        Returns all active and inactive edges.
        Source: data/discovered_edges.json
        """

    def get_learning_history(self, days: int = 30) -> List[LearningRecord]:
        """
        Returns last N days of EOD learning records.
        Source: data/learning_db.json (history section)
        """

    def get_study_result(self, study_id: str) -> Optional[StudyResult]:
        """
        Loads and validates a specific study result JSON.
        Source: data/{study_id}_results.json
        """

    def get_all_study_ids(self) -> List[str]:
        """
        Returns IDs of all completed studies (study002, re001a, study002a, ars_*).
        Source: filesystem scan of data/*.json
        """

    def get_ars_knowledge_base(self) -> KnowledgeBase:
        """
        Returns current synthesised knowledge base.
        Source: data/ars_knowledge_base.json
        """

    def get_snapshot(self) -> KnowledgeSnapshot:
        """
        Returns a single immutable snapshot aggregating all above.
        Used as the entry point for gap detection.
        """
```

---

## Interface 2 — GapDetector

**Purpose:**  
Identifies specific gaps in platform knowledge from a KnowledgeSnapshot. Returns typed KnowledgeGap objects, each with enough detail to generate a testable hypothesis.

**Dependencies:** `KnowledgeProvider`  
**Inputs:** `KnowledgeSnapshot`  
**Outputs:** `List[KnowledgeGap]`

```python
@dataclass
class KnowledgeGap:
    gap_type: GapType                   # PERFORMANCE | COVERAGE | TEMPORAL | DEGRADATION | CONTRADICTION
    severity: GapSeverity               # CRITICAL | HIGH | MEDIUM | LOW
    regime: Optional[str]               # e.g., "TRENDING_DOWN", "VOLATILE"
    strategy: Optional[str]             # e.g., "momentum_breakout_v2"
    feature: Optional[str]              # e.g., "atr_14"
    description: str                    # Human-readable gap description
    evidence: Dict[str, Any]            # Quantitative evidence: {"win_rate": 0.22, "n_sessions": 8}
    detected_at: datetime

class GapDetector(ABC):

    def detect_performance_gaps(
        self, snapshot: KnowledgeSnapshot
    ) -> List[KnowledgeGap]:
        """
        Detects regimes or strategies where win_rate < 0.30 and
        sample_count >= MIN_SIGNIFICANT (default: 10 sessions).
        """

    def detect_coverage_gaps(
        self, snapshot: KnowledgeSnapshot
    ) -> List[KnowledgeGap]:
        """
        Detects: feature dimensions never studied, regimes with no
        assigned study in last 90 days, discovered edges not yet
        validated in recent market conditions.
        """

    def detect_temporal_gaps(
        self, snapshot: KnowledgeSnapshot
    ) -> List[KnowledgeGap]:
        """
        Detects: studies older than 6 months in any active regime,
        patterns discovered before last major regime shift.
        """

    def detect_degradation_gaps(
        self, snapshot: KnowledgeSnapshot
    ) -> List[KnowledgeGap]:
        """
        Detects: pattern confidence dropped > 15% since discovery,
        strategy performance trending downward for 5+ sessions.
        """

    def detect_contradictions(
        self, snapshot: KnowledgeSnapshot
    ) -> List[KnowledgeGap]:
        """
        Detects: findings across studies that directly contradict
        each other on the same metric/regime.
        """

    def prioritize(
        self, gaps: List[KnowledgeGap]
    ) -> List[KnowledgeGap]:
        """
        Returns gaps sorted by: severity DESC, then recency DESC.
        CRITICAL always precedes HIGH which always precedes MEDIUM.
        """
```

---

## Interface 3 — HypothesisProvider

**Purpose:**  
Generates testable hypotheses from knowledge gaps and maintains the hypothesis registry. Each hypothesis must be specific, falsifiable, and contain enough information to generate a study plan.

**Dependencies:** `HypothesisRegistry` (persistence), `GapDetector` (upstream)  
**Inputs:** `KnowledgeGap`  
**Outputs:** `Hypothesis`, `HypothesisID`

```python
@dataclass
class Hypothesis:
    id: str                              # e.g., "H2026-08-003"
    question: str                        # Specific testable question
    null_hypothesis: str                 # What would be true if the gap is noise
    expected_finding: str                # Researcher's prediction
    source: HypothesisSource             # PERFORMANCE_GAP | COVERAGE_GAP | TEMPORAL | DEGRADATION | MANUAL
    status: HypothesisStatus             # OPEN | ACTIVE | TESTED | PROMOTED | REJECTED | INCONCLUSIVE | DEFERRED
    regime: Optional[str]
    strategy: Optional[str]
    priority: int                        # 1 (urgent) to 5 (exploratory)
    governance_class: GovernanceClass    # A or B
    min_evidence: MinEvidenceSpec        # n, p_threshold, min_lift
    data_requirements: DataSpec          # date_range, regime_filter, min_rows
    estimated_cost: StudyCost
    depends_on: List[str]                # Prior hypothesis IDs that must be PROMOTED first
    created_at: datetime
    study_ids: List[str]
    findings: List[StudyFinding]
    notes: str

class HypothesisProvider(ABC):

    def generate(self, gap: KnowledgeGap) -> Hypothesis:
        """
        Translates a KnowledgeGap into a Hypothesis.
        Sets: question, null_hypothesis, min_evidence, data_requirements,
              estimated_cost, governance_class (based on gap_type).
        """

    def register(self, h: Hypothesis) -> str:
        """
        Persists hypothesis to data/ars_hypothesis_registry.json.
        Returns hypothesis ID.
        Raises DuplicateHypothesisError if identical question already exists.
        """

    def update_status(
        self,
        id: str,
        status: HypothesisStatus,
        evidence: Optional[StudyFinding] = None
    ) -> None:
        """
        Updates hypothesis status and appends evidence.
        Persists immediately. Thread-safe.
        """

    def get_open(
        self,
        regime: Optional[str] = None,
        governance_class: Optional[GovernanceClass] = None
    ) -> List[Hypothesis]:
        """
        Returns hypotheses with status OPEN or ACTIVE.
        Optional filter by regime or class.
        """

    def get_evidence_chain(self, id: str) -> List[StudyFinding]:
        """
        Returns all evidence (from all studies) for a hypothesis.
        """

    def detect_duplicates(self, h: Hypothesis) -> List[Hypothesis]:
        """
        Returns existing hypotheses testing a similar question.
        Prevents running the same study twice.
        """
```

---

## Interface 4 — StudyPlanner

**Purpose:**  
Converts an approved hypothesis into a complete, unambiguous study plan. The plan fully specifies the study — nothing should be left to interpretation at execution time.

**Dependencies:** `KnowledgeProvider` (for data availability check)  
**Inputs:** `Hypothesis`  
**Outputs:** `StudyPlan`, `StudyProposal` (for Class B)

```python
@dataclass
class StudyPlan:
    plan_id: str
    hypothesis_id: str
    study_type: StudyType               # PATTERN_MINING | FEATURE_ANALYSIS | REGIME_STUDY | COMPLEX_PIPELINE
    data_source: DataSource             # REPLAY_DB | LIVE_SUPPLEMENT | BOTH
    date_range: Tuple[date, date]
    regime_filter: Optional[List[str]]
    feature_set: List[str]              # Feature names from existing extractors
    validation_method: List[ValidationMethod]  # WALK_FORWARD | MONTE_CARLO | CROSS_MARKET | SENSITIVITY
    min_sample_size: int
    min_confidence: float
    min_lift: float
    executor: StudyExecutor             # Which module executes this (EDGE_DISCOVERY | STUDY_EXECUTOR | RESEARCH_LAB | WF_TESTER)
    governance_class: GovernanceClass
    estimated_wall_clock_hours: float
    estimated_rows_processed: int
    output_schema: str                  # Expected JSON schema of result

class StudyPlanner(ABC):

    def plan(self, h: Hypothesis) -> StudyPlan:
        """
        Converts hypothesis into a complete StudyPlan.
        Checks data availability, feature existence, executor availability.
        Raises InfeasibleStudyError if requirements cannot be met.
        """

    def estimate_cost(self, plan: StudyPlan) -> StudyCost:
        """
        Returns estimated: wall_clock_hours, memory_mb, rows_processed.
        Based on replay.db row count for plan's date_range + regime_filter.
        """

    def assess_feasibility(self, plan: StudyPlan) -> FeasibilityReport:
        """
        Checks:
        - Data availability (date range exists in replay.db)
        - Minimum sample size achievable given regime filter
        - Required features are present in feature extractors
        - Executor module is healthy
        Returns: FEASIBLE | MARGINAL | INFEASIBLE + reason
        """

    def generate_proposal(self, plan: StudyPlan) -> StudyProposal:
        """
        For Class B plans: generates full Markdown proposal text.
        Includes hypothesis, design, impact assessment, rollback plan.
        Writes to data/ars_proposals/PROPOSAL_{date}_{slug}.md
        """
```

---

## Interface 5 — ResearchCoordinator

**Purpose:**  
Schedules study execution and delegates to the correct existing IIOS module. Never executes algorithms itself. The coordinator's only job is to pick the right existing module and submit the task correctly.

**Dependencies:** `TaskQueue`, `EdgeDiscoveryEngine`, `ValidationEngine`, `ResearchLab`, `WalkForwardTester`, `study_executor`  
**Inputs:** `StudyPlan`  
**Outputs:** `ScheduledStudy`, `ExecutionStatus`

```python
@dataclass
class ScheduledStudy:
    execution_id: str
    plan_id: str
    hypothesis_id: str
    scheduled_at: datetime
    scheduled_for: datetime              # When it will run (or ASAP if Priority.LOW)
    executor_module: str                 # Which module will execute
    task_queue_id: Optional[str]         # TaskQueue task ID

class ResearchCoordinator(ABC):

    def schedule(
        self, plan: StudyPlan, priority: ResearchPriority = ResearchPriority.NORMAL
    ) -> ScheduledStudy:
        """
        Submits study to TaskQueue at appropriate priority.
        ResearchPriority.URGENT   → TaskQueue Priority.HIGH
        ResearchPriority.NORMAL   → TaskQueue Priority.LOW
        ResearchPriority.DEFERRED → TaskQueue Priority.LOW + scheduled time
        """

    def delegate(self, plan: StudyPlan) -> str:
        """
        Routes study to correct existing module:
          PATTERN_MINING    → EdgeDiscoveryEngine.mine(config)
          FEATURE_ANALYSIS  → study_executor.run_feature_study(plan)
          COMPLEX_PIPELINE  → study_executor.run_pipeline(plan)
          VALIDATION_ONLY   → ValidationEngine.validate(candidate)
          SANDBOX           → ResearchLab.run_experiment(config)
          WF_ONLY           → WalkForwardTester.test(strategy, data)
        Returns: execution_id (matches ScheduledStudy.execution_id)
        """

    def get_status(self, execution_id: str) -> ExecutionStatus:
        """
        Returns: QUEUED | RUNNING | COMPLETE | FAILED | CANCELLED
        """

    def get_result(self, execution_id: str) -> Optional[StudyResult]:
        """
        Returns result if status == COMPLETE, else None.
        """

    def cancel(self, execution_id: str) -> bool:
        """
        Cancels a QUEUED study (cannot cancel RUNNING).
        Returns True if cancelled, False if already running/complete.
        """

    def is_compute_available(self) -> bool:
        """
        Returns True only if:
        - Market is closed (outside 09:15-15:30 IST)
        - No CRITICAL or HIGH priority tasks in TaskQueue
        - SystemMonitor reports HEALTHY
        """
```

---

## Interface 6 — EvidenceValidator

**Purpose:**  
Quality-gates study results before they enter the knowledge base. A finding that passes EvidenceValidator has sufficient evidence for the platform to act on it (via human-approved integration). A rejected finding is archived with its failure reason.

**Dependencies:** None (pure logic — no external calls)  
**Inputs:** `StudyResult`, `StudyPlan`  
**Outputs:** `ValidationVerdict`

```python
@dataclass
class ValidationVerdict:
    passed: bool
    verdict: Verdict                     # ACCEPT | REJECT | INCONCLUSIVE | NEEDS_MORE_DATA
    checks: List[EvidenceCheck]          # Each check: name, passed, value, threshold
    rejection_reason: Optional[str]
    follow_up_recommendation: Optional[str]

class EvidenceValidator(ABC):

    def validate(
        self, result: StudyResult, plan: StudyPlan
    ) -> ValidationVerdict:
        """
        Runs all checks below. Returns ACCEPT only if ALL pass.
        """

    def check_minimum_samples(
        self, result: StudyResult, min_n: int
    ) -> EvidenceCheck:
        """
        Checks: result.sample_count >= min_n
        Default: min_n = 100 (pattern mining), 30 (strategy test)
        """

    def check_statistical_significance(
        self, result: StudyResult
    ) -> EvidenceCheck:
        """
        Checks: p_value < 0.05 for primary metric comparison.
        Source: MWU test result or chi-square in study output.
        """

    def check_economic_significance(
        self, result: StudyResult
    ) -> EvidenceCheck:
        """
        Checks: lift >= 1.30 over base rate (configurable).
        A statistically significant but economically trivial finding
        is NOT promoted.
        """

    def check_walkforward_pass_rate(
        self, result: StudyResult, min_pass_rate: float = 0.60
    ) -> EvidenceCheck:
        """
        Checks: fraction of WF windows where pattern holds >= min_pass_rate.
        Prevents overfitted patterns from entering knowledge base.
        """

    def check_oos_consistency(
        self, result: StudyResult, max_degradation: float = 0.20
    ) -> EvidenceCheck:
        """
        Checks: OOS metric is within 20% of IS metric.
        e.g., IS win_rate=0.42, OOS win_rate must be >= 0.336
        """

    def check_temporal_integrity(
        self, result: StudyResult, plan: StudyPlan
    ) -> EvidenceCheck:
        """
        Checks: no future data was used in study (no lookahead bias).
        Validates that WF splits are chronologically ordered.
        """

    def check_data_quality(
        self, result: StudyResult
    ) -> EvidenceCheck:
        """
        Checks: no NaN features, no duplicated observations,
        no regime filter that leaves < 50 rows in any WF window.
        """
```

---

## Interface 7 — RoadmapManager

**Purpose:**  
Maintains the research roadmap — a prioritised, dependency-aware view of what the platform knows, what it's studying, and what needs to be studied next. The roadmap is the primary output humans review to assess research health.

**Dependencies:** `HypothesisProvider`, `KnowledgeProvider`  
**Inputs:** `Hypothesis`, `ValidationVerdict`  
**Outputs:** `ResearchRoadmap`, `ResearchRoadmapSummary`

```python
@dataclass
class ResearchRoadmap:
    generated_at: datetime
    open_hypotheses: List[Hypothesis]
    active_studies: List[ScheduledStudy]
    completed_this_month: List[Hypothesis]
    promoted_findings: List[StudyFinding]
    pending_proposals: List[StudyProposal]
    knowledge_base_version: str
    overall_gap_coverage: float           # 0.0 – 1.0

class RoadmapManager(ABC):

    def get_current_roadmap(self) -> ResearchRoadmap:
        """
        Assembles current state from HypothesisRegistry, active TaskQueue
        tasks, and ars_knowledge_base.json.
        """

    def get_next_priority(self) -> Optional[Hypothesis]:
        """
        Returns the highest-priority OPEN hypothesis whose dependencies
        are all PROMOTED. Returns None if no ready hypothesis exists.
        """

    def update(
        self, h: Hypothesis, verdict: ValidationVerdict
    ) -> None:
        """
        Updates hypothesis status from verdict.
        ACCEPT  → marks PROMOTED, adds finding to roadmap
        REJECT  → marks REJECTED, logs reason
        INCONCLUSIVE → marks INCONCLUSIVE, generates follow-up if appropriate
        """

    def add_followup(
        self, parent: Hypothesis, followup: Hypothesis
    ) -> None:
        """
        Registers a follow-up hypothesis that depends on parent.
        Sets followup.depends_on = [parent.id].
        """

    def generate_summary(self) -> ResearchRoadmapSummary:
        """
        Returns summary metrics: total hypotheses, open, active, promoted,
        rejected, this-month completions, overall gap_coverage.
        """

    def generate_markdown_report(self) -> str:
        """
        Returns Markdown-formatted roadmap summary for human review.
        Written to data/ars_proposals/ROADMAP_CURRENT.md on each cycle.
        """
```

---

## Central Coordinator — ScientificDirector

**Purpose:**  
Orchestrates all 7 interfaces through the 10-step research lifecycle. This is the only component that calls all other interfaces. It is called by `MasterOrchestrator._do_ars_research()` at EOD.

**Dependencies:** All 7 interfaces above  
**Inputs:** None (pulls state from KnowledgeProvider)  
**Outputs:** `ResearchCycleReport`

```python
@dataclass
class ResearchCycleReport:
    cycle_id: str
    started_at: datetime
    completed_at: datetime
    gaps_detected: int
    hypotheses_generated: int
    hypotheses_registered: int
    studies_scheduled: int
    studies_completed: int
    findings_promoted: int
    findings_rejected: int
    proposals_generated: int
    knowledge_base_updated: bool
    roadmap_updated: bool
    errors: List[str]

class ScientificDirector:

    def __init__(
        self,
        knowledge: KnowledgeProvider,
        gap_detector: GapDetector,
        hypothesis_provider: HypothesisProvider,
        planner: StudyPlanner,
        coordinator: ResearchCoordinator,
        validator: EvidenceValidator,
        roadmap: RoadmapManager,
    ) -> None: ...

    def run_cycle(self) -> ResearchCycleReport:
        """
        Executes the full 10-step research lifecycle.
        Returns ResearchCycleReport.
        Publishes RESEARCH_CYCLE_COMPLETE event on exit.
        Never raises — catches and logs all exceptions.
        """

    def check_completed_studies(self) -> List[StudyResult]:
        """
        Called separately (e.g., on STUDY_COMPLETE event).
        Picks up completed study results and runs Steps 8-10.
        """

    def get_status(self) -> DirectorStatus:
        """
        Returns current state: IDLE | DETECTING_GAPS | PLANNING | WAITING_APPROVAL | EXECUTING | VALIDATING
        """
```

---

## Data Types Quick Reference

```python
# Enumerations
class GapType(Enum):         PERFORMANCE, COVERAGE, TEMPORAL, DEGRADATION, CONTRADICTION
class GapSeverity(Enum):     CRITICAL, HIGH, MEDIUM, LOW
class HypothesisSource(Enum):PERFORMANCE_GAP, COVERAGE_GAP, TEMPORAL, DEGRADATION, MANUAL
class HypothesisStatus(Enum):OPEN, ACTIVE, TESTED, PROMOTED, REJECTED, INCONCLUSIVE, DEFERRED
class GovernanceClass(Enum): A, B
class StudyType(Enum):       PATTERN_MINING, FEATURE_ANALYSIS, REGIME_STUDY, COMPLEX_PIPELINE
class ValidationMethod(Enum):WALK_FORWARD, MONTE_CARLO, CROSS_MARKET, SENSITIVITY
class ResearchPriority(Enum):URGENT, NORMAL, DEFERRED
class Verdict(Enum):         ACCEPT, REJECT, INCONCLUSIVE, NEEDS_MORE_DATA
class ExecutionStatus(Enum): QUEUED, RUNNING, COMPLETE, FAILED, CANCELLED

# Simple value objects (all immutable)
@dataclass(frozen=True)
class StudyCost:
    wall_clock_hours: float
    memory_mb: int
    rows_processed: int

@dataclass(frozen=True)
class MinEvidenceSpec:
    min_n: int
    p_threshold: float
    min_lift: float
    min_wf_pass_rate: float
    max_oos_degradation: float

@dataclass(frozen=True)
class StudyFinding:
    study_id: str
    hypothesis_id: str
    metric: str
    value: float
    confidence: float
    regime: Optional[str]
    description: str
    created_at: datetime
```

---

*Scientific Director Interfaces | ARS Phase 0 | Frozen 2026-08-03*

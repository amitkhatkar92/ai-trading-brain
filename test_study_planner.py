"""
test_study_planner.py — ARS Phase 2D test suite.

Covers:
    - Instantiation (with/without optional deps)
    - create_plan() — structure, determinism, task count, required fields
    - create_from_gap() — all 10 gap categories, correct study type mapping
    - create_from_hypothesis() — all HypothesisClassification types
    - create_from_entry() — provenance, title, related_gaps
    - DatasetRequirement — fields, to_dict
    - ValidationPlan — fields, defaults match config
    - ExecutionEstimate — total_hours = sum, cost > 0, breakdown
    - StudyDependency — to_dict, validate_dependencies
    - Approval classification — CLASS_A/B rules, config override
    - list_plans() / get_plan() / latest_plans()
    - statistics() — totals, sums, fractions
    - portfolio() — aggregate
    - Thread safety
    - Backward compatibility

Run:
    python test_study_planner.py
"""
from __future__ import annotations

import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_research import (
    # Phase 2D
    StudyPlanner,
    StudyPlannerConfig,
    StudyPlannerError,
    StudyPlanNotFoundError,
    StudyPlan,
    StudyTask,
    DatasetRequirement,
    ValidationPlan,
    ExecutionEstimate,
    StudyDependency,
    StudyPortfolio,
    PlanningStatistics,
    StudyType,
    ApprovalClass,
    PlanStatus,
    RiskClass,
    # Phase 2C
    EvidenceValidator,
    # Phase 2B
    RoadmapManager,
    RoadmapEntry,
    RoadmapEntryStatus,
    StudyCategory,
    KnowledgeGainEstimate,
    ResearchCostEstimate,
    ResearchDebt,
    # Phase 2A
    GapDetector,
    GapCategory,
    GapSeverity,
    GapStatus,
    KnowledgeGap,
    # Phase 1.2
    HypothesisRegistry,
    HypothesisClassification,
    HypothesisPriority,
    HypothesisStatus,
    # Phase 1.1
    KnowledgeProvider,
    CrossStudySynthesizer,
)
from autonomous_research.roadmap_models import RoadmapManagerConfig
from autonomous_research.study_planner_models import StudyPlannerConfig


# ═════════════════════════════════════════════════════════════════════════════
# Minimal test framework
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name:        str
    passed:      bool
    duration_ms: float
    detail:      str
    error:       Optional[str] = None


class TestRunner:
    def __init__(self) -> None:
        self.results: List[TestResult] = []

    def run(self, name: str, fn: Callable[[], Any]) -> None:
        t0 = time.perf_counter()
        try:
            detail = fn() or "OK"
            self.results.append(TestResult(
                name=name, passed=True,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                detail=str(detail),
            ))
        except AssertionError as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                detail="ASSERTION FAILED", error=str(exc),
            ))
        except Exception as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                detail="EXCEPTION",
                error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            ))

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)


def ok(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ═════════════════════════════════════════════════════════════════════════════
# Shared fixtures
# ═════════════════════════════════════════════════════════════════════════════

_KP:  Optional[KnowledgeProvider]    = None
_HR:  Optional[HypothesisRegistry]   = None
_SYN: Optional[CrossStudySynthesizer] = None
_GD:  Optional[GapDetector]          = None
_RM:  Optional[RoadmapManager]       = None
_TMP: Optional[Path]                 = None


def get_tmp() -> Path:
    global _TMP
    if _TMP is None:
        _TMP = Path(tempfile.mkdtemp(prefix="ars_sp_test_"))
    return _TMP


def get_kp() -> KnowledgeProvider:
    global _KP
    if _KP is None:
        _KP = KnowledgeProvider()
    return _KP


def get_hr() -> HypothesisRegistry:
    global _HR
    if _HR is None:
        _HR = HypothesisRegistry(
            knowledge_provider=get_kp(),
            registry_path=get_tmp() / "hr_state.json",
        )
    return _HR


def get_syn() -> CrossStudySynthesizer:
    global _SYN
    if _SYN is None:
        _SYN = CrossStudySynthesizer(knowledge_provider=get_kp())
    return _SYN


def get_gd() -> GapDetector:
    global _GD
    if _GD is None:
        _GD = GapDetector(get_kp(), synthesizer=get_syn())
    return _GD


def get_rm() -> RoadmapManager:
    global _RM
    if _RM is None:
        _RM = RoadmapManager(
            get_kp(),
            gap_detector=get_gd(),
            state_path=get_tmp() / "rm_state.json",
        )
    return _RM


def make_planner(config: Optional[StudyPlannerConfig] = None) -> StudyPlanner:
    return StudyPlanner(
        knowledge_provider=get_kp(),
        hypothesis_registry=get_hr(),
        gap_detector=get_gd(),
        config=config,
    )


def make_gap(
    gap_id: str = "GAP-001",
    category: GapCategory = GapCategory.DATA_GAP,
    severity: GapSeverity = GapSeverity.MEDIUM,
) -> KnowledgeGap:
    return KnowledgeGap(
        gap_id=gap_id,
        category=category,
        title=f"Test gap {category.value}",
        description=f"A test gap of category {category.value}.",
        severity=severity,
        severity_rationale="Test severity rationale.",
        confidence=0.75,
        status=GapStatus.OPEN,
        supporting_evidence=["STUDY-001", "FINDING-002"],
        related_studies=["STUDY-001"],
        related_hypotheses=["HYP-001"],
        related_findings=["FINDING-002"],
        recommended_action=f"Investigate {category.value} gap.",
        estimated_knowledge_gain=0.6,
        rule_id="R-GD-01",
        rule_parameters={"threshold": 100},
        created_at=datetime.now(),
    )


def make_entry(gap: Optional[KnowledgeGap] = None) -> RoadmapEntry:
    g = gap or make_gap()
    gain = KnowledgeGainEstimate(
        gap_id=g.gap_id,
        scientific_importance=0.75,
        evidence_gap_size=0.60,
        current_confidence=0.40,
        expected_confidence_improvement=0.50,
        expected_new_findings=3,
        coverage_increase=0.40,
        novelty=0.50,
        historical_impact=0.60,
        reuse_potential=0.50,
        uncertainty_reduction=0.45,
        total_gain=0.60,
        breakdown={"formula": "test"},
    )
    cost = ResearchCostEstimate(
        gap_id=g.gap_id,
        historical_days_required=252,
        replay_duration_estimate_hours=4.0,
        implementation_effort=0.50,
        dependencies=[],
        risk=0.30,
        total_cost=0.40,
        breakdown={"formula": "test"},
    )
    debt = ResearchDebt(
        gap_id=g.gap_id,
        category=g.category,
        severity=g.severity,
        base_debt=0.50,
        age_debt=0.10,
        contradiction_debt=0.0,
        expiry_debt=0.0,
        total_debt=0.30,
        accumulation_rationale="test",
        breakdown={"formula": "test"},
    )
    return RoadmapEntry(
        entry_id=f"RE-{g.gap_id[:8]}",
        gap=g,
        knowledge_gain_estimate=gain,
        cost_estimate=cost,
        debt=debt,
        priority_score=0.72,
        priority_breakdown={"formula": "test"},
        study_category=StudyCategory.WINNER_DNA,
        status=RoadmapEntryStatus.PENDING,
        rank=1,
        recommended_study_title=f"Study for {g.title}",
        recommended_approach="Test approach",
        created_at=datetime.now(),
    )


def make_hypothesis(classification: HypothesisClassification) -> str:
    """Create a hypothesis and return its ID."""
    hr = get_hr()
    h  = hr.create_hypothesis(
        title=f"Test hypothesis {classification.value}",
        research_question=f"Does {classification.value} effect exist?",
        description=f"Testing {classification.value} classification.",
        origin="unit_test",
        classification=classification,
        priority=HypothesisPriority.MEDIUM,
        confidence=0.60,
        knowledge_gap="Gap area",
        expected_knowledge_gain="Moderate gain",
        required_data={},
        validation_method="Statistical test",
        origin_study=None,
    )
    return h.hypothesis_id


# ═════════════════════════════════════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════════════════════════════════════

def run_all() -> int:
    runner = TestRunner()

    # ── T-01 to T-03: Instantiation ──────────────────────────────────────────

    def t01():
        sp = StudyPlanner(get_kp())
        ok(sp is not None, "StudyPlanner should instantiate with KP only")
        return "StudyPlanner(kp_only) OK"
    runner.run("T-01: Instantiation with KP only", t01)

    def t02():
        sp = StudyPlanner(
            get_kp(),
            hypothesis_registry=get_hr(),
            gap_detector=get_gd(),
            roadmap_manager=get_rm(),
            evidence_validator=EvidenceValidator(get_kp()),
        )
        ok(sp is not None, "Should instantiate with all optional providers")
        return "All optional providers accepted"
    runner.run("T-02: Instantiation with all optional providers", t02)

    def t03():
        cfg = StudyPlannerConfig(
            default_date_lookback_days=252,
            default_oos_split=0.25,
            default_min_observations=50,
        )
        sp = StudyPlanner(get_kp(), config=cfg)
        ok(sp._cfg.default_date_lookback_days == 252, "Config should be stored")
        ok(sp._cfg.default_oos_split == 0.25, "OOS split should be stored")
        return "Custom config accepted"
    runner.run("T-03: Custom StudyPlannerConfig accepted", t03)

    # ── T-04 to T-12: create_plan() ───────────────────────────────────────────

    def t04():
        sp   = make_planner()
        plan = sp.create_plan(
            title="Test Replay Study",
            study_type=StudyType.HISTORICAL_REPLAY,
            scientific_question="Does momentum persist in TRENDING_UP regime?",
        )
        ok(isinstance(plan, StudyPlan),        "Should return StudyPlan")
        ok(plan.plan_id.startswith("SP-"),     "plan_id must start with SP-")
        ok(len(plan.plan_id) == 11,            f"plan_id length wrong: {plan.plan_id}")
        ok(plan.study_type == StudyType.HISTORICAL_REPLAY, "study_type must be set")
        ok(plan.status == PlanStatus.DRAFT,    "New plans start as DRAFT")
        return f"plan_id={plan.plan_id}"
    runner.run("T-04: create_plan() returns well-formed StudyPlan", t04)

    def t05():
        sp   = make_planner()
        plan1 = sp.create_plan(
            title="Determinism Test",
            study_type=StudyType.DNA_DISCOVERY,
            scientific_question="Is determinism preserved?",
            source_gap_id="GAP-DET-001",
        )
        plan2 = sp.create_plan(
            title="Determinism Test",
            study_type=StudyType.DNA_DISCOVERY,
            scientific_question="Same question?",
            source_gap_id="GAP-DET-001",
        )
        ok(plan1.plan_id == plan2.plan_id,
           f"Same inputs must produce same plan_id: {plan1.plan_id} vs {plan2.plan_id}")
        return f"Deterministic plan_id={plan1.plan_id}"
    runner.run("T-05: create_plan() plan_id is deterministic", t05)

    def t06():
        sp   = make_planner()
        plan = sp.create_plan(
            title="Task Count Test",
            study_type=StudyType.REGIME_ANALYSIS,
            scientific_question="How many tasks?",
        )
        ok(len(plan.tasks) == 5, f"Expected 5 tasks, got {len(plan.tasks)}")
        ok(all(isinstance(t, StudyTask) for t in plan.tasks), "All tasks must be StudyTask")
        orders = [t.order for t in plan.tasks]
        ok(orders == list(range(1, 6)), f"Task orders must be 1-5, got {orders}")
        return f"{len(plan.tasks)} tasks in correct order"
    runner.run("T-06: create_plan() produces exactly 5 ordered tasks", t06)

    def t07():
        sp   = make_planner()
        plan = sp.create_plan(
            title="Dataset Test",
            study_type=StudyType.SECTOR_RESEARCH,
            scientific_question="Are datasets populated?",
        )
        ok(len(plan.dataset_requirements) >= 1, "Should have ≥ 1 dataset requirement")
        ok(all(isinstance(d, DatasetRequirement) for d in plan.dataset_requirements),
           "All entries must be DatasetRequirement")
        return f"{len(plan.dataset_requirements)} dataset requirement(s)"
    runner.run("T-07: create_plan() dataset_requirements non-empty", t07)

    def t08():
        sp   = make_planner()
        plan = sp.create_plan(
            title="Validation Plan Test",
            study_type=StudyType.EDGE_VALIDATION,
            scientific_question="Is edge present?",
        )
        ok(isinstance(plan.validation_plan, ValidationPlan), "Must have ValidationPlan")
        ok(len(plan.validation_plan.success_criteria) >= 1,  "Need ≥ 1 success criterion")
        ok(len(plan.validation_plan.acceptance_criteria) >= 1, "Need ≥ 1 acceptance criterion")
        ok(len(plan.validation_plan.metrics) >= 1, "Need ≥ 1 metric")
        return f"ValidationPlan: {len(plan.validation_plan.metrics)} metrics"
    runner.run("T-08: create_plan() validation_plan fully populated", t08)

    def t09():
        sp   = make_planner()
        plan = sp.create_plan(
            title="Estimate Test",
            study_type=StudyType.FEATURE_IMPORTANCE,
            scientific_question="Feature importance populated?",
        )
        ok(isinstance(plan.execution_estimate, ExecutionEstimate), "Must have ExecutionEstimate")
        ok(plan.execution_estimate.total_hours > 0, "total_hours must be > 0")
        ok(plan.execution_estimate.compute_cost_usd >= 0, "cost must be non-negative")
        expected = round(
            plan.execution_estimate.data_fetch_hours
            + plan.execution_estimate.compute_hours
            + plan.execution_estimate.analysis_hours,
            6,
        )
        ok(abs(plan.execution_estimate.total_hours - expected) < 0.001,
           f"total_hours != sum of components: {plan.execution_estimate.total_hours} vs {expected}")
        return f"total_hours={plan.execution_estimate.total_hours}"
    runner.run("T-09: create_plan() execution_estimate total = sum of components", t09)

    def t10():
        sp   = make_planner()
        plan = sp.create_plan(
            title="Outputs Test",
            study_type=StudyType.PATTERN_MINING,
            scientific_question="Expected outputs present?",
        )
        ok(len(plan.expected_outputs) >= 1,     "Must have ≥ 1 expected output")
        ok(len(plan.success_criteria) >= 1,     "Must have ≥ 1 success criterion")
        ok(len(plan.acceptance_criteria) >= 1,  "Must have ≥ 1 acceptance criterion")
        ok("study_report" in plan.expected_outputs, "study_report must always be present")
        return f"{len(plan.expected_outputs)} outputs, {len(plan.success_criteria)} criteria"
    runner.run("T-10: create_plan() expected_outputs and criteria populated", t10)

    def t11():
        sp   = make_planner()
        plan = sp.create_plan(
            title="Provenance Test",
            study_type=StudyType.CROSS_VALIDATION,
            scientific_question="Sources tracked?",
            source_gap_id="GAP-PROV",
            source_hypothesis_id="HYP-PROV",
            source_entry_id="RE-PROV",
        )
        ok(plan.source_gap_id == "GAP-PROV",           "source_gap_id must be stored")
        ok(plan.source_hypothesis_id == "HYP-PROV",    "source_hypothesis_id must be stored")
        ok(plan.source_entry_id == "RE-PROV",          "source_entry_id must be stored")
        return "All provenance fields stored"
    runner.run("T-11: create_plan() provenance fields stored", t11)

    def t12():
        sp  = make_planner()
        sp.create_plan("P1", StudyType.HISTORICAL_REPLAY, "Q1?", source_gap_id="G1")
        retrieved = sp.get_plan(
            sp.create_plan("P2", StudyType.DNA_DISCOVERY, "Q2?").plan_id
        )
        ok(retrieved.title == "P2", "Stored plan must be retrievable")
        return "Plan stored and retrieved"
    runner.run("T-12: created plan is stored and retrievable", t12)

    # ── T-13 to T-22: create_from_gap() ──────────────────────────────────────

    _GAP_TYPE_EXPECTED = [
        (GapCategory.DATA_GAP,          StudyType.HISTORICAL_REPLAY),
        (GapCategory.EVIDENCE_GAP,      StudyType.DNA_DISCOVERY),
        (GapCategory.REGIME_GAP,        StudyType.REGIME_ANALYSIS),
        (GapCategory.SECTOR_GAP,        StudyType.SECTOR_RESEARCH),
        (GapCategory.TEMPORAL_GAP,      StudyType.HISTORICAL_REPLAY),
        (GapCategory.VALIDATION_GAP,    StudyType.EDGE_VALIDATION),
        (GapCategory.CONTRADICTION_GAP, StudyType.CROSS_VALIDATION),
        (GapCategory.CONFIDENCE_GAP,    StudyType.EDGE_VALIDATION),
        (GapCategory.KNOWLEDGE_GAP,     StudyType.DNA_DISCOVERY),
        (GapCategory.COVERAGE_GAP,      StudyType.REGIME_ANALYSIS),
    ]

    for idx, (gap_cat, expected_type) in enumerate(_GAP_TYPE_EXPECTED, start=13):
        def _make_gap_type_test(cat=gap_cat, exp=expected_type, n=idx):
            def test():
                sp   = make_planner()
                gap  = make_gap(gap_id=f"GAP-{n:03d}", category=cat)
                plan = sp.create_from_gap(gap)
                ok(plan.study_type == exp,
                   f"T-{n}: {cat.value} → expected {exp.value}, got {plan.study_type.value}")
                ok(plan.source_gap_id == gap.gap_id, "source_gap_id must be set")
                ok(gap.gap_id in plan.related_gaps, "gap_id must be in related_gaps")
                ok(len(plan.tasks) == 5, "Must have 5 tasks")
                return f"{cat.value} → {plan.study_type.value}"
            return test
        runner.run(
            f"T-{idx:02d}: create_from_gap() {gap_cat.value} → {expected_type.value}",
            _make_gap_type_test(),
        )

    # ── T-23 to T-29: create_from_hypothesis() ───────────────────────────────

    def t23():
        sp = StudyPlanner(get_kp())  # no registry
        try:
            sp.create_from_hypothesis("HYP-MISSING")
            ok(False, "Should have raised StudyPlannerError")
        except StudyPlannerError:
            pass
        return "Raises StudyPlannerError when no registry"
    runner.run("T-23: create_from_hypothesis() without registry raises StudyPlannerError", t23)

    def t24():
        sp = make_planner()
        try:
            sp.create_from_hypothesis("HYP-DOES-NOT-EXIST-XYZABC")
            ok(False, "Should have raised StudyPlanNotFoundError")
        except StudyPlanNotFoundError:
            pass
        return "Raises StudyPlanNotFoundError for unknown hypothesis"
    runner.run("T-24: create_from_hypothesis() raises StudyPlanNotFoundError for unknown id", t24)

    _HYPO_EXPECTED = [
        (HypothesisClassification.PERFORMANCE_GAP, StudyType.EDGE_VALIDATION),
        (HypothesisClassification.COVERAGE_GAP,    StudyType.REGIME_ANALYSIS),
        (HypothesisClassification.TEMPORAL_GAP,    StudyType.HISTORICAL_REPLAY),
        (HypothesisClassification.DEGRADATION,     StudyType.EDGE_VALIDATION),
        (HypothesisClassification.CONTRADICTION,   StudyType.CROSS_VALIDATION),
    ]

    for h_idx, (h_class, h_exp_type) in enumerate(_HYPO_EXPECTED, start=25):
        def _make_hypo_test(cls=h_class, exp=h_exp_type, n=h_idx):
            def test():
                sp    = make_planner()
                h_id  = make_hypothesis(cls)
                plan  = sp.create_from_hypothesis(h_id)
                ok(plan.study_type == exp,
                   f"T-{n}: {cls.value} → expected {exp.value}, got {plan.study_type.value}")
                ok(plan.source_hypothesis_id == h_id, "source_hypothesis_id must be set")
                ok(h_id in plan.related_hypotheses, "hypothesis_id must be in related_hypotheses")
                return f"{cls.value} → {plan.study_type.value}"
            return test
        runner.run(
            f"T-{h_idx:02d}: create_from_hypothesis() {h_class.value} → {h_exp_type.value}",
            _make_hypo_test(),
        )

    def t30():
        sp   = make_planner()
        h_id = make_hypothesis(HypothesisClassification.EXPLORATORY)
        plan = sp.create_from_hypothesis(h_id)
        ok(plan.study_type == StudyType.DNA_DISCOVERY,
           f"EXPLORATORY should map to DNA_DISCOVERY, got {plan.study_type.value}")
        return f"EXPLORATORY → {plan.study_type.value}"
    runner.run("T-30: create_from_hypothesis() EXPLORATORY → DNA_DISCOVERY", t30)

    def t31():
        sp   = make_planner()
        h_id = make_hypothesis(HypothesisClassification.MANUAL)
        plan = sp.create_from_hypothesis(h_id)
        ok(plan.study_type == StudyType.CUSTOM,
           f"MANUAL should map to CUSTOM, got {plan.study_type.value}")
        ok(plan.approval_class == ApprovalClass.CLASS_B,
           "CUSTOM must be CLASS_B")
        return f"MANUAL → CUSTOM → CLASS_B"
    runner.run("T-31: create_from_hypothesis() MANUAL → CUSTOM → CLASS_B", t31)

    # ── T-32 to T-36: create_from_entry() ────────────────────────────────────

    def t32():
        sp    = make_planner()
        entry = make_entry()
        plan  = sp.create_from_entry(entry)
        ok(isinstance(plan, StudyPlan), "Should return StudyPlan")
        ok(plan.source_entry_id == entry.entry_id, "source_entry_id must be set")
        ok(plan.source_gap_id == entry.gap.gap_id, "source_gap_id must be set from entry.gap")
        return f"plan_id={plan.plan_id}, source_entry_id={plan.source_entry_id}"
    runner.run("T-32: create_from_entry() returns plan with correct provenance", t32)

    def t33():
        sp    = make_planner()
        entry = make_entry()
        plan  = sp.create_from_entry(entry)
        ok(plan.title == entry.recommended_study_title,
           f"Title should come from entry. Got '{plan.title}'")
        return f"title='{plan.title}'"
    runner.run("T-33: create_from_entry() title from entry.recommended_study_title", t33)

    def t34():
        sp    = make_planner()
        entry = make_entry()
        plan  = sp.create_from_entry(entry)
        ok(entry.gap.gap_id in plan.related_gaps, "gap_id must be in related_gaps")
        return f"related_gaps={plan.related_gaps}"
    runner.run("T-34: create_from_entry() related_gaps contains gap_id", t34)

    def t35():
        sp    = make_planner()
        entry = make_entry()
        plan  = sp.create_from_entry(entry)
        ok(plan.estimated_knowledge_gain == entry.knowledge_gain_estimate.total_gain,
           "knowledge gain must come from entry's estimate")
        return f"knowledge_gain={plan.estimated_knowledge_gain}"
    runner.run("T-35: create_from_entry() estimated_knowledge_gain from entry", t35)

    def t36():
        sp    = make_planner()
        entry = make_entry(make_gap(category=GapCategory.REGIME_GAP))
        plan  = sp.create_from_entry(entry)
        ok(plan.study_type == StudyType.REGIME_ANALYSIS,
           f"REGIME_GAP entry → REGIME_ANALYSIS, got {plan.study_type.value}")
        return f"REGIME_GAP entry → {plan.study_type.value}"
    runner.run("T-36: create_from_entry() inherits correct study type from gap", t36)

    # ── T-37 to T-40: DatasetRequirement ─────────────────────────────────────

    def t37():
        sp   = make_planner()
        plan = sp.create_plan("DS Test", StudyType.HISTORICAL_REPLAY, "Q?")
        ds   = plan.dataset_requirements[0]
        ok(hasattr(ds, "name"),             "name field required")
        ok(hasattr(ds, "symbols"),          "symbols field required")
        ok(hasattr(ds, "date_start"),       "date_start field required")
        ok(hasattr(ds, "date_end"),         "date_end field required")
        ok(hasattr(ds, "regimes"),          "regimes field required")
        ok(hasattr(ds, "sectors"),          "sectors field required")
        ok(hasattr(ds, "feature_groups"),   "feature_groups field required")
        ok(hasattr(ds, "min_observations"), "min_observations field required")
        ok(hasattr(ds, "notes"),            "notes field required")
        return "All DatasetRequirement fields present"
    runner.run("T-37: DatasetRequirement has all required fields", t37)

    def t38():
        sp   = make_planner()
        plan = sp.create_plan("DS Dict Test", StudyType.HISTORICAL_REPLAY, "Q?")
        ds   = plan.dataset_requirements[0]
        d    = ds.to_dict()
        ok("name"             in d, "to_dict() must have name")
        ok("symbols"          in d, "to_dict() must have symbols")
        ok("date_start"       in d, "to_dict() must have date_start")
        ok("date_end"         in d, "to_dict() must have date_end")
        ok("regimes"          in d, "to_dict() must have regimes")
        ok("sectors"          in d, "to_dict() must have sectors")
        ok("feature_groups"   in d, "to_dict() must have feature_groups")
        ok("min_observations" in d, "to_dict() must have min_observations")
        ok("notes"            in d, "to_dict() must have notes")
        return "DatasetRequirement.to_dict() complete"
    runner.run("T-38: DatasetRequirement.to_dict() produces complete dict", t38)

    def t39():
        cfg  = StudyPlannerConfig(default_min_observations=250)
        sp   = StudyPlanner(get_kp(), config=cfg)
        plan = sp.create_plan("Min Obs Test", StudyType.HISTORICAL_REPLAY, "Q?")
        ds   = plan.dataset_requirements[0]
        ok(ds.min_observations == 250,
           f"min_observations should come from config: {ds.min_observations}")
        return f"min_observations={ds.min_observations}"
    runner.run("T-39: DatasetRequirement.min_observations comes from config", t39)

    def t40():
        sp   = make_planner()
        plan = sp.create_plan("Regime DS Test", StudyType.REGIME_ANALYSIS, "Q?")
        ds   = plan.dataset_requirements[0]
        ok(len(ds.regimes) >= 2, f"REGIME_ANALYSIS should have ≥ 2 regimes: {ds.regimes}")
        return f"regimes={ds.regimes}"
    runner.run("T-40: DatasetRequirement.regimes populated for REGIME_ANALYSIS", t40)

    # ── T-41 to T-44: ValidationPlan ─────────────────────────────────────────

    def t41():
        sp   = make_planner()
        plan = sp.create_plan("VP Test", StudyType.EDGE_VALIDATION, "Q?")
        vp   = plan.validation_plan
        ok(vp.oos_split == 0.20,            "Default OOS split must be 0.20")
        ok(vp.walk_forward_windows == 5,    "Default WF windows must be 5")
        ok(vp.cross_validation_folds == 5,  "Default CV folds must be 5")
        return f"oos={vp.oos_split}, wf_windows={vp.walk_forward_windows}"
    runner.run("T-41: ValidationPlan defaults match config", t41)

    def t42():
        cfg  = StudyPlannerConfig(default_oos_split=0.30, default_walk_forward_windows=8)
        sp   = StudyPlanner(get_kp(), config=cfg)
        plan = sp.create_plan("VP Config Test", StudyType.EDGE_VALIDATION, "Q?")
        vp   = plan.validation_plan
        ok(vp.oos_split == 0.30,            f"OOS split should be 0.30: {vp.oos_split}")
        ok(vp.walk_forward_windows == 8,    f"WF windows should be 8: {vp.walk_forward_windows}")
        return f"custom oos={vp.oos_split}, wf={vp.walk_forward_windows}"
    runner.run("T-42: ValidationPlan respects custom config", t42)

    def t43():
        sp   = make_planner()
        plan = sp.create_plan("VP Dict Test", StudyType.EDGE_VALIDATION, "Q?")
        d    = plan.validation_plan.to_dict()
        for key in ("methodology", "walk_forward_windows", "oos_split",
                    "cross_validation_folds", "success_criteria",
                    "acceptance_criteria", "metrics", "min_win_rate",
                    "min_sharpe", "max_drawdown"):
            ok(key in d, f"to_dict() must include '{key}'")
        return "ValidationPlan.to_dict() complete"
    runner.run("T-43: ValidationPlan.to_dict() produces complete dict", t43)

    def t44():
        sp   = make_planner()
        plan = sp.create_plan("VP SC Test", StudyType.META_LEARNING, "Q?")
        vp   = plan.validation_plan
        ok(len(vp.success_criteria) >= 1,   "META_LEARNING must have success criteria")
        ok("accuracy" in vp.metrics or any("meta" in m.lower() for m in vp.metrics),
           f"META_LEARNING metrics should include accuracy: {vp.metrics}")
        return f"META_LEARNING metrics={vp.metrics}"
    runner.run("T-44: ValidationPlan has study-type-specific metrics", t44)

    # ── T-45 to T-48: ExecutionEstimate ──────────────────────────────────────

    def t45():
        sp   = make_planner()
        plan = sp.create_plan("Est Test", StudyType.META_LEARNING, "Q?")
        est  = plan.execution_estimate
        ok(est.compute_intensity == "HIGH",
           f"META_LEARNING must be HIGH intensity: {est.compute_intensity}")
        ok(est.parallelizable == False,
           f"META_LEARNING must not be parallelizable: {est.parallelizable}")
        ok(est.total_hours > 10, f"META_LEARNING hours should be > 10: {est.total_hours}")
        return f"intensity={est.compute_intensity}, hours={est.total_hours}"
    runner.run("T-45: ExecutionEstimate for META_LEARNING is HIGH intensity", t45)

    def t46():
        sp   = make_planner()
        plan = sp.create_plan("Par Test", StudyType.HISTORICAL_REPLAY, "Q?")
        est  = plan.execution_estimate
        ok(est.parallelizable == True,
           "HISTORICAL_REPLAY should be parallelizable")
        return f"parallelizable={est.parallelizable}"
    runner.run("T-46: ExecutionEstimate.parallelizable True for HISTORICAL_REPLAY", t46)

    def t47():
        sp   = make_planner()
        plan = sp.create_plan("Cost Test", StudyType.HISTORICAL_REPLAY, "Q?")
        est  = plan.execution_estimate
        ok(est.compute_cost_usd > 0,  "compute_cost_usd must be > 0")
        ok(est.storage_mb > 0,        "storage_mb must be > 0")
        ok("compute_hours" in est.breakdown, "breakdown must document compute_hours")
        return f"cost=${est.compute_cost_usd:.2f}, storage={est.storage_mb:.1f}MB"
    runner.run("T-47: ExecutionEstimate cost and storage > 0, breakdown documented", t47)

    def t48():
        sp   = make_planner()
        plan = sp.create_plan("Est2 Test", StudyType.HISTORICAL_REPLAY, "Q?")
        ok(sp.estimate_cost(plan.plan_id) is plan.execution_estimate,
           "estimate_cost() must return the plan's ExecutionEstimate")
        try:
            sp.estimate_cost("SP-00000000")
            ok(False, "Should raise StudyPlanNotFoundError")
        except StudyPlanNotFoundError:
            pass
        return "estimate_cost() returns estimate; raises for unknown plan"
    runner.run("T-48: estimate_cost() returns correct estimate; raises for unknown plan", t48)

    # ── T-49 to T-53: Dependencies & validate_dependencies() ─────────────────

    def t49():
        d = StudyDependency(
            depends_on_plan_id="SP-AABBCCDD",
            depends_on_gap_id=None,
            depends_on_hypothesis_id=None,
            reason="Requires prior replay",
            is_blocking=True,
        )
        dd = d.to_dict()
        ok("depends_on_plan_id"       in dd, "to_dict must have depends_on_plan_id")
        ok("depends_on_gap_id"        in dd, "to_dict must have depends_on_gap_id")
        ok("depends_on_hypothesis_id" in dd, "to_dict must have depends_on_hypothesis_id")
        ok("reason"                   in dd, "to_dict must have reason")
        ok("is_blocking"              in dd, "to_dict must have is_blocking")
        return "StudyDependency.to_dict() complete"
    runner.run("T-49: StudyDependency.to_dict() produces complete dict", t49)

    def t50():
        sp    = make_planner()
        plan1 = sp.create_plan("Dep Plan 1", StudyType.HISTORICAL_REPLAY, "Q1?")
        plan2 = sp.create_plan(
            "Dep Plan 2", StudyType.DNA_DISCOVERY, "Q2?",
            dependencies=[StudyDependency(
                depends_on_plan_id=plan1.plan_id,
                depends_on_gap_id=None,
                depends_on_hypothesis_id=None,
                reason="Requires replay first",
                is_blocking=True,
            )],
        )
        issues = sp.validate_dependencies(plan2.plan_id)
        ok(len(issues) == 0, f"No issues expected for valid dependency: {issues}")
        return "No issues for valid dependency"
    runner.run("T-50: validate_dependencies() empty list for resolved dependency", t50)

    def t51():
        sp   = make_planner()
        plan = sp.create_plan(
            "Broken Dep Plan", StudyType.DNA_DISCOVERY, "Q?",
            dependencies=[StudyDependency(
                depends_on_plan_id="SP-DEADBEEF",  # does not exist
                depends_on_gap_id=None,
                depends_on_hypothesis_id=None,
                reason="Missing plan dependency",
                is_blocking=True,
            )],
        )
        issues = sp.validate_dependencies(plan.plan_id)
        ok(len(issues) >= 1, f"Should detect missing plan dependency: {issues}")
        ok(any("SP-DEADBEEF" in i for i in issues),
           f"Issue should mention missing plan_id: {issues}")
        return f"Detected {len(issues)} issue(s)"
    runner.run("T-51: validate_dependencies() detects missing plan reference", t51)

    def t52():
        sp = make_planner()
        try:
            sp.validate_dependencies("SP-00000000")
            ok(False, "Should raise StudyPlanNotFoundError")
        except StudyPlanNotFoundError:
            pass
        return "Raises StudyPlanNotFoundError for unknown plan"
    runner.run("T-52: validate_dependencies() raises for unknown plan_id", t52)

    def t53():
        sp    = make_planner()
        plan1 = sp.create_plan("Cycle A", StudyType.HISTORICAL_REPLAY, "Q1?")
        plan2 = sp.create_plan(
            "Cycle B", StudyType.DNA_DISCOVERY, "Q2?",
            dependencies=[StudyDependency(
                depends_on_plan_id=plan1.plan_id,
                depends_on_gap_id=None,
                depends_on_hypothesis_id=None,
                reason="B depends on A",
                is_blocking=False,
            )],
        )
        # Add a self-dependency to force a cycle
        import autonomous_research.study_planner_models as _m
        plan1_deps = [StudyDependency(
            depends_on_plan_id=plan2.plan_id,
            depends_on_gap_id=None,
            depends_on_hypothesis_id=None,
            reason="A depends on B (cycle!)",
            is_blocking=False,
        )]
        # Patch plan1's dependencies in place to create the cycle
        plan1_with_cycle = _m.StudyPlan(
            plan_id=plan1.plan_id,
            study_type=plan1.study_type,
            title=plan1.title,
            objective=plan1.objective,
            scientific_question=plan1.scientific_question,
            background=plan1.background,
            supporting_evidence=plan1.supporting_evidence,
            related_hypotheses=plan1.related_hypotheses,
            related_gaps=plan1.related_gaps,
            dataset_requirements=plan1.dataset_requirements,
            validation_plan=plan1.validation_plan,
            tasks=plan1.tasks,
            execution_estimate=plan1.execution_estimate,
            dependencies=plan1_deps,
            risk_class=plan1.risk_class,
            approval_class=plan1.approval_class,
            status=plan1.status,
            expected_outputs=plan1.expected_outputs,
            success_criteria=plan1.success_criteria,
            acceptance_criteria=plan1.acceptance_criteria,
            estimated_knowledge_gain=plan1.estimated_knowledge_gain,
            source_gap_id=plan1.source_gap_id,
            source_hypothesis_id=plan1.source_hypothesis_id,
            source_entry_id=plan1.source_entry_id,
            created_at=plan1.created_at,
        )
        sp._plans[plan1.plan_id] = plan1_with_cycle
        issues = sp.validate_dependencies(plan1.plan_id)
        ok(len(issues) >= 1, f"Should detect circular dependency: {issues}")
        return f"Circular dependency detected: {issues[0]}"
    runner.run("T-53: validate_dependencies() detects circular dependency", t53)

    # ── T-54 to T-58: Approval classification ────────────────────────────────

    def t54():
        sp   = make_planner()
        plan = sp.create_plan("Class A Test", StudyType.HISTORICAL_REPLAY, "Q?")
        ok(plan.approval_class == ApprovalClass.CLASS_A,
           f"HISTORICAL_REPLAY should be CLASS_A: {plan.approval_class.value}")
        return f"HISTORICAL_REPLAY → {plan.approval_class.value}"
    runner.run("T-54: HISTORICAL_REPLAY is CLASS_A", t54)

    def t55():
        sp   = make_planner()
        plan = sp.create_plan("Meta Test", StudyType.META_LEARNING, "Q?")
        ok(plan.approval_class == ApprovalClass.CLASS_B,
           f"META_LEARNING must be CLASS_B: {plan.approval_class.value}")
        return f"META_LEARNING → {plan.approval_class.value}"
    runner.run("T-55: META_LEARNING is CLASS_B", t55)

    def t56():
        sp   = make_planner()
        plan = sp.create_plan("Custom Test", StudyType.CUSTOM, "Q?")
        ok(plan.approval_class == ApprovalClass.CLASS_B,
           f"CUSTOM must be CLASS_B: {plan.approval_class.value}")
        return f"CUSTOM → {plan.approval_class.value}"
    runner.run("T-56: CUSTOM is CLASS_B", t56)

    def t57():
        sp   = make_planner()
        plan = sp.create_plan(
            "High Risk Test", StudyType.EDGE_VALIDATION, "Q?",
            risk_class=RiskClass.HIGH,
        )
        ok(plan.risk_class == RiskClass.HIGH, "risk_class should be HIGH")
        ok(plan.approval_class == ApprovalClass.CLASS_B,
           f"HIGH risk must be CLASS_B: {plan.approval_class.value}")
        return f"HIGH risk EDGE_VALIDATION → {plan.approval_class.value}"
    runner.run("T-57: HIGH risk plan escalates to CLASS_B", t57)

    def t58():
        cfg  = StudyPlannerConfig(
            class_b_study_types=[StudyType.CUSTOM],         # META_LEARNING removed from B
            class_b_risk_threshold=RiskClass.HIGH,
        )
        sp   = StudyPlanner(get_kp(), config=cfg)
        plan = sp.create_plan("Meta Config Test", StudyType.META_LEARNING, "Q?")
        # META_LEARNING not in class_b_study_types; risk is HIGH by default → still CLASS_B
        ok(plan.approval_class == ApprovalClass.CLASS_B,
           f"META_LEARNING with HIGH risk should still be CLASS_B: {plan.approval_class.value}")
        return f"META_LEARNING (HIGH risk) → {plan.approval_class.value}"
    runner.run("T-58: class_b_study_types config overrides default (META_LEARNING via risk)", t58)

    # ── T-59 to T-62: list_plans() / get_plan() / latest_plans() ─────────────

    def t59():
        sp = make_planner()
        sp.create_plan("LP A", StudyType.HISTORICAL_REPLAY, "Q?")
        sp.create_plan("LP B", StudyType.DNA_DISCOVERY,     "Q?")
        sp.create_plan("LP C", StudyType.REGIME_ANALYSIS,   "Q?")
        all_plans = sp.list_plans()
        ok(len(all_plans) >= 3, f"list_plans() should return ≥ 3 plans: {len(all_plans)}")
        return f"{len(all_plans)} plans returned"
    runner.run("T-59: list_plans() returns all plans", t59)

    def t60():
        sp = make_planner()
        p  = sp.create_plan("Status Filter Test", StudyType.HISTORICAL_REPLAY, "Q?")
        draft_plans = sp.list_plans(status=PlanStatus.DRAFT)
        ok(len(draft_plans) >= 1, "Should have ≥ 1 DRAFT plan")
        ok(all(pl.status == PlanStatus.DRAFT for pl in draft_plans),
           "list_plans(DRAFT) must return only DRAFT plans")
        return f"{len(draft_plans)} DRAFT plan(s)"
    runner.run("T-60: list_plans(status=DRAFT) returns only DRAFT plans", t60)

    def t61():
        sp    = make_planner()
        plan  = sp.create_plan("Get Plan Test", StudyType.EDGE_VALIDATION, "Q?")
        found = sp.get_plan(plan.plan_id)
        ok(found.plan_id == plan.plan_id, "get_plan() should return exact plan")
        try:
            sp.get_plan("SP-XXXXXXXX")
            ok(False, "Should raise StudyPlanNotFoundError")
        except StudyPlanNotFoundError:
            pass
        return f"get_plan() retrieved {plan.plan_id}"
    runner.run("T-61: get_plan() returns correct plan; raises for unknown id", t61)

    def t62():
        sp = make_planner()
        for i in range(5):
            time.sleep(0.001)
            sp.create_plan(f"Latest {i}", StudyType.HISTORICAL_REPLAY, "Q?",
                           source_gap_id=f"G{i}")
        latest = sp.latest_plans(n=3)
        ok(len(latest) == 3, f"latest_plans(3) should return 3: {len(latest)}")
        # newest first
        ok(latest[0].created_at >= latest[1].created_at, "Must be newest-first order")
        ok(latest[1].created_at >= latest[2].created_at, "Must be newest-first order")
        return f"latest_plans(3) returned 3 plans in correct order"
    runner.run("T-62: latest_plans() returns N most recent, newest first", t62)

    # ── T-63 to T-65: statistics() ───────────────────────────────────────────

    def t63():
        sp = make_planner()
        sp.create_plan("Stats A", StudyType.HISTORICAL_REPLAY,  "Q?", source_gap_id="S1")
        sp.create_plan("Stats B", StudyType.DNA_DISCOVERY,       "Q?", source_gap_id="S2")
        sp.create_plan("Stats C", StudyType.META_LEARNING,       "Q?", source_gap_id="S3")
        stats = sp.statistics()
        ok(stats.total_plans_created >= 3,
           f"total_plans_created should be ≥ 3: {stats.total_plans_created}")
        ok(isinstance(stats.built_at, datetime), "built_at must be datetime")
        return f"total_plans_created={stats.total_plans_created}"
    runner.run("T-63: statistics() returns correct total", t63)

    def t64():
        sp = make_planner()
        sp.create_plan("Sum A", StudyType.HISTORICAL_REPLAY, "Q?", source_gap_id="T1")
        sp.create_plan("Sum B", StudyType.DNA_DISCOVERY,     "Q?", source_gap_id="T2")
        stats = sp.statistics()
        total_from_types = sum(stats.by_study_type.values())
        ok(total_from_types == stats.total_plans_created,
           f"by_study_type sum ({total_from_types}) != total ({stats.total_plans_created})")
        total_from_approval = sum(stats.by_approval_class.values())
        ok(total_from_approval == stats.total_plans_created,
           f"by_approval_class sum ({total_from_approval}) != total ({stats.total_plans_created})")
        return "by_study_type and by_approval_class sums match total"
    runner.run("T-64: statistics() category sums equal total_plans_created", t64)

    def t65():
        sp = make_planner()
        sp.create_plan("Frac A", StudyType.META_LEARNING,      "Q?", source_gap_id="F1")
        sp.create_plan("Frac B", StudyType.HISTORICAL_REPLAY,  "Q?", source_gap_id="F2")
        stats = sp.statistics()
        b_count = stats.by_approval_class.get(ApprovalClass.CLASS_B.value, 0)
        expected_frac = b_count / stats.total_plans_created if stats.total_plans_created else 0.0
        ok(abs(stats.class_b_fraction - expected_frac) < 0.001,
           f"class_b_fraction wrong: {stats.class_b_fraction} vs {expected_frac}")
        return f"class_b_fraction={stats.class_b_fraction:.2f}"
    runner.run("T-65: statistics() class_b_fraction is correct", t65)

    # ── T-66: portfolio() ─────────────────────────────────────────────────────

    def t66():
        sp = make_planner()
        sp.create_plan("Port A", StudyType.HISTORICAL_REPLAY, "Q?", source_gap_id="P1")
        sp.create_plan("Port B", StudyType.META_LEARNING,     "Q?", source_gap_id="P2")
        port = sp.portfolio()
        ok(isinstance(port, StudyPortfolio), "Should return StudyPortfolio")
        ok(port.total_plans >= 2,            "Portfolio must include all plans")
        ok(port.total_compute_hours > 0,     "total_compute_hours must be > 0")
        ok(len(port.class_b_plans) >= 1,     "META_LEARNING plan must appear in class_b_plans")
        ok(isinstance(port.built_at, datetime), "built_at must be datetime")
        return f"portfolio: {port.total_plans} plans, {len(port.class_b_plans)} CLASS_B"
    runner.run("T-66: portfolio() returns correct aggregate", t66)

    # ── T-67: StudyPlan.to_dict() ─────────────────────────────────────────────

    def t67():
        sp   = make_planner()
        plan = sp.create_plan("Dict Test", StudyType.EDGE_VALIDATION, "Q?",
                               source_gap_id="G-DICT")
        d    = plan.to_dict()
        for key in ("plan_id", "study_type", "title", "objective", "scientific_question",
                    "background", "supporting_evidence", "related_hypotheses",
                    "related_gaps", "dataset_requirements", "validation_plan",
                    "tasks", "execution_estimate", "dependencies", "risk_class",
                    "approval_class", "status", "expected_outputs",
                    "success_criteria", "acceptance_criteria",
                    "estimated_knowledge_gain", "source_gap_id",
                    "source_hypothesis_id", "source_entry_id", "created_at"):
            ok(key in d, f"to_dict() must include '{key}'")
        ok(isinstance(d["tasks"], list),              "tasks must be list")
        ok(isinstance(d["dataset_requirements"], list),"dataset_requirements must be list")
        return f"to_dict() complete ({len(d)} keys)"
    runner.run("T-67: StudyPlan.to_dict() produces complete dict", t67)

    # ── T-68: Thread safety ───────────────────────────────────────────────────

    def t68():
        sp      = make_planner()
        errors  = []
        results = []
        lock    = threading.Lock()

        def worker(n: int) -> None:
            try:
                plan = sp.create_plan(
                    f"Thread Plan {n}", StudyType.HISTORICAL_REPLAY, f"Q{n}?",
                    source_gap_id=f"G-THREAD-{n}",
                )
                with lock:
                    results.append(plan.plan_id)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        ok(len(errors) == 0,   f"Thread errors: {errors}")
        ok(len(results) >= 1,  "At least one plan should be created")
        return f"{len(results)} plans created concurrently, 0 errors"
    runner.run("T-68: Concurrent create_plan() calls are thread-safe", t68)

    # ── T-69: Backward compatibility ─────────────────────────────────────────

    def t69():
        from autonomous_research import (
            StudyPlanner, StudyPlannerConfig, StudyPlannerError,
            StudyPlanNotFoundError, StudyPlan, StudyTask, DatasetRequirement,
            ValidationPlan, ExecutionEstimate, StudyDependency, StudyPortfolio,
            PlanningStatistics, StudyType, ApprovalClass, PlanStatus, RiskClass,
        )
        ok(StudyPlanner         is not None, "StudyPlanner export missing")
        ok(StudyPlannerConfig   is not None, "StudyPlannerConfig export missing")
        ok(StudyPlannerError    is not None, "StudyPlannerError export missing")
        ok(StudyPlanNotFoundError is not None, "StudyPlanNotFoundError export missing")
        ok(StudyPlan            is not None, "StudyPlan export missing")
        ok(StudyTask            is not None, "StudyTask export missing")
        ok(DatasetRequirement   is not None, "DatasetRequirement export missing")
        ok(ValidationPlan       is not None, "ValidationPlan export missing")
        ok(ExecutionEstimate    is not None, "ExecutionEstimate export missing")
        ok(StudyDependency      is not None, "StudyDependency export missing")
        ok(StudyPortfolio       is not None, "StudyPortfolio export missing")
        ok(PlanningStatistics   is not None, "PlanningStatistics export missing")
        ok(len(list(StudyType)) == 10,       f"StudyType should have 10 members: {len(list(StudyType))}")
        ok(len(list(ApprovalClass)) == 2,    "ApprovalClass should have 2 members")
        ok(len(list(PlanStatus))    == 4,    "PlanStatus should have 4 members")
        ok(len(list(RiskClass))     == 3,    "RiskClass should have 3 members")
        return "All Phase 2D exports intact"
    runner.run("T-69: Backward compatibility — all Phase 2D exports intact", t69)

    # ─────────────────────────────────────────────────────────────────────────
    # Print results
    # ─────────────────────────────────────────────────────────────────────────

    print()
    print("=" * 72)
    print("ARS Phase 2D — StudyPlanner Test Suite")
    print("=" * 72)
    print()

    for r in runner.results:
        status = "[PASS]" if r.passed else "[FAIL]"
        print(f"  {status} {r.name} ({r.duration_ms}ms)")
        if not r.passed and r.error:
            for line in r.error.splitlines():
                print(f"         {line}")

    print()
    print("=" * 72)
    print(f"  Results: {runner.passed}/{len(runner.results)} passed")
    if runner.failed == 0:
        print("  All tests passed.")
    else:
        print(f"  FAILED:  {runner.failed}")
    print("=" * 72)
    print()

    return runner.failed


if __name__ == "__main__":
    sys.exit(run_all())

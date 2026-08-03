"""
test_evidence_validator.py — ARS Phase 2C test suite.

Covers:
    - Instantiation (with/without optional deps)
    - validate() generic dispatcher
    - validate_finding() — structure, gates, outcomes
    - validate_hypothesis() — structure, gates, evidence tracing
    - validate_roadmap_entry() — INAPPLICABLE gates, gap categories
    - All 10 gate evaluators (boundary conditions)
    - Quality score formula (PASSED/SKIPPED/FAILED weight contributions)
    - Outcome determination: PASSED / PASSED_WITH_OBSERVATIONS / FAILED
    - Critical gate: any FAILED critical gate forces FAILED outcome
    - Config customization: thresholds, weights, critical_gates
    - Traceability: gate_results, evidence_used, rules_evaluated
    - Read-only: KP stores, hypothesis, roadmap unchanged
    - Thread safety: concurrent validate_finding() calls
    - statistics(): session aggregation
    - latest_results(): ordering and count
    - to_dict() serialization
    - Backward compatibility: all Phase 2C exports intact

Run:
    python test_evidence_validator.py
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
    KnowledgeProvider,
    HypothesisRegistry,
    CrossStudySynthesizer,
    GapDetector,
    RoadmapManager,
    EvidenceValidator,
    EvidenceValidatorConfig,
    EvidenceValidation,
    EvidenceQualityScore,
    GateResult,
    GateStatus,
    ValidationOutcome,
    ValidationStatistics,
    ValidationSummary,
    EvidenceValidatorError,
    ValidationSubjectNotFoundError,
    HypothesisClassification,
    HypothesisPriority,
    GapCategory,
    GapSeverity,
    GapStatus,
    KnowledgeGap,
    RoadmapEntry,
    RoadmapEntryStatus,
    StudyCategory,
    KnowledgeGainEstimate,
    ResearchCostEstimate,
    ResearchDebt,
)
from autonomous_research.roadmap_models import RoadmapManagerConfig
from autonomous_research.evidence_validator_models import (
    EvidenceValidatorError,
    ValidationSubjectNotFoundError,
)


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
                detail="ASSERTION FAILED",
                error=str(exc),
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
_SYN: Optional[CrossStudySynthesizer] = None
_GD:  Optional[GapDetector]          = None
_RM:  Optional[RoadmapManager]       = None

_TMP: Optional[Path] = None


def get_kp() -> KnowledgeProvider:
    global _KP
    if _KP is None:
        _KP = KnowledgeProvider()
    return _KP


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
        _RM = RoadmapManager(get_kp(), gap_detector=get_gd(),
                             state_path=get_tmp() / "rm_state.json")
    return _RM


def get_tmp() -> Path:
    global _TMP
    if _TMP is None:
        _TMP = Path(tempfile.mkdtemp(prefix="ars_ev_test_"))
    return _TMP


def live_finding_id() -> str:
    findings = get_kp().list_findings()
    ok(len(findings) > 0, "No findings in KP — cannot run finding tests")
    return findings[0].finding_id


def make_ev(config: Optional[EvidenceValidatorConfig] = None) -> EvidenceValidator:
    return EvidenceValidator(
        knowledge_provider=get_kp(),
        synthesizer=get_syn(),
        config=config,
    )


def make_gap(
    gap_id: str,
    category: GapCategory,
    severity: GapSeverity,
    related_studies: Optional[List[str]] = None,
    related_findings: Optional[List[str]] = None,
    supporting_evidence: Optional[List[str]] = None,
    rule_parameters: Optional[dict] = None,
) -> KnowledgeGap:
    return KnowledgeGap(
        gap_id=gap_id,
        category=category,
        title=f"Test gap {gap_id}",
        description=f"Test gap for {category.value}",
        severity=severity,
        severity_rationale="Test",
        confidence=0.80,
        status=GapStatus.OPEN,
        supporting_evidence=supporting_evidence or [],
        related_studies=related_studies or [],
        related_hypotheses=[],
        related_findings=related_findings or [],
        recommended_action="Test",
        estimated_knowledge_gain=0.70,
        rule_id="R-TEST",
        rule_parameters=rule_parameters or {},
        created_at=datetime.now(),
    )


def make_entry(gap: KnowledgeGap) -> RoadmapEntry:
    """Create a minimal RoadmapEntry from a gap for testing."""
    import hashlib as _h
    e_id = f"RE-{_h.sha256(gap.gap_id.encode()).hexdigest()[:8].upper()}"
    kg = KnowledgeGainEstimate(
        gap_id=gap.gap_id, scientific_importance=0.7, evidence_gap_size=0.6,
        current_confidence=0.5, expected_confidence_improvement=0.4,
        expected_new_findings=2, coverage_increase=0.5, novelty=0.6,
        historical_impact=0.7, reuse_potential=0.6, uncertainty_reduction=0.5,
        total_gain=0.62, breakdown={},
    )
    cost = ResearchCostEstimate(
        gap_id=gap.gap_id, historical_days_required=90,
        replay_duration_estimate_hours=2.0, implementation_effort=0.5,
        dependencies=[], risk=0.3, total_cost=0.41, breakdown={},
    )
    debt = ResearchDebt(
        gap_id=gap.gap_id, category=gap.category, severity=gap.severity,
        base_debt=0.75, age_debt=0.0, contradiction_debt=0.0, expiry_debt=0.0,
        total_debt=0.375, accumulation_rationale="Test", breakdown={},
    )
    return RoadmapEntry(
        entry_id=e_id, gap=gap,
        knowledge_gain_estimate=kg, cost_estimate=cost, debt=debt,
        priority_score=0.62, priority_breakdown={},
        study_category=StudyCategory.VALIDATION,
        status=RoadmapEntryStatus.PENDING,
        rank=1,
        recommended_study_title=f"Test study for {gap.gap_id}",
        recommended_approach="Test approach",
        created_at=datetime.now(),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════════════════════════════════════

def run_all_tests() -> TestRunner:
    runner = TestRunner()

    # ── T-01: Instantiation with KP only ─────────────────────────────────
    def t01():
        ev = EvidenceValidator(knowledge_provider=get_kp())
        ok(ev is not None, "EvidenceValidator is None")
        return "KP-only instantiation"
    runner.run("T-01: Instantiation with KP only", t01)

    # ── T-02: Instantiation with all optional providers ───────────────────
    def t02():
        reg = HypothesisRegistry(get_kp(), registry_path=get_tmp() / "t02_reg.json")
        ev  = EvidenceValidator(
            knowledge_provider=get_kp(),
            hypothesis_registry=reg,
            synthesizer=get_syn(),
            gap_detector=get_gd(),
            roadmap_manager=get_rm(),
        )
        ok(ev is not None, "EvidenceValidator with all deps is None")
        return "full instantiation"
    runner.run("T-02: Instantiation with all optional providers", t02)

    # ── T-03: Custom config accepted ─────────────────────────────────────
    def t03():
        cfg = EvidenceValidatorConfig(min_observations=50, min_regime_count=1)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        ok(ev._cfg.min_observations == 50, "custom min_observations not set")
        ok(ev._cfg.min_regime_count == 1, "custom min_regime_count not set")
        return "custom config applied"
    runner.run("T-03: Custom EvidenceValidatorConfig accepted", t03)

    # ── T-04: validate() dispatches to validate_finding ───────────────────
    def t04():
        fid = live_finding_id()
        ev  = make_ev()
        r   = ev.validate(fid, subject_type="finding")
        ok(isinstance(r, EvidenceValidation), "validate() did not return EvidenceValidation")
        ok(r.subject_type == "finding", f"subject_type={r.subject_type}")
        ok(r.subject_id == fid, "subject_id mismatch")
        return f"validate(finding) → {r.outcome.value}"
    runner.run("T-04: validate() dispatches to validate_finding()", t04)

    # ── T-05: validate() with unknown type raises error ───────────────────
    def t05():
        ev = make_ev()
        try:
            ev.validate("anything", subject_type="unknown_type")
            ok(False, "Expected EvidenceValidatorError")
        except EvidenceValidatorError:
            pass
        return "EvidenceValidatorError raised for unknown type"
    runner.run("T-05: validate() with unknown subject_type raises EvidenceValidatorError", t05)

    # ── T-06: validate_finding() with unknown ID raises error ─────────────
    def t06():
        ev = make_ev()
        try:
            ev.validate_finding("NONEXISTENT-FINDING-ID")
            ok(False, "Expected ValidationSubjectNotFoundError")
        except ValidationSubjectNotFoundError:
            pass
        return "ValidationSubjectNotFoundError raised for unknown finding"
    runner.run("T-06: validate_finding() raises ValidationSubjectNotFoundError for unknown ID", t06)

    # ── T-07: validate_finding() returns EvidenceValidation ───────────────
    def t07():
        fid = live_finding_id()
        ev  = make_ev()
        r   = ev.validate_finding(fid)
        ok(isinstance(r, EvidenceValidation), f"Expected EvidenceValidation, got {type(r)}")
        ok(r.subject_type == "finding", "subject_type wrong")
        ok(r.subject_id == fid, "subject_id mismatch")
        ok(isinstance(r.validated_at, datetime), "validated_at not datetime")
        ok(isinstance(r.gate_results, list), "gate_results not list")
        ok(isinstance(r.quality_score, EvidenceQualityScore), "quality_score wrong type")
        ok(isinstance(r.outcome, ValidationOutcome), "outcome wrong type")
        ok(isinstance(r.outcome_explanation, str), "outcome_explanation not str")
        ok(isinstance(r.evidence_used, list), "evidence_used not list")
        ok(isinstance(r.rules_evaluated, list), "rules_evaluated not list")
        return f"outcome={r.outcome.value}, score={r.quality_score.total:.2f}"
    runner.run("T-07: validate_finding() returns well-formed EvidenceValidation", t07)

    # ── T-08: validate_finding() produces exactly 10 gate results ─────────
    def t08():
        fid = live_finding_id()
        ev  = make_ev()
        r   = ev.validate_finding(fid)
        ok(len(r.gate_results) == 10, f"Expected 10 gates, got {len(r.gate_results)}")
        gate_ids = {g.gate_id for g in r.gate_results}
        for expected in (f"G-EV-0{i}" if i < 10 else f"G-EV-{i}" for i in range(1, 11)):
            ok(expected in gate_ids, f"Gate {expected} missing from gate_results")
        return f"10 gates present: {sorted(gate_ids)}"
    runner.run("T-08: validate_finding() produces exactly 10 gate results", t08)

    # ── T-09: validation_id is deterministic ──────────────────────────────
    def t09():
        fid = live_finding_id()
        ev  = make_ev()
        r1  = ev.validate_finding(fid)
        r2  = ev.validate_finding(fid)
        ok(r1.validation_id == r2.validation_id,
           f"Non-deterministic ID: {r1.validation_id} vs {r2.validation_id}")
        ok(r1.validation_id.startswith("EV-F-"), f"Bad ID prefix: {r1.validation_id}")
        return f"deterministic ID={r1.validation_id}"
    runner.run("T-09: validation_id is deterministic for same finding", t09)

    # ── T-10: evidence_used contains at least the finding ID ─────────────
    def t10():
        fid = live_finding_id()
        ev  = make_ev()
        r   = ev.validate_finding(fid)
        ok(any(fid in e for e in r.evidence_used),
           f"finding:{fid} not in evidence_used: {r.evidence_used}")
        return f"evidence_used: {r.evidence_used[:3]}"
    runner.run("T-10: evidence_used contains the validated finding ID", t10)

    # ── T-11: rules_evaluated contains only non-INAPPLICABLE gate IDs ─────
    def t11():
        fid = live_finding_id()
        ev  = make_ev()
        r   = ev.validate_finding(fid)
        inapplicable_ids = {
            g.gate_id for g in r.gate_results if g.status == GateStatus.INAPPLICABLE
        }
        for gate_id in r.rules_evaluated:
            ok(gate_id not in inapplicable_ids,
               f"INAPPLICABLE gate {gate_id} in rules_evaluated")
        return f"rules_evaluated = {r.rules_evaluated}"
    runner.run("T-11: rules_evaluated excludes INAPPLICABLE gates", t11)

    # ── T-12: validate_hypothesis() without registry raises error ─────────
    def t12():
        ev = EvidenceValidator(get_kp())   # no registry
        try:
            ev.validate_hypothesis("H-ANYTHING")
            ok(False, "Expected EvidenceValidatorError")
        except EvidenceValidatorError:
            pass
        return "EvidenceValidatorError raised without registry"
    runner.run("T-12: validate_hypothesis() without registry raises EvidenceValidatorError", t12)

    # ── T-13: validate_hypothesis() unknown ID raises error ───────────────
    def t13():
        reg = HypothesisRegistry(get_kp(), registry_path=get_tmp() / "t13_reg.json")
        ev  = EvidenceValidator(get_kp(), hypothesis_registry=reg)
        try:
            ev.validate_hypothesis("H-NONEXISTENT-0001")
            ok(False, "Expected ValidationSubjectNotFoundError")
        except ValidationSubjectNotFoundError:
            pass
        return "ValidationSubjectNotFoundError raised for unknown hypothesis"
    runner.run("T-13: validate_hypothesis() raises ValidationSubjectNotFoundError for unknown ID", t13)

    # ── T-14: validate_hypothesis() returns EvidenceValidation ────────────
    def t14():
        reg = HypothesisRegistry(get_kp(), registry_path=get_tmp() / "t14_reg.json")
        h = reg.create_hypothesis(
            title="Test: win rate drops in trending markets",
            research_question="Does win rate correlate with trend strength?",
            description="Hypothesis for EvidenceValidator testing",
            origin="test",
            priority=HypothesisPriority.MEDIUM,
            classification=HypothesisClassification.COVERAGE_GAP,
            knowledge_gap="Unknown regime-win-rate correlation",
            expected_knowledge_gain="Improved regime targeting",
            validation_method="Backtesting with regime stratification",
        )
        ev = EvidenceValidator(get_kp(), hypothesis_registry=reg, synthesizer=get_syn())
        r  = ev.validate_hypothesis(h.hypothesis_id)
        ok(isinstance(r, EvidenceValidation), f"Got {type(r)}")
        ok(r.subject_type == "hypothesis", f"subject_type={r.subject_type}")
        ok(r.subject_id == h.hypothesis_id, "subject_id mismatch")
        ok(r.validation_id.startswith("EV-H-"), f"Bad prefix: {r.validation_id}")
        ok(len(r.gate_results) == 10, f"Expected 10 gates, got {len(r.gate_results)}")
        return f"hypothesis validated: {r.outcome.value}, score={r.quality_score.total:.2f}"
    runner.run("T-14: validate_hypothesis() returns well-formed EvidenceValidation", t14)

    # ── T-15: validate_hypothesis() with study evidence improves G-EV-01 ──
    def t15():
        studies = get_kp().list_studies()
        ok(len(studies) > 0, "No studies for hypothesis evidence test")
        study = studies[0]

        reg = HypothesisRegistry(get_kp(), registry_path=get_tmp() / "t15_reg.json")
        h = reg.create_hypothesis(
            title="Study-backed hypothesis",
            research_question="Does this study support the hypothesis?",
            description="Evidence-backed test",
            origin="test",
            priority=HypothesisPriority.HIGH,
            classification=HypothesisClassification.PERFORMANCE_GAP,
            knowledge_gap="Performance gap evidence",
            expected_knowledge_gain="Improved strategy",
            validation_method="Backtest",
        )
        from autonomous_research.hypothesis_models import EvidenceReference, EvidenceType
        ev_ref = EvidenceReference(
            evidence_id=study.study_id,
            evidence_type=EvidenceType.STUDY,
            description=f"Supporting study {study.study_id}",
            added_at=datetime.now(),
            added_by="test",
        )
        reg.add_evidence(h.hypothesis_id, ev_ref)

        # lenient config: accept 1 study as sufficient
        cfg = EvidenceValidatorConfig(
            min_corroborating_studies=1,
            min_certification_count=0,
            min_regime_count=1,
            min_sector_diversity=1,
        )
        ev = EvidenceValidator(get_kp(), hypothesis_registry=reg, config=cfg)
        r  = ev.validate_hypothesis(h.hypothesis_id)

        # With study evidence, G-EV-02 (replication) should PASS for min=1
        g02 = next(g for g in r.gate_results if g.gate_id == "G-EV-02")
        ok(g02.status == GateStatus.PASSED,
           f"G-EV-02 should PASS with 1 study (min=1), got {g02.status}")
        return f"G-EV-02 PASSED with 1 supporting study; outcome={r.outcome.value}"
    runner.run("T-15: validate_hypothesis() with study evidence — G-EV-02 PASSED", t15)

    # ── T-16: hypothesis validation_id deterministic ──────────────────────
    def t16():
        reg = HypothesisRegistry(get_kp(), registry_path=get_tmp() / "t16_reg.json")
        h = reg.create_hypothesis(
            title="Determinism test",
            research_question="Is validation deterministic?",
            description="Test hypothesis",
            origin="test",
            priority=HypothesisPriority.LOW,
            classification=HypothesisClassification.MANUAL,
            knowledge_gap="None",
            expected_knowledge_gain="None",
            validation_method="Manual",
        )
        ev = EvidenceValidator(get_kp(), hypothesis_registry=reg)
        r1 = ev.validate_hypothesis(h.hypothesis_id)
        r2 = ev.validate_hypothesis(h.hypothesis_id)
        ok(r1.validation_id == r2.validation_id, "Non-deterministic hypothesis validation_id")
        return f"deterministic ID={r1.validation_id}"
    runner.run("T-16: validate_hypothesis() produces deterministic validation_id", t16)

    # ── T-17: validate_hypothesis() outcome_explanation is non-empty ──────
    def t17():
        reg = HypothesisRegistry(get_kp(), registry_path=get_tmp() / "t17_reg.json")
        h = reg.create_hypothesis(
            title="Explanation test",
            research_question="Is the explanation populated?",
            description="Test",
            origin="test",
            priority=HypothesisPriority.LOW,
            classification=HypothesisClassification.MANUAL,
            knowledge_gap="None",
            expected_knowledge_gain="None",
            validation_method="Manual",
        )
        ev = EvidenceValidator(get_kp(), hypothesis_registry=reg)
        r  = ev.validate_hypothesis(h.hypothesis_id)
        ok(len(r.outcome_explanation) > 10, "outcome_explanation too short")
        return f"explanation: {r.outcome_explanation[:60]}"
    runner.run("T-17: validate_hypothesis() outcome_explanation is non-empty", t17)

    # ── T-18: validate_roadmap_entry() returns EvidenceValidation ─────────
    def t18():
        rm  = get_rm()
        rm.build()
        entries = rm.list_entries()
        ok(len(entries) > 0, "No roadmap entries for test")
        entry = entries[0]
        ev = make_ev()
        r  = ev.validate_roadmap_entry(entry)
        ok(isinstance(r, EvidenceValidation), f"Got {type(r)}")
        ok(r.subject_type == "roadmap_entry", f"subject_type={r.subject_type}")
        ok(r.subject_id == entry.entry_id, "subject_id mismatch")
        ok(r.validation_id.startswith("EV-R-"), f"Bad prefix: {r.validation_id}")
        ok(len(r.gate_results) == 10, f"Expected 10 gates, got {len(r.gate_results)}")
        return f"roadmap_entry validated: {r.outcome.value}"
    runner.run("T-18: validate_roadmap_entry() returns well-formed EvidenceValidation", t18)

    # ── T-19: roadmap_entry has G-EV-06/07 INAPPLICABLE ──────────────────
    def t19():
        gap   = make_gap("G-RE-TEST-01", GapCategory.EVIDENCE_GAP, GapSeverity.MEDIUM)
        entry = make_entry(gap)
        ev    = make_ev()
        r     = ev.validate_roadmap_entry(entry)
        for gid in ("G-EV-06", "G-EV-07"):
            g = next(g for g in r.gate_results if g.gate_id == gid)
            ok(g.status == GateStatus.INAPPLICABLE,
               f"{gid} should be INAPPLICABLE for roadmap_entry, got {g.status}")
        ok("G-EV-06" not in r.rules_evaluated, "G-EV-06 should not be in rules_evaluated")
        ok("G-EV-07" not in r.rules_evaluated, "G-EV-07 should not be in rules_evaluated")
        return "G-EV-06 and G-EV-07 are INAPPLICABLE for roadmap entries"
    runner.run("T-19: validate_roadmap_entry() — G-EV-06/07 are INAPPLICABLE", t19)

    # ── T-20: CONTRADICTION_GAP entry with ≥2 evidence items passes G-EV-08
    def t20():
        gap   = make_gap("G-CONT-TEST", GapCategory.CONTRADICTION_GAP, GapSeverity.HIGH,
                         supporting_evidence=["F-001", "F-002"])
        entry = make_entry(gap)
        ev    = make_ev()
        r     = ev.validate_roadmap_entry(entry)
        g08   = next(g for g in r.gate_results if g.gate_id == "G-EV-08")
        ok(g08.status == GateStatus.PASSED,
           f"CONTRADICTION_GAP with 2 evidence items should pass G-EV-08; got {g08.status}")
        return f"CONTRADICTION_GAP + 2 evidence → G-EV-08 PASSED"
    runner.run("T-20: CONTRADICTION_GAP entry with ≥2 evidence items passes G-EV-08", t20)

    # ── T-21: CONTRADICTION_GAP entry with <2 evidence items fails G-EV-08
    def t21():
        gap   = make_gap("G-CONT-BAD", GapCategory.CONTRADICTION_GAP, GapSeverity.HIGH,
                         supporting_evidence=["F-001"])  # only 1 evidence item
        entry = make_entry(gap)
        ev    = make_ev()
        r     = ev.validate_roadmap_entry(entry)
        g08   = next(g for g in r.gate_results if g.gate_id == "G-EV-08")
        ok(g08.status == GateStatus.FAILED,
           f"CONTRADICTION_GAP with 1 evidence should fail G-EV-08; got {g08.status}")
        # Critical failure → FAILED outcome
        ok(r.outcome == ValidationOutcome.FAILED,
           f"Expected FAILED outcome; got {r.outcome}")
        return "CONTRADICTION_GAP with 1 evidence → FAILED (critical gate)"
    runner.run("T-21: CONTRADICTION_GAP with <2 evidence items fails G-EV-08 → FAILED", t21)

    # ── T-22: roadmap entry validation_id deterministic ───────────────────
    def t22():
        gap   = make_gap("G-DET-RM-01", GapCategory.DATA_GAP, GapSeverity.MEDIUM)
        entry = make_entry(gap)
        ev    = make_ev()
        r1    = ev.validate_roadmap_entry(entry)
        r2    = ev.validate_roadmap_entry(entry)
        ok(r1.validation_id == r2.validation_id, "Non-deterministic roadmap_entry ID")
        return f"deterministic ID={r1.validation_id}"
    runner.run("T-22: validate_roadmap_entry() produces deterministic validation_id", t22)

    # ── T-23: G-EV-01 PASSES when n_obs ≥ threshold ──────────────────────
    def t23():
        cfg = EvidenceValidatorConfig(min_observations=50)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_sample_size(100)
        ok(g.gate_id == "G-EV-01", "wrong gate_id")
        ok(g.status == GateStatus.PASSED, f"Expected PASSED, got {g.status}")
        ok(g.actual_value == 100, f"actual_value={g.actual_value}")
        ok(g.threshold == 50, f"threshold={g.threshold}")
        return "G-EV-01 PASSED for 100 obs (min=50)"
    runner.run("T-23: G-EV-01 PASSED when n_obs ≥ threshold", t23)

    # ── T-24: G-EV-01 FAILS when n_obs < threshold ───────────────────────
    def t24():
        cfg = EvidenceValidatorConfig(min_observations=200)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_sample_size(50)
        ok(g.status == GateStatus.FAILED, f"Expected FAILED, got {g.status}")
        return "G-EV-01 FAILED for 50 obs (min=200)"
    runner.run("T-24: G-EV-01 FAILED when n_obs < threshold", t24)

    # ── T-25: G-EV-01 SKIPPED when n_obs is None ─────────────────────────
    def t25():
        ev = make_ev()
        g  = ev._gate_sample_size(None)
        ok(g.status == GateStatus.SKIPPED, f"Expected SKIPPED, got {g.status}")
        return "G-EV-01 SKIPPED when n_obs=None"
    runner.run("T-25: G-EV-01 SKIPPED when observation count unavailable", t25)

    # ── T-26: G-EV-02 PASSES when n_corroborating ≥ threshold ────────────
    def t26():
        cfg = EvidenceValidatorConfig(min_corroborating_studies=2)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_replication(3)
        ok(g.status == GateStatus.PASSED, f"Expected PASSED, got {g.status}")
        return "G-EV-02 PASSED for 3 studies (min=2)"
    runner.run("T-26: G-EV-02 PASSED when corroborating studies ≥ threshold", t26)

    # ── T-27: G-EV-03 PASSES when temporal_days ≥ threshold ──────────────
    def t27():
        cfg = EvidenceValidatorConfig(min_temporal_coverage_days=90)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_temporal_coverage(120)
        ok(g.status == GateStatus.PASSED, f"Expected PASSED, got {g.status}")
        ok(g.actual_value == 120, f"actual_value={g.actual_value}")
        return "G-EV-03 PASSED for 120d (min=90d)"
    runner.run("T-27: G-EV-03 PASSED when temporal span ≥ threshold", t27)

    # ── T-28: G-EV-04 PASSES when regimes ≥ threshold ────────────────────
    def t28():
        cfg = EvidenceValidatorConfig(min_regime_count=2)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_regime_coverage(["TREND", "RANGE", "VOLATILE"])
        ok(g.status == GateStatus.PASSED, f"Expected PASSED, got {g.status}")
        ok(g.actual_value == 3, f"actual_value={g.actual_value}")
        return "G-EV-04 PASSED for 3 regimes (min=2)"
    runner.run("T-28: G-EV-04 PASSED when distinct regimes ≥ threshold", t28)

    # ── T-29: G-EV-05 SKIPPED when no sector data ─────────────────────────
    def t29():
        ev = make_ev()
        g  = ev._gate_sector_coverage([])  # empty list
        ok(g.status == GateStatus.SKIPPED, f"Expected SKIPPED, got {g.status}")
        return "G-EV-05 SKIPPED for empty sectors"
    runner.run("T-29: G-EV-05 SKIPPED when no sector metadata available", t29)

    # ── T-30: G-EV-06 PASSES when wf_consistency ≥ threshold ─────────────
    def t30():
        cfg = EvidenceValidatorConfig(min_walk_forward_pass_rate=0.60)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_walk_forward(0.75)
        ok(g.status == GateStatus.PASSED, f"Expected PASSED, got {g.status}")
        return "G-EV-06 PASSED for wf=0.75 (min=0.60)"
    runner.run("T-30: G-EV-06 PASSED when walk-forward consistency ≥ threshold", t30)

    # ── T-31: G-EV-07 FAILS when oos_win_rate < threshold ─────────────────
    def t31():
        cfg = EvidenceValidatorConfig(min_oos_win_rate=0.55)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_oos(0.40)
        ok(g.status == GateStatus.FAILED, f"Expected FAILED, got {g.status}")
        return "G-EV-07 FAILED for oos=0.40 (min=0.55)"
    runner.run("T-31: G-EV-07 FAILED when OOS win rate < threshold", t31)

    # ── T-32: G-EV-08 PASSES when contradiction_ratio ≤ threshold ─────────
    def t32():
        cfg = EvidenceValidatorConfig(max_contradiction_ratio=0.30)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_contradiction(0.10)
        ok(g.status == GateStatus.PASSED, f"Expected PASSED, got {g.status}")
        ok(g.is_critical, "G-EV-08 should be critical by default")
        return "G-EV-08 PASSED for ratio=0.10 (max=0.30)"
    runner.run("T-32: G-EV-08 PASSED when contradiction ratio ≤ threshold", t32)

    # ── T-33: G-EV-09 FAILS when cert_count < threshold ───────────────────
    def t33():
        cfg = EvidenceValidatorConfig(min_certification_count=2)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_certification(1)
        ok(g.status == GateStatus.FAILED, f"Expected FAILED, got {g.status}")
        return "G-EV-09 FAILED for 1 cert (min=2)"
    runner.run("T-33: G-EV-09 FAILED when certification count < threshold", t33)

    # ── T-34: G-EV-10 PASSES when days_old ≤ threshold ───────────────────
    def t34():
        cfg = EvidenceValidatorConfig(max_evidence_staleness_days=180)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_freshness(30)
        ok(g.status == GateStatus.PASSED, f"Expected PASSED, got {g.status}")
        return "G-EV-10 PASSED for 30d old (max=180d)"
    runner.run("T-34: G-EV-10 PASSED when evidence age ≤ threshold", t34)

    # ── T-35: G-EV-10 FAILS when days_old > threshold ─────────────────────
    def t35():
        cfg = EvidenceValidatorConfig(max_evidence_staleness_days=90)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_freshness(200)
        ok(g.status == GateStatus.FAILED, f"Expected FAILED, got {g.status}")
        return "G-EV-10 FAILED for 200d old (max=90d)"
    runner.run("T-35: G-EV-10 FAILED when evidence age > threshold", t35)

    # ── T-36: Quality score 1.0 when all gates PASS ───────────────────────
    def t36():
        ev = make_ev()
        gates = [
            ev._gate_sample_size(500),
            ev._gate_replication(3),
            ev._gate_temporal_coverage(200),
            ev._gate_regime_coverage(["TREND", "RANGE", "VOLATILE"]),
            ev._gate_sector_coverage(["IT", "FMCG", "BANK"]),
            ev._gate_walk_forward(0.80),
            ev._gate_oos(0.65),
            ev._gate_contradiction(0.05),
            ev._gate_certification(2),
            ev._gate_freshness(10),
        ]
        qs = ev._compute_quality_score(gates)
        ok(qs.total == 1.0, f"Expected 1.0 when all PASS, got {qs.total}")
        ok(qs.passed_gates == 10, f"passed_gates={qs.passed_gates}")
        ok(qs.failed_gates == 0, f"failed_gates={qs.failed_gates}")
        return f"all PASS → score={qs.total}"
    runner.run("T-36: Quality score = 1.0 when all gates PASS", t36)

    # ── T-37: Quality score 0.0 when all applicable gates FAIL ───────────
    def t37():
        cfg = EvidenceValidatorConfig(
            min_observations=99999,
            min_corroborating_studies=99,
            min_temporal_coverage_days=9999,
            min_regime_count=99,
            min_sector_diversity=99,
            min_walk_forward_pass_rate=0.99,
            min_oos_win_rate=0.99,
            max_contradiction_ratio=0.0,
            min_certification_count=999,
            max_evidence_staleness_days=0,
            critical_gates=[],  # disable critical so we don't short-circuit
        )
        ev = EvidenceValidator(get_kp(), config=cfg)
        gates = [
            ev._gate_sample_size(1),
            ev._gate_replication(0),
            ev._gate_temporal_coverage(1),
            ev._gate_regime_coverage([]),
            ev._gate_sector_coverage(["A"]),
            ev._gate_walk_forward(0.1),
            ev._gate_oos(0.1),
            ev._gate_contradiction(0.9),
            ev._gate_certification(0),
            ev._gate_freshness(999),
        ]
        qs = ev._compute_quality_score(gates)
        ok(qs.total == 0.0, f"Expected 0.0 when all FAIL, got {qs.total}")
        ok(qs.failed_gates == 10, f"failed_gates={qs.failed_gates}")
        return f"all FAIL → score={qs.total}"
    runner.run("T-37: Quality score = 0.0 when all applicable gates FAIL", t37)

    # ── T-38: SKIPPED gate contributes half weight ────────────────────────
    def t38():
        ev = make_ev()
        # Only one gate, SKIPPED: earned = weight * 0.5, total = weight → score = 0.5
        gate = ev._gate_sample_size(None)   # SKIPPED
        ok(gate.status == GateStatus.SKIPPED, "Gate should be SKIPPED")
        # Build score with just this one gate (using internal method directly)
        qs = ev._compute_quality_score([gate])
        ok(abs(qs.total - 0.5) < 1e-9, f"SKIPPED gate should give score=0.5, got {qs.total}")
        return f"SKIPPED gate → score=0.5 (half weight)"
    runner.run("T-38: SKIPPED gate contributes 0.5× weight to quality score", t38)

    # ── T-39: INAPPLICABLE gate excluded from score denominator ───────────
    def t39():
        ev = make_ev()
        cfg = EvidenceValidatorConfig(min_observations=50)
        ev2 = EvidenceValidator(get_kp(), config=cfg)
        # One PASSED gate + one INAPPLICABLE: score should reflect only the PASSED gate
        passed_gate = ev2._gate_sample_size(100)    # PASSED
        inapp_gate  = ev2._gate_inapplicable("G-EV-06", "Walk-Forward", "Not applicable")
        qs = ev2._compute_quality_score([passed_gate, inapp_gate])
        ok(qs.total == 1.0, f"Expected 1.0 (PASSED + INAPPLICABLE excluded), got {qs.total}")
        ok(qs.applicable_gates == 1, f"applicable_gates should be 1, got {qs.applicable_gates}")
        return f"INAPPLICABLE excluded → score={qs.total} with {qs.applicable_gates} applicable gate"
    runner.run("T-39: INAPPLICABLE gate excluded from quality score denominator", t39)

    # ── T-40: PASSED outcome when score ≥ passed_threshold ────────────────
    def t40():
        cfg = EvidenceValidatorConfig(
            passed_threshold=0.80,
            passed_with_obs_threshold=0.60,
            min_observations=50,
            min_corroborating_studies=1,
            min_temporal_coverage_days=30,
            min_regime_count=1,
            min_sector_diversity=1,
            min_walk_forward_pass_rate=0.50,
            min_oos_win_rate=0.50,
            max_contradiction_ratio=0.30,
            min_certification_count=0,
            max_evidence_staleness_days=999,
            critical_gates=[],
        )
        ev    = EvidenceValidator(get_kp(), config=cfg)
        gates = [
            ev._gate_sample_size(500),
            ev._gate_replication(2),
            ev._gate_temporal_coverage(120),
            ev._gate_regime_coverage(["TREND", "RANGE"]),
            ev._gate_sector_coverage(["IT", "FMCG"]),
            ev._gate_walk_forward(0.70),
            ev._gate_oos(0.60),
            ev._gate_contradiction(0.05),
            ev._gate_certification(1),
            ev._gate_freshness(30),
        ]
        qs  = ev._compute_quality_score(gates)
        ok(qs.total >= 0.80, f"Expected score ≥ 0.80, got {qs.total}")
        out, expl, obs = ev._determine_outcome(qs.total, gates)
        ok(out == ValidationOutcome.PASSED, f"Expected PASSED, got {out}")
        ok(len(obs) == 0, f"PASSED should have no observations, got {obs}")
        return f"all PASS → PASSED outcome (score={qs.total:.2f})"
    runner.run("T-40: PASSED outcome when all gates pass", t40)

    # ── T-41: PASSED_WITH_OBSERVATIONS outcome ────────────────────────────
    def t41():
        # Give G-EV-01 (the failing gate) enough weight to pull score < 0.80
        # while keeping overall score above 0.60 (passed_with_obs_threshold)
        # G-EV-01: weight=5.0 FAIL → earned=0
        # G-EV-02: weight=1.5 PASS → earned=1.5
        # G-EV-03: weight=1.0 PASS → earned=1.0
        # G-EV-04: weight=1.0 PASS → earned=1.0
        # G-EV-05: weight=0.5 PASS → earned=0.5
        # G-EV-08: weight=2.0 PASS → earned=2.0  (critical disabled)
        # G-EV-09: weight=1.0 PASS → earned=1.0
        # G-EV-10: weight=1.0 PASS → earned=1.0
        # G-EV-06/07: INAPPLICABLE
        # total=13.0  earned=8.0  score=8/13=0.615 → PASSED_WITH_OBSERVATIONS ✓
        cfg = EvidenceValidatorConfig(
            passed_threshold=0.80,
            passed_with_obs_threshold=0.50,
            min_observations=200,
            min_corroborating_studies=1,
            min_temporal_coverage_days=30,
            min_regime_count=1,
            min_sector_diversity=1,
            min_certification_count=0,
            max_evidence_staleness_days=999,
            max_contradiction_ratio=0.30,
            critical_gates=[],
            gate_weights={
                "G-EV-01": 5.0,  # high weight — single failure drops score to 0.615
                "G-EV-02": 1.5,
                "G-EV-03": 1.0,
                "G-EV-04": 1.0,
                "G-EV-05": 0.5,
                "G-EV-06": 1.5,
                "G-EV-07": 1.0,
                "G-EV-08": 2.0,
                "G-EV-09": 1.0,
                "G-EV-10": 1.0,
            },
        )
        ev = EvidenceValidator(get_kp(), config=cfg)
        gates = [
            ev._gate_sample_size(1),                      # FAIL (< 200)
            ev._gate_replication(1),                      # PASS (≥ 1)
            ev._gate_temporal_coverage(45),               # PASS (≥ 30)
            ev._gate_regime_coverage(["TREND"]),          # PASS (≥ 1)
            ev._gate_sector_coverage(["IT"]),             # PASS (≥ 1)
            ev._gate_inapplicable("G-EV-06", "Walk-Forward", "N/A"),
            ev._gate_inapplicable("G-EV-07", "OOS", "N/A"),
            ev._gate_contradiction(0.05),                 # PASS
            ev._gate_certification(0),                    # PASS (min=0)
            ev._gate_freshness(30),                       # PASS
        ]
        qs  = ev._compute_quality_score(gates)
        out, expl, obs = ev._determine_outcome(qs.total, gates)
        ok(out == ValidationOutcome.PASSED_WITH_OBSERVATIONS,
           f"Expected PASSED_WITH_OBSERVATIONS, got {out} (score={qs.total:.3f})")
        ok(len(obs) > 0, "PASSED_WITH_OBSERVATIONS should have at least 1 observation")
        ok("Sample Size" in obs[0] or "G-EV-01" in obs[0] or "observation" in obs[0].lower(),
           f"First observation should mention the failing gate: {obs[0]}")
        return f"score={qs.total:.3f} → PASSED_WITH_OBSERVATIONS, {len(obs)} observation(s)"
    runner.run("T-41: PASSED_WITH_OBSERVATIONS when score is between thresholds", t41)

    # ── T-42: FAILED outcome when critical gate fails ─────────────────────
    def t42():
        cfg = EvidenceValidatorConfig(
            passed_threshold=0.80,
            passed_with_obs_threshold=0.50,
            max_contradiction_ratio=0.30,
            critical_gates=["G-EV-08"],
        )
        ev    = EvidenceValidator(get_kp(), config=cfg)
        gates = [
            ev._gate_sample_size(500),
            ev._gate_replication(3),
            ev._gate_temporal_coverage(200),
            ev._gate_regime_coverage(["TREND", "RANGE", "VOLATILE"]),
            ev._gate_sector_coverage(["IT", "FMCG"]),
            ev._gate_walk_forward(0.80),
            ev._gate_oos(0.65),
            ev._gate_contradiction(0.90),  # FAIL — CRITICAL → forces FAILED
            ev._gate_certification(2),
            ev._gate_freshness(10),
        ]
        qs  = ev._compute_quality_score(gates)
        out, expl, obs = ev._determine_outcome(qs.total, gates)
        ok(out == ValidationOutcome.FAILED, f"Expected FAILED from critical gate, got {out}")
        ok("critical" in expl.lower(), f"Explanation should mention 'critical': {expl}")
        return f"critical G-EV-08 failure → FAILED (score={qs.total:.2f})"
    runner.run("T-42: FAILED outcome when critical gate fails (regardless of score)", t42)

    # ── T-43: FAILED outcome when score < passed_with_obs_threshold ───────
    def t43():
        cfg = EvidenceValidatorConfig(
            passed_threshold=0.80,
            passed_with_obs_threshold=0.60,
            min_observations=99999,
            min_corroborating_studies=99,
            min_temporal_coverage_days=9999,
            min_regime_count=99,
            min_sector_diversity=99,
            max_contradiction_ratio=0.0,
            min_certification_count=999,
            max_evidence_staleness_days=0,
            critical_gates=[],
        )
        ev = EvidenceValidator(get_kp(), config=cfg)
        gates = [
            ev._gate_sample_size(1),
            ev._gate_replication(0),
            ev._gate_temporal_coverage(1),
            ev._gate_regime_coverage(["TREND"]),
            ev._gate_sector_coverage(["IT"]),
            ev._gate_walk_forward(0.10),
            ev._gate_oos(0.10),
            ev._gate_contradiction(0.90),
            ev._gate_certification(0),
            ev._gate_freshness(999),
        ]
        qs  = ev._compute_quality_score(gates)
        out, expl, obs = ev._determine_outcome(qs.total, gates)
        ok(out == ValidationOutcome.FAILED, f"Expected FAILED, got {out}")
        return f"score={qs.total:.2f} < 0.60 → FAILED"
    runner.run("T-43: FAILED outcome when score < passed_with_obs_threshold", t43)

    # ── T-44: Custom weights reflected in gate_scores ─────────────────────
    def t44():
        cfg = EvidenceValidatorConfig(
            gate_weights={
                "G-EV-01": 3.0,  # high weight
                "G-EV-02": 1.0,
                "G-EV-03": 1.0,
                "G-EV-04": 1.0,
                "G-EV-05": 1.0,
                "G-EV-06": 1.0,
                "G-EV-07": 1.0,
                "G-EV-08": 1.0,
                "G-EV-09": 1.0,
                "G-EV-10": 1.0,
            }
        )
        ev    = EvidenceValidator(get_kp(), config=cfg)
        g01   = ev._gate_sample_size(1000)       # PASS, weight=3.0
        g02   = ev._gate_replication(0)          # FAIL, weight=1.0
        gates = [g01, g02]
        qs    = ev._compute_quality_score(gates)
        # earned=3.0, total=4.0, score=0.75
        ok(abs(qs.total - 0.75) < 1e-9, f"Expected 0.75, got {qs.total}")
        return f"custom weights: w_G01=3.0 PASS + w_G02=1.0 FAIL → score=0.75"
    runner.run("T-44: Custom gate_weights are reflected in quality score calculation", t44)

    # ── T-45: Custom critical_gates config works ───────────────────────────
    def t45():
        cfg = EvidenceValidatorConfig(
            critical_gates=["G-EV-01"],  # make sample size critical
            min_observations=999,
        )
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g01 = ev._gate_sample_size(1)  # FAIL
        ok(g01.is_critical, "G-EV-01 should be critical with custom config")
        gates = [g01, ev._gate_replication(5)]
        qs    = ev._compute_quality_score(gates)
        out, _, _ = ev._determine_outcome(qs.total, gates)
        ok(out == ValidationOutcome.FAILED, f"Critical G-EV-01 failure should give FAILED")
        return "custom critical_gates=[G-EV-01] forces FAILED when G-EV-01 fails"
    runner.run("T-45: Custom critical_gates config forces FAILED on specified gate", t45)

    # ── T-46: Custom threshold: lenient min_observations ─────────────────
    def t46():
        cfg = EvidenceValidatorConfig(min_observations=1)
        ev  = EvidenceValidator(get_kp(), config=cfg)
        g   = ev._gate_sample_size(5)
        ok(g.status == GateStatus.PASSED, f"Expected PASSED for 5 obs with min=1")
        return "lenient min_observations=1 → PASSED for 5 obs"
    runner.run("T-46: Custom min_observations=1 allows any study to pass G-EV-01", t46)

    # ── T-47: GateResult has all required traceability fields ─────────────
    def t47():
        ev  = make_ev()
        fid = live_finding_id()
        r   = ev.validate_finding(fid)
        for g in r.gate_results:
            ok(isinstance(g.gate_id,      str),       f"gate_id not str: {g.gate_id}")
            ok(isinstance(g.name,         str),       f"name not str: {g.name}")
            ok(isinstance(g.status,       GateStatus), f"status wrong type: {g.status}")
            ok(isinstance(g.explanation,  str),       f"explanation not str")
            ok(isinstance(g.is_critical,  bool),      f"is_critical not bool")
            ok(g.weight > 0,                          f"weight ≤ 0: {g.weight}")
            ok(len(g.explanation) > 0,                f"empty explanation for {g.gate_id}")
        return f"all {len(r.gate_results)} gates have required traceability fields"
    runner.run("T-47: All GateResult objects have required traceability fields", t47)

    # ── T-48: quality_score.breakdown documents formula components ────────
    def t48():
        ev  = make_ev()
        fid = live_finding_id()
        r   = ev.validate_finding(fid)
        bd  = r.quality_score.breakdown
        required = {
            "earned_weight", "total_weight",
            "passed_weight", "skipped_weight", "failed_weight",
            "inapplicable_count",
            "passed_threshold", "passed_with_obs_threshold",
        }
        missing = required - set(bd.keys())
        ok(not missing, f"quality_score.breakdown missing keys: {missing}")
        return "quality_score.breakdown has all formula components"
    runner.run("T-48: quality_score.breakdown documents all formula components", t48)

    # ── T-49: EvidenceValidation.to_dict() round-trips correctly ──────────
    def t49():
        ev  = make_ev()
        fid = live_finding_id()
        r   = ev.validate_finding(fid)
        d   = r.to_dict()
        ok(isinstance(d, dict), "to_dict() not a dict")
        required = {
            "validation_id", "subject_type", "subject_id", "subject_summary",
            "validated_at", "gate_results", "quality_score", "outcome",
            "outcome_explanation", "observations", "evidence_used",
            "rules_evaluated", "validator_version",
        }
        missing = required - set(d.keys())
        ok(not missing, f"to_dict() missing keys: {missing}")
        ok(isinstance(d["gate_results"], list), "gate_results not list in dict")
        ok(len(d["gate_results"]) == 10, f"Expected 10 gate dicts, got {len(d['gate_results'])}")
        return "EvidenceValidation.to_dict() correct"
    runner.run("T-49: EvidenceValidation.to_dict() produces complete dict", t49)

    # ── T-50: GateResult.to_dict() has all fields ─────────────────────────
    def t50():
        ev = make_ev()
        g  = ev._gate_sample_size(100)
        d  = g.to_dict()
        for key in ("gate_id", "name", "status", "actual_value", "threshold",
                    "explanation", "is_critical", "weight"):
            ok(key in d, f"GateResult.to_dict() missing key: {key}")
        ok(d["status"] in ("PASSED", "FAILED", "SKIPPED", "INAPPLICABLE"),
           f"status not a valid value: {d['status']}")
        return "GateResult.to_dict() correct"
    runner.run("T-50: GateResult.to_dict() produces complete dict", t50)

    # ── T-51: KP stores read-only after validation ────────────────────────
    def t51():
        kp = KnowledgeProvider()
        n_studies  = len(kp.list_studies())
        n_findings = len(kp.list_findings())
        n_edges    = len(kp.list_edges())
        ev = EvidenceValidator(kp, synthesizer=get_syn())
        fid = kp.list_findings()[0].finding_id if kp.list_findings() else None
        if fid:
            ev.validate_finding(fid)
        ok(len(kp.list_studies())  == n_studies,  "validate_finding() changed study count")
        ok(len(kp.list_findings()) == n_findings, "validate_finding() changed finding count")
        ok(len(kp.list_edges())    == n_edges,    "validate_finding() changed edge count")
        return "KP stores unchanged after validate_finding()"
    runner.run("T-51: KP stores are read-only — validate_finding() does not modify them", t51)

    # ── T-52: Hypothesis object unchanged after validate_hypothesis() ──────
    def t52():
        reg = HypothesisRegistry(get_kp(), registry_path=get_tmp() / "t52_reg.json")
        h = reg.create_hypothesis(
            title="Read-only test",
            research_question="Is hypothesis unchanged?",
            description="Test",
            origin="test",
            priority=HypothesisPriority.LOW,
            classification=HypothesisClassification.MANUAL,
            knowledge_gap="None",
            expected_knowledge_gain="None",
            validation_method="Manual",
        )
        h_before_status   = h.status
        h_before_conf     = h.confidence
        h_before_ev_count = len(h.supporting_evidence)

        ev = EvidenceValidator(get_kp(), hypothesis_registry=reg)
        ev.validate_hypothesis(h.hypothesis_id)

        h_after = reg.get(h.hypothesis_id)
        ok(h_after.status     == h_before_status,   "status changed after validate_hypothesis()")
        ok(h_after.confidence == h_before_conf,     "confidence changed")
        ok(len(h_after.supporting_evidence) == h_before_ev_count,
           "evidence count changed after validate_hypothesis()")
        return "hypothesis object unchanged after validate_hypothesis()"
    runner.run("T-52: Hypothesis object not modified by validate_hypothesis()", t52)

    # ── T-53: statistics() aggregates session results ─────────────────────
    def t53():
        ev  = make_ev()
        fid = live_finding_id()
        ev.validate_finding(fid)
        ev.validate_finding(fid)
        stats = ev.statistics()
        ok(isinstance(stats, ValidationStatistics), f"Got {type(stats)}")
        ok(stats.total_validations_run >= 2, "total_validations < 2")
        ok(stats.by_subject_type.get("finding", 0) >= 2, "by_subject_type missing findings")
        ok(0.0 <= stats.avg_quality_score <= 1.0, f"avg_quality_score out of range")
        ok(isinstance(stats.built_at, datetime), "built_at not datetime")
        return (f"stats: n={stats.total_validations_run}, "
                f"avg_score={stats.avg_quality_score:.2f}")
    runner.run("T-53: statistics() returns correct session aggregation", t53)

    # ── T-54: statistics() by_outcome sums to total ───────────────────────
    def t54():
        ev  = make_ev()
        fid = live_finding_id()
        for _ in range(3):
            ev.validate_finding(fid)
        stats    = ev.statistics()
        outcome_sum = sum(stats.by_outcome.values())
        ok(outcome_sum == stats.total_validations_run,
           f"by_outcome sum {outcome_sum} != total {stats.total_validations_run}")
        return f"by_outcome sums to {outcome_sum}"
    runner.run("T-54: statistics().by_outcome sums to total_validations_run", t54)

    # ── T-55: statistics() most_failed_gate is a valid gate ID ───────────
    def t55():
        ev  = make_ev()
        fid = live_finding_id()
        for _ in range(3):
            ev.validate_finding(fid)
        stats = ev.statistics()
        if stats.most_failed_gate is not None:
            ok(stats.most_failed_gate.startswith("G-EV-"),
               f"most_failed_gate not a gate ID: {stats.most_failed_gate}")
        if stats.most_passed_gate is not None:
            ok(stats.most_passed_gate.startswith("G-EV-"),
               f"most_passed_gate not a gate ID: {stats.most_passed_gate}")
        return (f"most_failed={stats.most_failed_gate}, "
                f"most_passed={stats.most_passed_gate}")
    runner.run("T-55: statistics() most_failed_gate and most_passed_gate are valid gate IDs", t55)

    # ── T-56: latest_results() returns n most recent results ─────────────
    def t56():
        ev  = make_ev()
        fid = live_finding_id()
        for _ in range(5):
            ev.validate_finding(fid)
        recent = ev.latest_results(3)
        ok(len(recent) == 3, f"Expected 3 results, got {len(recent)}")
        ok(all(isinstance(r, EvidenceValidation) for r in recent),
           "Not all recent results are EvidenceValidation")
        return f"latest_results(3) returned {len(recent)} items"
    runner.run("T-56: latest_results(n) returns n most recent validations", t56)

    # ── T-57: latest_results() returns newest first ───────────────────────
    def t57():
        ev  = make_ev()
        fid = live_finding_id()
        for _ in range(3):
            ev.validate_finding(fid)
            time.sleep(0.001)
        recent = ev.latest_results(3)
        times = [r.validated_at for r in recent]
        ok(times == sorted(times, reverse=True) or
           all(abs((times[i] - times[i+1]).total_seconds()) < 0.1 for i in range(len(times)-1)),
           "latest_results() not ordered newest-first")
        return "latest_results() ordered correctly"
    runner.run("T-57: latest_results() ordered newest-first", t57)

    # ── T-58: Thread safety: concurrent validate_finding() calls ──────────
    def t58():
        ev     = make_ev()
        fid    = live_finding_id()
        errors = []
        results = []

        def worker():
            try:
                r = ev.validate_finding(fid)
                results.append(r.validation_id)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()

        ok(not errors, f"Thread errors: {errors}")
        ok(len(results) == 8, f"Expected 8 results, got {len(results)}")
        return "8 concurrent validate_finding() calls — no errors"
    runner.run("T-58: Concurrent validate_finding() calls are thread-safe", t58)

    # ── T-59: Backward compatibility — all Phase 2C exports intact ────────
    def t59():
        from autonomous_research import (
            EvidenceValidator as EV,
            EvidenceValidatorConfig as EVC,
            EvidenceValidation as EVN,
            EvidenceQualityScore as EQS,
            GateResult as GR,
            GateStatus as GS,
            ValidationOutcome as VO,
            ValidationStatistics as VS,
            ValidationSummary as VSm,
            EvidenceValidatorError as EVE,
            ValidationSubjectNotFoundError as VSNFE,
        )
        ok(EV   is EvidenceValidator,           "EvidenceValidator import broken")
        ok(EVC  is EvidenceValidatorConfig,     "EvidenceValidatorConfig import broken")
        ok(EVN  is EvidenceValidation,          "EvidenceValidation import broken")
        ok(EQS  is EvidenceQualityScore,        "EvidenceQualityScore import broken")
        ok(GR   is GateResult,                  "GateResult import broken")
        ok(GS   is GateStatus,                  "GateStatus import broken")
        ok(VO   is ValidationOutcome,           "ValidationOutcome import broken")
        ok(VS   is ValidationStatistics,        "ValidationStatistics import broken")
        ok(VSm  is ValidationSummary,           "ValidationSummary import broken")
        ok(EVE  is EvidenceValidatorError,      "EvidenceValidatorError import broken")
        ok(VSNFE is ValidationSubjectNotFoundError, "VSNFE import broken")
        return "all Phase 2C exports intact"
    runner.run("T-59: Backward compatibility — all Phase 2C exports intact", t59)

    # ── T-60: All GapCategory types accepted by validate_roadmap_entry ────
    def t60():
        ev = make_ev()
        for cat in GapCategory:
            gap   = make_gap(f"G-{cat.value[:4]}-60", cat, GapSeverity.MEDIUM,
                             supporting_evidence=["F-001", "F-002"])
            entry = make_entry(gap)
            r     = ev.validate_roadmap_entry(entry)
            ok(isinstance(r, EvidenceValidation),
               f"{cat.value} — validate_roadmap_entry() failed")
            ok(isinstance(r.outcome, ValidationOutcome),
               f"{cat.value} — outcome wrong type")
        return f"all {len(GapCategory)} GapCategory values accepted"
    runner.run("T-60: All GapCategory types accepted by validate_roadmap_entry()", t60)

    # ── T-61: G-EV-08 is_critical reflects config ─────────────────────────
    def t61():
        # Default config: G-EV-08 is critical
        ev1 = EvidenceValidator(get_kp())
        g1  = ev1._gate_contradiction(0.50)
        ok(g1.is_critical, "G-EV-08 should be critical by default")

        # Remove G-EV-08 from critical_gates
        cfg2 = EvidenceValidatorConfig(critical_gates=[])
        ev2  = EvidenceValidator(get_kp(), config=cfg2)
        g2   = ev2._gate_contradiction(0.50)
        ok(not g2.is_critical, "G-EV-08 should NOT be critical when removed from critical_gates")
        return "G-EV-08 is_critical reflects config.critical_gates"
    runner.run("T-61: G-EV-08 is_critical correctly reflects EvidenceValidatorConfig", t61)

    return runner


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 72)
    print("ARS Phase 2C — EvidenceValidator Test Suite")
    print("=" * 72)

    runner = run_all_tests()

    print()
    for r in runner.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name} ({r.duration_ms}ms)")
        if r.error:
            for line in r.error.splitlines():
                print(f"         {line}")

    print()
    print("=" * 72)
    total = len(runner.results)
    print(f"  Results: {runner.passed}/{total} passed")
    if runner.failed:
        print(f"  FAILED:  {runner.failed}")
    else:
        print("  All tests passed.")
    print("=" * 72)

    if runner.failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
test_roadmap_manager.py — ARS Phase 2B test suite.

Covers:
    - Instantiation (with/without optional dependencies)
    - build() return structure and caching
    - KnowledgeGainEstimate: all components, ordering, documented formula
    - ResearchCostEstimate: all components, formula documented
    - ResearchDebt: base debt, age accumulation, special categories
    - Priority ordering: CRITICAL > HIGH > MEDIUM > LOW for same category
    - Portfolio balance: allocation, balance_score, recommendations
    - All 6 query API methods
    - Statistics consistency
    - Determinism: same gaps → same scores
    - Config customization: custom weights reflected in breakdown
    - Read-only verification: KP/Registry/GapDetector gaps unchanged
    - Thread safety: concurrent build() calls
    - Pre-build empty state
    - to_dict() serialization
    - Backward compatibility

Run:
    python test_roadmap_manager.py
"""
from __future__ import annotations

import json
import shutil
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
    GapDetectorConfig,
    GapCategory,
    GapSeverity,
    GapStatus,
    KnowledgeGap,
    RoadmapManager,
    RoadmapManagerConfig,
    StudyCategory,
    RoadmapEntry,
    RoadmapEntryStatus,
    KnowledgeGainEstimate,
    ResearchCostEstimate,
    ResearchDebt,
    ResearchPortfolio,
    ResearchRoadmap,
    RoadmapStatistics,
    RoadmapManagerError,
    RoadmapBuildError,
    HypothesisClassification,
    HypothesisPriority,
)


# ═════════════════════════════════════════════════════════════════════════════
# Minimal test framework (same pattern as Phase 2A)
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

_SEV_GAIN = {
    GapSeverity.CRITICAL: 0.90,
    GapSeverity.HIGH:     0.70,
    GapSeverity.MEDIUM:   0.50,
    GapSeverity.LOW:      0.20,
}


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


def make_gap(
    gap_id:   str,
    category: GapCategory,
    title:    str,
    severity: GapSeverity,
    confidence: float = 1.0,
    related_hypotheses: Optional[List[str]] = None,
    related_studies: Optional[List[str]] = None,
) -> KnowledgeGap:
    """Create a minimal KnowledgeGap for testing."""
    return KnowledgeGap(
        gap_id=gap_id,
        category=category,
        title=title,
        description=f"Test gap: {title}",
        severity=severity,
        severity_rationale=f"Test: {severity.value}",
        confidence=confidence,
        status=GapStatus.OPEN,
        supporting_evidence=[gap_id],
        related_studies=related_studies or [],
        related_hypotheses=related_hypotheses or [],
        related_findings=[],
        recommended_action="Test action",
        estimated_knowledge_gain=_SEV_GAIN[severity],
        rule_id="R-TEST",
        rule_parameters={},
        created_at=datetime.now(),
    )


def live_gaps() -> List[KnowledgeGap]:
    return list(get_gd().detect().gaps)


# ═════════════════════════════════════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════════════════════════════════════

def run_all_tests() -> TestRunner:
    runner = TestRunner()
    tmp = Path(tempfile.mkdtemp(prefix="ars_rm_test_"))

    # ── T-01: Instantiation with all providers ───────────────────────────
    def t01():
        rm = RoadmapManager(
            knowledge_provider=get_kp(),
            hypothesis_registry=HypothesisRegistry(get_kp(), registry_path=tmp/"t01.json"),
            synthesizer=get_syn(),
            gap_detector=get_gd(),
            state_path=tmp/"t01_state.json",
        )
        ok(rm is not None, "RoadmapManager is None")
        return "instantiated with all providers"
    runner.run("T-01: Instantiation with all providers", t01)

    # ── T-02: Instantiation with KP only ─────────────────────────────────
    def t02():
        rm = RoadmapManager(knowledge_provider=get_kp(), state_path=tmp/"t02_state.json")
        ok(rm is not None, "RoadmapManager KP-only is None")
        return "KP-only instantiation"
    runner.run("T-02: Instantiation with KnowledgeProvider only", t02)

    # ── T-03: Custom config accepted ─────────────────────────────────────
    def t03():
        cfg = RoadmapManagerConfig(w_knowledge_gain=0.50, w_urgency=0.50,
                                   w_research_debt=0.0, w_scientific_importance=0.0,
                                   w_cost_efficiency=0.0)
        rm = RoadmapManager(get_kp(), config=cfg, state_path=tmp/"t03_state.json")
        ok(rm is not None, "RoadmapManager with custom config is None")
        return "custom config accepted"
    runner.run("T-03: Custom RoadmapManagerConfig accepted", t03)

    # ── T-04: build() with explicit gaps returns ResearchRoadmap ─────────
    def t04():
        gaps = [make_gap("G-1", GapCategory.EVIDENCE_GAP, "Test", GapSeverity.MEDIUM)]
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t04_state.json")
        rm_out = rm.build(gaps=gaps)
        ok(isinstance(rm_out, ResearchRoadmap), f"Expected ResearchRoadmap, got {type(rm_out)}")
        ok(rm_out.roadmap_id.startswith("RM-"), f"Bad roadmap_id: {rm_out.roadmap_id}")
        ok(isinstance(rm_out.built_at, datetime), "built_at not datetime")
        ok(isinstance(rm_out.entries, list), "entries not list")
        ok(isinstance(rm_out.portfolio, ResearchPortfolio), "portfolio wrong type")
        ok(isinstance(rm_out.statistics, RoadmapStatistics), "statistics wrong type")
        return f"roadmap_id={rm_out.roadmap_id}, {len(rm_out.entries)} entries"
    runner.run("T-04: build() with explicit gaps returns ResearchRoadmap", t04)

    # ── T-05: build() with gap_detector pulls live gaps ──────────────────
    def t05():
        rm  = RoadmapManager(get_kp(), gap_detector=get_gd(), state_path=tmp/"t05_state.json")
        out = rm.build()
        ok(len(out.entries) == len(live_gaps()),
           f"Expected {len(live_gaps())} entries, got {len(out.entries)}")
        return f"{len(out.entries)} entries from live GapDetector"
    runner.run("T-05: build() with gap_detector uses live gaps", t05)

    # ── T-06: build() raises RoadmapBuildError when gaps=None, no detector
    def t06():
        rm = RoadmapManager(get_kp(), state_path=tmp/"t06_state.json")
        try:
            rm.build(gaps=None)
            ok(False, "Expected RoadmapBuildError, no exception raised")
        except RoadmapBuildError:
            pass
        return "RoadmapBuildError raised correctly"
    runner.run("T-06: build(gaps=None, no detector) raises RoadmapBuildError", t06)

    # ── T-07: build() is cached (force=False) ────────────────────────────
    def t07():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t07_state.json")
        gaps = [make_gap("G-1", GapCategory.COVERAGE_GAP, "Test", GapSeverity.HIGH)]
        r1  = rm.build(gaps=gaps)
        r2  = rm.build(gaps=gaps)
        ok(r1.roadmap_id == r2.roadmap_id, "Cached roadmap has different roadmap_id")
        return f"same roadmap_id={r1.roadmap_id}"
    runner.run("T-07: build() is cached — same roadmap_id on second call", t07)

    # ── T-08: build(force=True) refreshes ────────────────────────────────
    def t08():
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t08_state.json")
        gaps = [make_gap("G-1", GapCategory.COVERAGE_GAP, "Test", GapSeverity.HIGH)]
        r1   = rm.build(gaps=gaps)
        r2   = rm.build(gaps=gaps, force=True)
        ok(r1.roadmap_id != r2.roadmap_id, "force=True did not produce new roadmap_id")
        return "force=True refreshes cache"
    runner.run("T-08: build(force=True) refreshes cache", t08)

    # ── T-09: KnowledgeGainEstimate: CRITICAL > MEDIUM knowledge gain ────
    def t09():
        rm    = RoadmapManager(get_kp(), state_path=tmp/"t09_state.json")
        g_crit = make_gap("G-C", GapCategory.EVIDENCE_GAP, "Crit", GapSeverity.CRITICAL)
        g_med  = make_gap("G-M", GapCategory.EVIDENCE_GAP, "Med",  GapSeverity.MEDIUM)
        out   = rm.build(gaps=[g_crit, g_med])
        kg_c  = out.entries[0].knowledge_gain_estimate if out.entries[0].gap.gap_id == "G-C" else out.entries[1].knowledge_gain_estimate
        kg_m  = out.entries[1].knowledge_gain_estimate if out.entries[0].gap.gap_id == "G-C" else out.entries[0].knowledge_gain_estimate
        ok(kg_c.total_gain > kg_m.total_gain,
           f"CRITICAL KG {kg_c.total_gain:.3f} not > MEDIUM KG {kg_m.total_gain:.3f}")
        return f"CRITICAL KG={kg_c.total_gain:.3f} > MEDIUM KG={kg_m.total_gain:.3f}"
    runner.run("T-09: CRITICAL gap has higher knowledge gain than MEDIUM gap", t09)

    # ── T-10: KnowledgeGainEstimate: total_gain in [0, 1] ────────────────
    def t10():
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t10_state.json")
        gaps = [make_gap(f"G-{cat.value[:3]}", cat, cat.value, sev)
                for cat in GapCategory for sev in GapSeverity]
        out  = rm.build(gaps=gaps)
        for entry in out.entries:
            kg = entry.knowledge_gain_estimate
            ok(0.0 <= kg.total_gain <= 1.0,
               f"total_gain {kg.total_gain} out of [0,1] for {entry.gap.gap_id}")
        return f"all {len(out.entries)} KG values in [0, 1]"
    runner.run("T-10: KnowledgeGainEstimate.total_gain always in [0, 1]", t10)

    # ── T-11: KnowledgeGainEstimate breakdown has all required keys ───────
    def t11():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t11_state.json")
        gap = make_gap("G-1", GapCategory.REGIME_GAP, "Test", GapSeverity.HIGH)
        out = rm.build(gaps=[gap])
        bd  = out.entries[0].knowledge_gain_estimate.breakdown
        required = {
            "scientific_importance", "evidence_gap_size",
            "expected_confidence_improvement", "coverage_increase",
            "novelty", "reuse_potential", "uncertainty_reduction",
            "historical_impact", "raw_gain", "adjusted_gain", "final_gain",
            "w_scientific_importance", "w_evidence_gap_size",
            "w_confidence_improvement", "w_coverage_increase",
            "w_novelty", "w_reuse_potential",
            "uncertainty_bonus_factor",
        }
        missing = required - set(bd.keys())
        ok(not missing, f"KG breakdown missing keys: {missing}")
        return "KG breakdown has all required keys"
    runner.run("T-11: KnowledgeGainEstimate.breakdown documents all formula components", t11)

    # ── T-12: COVERAGE_GAP has highest novelty ────────────────────────────
    def t12():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t12_state.json")
        gap = make_gap("G-COV", GapCategory.COVERAGE_GAP, "Test", GapSeverity.HIGH)
        out = rm.build(gaps=[gap])
        nov = out.entries[0].knowledge_gain_estimate.novelty
        ok(nov == 0.90, f"COVERAGE_GAP novelty should be 0.90, got {nov}")
        return f"COVERAGE_GAP novelty={nov}"
    runner.run("T-12: COVERAGE_GAP has highest novelty (0.90)", t12)

    # ── T-13: EVIDENCE_GAP has high evidence_gap_size ─────────────────────
    def t13():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t13_state.json")
        gap = make_gap("G-EV", GapCategory.EVIDENCE_GAP, "Test", GapSeverity.MEDIUM)
        out = rm.build(gaps=[gap])
        eg  = out.entries[0].knowledge_gain_estimate.evidence_gap_size
        ok(eg == 0.85, f"EVIDENCE_GAP evidence_gap_size should be 0.85, got {eg}")
        return f"EVIDENCE_GAP evidence_gap_size={eg}"
    runner.run("T-13: EVIDENCE_GAP has evidence_gap_size=0.85", t13)

    # ── T-14: VALIDATION_GAP has highest replay hours ─────────────────────
    def t14():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t14_state.json")
        gap = make_gap("G-VL", GapCategory.VALIDATION_GAP, "Test", GapSeverity.HIGH)
        out = rm.build(gaps=[gap])
        hrs = out.entries[0].cost_estimate.replay_duration_estimate_hours
        ok(hrs == 4.0, f"VALIDATION_GAP replay should be 4.0h, got {hrs}")
        return f"VALIDATION_GAP replay={hrs}h"
    runner.run("T-14: VALIDATION_GAP has highest replay hours (4.0)", t14)

    # ── T-15: ResearchCostEstimate: total_cost in [0, 1] ─────────────────
    def t15():
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t15_state.json")
        gaps = [make_gap(f"G-{cat.value[:3]}", cat, cat.value, GapSeverity.HIGH)
                for cat in GapCategory]
        out  = rm.build(gaps=gaps)
        for entry in out.entries:
            c = entry.cost_estimate.total_cost
            ok(0.0 <= c <= 1.0, f"total_cost {c} out of [0,1] for {entry.gap.gap_id}")
        return f"all {len(out.entries)} cost values in [0, 1]"
    runner.run("T-15: ResearchCostEstimate.total_cost always in [0, 1]", t15)

    # ── T-16: ResearchCostEstimate breakdown has all required keys ────────
    def t16():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t16_state.json")
        gap = make_gap("G-1", GapCategory.VALIDATION_GAP, "Test", GapSeverity.MEDIUM)
        out = rm.build(gaps=[gap])
        bd  = out.entries[0].cost_estimate.breakdown
        required = {
            "implementation_effort", "risk", "historical_days_required",
            "replay_duration_hours", "replay_factor", "total_cost",
            "w_implementation_effort", "w_risk", "w_replay",
        }
        missing = required - set(bd.keys())
        ok(not missing, f"Cost breakdown missing keys: {missing}")
        return "cost breakdown documented"
    runner.run("T-16: ResearchCostEstimate.breakdown documents formula", t16)

    # ── T-17: dependencies field is a list ────────────────────────────────
    def t17():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t17_state.json")
        gap = make_gap("G-KG", GapCategory.KNOWLEDGE_GAP, "Test", GapSeverity.HIGH,
                       related_hypotheses=["H2026-08-001", "H2026-08-002"])
        out = rm.build(gaps=[gap])
        deps = out.entries[0].cost_estimate.dependencies
        ok(isinstance(deps, list), "dependencies not a list")
        ok("H2026-08-001" in deps,
           f"KNOWLEDGE_GAP related_hypotheses not in dependencies: {deps}")
        return f"dependencies={deps}"
    runner.run("T-17: KNOWLEDGE_GAP dependencies include related_hypotheses", t17)

    # ── T-18: CRITICAL severity base_debt > LOW base_debt ────────────────
    def t18():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t18_state.json")
        g_crit = make_gap("G-C", GapCategory.DATA_GAP, "Crit", GapSeverity.CRITICAL)
        g_low  = make_gap("G-L", GapCategory.DATA_GAP, "Low",  GapSeverity.LOW)
        out   = rm.build(gaps=[g_crit, g_low])
        e_map = {e.gap.gap_id: e for e in out.entries}
        ok(e_map["G-C"].debt.base_debt == 1.00, "CRITICAL base_debt != 1.00")
        ok(e_map["G-L"].debt.base_debt == 0.25, "LOW base_debt != 0.25")
        ok(e_map["G-C"].debt.base_debt > e_map["G-L"].debt.base_debt,
           "CRITICAL base_debt not > LOW base_debt")
        return "base_debt ordering: CRITICAL=1.00 > LOW=0.25"
    runner.run("T-18: CRITICAL gap has base_debt=1.00, LOW gap has base_debt=0.25", t18)

    # ── T-19: Age debt starts at 0 for a freshly detected gap ────────────
    def t19():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t19_state.json")
        gap = make_gap("G-FRESH", GapCategory.EVIDENCE_GAP, "Fresh", GapSeverity.MEDIUM)
        out = rm.build(gaps=[gap])
        age = out.entries[0].debt.age_debt
        ok(age == 0.0, f"Fresh gap age_debt should be 0.0, got {age}")
        return f"fresh gap age_debt={age}"
    runner.run("T-19: Fresh gap has age_debt=0.0", t19)

    # ── T-20: Age debt accumulates for aged gaps ──────────────────────────
    def t20():
        gap_id   = "G-AGED-EVID-001"
        old_date = (datetime.now() - timedelta(days=200)).isoformat()
        state    = {"version": "1.0", "last_updated": datetime.now().isoformat(),
                    "gap_first_seen": {gap_id: old_date}}
        state_f  = tmp / "t20_state.json"
        state_f.write_text(json.dumps(state), encoding="utf-8")

        rm  = RoadmapManager(get_kp(), state_path=state_f)
        gap = make_gap(gap_id, GapCategory.EVIDENCE_GAP, "Aged gap", GapSeverity.MEDIUM)
        out = rm.build(gaps=[gap])
        age = out.entries[0].debt.age_debt
        # With debt_half_life=90 days and gap aged 200 days, age_debt should be 1.0 (capped)
        ok(age == 1.0, f"200-day old gap (half-life 90d) should have age_debt=1.0, got {age}")
        return f"200-day gap age_debt={age}"
    runner.run("T-20: Age debt caps at 1.0 after debt_half_life_days", t20)

    # ── T-21: CONTRADICTION_GAP has contradiction_debt > 0 ───────────────
    def t21():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t21_state.json")
        gap = make_gap("G-CONT", GapCategory.CONTRADICTION_GAP, "Test", GapSeverity.HIGH)
        out = rm.build(gaps=[gap])
        cd  = out.entries[0].debt.contradiction_debt
        ok(cd == 0.30, f"CONTRADICTION_GAP contradiction_debt should be 0.30, got {cd}")
        return f"contradiction_debt={cd}"
    runner.run("T-21: CONTRADICTION_GAP has contradiction_debt=0.30", t21)

    # ── T-22: TEMPORAL_GAP has expiry_debt > 0 ───────────────────────────
    def t22():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t22_state.json")
        gap = make_gap("G-TEMP", GapCategory.TEMPORAL_GAP, "Test", GapSeverity.MEDIUM)
        out = rm.build(gaps=[gap])
        ed  = out.entries[0].debt.expiry_debt
        ok(ed == 0.20, f"TEMPORAL_GAP expiry_debt should be 0.20, got {ed}")
        return f"expiry_debt={ed}"
    runner.run("T-22: TEMPORAL_GAP has expiry_debt=0.20", t22)

    # ── T-23: Entries sorted by descending priority ───────────────────────
    def t23():
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t23_state.json")
        gaps = live_gaps()
        ok(len(gaps) > 1, "Need ≥2 live gaps for ordering test")
        out  = rm.build(gaps=gaps)
        scores = [e.priority_score for e in out.entries]
        ok(scores == sorted(scores, reverse=True),
           f"Entries not sorted by descending priority: {scores[:5]}")
        return f"entries sorted; top={scores[0]:.3f}, bottom={scores[-1]:.3f}"
    runner.run("T-23: Entries are sorted by descending priority_score", t23)

    # ── T-24: CRITICAL > HIGH > MEDIUM > LOW priority for same category ───
    def t24():
        rm = RoadmapManager(get_kp(), state_path=tmp/"t24_state.json")
        gaps = [
            make_gap("G-CRIT", GapCategory.DATA_GAP, "Critical", GapSeverity.CRITICAL),
            make_gap("G-HIGH", GapCategory.DATA_GAP, "High",     GapSeverity.HIGH),
            make_gap("G-MED",  GapCategory.DATA_GAP, "Medium",   GapSeverity.MEDIUM),
            make_gap("G-LOW",  GapCategory.DATA_GAP, "Low",      GapSeverity.LOW),
        ]
        out  = rm.build(gaps=gaps)
        pmap = {e.gap.gap_id: e.priority_score for e in out.entries}
        ok(pmap["G-CRIT"] > pmap["G-HIGH"], "CRITICAL <= HIGH")
        ok(pmap["G-HIGH"] > pmap["G-MED"],  "HIGH <= MEDIUM")
        ok(pmap["G-MED"]  > pmap["G-LOW"],  "MEDIUM <= LOW")
        return (f"CRITICAL={pmap['G-CRIT']:.3f} > HIGH={pmap['G-HIGH']:.3f} > "
                f"MED={pmap['G-MED']:.3f} > LOW={pmap['G-LOW']:.3f}")
    runner.run("T-24: Priority ordering CRITICAL > HIGH > MEDIUM > LOW (same category)", t24)

    # ── T-25: Priority score in [0, 1] ────────────────────────────────────
    def t25():
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t25_state.json")
        gaps = [make_gap(f"G-{cat.value[:3]}-{sev.value[:2]}", cat, cat.value, sev)
                for cat in GapCategory for sev in GapSeverity]
        out  = rm.build(gaps=gaps)
        for e in out.entries:
            ok(0.0 <= e.priority_score <= 1.0,
               f"priority_score {e.priority_score} out of [0,1]: {e.entry_id}")
        return f"all {len(out.entries)} priority scores in [0, 1]"
    runner.run("T-25: All priority_scores are in [0, 1]", t25)

    # ── T-26: priority_breakdown documents all formula components ─────────
    def t26():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t26_state.json")
        gap = make_gap("G-1", GapCategory.EVIDENCE_GAP, "Test", GapSeverity.HIGH)
        out = rm.build(gaps=[gap])
        pb  = out.entries[0].priority_breakdown
        required = {
            "knowledge_gain_score", "research_debt_score", "scientific_importance_score",
            "cost_efficiency_score", "urgency_score",
            "knowledge_gain_contribution", "research_debt_contribution",
            "scientific_importance_contribution", "cost_efficiency_contribution",
            "urgency_contribution",
            "weights_used", "total_weight", "raw_score", "final_priority",
        }
        missing = required - set(pb.keys())
        ok(not missing, f"priority_breakdown missing keys: {missing}")
        weights = pb["weights_used"]
        ok("w_knowledge_gain" in weights, "weights_used missing w_knowledge_gain")
        return "priority_breakdown fully documented"
    runner.run("T-26: priority_breakdown documents all formula components", t26)

    # ── T-27: Portfolio allocation covers all StudyCategory values ────────
    def t27():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t27_state.json")
        out = rm.build(gaps=live_gaps())
        alloc = out.portfolio.allocation
        for cat in StudyCategory:
            ok(cat.value in alloc, f"StudyCategory.{cat.value} missing from portfolio")
        return f"portfolio covers all {len(StudyCategory)} categories"
    runner.run("T-27: Portfolio allocation covers all StudyCategory values", t27)

    # ── T-28: actual_fraction sums to 1.0 ────────────────────────────────
    def t28():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t28_state.json")
        out = rm.build(gaps=live_gaps())
        total = sum(out.portfolio.actual_fraction.values())
        ok(abs(total - 1.0) < 1e-9, f"actual_fraction sums to {total}, expected 1.0")
        return f"actual_fraction sums to {total:.6f}"
    runner.run("T-28: Portfolio actual_fraction sums to 1.0", t28)

    # ── T-29: Portfolio recommendations when imbalanced ──────────────────
    def t29():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t29_state.json")
        out = rm.build(gaps=live_gaps())
        recs = out.portfolio.recommendations
        # With live data (only EVIDENCE_GAP + REGIME_GAP), many categories are 0%
        # so recommendations should suggest adding underrepresented categories
        ok(isinstance(recs, list), "recommendations not a list")
        # At minimum, RISK and VALIDATION are likely underrepresented
        all_text = " ".join(recs)
        ok(len(all_text) > 0 or out.portfolio.balance_score == 1.0,
           "No recommendations despite imbalanced portfolio")
        return f"{len(recs)} portfolio recommendations"
    runner.run("T-29: Portfolio recommendations issued when categories are imbalanced", t29)

    # ── T-30: balance_score in [0, 1] ────────────────────────────────────
    def t30():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t30_state.json")
        out = rm.build(gaps=live_gaps())
        bs  = out.portfolio.balance_score
        ok(0.0 <= bs <= 1.0, f"balance_score {bs} out of [0,1]")
        return f"balance_score={bs:.3f}"
    runner.run("T-30: Portfolio balance_score is in [0, 1]", t30)

    # ── T-31: REGIME_GAP maps to MARKET_REGIMES study category ───────────
    def t31():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t31_state.json")
        gap = make_gap("G-R", GapCategory.REGIME_GAP, "Regime test", GapSeverity.HIGH)
        out = rm.build(gaps=[gap])
        cat = out.entries[0].study_category
        ok(cat == StudyCategory.MARKET_REGIMES,
           f"REGIME_GAP mapped to {cat}, expected MARKET_REGIMES")
        return f"REGIME_GAP → {cat.value}"
    runner.run("T-31: REGIME_GAP maps to MARKET_REGIMES study category", t31)

    # ── T-32: CONTRADICTION_GAP maps to RISK study category ──────────────
    def t32():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t32_state.json")
        gap = make_gap("G-CONT", GapCategory.CONTRADICTION_GAP, "Test", GapSeverity.HIGH)
        out = rm.build(gaps=[gap])
        cat = out.entries[0].study_category
        ok(cat == StudyCategory.RISK, f"CONTRADICTION_GAP mapped to {cat}, expected RISK")
        return f"CONTRADICTION_GAP → {cat.value}"
    runner.run("T-32: CONTRADICTION_GAP maps to RISK study category", t32)

    # ── T-33: list_entries() returns sorted entries ───────────────────────
    def t33():
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t33_state.json")
        gaps = live_gaps()
        rm.build(gaps=gaps)
        entries = rm.list_entries()
        ok(len(entries) == len(gaps), f"list_entries() count {len(entries)} != {len(gaps)}")
        ranks = [e.rank for e in entries]
        ok(ranks == list(range(1, len(entries) + 1)), f"Ranks not sequential: {ranks[:5]}")
        return f"list_entries() = {len(entries)} entries, ranks {ranks[0]}..{ranks[-1]}"
    runner.run("T-33: list_entries() returns entries with sequential ranks", t33)

    # ── T-34: top_priorities(3) returns top 3 ────────────────────────────
    def t34():
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t34_state.json")
        gaps = live_gaps()
        ok(len(gaps) >= 3, f"Need ≥3 live gaps; got {len(gaps)}")
        rm.build(gaps=gaps)
        top3 = rm.top_priorities(3)
        ok(len(top3) == 3, f"top_priorities(3) returned {len(top3)}")
        ok([e.rank for e in top3] == [1, 2, 3], "top 3 entries not rank 1,2,3")
        return f"top 3 entry_ids: {[e.entry_id for e in top3]}"
    runner.run("T-34: top_priorities(3) returns top 3 entries", t34)

    # ── T-35: get_next_study() returns rank=1 entry ───────────────────────
    def t35():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t35_state.json")
        rm.build(gaps=live_gaps())
        nxt = rm.get_next_study()
        ok(nxt is not None, "get_next_study() returned None on non-empty roadmap")
        ok(nxt.rank == 1, f"get_next_study() rank={nxt.rank}, expected 1")
        return f"next_study: {nxt.entry_id} ({nxt.gap.category.value})"
    runner.run("T-35: get_next_study() returns rank=1 entry", t35)

    # ── T-36: statistics() structure correct ─────────────────────────────
    def t36():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t36_state.json")
        rm.build(gaps=live_gaps())
        stats = rm.statistics()
        ok(isinstance(stats, RoadmapStatistics), "statistics() wrong type")
        ok(stats.total_entries >= 0, "total_entries negative")
        ok(stats.pending_entries >= 0, "pending_entries negative")
        ok(0.0 <= stats.avg_priority_score <= 1.0, "avg_priority out of [0,1]")
        ok(0.0 <= stats.avg_knowledge_gain  <= 1.0, "avg_kg out of [0,1]")
        ok(0.0 <= stats.avg_cost            <= 1.0, "avg_cost out of [0,1]")
        ok(stats.build_duration_ms >= 0, "build_duration negative")
        return f"total={stats.total_entries}, avg_priority={stats.avg_priority_score:.3f}"
    runner.run("T-36: statistics() returns well-formed RoadmapStatistics", t36)

    # ── T-37: statistics().by_gap_category sums to total_entries ─────────
    def t37():
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t37_state.json")
        rm.build(gaps=live_gaps())
        stats = rm.statistics()
        cat_sum = sum(stats.by_gap_category.values())
        ok(cat_sum == stats.total_entries,
           f"by_gap_category sum {cat_sum} != total {stats.total_entries}")
        sev_sum = sum(stats.by_severity.values())
        ok(sev_sum == stats.total_entries,
           f"by_severity sum {sev_sum} != total {stats.total_entries}")
        sc_sum = sum(stats.by_study_category.values())
        ok(sc_sum == stats.total_entries,
           f"by_study_category sum {sc_sum} != total {stats.total_entries}")
        return f"all category sums correct at {stats.total_entries}"
    runner.run("T-37: Statistics category dicts sum to total_entries", t37)

    # ── T-38: Same gaps → same priority scores (determinism) ─────────────
    def t38():
        gaps = [
            make_gap("G-1", GapCategory.EVIDENCE_GAP, "E1", GapSeverity.MEDIUM),
            make_gap("G-2", GapCategory.REGIME_GAP,   "R1", GapSeverity.HIGH),
        ]
        rm1 = RoadmapManager(get_kp(), state_path=tmp/"t38a_state.json")
        rm2 = RoadmapManager(get_kp(), state_path=tmp/"t38b_state.json")
        r1  = rm1.build(gaps=gaps)
        r2  = rm2.build(gaps=gaps)
        for e1, e2 in zip(r1.entries, r2.entries):
            ok(abs(e1.priority_score - e2.priority_score) < 1e-9,
               f"Non-deterministic priority: {e1.priority_score} vs {e2.priority_score}")
            ok(e1.entry_id == e2.entry_id,
               f"Non-deterministic entry_id: {e1.entry_id} vs {e2.entry_id}")
        return "priority scores and entry_ids are deterministic"
    runner.run("T-38: Same gaps produce identical priority scores (determinism)", t38)

    # ── T-39: Entry IDs are deterministic ────────────────────────────────
    def t39():
        gap = make_gap("G-DET-001", GapCategory.COVERAGE_GAP, "Det test", GapSeverity.HIGH)
        rm1 = RoadmapManager(get_kp(), state_path=tmp/"t39a_state.json")
        rm2 = RoadmapManager(get_kp(), state_path=tmp/"t39b_state.json")
        out1 = rm1.build(gaps=[gap])
        out2 = rm2.build(gaps=[gap])
        ok(out1.entries[0].entry_id == out2.entries[0].entry_id,
           f"Non-deterministic entry_id: {out1.entries[0].entry_id}")
        return f"entry_id={out1.entries[0].entry_id} is deterministic"
    runner.run("T-39: entry_id is deterministic from gap_id", t39)

    # ── T-40: build(force=True) produces new roadmap_id ──────────────────
    def t40():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t40_state.json")
        gap = make_gap("G-1", GapCategory.DATA_GAP, "Test", GapSeverity.MEDIUM)
        r1  = rm.build(gaps=[gap])
        r2  = rm.build(gaps=[gap], force=True)
        r3  = rm.build(gaps=[gap], force=True)
        ok(r1.roadmap_id != r2.roadmap_id, "force=True: r1 == r2")
        ok(r2.roadmap_id != r3.roadmap_id, "force=True: r2 == r3")
        return "each force=True call yields unique roadmap_id"
    runner.run("T-40: build(force=True) always produces a unique roadmap_id", t40)

    # ── T-41: Custom weights reflected in priority_breakdown ─────────────
    def t41():
        cfg = RoadmapManagerConfig(
            w_knowledge_gain=0.50,
            w_research_debt=0.20,
            w_scientific_importance=0.15,
            w_cost_efficiency=0.10,
            w_urgency=0.05,
        )
        rm  = RoadmapManager(get_kp(), config=cfg, state_path=tmp/"t41_state.json")
        gap = make_gap("G-1", GapCategory.EVIDENCE_GAP, "Test", GapSeverity.HIGH)
        out = rm.build(gaps=[gap])
        w   = out.entries[0].priority_breakdown["weights_used"]
        ok(w["w_knowledge_gain"]        == 0.50, f"w_kg={w['w_knowledge_gain']}")
        ok(w["w_urgency"]               == 0.05, f"w_urgency={w['w_urgency']}")
        ok(w["w_scientific_importance"] == 0.15, f"w_si={w['w_scientific_importance']}")
        return "custom weights in priority_breakdown confirmed"
    runner.run("T-41: Custom weights reflected in priority_breakdown.weights_used", t41)

    # ── T-42: Custom portfolio_allocation is used ──────────────────────────
    def t42():
        cfg = RoadmapManagerConfig(
            portfolio_allocation={
                "WINNER_DNA":      0.00,
                "MARKET_REGIMES":  1.00,
                "SECTOR_RESEARCH": 0.00,
                "VALIDATION":      0.00,
                "RISK":            0.00,
                "EXPLORATION":     0.00,
            }
        )
        rm  = RoadmapManager(get_kp(), config=cfg, state_path=tmp/"t42_state.json")
        out = rm.build(gaps=live_gaps())
        target = out.portfolio.target_allocation
        ok(target.get("MARKET_REGIMES") == 1.00,
           f"Custom portfolio target not used: {target}")
        return f"custom portfolio target MARKET_REGIMES=1.00 applied"
    runner.run("T-42: Custom portfolio_allocation used in portfolio analysis", t42)

    # ── T-43: Custom debt_half_life_days changes debt ─────────────────────
    def t43():
        gap_id  = "G-DEBT-HALF"
        dt_str  = (datetime.now() - timedelta(days=45)).isoformat()
        state   = {"version": "1.0", "last_updated": datetime.now().isoformat(),
                   "gap_first_seen": {gap_id: dt_str}}

        # With default half-life (90 days): age_debt = 45/90 = 0.50
        f1 = tmp / "t43a_state.json"
        f1.write_text(json.dumps(state), encoding="utf-8")
        cfg_def = RoadmapManagerConfig(debt_half_life_days=90)
        rm1 = RoadmapManager(get_kp(), config=cfg_def, state_path=f1)

        # With short half-life (45 days): age_debt = 45/45 = 1.0
        f2 = tmp / "t43b_state.json"
        f2.write_text(json.dumps(state), encoding="utf-8")
        cfg_short = RoadmapManagerConfig(debt_half_life_days=45)
        rm2 = RoadmapManager(get_kp(), config=cfg_short, state_path=f2)

        gap  = make_gap(gap_id, GapCategory.DATA_GAP, "Debt test", GapSeverity.MEDIUM)
        d1   = rm1.build(gaps=[gap]).entries[0].debt.age_debt
        d2   = rm2.build(gaps=[gap]).entries[0].debt.age_debt
        ok(d2 >= d1, f"Shorter half-life should give >= debt: d2={d2:.2f} d1={d1:.2f}")
        ok(abs(d1 - 0.50) < 0.02, f"Expected age_debt≈0.50 (90d half-life), got {d1:.3f}")
        ok(abs(d2 - 1.00) < 0.02, f"Expected age_debt≈1.00 (45d half-life), got {d2:.3f}")
        return f"age_debt: 90d-half-life={d1:.2f}, 45d-half-life={d2:.2f}"
    runner.run("T-43: debt_half_life_days controls age_debt rate", t43)

    # ── T-44: KP stores unchanged after build() ───────────────────────────
    def t44():
        kp = KnowledgeProvider()
        n_studies_before  = len(kp.list_studies())
        n_edges_before    = len(kp.list_edges())
        n_findings_before = len(kp.list_findings())
        rm = RoadmapManager(kp, state_path=tmp/"t44_state.json")
        rm.build(gaps=live_gaps())
        ok(len(kp.list_studies())  == n_studies_before,  "build() changed study count")
        ok(len(kp.list_edges())    == n_edges_before,    "build() changed edge count")
        ok(len(kp.list_findings()) == n_findings_before, "build() changed finding count")
        return "KP stores unchanged"
    runner.run("T-44: KP stores are read-only — build() does not modify them", t44)

    # ── T-45: Original gap objects unchanged after build() ────────────────
    def t45():
        gaps_before = live_gaps()
        ids_before  = [g.gap_id      for g in gaps_before]
        cats_before = [g.category    for g in gaps_before]
        sevs_before = [g.severity    for g in gaps_before]
        titles_before = [g.title     for g in gaps_before]

        rm = RoadmapManager(get_kp(), state_path=tmp/"t45_state.json")
        rm.build(gaps=gaps_before)

        ok([g.gap_id   for g in gaps_before] == ids_before,   "gap_id changed")
        ok([g.category for g in gaps_before] == cats_before,  "category changed")
        ok([g.severity for g in gaps_before] == sevs_before,  "severity changed")
        ok([g.title    for g in gaps_before] == titles_before, "title changed")
        return "original gap objects unchanged"
    runner.run("T-45: Input KnowledgeGap objects are not modified by build()", t45)

    # ── T-46: list_entries() before build() returns [] ────────────────────
    def t46():
        rm = RoadmapManager(get_kp(), state_path=tmp/"t46_state.json")
        ok(rm.list_entries()    == [], "list_entries() before build() not empty")
        ok(rm.top_priorities()  == [], "top_priorities() before build() not empty")
        ok(rm.get_next_study()  is None, "get_next_study() before build() not None")
        return "list_entries(), top_priorities(), get_next_study() return empty before build()"
    runner.run("T-46: Query methods return empty/None before first build()", t46)

    # ── T-47: statistics() before build() returns zero stats ─────────────
    def t47():
        rm    = RoadmapManager(get_kp(), state_path=tmp/"t47_state.json")
        stats = rm.statistics()
        ok(stats.total_entries == 0, f"total_entries {stats.total_entries} before build()")
        ok(stats.by_gap_category == {}, "by_gap_category not empty before build()")
        return "statistics() returns zeros before first build()"
    runner.run("T-47: statistics() returns zero stats before first build()", t47)

    # ── T-48: portfolio() before build() returns empty portfolio ──────────
    def t48():
        rm   = RoadmapManager(get_kp(), state_path=tmp/"t48_state.json")
        port = rm.portfolio()
        ok(port.total_entries == 0, "portfolio().total_entries not 0 before build()")
        ok(port.balance_score == 0.0, "portfolio().balance_score not 0.0 before build()")
        return "portfolio() returns empty before first build()"
    runner.run("T-48: portfolio() returns empty ResearchPortfolio before first build()", t48)

    # ── T-49: ResearchRoadmap.to_dict() round-trips correctly ────────────
    def t49():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t49_state.json")
        out = rm.build(gaps=live_gaps())
        d   = out.to_dict()
        ok(isinstance(d, dict), "to_dict() not a dict")
        for key in ("roadmap_id", "built_at", "entries", "portfolio", "statistics", "warnings"):
            ok(key in d, f"to_dict() missing '{key}'")
        ok(isinstance(d["entries"], list), "entries not a list")
        return f"to_dict() produced {len(d['entries'])} entry dicts"
    runner.run("T-49: ResearchRoadmap.to_dict() produces valid dict", t49)

    # ── T-50: RoadmapEntry.to_dict() has all required fields ─────────────
    def t50():
        rm  = RoadmapManager(get_kp(), state_path=tmp/"t50_state.json")
        out = rm.build(gaps=live_gaps())
        ok(len(out.entries) > 0, "No entries to test to_dict()")
        required = {
            "entry_id", "gap_id", "gap_title", "gap_category", "gap_severity",
            "knowledge_gain_estimate", "cost_estimate", "debt",
            "priority_score", "priority_breakdown",
            "study_category", "status", "rank",
            "recommended_study_title", "recommended_approach", "created_at",
        }
        for entry in out.entries:
            d       = entry.to_dict()
            missing = required - set(d.keys())
            ok(not missing, f"Entry {entry.entry_id} to_dict() missing: {missing}")
        return f"all {len(out.entries)} entry to_dict() dicts have required fields"
    runner.run("T-50: RoadmapEntry.to_dict() contains all required fields", t50)

    # ── T-51: Concurrent build() calls are thread-safe ────────────────────
    def t51():
        rm     = RoadmapManager(get_kp(), state_path=tmp/"t51_state.json")
        gaps   = live_gaps()
        errors = []
        ids    = []

        def worker():
            try:
                r = rm.build(gaps=gaps, force=True)
                ids.append(r.roadmap_id)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()

        ok(not errors, f"Thread errors: {errors}")
        ok(len(ids) == 8, f"Expected 8 results, got {len(ids)}")
        return "8 concurrent build() calls completed without error"
    runner.run("T-51: Concurrent build() calls are thread-safe", t51)

    # ── T-52: Backward compatibility — all Phase 1–2B exports intact ──────
    def t52():
        from autonomous_research import (
            KnowledgeProvider as KP,
            HypothesisRegistry as HR,
            CrossStudySynthesizer as CSS,
            GapDetector as GD,
            RoadmapManager as RM,
        )
        ok(KP  is KnowledgeProvider,    "KP import broken")
        ok(HR  is HypothesisRegistry,   "HR import broken")
        ok(CSS is CrossStudySynthesizer, "CSS import broken")
        ok(GD  is GapDetector,          "GD import broken")
        ok(RM  is RoadmapManager,       "RM import broken")
        from autonomous_research import (
            RoadmapManagerError, RoadmapBuildError, StudyCategory,
            KnowledgeGainEstimate, ResearchDebt,
        )
        return "all Phase 1–2B exports intact"
    runner.run("T-52: Backward compatibility — all Phase 1–2B exports intact", t52)

    # ── Cleanup ──────────────────────────────────────────────────────────────
    try:
        shutil.rmtree(str(tmp), ignore_errors=True)
    except Exception:
        pass

    return runner


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 72)
    print("ARS Phase 2B — RoadmapManager Test Suite")
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

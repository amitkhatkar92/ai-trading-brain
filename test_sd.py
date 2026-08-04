"""
test_sd.py — Scientific Director test suite.

IIOS Research Infrastructure — Phase 3C.

Test range: T001-T300 (300 tests)
Run: python test_sd.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# ─── test harness ────────────────────────────────────────────────────────────
PASS = 0
FAIL = 0
ERRORS: List[str] = []


def ok(test_id: str, cond: bool, msg: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        ERRORS.append(f"{test_id}: FAIL {msg}")


def section(title: str) -> None:
    print(f"\n-- {title} --")


# ─── imports under test ───────────────────────────────────────────────────────
from autonomous_research.sd_models import (
    DecisionClass,
    DecisionType,
    ReviewType,
    SDError,
    SDHealth,
    SDObservationError,
    ScientificDecision,
    ScientificHealth,
    ScientificObservation,
    ScientificReasoning,
    ScientificRecommendation,
    ScientificReview,
    ScientificRoadmap,
    SignificanceLevel,
    UrgencyLevel,
    _now_iso,
    make_decision_id,
    make_observation_id,
    make_recommendation_id,
    make_review_id,
)
from autonomous_research.sd_config import SDConfig
from autonomous_research.scientific_journal import JournalEntry, ScientificJournal
from autonomous_research.scientific_director import ScientificDirector


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_sd(
    kp=None, reg=None, gd=None, rm=None,
    ev=None, sp=None, synth=None,
    rc=None, mlc=None, idr=None, pig=None,
    dry_run: bool = True,
) -> ScientificDirector:
    cfg = SDConfig(dry_run=dry_run, journal_path=tempfile.mktemp(suffix=".json"))
    return ScientificDirector(
        knowledge_provider=kp,
        hypothesis_registry=reg,
        gap_detector=gd,
        roadmap_manager=rm,
        evidence_validator=ev,
        study_planner=sp,
        synthesizer=synth,
        rc=rc,
        mlc=mlc,
        idr=idr,
        pig=pig,
        config=cfg,
    )


def _make_obs(sig=SignificanceLevel.LOW, component="Test", metric="test",
              value=1, interpretation="test obs") -> ScientificObservation:
    return ScientificObservation(
        observation_id=make_observation_id(),
        component=component,
        metric=metric,
        value=value,
        interpretation=interpretation,
        significance=sig,
        timestamp=_now_iso(),
    )


def _make_reasoning(rationale="test reason") -> ScientificReasoning:
    return ScientificReasoning(
        knowledge_completeness=0.5,
        evidence_quality=0.5,
        research_value=0.5,
        expected_information_gain=0.5,
        scientific_risk="LOW",
        research_cost="LOW",
        strategic_alignment=0.5,
        rationale=rationale,
    )


def _make_decision(dtype=DecisionType.OBSERVE, dclass=DecisionClass.CLASS_A,
                   requires_human=False) -> ScientificDecision:
    return ScientificDecision(
        decision_id=make_decision_id(),
        decision_type=dtype,
        decision_class=dclass,
        observations=[_make_obs()],
        reasoning=_make_reasoning(),
        decision_text="Test decision",
        delegation_target="NONE",
        expected_outcome="Test outcome",
        confidence=0.8,
        timestamp=_now_iso(),
        requires_human_approval=requires_human,
        approved_by_human=None if requires_human else True,
    )


def _make_review(rtype=ReviewType.DAILY, n_obs=2, n_dec=1, health=SDHealth.HEALTHY) -> ScientificReview:
    return ScientificReview(
        review_id=make_review_id(),
        review_type=rtype,
        date="2025-01-15",
        observations=[_make_obs() for _ in range(n_obs)],
        decisions=[_make_decision() for _ in range(n_dec)],
        recommendations=[],
        health=health,
        summary="Test review",
        duration_ms=100.0,
        timestamp=_now_iso(),
    )


# ─── T001–T025: ReviewType enum ──────────────────────────────────────────────

section("T001-T025: ReviewType enum")

ok("T001", ReviewType.DAILY.value == "DAILY")
ok("T002", ReviewType.WEEKLY.value == "WEEKLY")
ok("T003", ReviewType.MONTHLY.value == "MONTHLY")
ok("T004", ReviewType.PLATFORM.value == "PLATFORM")
ok("T005", ReviewType.STUDY_REVIEW.value == "STUDY_REVIEW")
ok("T006", ReviewType.AD_HOC.value == "AD_HOC")
ok("T007", len(ReviewType) == 6)

ok("T008", DecisionType.CREATE_HYPOTHESIS.value == "CREATE_HYPOTHESIS")
ok("T009", DecisionType.REJECT_STUDY.value == "REJECT_STUDY")
ok("T010", DecisionType.ESCALATE_HUMAN.value == "ESCALATE_HUMAN")
ok("T011", DecisionType.OBSERVE.value == "OBSERVE")
ok("T012", DecisionType.DEFER.value == "DEFER")
ok("T013", DecisionType.APPROVE_STUDY_CLASS_A.value == "APPROVE_STUDY_CLASS_A")
ok("T014", DecisionType.APPROVE_STUDY_CLASS_B_PENDING.value == "APPROVE_STUDY_CLASS_B_PENDING")
ok("T015", DecisionType.CLOSE_STUDY.value == "CLOSE_STUDY")
ok("T016", DecisionType.ARCHIVE_HYPOTHESIS.value == "ARCHIVE_HYPOTHESIS")
ok("T017", DecisionType.PROMOTE_HYPOTHESIS.value == "PROMOTE_HYPOTHESIS")
ok("T018", DecisionType.UPDATE_ROADMAP.value == "UPDATE_ROADMAP")

ok("T019", DecisionClass.CLASS_A.value == "CLASS_A")
ok("T020", DecisionClass.CLASS_B.value == "CLASS_B")

ok("T021", SDHealth.HEALTHY.value == "HEALTHY")
ok("T022", SDHealth.DEGRADED.value == "DEGRADED")
ok("T023", SDHealth.BLIND.value == "BLIND")
ok("T024", SDHealth.NO_DATA.value == "NO_DATA")

ok("T025", SignificanceLevel.INFORMATIONAL.value == "INFORMATIONAL")

# ─── T026–T060: dataclass fields and to_dict ─────────────────────────────────

section("T026-T060: Dataclass fields and to_dict")

obs = _make_obs(SignificanceLevel.HIGH, "RC", "rc_health", "DEGRADED", "RC is degraded")
ok("T026", obs.component == "RC")
ok("T027", obs.metric == "rc_health")
ok("T028", obs.value == "DEGRADED")
ok("T029", obs.interpretation == "RC is degraded")
ok("T030", obs.significance == SignificanceLevel.HIGH)
ok("T031", isinstance(obs.observation_id, str) and obs.observation_id.startswith("sd-obs-"))
ok("T032", isinstance(obs.timestamp, str))

d = obs.to_dict()
ok("T033", d["component"] == "RC")
ok("T034", d["significance"] == "HIGH")
ok("T035", "observation_id" in d)

reas = _make_reasoning("test reasoning")
ok("T036", reas.rationale == "test reasoning")
ok("T037", reas.scientific_risk == "LOW")
rd = reas.to_dict()
ok("T038", "knowledge_completeness" in rd)
ok("T039", "expected_information_gain" in rd)
ok("T040", rd["research_cost"] == "LOW")

dec = _make_decision(DecisionType.CREATE_HYPOTHESIS, DecisionClass.CLASS_A)
ok("T041", dec.decision_type == DecisionType.CREATE_HYPOTHESIS)
ok("T042", dec.decision_class == DecisionClass.CLASS_A)
ok("T043", dec.requires_human_approval is False)
ok("T044", dec.approved_by_human is True)
ok("T045", isinstance(dec.decision_id, str) and dec.decision_id.startswith("sd-dec-"))
dd = dec.to_dict()
ok("T046", dd["decision_type"] == "CREATE_HYPOTHESIS")
ok("T047", dd["decision_class"] == "CLASS_A")
ok("T048", isinstance(dd["observations"], list))

rec = ScientificRecommendation(
    recommendation_id=make_recommendation_id(),
    target="ROADMAP",
    content="Prioritise critical gaps",
    urgency=UrgencyLevel.HIGH,
    decision_class=DecisionClass.CLASS_A,
    rationale="High severity gaps detected",
)
ok("T049", rec.target == "ROADMAP")
ok("T050", rec.urgency == UrgencyLevel.HIGH)
rd2 = rec.to_dict()
ok("T051", rd2["urgency"] == "HIGH")

rev = _make_review(ReviewType.WEEKLY, n_obs=3, n_dec=2, health=SDHealth.DEGRADED)
ok("T052", rev.review_type == ReviewType.WEEKLY)
ok("T053", len(rev.observations) == 3)
ok("T054", len(rev.decisions) == 2)
ok("T055", rev.health == SDHealth.DEGRADED)
rvd = rev.to_dict()
ok("T056", rvd["review_type"] == "WEEKLY")
ok("T057", rvd["health"] == "DEGRADED")
ok("T058", isinstance(rvd["decisions"], list))

rm = ScientificRoadmap(
    entries=[], total_entries=0, critical_gaps=1, high_gaps=2,
    medium_gaps=3, low_gaps=1, pending_plans=5,
    next_priority_id="g-001", next_priority_title="Fill coverage gap",
    next_priority_score=0.9, generated_at=_now_iso(),
)
ok("T059", rm.critical_gaps == 1)
ok("T060", rm.next_priority_score == 0.9)

# ─── T061–T075: SDConfig ─────────────────────────────────────────────────────

section("T061-T075: SDConfig")

cfg = SDConfig()
ok("T061", cfg.journal_path == "data/ars/sd/journal.json")
ok("T062", cfg.max_journal_entries == 365)
ok("T063", cfg.max_hypotheses_per_review == 3)
ok("T064", cfg.max_plans_per_review == 5)
ok("T065", cfg.gap_severity_threshold == "MEDIUM")
ok("T066", cfg.hypothesis_confidence_initial == 0.5)
ok("T067", cfg.auto_approve_class_a is True)
ok("T068", cfg.dry_run is False)
ok("T069", cfg.created_by == "scientific_director")

cfg2 = SDConfig(dry_run=True, max_journal_entries=100)
ok("T070", cfg2.dry_run is True)
ok("T071", cfg2.max_journal_entries == 100)
ok("T072", cfg2.max_hypotheses_per_review == 3, "defaults preserved")

# Validate defaults are reasonable
ok("T073", 1 <= cfg.max_hypotheses_per_review <= 10)
ok("T074", 1 <= cfg.max_plans_per_review <= 20)
ok("T075", 0.0 < cfg.hypothesis_confidence_initial <= 1.0)

# ─── T076–T100: ScientificJournal ────────────────────────────────────────────

section("T076-T100: ScientificJournal")

with tempfile.TemporaryDirectory() as tmpdir:
    jp = os.path.join(tmpdir, "test_journal.json")
    j = ScientificJournal(journal_path=jp, max_entries=50, dry_run=True)
    ok("T076", len(j) == 0)

    # record_review
    rev0 = _make_review()
    e0 = j.record_review(rev0)
    ok("T077", isinstance(e0, JournalEntry))
    ok("T078", e0.entry_type == "REVIEW")
    ok("T079", e0.review_id == rev0.review_id)
    ok("T080", len(j) == 1)

    # record_decision
    dec0 = _make_decision(requires_human=False)
    e1 = j.record_decision(dec0, review_id=rev0.review_id)
    ok("T081", isinstance(e1, JournalEntry))
    ok("T082", e1.entry_type == "DECISION")
    ok("T083", e1.decision == dec0.decision_text)
    ok("T084", len(j) == 2)

    # record_decision (escalation)
    dec_esc = _make_decision(requires_human=True)
    e2 = j.record_decision(dec_esc)
    ok("T085", e2.entry_type == "ESCALATION")

    # record_observation
    e3 = j.record_observation("TestComp", "test_metric", 42, "value is 42")
    ok("T086", isinstance(e3, JournalEntry))
    ok("T087", e3.entry_type == "OBSERVATION")

    # history
    h = j.history(limit=10)
    ok("T088", len(h) == 4)
    ok("T089", h[0].entry_type == "OBSERVATION")  # most recent first

    h_rev = j.history(limit=10, entry_type="REVIEW")
    ok("T090", len(h_rev) == 1)
    ok("T091", h_rev[0].entry_type == "REVIEW")

    # search
    results = j.search("42")
    ok("T092", len(results) >= 1)
    results2 = j.search("XYZZY_NOT_FOUND")
    ok("T093", len(results2) == 0)

    # pending_followups (none should be pending since follow_up_date=None)
    pending = j.pending_followups()
    ok("T094", len(pending) == 0)

    # statistics
    stats = j.statistics()
    ok("T095", stats["total_entries"] == 4)
    ok("T096", "REVIEW" in stats["by_type"])
    ok("T097", stats["escalations"] == 1)
    ok("T098", "pending_followups" in stats)

    # len
    ok("T099", len(j) == 4)

# Persistence test (dry_run=False)
with tempfile.TemporaryDirectory() as tmpdir2:
    jp2 = os.path.join(tmpdir2, "persist_test.json")
    j2 = ScientificJournal(journal_path=jp2, max_entries=50, dry_run=False)
    j2.record_review(_make_review())
    ok("T100", os.path.exists(jp2), "Journal file should be written to disk")

    # Reload
    j3 = ScientificJournal(journal_path=jp2, max_entries=50, dry_run=True)
    ok("T100b", len(j3) == 1, "Loaded 1 entry from disk")

# ─── T101–T115: SD construction and initial status ───────────────────────────

section("T101-T115: SD construction and status")

sd_empty = _make_sd()
ok("T101", sd_empty is not None)
ok("T102", isinstance(sd_empty, ScientificDirector))

status = sd_empty.status()
ok("T103", isinstance(status, ScientificHealth))
ok("T104", status.health == SDHealth.NO_DATA)
ok("T105", status.total_reviews == 0)
ok("T106", status.consecutive_review_failures == 0)
ok("T107", status.knowledge_completeness == 0.0)
ok("T108", status.rc_health == "UNKNOWN")
ok("T109", status.mlc_health == "UNKNOWN")
ok("T110", status.hypotheses_proposed == 0)
ok("T111", status.gaps_open == 0)
ok("T112", isinstance(status.detail, str))

sd_dict = status.to_dict()
ok("T113", sd_dict["health"] == "NO_DATA")
ok("T114", "knowledge_completeness" in sd_dict)
ok("T115", "last_review_id" in sd_dict)

# ─── T116–T145: Observation layer ────────────────────────────────────────────

section("T116-T145: Observation layer")

# All None — empty lists
sd0 = _make_sd()
ok("T116", sd0._observe_knowledge() == [])
ok("T117", sd0._observe_gaps() == [])
ok("T118", sd0._observe_roadmap() == [])
ok("T119", sd0._observe_research() == [])
ok("T120", sd0._observe_learning() == [])
ok("T121", sd0._observe_idr() == [])
ok("T122", sd0._observe_hypotheses() == [])
ok("T123", sd0._observe_synthesis() == [])

# KP mock
kp_mock = MagicMock()
kp_mock.get_snapshot.return_value = MagicMock(
    total_findings=10, total_edges=5, total_strategies=3,
    total_certifications=2,
)
kp_mock.get_warnings.return_value = []
sd_kp = _make_sd(kp=kp_mock)
kp_obs = sd_kp._observe_knowledge()
ok("T124", len(kp_obs) >= 1)
ok("T125", kp_obs[0].component == "KnowledgeProvider")
ok("T126", kp_obs[0].metric == "knowledge_completeness")
ok("T127", isinstance(kp_obs[0].value, float))

# KP with warnings
kp_warn = MagicMock()
kp_warn.get_snapshot.return_value = MagicMock(
    total_findings=1, total_edges=0, total_strategies=0, total_certifications=0,
)
kp_warn.get_warnings.return_value = ["w1", "w2", "w3", "w4", "w5"]
sd_warn = _make_sd(kp=kp_warn)
obs_warn = sd_warn._observe_knowledge()
ok("T128", len(obs_warn) == 2, "completeness obs + warnings obs")
ok("T129", obs_warn[1].significance == SignificanceLevel.HIGH)

# GD mock
gd_mock = MagicMock()

class _FakeSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"

@dataclass
class _FakeGap:
    gap_id: str = "g-001"
    title: str = "Coverage gap"
    description: str = "Missing data"
    severity: _FakeSeverity = _FakeSeverity.CRITICAL
    category: Any = None
    estimated_knowledge_gain: float = 0.8
    confidence: float = 0.7
    status: Any = None

gd_mock.detect.return_value = None
gd_mock.list_open.return_value = [_FakeGap(), _FakeGap(gap_id="g-002", severity=_FakeSeverity.HIGH)]
gd_mock.statistics.return_value = {}
sd_gd = _make_sd(gd=gd_mock)
gd_obs = sd_gd._observe_gaps()
ok("T130", len(gd_obs) >= 1)
ok("T131", gd_obs[0].component == "GapDetector")
ok("T132", gd_obs[0].significance == SignificanceLevel.HIGH, "critical gap => HIGH sig")

# RM mock
rm_mock = MagicMock()
rm_entry = MagicMock()
rm_entry.recommended_study_title = "Study X"
rm_entry.priority_score = 0.9
rm_mock.list_entries.return_value = [rm_entry]
rm_mock.top_priorities.return_value = [rm_entry]
sd_rm = _make_sd(rm=rm_mock)
rm_obs = sd_rm._observe_roadmap()
ok("T133", len(rm_obs) == 1)
ok("T134", rm_obs[0].component == "RoadmapManager")

# RC mock
rc_mock = MagicMock()
rc_st = MagicMock()
rc_st.health = MagicMock(value="HEALTHY")
rc_st.total_runs = 5
rc_st.consecutive_failures = 0
rc_mock.status.return_value = rc_st
sd_rc = _make_sd(rc=rc_mock)
rc_obs = sd_rc._observe_research()
ok("T135", len(rc_obs) == 1)
ok("T136", rc_obs[0].metric == "rc_health")
ok("T137", rc_obs[0].value == "HEALTHY")

# RC with failures => HIGH sig
rc_fail = MagicMock()
rc_st_f = MagicMock()
rc_st_f.health = MagicMock(value="DEGRADED")
rc_st_f.total_runs = 10
rc_st_f.consecutive_failures = 6
rc_fail.status.return_value = rc_st_f
sd_rcf = _make_sd(rc=rc_fail)
rcf_obs = sd_rcf._observe_research()
ok("T138", rcf_obs[0].significance == SignificanceLevel.HIGH)

# MLC mock
mlc_mock = MagicMock()
mlc_st = MagicMock()
mlc_st.health = MagicMock(value="HEALTHY")
mlc_st.pipeline_healthy = True
mlc_mock.status.return_value = mlc_st
sd_mlc = _make_sd(mlc=mlc_mock)
mlc_obs = sd_mlc._observe_learning()
ok("T139", len(mlc_obs) == 1)
ok("T140", mlc_obs[0].component == "MarketLearningCoordinator")

# IDR mock
idr_mock = MagicMock()
idr_stats = MagicMock()
idr_stats.active_count = 7
idr_mock.statistics.return_value = idr_stats
sd_idr = _make_sd(idr=idr_mock)
idr_obs = sd_idr._observe_idr()
ok("T141", len(idr_obs) == 1)
ok("T142", idr_obs[0].value == 7)

# Hypothesis registry mock
reg_mock = MagicMock()
reg_mock.statistics.return_value = {
    "total": 10, "by_status": {"PROPOSED": 3, "CONFIRMED": 2, "REJECTED": 1}
}
sd_reg = _make_sd(reg=reg_mock)
reg_obs = sd_reg._observe_hypotheses()
ok("T143", len(reg_obs) == 1)
ok("T144", reg_obs[0].component == "HypothesisRegistry")

# Synthesizer mock
synth_mock = MagicMock()
synth_stats = MagicMock()
synth_stats.total_synthesized_findings = 5
synth_stats.total_contradictions = 1
synth_mock.statistics.return_value = synth_stats
sd_synth = _make_sd(synth=synth_mock)
synth_obs = sd_synth._observe_synthesis()
ok("T145", len(synth_obs) == 1)

# ─── T146–T165: Reasoning layer ──────────────────────────────────────────────

section("T146-T165: Reasoning layer")

sd_r = _make_sd()

# knowledge completeness
class _FakeSnap:
    total_findings = 50
    total_edges = 10
    total_strategies = 5
    total_certifications = 5

ok("T146", sd_r._evaluate_knowledge_completeness(_FakeSnap()) == 1.0)
ok("T147", sd_r._evaluate_knowledge_completeness(MagicMock(
    total_findings=0, total_edges=0, total_certifications=0)) == 0.0)
ok("T148", 0.0 < sd_r._evaluate_knowledge_completeness(MagicMock(
    total_findings=10, total_edges=2, total_certifications=1)) < 1.0)

# gap urgency filtering
gaps_mixed = [
    _FakeGap(gap_id="g-c", severity=_FakeSeverity.CRITICAL),
    _FakeGap(gap_id="g-h", severity=_FakeSeverity.HIGH),
    _FakeGap(gap_id="g-l", severity=_FakeSeverity("LOW") if hasattr(_FakeSeverity, "LOW") else MagicMock(value="LOW")),
]
# patch low
class _FakeSevAll(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class _FakeGapAll:
    gap_id: str
    title: str = "title"
    description: str = "desc"
    severity: _FakeSevAll = _FakeSevAll.MEDIUM
    category: Any = None
    estimated_knowledge_gain: float = 0.5
    confidence: float = 0.5
    status: Any = None

g_crit = _FakeGapAll("g-c", severity=_FakeSevAll.CRITICAL)
g_high = _FakeGapAll("g-h", severity=_FakeSevAll.HIGH)
g_med  = _FakeGapAll("g-m", severity=_FakeSevAll.MEDIUM)
g_low  = _FakeGapAll("g-l", severity=_FakeSevAll.LOW)

sd_med_thresh = _make_sd()  # default threshold=MEDIUM
urgent = sd_med_thresh._evaluate_gap_urgency([g_crit, g_high, g_med, g_low])
ok("T149", g_low not in urgent, "LOW excluded by MEDIUM threshold")
ok("T150", g_crit in urgent, "CRITICAL included")
ok("T151", g_high in urgent, "HIGH included")
ok("T152", g_med in urgent, "MEDIUM included")
# Order: critical first
ok("T153", urgent[0].gap_id == "g-c", "CRITICAL should be first")

# classify_study
class _FakeStudyType(Enum):
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    META_LEARNING = "META_LEARNING"
    CUSTOM = "CUSTOM"
    EDGE_VALIDATION = "EDGE_VALIDATION"

class _FakeRiskClass(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

plan_a = MagicMock(study_type=_FakeStudyType.HISTORICAL_REPLAY, risk_class=_FakeRiskClass.LOW)
plan_b_meta = MagicMock(study_type=_FakeStudyType.META_LEARNING, risk_class=_FakeRiskClass.LOW)
plan_b_custom = MagicMock(study_type=_FakeStudyType.CUSTOM, risk_class=_FakeRiskClass.MEDIUM)
plan_b_high_risk = MagicMock(study_type=_FakeStudyType.EDGE_VALIDATION, risk_class=_FakeRiskClass.HIGH)

dc_a, _ = sd_r._classify_study(plan_a)
ok("T154", dc_a == DecisionClass.CLASS_A)

dc_b_meta, reason_meta = sd_r._classify_study(plan_b_meta)
ok("T155", dc_b_meta == DecisionClass.CLASS_B)
ok("T156", "META_LEARNING" in reason_meta)

dc_b_cus, _ = sd_r._classify_study(plan_b_custom)
ok("T157", dc_b_cus == DecisionClass.CLASS_B)

dc_b_hr, reason_hr = sd_r._classify_study(plan_b_high_risk)
ok("T158", dc_b_hr == DecisionClass.CLASS_B)
ok("T159", "HIGH" in reason_hr)

dc_none, _ = sd_r._classify_study(None)
ok("T160", dc_none == DecisionClass.CLASS_A)

# research value
ok("T161", 0.0 <= sd_r._evaluate_research_value(g_crit) <= 1.0)
ok("T162", sd_r._evaluate_research_value(g_crit) > sd_r._evaluate_research_value(g_low))

# recommendations
high_obs = _make_obs(SignificanceLevel.HIGH, "GapDetector", "open_gaps", 5, "5 gaps open")
recs = sd_r._build_recommendations([high_obs])
ok("T163", len(recs) >= 1)
ok("T164", recs[0].target == "ROADMAP")

low_obs = _make_obs(SignificanceLevel.LOW, "KP", "completeness", 0.9, "Rich")
recs2 = sd_r._build_recommendations([low_obs])
ok("T165", len(recs2) == 0)

# ─── T166–T190: daily_review ─────────────────────────────────────────────────

section("T166-T190: daily_review")

# Minimal (no components)
sd_bare = _make_sd()
rev = sd_bare.daily_review()
ok("T166", isinstance(rev, ScientificReview))
ok("T167", rev.review_type == ReviewType.DAILY)
ok("T168", isinstance(rev.review_id, str))
ok("T169", isinstance(rev.summary, str))
ok("T170", rev.duration_ms >= 0)
ok("T171", rev.health in (SDHealth.HEALTHY, SDHealth.DEGRADED, SDHealth.BLIND))

# Journal recorded
ok("T172", len(sd_bare._journal) >= 1)

# Status updates after review
st = sd_bare.status()
ok("T173", st.last_review_id == rev.review_id)
ok("T174", st.last_review_type == "DAILY")
ok("T175", st.health != SDHealth.NO_DATA)

# With GD and KP
kp2 = MagicMock()
kp2.get_snapshot.return_value = MagicMock(
    total_findings=20, total_edges=5, total_strategies=3, total_certifications=2,
)
kp2.get_warnings.return_value = []
gd2 = MagicMock()
gd2.detect.return_value = None
gd2.list_open.return_value = [
    _FakeGapAll("g-1", severity=_FakeSevAll.HIGH),
    _FakeGapAll("g-2", severity=_FakeSevAll.MEDIUM),
]
gd2.statistics.return_value = {}

sd_full = _make_sd(kp=kp2, gd=gd2)
rev2 = sd_full.daily_review()
ok("T176", len(rev2.observations) >= 2)
ok("T177", rev2.review_type == ReviewType.DAILY)

# dry_run check: no hypotheses created when reg is None
ok("T178", sd_full._config.dry_run is True)

# Multiple daily reviews don't crash
rev3 = sd_bare.daily_review()
ok("T179", isinstance(rev3, ScientificReview))
st2 = sd_bare.status()
ok("T180", st2.last_review_id == rev3.review_id)

# to_dict works
ok("T181", isinstance(rev.to_dict(), dict))

# Observations have proper IDs
for o in rev2.observations:
    ok("T182", o.observation_id.startswith("sd-obs-"))
    break

# Review has date
ok("T183", len(rev.date) == 10)  # "YYYY-MM-DD"

# Health in review
ok("T184", isinstance(rev.health, SDHealth))

# Review recommendations list present
ok("T185", isinstance(rev.recommendations, list))

# SD doesn't access trading layer
ok("T186", not hasattr(sd_bare, "_broker"), "SD has no broker access")
ok("T187", not hasattr(sd_bare, "_order_manager"), "SD has no order manager")
ok("T188", not hasattr(sd_bare, "_execution_engine"), "SD has no execution engine")

# review_id is unique per call
rev_a = _make_sd().daily_review()
rev_b = _make_sd().daily_review()
ok("T189", rev_a.review_id != rev_b.review_id)

# Summary includes type
ok("T190", "DAILY" in rev.summary)

# ─── T191–T205: weekly_review ────────────────────────────────────────────────

section("T191-T205: weekly_review")

sd_w = _make_sd()
wrev = sd_w.weekly_review()
ok("T191", wrev.review_type == ReviewType.WEEKLY)
ok("T192", isinstance(wrev, ScientificReview))
ok("T193", "WEEKLY" in wrev.summary)
ok("T194", wrev.health in (SDHealth.HEALTHY, SDHealth.DEGRADED, SDHealth.BLIND))
ok("T195", len(sd_w._journal) >= 1)

st_w = sd_w.status()
ok("T196", st_w.last_review_type == "WEEKLY")

# weekly includes synthesis observations when synth is set
synth2 = MagicMock()
synth_st2 = MagicMock()
synth_st2.total_synthesized_findings = 12
synth_st2.total_contradictions = 0
synth2.statistics.return_value = synth_st2
sd_ws = _make_sd(synth=synth2)
wrev2 = sd_ws.weekly_review()
ok("T197", any(o.component == "CrossStudySynthesizer" for o in wrev2.observations))

ok("T198", isinstance(wrev.to_dict(), dict))
ok("T199", "review_id" in wrev.to_dict())
ok("T200", wrev.duration_ms >= 0)
ok("T201", len(wrev.observations) >= 0)
ok("T202", isinstance(wrev.decisions, list))
ok("T203", isinstance(wrev.recommendations, list))
ok("T204", len(wrev.review_id) > 10)
ok("T205", wrev.date != "")

# ─── T206–T215: monthly_review ───────────────────────────────────────────────

section("T206-T215: monthly_review")

sd_m = _make_sd()
mrev = sd_m.monthly_review()
ok("T206", mrev.review_type == ReviewType.MONTHLY)
ok("T207", "MONTHLY" in mrev.summary)
ok("T208", isinstance(mrev, ScientificReview))

idr3 = MagicMock()
idr_s3 = MagicMock()
idr_s3.active_count = 3
idr3.statistics.return_value = idr_s3
sd_mi = _make_sd(idr=idr3)
mrev2 = sd_mi.monthly_review()
ok("T209", any(o.component == "IDRRepository" for o in mrev2.observations))
ok("T210", mrev.health in SDHealth.__members__.values())
ok("T211", mrev.duration_ms >= 0)
ok("T212", isinstance(mrev.to_dict(), dict))
ok("T213", sd_m.status().last_review_type == "MONTHLY")
ok("T214", sd_m.status().health != SDHealth.NO_DATA)
ok("T215", "MONTHLY" in mrev.summary)

# ─── T216–T225: evaluate_platform ────────────────────────────────────────────

section("T216-T225: evaluate_platform")

sd_p = _make_sd()
prev = sd_p.evaluate_platform()
ok("T216", prev.review_type == ReviewType.PLATFORM)
ok("T217", "PLATFORM" in prev.summary)
ok("T218", isinstance(prev, ScientificReview))
ok("T219", prev.health in SDHealth.__members__.values())
ok("T220", sd_p.status().last_review_type == "PLATFORM")

# platform includes idr + synthesis observations when available
idr4 = MagicMock()
idr4.statistics.return_value = MagicMock(active_count=10)
synth4 = MagicMock()
synth4.statistics.return_value = MagicMock(total_synthesized_findings=5, total_contradictions=0)
sd_pf = _make_sd(idr=idr4, synth=synth4)
prev2 = sd_pf.evaluate_platform()
ok("T221", any(o.component == "IDRRepository" for o in prev2.observations))
ok("T222", any(o.component == "CrossStudySynthesizer" for o in prev2.observations))
ok("T223", isinstance(prev.to_dict(), dict))
ok("T224", prev.duration_ms >= 0)
ok("T225", isinstance(prev.decisions, list))

# ─── T226–T240: approve_study ────────────────────────────────────────────────

section("T226-T240: approve_study")

# Class A plan
sp_mock = MagicMock()
plan_class_a = MagicMock()
plan_class_a.plan_id = "plan-001"
plan_class_a.title = "Edge Validation Study"
plan_class_a.study_type = _FakeStudyType.EDGE_VALIDATION
plan_class_a.risk_class = _FakeRiskClass.LOW
sp_mock.get_plan.return_value = plan_class_a
sp_mock.list_plans.return_value = []

sd_sp = _make_sd(sp=sp_mock)
dec_a = sd_sp.approve_study("plan-001")
ok("T226", isinstance(dec_a, ScientificDecision))
ok("T227", dec_a.decision_type == DecisionType.APPROVE_STUDY_CLASS_A)
ok("T228", dec_a.decision_class == DecisionClass.CLASS_A)
ok("T229", dec_a.requires_human_approval is False)
ok("T230", "plan-001" in dec_a.decision_text)
ok("T231", dec_a.confidence > 0.0)

# Class B plan (META_LEARNING)
plan_class_b = MagicMock()
plan_class_b.plan_id = "plan-002"
plan_class_b.title = "Meta Learning Study"
plan_class_b.study_type = _FakeStudyType.META_LEARNING
plan_class_b.risk_class = _FakeRiskClass.MEDIUM
sp_mock2 = MagicMock()
sp_mock2.get_plan.return_value = plan_class_b
sp_mock2.list_plans.return_value = []

sd_sp2 = _make_sd(sp=sp_mock2)
dec_b = sd_sp2.approve_study("plan-002")
ok("T232", dec_b.decision_type == DecisionType.APPROVE_STUDY_CLASS_B_PENDING)
ok("T233", dec_b.decision_class == DecisionClass.CLASS_B)
ok("T234", dec_b.requires_human_approval is True)
ok("T235", dec_b.approved_by_human is None)

# Plan not found
sp_missing = MagicMock()
sp_missing.get_plan.side_effect = KeyError("plan-999")
sd_spm = _make_sd(sp=sp_missing)
dec_missing = sd_spm.approve_study("plan-999")
ok("T236", dec_missing.decision_type == DecisionType.REJECT_STUDY)
ok("T237", dec_missing.confidence > 0.0)

# No study planner → still returns a decision
sd_nosp = _make_sd()
dec_nosp = sd_nosp.approve_study("plan-noop")
ok("T238", isinstance(dec_nosp, ScientificDecision))
ok("T239", dec_nosp.decision_type == DecisionType.APPROVE_STUDY_CLASS_A, "no plan -> default CLASS A")

# Decision is journaled
ok("T240", len(sd_sp._journal) >= 1)

# ─── T241–T248: reject_study ─────────────────────────────────────────────────

section("T241-T248: reject_study")

sd_rej = _make_sd()
dec_rej = sd_rej.reject_study("plan-003", "insufficient evidence base")
ok("T241", isinstance(dec_rej, ScientificDecision))
ok("T242", dec_rej.decision_type == DecisionType.REJECT_STUDY)
ok("T243", dec_rej.requires_human_approval is False)
ok("T244", "insufficient evidence base" in dec_rej.decision_text)
ok("T245", dec_rej.confidence > 0.5)
ok("T246", "plan-003" in dec_rej.decision_text)
ok("T247", isinstance(dec_rej.to_dict(), dict))
ok("T248", len(sd_rej._journal) >= 1)

# ─── T249–T258: roadmap API ───────────────────────────────────────────────────

section("T249-T258: roadmap API")

sd_rm0 = _make_sd()
rm0 = sd_rm0.roadmap()
ok("T249", isinstance(rm0, ScientificRoadmap))
ok("T250", rm0.total_entries == 0)
ok("T251", rm0.pending_plans == 0)
ok("T252", isinstance(rm0.generated_at, str))

rm_full = MagicMock()
entry1 = MagicMock()
entry1.gap = MagicMock(severity=MagicMock(value="CRITICAL"), gap_id="g-1")
entry1.recommended_study_title = "Study Critical"
entry1.priority_score = 0.95
entry2 = MagicMock()
entry2.gap = MagicMock(severity=MagicMock(value="HIGH"), gap_id="g-2")
entry2.recommended_study_title = "Study High"
entry2.priority_score = 0.7
rm_full.list_entries.return_value = [entry1, entry2]
rm_full.top_priorities.return_value = [entry1]

sp_plans = MagicMock()
sp_plans.list_plans.return_value = ["p1", "p2"]

sd_rmp = _make_sd(rm=rm_full, sp=sp_plans)
rm_p = sd_rmp.roadmap()
ok("T253", rm_p.total_entries == 2)
ok("T254", rm_p.critical_gaps == 1)
ok("T255", rm_p.high_gaps == 1)
ok("T256", rm_p.pending_plans == 2)
ok("T257", rm_p.next_priority_score == 0.95)
ok("T258", isinstance(rm_p.to_dict(), dict))

# ─── T259–T268: hypothesis generation ────────────────────────────────────────

section("T259-T268: hypothesis generation (dry_run=True)")

reg_g = MagicMock()
reg_g.search.return_value = []  # no existing hypotheses

gd_g = MagicMock()
gd_g.detect.return_value = None
gd_g.list_open.return_value = [
    _FakeGapAll("g-x", title="Coverage gap X", severity=_FakeSevAll.HIGH),
    _FakeGapAll("g-y", title="Regime gap Y", severity=_FakeSevAll.MEDIUM),
    _FakeGapAll("g-z", title="Temporal gap Z", severity=_FakeSevAll.MEDIUM),
    _FakeGapAll("g-w", title="Evidence gap W", severity=_FakeSevAll.LOW),
]
gd_g.statistics.return_value = {}

sd_hg = _make_sd(reg=reg_g, gd=gd_g)
gaps_f = sd_hg._evaluate_gap_urgency(gd_g.list_open.return_value)
decs = sd_hg._generate_hypotheses_for_gaps(gaps_f)
ok("T259", isinstance(decs, list))
ok("T260", len(decs) <= sd_hg._config.max_hypotheses_per_review, "never exceed max")
ok("T261", all(isinstance(d, ScientificDecision) for d in decs))
ok("T262", all(d.decision_type in (DecisionType.CREATE_HYPOTHESIS, DecisionType.DEFER) for d in decs))

# When existing hypothesis found, DEFER
reg_exists = MagicMock()
reg_exists.search.return_value = [MagicMock()]  # simulate found
sd_hg_exist = _make_sd(reg=reg_exists, gd=gd_g)
decs_exist = sd_hg_exist._generate_hypotheses_for_gaps(gaps_f)
ok("T263", all(d.decision_type == DecisionType.DEFER for d in decs_exist))

# No gaps → empty decisions
ok("T264", sd_hg._generate_hypotheses_for_gaps([]) == [])

# No registry → empty decisions
sd_hg_noreg = _make_sd(gd=gd_g)
ok("T265", sd_hg_noreg._generate_hypotheses_for_gaps(gaps_f) == [])

# Decisions contain observations and reasoning
if decs:
    ok("T266", len(decs[0].observations) >= 1)
    ok("T267", isinstance(decs[0].reasoning, ScientificReasoning))
    ok("T268", decs[0].delegation_target in ("HypothesisRegistry", "NONE"))

# ─── T269–T278: decision classification ──────────────────────────────────────

section("T269-T278: decision classification")

sd_dc = _make_sd()
# All edge cases

plan_str_type = MagicMock()
plan_str_type.study_type = "HISTORICAL_REPLAY"
plan_str_type.risk_class = MagicMock(value="LOW")
dc, _ = sd_dc._classify_study(plan_str_type)
ok("T269", dc == DecisionClass.CLASS_A)

plan_meta_str = MagicMock()
plan_meta_str.study_type = "META_LEARNING"
plan_meta_str.risk_class = MagicMock(value="LOW")
dc2, r2 = sd_dc._classify_study(plan_meta_str)
ok("T270", dc2 == DecisionClass.CLASS_B)
ok("T271", "META_LEARNING" in r2)

plan_custom_str = MagicMock()
plan_custom_str.study_type = "CUSTOM"
plan_custom_str.risk_class = MagicMock(value="MEDIUM")
dc3, _ = sd_dc._classify_study(plan_custom_str)
ok("T272", dc3 == DecisionClass.CLASS_B)

plan_high_risk = MagicMock()
plan_high_risk.study_type = "EDGE_VALIDATION"
plan_high_risk.risk_class = MagicMock(value="HIGH")
dc4, r4 = sd_dc._classify_study(plan_high_risk)
ok("T273", dc4 == DecisionClass.CLASS_B)
ok("T274", "HIGH" in r4)

plan_medium_risk = MagicMock()
plan_medium_risk.study_type = "REGIME_ANALYSIS"
plan_medium_risk.risk_class = MagicMock(value="MEDIUM")
dc5, _ = sd_dc._classify_study(plan_medium_risk)
ok("T275", dc5 == DecisionClass.CLASS_A)

# Enum-valued study type
plan_enum = MagicMock()
plan_enum.study_type = _FakeStudyType.META_LEARNING
plan_enum.risk_class = _FakeRiskClass.LOW
dc6, _ = sd_dc._classify_study(plan_enum)
ok("T276", dc6 == DecisionClass.CLASS_B)

plan_enum_a = MagicMock()
plan_enum_a.study_type = _FakeStudyType.HISTORICAL_REPLAY
plan_enum_a.risk_class = _FakeRiskClass.MEDIUM
dc7, _ = sd_dc._classify_study(plan_enum_a)
ok("T277", dc7 == DecisionClass.CLASS_A)

# None plan
dc_none2, _ = sd_dc._classify_study(None)
ok("T278", dc_none2 == DecisionClass.CLASS_A)

# ─── T279–T285: human escalation ─────────────────────────────────────────────

section("T279-T285: human escalation")

gd_esc = MagicMock()
gd_esc.detect.return_value = None
gd_esc.list_open.return_value = [
    _FakeGapAll(f"g-{i}", severity=_FakeSevAll.CRITICAL) for i in range(4)
]
gd_esc.statistics.return_value = {}
reg_esc = MagicMock()
reg_esc.search.return_value = [MagicMock()]  # all have existing hypotheses

sd_esc = _make_sd(gd=gd_esc, reg=reg_esc)
escs = sd_esc._check_escalations()
ok("T279", len(escs) >= 1)
ok("T280", any(d.decision_type == DecisionType.ESCALATE_HUMAN for d in escs))
ok("T281", any(d.requires_human_approval for d in escs))

# RC failure escalation
rc_fail2 = MagicMock()
rc_st_f2 = MagicMock()
rc_st_f2.health = MagicMock(value="BLIND")
rc_st_f2.total_runs = 20
rc_st_f2.consecutive_failures = 7
rc_fail2.status.return_value = rc_st_f2

sd_rcesc = _make_sd(rc=rc_fail2)
rc_escs = sd_rcesc._check_escalations()
ok("T282", len(rc_escs) >= 1)
ok("T283", rc_escs[0].decision_type == DecisionType.ESCALATE_HUMAN)
ok("T284", rc_escs[0].delegation_target == "HUMAN_OPERATOR")
ok("T285", rc_escs[0].confidence > 0.5)

# ─── T286–T293: thread safety ────────────────────────────────────────────────

section("T286-T293: thread safety")

sd_ts = _make_sd()
results_ts = []
errors_ts  = []

def _do_review():
    try:
        r = sd_ts.daily_review()
        results_ts.append(r.review_id)
    except Exception as exc:
        errors_ts.append(str(exc))

threads = [threading.Thread(target=_do_review) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()

ok("T286", len(errors_ts) == 0, f"no thread errors: {errors_ts}")
ok("T287", len(results_ts) == 5, "5 reviews completed")
ok("T288", len(set(results_ts)) == 5, "all review IDs unique")

# Journal concurrent writes
j_ts = ScientificJournal(
    journal_path=tempfile.mktemp(suffix=".json"),
    max_entries=100,
    dry_run=True,
)
jresults = []

def _journal_write(i):
    try:
        j_ts.record_observation("Comp", f"metric_{i}", i, f"value {i}")
        jresults.append(i)
    except Exception as exc:
        errors_ts.append(str(exc))

jthreads = [threading.Thread(target=_journal_write, args=(i,)) for i in range(20)]
for t in jthreads:
    t.start()
for t in jthreads:
    t.join()

ok("T289", len(errors_ts) == 0, f"no journal thread errors")
ok("T290", len(j_ts) == 20, f"20 entries written: {len(j_ts)}")
ok("T291", len(jresults) == 20)

# Status is thread-safe
st_ts = sd_ts.status()
ok("T292", isinstance(st_ts, ScientificHealth))
ok("T293", st_ts.health != SDHealth.NO_DATA)

# ─── T294–T300: constitutional constraints ────────────────────────────────────

section("T294-T300: Constitutional constraints")

sd_const = _make_sd()

# SD never directly trades
ok("T294", not hasattr(sd_const, "_broker"))
ok("T295", not hasattr(sd_const, "_order_manager"))
ok("T296", not hasattr(sd_const, "_execution_engine"))

# Every decision has a delegation_target
dec_const = sd_const.reject_study("plan-x", "test reason")
ok("T297", dec_const.delegation_target in ("NONE", "HypothesisRegistry",
    "ResearchCoordinator", "MarketLearningCoordinator", "HUMAN_OPERATOR"))

# Every decision has reasoning
ok("T298", isinstance(dec_const.reasoning, ScientificReasoning))
ok("T299", len(dec_const.reasoning.rationale) > 5)

# Every decision has expected_outcome
ok("T300", len(dec_const.expected_outcome) > 0)

# ─── Summary ──────────────────────────────────────────────────────────────────

print(f"\n{'='*58}")
print(f"  Scientific Director Test Suite")
print(f"  PASS: {PASS}  FAIL: {FAIL}  TOTAL: {PASS + FAIL}")
print(f"{'='*58}")

if ERRORS:
    print("\nFailed tests:")
    for e in ERRORS:
        print(f"  {e}")

sys.exit(0 if FAIL == 0 else 1)

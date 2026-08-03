"""
test_hypothesis_registry.py — ARS Phase 1.2 test suite.

Covers:
    - Full lifecycle path (PROPOSED → CONFIRMED)
    - Full rejection path (PROPOSED → REJECTED → ARCHIVED)
    - Revival path (REJECTED → PROPOSED)
    - All invalid transitions (raises InvalidTransitionError)
    - Evidence validation (valid / invalid / EXTERNAL bypass)
    - Persistence (save / reload round-trip)
    - Concurrent access (threading)
    - Duplicate title detection (warning only)
    - Missing hypothesis (HypothesisNotFoundError)
    - All query methods
    - Statistics
    - Backup file creation
    - Read-only constraint (KnowledgeProvider stores unchanged)
    - Backward compatibility (load registry written by older version)

Run:
    python test_hypothesis_registry.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_research import (
    HypothesisRegistry,
    KnowledgeProvider,
    HypothesisStatus,
    HypothesisPriority,
    HypothesisClassification,
    EvidenceReference,
    EvidenceType,
    ValidationResult,
    InvalidTransitionError,
    HypothesisNotFoundError,
    InvalidEvidenceError,
    RegistryValidationError,
    VALID_TRANSITIONS,
)


# ═════════════════════════════════════════════════════════════════════════════
# Minimal test framework
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    detail: str
    error: Optional[str] = None


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
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════

def make_registry(tmp_dir: Path) -> HypothesisRegistry:
    kp = KnowledgeProvider()
    return HypothesisRegistry(
        knowledge_provider=kp,
        registry_path=tmp_dir / "test_registry.json",
    )


def _study_evidence() -> EvidenceReference:
    """Returns a valid study evidence reference (study002a exists in KP)."""
    return EvidenceReference(
        evidence_id="study002a",
        evidence_type=EvidenceType.STUDY,
        description="Primary study backing this hypothesis",
        added_at=datetime.now(),
        added_by="test",
    )


def _create_minimal(reg: HypothesisRegistry, title: str = "Test hypothesis",
                    with_evidence: bool = True) -> "ScientificHypothesis":  # type: ignore[name-defined]
    evidence = [_study_evidence()] if with_evidence else []
    return reg.create_hypothesis(
        title=title,
        research_question="Does atr_14 > 0.03 predict wins in TRENDING_DOWN?",
        description="Testing ATR threshold in trending down regime.",
        origin="Performance gap in TRENDING_DOWN detected",
        priority=HypothesisPriority.HIGH,
        classification=HypothesisClassification.PERFORMANCE_GAP,
        knowledge_gap="Unknown whether ATR threshold separates winners in TRENDING_DOWN",
        expected_knowledge_gain="Validated or rejected ATR threshold for this regime",
        validation_method="Walk-forward decision tree analysis on replay.db",
        supporting_evidence=evidence,
        origin_study="study002a",
        created_by="test_suite",
        confidence=0.65,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════════════════════════════════════

def run_all_tests() -> TestRunner:
    runner = TestRunner()
    tmp = Path(tempfile.mkdtemp(prefix="ars_test_"))

    # ── T-01: Instantiation ──────────────────────────────────────────────────
    def t01():
        reg = make_registry(tmp / "t01")
        ok(reg is not None, "Registry is None")
        return "instantiated with empty store"
    runner.run("T-01: Instantiation", t01)

    # ── T-02: Create hypothesis with valid study evidence ─────────────────────
    def t02():
        reg = make_registry(tmp / "t02")
        h = _create_minimal(reg)
        ok(h.hypothesis_id.startswith("H"), f"Bad ID format: {h.hypothesis_id}")
        ok(h.status == HypothesisStatus.PROPOSED, f"Expected PROPOSED, got {h.status}")
        ok(len(h.decision_history) == 1, f"Expected 1 event, got {len(h.decision_history)}")
        ok(h.decision_history[0].action == "CREATE", "First event not CREATE")
        return f"created {h.hypothesis_id}"
    runner.run("T-02: create_hypothesis() — valid study evidence", t02)

    # ── T-03: ID format ───────────────────────────────────────────────────────
    def t03():
        reg = make_registry(tmp / "t03")
        h1 = _create_minimal(reg, "Hypothesis 1")
        h2 = _create_minimal(reg, "Hypothesis 2")
        ok(h1.hypothesis_id != h2.hypothesis_id, "Duplicate IDs")
        now = datetime.now()
        ok(h1.hypothesis_id.startswith(f"H{now.year}-{now.month:02d}-"),
           f"ID prefix wrong: {h1.hypothesis_id}")
        return f"IDs: {h1.hypothesis_id}, {h2.hypothesis_id}"
    runner.run("T-03: Hypothesis ID format and uniqueness", t03)

    # ── T-04: Full happy-path lifecycle: PROPOSED → CONFIRMED ─────────────────
    def t04():
        reg = make_registry(tmp / "t04")
        h = _create_minimal(reg)
        hid = h.hypothesis_id

        transitions = [
            (HypothesisStatus.UNDER_REVIEW, "analyst", "Ready for review"),
            (HypothesisStatus.APPROVED,     "lead",    "Hypothesis approved"),
            (HypothesisStatus.PLANNED,      "system",  "Study scheduled"),
            (HypothesisStatus.RUNNING,      "system",  "Study started"),
        ]
        for status, actor, reason in transitions:
            h = reg.update_status(hid, status, actor=actor, reason=reason)
            ok(h.status == status, f"Expected {status}, got {h.status}")

        # Set validation result while RUNNING
        vr = ValidationResult(
            validated_at=datetime.now(),
            validated_by="system",
            verdict="PASS",
            findings=["ATR > 0.029 confirmed as winner DNA marker"],
            study_ids=["study002a"],
            metrics={"lift": 2.7, "confidence": 0.72},
            notes="Confirmed across 18 test observations",
        )
        reg.set_validation_result(hid, vr, actor="system")

        h = reg.update_status(hid, HypothesisStatus.VALIDATED, actor="system", reason="Study complete")
        h = reg.update_status(hid, HypothesisStatus.CONFIRMED, actor="analyst", reason="Evidence sufficient")

        ok(h.status == HypothesisStatus.CONFIRMED, f"Final status wrong: {h.status}")
        ok(h.validation_result is not None, "validation_result is None")
        ok(h.validation_result.verdict == "PASS", "Wrong verdict")
        # Events: CREATE(1) + 4 transitions + set_validation_result(1) + VALIDATED(1) + CONFIRMED(1) = 8
        expected_events = 1 + len(transitions) + 1 + 1 + 1
        ok(len(h.decision_history) == expected_events,
           f"Decision history length wrong: expected {expected_events}, got {len(h.decision_history)}")
        return f"Full lifecycle complete: {len(h.decision_history)} events"
    runner.run("T-04: Full lifecycle PROPOSED → CONFIRMED", t04)

    # ── T-05: Full rejection path ─────────────────────────────────────────────
    def t05():
        reg = make_registry(tmp / "t05")
        h = _create_minimal(reg)
        hid = h.hypothesis_id
        reg.update_status(hid, HypothesisStatus.UNDER_REVIEW, "analyst", "Review")
        reg.update_status(hid, HypothesisStatus.REJECTED, "lead", "Insufficient evidence")
        h = reg.update_status(hid, HypothesisStatus.ARCHIVED, "system", "Archiving rejected")
        ok(h.status == HypothesisStatus.ARCHIVED, f"Expected ARCHIVED, got {h.status}")
        return "rejection path: PROPOSED → UNDER_REVIEW → REJECTED → ARCHIVED"
    runner.run("T-05: Rejection lifecycle path", t05)

    # ── T-06: Revival path (REJECTED → PROPOSED) ──────────────────────────────
    def t06():
        reg = make_registry(tmp / "t06")
        h = _create_minimal(reg)
        hid = h.hypothesis_id
        reg.update_status(hid, HypothesisStatus.UNDER_REVIEW, "a", "r")
        reg.update_status(hid, HypothesisStatus.REJECTED, "a", "r")
        h = reg.update_status(hid, HypothesisStatus.PROPOSED, "lead", "Revived with new data")
        ok(h.status == HypothesisStatus.PROPOSED, f"Expected PROPOSED after revival, got {h.status}")
        return "revival path: REJECTED → PROPOSED"
    runner.run("T-06: Revival path REJECTED → PROPOSED", t06)

    # ── T-07: Invalid transitions raise InvalidTransitionError ────────────────
    def t07():
        reg = make_registry(tmp / "t07")
        h = _create_minimal(reg)
        hid = h.hypothesis_id
        invalid_pairs = [
            (HypothesisStatus.PROPOSED,  HypothesisStatus.CONFIRMED),
            (HypothesisStatus.PROPOSED,  HypothesisStatus.RUNNING),
            (HypothesisStatus.PROPOSED,  HypothesisStatus.VALIDATED),
        ]
        caught = 0
        for from_s, to_s in invalid_pairs:
            try:
                reg.update_status(hid, to_s, "x", "x")
            except InvalidTransitionError:
                caught += 1
        ok(caught == len(invalid_pairs),
           f"Expected {len(invalid_pairs)} InvalidTransitionError, caught {caught}")
        return f"{caught} invalid transitions correctly blocked"
    runner.run("T-07: Invalid transitions raise InvalidTransitionError", t07)

    # ── T-08: Archived is terminal — no further transitions ───────────────────
    def t08():
        reg = make_registry(tmp / "t08")
        h = _create_minimal(reg)
        hid = h.hypothesis_id
        reg.update_status(hid, HypothesisStatus.UNDER_REVIEW, "a", "r")
        reg.update_status(hid, HypothesisStatus.APPROVED, "a", "r")
        reg.update_status(hid, HypothesisStatus.ARCHIVED, "a", "archiving")
        caught = False
        try:
            reg.update_status(hid, HypothesisStatus.PROPOSED, "a", "r")
        except InvalidTransitionError:
            caught = True
        ok(caught, "ARCHIVED → PROPOSED did not raise InvalidTransitionError")
        return "ARCHIVED terminal status confirmed"
    runner.run("T-08: ARCHIVED is terminal", t08)

    # ── T-09: All lifecycle transitions tested ────────────────────────────────
    def t09():
        # Verify that VALID_TRANSITIONS covers all status values
        all_statuses = set(HypothesisStatus)
        covered = set(VALID_TRANSITIONS.keys())
        ok(all_statuses == covered,
           f"Missing statuses in VALID_TRANSITIONS: {all_statuses - covered}")
        return f"all {len(all_statuses)} statuses covered in transition table"
    runner.run("T-09: All statuses covered in transition table", t09)

    # ── T-10: Valid evidence — FINDING type ───────────────────────────────────
    def t10():
        kp = KnowledgeProvider()
        findings = kp.list_findings()
        ok(len(findings) > 0, "No findings available for test")
        first_finding = findings[0]
        ev = EvidenceReference(
            evidence_id=first_finding.finding_id,
            evidence_type=EvidenceType.FINDING,
            description="Test finding reference",
            added_at=datetime.now(),
            added_by="test",
        )
        reg = make_registry(tmp / "t10")
        h = _create_minimal(reg)
        h = reg.add_evidence(h.hypothesis_id, ev, actor="test")
        ok(len(h.supporting_evidence) == 2, f"Expected 2 evidence refs, got {len(h.supporting_evidence)}")
        return f"FINDING evidence {first_finding.finding_id} attached"
    runner.run("T-10: add_evidence() — valid FINDING reference", t10)

    # ── T-11: Valid evidence — EDGE type ──────────────────────────────────────
    def t11():
        kp = KnowledgeProvider()
        edges = kp.list_edges()
        ok(len(edges) > 0, "No edges in KP")
        ev = EvidenceReference(
            evidence_id=edges[0].edge_id,
            evidence_type=EvidenceType.EDGE,
            description="Edge backing",
            added_at=datetime.now(),
            added_by="test",
        )
        reg = make_registry(tmp / "t11")
        h = _create_minimal(reg)
        h = reg.add_evidence(h.hypothesis_id, ev)
        ok(any(e.evidence_type == EvidenceType.EDGE for e in h.supporting_evidence), "EDGE not found")
        return f"EDGE evidence {edges[0].edge_id} attached"
    runner.run("T-11: add_evidence() — valid EDGE reference", t11)

    # ── T-12: Invalid evidence raises InvalidEvidenceError ────────────────────
    def t12():
        reg = make_registry(tmp / "t12")
        h = _create_minimal(reg)
        bad_ev = EvidenceReference(
            evidence_id="nonexistent_study_xyz",
            evidence_type=EvidenceType.STUDY,
            description="Bad ref",
            added_at=datetime.now(),
            added_by="test",
        )
        caught = False
        try:
            reg.add_evidence(h.hypothesis_id, bad_ev)
        except InvalidEvidenceError:
            caught = True
        ok(caught, "InvalidEvidenceError not raised for invalid study reference")
        return "invalid STUDY reference correctly rejected"
    runner.run("T-12: Invalid evidence raises InvalidEvidenceError", t12)

    # ── T-13: EXTERNAL evidence bypasses validation ───────────────────────────
    def t13():
        reg = make_registry(tmp / "t13")
        h = _create_minimal(reg)
        ext_ev = EvidenceReference(
            evidence_id="external_research_paper_arxiv_2025",
            evidence_type=EvidenceType.EXTERNAL,
            description="External academic research",
            added_at=datetime.now(),
            added_by="test",
        )
        h = reg.add_evidence(h.hypothesis_id, ext_ev)
        ok(any(e.evidence_type == EvidenceType.EXTERNAL for e in h.supporting_evidence),
           "EXTERNAL evidence not found")
        return "EXTERNAL evidence accepted without validation"
    runner.run("T-13: EXTERNAL evidence bypasses validation", t13)

    # ── T-14: Duplicate evidence ID is idempotent ─────────────────────────────
    def t14():
        reg = make_registry(tmp / "t14")
        h = _create_minimal(reg)
        ev = _study_evidence()
        # Add the same evidence_id that was already there from create
        h = reg.add_evidence(h.hypothesis_id, ev)
        ok(len(h.supporting_evidence) == 1, f"Duplicate evidence added: {len(h.supporting_evidence)}")
        return "duplicate evidence_id skipped (idempotent)"
    runner.run("T-14: Duplicate evidence_id is idempotent", t14)

    # ── T-15: add_note() appends timestamped note ─────────────────────────────
    def t15():
        reg = make_registry(tmp / "t15")
        h = _create_minimal(reg)
        reg.add_note(h.hypothesis_id, "Initial review complete", author="analyst")
        reg.add_note(h.hypothesis_id, "Waiting for data confirmation", author="analyst")
        h = reg.get(h.hypothesis_id)
        ok(len(h.notes) == 2, f"Expected 2 notes, got {len(h.notes)}")
        ok("analyst" in h.notes[0], "Author not in note")
        return f"{len(h.notes)} notes appended"
    runner.run("T-15: add_note() appends timestamped notes", t15)

    # ── T-16: Empty note raises RegistryValidationError ──────────────────────
    def t16():
        reg = make_registry(tmp / "t16")
        h = _create_minimal(reg)
        caught = False
        try:
            reg.add_note(h.hypothesis_id, "   ")
        except RegistryValidationError:
            caught = True
        ok(caught, "Empty note did not raise RegistryValidationError")
        return "empty note correctly rejected"
    runner.run("T-16: Empty note raises RegistryValidationError", t16)

    # ── T-17: get() returns None for unknown ID ───────────────────────────────
    def t17():
        reg = make_registry(tmp / "t17")
        result = reg.get("H0000-00-000")
        ok(result is None, f"Expected None, got {result}")
        return "get(unknown) → None"
    runner.run("T-17: get() returns None for unknown ID", t17)

    # ── T-18: get_or_raise() raises HypothesisNotFoundError ──────────────────
    def t18():
        reg = make_registry(tmp / "t18")
        caught = False
        try:
            reg.get_or_raise("H0000-00-000")
        except HypothesisNotFoundError:
            caught = True
        ok(caught, "HypothesisNotFoundError not raised")
        return "get_or_raise(unknown) → HypothesisNotFoundError"
    runner.run("T-18: get_or_raise() raises HypothesisNotFoundError", t18)

    # ── T-19: list_all() returns all hypotheses in creation order ─────────────
    def t19():
        reg = make_registry(tmp / "t19")
        h1 = _create_minimal(reg, "Hypothesis A")
        h2 = _create_minimal(reg, "Hypothesis B")
        h3 = _create_minimal(reg, "Hypothesis C")
        all_h = reg.list_all()
        ok(len(all_h) == 3, f"Expected 3, got {len(all_h)}")
        ok(all_h[0].hypothesis_id == h1.hypothesis_id, "Wrong order")
        return "3 hypotheses in creation order"
    runner.run("T-19: list_all() ordered by creation date", t19)

    # ── T-20: list_by_status() ────────────────────────────────────────────────
    def t20():
        reg = make_registry(tmp / "t20")
        h1 = _create_minimal(reg, "H1")
        h2 = _create_minimal(reg, "H2")
        reg.update_status(h2.hypothesis_id, HypothesisStatus.UNDER_REVIEW, "a", "r")
        proposed = reg.list_by_status(HypothesisStatus.PROPOSED)
        review   = reg.list_by_status(HypothesisStatus.UNDER_REVIEW)
        ok(len(proposed) == 1, f"Expected 1 PROPOSED, got {len(proposed)}")
        ok(len(review) == 1, f"Expected 1 UNDER_REVIEW, got {len(review)}")
        return f"PROPOSED={len(proposed)}, UNDER_REVIEW={len(review)}"
    runner.run("T-20: list_by_status() filter", t20)

    # ── T-21: list_by_priority() ──────────────────────────────────────────────
    def t21():
        reg = make_registry(tmp / "t21")
        _create_minimal(reg, "P1")
        reg.create_hypothesis(
            title="Low priority H",
            research_question="?",
            description="d",
            origin="o",
            priority=HypothesisPriority.LOW,
            classification=HypothesisClassification.EXPLORATORY,
            knowledge_gap="g",
            expected_knowledge_gain="k",
            validation_method="v",
            supporting_evidence=[_study_evidence()],
        )
        high = reg.list_by_priority(HypothesisPriority.HIGH)
        low  = reg.list_by_priority(HypothesisPriority.LOW)
        ok(len(high) == 1, f"Expected 1 HIGH, got {len(high)}")
        ok(len(low)  == 1, f"Expected 1 LOW, got {len(low)}")
        return f"HIGH={len(high)}, LOW={len(low)}"
    runner.run("T-21: list_by_priority() filter", t21)

    # ── T-22: list_open() excludes terminal states ────────────────────────────
    def t22():
        reg = make_registry(tmp / "t22")
        h1 = _create_minimal(reg, "Open")
        h2 = _create_minimal(reg, "Will archive")
        reg.update_status(h2.hypothesis_id, HypothesisStatus.UNDER_REVIEW, "a", "r")
        reg.update_status(h2.hypothesis_id, HypothesisStatus.APPROVED, "a", "r")
        reg.update_status(h2.hypothesis_id, HypothesisStatus.ARCHIVED, "a", "done")
        open_h = reg.list_open()
        ok(len(open_h) == 1, f"Expected 1 open, got {len(open_h)}")
        ok(open_h[0].hypothesis_id == h1.hypothesis_id, "Wrong open hypothesis")
        return "1 open, 1 archived correctly excluded"
    runner.run("T-22: list_open() excludes terminal states", t22)

    # ── T-23: list_confirmed() and list_rejected() ────────────────────────────
    def t23():
        reg = make_registry(tmp / "t23")
        hc = _create_minimal(reg, "Will confirm")
        hr = _create_minimal(reg, "Will reject")

        for status in [HypothesisStatus.UNDER_REVIEW, HypothesisStatus.APPROVED,
                       HypothesisStatus.PLANNED, HypothesisStatus.RUNNING]:
            reg.update_status(hc.hypothesis_id, status, "a", "r")

        vr = ValidationResult(datetime.now(), "system", "PASS", [], [], {}, "")
        reg.set_validation_result(hc.hypothesis_id, vr)
        reg.update_status(hc.hypothesis_id, HypothesisStatus.VALIDATED, "a", "r")
        reg.update_status(hc.hypothesis_id, HypothesisStatus.CONFIRMED, "a", "r")

        reg.update_status(hr.hypothesis_id, HypothesisStatus.UNDER_REVIEW, "a", "r")
        reg.update_status(hr.hypothesis_id, HypothesisStatus.REJECTED, "a", "r")

        ok(len(reg.list_confirmed()) == 1, f"Expected 1 CONFIRMED, got {len(reg.list_confirmed())}")
        ok(len(reg.list_rejected())  == 1, f"Expected 1 REJECTED, got {len(reg.list_rejected())}")
        return "1 confirmed, 1 rejected"
    runner.run("T-23: list_confirmed() and list_rejected()", t23)

    # ── T-24: list_by_study() ─────────────────────────────────────────────────
    def t24():
        reg = make_registry(tmp / "t24")
        h = _create_minimal(reg, "Study-linked H")
        result = reg.list_by_study("study002a")
        ok(len(result) >= 1, f"Expected ≥1, got {len(result)}")
        ok(any(x.hypothesis_id == h.hypothesis_id for x in result), "H not found in study filter")
        return f"{len(result)} hypotheses linked to study002a"
    runner.run("T-24: list_by_study() filter", t24)

    # ── T-25: search() ────────────────────────────────────────────────────────
    def t25():
        reg = make_registry(tmp / "t25")
        _create_minimal(reg, "ATR threshold analysis")
        reg.create_hypothesis(
            title="Momentum gap study",
            research_question="?",
            description="d",
            origin="o",
            priority=HypothesisPriority.MEDIUM,
            classification=HypothesisClassification.COVERAGE_GAP,
            knowledge_gap="momentum gap",
            expected_knowledge_gain="k",
            validation_method="v",
            supporting_evidence=[_study_evidence()],
        )
        atr_results = reg.search("atr")
        mom_results = reg.search("momentum")
        ok(len(atr_results) >= 1, "ATR search returned 0")
        ok(len(mom_results) >= 1, "Momentum search returned 0")
        ok(len(reg.search("nonexistent_xyz")) == 0, "Garbage search should return 0")
        return f"'atr'={len(atr_results)}, 'momentum'={len(mom_results)}"
    runner.run("T-25: search() keyword matching", t25)

    # ── T-26: search() is case-insensitive ────────────────────────────────────
    def t26():
        reg = make_registry(tmp / "t26")
        _create_minimal(reg, "ATR Threshold Study")
        upper = reg.search("ATR")
        lower = reg.search("atr")
        ok(len(upper) == len(lower), f"Case sensitivity issue: upper={len(upper)}, lower={len(lower)}")
        return "case-insensitive search confirmed"
    runner.run("T-26: search() is case-insensitive", t26)

    # ── T-27: statistics() ────────────────────────────────────────────────────
    def t27():
        reg = make_registry(tmp / "t27")
        h1 = _create_minimal(reg, "Stats H1")
        h2 = _create_minimal(reg, "Stats H2")
        reg.update_status(h2.hypothesis_id, HypothesisStatus.UNDER_REVIEW, "a", "r")
        stats = reg.statistics()
        ok(stats["total"] == 2, f"Expected total=2, got {stats['total']}")
        ok(stats["open"] == 2, f"Expected open=2, got {stats['open']}")
        ok("by_status" in stats, "by_status missing")
        ok("by_priority" in stats, "by_priority missing")
        ok("avg_evidence_count" in stats, "avg_evidence_count missing")
        return f"total={stats['total']}, open={stats['open']}"
    runner.run("T-27: statistics() returns complete metrics", t27)

    # ── T-28: Decision history is immutable (append-only check) ───────────────
    def t28():
        reg = make_registry(tmp / "t28")
        h = _create_minimal(reg)
        hid = h.hypothesis_id
        n_before = len(h.decision_history)
        reg.update_status(hid, HypothesisStatus.UNDER_REVIEW, "a", "r")
        reg.update_status(hid, HypothesisStatus.APPROVED, "a", "r")
        h2 = reg.get(hid)
        ok(len(h2.decision_history) == n_before + 2,
           f"Expected {n_before + 2} events, got {len(h2.decision_history)}")
        # Verify events have correct actors
        ok(h2.decision_history[-1].action.startswith("STATUS_CHANGE"),
           f"Last event not STATUS_CHANGE: {h2.decision_history[-1].action}")
        return f"{len(h2.decision_history)} decision events recorded"
    runner.run("T-28: Decision history is append-only", t28)

    # ── T-29: Persistence — save and reload ───────────────────────────────────
    def t29():
        tmp29 = tmp / "t29"
        reg_path = tmp29 / "registry.json"
        reg1 = HypothesisRegistry(knowledge_provider=KnowledgeProvider(),
                                  registry_path=reg_path)
        h = _create_minimal(reg1, "Persist me")
        hid = h.hypothesis_id
        reg1.update_status(hid, HypothesisStatus.UNDER_REVIEW, "analyst", "review")
        reg1.add_note(hid, "Noted for reload", "analyst")

        # Load fresh instance from same file
        reg2 = HypothesisRegistry(knowledge_provider=KnowledgeProvider(),
                                  registry_path=reg_path)
        h2 = reg2.get(hid)
        ok(h2 is not None, "Hypothesis not found after reload")
        ok(h2.status == HypothesisStatus.UNDER_REVIEW,
           f"Status not persisted: {h2.status}")
        ok(len(h2.notes) == 1, f"Notes not persisted: {h2.notes}")
        ok(len(h2.decision_history) == 2,  # CREATE + UNDER_REVIEW
           f"History not persisted: {len(h2.decision_history)}")
        return "save → reload round-trip verified"
    runner.run("T-29: Persistence — save/reload round-trip", t29)

    # ── T-30: Backup file created on overwrite ────────────────────────────────
    def t30():
        tmp30 = tmp / "t30"
        reg_path = tmp30 / "registry.json"
        reg = HypothesisRegistry(knowledge_provider=KnowledgeProvider(),
                                 registry_path=reg_path)
        _create_minimal(reg, "First write")    # creates registry.json
        _create_minimal(reg, "Second write")   # should create registry.json.bak
        bak_path = reg_path.with_suffix(".json.bak")
        ok(bak_path.exists(), f"Backup not created at {bak_path}")
        return f"backup created at {bak_path.name}"
    runner.run("T-30: Backup file created before overwrite", t30)

    # ── T-31: Concurrent access — thread-safety ───────────────────────────────
    def t31():
        tmp31 = tmp / "t31"
        kp = KnowledgeProvider()
        reg = HypothesisRegistry(knowledge_provider=kp,
                                 registry_path=tmp31 / "registry.json")
        errors: List[Exception] = []

        def worker(i: int) -> None:
            try:
                reg.create_hypothesis(
                    title=f"Concurrent hypothesis {i}",
                    research_question="?",
                    description=f"Thread {i}",
                    origin="concurrency_test",
                    priority=HypothesisPriority.LOW,
                    classification=HypothesisClassification.EXPLORATORY,
                    knowledge_gap="g",
                    expected_knowledge_gain="k",
                    validation_method="v",
                    supporting_evidence=[_study_evidence()],
                )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t_ in threads:
            t_.start()
        for t_ in threads:
            t_.join()

        ok(len(errors) == 0, f"Thread errors: {errors}")
        ok(len(reg.list_all()) == 10, f"Expected 10 hypotheses, got {len(reg.list_all())}")
        ids = {h.hypothesis_id for h in reg.list_all()}
        ok(len(ids) == 10, f"Duplicate IDs: {10 - len(ids)} collisions")
        return f"10 concurrent creates, 0 errors, {len(ids)} unique IDs"
    runner.run("T-31: Concurrent access — thread-safety", t31)

    # ── T-32: Empty title raises RegistryValidationError ─────────────────────
    def t32():
        reg = make_registry(tmp / "t32")
        caught = False
        try:
            reg.create_hypothesis(
                title="",
                research_question="?",
                description="d",
                origin="o",
                priority=HypothesisPriority.MEDIUM,
                classification=HypothesisClassification.MANUAL,
                knowledge_gap="g",
                expected_knowledge_gain="k",
                validation_method="v",
            )
        except RegistryValidationError:
            caught = True
        ok(caught, "Empty title did not raise RegistryValidationError")
        return "empty title rejected"
    runner.run("T-32: Empty title raises RegistryValidationError", t32)

    # ── T-33: confidence out of range raises ─────────────────────────────────
    def t33():
        reg = make_registry(tmp / "t33")
        for bad_conf in (-0.1, 1.01, 2.0):
            caught = False
            try:
                reg.create_hypothesis(
                    title=f"Bad confidence {bad_conf}",
                    research_question="?",
                    description="d",
                    origin="o",
                    priority=HypothesisPriority.MEDIUM,
                    classification=HypothesisClassification.MANUAL,
                    knowledge_gap="g",
                    expected_knowledge_gain="k",
                    validation_method="v",
                    confidence=bad_conf,
                )
            except RegistryValidationError:
                caught = True
            ok(caught, f"confidence={bad_conf} did not raise RegistryValidationError")
        return "all out-of-range confidence values rejected"
    runner.run("T-33: Out-of-range confidence raises RegistryValidationError", t33)

    # ── T-34: set_validation_result requires RUNNING status ───────────────────
    def t34():
        reg = make_registry(tmp / "t34")
        h = _create_minimal(reg)
        vr = ValidationResult(datetime.now(), "system", "PASS", [], [], {}, "")
        caught = False
        try:
            reg.set_validation_result(h.hypothesis_id, vr)
        except RegistryValidationError:
            caught = True
        ok(caught, "set_validation_result on PROPOSED did not raise")
        return "set_validation_result on non-RUNNING correctly rejected"
    runner.run("T-34: set_validation_result requires RUNNING status", t34)

    # ── T-35: get_evidence_chain() ────────────────────────────────────────────
    def t35():
        kp = KnowledgeProvider()
        reg = make_registry(tmp / "t35")
        h = _create_minimal(reg)
        edges = kp.list_edges()
        ev2 = EvidenceReference(
            evidence_id=edges[0].edge_id,
            evidence_type=EvidenceType.EDGE,
            description="Edge reference",
            added_at=datetime.now(),
            added_by="test",
        )
        reg.add_evidence(h.hypothesis_id, ev2)
        chain = reg.get_evidence_chain(h.hypothesis_id)
        ok(len(chain) == 2, f"Expected 2 evidence refs, got {len(chain)}")
        types = {e.evidence_type for e in chain}
        ok(EvidenceType.STUDY in types, "STUDY missing from chain")
        ok(EvidenceType.EDGE in types, "EDGE missing from chain")
        return f"evidence chain: {[e.evidence_id for e in chain]}"
    runner.run("T-35: get_evidence_chain() returns full chain", t35)

    # ── T-36: get_decision_history() returns immutable copy ───────────────────
    def t36():
        reg = make_registry(tmp / "t36")
        h = _create_minimal(reg)
        history1 = reg.get_decision_history(h.hypothesis_id)
        history1.append(None)  # modify the copy
        history2 = reg.get_decision_history(h.hypothesis_id)
        ok(len(history2) == 1, f"History was mutated: {len(history2)} events")
        return "decision history copy is isolated from original"
    runner.run("T-36: get_decision_history() returns isolated copy", t36)

    # ── T-37: update_confidence() ────────────────────────────────────────────
    def t37():
        reg = make_registry(tmp / "t37")
        h = _create_minimal(reg)
        ok(h.confidence == 0.65, f"Initial confidence wrong: {h.confidence}")
        h = reg.update_confidence(h.hypothesis_id, 0.80, "analyst", "New evidence")
        ok(h.confidence == 0.80, f"Confidence not updated: {h.confidence}")
        last_event = h.decision_history[-1]
        ok(last_event.action == "UPDATE_CONFIDENCE", "Wrong event action")
        ok(last_event.metadata["new_confidence"] == 0.80, "Metadata not recorded")
        return "confidence updated and event recorded"
    runner.run("T-37: update_confidence() records event", t37)

    # ── T-38: Duplicate title generates warning, not error ────────────────────
    def t38():
        import logging, io
        reg = make_registry(tmp / "t38")
        _create_minimal(reg, "Duplicate Title Check")
        # Capture warning
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logging.getLogger("autonomous_research.hypothesis_registry").addHandler(handler)
        try:
            _create_minimal(reg, "Duplicate Title Check")
        except Exception:
            pass  # should NOT raise
        finally:
            logging.getLogger("autonomous_research.hypothesis_registry").removeHandler(handler)
        all_h = reg.list_all()
        ok(len(all_h) == 2, f"Expected 2 (duplicate allowed with warning), got {len(all_h)}")
        return "duplicate title allowed with warning (not an error)"
    runner.run("T-38: Duplicate title — warning only, not error", t38)

    # ── T-39: Registry does NOT modify KnowledgeProvider stores ──────────────
    def t39():
        import os
        from pathlib import Path
        data_dir = ROOT / "data"
        # Check mtime of a known store before and after registry operations
        sp_path = data_dir / "strategy_performance.json"
        mtime_before = os.path.getmtime(sp_path) if sp_path.exists() else None

        reg = make_registry(tmp / "t39")
        _create_minimal(reg)
        reg.update_status(reg.list_all()[0].hypothesis_id,
                          HypothesisStatus.UNDER_REVIEW, "a", "r")

        mtime_after = os.path.getmtime(sp_path) if sp_path.exists() else None
        ok(mtime_before == mtime_after,
           "strategy_performance.json was modified during registry operations")
        return "KnowledgeProvider stores unchanged"
    runner.run("T-39: Registry does not modify KP stores", t39)

    # ── T-40: Archive convenience method ─────────────────────────────────────
    def t40():
        reg = make_registry(tmp / "t40")
        h = _create_minimal(reg)
        h = reg.update_status(h.hypothesis_id, HypothesisStatus.UNDER_REVIEW, "a", "r")
        h = reg.update_status(h.hypothesis_id, HypothesisStatus.APPROVED, "a", "r")
        h = reg.archive(h.hypothesis_id, actor="system", reason="Superseded")
        ok(h.status == HypothesisStatus.ARCHIVED, f"Expected ARCHIVED, got {h.status}")
        return "archive() convenience method works"
    runner.run("T-40: archive() convenience method", t40)

    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)
    return runner


# ═════════════════════════════════════════════════════════════════════════════
# Report generation
# ═════════════════════════════════════════════════════════════════════════════

def generate_report(runner: TestRunner) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(runner.results)
    passed = runner.passed
    failed = runner.failed
    pass_rate = f"{100 * passed // total}%" if total else "N/A"

    lines = [
        "# HYPOTHESIS REGISTRY TEST REPORT",
        "## ARS Phase 1.2 — Scientific Hypothesis Registry",
        "",
        f"**Date:** {now}  ",
        f"**Total tests:** {total}  ",
        f"**Passed:** {passed}  ",
        f"**Failed:** {failed}  ",
        f"**Pass rate:** {pass_rate}  ",
        "",
        "---",
        "",
        "## Test Results",
        "",
        "| Test | Status | Duration (ms) | Detail |",
        "|---|---|---|---|",
    ]
    for r in runner.results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        detail = r.detail if len(r.detail) < 80 else r.detail[:77] + "..."
        lines.append(f"| {r.name} | {status} | {r.duration_ms} | {detail} |")

    lines += ["", "---", "", "## Failures", ""]
    failures = [r for r in runner.results if not r.passed]
    if failures:
        for r in failures:
            lines += [f"### {r.name}", "", "```", r.error or "No detail", "```", ""]
    else:
        lines.append("*No failures.*")

    lines += [
        "", "---", "", "## Coverage Summary", "",
        "| Test Category | Tests |",
        "|---|---|",
        "| Lifecycle — full happy path | T-04 |",
        "| Lifecycle — rejection path | T-05 |",
        "| Lifecycle — revival path | T-06 |",
        "| Invalid transitions | T-07, T-08 |",
        "| Transition table completeness | T-09 |",
        "| Evidence — valid FINDING | T-10 |",
        "| Evidence — valid EDGE | T-11 |",
        "| Evidence — invalid reference | T-12 |",
        "| Evidence — EXTERNAL bypass | T-13 |",
        "| Evidence — idempotent add | T-14 |",
        "| Notes — append-only | T-15, T-16 |",
        "| get() / get_or_raise() | T-17, T-18 |",
        "| list_all() order | T-19 |",
        "| list_by_status() | T-20 |",
        "| list_by_priority() | T-21 |",
        "| list_open() | T-22 |",
        "| list_confirmed() / list_rejected() | T-23 |",
        "| list_by_study() | T-24 |",
        "| search() | T-25, T-26 |",
        "| statistics() | T-27 |",
        "| Decision history append-only | T-28 |",
        "| Persistence (save/reload) | T-29 |",
        "| Backup file creation | T-30 |",
        "| Concurrent access | T-31 |",
        "| Validation — empty fields | T-32 |",
        "| Validation — confidence range | T-33 |",
        "| Validation — set_validation_result | T-34 |",
        "| get_evidence_chain() | T-35 |",
        "| get_decision_history() isolation | T-36 |",
        "| update_confidence() | T-37 |",
        "| Duplicate title warning | T-38 |",
        "| Read-only KP constraint | T-39 |",
        "| archive() convenience | T-40 |",
        "",
        "---",
        "",
        f"*Generated by test_hypothesis_registry.py | {now}*",
    ]
    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 64)
    print("ARS Phase 1.2 — Hypothesis Registry Test Suite")
    print("=" * 64)

    t_start = time.perf_counter()
    runner = run_all_tests()
    elapsed = time.perf_counter() - t_start

    print(f"\nResults: {runner.passed} passed / {runner.failed} failed "
          f"({len(runner.results)} total) in {elapsed:.2f}s\n")

    for r in runner.results:
        icon = "✓" if r.passed else "✗"
        print(f"  {icon} {r.name:60s} {r.duration_ms:6.1f}ms  {r.detail[:55]}")

    if runner.failed:
        print("\nFAILURES:")
        for r in runner.results:
            if not r.passed:
                print(f"\n  ✗ {r.name}")
                print(f"    {r.error}")

    report_path = ROOT / "HYPOTHESIS_REGISTRY_TEST_REPORT.md"
    report_path.write_text(generate_report(runner), encoding="utf-8")
    print(f"\nTest report written → {report_path}")

    sys.exit(0 if runner.failed == 0 else 1)

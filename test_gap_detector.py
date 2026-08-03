"""
test_gap_detector.py — ARS Phase 2A test suite.

Covers:
    - Instantiation (with/without optional dependencies)
    - detect() return structure and caching
    - All 10 gap category rules fire correctly
    - All 4 severity levels are reachable
    - Evidence traceability (every gap has supporting_evidence)
    - All 8 query API methods
    - Statistics consistency (by_category + by_severity sums)
    - Deterministic gap_ids (same data → same id)
    - Reproducibility: detect() twice gives same results
    - Config customisation
    - rule_id and rule_parameters documented on every gap
    - Read-only verification (KP, Registry, Synthesizer unchanged)
    - Thread safety (concurrent detect() calls)
    - Pre-detect() empty state
    - to_dict() round-trip

Run:
    python test_gap_detector.py
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
from unittest.mock import MagicMock

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
    GapDetectionReport,
    GapStatistics,
    HypothesisClassification,
    HypothesisPriority,
    FindingClassification,
)
from autonomous_research.synthesis_models import (
    ContradictionRecord,
    ContradictionType,
    SynthesisReport,
    SynthesisStatistics,
    SynthesizedFinding,
    SynthesisClassification,
    EvidenceChain,
    KnowledgeRelationship,
    KnowledgeConsensus,
)
from autonomous_research.gap_models import GapDetectorError, DetectionError


# ═════════════════════════════════════════════════════════════════════════════
# Minimal test framework (mirrors Phase 1.2 / 1.3 pattern)
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

_KP: Optional[KnowledgeProvider]  = None
_SYN: Optional[CrossStudySynthesizer] = None


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


def make_temp_registry(tmp: Path) -> HypothesisRegistry:
    return HypothesisRegistry(
        knowledge_provider=get_kp(),
        registry_path=tmp / "test_registry.json",
    )


def make_detector(
    tmp: Path,
    config: Optional[GapDetectorConfig] = None,
) -> GapDetector:
    reg = make_temp_registry(tmp)
    return GapDetector(
        knowledge_provider=get_kp(),
        hypothesis_registry=reg,
        synthesizer=get_syn(),
        config=config,
    )


def _empty_syn_stats() -> SynthesisStatistics:
    return SynthesisStatistics(
        total_findings_processed=0, total_synthesized_findings=0,
        total_relationships=0, total_contradictions=0,
        by_classification={}, by_finding_type={},
        avg_synthesis_confidence=0.0, avg_evidence_count=0.0,
        studies_processed=0, edges_correlated=0, hypotheses_correlated=0,
        certifications_correlated=0, metrics_correlated=0,
        synthesis_duration_ms=0.0, synthesized_at=datetime.now(),
    )


def make_mock_syn_with_contradiction(severity: float = 0.8) -> CrossStudySynthesizer:
    """Returns a mock synthesizer whose synthesize() has one ContradictionRecord."""
    contra = ContradictionRecord(
        contradiction_id="CONTRA-MOCK-001",
        contradiction_type=ContradictionType.CONFLICTING_VALUES,
        finding_a_id="F-MOCK-001",
        study_a_id="study-mock-a",
        finding_b_id="F-MOCK-002",
        study_b_id="study-mock-b",
        metric="win_rate",
        value_a=0.70,
        value_b=0.25,
        description="Mock contradiction for testing",
        severity=severity,
    )
    report = SynthesisReport(
        report_id="SYN-MOCK",
        synthesized_at=datetime.now(),
        synthesized_findings=[],
        relationships=[],
        contradictions=[contra],
        consensus_blocks=[],
        statistics=_empty_syn_stats(),
        warnings=[],
    )
    mock_syn = MagicMock(spec=CrossStudySynthesizer)
    mock_syn.synthesize.return_value = report
    return mock_syn


def make_mock_syn_empty() -> CrossStudySynthesizer:
    """Returns a mock synthesizer with an empty SynthesisReport."""
    report = SynthesisReport(
        report_id="SYN-EMPTY",
        synthesized_at=datetime.now(),
        synthesized_findings=[],
        relationships=[],
        contradictions=[],
        consensus_blocks=[],
        statistics=_empty_syn_stats(),
        warnings=[],
    )
    mock_syn = MagicMock(spec=CrossStudySynthesizer)
    mock_syn.synthesize.return_value = report
    return mock_syn


# ═════════════════════════════════════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════════════════════════════════════

def run_all_tests() -> TestRunner:
    runner = TestRunner()
    tmp = Path(tempfile.mkdtemp(prefix="ars_gd_test_"))

    # ── T-01: Instantiation with all three providers ───────────────────────
    def t01():
        kp  = KnowledgeProvider()
        reg = HypothesisRegistry(kp, registry_path=tmp / "t01.json")
        syn = CrossStudySynthesizer(kp)
        gd  = GapDetector(kp, reg, syn)
        ok(gd is not None, "GapDetector is None")
        return "instantiated with all three providers"
    runner.run("T-01: Instantiation with KP + Registry + Synthesizer", t01)

    # ── T-02: Instantiation without optional HypothesisRegistry ───────────
    def t02():
        gd = GapDetector(knowledge_provider=get_kp(), synthesizer=get_syn())
        ok(gd is not None, "GapDetector without registry is None")
        report = gd.detect()
        ok(isinstance(report, GapDetectionReport), "Expected GapDetectionReport")
        return "no KNOWLEDGE_GAP rules fired (no registry)"
    runner.run("T-02: Instantiation without HypothesisRegistry", t02)

    # ── T-03: Instantiation without optional CrossStudySynthesizer ────────
    def t03():
        gd = GapDetector(knowledge_provider=get_kp())
        ok(gd is not None, "GapDetector without synthesizer is None")
        report = gd.detect()
        ok(isinstance(report, GapDetectionReport), "Expected GapDetectionReport")
        syn_rules = {"R-GD-02", "R-GD-07", "R-GD-08"}
        fired = set(report.statistics.rules_fired.keys())
        ok(not syn_rules.intersection(fired),
           f"Synthesis rules fired without synthesizer: {syn_rules & fired}")
        return "synthesis-dependent rules correctly skipped"
    runner.run("T-03: Instantiation without CrossStudySynthesizer", t03)

    # ── T-04: detect() returns GapDetectionReport ─────────────────────────
    def t04():
        gd     = make_detector(tmp / "t04")
        report = gd.detect()
        ok(isinstance(report, GapDetectionReport), f"Expected GapDetectionReport, got {type(report)}")
        ok(report.report_id.startswith("GDR-"), f"Bad report_id prefix: {report.report_id}")
        ok(isinstance(report.detected_at, datetime), "detected_at not a datetime")
        ok(isinstance(report.gaps, list), "gaps not a list")
        ok(isinstance(report.statistics, GapStatistics), "statistics not GapStatistics")
        ok(isinstance(report.warnings, list), "warnings not a list")
        return f"report_id={report.report_id}, {len(report.gaps)} gaps"
    runner.run("T-04: detect() returns well-formed GapDetectionReport", t04)

    # ── T-05: GapDetectionReport has all required fields ──────────────────
    def t05():
        gd     = make_detector(tmp / "t05")
        report = gd.detect()
        ok(report.report_id, "report_id is empty")
        ok(report.detected_at is not None, "detected_at is None")
        ok(report.statistics.total_gaps >= 0, "total_gaps < 0")
        ok(report.statistics.detection_duration_ms >= 0, "duration < 0")
        return "all report fields present"
    runner.run("T-05: GapDetectionReport fields all present and typed", t05)

    # ── T-06: detect() is cached (force=False) ────────────────────────────
    def t06():
        gd = make_detector(tmp / "t06")
        r1 = gd.detect()
        r2 = gd.detect()
        ok(r1.report_id == r2.report_id, "Cached report has different report_id")
        return f"same report_id={r1.report_id}"
    runner.run("T-06: detect() is cached — same report_id on second call", t06)

    # ── T-07: detect(force=True) refreshes ────────────────────────────────
    def t07():
        gd = make_detector(tmp / "t07")
        r1 = gd.detect()
        r2 = gd.detect(force=True)
        ok(r1.report_id != r2.report_id, "force=True did not produce a new report_id")
        return f"new report_id after force: {r2.report_id}"
    runner.run("T-07: detect(force=True) refreshes cache", t07)

    # ── T-08: DATA_GAP fires when threshold is above study observations ───
    def t08():
        cfg = GapDetectorConfig(min_study_observations=999_999)
        gd  = make_detector(tmp / "t08", config=cfg)
        rpt = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.DATA_GAP]
        ok(len(gaps) > 0, "DATA_GAP did not fire with threshold=999,999")
        for g in gaps:
            ok(g.rule_id == "R-GD-01", f"Wrong rule_id on DATA_GAP: {g.rule_id}")
            ok(len(g.supporting_evidence) > 0, "DATA_GAP has empty supporting_evidence")
            ok(len(g.related_studies) > 0, "DATA_GAP has empty related_studies")
        return f"{len(gaps)} DATA_GAP(s) detected"
    runner.run("T-08: DATA_GAP fires when min_study_observations exceeded", t08)

    # ── T-09: EVIDENCE_GAP fires for under-corroborated findings ─────────
    def t09():
        cfg = GapDetectorConfig(min_corroborating_studies=999)
        gd  = make_detector(tmp / "t09", config=cfg)
        rpt = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.EVIDENCE_GAP]
        ok(len(gaps) > 0, "EVIDENCE_GAP did not fire with min_corroborating_studies=999")
        for g in gaps:
            ok(g.rule_id == "R-GD-02", f"Wrong rule_id: {g.rule_id}")
            ok(len(g.supporting_evidence) > 0, "EVIDENCE_GAP has empty supporting_evidence")
        return f"{len(gaps)} EVIDENCE_GAP(s)"
    runner.run("T-09: EVIDENCE_GAP fires for under-corroborated synthesized findings", t09)

    # ── T-10: REGIME_GAP fires when known regime has no findings ─────────
    def t10():
        # Use an impossible regime name so it never appears in findings
        cfg = GapDetectorConfig(known_regimes=("__NEVER_EXISTS__",))
        gd  = make_detector(tmp / "t10", config=cfg)
        rpt = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.REGIME_GAP]
        ok(len(gaps) > 0, "REGIME_GAP did not fire for unknown regime")
        ok(gaps[0].rule_id == "R-GD-03", f"Wrong rule_id: {gaps[0].rule_id}")
        ok(any("regime:__NEVER_EXISTS__" in e for e in gaps[0].supporting_evidence),
           "REGIME_GAP supporting_evidence missing regime identifier")
        return f"{len(gaps)} REGIME_GAP(s)"
    runner.run("T-10: REGIME_GAP fires when known regime has no findings", t10)

    # ── T-11: SECTOR_GAP fires with high threshold ────────────────────────
    def t11():
        cfg = GapDetectorConfig(min_sector_observations=999_999)
        gd  = make_detector(tmp / "t11", config=cfg)
        rpt = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.SECTOR_GAP]
        ok(len(gaps) > 0,
           "SECTOR_GAP did not fire with min_sector_observations=999,999")
        for g in gaps:
            ok(g.rule_id == "R-GD-04", f"Wrong rule_id: {g.rule_id}")
            ok(len(g.supporting_evidence) > 0, "SECTOR_GAP missing supporting_evidence")
        return f"{len(gaps)} SECTOR_GAP(s)"
    runner.run("T-11: SECTOR_GAP fires with elevated threshold", t11)

    # ── T-12: TEMPORAL_GAP fires — studies are older than threshold ───────
    def t12():
        cfg = GapDetectorConfig(max_study_age_days=-1)  # negative → always fires
        gd  = make_detector(tmp / "t12", config=cfg)
        rpt = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.TEMPORAL_GAP]
        ok(len(gaps) == 1, f"Expected 1 TEMPORAL_GAP, got {len(gaps)}")
        ok(gaps[0].rule_id == "R-GD-05", f"Wrong rule_id: {gaps[0].rule_id}")
        ok(len(gaps[0].related_studies) > 0, "TEMPORAL_GAP has no related_studies")
        return f"TEMPORAL_GAP: {gaps[0].title}"
    runner.run("T-12: TEMPORAL_GAP fires for stale research studies", t12)

    # ── T-13: VALIDATION_GAP fires for CANDIDATE edges without metrics ────
    def t13():
        cfg = GapDetectorConfig(max_edge_unvalidated_days=0)
        gd  = make_detector(tmp / "t13", config=cfg)
        rpt = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.VALIDATION_GAP]
        # Rule only fires if CANDIDATE edges without oos/wf metrics exist
        for g in gaps:
            ok(g.rule_id == "R-GD-06", f"Wrong rule_id: {g.rule_id}")
            ok(len(g.supporting_evidence) > 0, "VALIDATION_GAP missing evidence")
            ok(g.severity in (GapSeverity.HIGH, GapSeverity.MEDIUM),
               f"Unexpected VALIDATION_GAP severity: {g.severity}")
        return f"{len(gaps)} VALIDATION_GAP(s) with max_edge_unvalidated_days=0"
    runner.run("T-13: VALIDATION_GAP structure when CANDIDATE edges exist", t13)

    # ── T-14: CONTRADICTION_GAP fires for each ContradictionRecord ────────
    def t14():
        mock_syn = make_mock_syn_with_contradiction(severity=0.8)
        reg      = make_temp_registry(tmp / "t14")
        gd       = GapDetector(get_kp(), reg, mock_syn)
        rpt      = gd.detect()
        gaps     = [g for g in rpt.gaps if g.category == GapCategory.CONTRADICTION_GAP]
        ok(len(gaps) == 1, f"Expected 1 CONTRADICTION_GAP, got {len(gaps)}")
        ok(gaps[0].rule_id == "R-GD-07", f"Wrong rule_id: {gaps[0].rule_id}")
        ok("CONTRA-MOCK-001" in gaps[0].supporting_evidence,
           "CONTRADICTION_GAP missing contradiction_id in supporting_evidence")
        ok("F-MOCK-001" in gaps[0].related_findings, "finding_a not in related_findings")
        ok("F-MOCK-002" in gaps[0].related_findings, "finding_b not in related_findings")
        return f"CONTRADICTION_GAP fired: {gaps[0].title}"
    runner.run("T-14: CONTRADICTION_GAP fires once per ContradictionRecord", t14)

    # ── T-15: CONFIDENCE_GAP fires when synthesis confidence is low ───────
    def t15():
        cfg = GapDetectorConfig(
            min_synthesis_confidence=0.9999,
            confidence_critical_threshold=0.001,
            confidence_high_threshold=0.01,
        )
        gd  = make_detector(tmp / "t15", config=cfg)
        rpt = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.CONFIDENCE_GAP]
        ok(len(gaps) > 0,
           "CONFIDENCE_GAP did not fire with min_synthesis_confidence=0.9999")
        for g in gaps:
            ok(g.rule_id == "R-GD-08", f"Wrong rule_id: {g.rule_id}")
            ok(len(g.supporting_evidence) > 0, "CONFIDENCE_GAP missing evidence")
        return f"{len(gaps)} CONFIDENCE_GAP(s)"
    runner.run("T-15: CONFIDENCE_GAP fires when min_synthesis_confidence elevated", t15)

    # ── T-16: KNOWLEDGE_GAP fires for stalled hypotheses ─────────────────
    def t16():
        kp  = get_kp()
        reg = HypothesisRegistry(kp, registry_path=tmp / "t16_reg.json")
        reg.create_hypothesis(
            title="Stalled test hypothesis for gap detection",
            research_question="Does strategy X underperform in trending markets?",
            description="Created for KNOWLEDGE_GAP test",
            classification=HypothesisClassification.PERFORMANCE_GAP,
            priority=HypothesisPriority.HIGH,
            origin="test",
            knowledge_gap="No research on strategy X in trending markets",
            expected_knowledge_gain="Identify underperformance root cause",
            validation_method="walk_forward_test",
        )
        cfg = GapDetectorConfig(max_hypothesis_open_days=-1)
        gd  = GapDetector(kp, reg, get_syn(), config=cfg)
        rpt = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.KNOWLEDGE_GAP]
        ok(len(gaps) >= 1, f"KNOWLEDGE_GAP did not fire; open hypotheses: {reg.list_open()}")
        ok(gaps[0].rule_id == "R-GD-09", f"Wrong rule_id: {gaps[0].rule_id}")
        ok(len(gaps[0].related_hypotheses) > 0, "KNOWLEDGE_GAP missing related_hypotheses")
        return f"KNOWLEDGE_GAP: {gaps[0].title}"
    runner.run("T-16: KNOWLEDGE_GAP fires for stalled open hypotheses", t16)

    # ── T-17: COVERAGE_GAP fires for missing FindingClassification ────────
    def t17():
        gd   = make_detector(tmp / "t17")
        rpt  = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.COVERAGE_GAP]
        covered = {f.classification for f in get_kp().list_findings()}
        missing = [
            cls for cls in FindingClassification
            if cls != FindingClassification.UNKNOWN and cls not in covered
        ]
        ok(len(gaps) == len(missing),
           f"Expected {len(missing)} COVERAGE_GAP(s), got {len(gaps)}")
        for g in gaps:
            ok(g.rule_id == "R-GD-10", f"Wrong rule_id: {g.rule_id}")
            ok(g.severity == GapSeverity.HIGH, f"COVERAGE_GAP should be HIGH, got {g.severity}")
        return f"{len(gaps)} COVERAGE_GAP(s) for missing classifications: {[c.value for c in missing]}"
    runner.run("T-17: COVERAGE_GAP fires for each missing FindingClassification", t17)

    # ── T-18: CRITICAL severity is reachable ─────────────────────────────
    def t18():
        # Negative threshold → age(0) > 3×(-1)=-3 → CRITICAL for any study
        cfg  = GapDetectorConfig(max_study_age_days=-1)
        gd   = make_detector(tmp / "t18", config=cfg)
        rpt  = gd.detect()
        crits = [g for g in rpt.gaps if g.severity == GapSeverity.CRITICAL]
        ok(len(crits) > 0, "No CRITICAL severity gap found with max_study_age_days=1")
        ok(all(g.estimated_knowledge_gain == 0.90 for g in crits),
           "CRITICAL gap has wrong estimated_knowledge_gain (expected 0.90)")
        return f"{len(crits)} CRITICAL gap(s)"
    runner.run("T-18: CRITICAL severity reachable via TEMPORAL_GAP", t18)

    # ── T-19: HIGH severity is reachable ──────────────────────────────────
    def t19():
        gd  = make_detector(tmp / "t19")
        rpt = gd.detect()
        high = [g for g in rpt.gaps if g.severity == GapSeverity.HIGH]
        ok(len(high) > 0, "No HIGH severity gap found")
        ok(all(g.estimated_knowledge_gain == 0.70 for g in high),
           "HIGH gap has wrong estimated_knowledge_gain (expected 0.70)")
        return f"{len(high)} HIGH gap(s)"
    runner.run("T-19: HIGH severity reachable (COVERAGE_GAP / REGIME_GAP)", t19)

    # ── T-20: MEDIUM severity is reachable ────────────────────────────────
    def t20():
        cfg = GapDetectorConfig(
            min_corroborating_studies=999,  # forces EVIDENCE_GAP at MEDIUM
        )
        gd   = make_detector(tmp / "t20", config=cfg)
        rpt  = gd.detect()
        meds = [g for g in rpt.gaps if g.severity == GapSeverity.MEDIUM]
        ok(len(meds) > 0, "No MEDIUM severity gap found")
        ok(all(g.estimated_knowledge_gain == 0.50 for g in meds),
           "MEDIUM gap has wrong estimated_knowledge_gain (expected 0.50)")
        return f"{len(meds)} MEDIUM gap(s)"
    runner.run("T-20: MEDIUM severity reachable (EVIDENCE_GAP)", t20)

    # ── T-21: LOW severity is reachable ───────────────────────────────────
    def t21():
        mock_syn = make_mock_syn_with_contradiction(severity=0.1)  # 0.1 < 0.40 → LOW
        reg      = make_temp_registry(tmp / "t21")
        gd       = GapDetector(get_kp(), reg, mock_syn)
        rpt      = gd.detect()
        lows     = [g for g in rpt.gaps if g.severity == GapSeverity.LOW]
        ok(len(lows) > 0, "No LOW severity gap found (contradiction severity=0.1)")
        ok(all(g.estimated_knowledge_gain == 0.20 for g in lows),
           "LOW gap has wrong estimated_knowledge_gain (expected 0.20)")
        return f"{len(lows)} LOW gap(s)"
    runner.run("T-21: LOW severity reachable via CONTRADICTION_GAP with low severity", t21)

    # ── T-22: Every gap has non-empty supporting_evidence ─────────────────
    def t22():
        gd  = make_detector(tmp / "t22")
        rpt = gd.detect()
        for g in rpt.gaps:
            ok(len(g.supporting_evidence) > 0,
               f"Gap {g.gap_id} ({g.category.value}) has empty supporting_evidence")
        return f"all {len(rpt.gaps)} gaps have supporting_evidence"
    runner.run("T-22: All gaps have non-empty supporting_evidence (traceability)", t22)

    # ── T-23: DATA_GAP supporting_evidence includes study_id ─────────────
    def t23():
        cfg  = GapDetectorConfig(min_study_observations=999_999)
        gd   = make_detector(tmp / "t23", config=cfg)
        rpt  = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.DATA_GAP]
        ok(len(gaps) > 0, "No DATA_GAP to test")
        for g in gaps:
            study_ids = get_kp().list_studies()
            study_in_evidence = any(
                s.study_id in g.supporting_evidence for s in study_ids
            )
            ok(study_in_evidence, f"DATA_GAP {g.gap_id}: study_id not in supporting_evidence")
            ok(g.related_studies, f"DATA_GAP {g.gap_id}: related_studies is empty")
        return "DATA_GAP supporting_evidence contains study_id"
    runner.run("T-23: DATA_GAP supporting_evidence includes study_id", t23)

    # ── T-24: EVIDENCE_GAP supporting_evidence includes synthesis_id ──────
    def t24():
        cfg  = GapDetectorConfig(min_corroborating_studies=999)
        gd   = make_detector(tmp / "t24", config=cfg)
        rpt  = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.EVIDENCE_GAP]
        ok(len(gaps) > 0, "No EVIDENCE_GAP to test")
        syn_report = get_syn().synthesize()
        syn_ids = {sf.synthesis_id for sf in syn_report.synthesized_findings}
        for g in gaps:
            found = any(e in syn_ids for e in g.supporting_evidence)
            ok(found, f"EVIDENCE_GAP {g.gap_id}: synthesis_id not in supporting_evidence")
        return "EVIDENCE_GAP supporting_evidence contains synthesis_id"
    runner.run("T-24: EVIDENCE_GAP supporting_evidence contains synthesis_id", t24)

    # ── T-25: REGIME_GAP supporting_evidence describes the regime ─────────
    def t25():
        cfg  = GapDetectorConfig(known_regimes=("__TEST_REGIME_X__",))
        gd   = make_detector(tmp / "t25", config=cfg)
        rpt  = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.REGIME_GAP]
        ok(len(gaps) > 0, "No REGIME_GAP to test")
        for g in gaps:
            ok(any("regime:" in e for e in g.supporting_evidence),
               f"REGIME_GAP {g.gap_id}: 'regime:' descriptor not in supporting_evidence")
        return "REGIME_GAP supporting_evidence contains 'regime:' descriptor"
    runner.run("T-25: REGIME_GAP supporting_evidence describes the regime", t25)

    # ── T-26: KNOWLEDGE_GAP supporting_evidence includes hypothesis_id ────
    def t26():
        kp  = get_kp()
        reg = HypothesisRegistry(kp, registry_path=tmp / "t26_reg.json")
        hyp = reg.create_hypothesis(
            title="Hypothesis for evidence traceability test",
            research_question="Is coverage complete across all FindingClassifications?",
            description="Test",
            classification=HypothesisClassification.COVERAGE_GAP,
            priority=HypothesisPriority.MEDIUM,
            origin="test",
            knowledge_gap="Missing classification coverage",
            expected_knowledge_gain="Confirm or identify gaps in classification coverage",
            validation_method="coverage_analysis",
        )
        cfg = GapDetectorConfig(max_hypothesis_open_days=-1)
        gd  = GapDetector(kp, reg, get_syn(), config=cfg)
        rpt = gd.detect()
        gaps = [g for g in rpt.gaps if g.category == GapCategory.KNOWLEDGE_GAP]
        ok(len(gaps) >= 1, "No KNOWLEDGE_GAP produced")
        found = any(
            hyp.hypothesis_id in g.supporting_evidence for g in gaps
        )
        ok(found, f"hypothesis_id {hyp.hypothesis_id} not in any KNOWLEDGE_GAP.supporting_evidence")
        return "KNOWLEDGE_GAP supporting_evidence contains hypothesis_id"
    runner.run("T-26: KNOWLEDGE_GAP supporting_evidence includes hypothesis_id", t26)

    # ── T-27: list_all() returns all detected gaps ────────────────────────
    def t27():
        gd  = make_detector(tmp / "t27")
        rpt = gd.detect()
        all_gaps = gd.list_all()
        ok(len(all_gaps) == len(rpt.gaps),
           f"list_all() count {len(all_gaps)} != report count {len(rpt.gaps)}")
        ok(all_gaps is not rpt.gaps, "list_all() returned the same list object (not a copy)")
        return f"list_all() = {len(all_gaps)} gaps"
    runner.run("T-27: list_all() returns all gaps from last detection", t27)

    # ── T-28: list_open() returns only OPEN gaps ─────────────────────────
    def t28():
        gd   = make_detector(tmp / "t28")
        gd.detect()
        open_gaps = gd.list_open()
        ok(all(g.status == GapStatus.OPEN for g in open_gaps),
           "list_open() returned non-OPEN gaps")
        all_gaps  = gd.list_all()
        open_count = sum(1 for g in all_gaps if g.status == GapStatus.OPEN)
        ok(len(open_gaps) == open_count,
           f"list_open() count {len(open_gaps)} != actual open count {open_count}")
        return f"list_open() = {len(open_gaps)} OPEN gaps"
    runner.run("T-28: list_open() returns only OPEN-status gaps", t28)

    # ── T-29: list_by_category() returns correct subset ──────────────────
    def t29():
        gd  = make_detector(tmp / "t29")
        gd.detect()
        for cat in GapCategory:
            subset = gd.list_by_category(cat)
            ok(all(g.category == cat for g in subset),
               f"list_by_category({cat.value}) returned wrong-category gaps")
        total = sum(len(gd.list_by_category(cat)) for cat in GapCategory)
        ok(total == len(gd.list_all()),
           f"sum of category subsets {total} != total {len(gd.list_all())}")
        return "all category subsets correct"
    runner.run("T-29: list_by_category() returns correct subset per category", t29)

    # ── T-30: list_by_severity() returns correct subset ──────────────────
    def t30():
        gd  = make_detector(tmp / "t30")
        gd.detect()
        for sev in GapSeverity:
            subset = gd.list_by_severity(sev)
            ok(all(g.severity == sev for g in subset),
               f"list_by_severity({sev.value}) returned wrong-severity gaps")
        total = sum(len(gd.list_by_severity(sev)) for sev in GapSeverity)
        ok(total == len(gd.list_all()),
           f"sum of severity subsets {total} != total {len(gd.list_all())}")
        return "all severity subsets correct"
    runner.run("T-30: list_by_severity() returns correct subset per severity", t30)

    # ── T-31: list_by_study() returns gaps referencing that study_id ──────
    def t31():
        gd    = make_detector(tmp / "t31")
        gd.detect()
        kp    = get_kp()
        studies = kp.list_studies()
        ok(len(studies) > 0, "No studies in KP for test")
        sid   = studies[0].study_id
        gaps  = gd.list_by_study(sid)
        ok(all(sid in g.related_studies for g in gaps),
           f"list_by_study('{sid}') returned gap without that study in related_studies")
        all_with_study = [g for g in gd.list_all() if sid in g.related_studies]
        ok(len(gaps) == len(all_with_study),
           f"list_by_study count mismatch: {len(gaps)} vs {len(all_with_study)}")
        return f"list_by_study('{sid}') = {len(gaps)} gaps"
    runner.run("T-31: list_by_study() returns correct gaps for a study_id", t31)

    # ── T-32: list_by_hypothesis() returns correct subset ─────────────────
    def t32():
        kp  = get_kp()
        reg = HypothesisRegistry(kp, registry_path=tmp / "t32_reg.json")
        hyp = reg.create_hypothesis(
            title="Hypothesis for list_by_hypothesis test",
            research_question="Does stale knowledge affect prediction accuracy?",
            description="Test",
            classification=HypothesisClassification.TEMPORAL_GAP,
            priority=HypothesisPriority.HIGH,
            origin="test",
            knowledge_gap="Temporal staleness not quantified",
            expected_knowledge_gain="Establish staleness threshold",
            validation_method="temporal_comparison",
        )
        cfg = GapDetectorConfig(max_hypothesis_open_days=-1)
        gd  = GapDetector(kp, reg, get_syn(), config=cfg)
        gd.detect()
        gaps = gd.list_by_hypothesis(hyp.hypothesis_id)
        ok(len(gaps) >= 1,
           f"No gap references hypothesis {hyp.hypothesis_id}")
        ok(all(hyp.hypothesis_id in g.related_hypotheses for g in gaps),
           "list_by_hypothesis returned gap without hypothesis_id in related_hypotheses")
        return f"list_by_hypothesis = {len(gaps)} gap(s)"
    runner.run("T-32: list_by_hypothesis() returns gaps referencing hypothesis_id", t32)

    # ── T-33: statistics() structure is correct ───────────────────────────
    def t33():
        gd   = make_detector(tmp / "t33")
        gd.detect()
        stats = gd.statistics()
        ok(isinstance(stats, GapStatistics), "statistics() did not return GapStatistics")
        ok(stats.total_gaps >= 0, "total_gaps negative")
        ok(stats.open_gaps >= 0, "open_gaps negative")
        ok(stats.critical_count >= 0, "critical_count negative")
        ok(stats.high_count >= 0, "high_count negative")
        ok(stats.detection_duration_ms >= 0, "duration negative")
        ok(isinstance(stats.by_category, dict), "by_category not dict")
        ok(isinstance(stats.by_severity, dict), "by_severity not dict")
        ok(isinstance(stats.rules_fired, dict), "rules_fired not dict")
        return f"total={stats.total_gaps}, open={stats.open_gaps}"
    runner.run("T-33: statistics() returns well-formed GapStatistics", t33)

    # ── T-34: by_category sums to total_gaps ─────────────────────────────
    def t34():
        gd   = make_detector(tmp / "t34")
        gd.detect()
        stats = gd.statistics()
        cat_total = sum(stats.by_category.values())
        ok(cat_total == stats.total_gaps,
           f"by_category sum {cat_total} != total_gaps {stats.total_gaps}")
        return f"by_category sums correctly to {stats.total_gaps}"
    runner.run("T-34: statistics().by_category values sum to total_gaps", t34)

    # ── T-35: by_severity sums to total_gaps ─────────────────────────────
    def t35():
        gd   = make_detector(tmp / "t35")
        gd.detect()
        stats = gd.statistics()
        sev_total = sum(stats.by_severity.values())
        ok(sev_total == stats.total_gaps,
           f"by_severity sum {sev_total} != total_gaps {stats.total_gaps}")
        return f"by_severity sums correctly to {stats.total_gaps}"
    runner.run("T-35: statistics().by_severity values sum to total_gaps", t35)

    # ── T-36: critical_count and high_count match by_severity ─────────────
    def t36():
        gd   = make_detector(tmp / "t36")
        gd.detect()
        stats = gd.statistics()
        ok(stats.critical_count == stats.by_severity.get("CRITICAL", 0),
           "critical_count != by_severity['CRITICAL']")
        ok(stats.high_count == stats.by_severity.get("HIGH", 0),
           "high_count != by_severity['HIGH']")
        return (f"critical_count={stats.critical_count}, "
                f"high_count={stats.high_count}")
    runner.run("T-36: statistics() critical_count and high_count match by_severity", t36)

    # ── T-37: gap_ids are deterministic ──────────────────────────────────
    def t37():
        gd  = make_detector(tmp / "t37")
        r1  = gd.detect()
        r2  = gd.detect(force=True)
        ids1 = sorted(g.gap_id for g in r1.gaps)
        ids2 = sorted(g.gap_id for g in r2.gaps)
        ok(ids1 == ids2, f"gap_ids changed between runs:\n  run1: {ids1}\n  run2: {ids2}")
        return f"{len(ids1)} deterministic gap_ids confirmed"
    runner.run("T-37: gap_ids are deterministic (same data → same IDs)", t37)

    # ── T-38: detect(force=True) produces a fresh report_id ──────────────
    def t38():
        gd  = make_detector(tmp / "t38")
        r1  = gd.detect()
        r2  = gd.detect(force=True)
        r3  = gd.detect(force=True)
        ok(r1.report_id != r2.report_id, "force=True did not change report_id")
        ok(r2.report_id != r3.report_id, "Two force=True calls produced same report_id")
        return "each force=True call produces a unique report_id"
    runner.run("T-38: detect(force=True) always produces a fresh report_id", t38)

    # ── T-39: custom config changes detection results ────────────────────
    def t39():
        gd_default = make_detector(tmp / "t39a")
        gd_strict  = make_detector(
            tmp / "t39b",
            config=GapDetectorConfig(min_study_observations=999_999),
        )
        r_default = gd_default.detect()
        r_strict  = gd_strict.detect()
        default_data = sum(1 for g in r_default.gaps if g.category == GapCategory.DATA_GAP)
        strict_data  = sum(1 for g in r_strict.gaps if g.category == GapCategory.DATA_GAP)
        ok(strict_data >= default_data,
           "Stricter threshold produced fewer DATA_GAPs (impossible)")
        return (f"default DATA_GAPs={default_data}, "
                f"strict DATA_GAPs={strict_data}")
    runner.run("T-39: custom config changes detection results", t39)

    # ── T-40: rule_parameters document the active config values ──────────
    def t40():
        cfg = GapDetectorConfig(min_study_observations=12345)
        gd  = make_detector(tmp / "t40", config=cfg)
        rpt = gd.detect()
        data_gaps = [g for g in rpt.gaps if g.category == GapCategory.DATA_GAP]
        ok(len(data_gaps) > 0, "No DATA_GAP to inspect rule_parameters")
        for g in data_gaps:
            ok("min_study_observations" in g.rule_parameters,
               f"rule_parameters missing 'min_study_observations' on {g.gap_id}")
            ok(g.rule_parameters["min_study_observations"] == 12345,
               f"rule_parameters has wrong value: {g.rule_parameters}")
        return "rule_parameters correctly documented"
    runner.run("T-40: rule_parameters on every gap documents active config values", t40)

    # ── T-41: gap.rule_id identifies the firing rule ─────────────────────
    def t41():
        gd  = make_detector(tmp / "t41")
        rpt = gd.detect()
        valid_rule_ids = {
            "R-GD-01", "R-GD-02", "R-GD-03", "R-GD-04", "R-GD-05",
            "R-GD-06", "R-GD-07", "R-GD-08", "R-GD-09", "R-GD-10",
        }
        for g in rpt.gaps:
            ok(g.rule_id in valid_rule_ids,
               f"Unknown rule_id '{g.rule_id}' on gap {g.gap_id}")
        fired = set(rpt.statistics.rules_fired.keys())
        ok(fired.issubset(valid_rule_ids),
           f"Unknown rule_ids in statistics: {fired - valid_rule_ids}")
        return f"rule_ids fired: {sorted(fired)}"
    runner.run("T-41: gap.rule_id is always a known R-GD-XX identifier", t41)

    # ── T-42: KP stores unchanged after detect() ─────────────────────────
    def t42():
        kp = KnowledgeProvider()
        n_studies_before  = len(kp.list_studies())
        n_edges_before    = len(kp.list_edges())
        n_findings_before = len(kp.list_findings())
        gd = GapDetector(kp)
        gd.detect(force=True)
        ok(len(kp.list_studies())  == n_studies_before,
           "detect() changed study count in KP")
        ok(len(kp.list_edges())    == n_edges_before,
           "detect() changed edge count in KP")
        ok(len(kp.list_findings()) == n_findings_before,
           "detect() changed finding count in KP")
        return "KP stores unchanged"
    runner.run("T-42: KP stores are read-only — detect() does not modify them", t42)

    # ── T-43: HypothesisRegistry unchanged after detect() ────────────────
    def t43():
        kp      = get_kp()
        reg     = HypothesisRegistry(kp, registry_path=tmp / "t43_reg.json")
        # Create one hypothesis
        reg.create_hypothesis(
            title="T-43 baseline hypothesis",
            research_question="Baseline test — does detect() mutate the registry?",
            description="Read-only test",
            classification=HypothesisClassification.MANUAL,
            priority=HypothesisPriority.LOW,
            origin="test",
            knowledge_gap="None — this is a structural test",
            expected_knowledge_gain="Confirm read-only behaviour",
            validation_method="registry_count_check",
        )
        count_before = reg.statistics()["total"]
        gd = GapDetector(kp, reg)
        gd.detect()
        count_after = reg.statistics()["total"]
        ok(count_before == count_after,
           f"detect() changed registry count from {count_before} to {count_after}")
        return f"registry hypothesis count unchanged at {count_before}"
    runner.run("T-43: HypothesisRegistry unchanged after detect()", t43)

    # ── T-44: Synthesizer cached report unchanged after detect() ──────────
    def t44():
        syn    = CrossStudySynthesizer(knowledge_provider=get_kp())
        r_before = syn.synthesize()
        gd       = GapDetector(get_kp(), synthesizer=syn)
        gd.detect()
        r_after  = syn.synthesize()
        ok(r_before.report_id == r_after.report_id,
           "detect() caused synthesizer to regenerate its cached report")
        return f"synthesizer report_id stable: {r_before.report_id}"
    runner.run("T-44: CrossStudySynthesizer cache unchanged after detect(force=False)", t44)

    # ── T-45: Concurrent detect() calls are thread-safe ──────────────────
    def t45():
        gd      = make_detector(tmp / "t45")
        errors  = []
        results = []

        def worker():
            try:
                r = gd.detect(force=True)
                results.append(r.report_id)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        ok(len(errors) == 0, f"Thread errors: {errors}")
        ok(len(results) == 8, f"Expected 8 results, got {len(results)}")
        return f"8 concurrent detect() calls completed without errors"
    runner.run("T-45: Concurrent detect() calls are thread-safe", t45)

    # ── T-46: list_all() before detect() returns empty list ──────────────
    def t46():
        gd = GapDetector(knowledge_provider=get_kp())
        all_before = gd.list_all()
        ok(all_before == [], f"Expected [], got {all_before}")
        open_before = gd.list_open()
        ok(open_before == [], f"list_open() before detect() not empty")
        return "list_all() and list_open() return [] before detect()"
    runner.run("T-46: list_all() and list_open() return [] before first detect()", t46)

    # ── T-47: statistics() before detect() returns zero stats ────────────
    def t47():
        gd    = GapDetector(knowledge_provider=get_kp())
        stats = gd.statistics()
        ok(stats.total_gaps == 0, f"total_gaps before detect() = {stats.total_gaps}")
        ok(stats.open_gaps  == 0, f"open_gaps before detect() = {stats.open_gaps}")
        ok(stats.by_category == {}, "by_category not empty before detect()")
        ok(stats.by_severity == {}, "by_severity not empty before detect()")
        ok(stats.rules_fired == {}, "rules_fired not empty before detect()")
        return "statistics() returns zero stats before first detect()"
    runner.run("T-47: statistics() returns zero stats before first detect()", t47)

    # ── T-48: GapDetectionReport.to_dict() round-trips correctly ─────────
    def t48():
        gd  = make_detector(tmp / "t48")
        rpt = gd.detect()
        d   = rpt.to_dict()
        ok(isinstance(d, dict), "to_dict() did not return a dict")
        ok("report_id" in d, "to_dict() missing 'report_id'")
        ok("detected_at" in d, "to_dict() missing 'detected_at'")
        ok("gaps" in d, "to_dict() missing 'gaps'")
        ok("statistics" in d, "to_dict() missing 'statistics'")
        ok("warnings" in d, "to_dict() missing 'warnings'")
        ok(isinstance(d["gaps"], list), "to_dict()['gaps'] not a list")
        return f"to_dict() produced {len(d['gaps'])} gap dicts"
    runner.run("T-48: GapDetectionReport.to_dict() produces valid dict", t48)

    # ── T-49: KnowledgeGap.to_dict() has all required fields ─────────────
    def t49():
        gd   = make_detector(tmp / "t49")
        rpt  = gd.detect()
        ok(len(rpt.gaps) > 0, "No gaps to test to_dict()")
        required = {
            "gap_id", "category", "title", "description", "severity",
            "severity_rationale", "confidence", "status", "supporting_evidence",
            "related_studies", "related_hypotheses", "related_findings",
            "recommended_action", "estimated_knowledge_gain",
            "rule_id", "rule_parameters", "created_at",
        }
        for g in rpt.gaps:
            d   = g.to_dict()
            missing = required - d.keys()
            ok(not missing, f"Gap {g.gap_id} to_dict() missing fields: {missing}")
        return f"all {len(rpt.gaps)} gap to_dict() dicts have required fields"
    runner.run("T-49: KnowledgeGap.to_dict() contains all required fields", t49)

    # ── T-50: Backward compatibility — Phase 1 exports still work ────────
    def t50():
        from autonomous_research import (
            KnowledgeProvider as KP,
            HypothesisRegistry as HR,
            CrossStudySynthesizer as CSS,
            GapDetector as GD,
        )
        ok(KP is KnowledgeProvider, "KnowledgeProvider import broken")
        ok(HR is HypothesisRegistry, "HypothesisRegistry import broken")
        ok(CSS is CrossStudySynthesizer, "CrossStudySynthesizer import broken")
        ok(GD is GapDetector, "GapDetector import broken")
        # Confirm all exception classes still importable
        from autonomous_research import (
            RegistryError, GapDetectorError, DetectionError,
        )
        return "all Phase 1 and Phase 2A exports intact"
    runner.run("T-50: Backward compatibility — all Phase 1 + 2A exports intact", t50)

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
    print("ARS Phase 2A — GapDetector Test Suite")
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

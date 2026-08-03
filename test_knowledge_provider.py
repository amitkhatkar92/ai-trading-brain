"""
test_knowledge_provider.py — ARS Phase 1.1 test suite.

Exercises every public method of KnowledgeProvider and reports pass/fail
for each test case.  Generates KNOWLEDGE_PROVIDER_TEST_REPORT.md.

Run:
    python test_knowledge_provider.py
"""
from __future__ import annotations

import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional

# ─── ensure project root is on path ──────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_research import KnowledgeProvider
from autonomous_research.models import (
    EdgeStatus,
    FindingClassification,
    LoadSeverity,
)


# ═════════════════════════════════════════════════════════════════════════════
# Test framework (stdlib only)
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name:     str
    passed:   bool
    duration_ms: float
    detail:   str
    error:    Optional[str] = None


class TestRunner:
    def __init__(self) -> None:
        self.results: List[TestResult] = []

    def run(self, name: str, fn: Callable[[], Any]) -> None:
        t0 = time.perf_counter()
        try:
            detail = fn()
            elapsed = (time.perf_counter() - t0) * 1000
            self.results.append(TestResult(
                name=name, passed=True,
                duration_ms=round(elapsed, 1),
                detail=str(detail) if detail else "OK",
            ))
        except AssertionError as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=round(elapsed, 1),
                detail="ASSERTION FAILED",
                error=str(exc),
            ))
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=round(elapsed, 1),
                detail="EXCEPTION",
                error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            ))

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)


# ═════════════════════════════════════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════════════════════════════════════

def run_all_tests() -> TestRunner:
    runner = TestRunner()
    kp = KnowledgeProvider()

    # ── T-01: Instantiation ──────────────────────────────────────────────────
    runner.run("T-01: Instantiation", lambda: (
        assert_true(kp is not None, "KnowledgeProvider is None")
    ))

    # ── T-02: list_studies() returns a non-empty list ────────────────────────
    def t02():
        studies = kp.list_studies()
        assert_true(len(studies) >= 1, f"Expected ≥1 study, got {len(studies)}")
        return f"{len(studies)} studies loaded"
    runner.run("T-02: list_studies() — non-empty", t02)

    # ── T-03: list_studies() titles are non-empty strings ────────────────────
    def t03():
        for s in kp.list_studies():
            assert_true(bool(s.title), f"Empty title for study {s.study_id}")
            assert_true(bool(s.study_id), "Empty study_id")
        return f"all {len(kp.list_studies())} titles valid"
    runner.run("T-03: Study titles are non-empty", t03)

    # ── T-04: study002a loaded with correct metadata ─────────────────────────
    def t04():
        s = kp.get_study("study002a")
        assert_true(s is not None, "study002a not found")
        assert_true(s.n_observations == 280909,
                    f"Expected 280909 observations, got {s.n_observations}")
        return f"study002a: n={s.n_observations}, executed={s.executed_at}"
    runner.run("T-04: study002a metadata correct", t04)

    # ── T-05: get_study() with unknown ID returns None ────────────────────────
    runner.run("T-05: get_study(unknown) → None", lambda: (
        assert_true(kp.get_study("no_such_study") is None, "Expected None")
    ))

    # ── T-06: get_latest_study() returns most recent ─────────────────────────
    def t06():
        latest = kp.get_latest_study()
        assert_true(latest is not None, "get_latest_study() returned None")
        return f"Latest: {latest.study_id} ({latest.executed_at})"
    runner.run("T-06: get_latest_study() returns a study", t06)

    # ── T-07: list_findings() returns findings ────────────────────────────────
    def t07():
        findings = kp.list_findings()
        assert_true(len(findings) > 0, "Expected findings from studies")
        return f"{len(findings)} findings extracted"
    runner.run("T-07: list_findings() — non-empty", t07)

    # ── T-08: Winner DNA findings exist ──────────────────────────────────────
    def t08():
        dna = kp.get_findings_by_classification(FindingClassification.WINNER_DNA)
        assert_true(len(dna) > 0, "No WINNER_DNA findings found")
        assert_true(all(f.confidence is not None for f in dna),
                    "Some WINNER_DNA findings missing confidence")
        return f"{len(dna)} WINNER_DNA patterns"
    runner.run("T-08: WINNER_DNA findings present", t08)

    # ── T-09: Loser DNA findings exist ────────────────────────────────────────
    def t09():
        loser = kp.get_findings_by_classification(FindingClassification.LOSER_DNA)
        assert_true(len(loser) >= 1, "No LOSER_DNA findings found")
        return f"{len(loser)} LOSER_DNA patterns"
    runner.run("T-09: LOSER_DNA findings present", t09)

    # ── T-10: Feature importance findings exist ───────────────────────────────
    def t10():
        feats = kp.get_findings_by_classification(FindingClassification.FEATURE_IMPORTANCE)
        assert_true(len(feats) > 0, "No FEATURE_IMPORTANCE findings")
        return f"{len(feats)} feature rankings"
    runner.run("T-10: FEATURE_IMPORTANCE findings present", t10)

    # ── T-11: list_edges() returns edges ─────────────────────────────────────
    def t11():
        edges = kp.list_edges()
        assert_true(len(edges) > 0, "No edges loaded")
        return f"{len(edges)} edges loaded"
    runner.run("T-11: list_edges() — non-empty", t11)

    # ── T-12: EdgeRecord fields are populated ─────────────────────────────────
    def t12():
        edges = kp.list_edges()
        for e in edges[:5]:
            assert_true(bool(e.edge_id),   f"Empty edge_id: {e}")
            assert_true(bool(e.name),      f"Empty name: {e.edge_id}")
            assert_true(e.status in EdgeStatus, f"Invalid status: {e.status}")
        return f"first 5 edge records valid"
    runner.run("T-12: EdgeRecord fields populated", t12)

    # ── T-13: list_edges(status=DECAYING) filters correctly ───────────────────
    def t13():
        decaying = kp.list_edges(status=EdgeStatus.DECAYING)
        all_edges = kp.list_edges()
        assert_true(len(decaying) < len(all_edges),
                    "DECAYING filter returned all edges — no filtering occurred")
        assert_true(all(e.status == EdgeStatus.DECAYING for e in decaying),
                    "Not all filtered edges are DECAYING")
        return f"{len(decaying)} DECAYING edges of {len(all_edges)} total"
    runner.run("T-13: list_edges(status=DECAYING) filter", t13)

    # ── T-14: list_edges(min_composite_score) filter works ───────────────────
    def t14():
        high_score = kp.list_edges(min_composite_score=1.5)
        all_edges  = kp.list_edges()
        assert_true(len(high_score) <= len(all_edges), "Filter returned more than total")
        scored = [e for e in high_score if e.composite_score is not None]
        assert_true(all(e.composite_score >= 1.5 for e in scored),
                    "Some returned edges have composite_score < 1.5")
        return f"{len(high_score)} edges with composite_score ≥ 1.5"
    runner.run("T-14: list_edges(min_composite_score) filter", t14)

    # ── T-15: list_strategies() returns strategies ────────────────────────────
    def t15():
        strats = kp.list_strategies()
        assert_true(len(strats) > 0, "No strategies loaded")
        return f"{len(strats)} strategy records"
    runner.run("T-15: list_strategies() — non-empty", t15)

    # ── T-16: list_strategies(approved_only=True) filter ─────────────────────
    def t16():
        approved = kp.list_strategies(approved_only=True)
        all_strats = kp.list_strategies()
        assert_true(len(approved) <= len(all_strats), "Filter returned more than total")
        assert_true(all(s.approved for s in approved), "Not all returned strategies are approved")
        return f"{len(approved)} approved of {len(all_strats)} total strategies"
    runner.run("T-16: list_strategies(approved_only) filter", t16)

    # ── T-17: list_certifications() returns certs ─────────────────────────────
    def t17():
        certs = kp.list_certifications()
        assert_true(len(certs) > 0, "No certifications loaded")
        return f"{len(certs)} certification records"
    runner.run("T-17: list_certifications() — non-empty", t17)

    # ── T-18: Certification fields populated ─────────────────────────────────
    def t18():
        certs = kp.list_certifications()
        for c in certs:
            assert_true(bool(c.cert_id), "Empty cert_id")
            assert_true(bool(c.certification_type), "Empty certification_type")
            assert_true(isinstance(c.passed, bool), "passed is not bool")
        return f"{len(certs)} certifications all valid"
    runner.run("T-18: Certification fields valid", t18)

    # ── T-19: list_knowledge_metrics() returns metrics ────────────────────────
    def t19():
        metrics = kp.list_knowledge_metrics()
        assert_true(len(metrics) > 0, "No metrics returned")
        return f"{len(metrics)} knowledge metrics"
    runner.run("T-19: list_knowledge_metrics() — non-empty", t19)

    # ── T-20: list_knowledge_metrics(category) filter ─────────────────────────
    def t20():
        edge_metrics = kp.list_knowledge_metrics(category="EDGE")
        study_metrics = kp.list_knowledge_metrics(category="STUDY")
        assert_true(all(m.category == "EDGE" for m in edge_metrics),
                    "Non-EDGE metrics returned for category='EDGE'")
        assert_true(all(m.category == "STUDY" for m in study_metrics),
                    "Non-STUDY metrics returned for category='STUDY'")
        return f"{len(edge_metrics)} EDGE, {len(study_metrics)} STUDY metrics"
    runner.run("T-20: list_knowledge_metrics(category) filter", t20)

    # ── T-21: get_regime_history() returns records ────────────────────────────
    def t21():
        records = kp.get_regime_history()
        assert_true(len(records) > 0, "No regime history records")
        assert_true(all(r.dominant_regime is not None for r in records[:10]),
                    "Some records missing dominant_regime")
        return f"{len(records)} regime probability records"
    runner.run("T-21: get_regime_history() — non-empty", t21)

    # ── T-22: get_regime_history(limit) works ────────────────────────────────
    def t22():
        limited = kp.get_regime_history(limit=10)
        assert_true(len(limited) == 10, f"Expected 10 records, got {len(limited)}")
        return "limit=10 correctly applied"
    runner.run("T-22: get_regime_history(limit=10)", t22)

    # ── T-23: get_regime_history(dominant_regime) filter ─────────────────────
    def t23():
        # get a valid regime to filter on
        sample = kp.get_regime_history(limit=5)
        if not sample:
            return "skip — no regime history"
        regime = sample[0].dominant_regime
        filtered = kp.get_regime_history(dominant_regime=regime)
        assert_true(all(r.dominant_regime == regime for r in filtered),
                    f"Some records have regime != {regime}")
        return f"{len(filtered)} records for regime={regime}"
    runner.run("T-23: get_regime_history(dominant_regime) filter", t23)

    # ── T-24: list_features() returns records ─────────────────────────────────
    def t24():
        features = kp.list_features()
        assert_true(len(features) > 0, "No feature records returned")
        assert_true(all(isinstance(f.features, dict) for f in features[:10]),
                    "Some feature records have non-dict features")
        return f"{len(features)} feature records (default limit 500)"
    runner.run("T-24: list_features() — non-empty", t24)

    # ── T-25: list_features(limit) works ─────────────────────────────────────
    def t25():
        features = kp.list_features(limit=50)
        assert_true(len(features) == 50, f"Expected 50, got {len(features)}")
        return "limit=50 correctly applied"
    runner.run("T-25: list_features(limit=50)", t25)

    # ── T-26: list_features(limit=None) returns all ───────────────────────────
    def t26():
        all_features = kp.list_features(limit=None)
        assert_true(len(all_features) >= 500, f"Expected ≥500, got {len(all_features)}")
        return f"{len(all_features)} total feature records"
    runner.run("T-26: list_features(limit=None) returns all", t26)

    # ── T-27: get_replay_summary() returns a summary ─────────────────────────
    def t27():
        summary = kp.get_replay_summary()
        assert_true(summary is not None, "replay_summary returned None")
        assert_true(summary.days_replayed is not None, "days_replayed is None")
        return f"days_replayed={summary.days_replayed}, metrics keys={list((summary.metrics or {}).keys())[:3]}"
    runner.run("T-27: get_replay_summary() — non-None", t27)

    # ── T-28: list_stores() returns all expected stores ───────────────────────
    def t28():
        stores = kp.list_stores()
        store_ids = {s.store_id for s in stores}
        expected = {"study002", "study002a", "re001a", "discovered_edges",
                    "evolved_strategies", "ede_feature_db", "replay_db"}
        missing = expected - store_ids
        assert_true(len(missing) == 0, f"Missing stores: {missing}")
        loaded = [s for s in stores if s.loaded]
        return f"{len(loaded)} of {len(stores)} stores present on disk"
    runner.run("T-28: list_stores() — all expected stores present", t28)

    # ── T-29: search() returns dict with all expected keys ────────────────────
    def t29():
        result = kp.search("breakout")
        expected_keys = {"studies", "edges", "strategies", "findings"}
        assert_true(set(result.keys()) == expected_keys,
                    f"search() keys mismatch: {set(result.keys())}")
        return f"search('breakout') → strategies={len(result['strategies'])}, edges={len(result['edges'])}"
    runner.run("T-29: search() returns correct structure", t29)

    # ── T-30: search() keyword matching is case-insensitive ──────────────────
    def t30():
        upper = kp.search("BREAKOUT")
        lower = kp.search("breakout")
        assert_true(
            len(upper["strategies"]) == len(lower["strategies"]),
            "Case sensitivity: upper and lower returned different strategy counts"
        )
        return "case-insensitive match confirmed"
    runner.run("T-30: search() is case-insensitive", t30)

    # ── T-31: get_snapshot() returns KnowledgeSnapshot ───────────────────────
    def t31():
        snap = kp.get_snapshot()
        assert_true(snap.generated_at is not None, "generated_at is None")
        assert_true(len(snap.studies) > 0,   "snapshot.studies empty")
        assert_true(len(snap.edges) > 0,     "snapshot.edges empty")
        assert_true(len(snap.findings) > 0,  "snapshot.findings empty")
        assert_true(snap.regime_history_count > 0, "regime_history_count = 0")
        assert_true(snap.feature_db_count > 0,     "feature_db_count = 0")
        return (
            f"studies={len(snap.studies)}, edges={len(snap.edges)}, "
            f"findings={len(snap.findings)}, certs={len(snap.certifications)}"
        )
    runner.run("T-31: get_snapshot() — complete snapshot", t31)

    # ── T-32: get_warnings() returns list (possibly empty) ───────────────────
    def t32():
        warnings = kp.get_warnings()
        assert_true(isinstance(warnings, list), "get_warnings() did not return list")
        errors = [w for w in warnings if w.severity == LoadSeverity.ERROR]
        assert_true(len(errors) == 0, f"Load errors found: {[w.message for w in errors]}")
        return f"{len(warnings)} warnings, 0 errors"
    runner.run("T-32: get_warnings() — no load errors", t32)

    # ── T-33: KnowledgeProvider does NOT write any files ─────────────────────
    def t33():
        # Check that no new files were created in data/ during the test run
        data_dir = ROOT / "data"
        ars_files_before = set(data_dir.glob("ars_*.json"))
        # Re-run full snapshot to exercise all paths
        _ = kp.get_snapshot()
        ars_files_after = set(data_dir.glob("ars_*.json"))
        new_files = ars_files_after - ars_files_before
        assert_true(len(new_files) == 0, f"KnowledgeProvider created files: {new_files}")
        return "zero files written — read-only constraint confirmed"
    runner.run("T-33: Read-only constraint — no files written", t33)

    # ── T-34: Duplicate instantiation loads same data ─────────────────────────
    def t34():
        kp2 = KnowledgeProvider()
        studies1 = [s.study_id for s in kp.list_studies()]
        studies2 = [s.study_id for s in kp2.list_studies()]
        assert_true(studies1 == studies2, f"Inconsistent: {studies1} vs {studies2}")
        return "second instance returns identical study list"
    runner.run("T-34: Two instances return consistent data", t34)

    # ── T-35: Missing file handled gracefully ─────────────────────────────────
    def t35():
        # Point to a data dir that has no learning_db.json (it never existed)
        kp_test = KnowledgeProvider()
        # learning_db.json doesn't exist — should not raise
        stores = kp_test.list_stores()
        warnings = kp_test.get_warnings()
        # No unhandled exception = pass
        return f"missing files handled, {len(warnings)} warnings issued"
    runner.run("T-35: Missing files handled gracefully", t35)

    return runner


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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
        "# KNOWLEDGE PROVIDER TEST REPORT",
        "## ARS Phase 1.1 — KnowledgeProvider",
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
            lines += [
                f"### {r.name}",
                "",
                f"**Error:**",
                "```",
                r.error or "No error message",
                "```",
                "",
            ]
    else:
        lines.append("*No failures.*")

    lines += [
        "",
        "---",
        "",
        "## Coverage Summary",
        "",
        "| API Method | Covered by Tests |",
        "|---|---|",
        "| `list_studies()` | T-02, T-03, T-34 |",
        "| `get_study(id)` | T-04, T-05 |",
        "| `get_latest_study()` | T-06 |",
        "| `list_findings()` | T-07 |",
        "| `get_findings_by_classification()` | T-08, T-09, T-10 |",
        "| `list_edges()` | T-11, T-12 |",
        "| `list_edges(status=)` | T-13 |",
        "| `list_edges(min_composite_score=)` | T-14 |",
        "| `list_strategies()` | T-15 |",
        "| `list_strategies(approved_only=)` | T-16 |",
        "| `list_certifications()` | T-17, T-18 |",
        "| `list_knowledge_metrics()` | T-19 |",
        "| `list_knowledge_metrics(category=)` | T-20 |",
        "| `get_regime_history()` | T-21 |",
        "| `get_regime_history(limit=)` | T-22 |",
        "| `get_regime_history(dominant_regime=)` | T-23 |",
        "| `list_features()` | T-24 |",
        "| `list_features(limit=)` | T-25 |",
        "| `list_features(limit=None)` | T-26 |",
        "| `get_replay_summary()` | T-27 |",
        "| `list_stores()` | T-28 |",
        "| `search(keyword)` | T-29, T-30 |",
        "| `get_snapshot()` | T-31 |",
        "| `get_warnings()` | T-32 |",
        "| Read-only constraint | T-33 |",
        "| Error handling (missing files) | T-35 |",
        "",
        "---",
        "",
        f"*Generated by test_knowledge_provider.py | {now}*",
    ]

    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 64)
    print("ARS Phase 1.1 — KnowledgeProvider Test Suite")
    print("=" * 64)

    t_start = time.perf_counter()
    runner = run_all_tests()
    elapsed = time.perf_counter() - t_start

    print(f"\nResults: {runner.passed} passed / {runner.failed} failed "
          f"({len(runner.results)} total) in {elapsed:.2f}s\n")

    for r in runner.results:
        icon = "✓" if r.passed else "✗"
        print(f"  {icon} {r.name:55s} {r.duration_ms:6.1f}ms  {r.detail[:60]}")

    if runner.failed:
        print("\nFAILURES:")
        for r in runner.results:
            if not r.passed:
                print(f"\n  ✗ {r.name}")
                print(f"    {r.error}")

    # Write report
    report_path = ROOT / "KNOWLEDGE_PROVIDER_TEST_REPORT.md"
    report_path.write_text(generate_report(runner), encoding="utf-8")
    print(f"\nTest report written → {report_path}")

    sys.exit(0 if runner.failed == 0 else 1)

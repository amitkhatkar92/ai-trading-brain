"""tests/performance/conftest.py
Performance Certification Report — hooks for the IIOS Platform Performance
& Load Certification suite.  Collects per-part pass/fail and prints the
institutional performance certification report after the session finishes.
"""
from __future__ import annotations

import datetime
from collections import defaultdict
from typing import DefaultDict, Dict, List

import pytest


# ── Result store ──────────────────────────────────────────────────────────────

_PERF_RESULTS: DefaultDict[str, List[bool]] = defaultdict(list)

_PART_MAP: Dict[str, str] = {
    "PerfPart1":  "Part 01 - Latency",
    "PerfPart2":  "Part 02 - Throughput",
    "PerfPart3":  "Part 03 - Scalability",
    "PerfPart4":  "Part 04 - Resources",
    "PerfPart5":  "Part 05 - Long Run",
    "PerfPart6":  "Part 06 - Framework Overhead",
    "PerfPart7":  "Part 07 - Stress",
    "PerfPart8":  "Part 08 - Bottleneck",
    "PerfPart9":  "Part 09 - Optimization Report",
    "PerfPart10": "Part 10 - Final Certification",
}


# Sort longest prefix first so "PerfPart10" is matched before "PerfPart1"
_SORTED_PART_MAP = sorted(_PART_MAP.items(), key=lambda kv: len(kv[0]), reverse=True)


def pytest_runtest_makereport(item, call):
    """Classify each test result into its certification part."""
    if call.when != "call":
        return
    node = item.nodeid
    for cls_prefix, part_label in _SORTED_PART_MAP:
        if cls_prefix in node:
            _PERF_RESULTS[part_label].append(call.excinfo is None)
            break


# ── Grade helpers ─────────────────────────────────────────────────────────────

def _score(results: List[bool]) -> float:
    if not results:
        return 0.0
    return 100.0 * sum(results) / len(results)


def _grade(pct: float) -> str:
    if pct >= 95.0:
        return "A"
    if pct >= 85.0:
        return "B"
    if pct >= 70.0:
        return "C"
    if pct >= 50.0:
        return "D"
    return "F"


def _verdict(overall: float) -> str:
    if overall >= 95.0:
        return "[GO]  Platform certified for C6 Execution Intelligence"
    if overall >= 80.0:
        return "[CONDITIONAL GO]  Minor optimisations required before C6"
    if overall >= 60.0:
        return "[CONDITIONAL GO]  Significant optimisations required before C6"
    return "[NO-GO]  Critical performance deficiencies block C6 deployment"


# ── Report ─────────────────────────────────────────────────────────────────────

def pytest_sessionfinish(session, exitstatus):
    """Print the institutional performance certification report."""
    if not _PERF_RESULTS:
        return

    now   = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    width = 78
    sep   = "=" * width

    lines: List[str] = []

    lines += [
        "",
        sep,
        "  IIOS CORE INTELLIGENCE PLATFORM",
        "  PERFORMANCE & LOAD CERTIFICATION REPORT",
        sep,
        f"  Date:          {now}",
        f"  Scope:         C1-C5  |  M2.1-M2.5 Frameworks",
        f"  Goal:          Certify platform for C6 Execution Intelligence",
        sep,
        "",
        f"  {'PART':<35}  {'SCORE':>7}  {'GRADE':>5}  {'RESULT':>6}",
        "  " + "-" * (width - 2),
    ]

    ordered_parts = [
        "Part 01 - Latency",
        "Part 02 - Throughput",
        "Part 03 - Scalability",
        "Part 04 - Resources",
        "Part 05 - Long Run",
        "Part 06 - Framework Overhead",
        "Part 07 - Stress",
        "Part 08 - Bottleneck",
        "Part 09 - Optimization Report",
        "Part 10 - Final Certification",
    ]

    part_scores: List[float] = []
    issues:      List[str]   = []

    for part in ordered_parts:
        results = _PERF_RESULTS.get(part, [])
        n       = len(results)
        p       = sum(results)
        f       = n - p
        sc      = _score(results)
        gr      = _grade(sc)
        part_scores.append(sc)
        status  = "PASS" if f == 0 and n > 0 else ("SKIP" if n == 0 else "FAIL")
        lines.append(
            f"  {part:<35}  {sc:6.1f}%  {gr:>5}  {status:>6}  ({p}/{n})"
        )
        if f > 0:
            issues.append(f"{part}: {f} test(s) failed")

    # -- Derived scores --------------------------------------------------------
    def _s(name: str) -> float:
        return _score(_PERF_RESULTS.get(name, []))

    lat_score      = _s("Part 01 - Latency")
    tput_score     = _s("Part 02 - Throughput")
    scale_score    = _s("Part 03 - Scalability")
    res_score      = _s("Part 04 - Resources")
    longrun_score  = _s("Part 05 - Long Run")
    fwk_score      = _s("Part 06 - Framework Overhead")
    stress_score   = _s("Part 07 - Stress")
    bottleneck_score = _s("Part 08 - Bottleneck")

    # Weighted average (latency + throughput have higher weight)
    weights = [0.20, 0.15, 0.15, 0.10, 0.15, 0.10, 0.10, 0.05]
    scores  = [lat_score, tput_score, scale_score, res_score,
               longrun_score, fwk_score, stress_score, bottleneck_score]
    production_score = sum(w * s for w, s in zip(weights, scores))

    overall = production_score
    overall_grade = _grade(overall)

    lines += [
        "",
        "  " + "-" * (width - 2),
        "  PERFORMANCE SCORES",
        "  " + "-" * (width - 2),
        f"  Latency Score         (p50/p95/p99 vs thresholds):   {lat_score:5.1f}%",
        f"  Throughput Score      (wf/sec, snapshots/sec):        {tput_score:5.1f}%",
        f"  Scalability Score     (1-100 concurrent):             {scale_score:5.1f}%",
        f"  Memory Score          (heap, threads, GC):            {res_score:5.1f}%",
        f"  Long Run Score        (1k/5k/10k stability):          {longrun_score:5.1f}%",
        f"  Framework Overhead    (lifecycle/log/error/async):    {fwk_score:5.1f}%",
        f"  Stress Score          (concurrency, cancel, failure): {stress_score:5.1f}%",
        f"  Bottleneck Score      (contention, serialisation):    {bottleneck_score:5.1f}%",
        "",
        f"  Production Performance Score (weighted):              {production_score:5.1f}%",
        f"  Overall Performance Grade:                            {overall_grade}",
        "",
    ]

    if issues:
        lines += [
            "  " + "-" * (width - 2),
            "  FINDINGS REQUIRING ATTENTION",
            "  " + "-" * (width - 2),
        ]
        for iss in issues:
            lines.append(f"  [!] {iss}")
        lines.append("")

    lines += [
        "  " + "-" * (width - 2),
        f"  VERDICT:  {_verdict(overall)}",
        sep,
        "",
    ]

    print("\n".join(lines))

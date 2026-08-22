"""tests/certification/conftest.py
Certification hooks - collects per-part pass/fail and generates the
institutional certification report after the test session finishes.
"""
from __future__ import annotations

import datetime
from collections import defaultdict
from typing import DefaultDict, Dict, List, Tuple

import pytest


# -- Result store (populated by pytest_runtest_makereport hook) ---------------

_PART_RESULTS: DefaultDict[str, List[bool]] = defaultdict(list)

_PART_MAP: Dict[str, str] = {
    "CertPart1": "Part 1 - Pipeline",
    "CertPart2": "Part 2 - Workflow",
    "CertPart3": "Part 3 - Framework",
    "CertPart4": "Part 4 - Thread Safety",
    "CertPart5": "Part 5 - Fault Injection",
    "CertPart6": "Part 6 - Long Run",
    "CertPart7": "Part 7 - Regression",
}


def pytest_runtest_makereport(item, call):
    """Classify each test result into its certification part."""
    if call.when != "call":
        return
    node = item.nodeid
    for cls_prefix, part_label in _PART_MAP.items():
        if cls_prefix in node:
            _PART_RESULTS[part_label].append(call.excinfo is None)
            break


# -- Certification report ------------------------------------------------------

def _score(results: List[bool]) -> float:
    if not results:
        return 0.0
    return 100.0 * sum(results) / len(results)


def _verdict(scores: List[float]) -> str:
    avg = sum(scores) / len(scores) if scores else 0.0
    if avg >= 95.0:
        return "-  GO  - Platform certified for Performance Certification"
    if avg >= 80.0:
        return "--  CONDITIONAL GO  - Minor issues; remediation required"
    return "-  NO-GO  - Critical issues block progression"


def pytest_sessionfinish(session, exitstatus):
    """Print the institutional certification report."""
    if not _PART_RESULTS:
        return

    now   = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    width = 72

    lines: List[str] = []
    sep   = "=" * width

    lines += [
        "",
        sep,
        "  IIOS CORE INTELLIGENCE PLATFORM - INTEGRATION CERTIFICATION REPORT",
        sep,
        f"  Date:          {now}",
        f"  Certification: C1-C5 End-to-End  |  M2.1-M2.5 Frameworks",
        sep,
        "",
    ]

    part_scores: List[float] = []
    issues: List[str]        = []

    ordered_parts = [
        "Part 1 - Pipeline",
        "Part 2 - Workflow",
        "Part 3 - Framework",
        "Part 4 - Thread Safety",
        "Part 5 - Fault Injection",
        "Part 6 - Long Run",
        "Part 7 - Regression",
    ]

    for part in ordered_parts:
        results = _PART_RESULTS.get(part, [])
        n       = len(results)
        p       = sum(results)
        f       = n - p
        sc      = _score(results)
        part_scores.append(sc)
        status  = "PASS" if f == 0 and n > 0 else ("SKIP" if n == 0 else "FAIL")
        bar     = "#" * int(sc / 5) + "." * (20 - int(sc / 5))
        lines.append(
            f"  {part:<28}  [{bar}]  {sc:5.1f}%  ({p}/{n})  {status}"
        )
        if f > 0:
            issues.append(f"    [{part}] {f} test(s) failed")

    # -- Derived scores --------------------------------------------------------
    results_map = {p: _PART_RESULTS.get(p, []) for p in ordered_parts}

    pipeline_score    = _score(results_map["Part 1 - Pipeline"])
    workflow_score    = _score(results_map["Part 2 - Workflow"])
    framework_score   = _score(results_map["Part 3 - Framework"])
    thread_score      = _score(results_map["Part 4 - Thread Safety"])
    fault_score       = _score(results_map["Part 5 - Fault Injection"])
    longrun_score     = _score(results_map["Part 6 - Long Run"])
    regression_score  = _score(results_map["Part 7 - Regression"])

    integration_score = (pipeline_score + framework_score) / 2
    reliability_score = (workflow_score + longrun_score) / 2
    recovery_score    = (fault_score + workflow_score) / 2
    production_score  = sum(part_scores) / len(part_scores) if part_scores else 0.0

    lines += [
        "",
        "  " + "-" * (width - 2),
        "  DERIVED SCORES",
        "  " + "-" * (width - 2),
        f"  Integration Score     (C1-C5 pipeline + framework):  {integration_score:5.1f}%",
        f"  Reliability Score     (workflow stability + long run): {reliability_score:5.1f}%",
        f"  Recovery Score        (fault injection + retry):       {recovery_score:5.1f}%",
        f"  Thread Safety Score   (concurrent + context):          {thread_score:5.1f}%",
        f"  Framework Integration (lifecycle/log/error/async):     {framework_score:5.1f}%",
        f"  Regression Score      (no new failures):               {regression_score:5.1f}%",
        f"  Production Readiness  (weighted average all parts):    {production_score:5.1f}%",
        "",
    ]

    if issues:
        lines += ["  REMAINING ISSUES", "  " + "-" * (width - 2)]
        lines += [f"  [!] {iss.strip()}" for iss in issues]
        lines += [""]

    lines += [
        "  " + "-" * (width - 2),
        f"  VERDICT:  {_verdict(part_scores)}",
        sep,
        "",
    ]

    print("\n".join(lines))

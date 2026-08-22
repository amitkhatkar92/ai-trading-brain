"""
live_operations/phase7_go_nogo.py
===================================
Phase 7 — GO / NO-GO Decision

Before market opens, aggregates signals from four authorities:
  1. System Health (Phase 1 result)
  2. Broker readiness (DhanFeed auth + connectivity)
  3. Scientific Director (critical alerts)
  4. Market Learning Coordinator (pipeline health)

Produces a structured GO / GO WITH OBSERVATIONS / NO GO decision.

NO GO is issued when:
  - System is BLOCKED (critical infra down)
  - Broker authentication is expired
  - Internet is unreachable
  - VIX > 45 (kill-switch threshold)

NO live trading begins if NO GO is issued.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .lol_config import (
    DATA_DIR,
    GONOGO_WEIGHT_HEALTH, GONOGO_WEIGHT_BROKER,
    GONOGO_WEIGHT_SD,     GONOGO_WEIGHT_MLC,
    GONOGO_PASS_THRESHOLD, GONOGO_WARN_THRESHOLD,
)
from .report_writer import (
    report_header, section, kv, kv_ok, kv_warn, kv_fail,
    hr, badge, now_ist_str
)
from .phase1_health_check import HealthCheckResult, run_health_check

IST = timezone(timedelta(hours=5, minutes=30))


DECISION_GO      = "GO"
DECISION_GO_OBS  = "GO_OBS"
DECISION_NO_GO   = "NO_GO"


@dataclass
class AuthorityVote:
    authority:  str
    score:      float          # 0.0–1.0
    verdict:    str            # GO | GO_OBS | NO_GO
    notes:      List[str] = field(default_factory=list)
    blocking:   bool = False   # True → forces NO_GO regardless of score


@dataclass
class GoNoGoResult:
    report_date:  str
    decision:     str = DECISION_NO_GO
    score:        float = 0.0
    votes:        List[AuthorityVote] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    blockers:     List[str] = field(default_factory=list)
    health_result: Optional[HealthCheckResult] = None


# ── Authority evaluators ────────────────────────────────────────────────────

def _evaluate_health(health: HealthCheckResult) -> AuthorityVote:
    score = health.score()
    notes = [f"checks={len(health.points)}  pass={health.pass_count}"
             f"  warn={health.warn_count}  fail={health.fail_count}"]

    if health.overall == "BLOCKED":
        return AuthorityVote(
            authority="SystemHealth", score=0.0, verdict=DECISION_NO_GO,
            notes=[f"System BLOCKED: {health.blocking_count} critical failures"] + notes,
            blocking=True,
        )
    if health.overall == "NOT_READY":
        return AuthorityVote(
            authority="SystemHealth", score=score, verdict=DECISION_GO_OBS,
            notes=notes, blocking=False,
        )
    return AuthorityVote(
        authority="SystemHealth", score=score, verdict=DECISION_GO,
        notes=notes,
    )


def _evaluate_broker() -> AuthorityVote:
    notes = []
    score = 1.0
    verdict = DECISION_GO
    blocking = False

    import config as _cfg
    if getattr(_cfg, "PAPER_TRADING", True):
        notes.append("PAPER_TRADING=True — broker auth not required")
        return AuthorityVote("Broker", 1.0, DECISION_GO, notes)

    import os as _os
    cid   = _os.getenv("DHAN_CLIENT_ID", "")
    token = _os.getenv("DHAN_ACCESS_TOKEN", "")
    if not cid or not token:
        return AuthorityVote(
            "Broker", 0.0, DECISION_NO_GO,
            ["Dhan credentials missing — live trading impossible"],
            blocking=True,
        )
    # Check JWT expiry
    try:
        import base64 as _b64, re as _re, time as _time
        part = token.split(".")[1]
        part += "=" * (4 - len(part) % 4)
        raw  = _b64.urlsafe_b64decode(part).decode("latin-1")
        m    = _re.search(r'"exp"\s*:\s*(\d+)', raw)
        if m:
            rem_h = (int(m.group(1)) - _time.time()) / 3600
            if rem_h <= 0:
                return AuthorityVote(
                    "Broker", 0.0, DECISION_NO_GO,
                    [f"Dhan token EXPIRED {abs(rem_h):.1f}h ago"],
                    blocking=True,
                )
            if rem_h <= 1:
                score = 0.6
                verdict = DECISION_GO_OBS
                notes.append(f"Token expires in {rem_h*60:.0f}m — refresh soon")
            else:
                notes.append(f"Token valid — expires in {rem_h:.0f}h")
    except Exception as e:
        notes.append(f"JWT parse warning: {e}")
        score = 0.8
        verdict = DECISION_GO_OBS

    return AuthorityVote("Broker", score, verdict, notes, blocking)


def _evaluate_scientific_director() -> AuthorityVote:
    notes = []
    score = 1.0

    sd_journal = DATA_DIR / "scientific_journal.json"
    if not sd_journal.exists():
        notes.append("SD journal not found — assuming no alerts")
        return AuthorityVote("ScientificDirector", 1.0, DECISION_GO, notes)

    try:
        with open(sd_journal, encoding="utf-8") as f:
            journal = json.load(f)
        today   = date.today().isoformat()
        entries = journal.get("entries", journal if isinstance(journal, list) else [])
        critical = []
        for e in (entries or []):
            if isinstance(e, dict):
                ts  = str(e.get("timestamp", e.get("date", "")))
                sev = str(e.get("severity", e.get("level", "INFO"))).upper()
                msg = str(e.get("message", e.get("content", "")))
                if today in ts and sev in ("CRITICAL", "HALT"):
                    critical.append(msg[:100])

        if critical:
            notes.extend(critical)
            return AuthorityVote(
                "ScientificDirector", 0.2, DECISION_NO_GO,
                notes, blocking=False,  # SD can recommend NO GO but not force it
            )
        notes.append("No critical SD alerts today")
    except Exception as e:
        notes.append(f"SD journal unreadable: {e}")
        score = 0.8

    return AuthorityVote("ScientificDirector", score, DECISION_GO, notes)


def _evaluate_mlc() -> AuthorityVote:
    notes = []
    score = 1.0

    # Check last MLC run health
    mlc_hist = DATA_DIR / "mls" / "mlc_runs.json"
    if not mlc_hist.exists():
        notes.append("MLC run history not found — no learning data yet")
        return AuthorityVote("MLC", 0.8, DECISION_GO_OBS, notes)

    try:
        with open(mlc_hist, encoding="utf-8") as f:
            runs = json.load(f)
        if runs:
            last = runs[-1] if isinstance(runs, list) else runs
            health = last.get("health", "UNKNOWN")
            run_id = last.get("run_id", "?")
            notes.append(f"Last MLC run: {run_id}  health={health}")
            if health == "FAILED":
                score = 0.3
                return AuthorityVote("MLC", score, DECISION_GO_OBS,
                                     notes + ["MLC pipeline FAILED last run"])
            if health == "DEGRADED":
                score = 0.7
                return AuthorityVote("MLC", score, DECISION_GO_OBS, notes)
    except Exception as e:
        notes.append(f"MLC history unreadable: {e}")
        score = 0.7

    return AuthorityVote("MLC", score, DECISION_GO, notes)


# ── Main runner ─────────────────────────────────────────────────────────────

def run_go_nogo(
    report_date: Optional[str] = None,
    health_result: Optional[HealthCheckResult] = None,
) -> GoNoGoResult:
    """
    Aggregate all four authority votes and issue GO / GO WITH OBSERVATIONS / NO GO.
    Pass pre-computed HealthCheckResult to avoid running health check twice.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    if health_result is None:
        health_result = run_health_check(report_date)

    result = GoNoGoResult(
        report_date=report_date,
        health_result=health_result,
    )

    # Evaluate all four authorities
    votes = [
        _evaluate_health(health_result),
        _evaluate_broker(),
        _evaluate_scientific_director(),
        _evaluate_mlc(),
    ]
    result.votes = votes

    # Check for blockers
    for vote in votes:
        if vote.blocking:
            result.blockers.append(f"{vote.authority}: {vote.notes[0] if vote.notes else 'BLOCKED'}")

    # Weighted score
    weights = [
        GONOGO_WEIGHT_HEALTH,
        GONOGO_WEIGHT_BROKER,
        GONOGO_WEIGHT_SD,
        GONOGO_WEIGHT_MLC,
    ]
    result.score = sum(v.score * w for v, w in zip(votes, weights))

    # Observations
    for vote in votes:
        for note in vote.notes:
            if vote.verdict != DECISION_GO:
                result.observations.append(f"{vote.authority}: {note}")

    # Final decision
    if result.blockers:
        result.decision = DECISION_NO_GO
    elif result.score >= GONOGO_PASS_THRESHOLD and not any(
        v.verdict == DECISION_NO_GO for v in votes
    ):
        result.decision = DECISION_GO
    elif result.score >= GONOGO_WARN_THRESHOLD:
        result.decision = DECISION_GO_OBS
    else:
        result.decision = DECISION_NO_GO

    return result


def format_go_nogo_report(result: GoNoGoResult, report_date: str) -> str:
    decision_badge = badge(result.decision)
    lines = [
        report_header("GO / NO-GO DECISION", report_date,
                      f"Decision: {decision_badge}")
    ]

    lines.append(section("DECISION"))
    d_kv = kv_ok if result.decision == DECISION_GO else (
           kv_warn if result.decision == DECISION_GO_OBS else kv_fail)
    lines.append(d_kv("FINAL DECISION:", decision_badge))
    lines.append(kv("Weighted score:", f"{result.score*100:.0f}%"))
    lines.append(kv("Blockers:", len(result.blockers)))
    lines.append(kv("Observations:", len(result.observations)))

    lines.append(section("AUTHORITY VOTES"))
    for vote in result.votes:
        v_kv = kv_ok if vote.verdict == DECISION_GO else (
               kv_warn if vote.verdict == DECISION_GO_OBS else kv_fail)
        lines.append(v_kv(f"{vote.authority}:",
                          f"{badge(vote.verdict)}  score={vote.score*100:.0f}%"))
        for note in vote.notes:
            lines.append(f"    • {note}")

    if result.blockers:
        lines.append(section("BLOCKERS (REQUIRE RESOLUTION)"))
        for b in result.blockers:
            lines.append(f"  ✗ {b}")

    if result.observations:
        lines.append(section("OBSERVATIONS"))
        for obs in result.observations:
            lines.append(f"  ⚠ {obs}")

    lines.append(section("OPERATIONAL GUIDANCE"))
    if result.decision == DECISION_GO:
        lines.append("  ✓ All systems ready. Proceed to live trading.")
    elif result.decision == DECISION_GO_OBS:
        lines.append("  ⚠ Trading may proceed. Monitor observations closely.")
        lines.append("  ⚠ Increase monitoring frequency. Consider reducing position sizes.")
    else:
        lines.append("  ✗ DO NOT begin live trading until blockers are resolved.")
        for b in result.blockers:
            lines.append(f"  ✗ RESOLVE: {b}")

    lines.append(f"\n{hr()}")
    return "\n".join(lines)

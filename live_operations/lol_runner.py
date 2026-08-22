"""
live_operations/lol_runner.py
===============================
LOL-001 Main Runner — Orchestrates all seven operational phases.

Usage (from CLI):
    python -m live_operations.lol_runner --phase premarket
    python -m live_operations.lol_runner --phase monitor
    python -m live_operations.lol_runner --phase incident
    python -m live_operations.lol_runner --phase postmarket
    python -m live_operations.lol_runner --phase all

Callable from orchestrator:
    from live_operations import run_premarket, run_postmarket

Writes all reports to data/lol/YYYY-MM-DD/
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .lol_config import (
    LOL_DIR,
    RPT_PREMARKET, RPT_SYSTEM_HEALTH, RPT_LIVE_MONITOR,
    RPT_INCIDENT, RPT_DAILY_TRADING, RPT_EXEC_SUMMARY, RPT_CERTIFICATE,
    MONITOR_INTERVAL_SEC,
)
from .report_writer import (
    write_report, append_report, report_header, section,
    kv, kv_ok, kv_warn, kv_fail, hr, badge, now_ist_str
)
from .phase1_health_check import run_health_check, format_health_report
from .phase2_premarket_report import generate_premarket_report
from .phase3_live_monitor import capture_snapshot, format_monitor_report
from .phase4_incident_manager import run_incident_scan, format_incident_report
from .phase5_postmarket_review import generate_daily_trading_report
from .phase6_executive_dashboard import generate_executive_summary
from .phase7_go_nogo import run_go_nogo, format_go_nogo_report, DECISION_NO_GO

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))


# ── Pre-market flow: Phases 1 + 2 + 7 ──────────────────────────────────────

def run_premarket(report_date: Optional[str] = None) -> dict:
    """
    Run Phases 1 (Health Check) + 2 (Pre-Market Report) + 7 (GO/NO-GO).
    Returns dict with paths to generated files and the GO/NO-GO decision.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    log.info("[LOL] Pre-market run started — %s", report_date)
    results = {"report_date": report_date, "files": {}, "go_nogo": None}

    # Phase 1 — Health Check
    log.info("[LOL] Phase 1: Health Check")
    health = run_health_check(report_date)
    health_md = format_health_report(health)
    path = write_report(RPT_SYSTEM_HEALTH, health_md, report_date)
    results["files"]["system_health"] = str(path)
    log.info("[LOL] Health: %s  score=%.0f%%", health.overall, health.score() * 100)

    # Phase 2 — Pre-Market Report
    log.info("[LOL] Phase 2: Pre-Market Report")
    premarket_md = generate_premarket_report(report_date)
    path = write_report(RPT_PREMARKET, premarket_md, report_date)
    results["files"]["premarket_report"] = str(path)

    # Phase 7 — GO/NO-GO
    log.info("[LOL] Phase 7: GO/NO-GO Decision")
    gonogo = run_go_nogo(report_date, health_result=health)
    gonogo_md = format_go_nogo_report(gonogo, report_date)

    # Append GO/NO-GO section to pre-market report
    append_report(RPT_PREMARKET, gonogo_md, report_date)

    results["go_nogo"] = gonogo.decision
    results["go_nogo_score"] = round(gonogo.score, 3)
    results["blockers"] = gonogo.blockers

    log.info("[LOL] GO/NO-GO: %s  score=%.0f%%", gonogo.decision, gonogo.score * 100)

    if gonogo.decision == DECISION_NO_GO:
        log.warning("[LOL] NO GO — do not begin trading. Blockers: %s", gonogo.blockers)

    # Write LOL certificate
    cert_md = _generate_certificate(report_date, health, gonogo)
    path = write_report(RPT_CERTIFICATE, cert_md, report_date)
    results["files"]["certificate"] = str(path)

    log.info("[LOL] Pre-market complete. Reports in %s", LOL_DIR / report_date)
    return results


# ── Live monitor flow: Phase 3 ──────────────────────────────────────────────

def run_live_monitor(
    report_date: Optional[str] = None,
    once: bool = True,
) -> dict:
    """
    Phase 3: capture a live snapshot and update LIVE_MONITOR_REPORT.md.
    Set once=False to run a continuous monitoring loop (blocking).
    """
    if report_date is None:
        report_date = date.today().isoformat()

    def _one_pass():
        snap = capture_snapshot(report_date)
        md   = format_monitor_report(snap, report_date)
        write_report(RPT_LIVE_MONITOR, md, report_date)
        # Also check for incidents
        run_incident_check(report_date)
        return snap

    if once:
        snap = _one_pass()
        return {"snapshot": snap, "report_date": report_date}

    # Continuous loop
    log.info("[LOL] Starting continuous live monitor (interval=%ds)", MONITOR_INTERVAL_SEC)
    while True:
        try:
            _one_pass()
        except Exception as exc:
            log.warning("[LOL] Monitor pass error: %s", exc)
        time.sleep(MONITOR_INTERVAL_SEC)


# ── Incident check: Phase 4 ─────────────────────────────────────────────────

def run_incident_check(report_date: Optional[str] = None) -> dict:
    """Phase 4: run one incident scan pass."""
    if report_date is None:
        report_date = date.today().isoformat()

    report = run_incident_scan(report_date)
    if report.incidents:
        md   = format_incident_report(report)
        path = write_report(RPT_INCIDENT, md, report_date)
        log.warning("[LOL] Incidents detected: %d  status=%s", len(report.incidents), report.status)
        return {"status": report.status, "incident_count": len(report.incidents), "file": str(path)}
    return {"status": "CLEAR", "incident_count": 0}


# ── Post-market flow: Phases 5 + 6 ─────────────────────────────────────────

def run_postmarket(report_date: Optional[str] = None) -> dict:
    """
    Run Phases 5 (Daily Trading Report) + 6 (Executive Summary).
    Also generates weekly and monthly summaries when applicable.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    log.info("[LOL] Post-market run started — %s", report_date)
    results = {"report_date": report_date, "files": {}}

    # Phase 5 — Daily Trading Report
    log.info("[LOL] Phase 5: Daily Trading Report")
    daily_md = generate_daily_trading_report(report_date)
    path = write_report(RPT_DAILY_TRADING, daily_md, report_date)
    results["files"]["daily_trading"] = str(path)

    # Phase 6 — Executive Summary (daily)
    log.info("[LOL] Phase 6: Executive Summary")
    exec_md = generate_executive_summary(report_date, period="daily")
    path = write_report(RPT_EXEC_SUMMARY, exec_md, report_date)
    results["files"]["executive_summary"] = str(path)

    # Weekly summary on Monday (day 0)
    today = date.fromisoformat(report_date)
    if today.weekday() == 0:
        weekly_md = generate_executive_summary(report_date, period="weekly")
        path = write_report("WEEKLY_EXECUTIVE_SUMMARY.md", weekly_md, report_date)
        results["files"]["weekly_summary"] = str(path)
        log.info("[LOL] Weekly summary generated")

    # Monthly summary on 1st of month
    if today.day == 1:
        monthly_md = generate_executive_summary(report_date, period="monthly")
        path = write_report("MONTHLY_EXECUTIVE_SUMMARY.md", monthly_md, report_date)
        results["files"]["monthly_summary"] = str(path)
        log.info("[LOL] Monthly summary generated")

    log.info("[LOL] Post-market complete. Reports in %s", LOL_DIR / report_date)
    return results


# ── Full-day flow ────────────────────────────────────────────────────────────

def run_all(report_date: Optional[str] = None) -> dict:
    """Run all phases sequentially (for testing / manual invocation)."""
    if report_date is None:
        report_date = date.today().isoformat()

    results = {}
    results["premarket"]  = run_premarket(report_date)
    results["monitor"]    = run_live_monitor(report_date, once=True)
    results["incident"]   = run_incident_check(report_date)
    results["postmarket"] = run_postmarket(report_date)
    return results


# ── Certificate generator ────────────────────────────────────────────────────

def _generate_certificate(report_date: str, health, gonogo) -> str:
    from .phase1_health_check import HealthCheckResult
    from .phase7_go_nogo import GoNoGoResult

    decision_badge = badge(gonogo.decision)
    lines = [
        report_header("LIVE OPERATIONS CERTIFICATE", report_date,
                      f"LOL-001  Decision: {decision_badge}")
    ]
    lines.append(section("CERTIFICATION SUMMARY"))
    lines.append(kv("Date:", report_date))
    lines.append(kv("Generated:", now_ist_str()))
    d_kv = kv_ok if gonogo.decision == "GO" else (
           kv_warn if gonogo.decision == "GO_OBS" else kv_fail)
    lines.append(d_kv("DECISION:", decision_badge))
    lines.append(kv("Health score:", f"{health.score()*100:.0f}%"))
    lines.append(kv("GO/NO-GO score:", f"{gonogo.score*100:.0f}%"))

    lines.append(section("SYSTEM HEALTH"))
    lines.append(kv("Overall:", badge(health.overall)))
    lines.append(kv("Checks passed:", f"{health.pass_count}/{len(health.points)}"))
    lines.append(kv("Warnings:", health.warn_count))
    lines.append(kv("Failures:", health.fail_count))

    lines.append(section("AUTHORITY VOTES"))
    for vote in gonogo.votes:
        v_kv = kv_ok if vote.verdict == "GO" else (
               kv_warn if vote.verdict == "GO_OBS" else kv_fail)
        lines.append(v_kv(f"{vote.authority}:", badge(vote.verdict)))

    if gonogo.blockers:
        lines.append(section("BLOCKERS"))
        for b in gonogo.blockers:
            lines.append(f"  ✗ {b}")

    if gonogo.observations:
        lines.append(section("OBSERVATIONS"))
        for obs in gonogo.observations[:10]:
            lines.append(f"  ⚠ {obs}")

    lines.append(section("OPERATIONAL GUIDANCE"))
    if gonogo.decision == "GO":
        lines.append("  ✓ All systems certified. Trading may commence.")
    elif gonogo.decision == "GO_OBS":
        lines.append("  ⚠ Trading may commence with enhanced monitoring.")
    else:
        lines.append("  ✗ DO NOT TRADE until all blockers are resolved.")

    lines.append(f"\n{hr()}")
    lines.append(f"  LOL-001 Live Operations Certificate — {report_date}")
    lines.append(hr())
    return "\n".join(lines)


# ── LOLRunner class ─────────────────────────────────────────────────────────

class LOLRunner:
    """
    Full automated LOL-001 runner. Wires all 7 phases for daily operation.

    Usage:
        runner = LOLRunner()
        runner.premarket()         # before 09:15 IST
        runner.live_monitor_once() # called each cycle by orchestrator
        runner.incident_check()    # called each cycle
        runner.postmarket()        # after 15:35 IST
    """

    def __init__(self, report_date: Optional[str] = None):
        self.report_date = report_date or date.today().isoformat()

    def premarket(self) -> dict:
        return run_premarket(self.report_date)

    def live_monitor_once(self) -> dict:
        return run_live_monitor(self.report_date, once=True)

    def incident_check(self) -> dict:
        return run_incident_check(self.report_date)

    def postmarket(self) -> dict:
        return run_postmarket(self.report_date)

    def run_all(self) -> dict:
        return run_all(self.report_date)


# ── CLI entry point ─────────────────────────────────────────────────────────

def main():
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [LOL] %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="LOL-001 Live Operations Runner")
    parser.add_argument("--phase", choices=["premarket", "monitor", "incident",
                                            "postmarket", "all"],
                        default="all", help="Which phase to run")
    parser.add_argument("--date", default=None, help="Report date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    report_date = args.date or date.today().isoformat()

    phase_map = {
        "premarket":  lambda: run_premarket(report_date),
        "monitor":    lambda: run_live_monitor(report_date, once=True),
        "incident":   lambda: run_incident_check(report_date),
        "postmarket": lambda: run_postmarket(report_date),
        "all":        lambda: run_all(report_date),
    }

    result = phase_map[args.phase]()
    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    main()

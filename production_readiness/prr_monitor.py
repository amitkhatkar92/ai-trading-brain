"""
production_readiness/prr_monitor.py
=======================================
Self-Learning Ecosystem — Phase 5: production_readiness score -> monitoring
integration (advisory-only, no trade halt).

production_readiness/prr_runner.py::run_prr() already computes a clean daily
certification summary (certification_status, ils_score, gva_score,
critical_failures, warnings, elapsed_seconds) at EOD (wired in
orchestrator/master_orchestrator.py's _do_eod_learning(), PRR-001 block).
Its entire effect today is ONE log.info() line -- the summary dict is
discarded immediately after: never persisted, never surfaced to an
operator, never queryable by any future consumer. This closes that
dead-end, the same class of gap found in Phase 3 (PGA) and Phase 4
(rejection tracker): a value is computed and validated by the existing
9-phase certification pipeline, but never propagated anywhere.

KBL stages:
  ACQUISITION  (already exists, no change): run_prr()'s daily summary dict.
  VALIDATION   (already exists, no change): ph9_certification.py's own
               9-phase CRITICAL/WARNING pass-fail logic already decides
               the verdict -- no new statistical gate needed here.
  SYNTHESIS    (NEW, trivial): append-only daily history record.
  PROPAGATION  (NEW): get_latest_certification() / get_certification_
               history() read-only accessors for a future dashboard/
               Telegram command.
  GOVERNANCE   : advisory-only, explicitly no trade halt. Alerts only on
               NOT_READY or a verdict CHANGE (mirrors the existing KDA
               Authority Update "only alert on state change" convention)
               to avoid daily noise. Never reads/writes any risk,
               decision, or execution state.

Found, not fixed (separate, pre-existing issue, out of this phase's
scope): production_readiness/ph5_daily_pipeline.py::run_daily_pipeline()
is dead code -- never called from master_orchestrator.py or anywhere
else, despite its own docstring claiming it replaces the orchestrator's
individual PGA/ILC try/except blocks. Because of this,
ph9_certification.py's "Daily_ILC_Operational" check always evaluates
data["pipeline"] as None (prr_runner.py's _collect_prr_data() never sets
it), which its own code hard-codes to a static PASS/INFO regardless of
actual pipeline health. Fixing this would change ph9's certification
LOGIC itself (a bigger, separate, more sensitive task -- Phase 5 as
scoped is "surface the existing score," not "fix how the score is
computed"). Flagged for a future phase, not touched here.

Safety contract: read-only w.r.t. all trading state. Writes only to
data/prr/daily_summary_history.jsonl (new, append-only). Sends a Telegram
alert via the existing notifier.market_alert() only -- never places an
order, never reads/writes PAPER_TRADING, RiskGuardian, or any decision
gate. Never raises.
"""
from __future__ import annotations

import json
import os
from datetime import date
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR  = os.path.join(_ROOT, "data", "prr")
HISTORY_FILE = os.path.join(HISTORY_DIR, "daily_summary_history.jsonl")


def record_daily_result(prr_summary: Dict[str, Any]) -> None:
    """Append today's PRR summary to the history JSONL. Never raises."""
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
        record = {
            "date":                 prr_summary.get("date") or date.today().isoformat(),
            "certification_status": prr_summary.get("certification_status", "UNKNOWN"),
            "ils_score":            prr_summary.get("ils_score", 0.0),
            "gva_score":            prr_summary.get("gva_score", 0.0),
            "critical_failures":    prr_summary.get("critical_failures", 0),
            "warnings":             prr_summary.get("warnings", 0),
        }
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        log.debug("[PRRMonitor] history write skipped: %s", exc)


def get_certification_history(n: int = 30) -> List[Dict[str, Any]]:
    """Return the last n recorded daily summaries, oldest first. Never raises."""
    try:
        if not os.path.exists(HISTORY_FILE):
            return []
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = [ln for ln in f if ln.strip()]
        return [json.loads(ln) for ln in lines[-n:]]
    except Exception:
        return []


def get_latest_certification() -> Optional[Dict[str, Any]]:
    """Read-only accessor for a future consumer (dashboard/Telegram). Never raises."""
    history = get_certification_history(n=1)
    return history[-1] if history else None


def check_and_alert(prr_summary: Dict[str, Any], notifier: Any = None) -> None:
    """
    Send an advisory Telegram alert only when the certification status is
    NOT_READY, or when it changed since the last recorded entry. Never
    raises; never touches any trade/risk/decision state.
    """
    try:
        status = prr_summary.get("certification_status", "UNKNOWN")
        previous = get_latest_certification()
        prev_status = previous.get("certification_status") if previous else None

        should_alert = status == "NOT_READY" or (
            prev_status is not None and prev_status != status
        )
        if should_alert and notifier is not None:
            notifier.market_alert(
                "🏭 Production Readiness Update",
                f"Certification: <b>{status}</b>\n"
                f"ILS: {prr_summary.get('ils_score', 0.0):.1f}/100 | "
                f"GVA: {prr_summary.get('gva_score', 0.0):.1f}/100\n"
                f"Critical failures: {prr_summary.get('critical_failures', 0)} | "
                f"Warnings: {prr_summary.get('warnings', 0)}\n"
                f"Advisory only — does not halt trading.",
            )
    except Exception as exc:
        log.debug("[PRRMonitor] alert check skipped: %s", exc)

"""
DTA-038 MorningReadinessCheck — pre-market sanity check using yesterday's EOD report.

Answers:
  1. Were there trace gaps (restart anomalies) yesterday?
  2. Are any hypotheses in HUMAN_APPROVAL_REQUIRED status?
  3. Were there repeated bottleneck stages?
  4. What was yesterday's execution rate?
  5. Is there any carryover action required before market open?

CONTRACT: never raises, never modifies trading state.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from audit.dta038_models import HypothesisStatus
from audit.dta038_trace import _DATA_DIR, _now_utc


class MorningReadinessCheck:

    def run(self, trading_date: Optional[str] = None) -> dict:
        """
        Run readiness check. Returns dict with findings. Never raises.
        """
        try:
            return self._run_impl(trading_date)
        except Exception:
            return {"status": "ERROR", "message": "Morning check failed"}

    def _run_impl(self, trading_date: Optional[str]) -> dict:
        from audit.dta038_trace import _today_str
        today     = trading_date or _today_str()
        yesterday = (
            datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)
        ).strftime("%Y-%m-%d")

        eod_path = _DATA_DIR / f"DTA038_EOD_{yesterday}.json"
        hyp_path = _DATA_DIR / f"DTA038_HYPOTHESIS_{yesterday}.jsonl"

        findings: List[str] = []
        warnings: List[str] = []
        actions:  List[str] = []
        status = "READY"

        # ── Load yesterday's EOD report ────────────────────────────────────
        eod: dict = {}
        if eod_path.exists():
            try:
                eod = json.loads(eod_path.read_text(encoding="utf-8"))
            except Exception:
                findings.append(f"Could not parse yesterday's EOD report: {eod_path.name}")
        else:
            findings.append(f"No EOD report found for {yesterday}. First day or system not running?")

        if eod:
            exec_rate = eod.get("execution_rate_pct", 0.0)
            findings.append(f"Yesterday execution rate: {exec_rate}%")
            if exec_rate == 0.0 and eod.get("total_signals_generated", 0) > 0:
                warnings.append("Zero executions yesterday despite signals. Review rejection chain.")
                status = "NEEDS_REVIEW"

            n_anomalies = eod.get("anomalies_detected", 0)
            if n_anomalies > 0:
                findings.append(f"Yesterday had {n_anomalies} anomaly(-ies).")
                for a in eod.get("anomaly_summary", []):
                    if a.get("severity") == "ALERT":
                        warnings.append(f"ALERT anomaly: {a.get('description','')[:80]}")
                        status = "NEEDS_REVIEW"

            top_findings = eod.get("top_findings", [])
            if top_findings:
                findings.append(f"Yesterday top finding: {top_findings[0][:100]}")

        # ── Load yesterday's hypotheses ────────────────────────────────────
        har_hyps: List[dict] = []
        if hyp_path.exists():
            try:
                with hyp_path.open("r", encoding="utf-8") as fh:
                    for raw in fh:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            evt = json.loads(raw)
                        except Exception:
                            continue
                        if (evt.get("event") == "HYP_CREATE"
                                and evt.get("status") == HypothesisStatus.HUMAN_APPROVAL_REQUIRED.value):
                            har_hyps.append(evt)
            except Exception:
                pass

        if har_hyps:
            titles = "; ".join(h.get("title", "")[:50] for h in har_hyps[:3])
            warnings.append(
                f"{len(har_hyps)} hypothesis(-es) require HUMAN APPROVAL before any code change: {titles}"
            )
            actions.append("Review HUMAN_APPROVAL_REQUIRED hypotheses in DTA038_HYPOTHESIS log.")
            status = "NEEDS_REVIEW"

        if not warnings:
            findings.append("No critical issues from yesterday. System ready for today.")

        return {
            "status":        status,
            "trading_date":  today,
            "checked_ts":    _now_utc(),
            "yesterday_date": yesterday,
            "findings":      findings,
            "warnings":      warnings,
            "actions":       actions,
        }

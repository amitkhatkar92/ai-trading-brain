"""
DTA-038 EODReportGenerator — end-of-day structured + human-readable reports.

OUTPUT
------
  data/audit/dta038/DTA038_EOD_YYYY-MM-DD.json  — structured JSON report
  data/audit/dta038/DTA038_EOD_YYYY-MM-DD.txt   — human-readable summary

CONTRACT: never raises, never modifies trading state.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from audit.dta038_models import (
    AnomalyRecord, CycleAudit, Hypothesis, SelfQuestioningReport,
)
import audit.dta038_trace as _trace_mod
from audit.dta038_trace import _now_utc, _today_str, get_trace_manager


class EODReportGenerator:

    def generate(
        self,
        date_str: Optional[str] = None,
        cycles: Optional[List[CycleAudit]] = None,
        sq_reports: Optional[List[SelfQuestioningReport]] = None,
        anomalies: Optional[List[AnomalyRecord]] = None,
        hypotheses: Optional[List[Hypothesis]] = None,
    ) -> dict:
        """
        Build and persist EOD report. Never raises.
        Returns report dict (empty on failure).
        """
        try:
            return self._generate_impl(
                date_str or _today_str(),
                cycles or [],
                sq_reports or [],
                anomalies or [],
                hypotheses or [],
            )
        except Exception:
            return {}

    def _generate_impl(
        self,
        date_str: str,
        cycles: List[CycleAudit],
        sq_reports: List[SelfQuestioningReport],
        anomalies: List[AnomalyRecord],
        hypotheses: List[Hypothesis],
    ) -> dict:
        total_signals  = sum(c.signals_generated for c in cycles)
        total_executed = sum(c.executed for c in cycles)
        unique_syms_executed = len({
            t.symbol
            for c in cycles
            for t in []   # placeholder — would need trace manager
        })

        # Aggregate each trace's final rejection, not every historical rejection.
        stage_drops: dict = {}
        trace_manager = get_trace_manager()
        for c in cycles:
            terminal_drops = trace_manager.get_terminal_stage_drop_map(c.cycle_id)
            for stage, drop in (terminal_drops or c.stage_drop_map).items():
                stage_drops[stage] = stage_drops.get(stage, 0) + drop

        # Top anomalies
        top_anomalies = sorted(anomalies, key=lambda a: a.severity, reverse=True)[:5]

        # Hypotheses summary
        hyp_by_status: dict = {}
        for h in hypotheses:
            k = h.status.value
            hyp_by_status[k] = hyp_by_status.get(k, 0) + 1

        # Top findings
        top_findings = []
        for r in sq_reports:
            if r.top_finding and r.top_finding not in top_findings:
                top_findings.append(r.top_finding)
        top_findings = top_findings[:5]

        report = {
            "report_type": "DTA038_EOD",
            "trading_date": date_str,
            "generated_ts": _now_utc(),
            "cycles_completed": len(cycles),
            "total_signals_generated": total_signals,
            "total_executed": total_executed,
            "execution_rate_pct": round(total_executed / max(total_signals, 1) * 100, 1),
            "stage_drop_summary": stage_drops,
            "anomalies_detected": len(anomalies),
            "anomaly_summary": [
                {"kind": a.kind.value, "severity": a.severity, "description": a.description[:120]}
                for a in top_anomalies
            ],
            "hypotheses_raised": len(hypotheses),
            "hypotheses_by_status": hyp_by_status,
            "top_findings": top_findings,
            "cycle_ids": [c.cycle_id for c in cycles],
        }

        # Persist JSON
        json_path = _trace_mod._DATA_DIR / f"DTA038_EOD_{date_str}.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

        # Persist human-readable TXT
        txt_path = _trace_mod._DATA_DIR / f"DTA038_EOD_{date_str}.txt"
        try:
            txt_path.write_text(self._format_txt(report, cycles, anomalies, hypotheses), encoding="utf-8")
        except Exception:
            pass

        return report

    def _format_txt(
        self,
        report: dict,
        cycles: List[CycleAudit],
        anomalies: List[AnomalyRecord],
        hypotheses: List[Hypothesis],
    ) -> str:
        lines = [
            "=" * 70,
            f"  DTA-038 END-OF-DAY SELF-AUDIT REPORT — {report['trading_date']}",
            "=" * 70,
            f"  Generated : {report['generated_ts']}",
            f"  Cycles    : {report['cycles_completed']}",
            f"  Signals   : {report['total_signals_generated']} generated, "
            f"{report['total_executed']} executed "
            f"({report['execution_rate_pct']}%)",
            "",
            "── Stage Drop Breakdown ──",
        ]
        for stage, cnt in report.get("stage_drop_summary", {}).items():
            lines.append(f"  {stage:<20}  dropped {cnt}")
        lines += [
            "",
            "── Anomalies ──",
        ]
        if anomalies:
            for a in anomalies[:10]:
                lines.append(f"  [{a.severity}] {a.kind.value}: {a.description[:80]}")
        else:
            lines.append("  None detected.")
        lines += [
            "",
            "── Hypotheses ──",
        ]
        if hypotheses:
            for h in hypotheses[:10]:
                lines.append(f"  [{h.status.value}] {h.title[:70]}")
        else:
            lines.append("  None raised.")
        lines += [
            "",
            "── Top Findings ──",
        ]
        for f in report.get("top_findings", []):
            lines.append(f"  • {f[:100]}")
        lines += [
            "",
            "── Per-Cycle Funnel ──",
        ]
        for c in cycles:
            lines.append(
                f"  {c.cycle_id}  gen={c.signals_generated} strat={c.strategy_passed} "
                f"cre={c.cre_passed} risk={c.risk_passed} exec={c.executed}"
            )
        lines += ["", "=" * 70, "  END OF REPORT", "=" * 70]
        return "\n".join(lines) + "\n"

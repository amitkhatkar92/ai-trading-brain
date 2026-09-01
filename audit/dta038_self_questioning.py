"""
DTA-038 SelfQuestioningEngine — per-cycle automated Q&A.

Generates structured answers to 8 canonical questions after each cycle:
  Q1  How many signals were generated and what happened to them?
  Q2  Where in the pipeline did most signals die?
  Q3  Were there near-miss threshold events?
  Q4  Did any symbol appear across multiple consecutive rejections?
  Q5  Were all rejections explainable by documented rules?
  Q6  Was the rejection pattern consistent with the stated market regime?
  Q7  Did any passed signal look anomalous (very low score but passed)?
  Q8  What is the highest-conviction signal rejected today and why?

CONTRACT: never raises, never modifies trading state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from audit.dta038_models import (
    CycleAudit, CycleQuestion, SelfQuestioningReport, StageStatus,
)
from audit.dta038_trace import TraceManager, _today_str, _now_utc


_KNOWN_REJECTION_REASONS = {
    "STRATEGY_REJECTED",
    "CRE_QTY_ZERO",
    "RR_BELOW_THRESHOLD",
    "CONFIDENCE_BELOW_THRESHOLD",
    "GUARDIAN_BLOCKED",
    "STABILITY_THRESHOLD",
    "EXPOSURE_LIMIT",
}

_NEAR_MISS_DELTA = 0.3   # confidence within 0.3 of threshold = near-miss


class SelfQuestioningEngine:

    def __init__(self, trace_manager: TraceManager) -> None:
        self._tm = trace_manager

    def generate_cycle_report(
        self, cycle: CycleAudit, effective_threshold: float = 6.5
    ) -> SelfQuestioningReport:
        """
        Run all 8 questions for one completed cycle. Never raises.
        """
        try:
            return self._run(cycle, effective_threshold)
        except Exception:
            return SelfQuestioningReport(
                cycle_id=cycle.cycle_id,
                trading_date=cycle.trading_date,
                generated_ts=_now_utc(),
                top_finding="ERROR_IN_SELF_QUESTIONING",
            )

    def _run(
        self, cycle: CycleAudit, threshold: float
    ) -> SelfQuestioningReport:
        traces  = self._tm.get_today_traces()
        c_traces = [t for t in traces if t.cycle_id == cycle.cycle_id]
        questions: List[CycleQuestion] = []

        # ── Q1: Signal funnel summary ──────────────────────────────────────
        total    = cycle.signals_generated
        executed = cycle.executed
        funnel   = (
            f"Generated={total}, Strategy={cycle.strategy_passed}, "
            f"CRE={cycle.cre_passed}, Risk={cycle.risk_passed}, "
            f"Guardian={cycle.guardian_passed}, DebateIn={cycle.debate_input}, "
            f"Executed={executed}"
        )
        q1 = CycleQuestion(
            question="How many signals were generated and what happened to them?",
            answer=funnel,
            severity="INFO",
        )
        questions.append(q1)

        # ── Q2: Biggest drop stage ─────────────────────────────────────────
        drop = cycle.stage_drop_map
        if drop:
            biggest_stage = max(drop, key=lambda k: drop[k])
            biggest_count = drop[biggest_stage]
            severity = "WARN" if biggest_count > 0 and executed == 0 else "INFO"
            q2 = CycleQuestion(
                question="Where did most signals die?",
                answer=(
                    f"Stage '{biggest_stage}' dropped {biggest_count} signals. "
                    f"Drop breakdown: {drop}"
                ),
                severity=severity,
                tags=[biggest_stage],
            )
        else:
            q2 = CycleQuestion(
                question="Where did most signals die?",
                answer="No drop map available.",
                severity="INFO",
            )
        questions.append(q2)

        # ── Q3: Near-miss threshold events ────────────────────────────────
        near_misses = [
            t for t in c_traces
            if t.stage_status("DEBATE") == StageStatus.REJECTED
            and any(
                abs(s.details.get("confidence_score", 0.0) - threshold) <= _NEAR_MISS_DELTA
                for s in t.stages if s.stage == "DEBATE"
            )
        ]
        if near_misses:
            nm_detail = ", ".join(
                f"{t.symbol}({next((s.details.get('confidence_score', 0) for s in t.stages if s.stage == 'DEBATE'), 0):.2f})"
                for t in near_misses[:5]
            )
            q3 = CycleQuestion(
                question="Were there near-miss threshold events?",
                answer=f"{len(near_misses)} signal(s) within {_NEAR_MISS_DELTA:.1f} of threshold. {nm_detail}",
                severity="WARN" if near_misses else "INFO",
                tags=["NEAR_MISS"],
            )
        else:
            q3 = CycleQuestion(
                question="Were there near-miss threshold events?",
                answer=f"No near-miss events (within {_NEAR_MISS_DELTA:.1f} pts of threshold {threshold:.1f}).",
                severity="INFO",
            )
        questions.append(q3)

        # ── Q4: Repeated symbol rejections across cycles ──────────────────
        all_traces = self._tm.get_today_traces()
        rejection_counts: dict = {}
        for t in all_traces:
            if t.final_outcome and t.final_outcome.startswith("REJECTED"):
                rejection_counts[t.symbol] = rejection_counts.get(t.symbol, 0) + 1
        repeat_syms = {sym: cnt for sym, cnt in rejection_counts.items() if cnt >= 2}
        if repeat_syms:
            detail = ", ".join(f"{s}×{c}" for s, c in sorted(repeat_syms.items(), key=lambda x: -x[1])[:5])
            q4 = CycleQuestion(
                question="Did any symbol appear across multiple consecutive rejections today?",
                answer=f"Repeated rejections: {detail}",
                severity="WARN",
                tags=["REPEATED_REJECTION"],
            )
        else:
            q4 = CycleQuestion(
                question="Did any symbol appear across multiple consecutive rejections today?",
                answer="No symbol rejected in ≥2 cycles today.",
                severity="INFO",
            )
        questions.append(q4)

        # ── Q5: Unexplained rejections ─────────────────────────────────────
        unexplained = [
            t for t in c_traces
            if t.final_outcome and t.final_outcome.startswith("REJECTED")
            and all(
                s.rejection_reason not in _KNOWN_REJECTION_REASONS
                for s in t.stages
                if s.rejection_reason
            )
        ]
        if unexplained:
            syms = ", ".join(t.symbol for t in unexplained[:5])
            q5 = CycleQuestion(
                question="Were all rejections explainable by documented rules?",
                answer=f"{len(unexplained)} rejection(s) with undocumented reason: {syms}",
                severity="WARN",
                tags=["UNEXPLAINED_REJECTION"],
            )
        else:
            q5 = CycleQuestion(
                question="Were all rejections explainable by documented rules?",
                answer="All rejections map to a documented rule.",
                severity="INFO",
            )
        questions.append(q5)

        # ── Q6: Regime consistency ────────────────────────────────────────
        regimes = {t.scanner_regime for t in c_traces if t.scanner_regime}
        regime_note = f"Observed regimes in scanner signals: {sorted(regimes)}"
        q6 = CycleQuestion(
            question="Was the rejection pattern consistent with the stated market regime?",
            answer=f"Cycle regime={cycle.regime}. {regime_note}",
            severity="INFO",
        )
        questions.append(q6)

        # ── Q7: Anomalous passers (low score but executed) ────────────────
        passed_traces = [t for t in c_traces if t.final_outcome == "EXECUTED"]
        anomalous_pass = [
            t for t in passed_traces
            if any(
                s.stage == "DEBATE"
                and s.details.get("confidence_score", 10.0) < threshold + 0.5
                for s in t.stages
            )
        ]
        if anomalous_pass:
            detail = ", ".join(
                f"{t.symbol}({next((s.details.get('confidence_score',0) for s in t.stages if s.stage=='DEBATE'), 0):.2f})"
                for t in anomalous_pass
            )
            q7 = CycleQuestion(
                question="Did any passed signal look anomalous (barely above threshold)?",
                answer=f"{len(anomalous_pass)} signal(s) passed within 0.5 of threshold: {detail}",
                severity="WARN",
                tags=["LOW_MARGIN_PASS"],
            )
        else:
            q7 = CycleQuestion(
                question="Did any passed signal look anomalous (barely above threshold)?",
                answer="No anomalously-thin passes detected.",
                severity="INFO",
            )
        questions.append(q7)

        # ── Q8: Highest-conviction rejected signal ────────────────────────
        rejected_debate = [
            t for t in c_traces
            if t.stage_status("DEBATE") == StageStatus.REJECTED
        ]
        if rejected_debate:
            def _score(t):
                for s in t.stages:
                    if s.stage == "DEBATE":
                        return s.details.get("confidence_score", 0.0)
                return 0.0
            best = max(rejected_debate, key=_score)
            best_score = _score(best)
            reason = next(
                (s.rejection_reason for s in best.stages if s.stage == "DEBATE" and s.rejection_reason),
                "UNKNOWN"
            )
            q8 = CycleQuestion(
                question="What is the highest-conviction signal rejected today and why?",
                answer=f"{best.symbol} {best.direction} score={best_score:.2f} reason={reason}",
                severity="WARN" if best_score >= threshold - 0.5 else "INFO",
                tags=["HIGHEST_CONVICTION_REJECT"],
            )
        elif rejected_debate is not None and cycle.signals_generated == 0:
            q8 = CycleQuestion(
                question="What is the highest-conviction signal rejected today and why?",
                answer="No signals generated this cycle.",
                severity="INFO",
            )
        else:
            q8 = CycleQuestion(
                question="What is the highest-conviction signal rejected today and why?",
                answer="No signals reached debate stage.",
                severity="INFO",
            )
        questions.append(q8)

        # ── Top finding ───────────────────────────────────────────────────
        alerts = [q for q in questions if q.severity == "ALERT"]
        warns  = [q for q in questions if q.severity == "WARN"]
        if alerts:
            top_finding = alerts[0].answer
        elif warns:
            top_finding = warns[0].answer
        else:
            top_finding = f"Healthy cycle. Executed={executed}/{total} signals."

        return SelfQuestioningReport(
            cycle_id=cycle.cycle_id,
            trading_date=cycle.trading_date,
            generated_ts=_now_utc(),
            questions=questions,
            anomalies_detected=0,
            hypotheses_raised=0,
            top_finding=top_finding,
        )

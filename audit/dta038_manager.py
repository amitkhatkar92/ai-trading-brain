"""
DTA-038 DTA038Manager — top-level facade for the self-audit layer.

Provides a clean, safe entry point used by the orchestrator at:
  • cycle start
  • cycle end
  • EOD

CONTRACT: all public methods never raise.
"""
from __future__ import annotations

from dataclasses import replace
from typing import List, Optional

from audit.dta038_trace import TraceManager, get_trace_manager, _today_str, _now_utc
from audit.dta038_models import CycleAudit
from audit.dta038_self_questioning import SelfQuestioningEngine
from audit.dta038_anomaly import AnomalyDetector
from audit.dta038_hypothesis import HypothesisEngine
from audit.dta038_eod_report import EODReportGenerator
from audit.dta038_morning_check import MorningReadinessCheck
from utils import get_logger

log = get_logger(__name__)


class DTA038Manager:
    """
    Process-level facade for DTA-038.
    Instantiate once; call methods from master_orchestrator at the documented hooks.
    """

    def __init__(self, trace_manager: Optional[TraceManager] = None) -> None:
        self._tm   = trace_manager or get_trace_manager()
        self._sq   = SelfQuestioningEngine(self._tm)
        self._anom = AnomalyDetector(self._tm)
        self._hyp  = HypothesisEngine()
        self._eod  = EODReportGenerator()
        self._morn = MorningReadinessCheck()

    # ── Cycle hooks ────────────────────────────────────────────────────────

    def on_cycle_start(
        self, cycle_id: str, regime: str = "", vix: float = 0.0
    ) -> None:
        """Call at the START of every run_full_cycle_inner(). Never raises."""
        try:
            self._tm.set_cycle_id(cycle_id)
            self._tm.record_cycle_start(regime=regime, vix=vix)
            log.debug("[DTA038] Cycle start recorded: %s", cycle_id)
        except Exception as exc:
            log.debug("[DTA038] on_cycle_start error: %s", exc)

    def on_cycle_end(
        self,
        signals_generated: int = 0,
        strategy_passed: int = 0,
        cre_passed: int = 0,
        risk_passed: int = 0,
        guardian_passed: int = 0,
        debate_input: int = 0,
        executed: int = 0,
        effective_threshold: float = 6.5,
    ) -> None:
        """
        Call at the END of every run_full_cycle_inner() (including early returns).
        Runs anomaly detection and self-questioning.
        """
        try:
            self._tm.record_cycle_end(
                signals_generated=signals_generated,
                strategy_passed=strategy_passed,
                cre_passed=cre_passed,
                risk_passed=risk_passed,
                guardian_passed=guardian_passed,
                debate_input=debate_input,
                executed=executed,
            )
            # Retrieve the cycle just closed
            cid    = self._tm.get_cycle_id()
            cycles = self._tm.get_today_cycles()
            cycle  = next((c for c in cycles if c.cycle_id == cid), None)
            if cycle is None:
                return
            # Preserve raw stage events; reports use the final outcome per trace.
            report_cycle = replace(
                cycle,
                stage_drop_map=self._tm.get_terminal_stage_drop_map(cid),
            )

            # Anomaly detection
            anomalies = self._anom.detect(report_cycle)
            if anomalies:
                log.info("[DTA038] %d anomaly(-ies) detected in cycle %s", len(anomalies), cid)
                for a in anomalies:
                    log.info("[DTA038][Anomaly] %s: %s", a.kind.value, a.description)
                    # Raise hypothesis for each anomaly
                    hyp = self._hyp.raise_from_anomaly(a)
                    if hyp:
                        log.info("[DTA038][Hypothesis] Raised: %s [%s]", hyp.title[:60], hyp.hyp_id)

            # Self-questioning
            sq = self._sq.generate_cycle_report(report_cycle, effective_threshold)
            log.info("[DTA038][SelfQ] Cycle=%s | %s", cid, sq.top_finding)
            for q in sq.questions:
                if q.severity in ("WARN", "ALERT"):
                    log.info("[DTA038][Q] [%s] %s → %s", q.severity, q.question, q.answer)

        except Exception as exc:
            log.debug("[DTA038] on_cycle_end error: %s", exc)

    # ── EOD ────────────────────────────────────────────────────────────────

    def generate_eod_report(self, date_str: Optional[str] = None) -> dict:
        """Generate and persist EOD report. Call from _do_eod_learning(). Never raises."""
        try:
            ds       = date_str or _today_str()
            cycles   = self._tm.get_today_cycles()
            anomalies = self._tm.get_anomalies()
            hyps     = self._hyp.get_today_hypotheses()
            report   = self._eod.generate(
                date_str=ds,
                cycles=cycles,
                anomalies=anomalies,
                hypotheses=hyps,
            )
            if report:
                log.info(
                    "[DTA038][EOD] Report generated: cycles=%d signals=%d executed=%d anomalies=%d hyps=%d",
                    report.get("cycles_completed", 0),
                    report.get("total_signals_generated", 0),
                    report.get("total_executed", 0),
                    report.get("anomalies_detected", 0),
                    report.get("hypotheses_raised", 0),
                )
            return report
        except Exception as exc:
            log.debug("[DTA038] generate_eod_report error: %s", exc)
            return {}

    # ── Morning check ──────────────────────────────────────────────────────

    def run_morning_check(self, trading_date: Optional[str] = None) -> dict:
        """Run pre-market readiness check. Call from _do_pre_market_init(). Never raises."""
        try:
            result = self._morn.run(trading_date)
            status = result.get("status", "UNKNOWN")
            log.info("[DTA038][Morning] Status=%s", status)
            for w in result.get("warnings", []):
                log.warning("[DTA038][Morning] %s", w)
            for a in result.get("actions", []):
                log.info("[DTA038][Morning] ACTION: %s", a)
            return result
        except Exception as exc:
            log.debug("[DTA038] run_morning_check error: %s", exc)
            return {}


# ── Module-level singleton ──────────────────────────────────────────────────

import threading as _threading

_MGR_INSTANCE: Optional[DTA038Manager] = None
_MGR_LOCK = _threading.Lock()


def get_dta038_manager() -> DTA038Manager:
    global _MGR_INSTANCE
    if _MGR_INSTANCE is not None:
        return _MGR_INSTANCE
    with _MGR_LOCK:
        if _MGR_INSTANCE is None:
            _MGR_INSTANCE = DTA038Manager()
    return _MGR_INSTANCE

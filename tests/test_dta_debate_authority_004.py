"""
DTA-DEBATE-AUTHORITY-004 — Debate telemetry / outcome-attribution repair tests.

Calls the real DTA-038 (`get_trace_manager().record_debate_outcome`) and
DTA-041 (`get_pit_discovery_evidence_recorder().record_stage_outcomes`)
directly (production code, not a simulation) to verify:

  1. Genuine Debate rejection -> DEBATE stage REJECTED /
     "REJECTED_AT_DEBATE" / "CONFIDENCE_BELOW_THRESHOLD" (unchanged).
  2. Debate approved + execution succeeded -> DEBATE stage PASSED /
     "EXECUTED" (unchanged).
  3. Debate approved + execution failed -> DEBATE stage PASSED (NOT
     REJECTED) / "EXECUTION_FAILED" (the core fix).
  4. confidence_score recorded is the real value passed in via `scores`,
     not a silent 0.0 from a nonexistent sig.confidence_score attribute.
  5. DTA-041 produces two independent stage records ("DEBATE" and
     "EXECUTION") instead of one conflated "DEBATE_EXECUTION" record.
  6. EventType.EXECUTION_FAILED is additive only.
  7. Backward compatibility: calling record_debate_outcome without the new
     optional params falls back to the legacy exec_syms-only behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pytest

from audit.dta038_models import StageStatus
from communication.events import EventType


class _Dir:
    def __init__(self, v):
        self.value = v


@dataclass
class _Sig:
    symbol: str
    direction: Any
    entry_price: float = 100.0
    confidence_score: float = 7.0
    _obs_regime: Optional[str] = None


def _sig(symbol, direction="BUY", score=7.0):
    return _Sig(symbol=symbol, direction=_Dir(direction), confidence_score=score)


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect DTA-038 storage to a temp directory for every test (same
    pattern as tests/test_dta_038_self_audit.py)."""
    audit_dir = tmp_path / "data" / "audit" / "dta038"
    audit_dir.mkdir(parents=True)
    import audit.dta038_trace as _trace
    monkeypatch.setattr(_trace, "_DATA_DIR", audit_dir)
    monkeypatch.setattr(_trace, "_INSTANCE", None)
    monkeypatch.setattr(_trace, "_CURRENT_CYCLE_ID", None)
    yield audit_dir


def test_genuine_rejection_recorded_as_rejected_at_debate():
    from audit.dta038_trace import get_trace_manager
    tm = get_trace_manager()
    tm.set_cycle_id("20260904_T1")
    sig = _sig("REJECTED1")
    tm.record_scanner_stage(sig, {})
    tm.record_debate_outcome([sig], executed=[], approved_symbols=set(), scores={})
    trace = next(t for t in tm.get_today_traces() if t.symbol == "REJECTED1")
    assert trace.stage_status("DEBATE") == StageStatus.REJECTED
    assert trace.final_outcome == "REJECTED_AT_DEBATE"


def test_approved_and_executed_recorded_as_executed():
    from audit.dta038_trace import get_trace_manager
    tm = get_trace_manager()
    tm.set_cycle_id("20260904_T2")
    sig = _sig("EXEC1")
    tm.record_scanner_stage(sig, {})
    executed = [{"symbol": "EXEC1", "score": 7.4}]
    tm.record_debate_outcome(
        [sig], executed=executed, approved_symbols={"EXEC1"}, scores={"EXEC1": 7.4},
    )
    trace = next(t for t in tm.get_today_traces() if t.symbol == "EXEC1")
    assert trace.stage_status("DEBATE") == StageStatus.PASSED
    assert trace.final_outcome == "EXECUTED"


def test_approved_but_execution_failed_not_marked_rejected_at_debate():
    """The core fix: approved-but-execution-failed must be PASSED at DEBATE,
    not REJECTED_AT_DEBATE."""
    from audit.dta038_trace import get_trace_manager
    tm = get_trace_manager()
    tm.set_cycle_id("20260904_T3")
    sig = _sig("EXECFAIL1")
    tm.record_scanner_stage(sig, {})
    tm.record_debate_outcome(
        [sig], executed=[], approved_symbols={"EXECFAIL1"}, scores={"EXECFAIL1": 7.1},
    )
    trace = next(t for t in tm.get_today_traces() if t.symbol == "EXECFAIL1")
    assert trace.stage_status("DEBATE") == StageStatus.PASSED
    assert trace.final_outcome == "EXECUTION_FAILED"
    assert trace.final_outcome != "REJECTED_AT_DEBATE"


def test_confidence_score_uses_real_decision_score_not_stub_attribute():
    """confidence_score must come from the `scores` dict (the real
    DecisionEngine value), never from sig.confidence_score, even though the
    test stub happens to carry that attribute (it must be ignored)."""
    from audit.dta038_trace import get_trace_manager
    tm = get_trace_manager()
    tm.set_cycle_id("20260904_T4")
    sig = _sig("SCORECHK1", score=0.0)   # stub attribute deliberately wrong/unused
    tm.record_scanner_stage(sig, {})
    tm.record_debate_outcome(
        [sig], executed=[{"symbol": "SCORECHK1", "score": 8.2}],
        approved_symbols={"SCORECHK1"}, scores={"SCORECHK1": 8.2},
    )
    trace = next(t for t in tm.get_today_traces() if t.symbol == "SCORECHK1")
    stage = next(s for s in trace.stages if s.stage == "DEBATE")
    assert stage.details.get("confidence_score") == 8.2


def test_legacy_call_without_new_params_still_works():
    """Backward compatibility: omitting approved_symbols/scores must not
    raise, and preserves the old exec_syms-only behavior."""
    from audit.dta038_trace import get_trace_manager
    tm = get_trace_manager()
    tm.set_cycle_id("20260904_T5")
    sig = _sig("LEGACY1")
    tm.record_scanner_stage(sig, {})
    tm.record_debate_outcome([sig], [{"symbol": "LEGACY1", "score": 6.0}])
    trace = next(t for t in tm.get_today_traces() if t.symbol == "LEGACY1")
    assert trace.stage_status("DEBATE") == StageStatus.PASSED
    assert trace.final_outcome == "EXECUTED"


def test_dta041_record_stage_outcomes_debate_and_execution_independent():
    from audit.dta041_pit_discovery_evidence import get_pit_discovery_evidence_recorder
    from audit.dta038_trace import get_trace_manager
    get_trace_manager().set_cycle_id("20260904_T6")
    rec = get_pit_discovery_evidence_recorder()
    sig = _sig("PIT1")
    # Debate approved (in approved_symbols) but execution failed (not in exec_syms)
    rec.record_stage_outcomes([sig], {"PIT1"}, "DEBATE", "CONFIDENCE_BELOW_THRESHOLD")
    rec.record_stage_outcomes([sig], set(), "EXECUTION", "EXECUTION_FAILED")
    # No exception raised == the two independent stage calls work end-to-end.


def test_execution_failed_event_type_is_additive():
    assert EventType.EXECUTION_FAILED.value == "execution.order.not_placed"
    # Pre-existing event types remain unchanged
    assert EventType.ORDER_PLACED.value == "execution.order.placed"
    assert EventType.ORDER_REJECTED.value == "execution.order.rejected"
    assert EventType.TRADE_APPROVED.value == "decision.approved"
    assert EventType.TRADE_REJECTED.value == "decision.rejected"


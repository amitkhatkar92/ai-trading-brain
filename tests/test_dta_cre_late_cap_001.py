"""
tests/test_dta_cre_late_cap_001.py
=============================================
DTA-CRE-LATE-CAP-001

User-identified architectural issue: the real MAX_POSITIONS cap used to be
enforced by CapitalRiskEngine at Step 3.5 -- BEFORE RiskControl, Market
Simulation, RiskGuardian, and Debate/KDA ever evaluated a candidate. That
meant a genuinely strong signal could be pruned early (on CRE's cheap,
pre-Debate score) while a weaker one that happened to rank higher at that
early stage consumed a slot, only to fail a later gate anyway -- wasting
the very capacity the cap was meant to protect.

Fix: CapitalRiskEngine's own cutoff is now a widened, capacity-agnostic
"evaluation pool" (see test_dta_cre_real_position_cap_001.py) -- a compute-
cost guard only. The REAL cap is enforced exactly once, in
orchestrator/master_orchestrator.py's run_full_cycle() STEP 6, AFTER every
signal that survived RiskControl/Simulation/RiskGuardian/Correlation has
been evaluated by Debate/KDA -- ranked by each signal's own final
decision.confidence_score, so the best-scored candidates get the
available slots first.

This file unit-tests the pure ranking/splitting helper,
_rank_and_split_by_position_cap(), directly -- no orchestrator, no real
signals/broker calls needed.
"""
from __future__ import annotations

from types import SimpleNamespace

from orchestrator.master_orchestrator import _rank_and_split_by_position_cap


def _decision(score: float):
    return SimpleNamespace(confidence_score=score)


def _row(symbol: str, score: float):
    return (SimpleNamespace(symbol=symbol), _decision(score), [])


def test_t01_empty_input_returns_empty():
    to_exec, capped = _rank_and_split_by_position_cap([], open_positions=0, max_positions=5)
    assert to_exec == [] and capped == []


def test_t02_fewer_approved_than_available_slots_all_execute():
    rows = [_row("A", 9.0), _row("B", 7.5)]
    to_exec, capped = _rank_and_split_by_position_cap(rows, open_positions=0, max_positions=5)
    assert len(to_exec) == 2 and capped == []


def test_t03_more_approved_than_slots_ranks_by_confidence_score():
    rows = [_row("LOW", 6.6), _row("HIGH", 9.5), _row("MID", 7.8)]
    to_exec, capped = _rank_and_split_by_position_cap(rows, open_positions=0, max_positions=2)
    assert [r[0].symbol for r in to_exec] == ["HIGH", "MID"]
    assert [r[0].symbol for r in capped] == ["LOW"]


def test_t04_open_positions_reduce_available_slots():
    rows = [_row("A", 9.0), _row("B", 8.0), _row("C", 7.0)]
    # 3 open, max 5 -> only 2 slots available this cycle
    to_exec, capped = _rank_and_split_by_position_cap(rows, open_positions=3, max_positions=5)
    assert [r[0].symbol for r in to_exec] == ["A", "B"]
    assert [r[0].symbol for r in capped] == ["C"]


def test_t05_already_at_or_over_cap_executes_nothing():
    rows = [_row("A", 9.0), _row("B", 8.0)]
    to_exec, capped = _rank_and_split_by_position_cap(rows, open_positions=5, max_positions=5)
    assert to_exec == []
    assert len(capped) == 2


def test_t06_over_cap_open_positions_never_goes_negative_available():
    """open_positions > max_positions must not somehow "free up" slots via
    a negative-available bug."""
    rows = [_row("A", 9.0)]
    to_exec, capped = _rank_and_split_by_position_cap(rows, open_positions=8, max_positions=5)
    assert to_exec == []
    assert len(capped) == 1


def test_t07_disabled_bypasses_cap_entirely():
    """enabled=False (emergency rollback) must execute every approved
    signal, regardless of open positions -- restores pre-fix behavior."""
    rows = [_row("A", 9.0), _row("B", 8.0), _row("C", 7.0)]
    to_exec, capped = _rank_and_split_by_position_cap(
        rows, open_positions=5, max_positions=5, enabled=False,
    )
    assert len(to_exec) == 3
    assert capped == []


def test_t08_never_mutates_input_list():
    rows = [_row("A", 9.0), _row("B", 8.0), _row("C", 7.0)]
    original = list(rows)
    _rank_and_split_by_position_cap(rows, open_positions=0, max_positions=1)
    assert rows == original


def test_t09_tie_scores_preserve_relative_order_stably():
    """Python's sort is stable -- equal scores keep their original
    relative order rather than being shuffled."""
    rows = [_row("FIRST", 8.0), _row("SECOND", 8.0), _row("THIRD", 8.0)]
    to_exec, capped = _rank_and_split_by_position_cap(rows, open_positions=0, max_positions=2)
    assert [r[0].symbol for r in to_exec] == ["FIRST", "SECOND"]
    assert [r[0].symbol for r in capped] == ["THIRD"]

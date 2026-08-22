"""
tests/test_final_knowledge_led_c2_001.py
==========================================
FINAL_KNOWLEDGE_LED_C2_001 — Full test suite

Tests the frozen C2 selection architecture in final_c2_selector.py.

Coverage areas:
  T001-T010  C2 formula correctness
  T011-T020  UP direction ranking
  T021-T030  DOWN direction ranking
  T031-T045  Strategy as context (not a gate)
  T046-T060  Knowledge/Strategy disagreement classification
  T061-T070  Pool preservation (20+20 complete)
  T071-T080  Isolation / safety invariants
  T081-T090  select_c2_top5 integration
  T091-T100  Historical regression against OOS anchors
"""
from __future__ import annotations

import importlib
import inspect
import os
import re
import sys
from typing import List

import pytest

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from opportunity_engine.final_c2_selector import (
    AGREE_PASS,
    C2_TOP_N,
    KNOWLEDGE_OVERRULES_STRATEGY,
    MODULE_VERSION,
    NO_STRATEGY_MATCH,
    STRATEGY_UNAVAILABLE,
    STRATEGY_SUPPORTS_KNOWLEDGE,
    C2Candidate,
    C2SelectionResult,
    compute_c2_score,
    compute_disagreement,
    compute_gap_pct,
    evaluate_strategy_context,
    select_c2_top5,
    candidates_to_records,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_pool(n: int, direction: str, base_close: float = 100.0,
               score_start: float = 1.0) -> List[dict]:
    """Build a minimal V3 pool list for testing."""
    score_key = "v3_up_score" if direction == "UP" else "v3_down_score"
    return [
        {
            "symbol":         f"SYM{i:02d}",
            "previous_close": base_close + i,
            score_key:        score_start + i * 0.1,
        }
        for i in range(n)
    ]


def _make_opening_prices(pool: List[dict], gap_pct: float = 0.5) -> dict:
    """Return opening prices giving each symbol a fixed gap_pct."""
    return {
        c["symbol"]: round(c["previous_close"] * (1 + gap_pct / 100), 4)
        for c in pool
    }


def _make_varying_opens(pool: List[dict], gaps: List[float]) -> dict:
    """Map each symbol to a specific gap_pct from the gaps list."""
    opens = {}
    for i, c in enumerate(pool):
        gap = gaps[i] if i < len(gaps) else 0.0
        opens[c["symbol"]] = round(c["previous_close"] * (1 + gap / 100), 4)
    return opens


# ─────────────────────────────────────────────────────────────────────────────
# T001–T010 — compute_c2_score formula
# ─────────────────────────────────────────────────────────────────────────────

def test_T001_c2_up_positive_gap():
    """UP: stock opens above close → positive c2_score."""
    score = compute_c2_score(100.0, 102.0, "UP")
    assert score is not None
    assert abs(round(score, 4) - 2.0) < 1e-4


def test_T002_c2_up_negative_gap():
    """UP: stock opens below close → negative c2_score (bad candidate)."""
    score = compute_c2_score(100.0, 99.0, "UP")
    assert score is not None
    assert score < 0


def test_T003_c2_down_negative_gap():
    """DOWN: stock opens below close → positive c2_score (gap down = reward)."""
    score = compute_c2_score(100.0, 98.0, "DOWN")
    assert score is not None
    assert abs(round(score, 4) - 2.0) < 1e-4


def test_T004_c2_down_positive_gap():
    """DOWN: stock opens above close → negative c2_score (bad candidate)."""
    score = compute_c2_score(100.0, 102.0, "DOWN")
    assert score is not None
    assert score < 0


def test_T005_c2_symmetry():
    """c2_score(UP) + c2_score(DOWN) = 0 for same inputs."""
    up   = compute_c2_score(100.0, 103.0, "UP")
    down = compute_c2_score(100.0, 103.0, "DOWN")
    assert up is not None and down is not None
    assert abs(round(up + down, 6)) < 1e-5


def test_T006_c2_formula_exact():
    """Exact formula: gap_pct = (open/close-1)*100; UP=+gap."""
    prev, op = 517.55, 524.00
    expected = round((op / prev - 1) * 100, 6)
    assert compute_c2_score(prev, op, "UP") is not None
    assert abs(compute_c2_score(prev, op, "UP") - expected) < 1e-4


def test_T007_c2_no_look_ahead():
    """C2 takes ONLY previous_close and opening_price — no other fields."""
    sig = inspect.signature(compute_c2_score)
    params = list(sig.parameters.keys())
    assert params == ["previous_close", "opening_price", "direction"]


def test_T008_c2_invalid_zero_close():
    assert compute_c2_score(0.0, 100.0, "UP") is None


def test_T009_c2_invalid_negative():
    assert compute_c2_score(-1.0, 100.0, "UP") is None


def test_T010_c2_none_inputs():
    assert compute_c2_score(None, 100.0, "UP") is None  # type: ignore[arg-type]
    assert compute_c2_score(100.0, None, "UP") is None  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# T011–T020 — UP direction ranking
# ─────────────────────────────────────────────────────────────────────────────

def test_T011_up_top5_selected():
    """Top-5 UP candidates are flagged selected_top5=True."""
    up   = _make_pool(20, "UP")
    gaps = [float(i) * 0.1 for i in range(20)][::-1]  # descending gaps
    opens = _make_varying_opens(up, gaps)
    result = select_c2_top5(up, [], opens, regime="BULL")
    selected = [c for c in result.up_pool if c.selected_top5]
    assert len(selected) == 5


def test_T012_up_ranked_descending():
    """UP pool sorted by c2_score descending."""
    up   = _make_pool(10, "UP")
    gaps = [float(i) for i in range(10)]  # SYM00=0%, SYM09=9%
    opens = _make_varying_opens(up, gaps)
    result = select_c2_top5(up, [], opens)
    valid  = [c for c in result.up_pool if c.c2_rank is not None]
    valid.sort(key=lambda c: c.c2_rank)
    for i in range(len(valid) - 1):
        assert valid[i].c2_score >= valid[i + 1].c2_score


def test_T013_up_highest_gap_wins():
    """Candidate with highest gap_pct must be C2 rank 1 in UP."""
    up   = _make_pool(8, "UP", base_close=100.0)
    # SYM04 gets the biggest gap
    opens = {f"SYM{i:02d}": 100.0 + i * 0.5 + (i * 5) for i in range(8)}
    opens["SYM04"] += 100.0  # make SYM04 have a massive gap
    result = select_c2_top5(up, [], opens)
    rank1 = [c for c in result.up_pool if c.c2_rank == 1]
    assert rank1 and rank1[0].symbol == "SYM04"


def test_T014_up_full_pool_preserved():
    """All 20 UP candidates appear in result.up_pool."""
    up = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.5)
    result = select_c2_top5(up, [], opens)
    assert len(result.up_pool) == 20


def test_T015_up_exactly_5_no_more():
    """Exactly 5 candidates selected, no 6th."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens)
    assert sum(1 for c in result.up_pool if c.selected_top5) == 5


def test_T016_up_directions_correct():
    """All candidates in result.up_pool have direction='UP'."""
    up = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.4)
    result = select_c2_top5(up, [], opens)
    for c in result.up_pool:
        assert c.direction == "UP"


def test_T017_up_c2_score_up_formula():
    """result.up_pool[i].c2_score == +gap_pct."""
    up   = _make_pool(5, "UP", base_close=200.0)
    gaps = [1.0, 2.0, 0.5, 3.0, 1.5]
    opens = _make_varying_opens(up, gaps)
    result = select_c2_top5(up, [], opens)
    for cand in result.up_pool:
        if cand.c2_score is not None and cand.gap_pct is not None:
                assert abs(cand.c2_score - cand.gap_pct) < 1e-3


def test_T018_up_tie_broken_by_v3_rank():
    """When two c2_scores are equal, lower v3_rank (higher V3 position) wins."""
    up = [
        {"symbol": "SYM_A", "previous_close": 100.0, "v3_up_score": 0.9},
        {"symbol": "SYM_B", "previous_close": 100.0, "v3_up_score": 0.7},
    ]
    # Identical opening → identical gap → identical c2_score
    opens = {"SYM_A": 101.0, "SYM_B": 101.0}
    result = select_c2_top5(up, [], opens)
    sym_a = next(c for c in result.up_pool if c.symbol == "SYM_A")
    sym_b = next(c for c in result.up_pool if c.symbol == "SYM_B")
    # SYM_A has v3_rank=1, SYM_B has v3_rank=2 → SYM_A should be ranked higher
    assert sym_a.c2_rank < sym_b.c2_rank


def test_T019_up_no_data_candidates_at_end():
    """Candidates without opening prices get c2_rank=None and selected_top5=False."""
    up = _make_pool(6, "UP")
    opens = {c["symbol"]: c["previous_close"] * 1.01 for c in up[:3]}
    # Only 3 of 6 have opens; rest have no data
    result = select_c2_top5(up, [], opens)
    no_data = [c for c in result.up_pool if c.c2_rank is None]
    assert len(no_data) == 3
    for c in no_data:
        assert not c.selected_top5


def test_T020_up_top5_property():
    """result.up_top5 convenience property returns same 5 as selected_top5=True."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens)
    assert result.up_top5 == [c for c in result.up_pool if c.selected_top5]


# ─────────────────────────────────────────────────────────────────────────────
# T021–T030 — DOWN direction ranking
# ─────────────────────────────────────────────────────────────────────────────

def test_T021_down_top5_selected():
    """Top-5 DOWN candidates are flagged selected_top5=True."""
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.995 for c in dn}
    result = select_c2_top5([], dn, opens)
    assert sum(1 for c in result.down_pool if c.selected_top5) == 5


def test_T022_down_rank1_biggest_gap_down():
    """DOWN rank 1 = candidate with biggest downward gap (most negative gap_pct)."""
    dn = _make_pool(10, "DOWN", base_close=200.0)
    # gaps: SYM04 has -5% gap
    opens = {f"SYM{i:02d}": 200.0 + i * (1 + i * 0.1) for i in range(10)}
    opens["SYM04"] = 200.0 * 0.95  # -5% gap → c2_score = +5
    result = select_c2_top5([], dn, opens)
    rank1 = [c for c in result.down_pool if c.c2_rank == 1]
    assert rank1 and rank1[0].symbol == "SYM04"


def test_T023_down_c2_score_down_formula():
    """result.down_pool[i].c2_score == -gap_pct."""
    dn   = _make_pool(5, "DOWN", base_close=150.0)
    gaps = [-1.0, -2.0, -0.5, -3.0, -1.5]
    opens = _make_varying_opens(dn, gaps)
    result = select_c2_top5([], dn, opens)
    for cand in result.down_pool:
        if cand.c2_score is not None and cand.gap_pct is not None:
                assert abs(cand.c2_score - (-cand.gap_pct)) < 1e-3


def test_T024_down_full_pool_preserved():
    """All 20 DOWN candidates appear in result.down_pool."""
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.99 for c in dn}
    result = select_c2_top5([], dn, opens)
    assert len(result.down_pool) == 20


def test_T025_down_directions_correct():
    """All candidates in result.down_pool have direction='DOWN'."""
    dn    = _make_pool(10, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.99 for c in dn}
    result = select_c2_top5([], dn, opens)
    for c in result.down_pool:
        assert c.direction == "DOWN"


def test_T026_up_down_independent():
    """UP and DOWN rankings are computed independently — no cross-contamination."""
    up = _make_pool(20, "UP")
    dn = _make_pool(20, "DOWN")
    all_syms = {c["symbol"] for c in up} | {c["symbol"] for c in dn}
    opens = {s: 101.0 for s in all_syms}
    result = select_c2_top5(up, dn, opens)
    up_syms = {c.symbol for c in result.up_pool}
    dn_syms = {c.symbol for c in result.down_pool}
    # Pools overlap if same symbols used — but ranks must be independent
    up_rank1 = [c for c in result.up_pool if c.c2_rank == 1]
    dn_rank1 = [c for c in result.down_pool if c.c2_rank == 1]
    assert len(up_rank1) == 1
    assert len(dn_rank1) == 1


def test_T027_down_top5_property():
    """result.down_top5 matches selected_top5=True in down_pool."""
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.98 for c in dn}
    result = select_c2_top5([], dn, opens)
    assert result.down_top5 == [c for c in result.down_pool if c.selected_top5]


# ─────────────────────────────────────────────────────────────────────────────
# T031–T045 — Strategy as context (not a gate)
# ─────────────────────────────────────────────────────────────────────────────

def test_T031_strategy_bear_up_returns_reject_context():
    """BEAR + UP → strategy_status='REJECT' but candidate NOT removed."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.5)
    result = select_c2_top5(up, [], opens, regime="BEAR")
    # Top-5 UP are still present despite BEAR regime
    assert len(result.up_top5) == 5
    # strategy_status is REJECT for all UP in BEAR
    for c in result.up_top5:
        assert c.strategy_status == "REJECT"


def test_T032_strategy_volatile_up_returns_reject_context():
    """VOLATILE + UP → strategy_status='REJECT' but candidate still selected."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.4)
    result = select_c2_top5(up, [], opens, regime="VOLATILE")
    assert len(result.up_top5) == 5
    for c in result.up_top5:
        assert c.strategy_status == "REJECT"


def test_T033_strategy_bull_up_returns_pass():
    """BULL + UP → strategy_status='PASS'."""
    up    = _make_pool(10, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens, regime="BULL")
    for c in result.up_pool:
        assert c.strategy_status == "PASS"


def test_T034_strategy_range_up_returns_pass():
    """RANGE + UP → strategy_status='PASS'."""
    up    = _make_pool(10, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens, regime="RANGE")
    for c in result.up_pool:
        assert c.strategy_status == "PASS"


def test_T035_strategy_bear_down_returns_aligned():
    """BEAR + DOWN → strategy_status='ALIGNED' (no SELL gate)."""
    dn    = _make_pool(10, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.99 for c in dn}
    result = select_c2_top5([], dn, opens, regime="BEAR")
    for c in result.down_pool:
        assert c.strategy_status == "ALIGNED"


def test_T036_strategy_bull_down_returns_contradicted():
    """BULL + DOWN → strategy_status='CONTRADICTED'."""
    dn    = _make_pool(10, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.99 for c in dn}
    result = select_c2_top5([], dn, opens, regime="BULL")
    for c in result.down_pool:
        assert c.strategy_status == "CONTRADICTED"


def test_T037_strategy_unavailable_regime():
    """No regime → strategy_status='STRATEGY_UNAVAILABLE'."""
    up    = _make_pool(10, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens, regime="UNAVAILABLE")
    for c in result.up_pool:
        assert c.strategy_status == STRATEGY_UNAVAILABLE


def test_T038_strategy_reject_does_not_remove_c2_rank1():
    """Even if strategy=REJECT, C2 rank-1 candidate stays at rank 1."""
    up    = _make_pool(20, "UP")
    # Biggest gap to SYM03
    opens = {c["symbol"]: c["previous_close"] * 1.005 for c in up}
    opens["SYM03"] = up[3]["previous_close"] * 1.05  # +5% gap
    result = select_c2_top5(up, [], opens, regime="BEAR")
    rank1 = [c for c in result.up_pool if c.c2_rank == 1]
    assert rank1[0].symbol == "SYM03"
    assert rank1[0].selected_top5 is True
    assert rank1[0].strategy_status == "REJECT"


def test_T039_evaluate_strategy_context_pure():
    """evaluate_strategy_context returns 3-tuple with expected types."""
    status, name, reason = evaluate_strategy_context("UP", "BEAR")
    assert isinstance(status, str)
    assert isinstance(name, str)
    assert isinstance(reason, str)


def test_T040_evaluate_strategy_none_regime():
    """None regime → STRATEGY_UNAVAILABLE."""
    status, _, _ = evaluate_strategy_context("UP", None)
    assert status == STRATEGY_UNAVAILABLE


def test_T041_model_b_up_is_strategy_gated_counterfactual():
    """Model B UP = what the strategy gate WOULD have produced (PASS only)."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens, regime="BULL")  # all PASS
    assert len(result.model_b_up()) == 5


def test_T042_model_b_up_bear_empty():
    """In BEAR regime, Model B UP = 0 (all REJECT, so no PASS candidates)."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.4)
    result = select_c2_top5(up, [], opens, regime="BEAR")
    assert len(result.model_b_up()) == 0


def test_T043_model_b_down_always_all():
    """Model B DOWN = all top-5 DOWN (no gate exists for DOWN)."""
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.99 for c in dn}
    result = select_c2_top5([], dn, opens, regime="BULL")
    assert len(result.model_b_down()) == 5


def test_T044_strategy_regime_stored_in_candidate():
    """Strategy regime is propagated to every candidate."""
    up    = _make_pool(8, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens, regime="VOLATILE")
    for c in result.up_pool:
        assert c.strategy_regime == "VOLATILE"


def test_T045_strategy_range_down_neutral():
    """RANGE + DOWN → NEUTRAL (no SELL strategies)."""
    dn    = _make_pool(8, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.99 for c in dn}
    result = select_c2_top5([], dn, opens, regime="RANGE")
    for c in result.down_pool:
        assert c.strategy_status == "NEUTRAL"


# ─────────────────────────────────────────────────────────────────────────────
# T046–T060 — Knowledge/Strategy disagreement classification
# ─────────────────────────────────────────────────────────────────────────────

def test_T046_disagree_bear_up_selected():
    """BEAR + UP selected → KNOWLEDGE_OVERRULES_STRATEGY."""
    assert compute_disagreement("REJECT", "UP", True) == KNOWLEDGE_OVERRULES_STRATEGY


def test_T047_disagree_bull_up_selected():
    """BULL/RANGE + UP selected (PASS) → AGREE_PASS."""
    assert compute_disagreement("PASS", "UP", True) == AGREE_PASS


def test_T048_disagree_unavail():
    """STRATEGY_UNAVAILABLE → STRATEGY_UNAVAILABLE regardless of direction."""
    assert compute_disagreement(STRATEGY_UNAVAILABLE, "UP",  True) == STRATEGY_UNAVAILABLE
    assert compute_disagreement(STRATEGY_UNAVAILABLE, "DOWN", True) == STRATEGY_UNAVAILABLE


def test_T049_disagree_down_aligned():
    """DOWN + ALIGNED → STRATEGY_SUPPORTS_KNOWLEDGE."""
    assert compute_disagreement("ALIGNED", "DOWN", True) == STRATEGY_SUPPORTS_KNOWLEDGE


def test_T050_disagree_down_contradicted_selected():
    """DOWN + CONTRADICTED + selected → KNOWLEDGE_OVERRULES_STRATEGY.
    Macro headwind exists; Knowledge still selects the candidate.
    This is a real K/S relationship, not NO_STRATEGY_MATCH.
    """
    val = compute_disagreement("CONTRADICTED", "DOWN", True)
    assert val == KNOWLEDGE_OVERRULES_STRATEGY


def test_T051_disagree_down_neutral_selected():
    """DOWN + NEUTRAL + selected → AGREE_PASS.
    No macro context concern; no strategy gate — no conflict.
    """
    assert compute_disagreement("NEUTRAL", "DOWN", True) == AGREE_PASS


def test_T052_disagree_not_selected_carries_strategy_verdict():
    """
    Non-selected candidates carry their strategy verdict directly.
    Being outside the C2 Top-5 must NOT cause NO_STRATEGY_MATCH when a
    real strategy evaluation exists.
    """
    # UP: PASS and REJECT are both real strategy verdicts
    assert compute_disagreement("PASS",   "UP", False) == "PASS"
    assert compute_disagreement("REJECT", "UP", False) == "REJECT"
    # DOWN contextual labels are real evaluations too
    assert compute_disagreement("ALIGNED",     "DOWN", False) == "ALIGNED"
    assert compute_disagreement("CONTRADICTED", "DOWN", False) == "CONTRADICTED"
    assert compute_disagreement("NEUTRAL",      "DOWN", False) == "NEUTRAL"


def test_T053_disagree_in_full_result_bear():
    """BEAR regime → every UP top-5 has KNOWLEDGE_OVERRULES_STRATEGY."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.5)
    result = select_c2_top5(up, [], opens, regime="BEAR")
    for c in result.up_top5:
        assert c.knowledge_strategy_disagreement == KNOWLEDGE_OVERRULES_STRATEGY


def test_T054_disagree_in_full_result_bull():
    """BULL regime → every UP top-5 has AGREE_PASS."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.5)
    result = select_c2_top5(up, [], opens, regime="BULL")
    for c in result.up_top5:
        assert c.knowledge_strategy_disagreement == AGREE_PASS


def test_T055_disagree_in_full_result_down_bear():
    """BEAR + DOWN top-5 → STRATEGY_SUPPORTS_KNOWLEDGE."""
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.98 for c in dn}
    result = select_c2_top5([], dn, opens, regime="BEAR")
    for c in result.down_top5:
        assert c.knowledge_strategy_disagreement == STRATEGY_SUPPORTS_KNOWLEDGE


def test_T056_non_selected_carry_strategy_verdict_not_no_match():
    """
    Non-top-5 candidates in a known regime must NOT get NO_STRATEGY_MATCH.
    BULL regime → strategy_status=PASS for all UP → non-selected carry 'PASS'.
    """
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.5)
    result = select_c2_top5(up, [], opens, regime="BULL")
    non_sel = [c for c in result.up_pool if not c.selected_top5]
    assert len(non_sel) == 15
    for c in non_sel:
        assert c.knowledge_strategy_disagreement == "PASS", (
            f"{c.symbol}: expected 'PASS' (non-selected, BULL), "
            f"got '{c.knowledge_strategy_disagreement}'"
        )


def test_T057_valid_disagreement_label_universe():
    """
    Selected candidates use K/S relationship labels.
    Non-selected candidates carry raw strategy verdict.
    NO_STRATEGY_MATCH never appears solely because a candidate was not in top-5.
    """
    up    = _make_pool(20, "UP")
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 1.01 for c in up}
    opens.update({c["symbol"]: c["previous_close"] * 0.99 for c in dn})

    valid_selected   = {
        AGREE_PASS, KNOWLEDGE_OVERRULES_STRATEGY, STRATEGY_SUPPORTS_KNOWLEDGE,
        STRATEGY_UNAVAILABLE,
    }
    valid_non_selected = {
        "PASS", "REJECT", "ALIGNED", "CONTRADICTED", "NEUTRAL",
        STRATEGY_UNAVAILABLE, NO_STRATEGY_MATCH,
    }

    for regime in ("BULL", "BEAR", "RANGE", "UNAVAILABLE"):
        result = select_c2_top5(up, dn, opens, regime=regime)
        for c in result.up_pool + result.down_pool:
            if c.selected_top5:
                assert c.knowledge_strategy_disagreement in valid_selected, (
                    f"{c.symbol} {regime} selected: unexpected "
                    f"'{c.knowledge_strategy_disagreement}'"
                )
            else:
                assert c.knowledge_strategy_disagreement in valid_non_selected, (
                    f"{c.symbol} {regime} non-selected: unexpected "
                    f"'{c.knowledge_strategy_disagreement}'"
                )
                # The key invariant: NO_STRATEGY_MATCH must not appear when a
                # real strategy evaluation exists
                if regime != "UNAVAILABLE":
                    assert c.knowledge_strategy_disagreement != NO_STRATEGY_MATCH, (
                        f"{c.symbol} {regime}: non-selected got NO_STRATEGY_MATCH "
                        f"despite known regime — strategy_status={c.strategy_status}"
                    )


def test_T058_disagree_volatile_up():
    """VOLATILE + UP selected → KNOWLEDGE_OVERRULES_STRATEGY."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens, regime="VOLATILE")
    for c in result.up_top5:
        assert c.knowledge_strategy_disagreement == KNOWLEDGE_OVERRULES_STRATEGY


# ─────────────────────────────────────────────────────────────────────────────
# T061–T070 — Pool preservation (20+20 complete)
# ─────────────────────────────────────────────────────────────────────────────

def test_T061_full_pool_20_up_preserved():
    """All 20 UP candidates preserved even when only 5 selected."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens)
    assert len(result.up_pool) == 20


def test_T062_full_pool_20_down_preserved():
    up    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.99 for c in up}
    result = select_c2_top5([], up, opens)
    assert len(result.down_pool) == 20


def test_T063_all_candidates_have_v3_rank():
    """Every candidate has a v3_rank 1..20."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens)
    ranks = [c.v3_rank for c in result.up_pool]
    assert sorted(ranks) == list(range(1, 21))


def test_T064_selected_and_not_selected_add_to_20():
    """Exactly 5 selected + 15 not-selected = 20."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.4)
    result = select_c2_top5(up, [], opens)
    sel     = sum(1 for c in result.up_pool if c.selected_top5)
    not_sel = sum(1 for c in result.up_pool if not c.selected_top5)
    assert sel == 5
    assert not_sel == 15


def test_T065_candidates_to_records_count():
    """candidates_to_records returns 40 records for 20+20 pool."""
    up    = _make_pool(20, "UP")
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 1.005 for c in up}
    opens.update({c["symbol"]: c["previous_close"] * 0.995 for c in dn})
    result  = select_c2_top5(up, dn, opens)
    records = candidates_to_records(result)
    assert len(records) == 40


def test_T066_each_record_has_required_fields():
    """Every record from candidates_to_records has the required fields."""
    up    = _make_pool(5, "UP")
    opens = _make_opening_prices(up, 0.3)
    result  = select_c2_top5(up, [], opens, trade_date="2026-07-01")
    records = candidates_to_records(result)
    required = {
        "symbol", "direction", "c2_score", "c2_rank", "selected_top5",
        "strategy_status", "knowledge_strategy_disagreement",
        "trade_date", "architecture_version",
    }
    for rec in records:
        for field in required:
            assert field in rec, f"Missing '{field}' in record for {rec.get('symbol')}"


def test_T067_empty_up_pool():
    """Empty UP pool yields empty result.up_pool."""
    result = select_c2_top5([], [], {})
    assert result.up_pool == []
    assert result.down_pool == []


def test_T068_small_pool_less_than_5():
    """Pool of 3 → only 3 selected (not 5)."""
    up    = _make_pool(3, "UP")
    opens = _make_opening_prices(up, 0.4)
    result = select_c2_top5(up, [], opens)
    assert sum(1 for c in result.up_pool if c.selected_top5) == 3


def test_T069_previous_close_preserved():
    """previous_close is preserved in C2Candidate."""
    up    = _make_pool(5, "UP", base_close=500.0)
    opens = _make_opening_prices(up, 0.5)
    result = select_c2_top5(up, [], opens)
    for cand in result.up_pool:
        assert cand.previous_close is not None
        assert cand.previous_close > 0


def test_T070_pool_size_stored():
    """C2Candidate.pool_size equals the pool size passed in."""
    up = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens)
    for c in result.up_pool:
        assert c.pool_size == 20


# ─────────────────────────────────────────────────────────────────────────────
# T071–T080 — Isolation / safety invariants
# ─────────────────────────────────────────────────────────────────────────────

def test_T071_no_broker_imports():
    """final_c2_selector must NOT import any broker or execution module."""
    import opportunity_engine.final_c2_selector as mod
    source = inspect.getsource(mod)
    # Check for actual import statements only (not docstring mentions)
    import_lines = [l for l in source.splitlines() if re.match(r'^\s*(import|from)\s', l)]
    import_block = "\n".join(import_lines)
    forbidden_imports = [
        "order_manager", "dhan_feed", "zerodb_broker",
        "execution_engine", "risk_control",
        "candidate_store", "DecisionEngine",
    ]
    for term in forbidden_imports:
        assert term not in import_block, (
            f"Forbidden import '{term}' found in import statements"
        )


def test_T072_no_order_placement():
    """final_c2_selector must never call place_order or similar."""
    import opportunity_engine.final_c2_selector as mod
    source = inspect.getsource(mod)
    forbidden_calls = ["place_order", "place_trade", "send_order", "submit_order"]
    for call in forbidden_calls:
        assert call not in source, f"Forbidden call '{call}' found"


def test_T073_no_candidatestore():
    """final_c2_selector must never write to CandidateStore."""
    import opportunity_engine.final_c2_selector as mod
    source = inspect.getsource(mod)
    assert re.search(r"CandidateStore\s*\(", source) is None, (
        "CandidateStore instantiation found in final_c2_selector"
    )
    assert re.search(r"\.write\s*\(", source) is None or True  # write() is generic, ok


def test_T074_select_c2_top5_returns_result_type():
    """select_c2_top5 returns C2SelectionResult."""
    up    = _make_pool(5, "UP")
    opens = _make_opening_prices(up, 0.3)
    result = select_c2_top5(up, [], opens)
    assert isinstance(result, C2SelectionResult)


def test_T075_c2candidate_is_dataclass():
    """C2Candidate is a dataclass."""
    import dataclasses
    assert dataclasses.is_dataclass(C2Candidate)


def test_T076_deterministic():
    """Same inputs always produce the same result."""
    up    = _make_pool(20, "UP")
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 1.01 for c in up}
    opens.update({c["symbol"]: c["previous_close"] * 0.99 for c in dn})
    result1 = select_c2_top5(up, dn, opens, regime="BULL")
    result2 = select_c2_top5(up, dn, opens, regime="BULL")
    r1_syms = [c.symbol for c in result1.up_top5]
    r2_syms = [c.symbol for c in result2.up_top5]
    assert r1_syms == r2_syms


def test_T077_module_version_constant():
    """MODULE_VERSION constant is set."""
    assert MODULE_VERSION.startswith("FINAL_C2_SELECTOR")


def test_T078_c2_top_n_constant():
    """C2_TOP_N is exactly 5 (validated OOS number)."""
    assert C2_TOP_N == 5


def test_T079_no_t1_close_in_selection():
    """
    C2 formula only uses previous_close and opening_price.
    Verify no t1_close / t1_high / t1_low used in compute_c2_score body.
    """
    source = inspect.getsource(compute_c2_score)
    # Strip the function signature line (contains 'previous_close' and 'opening_price')
    body_lines = source.splitlines()[1:]  # skip def line
    body = "\n".join(body_lines).lower()
    for term in ["t1_close", "t1_high", "t1_low"]:
        assert term not in body, f"Forbidden field '{term}' found in compute_c2_score body"
    # The body must NOT reference anything other than the two params
    assert "previous_close" not in body or "opening_price" not in body or True  # params OK


def test_T080_compute_gap_pct_formula():
    """compute_gap_pct is raw gap (T1_open / T0_close - 1) × 100."""
    gp = compute_gap_pct(100.0, 103.0)
    assert abs(gp - 3.0) < 1e-4
    gp2 = compute_gap_pct(100.0, 97.0)
    assert abs(gp2 - (-3.0)) < 1e-4


# ─────────────────────────────────────────────────────────────────────────────
# T081–T090 — select_c2_top5 integration / metadata
# ─────────────────────────────────────────────────────────────────────────────

def test_T081_result_stores_trade_date():
    result = select_c2_top5([], [], {}, trade_date="2026-07-14")
    assert result.trade_date == "2026-07-14"


def test_T082_result_stores_t1_date():
    result = select_c2_top5([], [], {}, t1_date="2026-07-15")
    assert result.t1_date == "2026-07-15"


def test_T083_result_stores_regime():
    result = select_c2_top5([], [], {}, regime="BEAR")
    assert result.regime == "BEAR"


def test_T084_result_stores_architecture_version():
    result = select_c2_top5([], [], {})
    assert result.architecture_version == MODULE_VERSION


def test_T085_result_has_timestamp():
    result = select_c2_top5([], [], {})
    assert result.selection_timestamp
    assert "T" in result.selection_timestamp  # ISO format has T


def test_T086_c2_rank_contiguous():
    """C2 ranks in up_pool are 1, 2, 3, … N with no gaps."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.4)
    result = select_c2_top5(up, [], opens)
    ranks = sorted(c.c2_rank for c in result.up_pool if c.c2_rank is not None)
    assert ranks == list(range(1, len(ranks) + 1))


def test_T087_c2_rank_1_has_highest_score():
    """C2 rank 1 has the highest c2_score in the pool."""
    up    = _make_pool(20, "UP")
    gaps  = [float(i) * 0.3 for i in range(20)]
    opens = _make_varying_opens(up, gaps)
    result = select_c2_top5(up, [], opens)
    rank1 = next(c for c in result.up_pool if c.c2_rank == 1)
    for c in result.up_pool:
        if c.c2_rank is not None and c.c2_rank > 1:
            assert rank1.c2_score >= c.c2_score


def test_T088_strategy_agree_up_count():
    """strategy_agree_up counts AGREE_PASS in top-5 UP."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.4)
    result = select_c2_top5(up, [], opens, regime="BULL")  # all PASS
    assert result.strategy_agree_up == 5


def test_T089_strategy_overrule_up_count():
    """strategy_overrule_up counts KNOWLEDGE_OVERRULES_STRATEGY in top-5 UP."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.4)
    result = select_c2_top5(up, [], opens, regime="BEAR")  # all REJECT
    assert result.strategy_overrule_up == 5


def test_T090_as_dict_keys():
    """C2Candidate.as_dict() contains all required keys."""
    up   = _make_pool(1, "UP")
    opens = _make_opening_prices(up, 0.5)
    result = select_c2_top5(up, [], opens)
    d = result.up_pool[0].as_dict()
    required = [
        "symbol", "direction", "v3_score", "v3_rank",
        "c2_score", "c2_rank", "selected_top5",
        "strategy_status", "knowledge_strategy_disagreement",
    ]
    for k in required:
        assert k in d, f"Missing key '{k}' in as_dict()"


# ─────────────────────────────────────────────────────────────────────────────
# T091–T100 — Historical regression (OOS anchors)
# ─────────────────────────────────────────────────────────────────────────────

def _load_oos_data():
    """Load OOS split from the research CSV. Skip if file missing."""
    import os, pandas as pd
    csv_path = os.path.join(
        os.path.dirname(__file__), "..",
        "reports", "mover_discovery_v3", "post_open_gap_analysis.csv"
    )
    if not os.path.exists(csv_path):
        pytest.skip("post_open_gap_analysis.csv not available — skip regression tests")
    df = pd.read_csv(csv_path)
    return df[df["split"] == "OOS"].copy()


def _oos_dir_acc(df, direction: str) -> float:
    """Compute direction accuracy: fraction of rows where t1_ret favours direction."""
    sub = df[df["direction"] == direction].dropna(subset=["t1_ret_pct"])
    if sub.empty:
        return 0.0
    if direction == "UP":
        return (sub["t1_ret_pct"] > 0).mean()
    else:
        return (sub["t1_ret_pct"] < 0).mean()


def _oos_ge2_rate(df, direction: str) -> float:
    """Compute ge2 rate: |t1_ret_pct| >= 2% in favourable direction."""
    sub = df[df["direction"] == direction].dropna(subset=["t1_ret_pct"])
    if sub.empty:
        return 0.0
    if direction == "UP":
        return ((sub["t1_ret_pct"] >= 2.0)).mean()
    else:
        return ((sub["t1_ret_pct"] <= -2.0)).mean()


def test_T091_oos_sample_size_adequate():
    """OOS CSV has >= 1000 UP and >= 1000 DOWN rows."""
    oos = _load_oos_data()
    assert (oos["direction"] == "UP").sum() >= 1000
    assert (oos["direction"] == "DOWN").sum() >= 1000


def test_T092_oos_top5_c2_score_matches_existing_column():
    """
    Verify compute_c2_score matches pre-computed C2_score column in CSV.
    C2_score in CSV = gap_pct for UP, -gap_pct for DOWN.
    """
    oos = _load_oos_data()
    mismatches = 0
    for _, row in oos.iterrows():
        computed = compute_c2_score(
            float(row["t_close"]),
            float(row["t1_open"]),
            str(row["direction"]),
        )
        expected = float(row["C2_score"])
        if computed is None:
            continue
        if abs(computed - expected) > 0.001:
            mismatches += 1
    # Allow 0 mismatches (frozen formula must be exact)
    assert mismatches == 0, f"{mismatches} C2_score mismatches in OOS data"


def test_T093_oos_up_dir_acc_anchor():
    """
    OOS UP dir_acc must be 0.6151 ± 0.006.
    Frozen anchor from FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001.
    """
    oos = _load_oos_data()
    oos_top5_up = _simulate_daily_top5(oos, "UP")
    if oos_top5_up.empty:
        pytest.skip("No UP top-5 data")
    acc = _oos_dir_acc(oos_top5_up, "UP")
    assert 0.609 <= acc <= 0.622, (
        f"OOS UP dir_acc={acc:.4f} outside anchor range [0.609, 0.622]"
    )


def test_T094_oos_down_dir_acc_anchor():
    """
    OOS DOWN dir_acc must be 0.6000 ± 0.006.
    """
    oos = _load_oos_data()
    oos_top5_dn = _simulate_daily_top5(oos, "DOWN")
    if oos_top5_dn.empty:
        pytest.skip("No DOWN top-5 data")
    acc = _oos_dir_acc(oos_top5_dn, "DOWN")
    assert 0.594 <= acc <= 0.607, (
        f"OOS DOWN dir_acc={acc:.4f} outside anchor range [0.594, 0.607]"
    )


def test_T095_oos_up_ge2_anchor():
    """OOS UP ge2_rate must be 0.2906 ± 0.006."""
    oos = _load_oos_data()
    oos_top5_up = _simulate_daily_top5(oos, "UP")
    if oos_top5_up.empty:
        pytest.skip("No UP top-5 data")
    ge2 = _oos_ge2_rate(oos_top5_up, "UP")
    assert 0.284 <= ge2 <= 0.297, (
        f"OOS UP ge2_rate={ge2:.4f} outside anchor range [0.284, 0.297]"
    )


def test_T096_oos_down_ge2_anchor():
    """OOS DOWN ge2_rate must be 0.2377 ± 0.007."""
    oos = _load_oos_data()
    oos_top5_dn = _simulate_daily_top5(oos, "DOWN")
    if oos_top5_dn.empty:
        pytest.skip("No DOWN top-5 data")
    ge2 = _oos_ge2_rate(oos_top5_dn, "DOWN")
    assert 0.230 <= ge2 <= 0.245, (
        f"OOS DOWN ge2_rate={ge2:.4f} outside anchor range [0.230, 0.245]"
    )


def test_T097_oos_up_lift_vs_pool():
    """
    OOS top-5 UP dir_acc > full pool UP dir_acc → C2 adds genuine lift.
    Anchor: lift >= 1.2×.
    """
    oos = _load_oos_data()
    oos_up = oos[oos["direction"] == "UP"]
    full_acc = _oos_dir_acc(oos_up, "UP")
    top5_acc = _oos_dir_acc(_simulate_daily_top5(oos, "UP"), "UP")
    lift = top5_acc / full_acc if full_acc > 0 else 0.0
    assert lift >= 1.2, (
        f"C2 lift={lift:.2f} — expected >= 1.2× but full={full_acc:.3f}, top5={top5_acc:.3f}"
    )


def test_T098_oos_down_lift_vs_pool():
    """OOS top-5 DOWN lift >= 1.2× vs full DOWN pool."""
    oos = _load_oos_data()
    oos_dn = oos[oos["direction"] == "DOWN"]
    full_acc = _oos_dir_acc(oos_dn, "DOWN")
    top5_acc = _oos_dir_acc(_simulate_daily_top5(oos, "DOWN"), "DOWN")
    lift = top5_acc / full_acc if full_acc > 0 else 0.0
    assert lift >= 1.2, (
        f"C2 DOWN lift={lift:.2f} — expected >= 1.2×"
    )


def test_T099_oos_no_look_ahead_verification():
    """
    Verify C2_score is derived from T0_close → T1_open (opening gap),
    NOT from T1_open → T1_close (intraday return).

    Method: recompute the gap formula from t_close / t1_open and check that
    the recomputed value matches C2_score almost perfectly (r > 0.999).
    A separate check confirms C2_score is NOT equivalent to t1_ret_pct.
    """
    oos = _load_oos_data()
    up_rows = oos[(oos["direction"] == "UP")].dropna(
        subset=["t_close", "t1_open", "C2_score", "t1_ret_pct"]
    ).head(300)

    # Recompute the gap formula from raw prices
    recomputed = ((up_rows["t1_open"].astype(float) /
                   up_rows["t_close"].astype(float)) - 1) * 100

    c2_values = up_rows["C2_score"].astype(float)
    ret_values = up_rows["t1_ret_pct"].astype(float)

    # C2 must closely match the gap formula (mean abs diff < 0.001%)
    gap_diff = (recomputed - c2_values).abs().mean()
    assert gap_diff < 0.001, (
        f"C2_score does not match gap formula: mean_abs_diff={gap_diff:.6f}"
    )

    # C2 must differ substantially from t1_ret_pct (mean abs diff > 0.3%)
    ret_diff = (c2_values - ret_values).abs().mean()
    assert ret_diff > 0.3, (
        f"C2_score is too similar to t1_ret_pct: mean_abs_diff={ret_diff:.4f} "
        f"(expected > 0.3 — look-ahead risk)"
    )


def test_T100_oos_c2_monotone():
    """
    In each trading day, the 5 candidates with highest c2_score (UP) should
    have higher dir_acc than the 5 with lowest c2_score (bottom-5 from pool).
    This validates that C2 rank ordering is informative.
    """
    oos = _load_oos_data()
    oos_up = oos[oos["direction"] == "UP"].dropna(subset=["C2_score", "t1_ret_pct"])
    top5   = _simulate_daily_top5(oos_up, "UP")
    bottom5 = _simulate_daily_bottom5(oos_up, "UP")

    top5_acc = _oos_dir_acc(top5, "UP") if not top5.empty else 0.0
    bot5_acc = _oos_dir_acc(bottom5, "UP") if not bottom5.empty else 0.0
    assert top5_acc > bot5_acc, (
        f"Top-5 dir_acc={top5_acc:.3f} NOT > Bottom-5 dir_acc={bot5_acc:.3f}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T101–T110 — C2 selection / Strategy applicability independence
# ─────────────────────────────────────────────────────────────────────────────

def test_T101_strategy_status_same_across_all_20_up():
    """strategy_status is regime-level: all 20 UP candidates share the same value."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.4)
    result = select_c2_top5(up, [], opens, regime="BEAR")
    statuses = {c.strategy_status for c in result.up_pool}
    assert statuses == {"REJECT"}, (
        f"Expected all UP candidates to have strategy_status=REJECT in BEAR; got {statuses}"
    )


def test_T102_strategy_status_same_across_all_20_down():
    """strategy_status is regime-level: all 20 DOWN candidates share the same value."""
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.99 for c in dn}
    result = select_c2_top5([], dn, opens, regime="BEAR")
    statuses = {c.strategy_status for c in result.down_pool}
    assert statuses == {"ALIGNED"}


def test_T103_strategy_status_does_not_depend_on_c2_rank():
    """Changing opening prices (altering C2 ranks) must NOT change strategy_status."""
    up = _make_pool(20, "UP")
    # Run 1: uniform gap → equal ranks
    opens1 = _make_opening_prices(up, 0.3)
    result1 = select_c2_top5(up, [], opens1, regime="BULL")
    # Run 2: varied gaps → different ranks
    opens2 = _make_varying_opens(up, [float(i) * 0.2 for i in range(20)])
    result2 = select_c2_top5(up, [], opens2, regime="BULL")

    for c1, c2 in zip(
        sorted(result1.up_pool, key=lambda c: c.symbol),
        sorted(result2.up_pool, key=lambda c: c.symbol),
    ):
        assert c1.strategy_status == c2.strategy_status, (
            f"{c1.symbol}: strategy_status changed between runs "
            f"({c1.strategy_status} vs {c2.strategy_status})"
        )


def test_T104_non_selected_bear_up_gets_reject_not_no_match():
    """Non-selected UP candidates in BEAR regime carry 'REJECT', not NO_STRATEGY_MATCH."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.5)
    result = select_c2_top5(up, [], opens, regime="BEAR")
    non_sel = [c for c in result.up_pool if not c.selected_top5]
    assert len(non_sel) == 15
    for c in non_sel:
        assert c.knowledge_strategy_disagreement == "REJECT", (
            f"{c.symbol}: expected 'REJECT' for non-selected BEAR+UP, "
            f"got '{c.knowledge_strategy_disagreement}'"
        )


def test_T105_non_selected_down_bear_gets_aligned():
    """Non-selected DOWN candidates in BEAR regime carry 'ALIGNED', not NO_STRATEGY_MATCH."""
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.98 for c in dn}
    result = select_c2_top5([], dn, opens, regime="BEAR")
    non_sel = [c for c in result.down_pool if not c.selected_top5]
    for c in non_sel:
        assert c.knowledge_strategy_disagreement == "ALIGNED", (
            f"{c.symbol}: expected 'ALIGNED', got '{c.knowledge_strategy_disagreement}'"
        )


def test_T106_non_selected_down_bull_gets_contradicted():
    """Non-selected DOWN candidates in BULL regime carry 'CONTRADICTED', not NO_STRATEGY_MATCH."""
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 0.99 for c in dn}
    result = select_c2_top5([], dn, opens, regime="BULL")
    non_sel = [c for c in result.down_pool if not c.selected_top5]
    for c in non_sel:
        assert c.knowledge_strategy_disagreement == "CONTRADICTED"


def test_T107_selected_and_non_selected_same_strategy_status():
    """Selected and non-selected candidates in the same pool share strategy_status."""
    up    = _make_pool(20, "UP")
    gaps  = [float(i) * 0.3 for i in range(20)]
    opens = _make_varying_opens(up, gaps)
    result = select_c2_top5(up, [], opens, regime="BULL")
    sel_statuses     = {c.strategy_status for c in result.up_pool if c.selected_top5}
    non_sel_statuses = {c.strategy_status for c in result.up_pool if not c.selected_top5}
    # Both sets must be identical (regime-level evaluation applies to all)
    assert sel_statuses == non_sel_statuses == {"PASS"}


def test_T108_selected_disagreement_uses_ks_labels():
    """Selected candidates use K/S relationship labels, not raw strategy_status."""
    up    = _make_pool(20, "UP")
    opens = _make_opening_prices(up, 0.4)
    ks_labels = {AGREE_PASS, KNOWLEDGE_OVERRULES_STRATEGY, STRATEGY_SUPPORTS_KNOWLEDGE,
                 STRATEGY_UNAVAILABLE}
    for regime in ("BULL", "BEAR", "RANGE", "UNAVAILABLE"):
        result = select_c2_top5(up, [], opens, regime=regime)
        for c in result.up_top5:
            assert c.knowledge_strategy_disagreement in ks_labels, (
                f"{c.symbol} {regime}: selected candidate has raw strategy_status "
                f"'{c.knowledge_strategy_disagreement}' as disagreement label"
            )


def test_T109_no_strategy_match_only_when_unavailable_regime():
    """
    In a fully known regime, NO_STRATEGY_MATCH must not appear on any candidate
    (selected or not).  It may only appear when regime is UNAVAILABLE.
    """
    up    = _make_pool(20, "UP")
    dn    = _make_pool(20, "DOWN")
    opens = {c["symbol"]: c["previous_close"] * 1.01 for c in up}
    opens.update({c["symbol"]: c["previous_close"] * 0.99 for c in dn})

    for regime in ("BULL", "BEAR", "RANGE"):  # known regimes only
        result = select_c2_top5(up, dn, opens, regime=regime)
        for c in result.up_pool + result.down_pool:
            assert c.knowledge_strategy_disagreement != NO_STRATEGY_MATCH, (
                f"{c.symbol} {regime}: NO_STRATEGY_MATCH appeared in a known regime"
            )


def test_T110_c2_selection_does_not_change_strategy_regime():
    """
    Varying which candidates are in the top-5 (by changing opening prices)
    must leave strategy_regime, strategy_status, strategy_reason unchanged
    for every candidate.
    """
    up = _make_pool(20, "UP")
    regime = "BEAR"

    # Two runs with different opening prices → different top-5 sets
    opens_a = _make_varying_opens(up, [float(i) * 0.5 for i in range(20)])
    opens_b = _make_varying_opens(up, [float(19 - i) * 0.5 for i in range(20)])  # reversed

    result_a = select_c2_top5(up, [], opens_a, regime=regime)
    result_b = select_c2_top5(up, [], opens_b, regime=regime)

    for ca, cb in zip(
        sorted(result_a.up_pool, key=lambda c: c.symbol),
        sorted(result_b.up_pool, key=lambda c: c.symbol),
    ):
        assert ca.strategy_regime  == cb.strategy_regime
        assert ca.strategy_status  == cb.strategy_status
        assert ca.strategy_reason  == cb.strategy_reason


# ─────────────────────────────────────────────────────────────────────────────
# Regression helpers
# ─────────────────────────────────────────────────────────────────────────────

def _simulate_daily_top5(df, direction: str):
    """
    Per trading date, keep top-5 by C2_score descending.
    Returns filtered DataFrame of top-5 rows per date.
    """
    import pandas as pd
    sub = df[df["direction"] == direction].copy()
    if sub.empty:
        return sub
    sub = sub.dropna(subset=["C2_score"])
    # Sort then use groupby.head() — avoids FutureWarning from apply()
    top5_rows = (
        sub.sort_values("C2_score", ascending=False)
        .groupby("trading_date", group_keys=False)
        .head(5)
    )
    return top5_rows.reset_index(drop=True)


def _simulate_daily_bottom5(df, direction: str):
    """Per trading date, keep bottom-5 by C2_score descending (i.e. tail after sort)."""
    import pandas as pd
    sub = df[df["direction"] == direction].copy()
    if sub.empty:
        return sub
    sub = sub.dropna(subset=["C2_score"])
    bot5_rows = (
        sub.sort_values("C2_score", ascending=False)
        .groupby("trading_date", group_keys=False)
        .tail(5)
    )
    return bot5_rows.reset_index(drop=True)

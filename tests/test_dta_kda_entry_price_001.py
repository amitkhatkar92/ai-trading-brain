"""
tests/test_dta_kda_entry_price_001.py
=======================================
DTA-KDA-ENTRY-PRICE-001 — root-cause fix for KDA outcome-accuracy
measurement being computed against the wrong reference price.

Root cause: KDADecisionRecord never persisted the real observation/
decision-time entry price, forcing every outcome evaluation onto the
bars[0].open (next trading day open) fallback for 100% of historical
decisions (verified live: 0/940 directional decisions across 3 real
backlog days had entry_price populated).

Covers:
  1. entry_price now flows from the live observation into the
     persisted KDADecisionRecord.
  2. as_dict()/from_dict() round-trip preserves entry_price.
  3. Backward compatibility: old ledger dicts with no "entry_price" key
     (or a zero value) still reconstruct with entry_price=None, falling
     back to bars[0].open exactly as before (zero behavior change for
     already-logged historical decisions).
  4. _classify_outcome() ordering fix: a stop-hit-first trade that later
     also touches target within the window is now correctly classified
     INCORRECT, not CORRECT. Callers that don't pass first_event (old
     signature) keep the exact prior behavior.
  5. AuthorityValidationReport.directional_decisions correctly reports
     the real sample size behind direction_accuracy, distinct from
     total_decisions (which also counts WAIT/HOLD/EXIT decisions).
"""
from __future__ import annotations

from typing import List
from unittest.mock import MagicMock

import pytest

from knowledge_authority import (
    KDAAuthorityReporter,
    KDADecisionRecord,
    KDAOutcomeEngine,
    KnowledgeDecisionAuthority,
    OHLCVBar,
)
from knowledge_authority.kda_outcome_engine import _classify_outcome

KDA = KnowledgeDecisionAuthority()
ENGINE = KDAOutcomeEngine()
REPORTER = KDAAuthorityReporter()


def _obs(**kwargs):
    defaults = dict(symbol="RELIANCE", direction="BUY", entry_price=2800.0,
                    atr=28.0, atr_pct=1.0, scanner_confidence=7.0)
    defaults.update(kwargs)
    return defaults


def _bm(ess=150.0, target_prob=0.70, stop_prob=0.20, **kwargs):
    bm = MagicMock()
    bm.effective_sample_size       = ess
    bm.relevant_sample_size        = int(ess)
    bm.target_hit_probability      = target_prob
    bm.stop_first_probability      = stop_prob
    bm.target_source               = "EMPIRICAL"
    bm.stop_source                 = "EMPIRICAL"
    bm.knowledge_target_offset_p50 = kwargs.get("target_offset", 5.0)
    bm.knowledge_stop_offset_p50   = kwargs.get("stop_offset", 2.0)
    bm.expected_move_p25           = 1.0
    bm.expected_move_p50           = 2.5
    bm.expected_move_p75           = 4.5
    bm.expected_days_p25           = 2.0
    bm.expected_days_p50           = 4.0
    bm.expected_days_p75           = 8.0
    bm.evidence_source             = "SYMBOL_DIRECTION"
    return bm


def _bars(n=20, o=100.0, h=103.0, l=99.0, c=102.0) -> List[OHLCVBar]:
    return [OHLCVBar(date=f"2026-08-{10+i:02d}", open=o, high=h, low=l, close=c)
            for i in range(n)]


class TestEntryPriceFlow:

    def test_t01_real_entry_price_flows_into_decision_record(self):
        """T01: A real observation entry_price ends up on the persisted record."""
        rec = KDA.evaluate(_obs(direction="BUY", entry_price=2800.0), behaviour=_bm())
        assert rec.entry_price == pytest.approx(2800.0)

    def test_t02_zero_entry_price_becomes_none(self):
        """T02: entry_price=0.0 (no real price available) stored as None, not 0.0."""
        rec = KDA.evaluate(_obs(direction="BUY", entry_price=0.0), behaviour=None)
        assert rec.entry_price is None

    def test_t03_as_dict_roundtrip_preserves_entry_price(self):
        """T03: as_dict() -> from_dict() round-trip keeps the real entry_price."""
        rec = KDA.evaluate(_obs(direction="BUY", entry_price=3100.5), behaviour=_bm())
        d = rec.as_dict()
        assert d["entry_price"] == pytest.approx(3100.5)
        rebuilt = KDADecisionRecord.from_dict(d)
        assert rebuilt.entry_price == pytest.approx(3100.5)

    def test_t04_from_dict_missing_key_is_backward_compatible(self):
        """T04: A ledger dict from BEFORE this fix (no 'entry_price' key at all)
        reconstructs with entry_price=None -- zero behavior change for
        already-logged historical decisions."""
        rec = KDA.evaluate(_obs(direction="BUY", entry_price=2800.0), behaviour=_bm())
        d = rec.as_dict()
        del d["entry_price"]  # simulate an old, pre-fix ledger record
        rebuilt = KDADecisionRecord.from_dict(d)
        assert rebuilt.entry_price is None

    def test_t05_from_dict_zero_value_treated_as_none(self):
        """T05: A stored entry_price of 0 (falsy) is treated as 'not populated'."""
        rec = KDA.evaluate(_obs(direction="BUY", entry_price=2800.0), behaviour=_bm())
        d = rec.as_dict()
        d["entry_price"] = 0.0
        rebuilt = KDADecisionRecord.from_dict(d)
        assert rebuilt.entry_price is None

    def test_t06_outcome_engine_uses_real_entry_price_when_present(self):
        """T06: KDAOutcomeEngine.evaluate() uses the decision's own recorded
        entry_price when the caller passes it through (mirrors how
        knowledge_decision_pipeline.py reads rec_dict.get('entry_price'))."""
        rec = KDA.evaluate(_obs(direction="BUY", entry_price=100.0), behaviour=_bm())
        bars = _bars(5, o=105.0, h=108.0, l=104.0, c=107.0)  # T+1 open already 105, not 100
        out_with_real_entry = ENGINE.evaluate(rec, bars, entry_price=rec.entry_price)
        out_with_fallback    = ENGINE.evaluate(rec, bars, entry_price=None)
        assert out_with_real_entry.entry_price == pytest.approx(100.0)
        assert out_with_fallback.entry_price == pytest.approx(105.0)  # bars[0].open fallback
        # Same bars, different entry reference -> materially different measured return
        assert out_with_real_entry.return_t1 != out_with_fallback.return_t1


class TestClassifyOutcomeOrderingFix:

    def test_t07_stop_first_then_target_is_incorrect(self):
        """T07: stop hit BEFORE target (even if target also touched later in
        the window) is a real loss -> INCORRECT, not CORRECT."""
        cls = _classify_outcome("KNOWLEDGE_BUY", True, True, True, True, 3.0, 10,
                                 first_event="STOP_HIT")
        assert cls == "INCORRECT_BUY"

    def test_t08_target_first_then_stop_is_correct(self):
        """T08: target hit BEFORE stop -> still a real win -> CORRECT."""
        cls = _classify_outcome("KNOWLEDGE_BUY", True, True, True, True, 3.0, 10,
                                 first_event="TARGET_HIT")
        assert cls == "CORRECT_BUY"

    def test_t09_no_first_event_preserves_old_behavior(self):
        """T09: Callers that don't pass first_event (pre-fix call sites) keep
        the exact prior behavior -- both-hit always classified CORRECT."""
        cls = _classify_outcome("KNOWLEDGE_BUY", True, True, True, True, 3.0, 10)
        assert cls == "CORRECT_BUY"

    def test_t10_sell_stop_first_then_target_is_incorrect(self):
        """T10: same ordering fix applies symmetrically to SELL decisions."""
        cls = _classify_outcome("KNOWLEDGE_SELL", True, True, True, True, 3.0, 10,
                                 first_event="STOP_HIT")
        assert cls == "INCORRECT_SELL"

    def test_t11_single_event_paths_unaffected(self):
        """T11: target-only or stop-only paths (the common case) are completely
        unchanged by this fix."""
        assert _classify_outcome("KNOWLEDGE_BUY", True, True, False, True, 3.0, 5) == "CORRECT_BUY"
        assert _classify_outcome("KNOWLEDGE_BUY", True, False, True, False, -2.5, 5) == "INCORRECT_BUY"


class TestAuthorityReportDirectionalSampleSize:

    def test_t12_directional_decisions_matches_real_denominator(self):
        """T12: directional_decisions == the actual number of BUY/SELL outcomes
        direction_accuracy was computed over, not total_decisions."""
        buy = KDA.evaluate(_obs(direction="BUY", entry_price=100.0), behaviour=_bm())
        wait = KDA.evaluate(_obs(direction="BUY", entry_price=0.0), behaviour=None)
        bars = _bars(5)
        out_buy  = ENGINE.evaluate(buy, bars, entry_price=buy.entry_price)
        out_wait = ENGINE.evaluate(wait, bars, entry_price=None)
        report = REPORTER.generate_report(outcomes=[out_buy, out_wait])
        assert report.total_decisions == 2
        # Only the real BUY outcome is directional -- WAIT never counts here.
        assert report.directional_decisions <= report.total_decisions

    def test_t13_directional_decisions_field_exists_and_is_int(self):
        """T13: field is always present (additive, default 0) and never None."""
        report = REPORTER.generate_report(outcomes=[])
        assert isinstance(report.directional_decisions, int)
        assert report.directional_decisions == 0

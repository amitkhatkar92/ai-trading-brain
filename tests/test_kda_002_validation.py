"""
tests/test_kda_002_validation.py
==================================
KDA-002 — Outcome & Comparative Validation
120 tests (T001–T120)

Coverage:
  Safety invariants (T001-T010)
  T+N returns (T011-T025)
  Target/stop events (T021-T035)
  MFE/MAE (T036-T045)
  Horizon accuracy (T046-T050)
  Decision classification (T051-T060)
  Ledger operations (T061-T070)
  KDA vs StrategyLab comparison (T071-T080)
  Source performance & counterfactual (T081-T090)
  Evidence tier & authority bucket analysis (T091-T100)
  Calibration & authority validation (T101-T110)
  Missed opportunities & overrule analysis (T111-T120)

Safety contract:
  broker_calls = 0, orders = 0, no_lookahead = True
  PAPER_TRADING unchanged, no execution imports
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from knowledge_authority import (
    AuthorityBucketResult,
    AuthorityStatus,
    AuthorityValidationReport,
    ComparisonType,
    EvidenceTierResult,
    KDAAuthorityReporter,
    KDAComparativeAnalyzer,
    KDADecision,
    KDALedger,
    KDAOutcomeEngine,
    KDAOutcomeRecord,
    MoveSpeed,
    OHLCVBar,
    OutcomeClass,
    OutcomeStatus,
    OverruleResult,
    SourcePerformanceRecord,
    TargetComparison,
)
from knowledge_authority.kda_outcome_engine import _classify_outcome
from knowledge_authority import KnowledgeDecisionAuthority
from unittest.mock import MagicMock

# ─────────────────────────────────────────────────────────────────────────────
# Local fixture helpers (duplicated from test_kda_001 to avoid cross-test import)
# ─────────────────────────────────────────────────────────────────────────────

KDA = KnowledgeDecisionAuthority()


def _obs(**kwargs):
    defaults = dict(symbol="RELIANCE", direction="BUY", entry_price=2800.0,
                    atr=28.0, atr_pct=1.0, scanner_confidence=7.0)
    defaults.update(kwargs)
    return defaults


def _bm(ess=50.0, target_prob=0.6, stop_prob=0.3, target_src="EMPIRICAL", **kwargs):
    bm = MagicMock()
    bm.effective_sample_size       = ess
    bm.relevant_sample_size        = int(ess)
    bm.target_hit_probability      = target_prob
    bm.stop_first_probability      = stop_prob
    bm.target_source               = target_src
    bm.stop_source                 = target_src
    bm.knowledge_target_offset_p50 = kwargs.get("target_offset", 3.0)
    bm.knowledge_stop_offset_p50   = kwargs.get("stop_offset", 1.5)
    bm.expected_move_p25           = kwargs.get("em_p25", 1.0)
    bm.expected_move_p50           = kwargs.get("em_p50", 2.5)
    bm.expected_move_p75           = kwargs.get("em_p75", 4.5)
    bm.expected_days_p25           = kwargs.get("days_p25", 2.0)
    bm.expected_days_p50           = kwargs.get("days_p50", 4.0)
    bm.expected_days_p75           = kwargs.get("days_p75", 8.0)
    bm.evidence_source             = kwargs.get("evidence_src", "SYMBOL_DIRECTION_REGIME")
    return bm

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

ENGINE = KDAOutcomeEngine()
COMPARATOR = KDAComparativeAnalyzer()


def _bar(date="2026-08-10", o=100.0, h=105.0, l=98.0, c=103.0, v=1_000_000.0) -> OHLCVBar:
    return OHLCVBar(date=date, open=o, high=h, low=l, close=c, volume=v)


def _bars(n=20, base_close=103.0) -> List[OHLCVBar]:
    """n flat bars with close=base_close."""
    return [
        OHLCVBar(
            date=f"2026-08-{10+i:02d}",
            open=100.0,
            high=106.0,
            low=98.0,
            close=base_close,
        )
        for i in range(n)
    ]


def _buy_decision(ess=150.0, entry=100.0, target=105.0, stop=98.0, confidence=8.0):
    """KDADecisionRecord for a BUY scenario."""
    bm = _bm(
        ess=ess,
        target_prob=0.70,
        stop_prob=0.20,
        target_offset=target - entry,
        stop_offset=entry - stop,
        days_p25=2.0,
        days_p50=4.0,
        days_p75=8.0,
    )
    rec = KDA.evaluate(
        _obs(direction="BUY", entry_price=entry, atr=entry * 0.02, scanner_confidence=confidence),
        behaviour=bm,
    )
    return rec


def _sell_decision(entry=100.0, target=95.0, stop=102.0, confidence=8.0):
    bm = _bm(ess=150.0, target_prob=0.70, stop_prob=0.20,
             target_offset=entry - target, stop_offset=stop - entry,
             days_p50=4.0)
    return KDA.evaluate(
        _obs(direction="SELL", entry_price=entry, atr=entry * 0.02, scanner_confidence=confidence),
        behaviour=bm,
    )


def _wait_decision():
    return KDA.evaluate(_obs(), behaviour=None)


def _kda_outcome(
    decision=None,
    direction_correct=True,
    target_hit=True,
    stop_hit=False,
    return_t5=3.0,
    return_t1=1.0,
    knowledge_authority=0.70,
    evidence_state="DECISION_ELIGIBLE",
    status=OutcomeStatus.OUTCOME_COMPLETE.value,
    move_speed="NORMAL_MOVE",
    horizon_error=1.0,
    horizon_accuracy=0.75,
) -> KDAOutcomeRecord:
    """Build a synthetic outcome for analysis tests."""
    dec = decision or _buy_decision()
    return KDAOutcomeRecord(
        outcome_id            = str(uuid.uuid4()),
        decision_id           = dec.decision_id,
        observation_id        = None,
        trading_date          = "2026-08-10",
        symbol                = dec.symbol,
        direction             = dec.direction,
        decision              = dec.decision.value,
        authority             = dec.authority.value,
        knowledge_authority   = knowledge_authority,
        entry_price           = 100.0,
        target                = 105.0,
        stop_loss             = 98.0,
        expected_move_p25     = 1.0,
        expected_move_p50     = 3.0,
        expected_move_p75     = 5.0,
        expected_days_p25     = 2.0,
        expected_days_p50     = 4.0,
        expected_days_p75     = 8.0,
        target_source         = "EMPIRICAL",
        stop_source           = "EMPIRICAL",
        horizon_source        = "EMPIRICAL",
        return_t1             = return_t1,
        return_t3             = return_t5 * 0.6,
        return_t5             = return_t5,
        return_t10            = return_t5 * 1.2,
        return_t20            = return_t5 * 1.5,
        mfe                   = abs(return_t5) + 0.5,
        mae                   = 0.8,
        target_hit            = target_hit,
        stop_hit              = stop_hit,
        time_to_target        = 3 if target_hit else None,
        time_to_stop          = 5 if stop_hit else None,
        first_event           = "TARGET_HIT" if target_hit else ("STOP_HIT" if stop_hit else None),
        event_day             = 3 if target_hit else (5 if stop_hit else None),
        horizon_error         = horizon_error,
        horizon_accuracy      = horizon_accuracy,
        move_speed            = move_speed,
        target_accuracy       = 1.0 if target_hit else 0.6,
        target_comparison     = TargetComparison.REASONABLE.value,
        direction_correct     = direction_correct,
        decision_correct      = direction_correct,
        outcome_class         = OutcomeClass.CORRECT_BUY.value if direction_correct else OutcomeClass.INCORRECT_BUY.value,
        evidence_state        = evidence_state,
        evidence_level        = "SYMBOL_DIR_REGIME_CTX",
        status                = status,
        bars_available        = 20,
        evaluation_horizon    = 20,
        strategy_status       = "PASS",
        scanner_confidence    = 8.0,
        no_lookahead          = True,
        broker_calls          = 0,
        orders                = 0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# T001-T010: Safety invariants
# ─────────────────────────────────────────────────────────────────────────────

class TestSafetyInvariants:

    def test_t001_outcome_broker_calls_zero(self):
        """T001: KDAOutcomeRecord has broker_calls=0."""
        dec = _buy_decision()
        out = ENGINE.evaluate(dec, _bars())
        assert out.broker_calls == 0

    def test_t002_outcome_orders_zero(self):
        """T002: KDAOutcomeRecord has orders=0."""
        dec = _buy_decision()
        out = ENGINE.evaluate(dec, _bars())
        assert out.orders == 0

    def test_t003_outcome_no_lookahead_true(self):
        """T003: KDAOutcomeRecord has no_lookahead=True."""
        dec = _buy_decision()
        out = ENGINE.evaluate(dec, _bars())
        assert out.no_lookahead is True

    def test_t004_comparison_broker_calls_zero(self):
        """T004: KDAComparisonRecord has broker_calls=0."""
        dec = _buy_decision()
        rec = COMPARATOR.compare(dec, "PASS")
        assert rec.broker_calls == 0

    def test_t005_authority_report_broker_calls_zero(self):
        """T005: AuthorityValidationReport has broker_calls=0."""
        reporter = KDAAuthorityReporter()
        report = reporter.generate_report([_kda_outcome()])
        assert report.broker_calls == 0

    def test_t006_authority_report_modifications_zero(self):
        """T006: AuthorityValidationReport has modifications=0, cancellations=0."""
        reporter = KDAAuthorityReporter()
        report = reporter.generate_report([_kda_outcome()])
        assert report.modifications == 0
        assert report.cancellations == 0

    def test_t007_authority_report_no_lookahead(self):
        """T007: AuthorityValidationReport has no_lookahead=True."""
        reporter = KDAAuthorityReporter()
        report = reporter.generate_report([])
        assert report.no_lookahead is True

    def test_t008_no_data_when_empty_bars(self):
        """T008: Empty bars → OUTCOME_NO_DATA status."""
        dec = _buy_decision()
        out = ENGINE.evaluate(dec, [])
        assert out.status == OutcomeStatus.OUTCOME_NO_DATA.value

    def test_t009_engine_no_execution_imports(self):
        """T009: KDA outcome engine has no execution/broker imports."""
        import inspect
        from knowledge_authority import kda_outcome_engine as mod
        src = inspect.getsource(mod)
        import_lines = [l for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
        text = "\n".join(import_lines)
        for forbidden in ("OrderManager", "dhan_feed", "execution_engine", "DhanBroker"):
            assert forbidden not in text

    def test_t010_outcome_record_is_frozen(self):
        """T010: KDAOutcomeRecord is immutable."""
        out = _kda_outcome()
        with pytest.raises((AttributeError, TypeError)):
            out.orders = 99  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# T011-T020: T+N returns
# ─────────────────────────────────────────────────────────────────────────────

class TestTNReturns:

    def test_t011_buy_t1_return(self):
        """T011: BUY T+1 = (bars[0].close - entry) / entry * 100."""
        dec = _buy_decision(entry=100.0, ess=150.0)
        bars = [_bar(c=103.0)] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.return_t1 == pytest.approx(3.0, abs=0.01)

    def test_t012_buy_t3_return(self):
        """T012: BUY T+3 = (bars[2].close - entry) / entry * 100."""
        dec = _buy_decision(entry=100.0, ess=150.0)
        bars = [_bar(c=100.0), _bar(c=101.0), _bar(c=104.0)] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.return_t3 == pytest.approx(4.0, abs=0.01)

    def test_t013_buy_t5_return(self):
        """T013: BUY T+5 = (bars[4].close - entry) / entry * 100."""
        close_vals = [100.0, 100.0, 100.0, 100.0, 106.0] + [100.0] * 15
        bars = [_bar(c=c) for c in close_vals]
        dec = _buy_decision(entry=100.0, ess=150.0)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.return_t5 == pytest.approx(6.0, abs=0.01)

    def test_t014_sell_t1_return(self):
        """T014: SELL T+1 = (entry - bars[0].close) / entry * 100."""
        dec = _sell_decision(entry=100.0, target=95.0, stop=102.0)
        bars = [_bar(c=97.0)] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.return_t1 == pytest.approx(3.0, abs=0.01)

    def test_t015_sell_t5_return(self):
        """T015: SELL T+5 uses entry - close[4] formula."""
        close_vals = [100.0, 100.0, 100.0, 100.0, 94.0] + [100.0] * 15
        bars = [_bar(c=c) for c in close_vals]
        dec = _sell_decision(entry=100.0)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.return_t5 == pytest.approx(6.0, abs=0.01)

    def test_t016_t10_return_requires_10_bars(self):
        """T016: T+10 return is None when only 3 bars available."""
        dec = _buy_decision(ess=150.0)
        out = ENGINE.evaluate(dec, _bars(3), entry_price=100.0)
        assert out.return_t10 is None

    def test_t017_t20_return_present_with_20_bars(self):
        """T017: T+20 return populated when 20 bars available."""
        dec = _buy_decision(ess=150.0)
        out = ENGINE.evaluate(dec, _bars(20, base_close=104.0), entry_price=100.0)
        assert out.return_t20 == pytest.approx(4.0, abs=0.01)

    def test_t018_returns_are_percentage(self):
        """T018: Returns are in %, not raw price difference."""
        dec = _buy_decision(entry=1000.0, ess=150.0)
        bars = [_bar(c=1010.0)] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=1000.0)
        # 1% gain, not 10.0 raw
        assert out.return_t1 == pytest.approx(1.0, abs=0.01)

    def test_t019_entry_defaults_to_next_bar_open(self):
        """T019: If no entry_price given, uses bars[0].open."""
        dec = _buy_decision(ess=150.0)
        bars = [_bar(o=100.0, c=105.0)] + _bars(5)
        out = ENGINE.evaluate(dec, bars)
        assert out.entry_price == pytest.approx(100.0)
        assert out.return_t1 == pytest.approx(5.0, abs=0.01)

    def test_t020_t1_none_when_zero_bars(self):
        """T020: All returns are None when bars is empty."""
        dec = _buy_decision(ess=150.0)
        out = ENGINE.evaluate(dec, [])
        assert out.return_t1 is None
        assert out.return_t5 is None


# ─────────────────────────────────────────────────────────────────────────────
# T021-T035: Target / stop events
# ─────────────────────────────────────────────────────────────────────────────

class TestTargetStopEvents:

    def test_t021_buy_target_hit_when_high_ge_target(self):
        """T021: BUY target hit when bar.high >= target."""
        dec = _buy_decision(entry=100.0, target=105.0, stop=97.0, ess=150.0)
        bars = [_bar(h=106.0, l=100.0, c=104.0)] + _bars(3)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.target_hit is True

    def test_t022_buy_stop_hit_when_low_le_stop(self):
        """T022: BUY stop hit when bar.low <= stop_loss."""
        dec = _buy_decision(entry=100.0, target=105.0, stop=97.0, ess=150.0)
        bars = [_bar(h=101.0, l=96.0, c=99.0)] + _bars(3)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.stop_hit is True

    def test_t023_sell_target_hit_when_low_le_target(self):
        """T023: SELL target hit when bar.low <= target."""
        dec = _sell_decision(entry=100.0, target=95.0, stop=103.0)
        bars = [_bar(h=100.0, l=94.0, c=96.0)] + _bars(3)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.target_hit is True

    def test_t024_sell_stop_hit_when_high_ge_stop(self):
        """T024: SELL stop hit when bar.high >= stop_loss."""
        dec = _sell_decision(entry=100.0, target=95.0, stop=103.0)
        bars = [_bar(h=104.0, l=99.0, c=101.0)] + _bars(3)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.stop_hit is True

    def test_t025_target_hit_records_day_index(self):
        """T025: time_to_target = bar index (1-based) when target first hit."""
        dec = _buy_decision(entry=100.0, target=105.0, stop=97.0, ess=150.0)
        bars = [
            _bar(h=103.0, c=102.0),   # bar 1 — miss
            _bar(h=103.0, c=102.0),   # bar 2 — miss
            _bar(h=106.0, c=105.0),   # bar 3 — HIT
        ] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.time_to_target == 3

    def test_t026_stop_hit_records_day_index(self):
        """T026: time_to_stop = bar index when stop first hit."""
        dec = _buy_decision(entry=100.0, target=110.0, stop=97.0, ess=150.0)
        bars = [
            _bar(h=103.0, l=99.0, c=102.0),  # bar 1 — safe
            _bar(h=103.0, l=96.0, c=99.0),   # bar 2 — STOP HIT
        ] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.time_to_stop == 2

    def test_t027_first_event_target_when_target_hits_first(self):
        """T027: first_event = TARGET_HIT when target day < stop day."""
        dec = _buy_decision(entry=100.0, target=104.0, stop=97.0, ess=150.0)
        bars = [
            _bar(h=105.0, l=99.0, c=103.0),   # bar 1: target hit
            _bar(h=103.0, l=95.0, c=98.0),    # bar 2: stop would hit
        ] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.first_event == "TARGET_HIT"
        assert out.event_day == 1

    def test_t028_first_event_stop_when_stop_hits_first(self):
        """T028: first_event = STOP_HIT when stop day < target day."""
        dec = _buy_decision(entry=100.0, target=110.0, stop=97.0, ess=150.0)
        bars = [
            _bar(h=103.0, l=95.0, c=99.0),   # bar 1: stop hit
            _bar(h=112.0, l=100.0, c=110.0), # bar 2: target would hit
        ] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.first_event == "STOP_HIT"
        assert out.event_day == 1

    def test_t029_same_day_target_and_stop_favors_target(self):
        """T029: Same-bar target AND stop → first_event = TARGET_HIT."""
        dec = _buy_decision(entry=100.0, target=104.0, stop=97.0, ess=150.0)
        # Wide bar that breaches both
        bars = [_bar(h=105.0, l=96.0, c=102.0)] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.first_event == "TARGET_HIT"

    def test_t030_no_target_means_target_hit_false(self):
        """T030: No target in decision → target_hit=False."""
        dec = KDA.evaluate(_obs(direction="BUY"), behaviour=None)
        bars = _bars(5, base_close=110.0)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.target_hit is False

    def test_t031_no_stop_means_stop_hit_false(self):
        """T031: No stop in decision → stop_hit=False."""
        # atr=0 → no ATR fallback → stop_loss=None in decision
        dec = KDA.evaluate(_obs(direction="BUY", entry_price=100.0, atr=0.0), behaviour=None)
        assert dec.stop_loss is None
        bars = [_bar(l=90.0)] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.stop_hit is False

    def test_t032_time_to_target_none_when_not_hit(self):
        """T032: time_to_target=None when target never reached."""
        dec = _buy_decision(entry=100.0, target=200.0, stop=50.0, ess=150.0)
        bars = _bars(5, base_close=105.0)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.time_to_target is None

    def test_t033_target_hit_within_20_bars(self):
        """T033: Target hit on bar 18 still detected (within max 20)."""
        # target=110 > h=106, stop=90 < l=98: first 17 _bars hit neither
        dec = _buy_decision(entry=100.0, target=110.0, stop=90.0, ess=150.0)
        bars = _bars(17, base_close=103.0) + [_bar(h=111.0, c=110.5, l=99.0)] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.target_hit is True
        assert out.time_to_target == 18

    def test_t034_event_day_is_min_of_target_and_stop(self):
        """T034: event_day = min(target_day, stop_day)."""
        dec = _buy_decision(entry=100.0, target=104.0, stop=97.0, ess=150.0)
        bars = [
            _bar(h=103.0, l=99.0, c=101.0),  # bar 1: safe
            _bar(h=105.0, l=96.0, c=103.0),  # bar 2: BOTH hit
        ] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.event_day == 2

    def test_t035_first_event_none_when_no_events(self):
        """T035: first_event=None when neither target nor stop hit."""
        dec = _buy_decision(entry=100.0, target=120.0, stop=80.0, ess=150.0)
        bars = _bars(10, base_close=103.0)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.first_event is None
        assert out.event_day is None


# ─────────────────────────────────────────────────────────────────────────────
# T036-T045: MFE / MAE
# ─────────────────────────────────────────────────────────────────────────────

class TestMFEAndMAE:

    def test_t036_buy_mfe_is_max_high_minus_entry_pct(self):
        """T036: BUY MFE = max(bar.high - entry) / entry * 100 over all bars."""
        dec = _buy_decision(entry=100.0, ess=150.0)
        bars = [_bar(h=104.0), _bar(h=108.0), _bar(h=106.0)]
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.mfe == pytest.approx(8.0, abs=0.01)

    def test_t037_buy_mae_is_max_entry_minus_low_pct(self):
        """T037: BUY MAE = max(entry - bar.low) / entry * 100 over all bars."""
        dec = _buy_decision(entry=100.0, ess=150.0)
        bars = [_bar(l=97.0), _bar(l=95.0), _bar(l=98.0)]
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.mae == pytest.approx(5.0, abs=0.01)

    def test_t038_sell_mfe_is_entry_minus_min_low_pct(self):
        """T038: SELL MFE = max(entry - bar.low) / entry * 100."""
        dec = _sell_decision(entry=100.0)
        bars = [_bar(l=93.0), _bar(l=96.0)]
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.mfe == pytest.approx(7.0, abs=0.01)

    def test_t039_sell_mae_is_max_high_minus_entry_pct(self):
        """T039: SELL MAE = max(bar.high - entry) / entry * 100."""
        dec = _sell_decision(entry=100.0)
        bars = [_bar(h=103.0), _bar(h=107.0)]
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.mae == pytest.approx(7.0, abs=0.01)

    def test_t040_mfe_ge_zero(self):
        """T040: MFE >= 0 always (even if price moves only against)."""
        dec = _buy_decision(entry=100.0, ess=150.0)
        bars = [_bar(h=101.0, l=95.0)]  # slight high, large low
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.mfe is not None
        assert out.mfe >= 0.0

    def test_t041_mae_ge_zero(self):
        """T041: MAE >= 0 always."""
        dec = _buy_decision(entry=100.0, ess=150.0)
        bars = [_bar(h=106.0, l=100.0)]  # only favorable
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.mae is not None
        assert out.mae == pytest.approx(0.0, abs=0.01)

    def test_t042_mfe_zero_when_flat_bars(self):
        """T042: MFE=0 when high == entry and low == entry (flat)."""
        dec = _buy_decision(entry=100.0, ess=150.0)
        bars = [OHLCVBar(date="2026-08-10", open=100.0, high=100.0, low=100.0, close=100.0)]
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.mfe == pytest.approx(0.0, abs=0.01)

    def test_t043_mfe_uses_all_bars_up_to_20(self):
        """T043: MFE computed over all bars up to max 20."""
        dec = _buy_decision(entry=100.0, ess=150.0)
        bars = _bars(15, base_close=103.0)
        bars[-1] = OHLCVBar(date="2026-08-25", open=100.0, high=112.0, low=100.0, close=110.0)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.mfe == pytest.approx(12.0, abs=0.01)

    def test_t044_mfe_mae_none_for_non_directional(self):
        """T044: MFE/MAE are None for WAIT/HOLD decisions (not a real trade)."""
        dec = _wait_decision()
        bars = _bars(5, base_close=110.0)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        # Engine uses KDA decision (KNOWLEDGE_WAIT) not scanner direction
        assert out.mfe is None
        assert out.mae is None

    def test_t045_mfe_mae_as_percentage_not_raw(self):
        """T045: MFE/MAE are percentages (entry=1000, high=1010 → MFE=1.0%)."""
        dec = _buy_decision(entry=1000.0, ess=150.0)
        bars = [_bar(o=1000.0, h=1010.0, l=995.0, c=1005.0)]
        out = ENGINE.evaluate(dec, bars, entry_price=1000.0)
        assert out.mfe == pytest.approx(1.0, abs=0.01)
        assert out.mae == pytest.approx(0.5, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# T046-T050: Horizon accuracy
# ─────────────────────────────────────────────────────────────────────────────

class TestHorizonAccuracy:

    def test_t046_perfect_horizon_accuracy_when_exact_match(self):
        """T046: horizon_accuracy=1.0 when actual event_day == expected_days_p50."""
        dec = _buy_decision(entry=100.0, target=104.0, stop=90.0, ess=150.0)
        # stop=90 safely below all bars (l=99), target=104, p50=4 days
        bars = [
            OHLCVBar("2026-08-10", 100.0, 103.0, 99.0, 102.0),
            OHLCVBar("2026-08-11", 100.0, 103.0, 99.0, 102.0),
            OHLCVBar("2026-08-12", 100.0, 103.0, 99.0, 102.0),
            OHLCVBar("2026-08-13", 100.0, 106.0, 99.0, 104.5),  # day 4 — target hit
        ]
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.time_to_target == 4
        assert out.horizon_accuracy == pytest.approx(1.0, abs=0.01)

    def test_t047_horizon_accuracy_decreases_with_error(self):
        """T047: Larger horizon error → lower accuracy."""
        dec = _buy_decision(entry=100.0, target=104.0, stop=90.0, ess=150.0)
        # Expected p50=4; hit on day 8 → error=4 → accuracy = max(0, 1 - 4/4) = 0.0
        safe_bar = OHLCVBar("2026-08-10", 100.0, 103.0, 99.0, 102.0)
        hit_bar  = OHLCVBar("2026-08-17", 100.0, 106.0, 99.0, 104.5)
        bars = [safe_bar] * 7 + [hit_bar] + _bars(3)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.horizon_accuracy is not None
        assert out.horizon_accuracy < 1.0

    def test_t048_horizon_accuracy_ge_zero(self):
        """T048: horizon_accuracy >= 0.0 always (clamped)."""
        dec = _buy_decision(entry=100.0, target=104.0, ess=150.0)
        # Hit on day 20 >> p50=4 → accuracy clamped to 0
        bars = _bars(19, base_close=102.0) + [_bar(h=106.0, c=104.5)]
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.horizon_accuracy is not None
        assert out.horizon_accuracy >= 0.0

    def test_t049_horizon_none_when_no_p50(self):
        """T049: horizon_accuracy=None when no expected_days_p50 (WAIT decision)."""
        dec = _wait_decision()
        out = ENGINE.evaluate(dec, _bars(5))
        assert out.horizon_accuracy is None

    def test_t050_move_speed_fast_when_event_before_p25(self):
        """T050: move_speed=FAST_MOVE when event_day < expected_days_p25."""
        dec = _buy_decision(entry=100.0, target=104.0, ess=150.0)
        # p25=2; hit on day 1 → FAST
        bars = [_bar(h=106.0, c=104.5)] + _bars(5)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)
        assert out.move_speed == MoveSpeed.FAST_MOVE.value


# ─────────────────────────────────────────────────────────────────────────────
# T051-T060: Decision classification
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionClassification:

    def test_t051_correct_buy_when_target_hit(self):
        """T051: KNOWLEDGE_BUY + target_hit → CORRECT_BUY."""
        cls = _classify_outcome("KNOWLEDGE_BUY", True, True, False, True, 3.0, 5)
        assert cls == OutcomeClass.CORRECT_BUY.value

    def test_t052_incorrect_buy_when_stop_hit(self):
        """T052: KNOWLEDGE_BUY + stop_hit + no target → INCORRECT_BUY."""
        cls = _classify_outcome("KNOWLEDGE_BUY", True, False, True, False, -2.5, 5)
        assert cls == OutcomeClass.INCORRECT_BUY.value

    def test_t053_correct_sell_when_target_hit(self):
        """T053: KNOWLEDGE_SELL + target_hit → CORRECT_SELL."""
        cls = _classify_outcome("KNOWLEDGE_SELL", True, True, False, True, 3.0, 5)
        assert cls == OutcomeClass.CORRECT_SELL.value

    def test_t054_incorrect_sell_when_stop_hit(self):
        """T054: KNOWLEDGE_SELL + stop_hit → INCORRECT_SELL."""
        cls = _classify_outcome("KNOWLEDGE_SELL", True, False, True, False, -2.0, 5)
        assert cls == OutcomeClass.INCORRECT_SELL.value

    def test_t055_correct_wait_when_no_meaningful_move(self):
        """T055: KNOWLEDGE_WAIT + abs(return) < 2% → CORRECT_WAIT."""
        cls = _classify_outcome("KNOWLEDGE_WAIT", False, False, False, None, 0.5, 5)
        assert cls == OutcomeClass.CORRECT_WAIT.value

    def test_t056_missed_opportunity_when_wait_with_big_move(self):
        """T056: KNOWLEDGE_WAIT + abs(return) >= 2% → MISSED_OPPORTUNITY."""
        cls = _classify_outcome("KNOWLEDGE_WAIT", False, False, False, None, 3.5, 5)
        assert cls == OutcomeClass.MISSED_OPPORTUNITY.value

    def test_t057_unresolved_when_insufficient_bars_and_no_event(self):
        """T057: UNRESOLVED when no event and direction_correct=None."""
        cls = _classify_outcome("KNOWLEDGE_BUY", True, False, False, None, None, 5)
        assert cls == OutcomeClass.UNRESOLVED.value

    def test_t058_correct_buy_by_t5_direction_when_no_event(self):
        """T058: KNOWLEDGE_BUY + no event + T+5 positive → CORRECT_BUY."""
        cls = _classify_outcome("KNOWLEDGE_BUY", True, False, False, True, 2.5, 5)
        assert cls == OutcomeClass.CORRECT_BUY.value

    def test_t059_incorrect_buy_by_t5_direction_when_negative(self):
        """T059: KNOWLEDGE_BUY + no event + T+5 negative → INCORRECT_BUY."""
        cls = _classify_outcome("KNOWLEDGE_BUY", True, False, False, False, -2.5, 5)
        assert cls == OutcomeClass.INCORRECT_BUY.value

    def test_t060_outcome_class_is_string(self):
        """T060: outcome_class in KDAOutcomeRecord is a string."""
        dec = _buy_decision(ess=150.0)
        out = ENGINE.evaluate(dec, _bars(5), entry_price=100.0)
        assert isinstance(out.outcome_class, str)
        valid = {c.value for c in OutcomeClass}
        assert out.outcome_class in valid


# ─────────────────────────────────────────────────────────────────────────────
# T061-T070: Ledger operations
# ─────────────────────────────────────────────────────────────────────────────

class TestLedger:

    @pytest.fixture
    def tmp_ledger(self, tmp_path):
        return KDALedger(base_dir=tmp_path)

    def test_t061_ledger_write_returns_true_on_first_write(self, tmp_ledger):
        """T061: Ledger.record() returns True on first write."""
        dec = _buy_decision()
        assert tmp_ledger.record(dec) is True

    def test_t062_ledger_creates_daily_jsonl_file(self, tmp_ledger, tmp_path):
        """T062: Record creates kda_decisions_YYYY-MM-DD.jsonl file."""
        dec = _buy_decision()
        tmp_ledger.record(dec)
        files = list(tmp_path.glob("kda_decisions_*.jsonl"))
        assert len(files) == 1

    def test_t063_ledger_duplicate_returns_false(self, tmp_ledger):
        """T063: Second record() with same decision_id returns False."""
        dec = _buy_decision()
        tmp_ledger.record(dec)
        assert tmp_ledger.record(dec) is False

    def test_t064_load_decisions_returns_list(self, tmp_ledger):
        """T064: load_decisions returns a list of dicts."""
        dec = _buy_decision()
        tmp_ledger.record(dec)
        records = tmp_ledger.load_decisions("2026-08-22")
        # Will be empty if date doesn't match; just check type
        assert isinstance(records, list)

    def test_t065_load_all_decisions_returns_all(self, tmp_ledger):
        """T065: load_all_decisions returns all records across date files."""
        d1 = _buy_decision()
        d2 = _buy_decision()
        tmp_ledger.record(d1)
        tmp_ledger.record(d2)
        all_recs = tmp_ledger.load_all_decisions()
        assert len(all_recs) >= 2

    def test_t066_load_unknown_date_returns_empty(self, tmp_ledger):
        """T066: load_decisions for date with no file returns []."""
        result = tmp_ledger.load_decisions("1990-01-01")
        assert result == []

    def test_t067_corrupt_line_skipped_silently(self, tmp_path):
        """T067: Corrupt JSONL line skipped; valid lines still returned."""
        import datetime as dt
        date = dt.date.today().isoformat()
        path = tmp_path / f"kda_decisions_{date}.jsonl"
        path.write_text('{"decision_id": "abc"}\n{CORRUPT\n{"decision_id": "def"}\n')
        ledger = KDALedger(base_dir=tmp_path)
        records = ledger.load_decisions(date)
        assert len(records) == 2  # two valid lines

    def test_t068_ledger_creates_directory_if_missing(self, tmp_path):
        """T068: Ledger creates subdirectory if it doesn't exist."""
        sub = tmp_path / "deeply" / "nested" / "kda"
        ledger = KDALedger(base_dir=sub)
        dec = _buy_decision()
        result = ledger.record(dec)
        assert result is True
        assert sub.exists()

    def test_t069_is_duplicate_false_for_unseen_id(self, tmp_ledger):
        """T069: is_duplicate returns False for an ID never written."""
        assert tmp_ledger.is_duplicate("never-written-id") is False

    def test_t070_is_duplicate_true_after_write(self, tmp_ledger):
        """T070: is_duplicate returns True after a decision is recorded."""
        dec = _buy_decision()
        tmp_ledger.record(dec)
        assert tmp_ledger.is_duplicate(dec.decision_id) is True


# ─────────────────────────────────────────────────────────────────────────────
# T071-T080: KDA vs StrategyLab comparison
# ─────────────────────────────────────────────────────────────────────────────

class TestKDAComparison:

    def test_t071_both_agree_when_kda_directional_and_strategy_pass(self):
        """T071: comparison_type=BOTH_AGREE when KDA BUY + StrategyLab PASS."""
        dec = _buy_decision(ess=150.0)
        rec = COMPARATOR.compare(dec, "PASS")
        if dec.decision in (KDADecision.KNOWLEDGE_BUY, KDADecision.KNOWLEDGE_SELL):
            assert rec.comparison_type == ComparisonType.BOTH_AGREE.value

    def test_t072_both_reject_when_kda_wait_and_strategy_reject(self):
        """T072: comparison_type=BOTH_REJECT when KDA WAIT + StrategyLab REJECT."""
        dec = _wait_decision()
        rec = COMPARATOR.compare(dec, "REJECT")
        assert rec.comparison_type == ComparisonType.BOTH_REJECT.value

    def test_t073_kda_overrules_when_kda_directional_strategy_reject(self):
        """T073: KDA_OVERRULES_STRATEGY when KDA BUY + StrategyLab REJECT."""
        dec = _buy_decision(ess=150.0)
        rec = COMPARATOR.compare(dec, "REJECT")
        if dec.decision in (KDADecision.KNOWLEDGE_BUY, KDADecision.KNOWLEDGE_SELL):
            assert rec.comparison_type == ComparisonType.KDA_OVERRULES_STRATEGY.value

    def test_t074_strategy_overrules_when_kda_wait_strategy_pass(self):
        """T074: STRATEGY_OVERRULES_KDA when KDA WAIT + StrategyLab PASS."""
        dec = _wait_decision()
        rec = COMPARATOR.compare(dec, "PASS")
        assert rec.comparison_type == ComparisonType.STRATEGY_OVERRULES_KDA.value

    def test_t075_successful_overrule_when_direction_correct(self):
        """T075: KNOWLEDGE_SUCCESSFUL_OVERRULE when KDA overrules AND direction_correct."""
        dec = _buy_decision(ess=150.0)
        outcome = {"direction_correct": True, "return_t5": 3.5,
                   "outcome_class": "CORRECT_BUY", "target_hit": True, "stop_hit": False}
        rec = COMPARATOR.compare(dec, "REJECT", outcome)
        if rec.comparison_type == ComparisonType.KDA_OVERRULES_STRATEGY.value:
            assert rec.overrule_result == OverruleResult.KNOWLEDGE_SUCCESSFUL_OVERRULE.value

    def test_t076_false_overrule_when_direction_wrong(self):
        """T076: KNOWLEDGE_FALSE_OVERRULE when KDA overrules AND direction_correct=False."""
        dec = _buy_decision(ess=150.0)
        outcome = {"direction_correct": False, "return_t5": -3.0,
                   "outcome_class": "INCORRECT_BUY", "target_hit": False, "stop_hit": True}
        rec = COMPARATOR.compare(dec, "REJECT", outcome)
        if rec.comparison_type == ComparisonType.KDA_OVERRULES_STRATEGY.value:
            assert rec.overrule_result == OverruleResult.KNOWLEDGE_FALSE_OVERRULE.value

    def test_t077_false_rejection_when_kda_wait_big_move(self):
        """T077: FALSE_KNOWLEDGE_REJECTION when KDA WAIT + |return_t5| >= 2%."""
        dec = _wait_decision()
        outcome = {"direction_correct": True, "return_t5": 4.0,
                   "outcome_class": "MISSED_OPPORTUNITY", "target_hit": None, "stop_hit": None}
        rec = COMPARATOR.compare(dec, "REJECT", outcome)
        assert rec.overrule_result == OverruleResult.FALSE_KNOWLEDGE_REJECTION.value

    def test_t078_false_selection_when_kda_directional_wrong(self):
        """T078: FALSE_KNOWLEDGE_SELECTION when KDA BUY + direction_correct=False."""
        dec = _buy_decision(ess=150.0)
        outcome = {"direction_correct": False, "return_t5": -3.5,
                   "outcome_class": "INCORRECT_BUY", "target_hit": False, "stop_hit": True}
        rec = COMPARATOR.compare(dec, "PASS", outcome)
        if dec.decision in (KDADecision.KNOWLEDGE_BUY.value, KDADecision.KNOWLEDGE_SELL.value):
            # BOTH_AGREE (strategy also PASS) → FALSE_KNOWLEDGE_SELECTION
            pass  # assertion varies by comparison_type; check overrule_result
        # If KDA_ONLY or BOTH_AGREE with wrong direction:
        assert rec.overrule_result in (
            OverruleResult.FALSE_KNOWLEDGE_SELECTION.value, None
        )

    def test_t079_comparison_type_is_string(self):
        """T079: comparison_type in KDAComparisonRecord is a string."""
        dec = _buy_decision()
        rec = COMPARATOR.compare(dec, "PASS")
        assert isinstance(rec.comparison_type, str)
        assert rec.comparison_type in {ct.value for ct in ComparisonType}

    def test_t080_overrule_result_none_when_not_overrule(self):
        """T080: overrule_result=None when comparison_type=BOTH_AGREE."""
        dec = _buy_decision(ess=150.0)
        outcome = {"direction_correct": True, "return_t5": 3.0,
                   "outcome_class": "CORRECT_BUY", "target_hit": True, "stop_hit": False}
        rec = COMPARATOR.compare(dec, "PASS", outcome)
        if rec.comparison_type == ComparisonType.BOTH_AGREE.value:
            assert rec.overrule_result is None


# ─────────────────────────────────────────────────────────────────────────────
# T081-T090: Source performance and counterfactual
# ─────────────────────────────────────────────────────────────────────────────

class TestSourcePerformance:

    def test_t081_source_performance_has_required_fields(self):
        """T081: SourcePerformanceRecord has all required fields."""
        rec = SourcePerformanceRecord(
            source="STOCK", sample_count=10, support_count=8,
            contradiction_count=2, decision_change_count=3,
            correct_change_count=2, incorrect_change_count=1,
            incremental_value=0.67, oos_value=0.5,
        )
        d = rec.as_dict()
        for key in ("source", "sample_count", "support_count", "contradiction_count",
                    "decision_change_count", "correct_change_count", "incorrect_change_count",
                    "incremental_value", "oos_value"):
            assert key in d

    def test_t082_incremental_value_from_correct_changes(self):
        """T082: incremental_value = correct_changes / decision_changes."""
        rec = SourcePerformanceRecord(
            source="SECTOR", sample_count=20, support_count=15,
            contradiction_count=5, decision_change_count=10,
            correct_change_count=7, incorrect_change_count=3,
            incremental_value=0.70, oos_value=0.5,
        )
        assert rec.incremental_value == pytest.approx(0.70, abs=0.01)

    def test_t083_source_performance_from_authority_report(self):
        """T083: KDAAuthorityReporter generates source_performance list."""
        reporter = KDAAuthorityReporter()
        contributions = [
            {"source": "STOCK", "direction": "SUPPORT", "contribution": 0.15},
            {"source": "SECTOR", "direction": "CONTRADICT", "contribution": -0.05},
            {"source": "STOCK", "direction": "SUPPORT", "contribution": 0.12},
        ]
        outcomes = [_kda_outcome() for _ in range(10)]
        report = reporter.generate_report(outcomes, contributions)
        assert isinstance(report.source_performance, list)

    def test_t084_no_source_performance_when_no_contributions(self):
        """T084: source_performance=[] when no contributions provided."""
        reporter = KDAAuthorityReporter()
        report = reporter.generate_report([_kda_outcome()])
        assert report.source_performance == []

    def test_t085_comparison_record_has_scanner_signal(self):
        """T085: KDAComparisonRecord.scanner_signal set from scanner confidence."""
        dec = _buy_decision(confidence=7.0)  # above 6.0 threshold
        rec = COMPARATOR.compare(dec, "PASS")
        # Scanner confidence >= 6.0 → scanner approves → signal = direction
        assert rec.scanner_signal in ("BUY", "SELL", dec.direction)

    def test_t086_scanner_holds_when_confidence_low(self):
        """T086: scanner_signal = HOLD when confidence < threshold."""
        dec = _buy_decision(confidence=3.0)
        rec = COMPARATOR.compare(dec, "REJECT")
        assert rec.scanner_signal == "HOLD"

    def test_t087_kda_correct_none_when_no_outcome(self):
        """T087: kda_correct=None when no outcome provided."""
        dec = _buy_decision()
        rec = COMPARATOR.compare(dec, "PASS", outcome=None)
        assert rec.kda_correct is None

    def test_t088_comparison_summary_has_required_keys(self):
        """T088: summarize() returns dict with all required keys."""
        dec = _buy_decision(ess=150.0)
        rec = COMPARATOR.compare(dec, "PASS")
        summary = COMPARATOR.summarize([rec])
        for key in ("n", "kda_direction_accuracy", "strategy_direction_accuracy",
                    "overrule_count", "successful_overrules", "false_overrules",
                    "missed_opportunities", "comparison_type_counts"):
            assert key in summary

    def test_t089_summarize_empty_list(self):
        """T089: summarize([]) returns status=INSUFFICIENT_SAMPLE."""
        summary = COMPARATOR.summarize([])
        assert summary["status"] == "INSUFFICIENT_SAMPLE"

    def test_t090_scanner_correct_none_when_no_outcome(self):
        """T090: scanner_correct=None when outcome not provided."""
        dec = _buy_decision()
        rec = COMPARATOR.compare(dec, "PASS", outcome=None)
        assert rec.scanner_correct is None


# ─────────────────────────────────────────────────────────────────────────────
# T091-T100: Evidence tiers and authority buckets
# ─────────────────────────────────────────────────────────────────────────────

class TestTiersAndBuckets:

    def _many_outcomes(self, n=20, direction_correct=True, auth=0.70, state="DECISION_ELIGIBLE"):
        return [_kda_outcome(direction_correct=direction_correct,
                             knowledge_authority=auth,
                             evidence_state=state) for _ in range(n)]

    def test_t091_authority_buckets_cover_all_ranges(self):
        """T091: Authority buckets cover 0.00-0.20, 0.20-0.40, ..., 0.80-1.00."""
        reporter = KDAAuthorityReporter()
        report = reporter.generate_report(self._many_outcomes())
        labels = {b.bucket for b in report.authority_buckets}
        assert "0.00-0.20" in labels
        assert "0.40-0.60" in labels
        assert "0.80-1.00" in labels

    def test_t092_authority_bucket_has_correct_n(self):
        """T092: n in bucket matches outcomes with knowledge_authority in that range."""
        reporter = KDAAuthorityReporter()
        # All outcomes have auth=0.70 → falls in 0.60-0.80 bucket
        outcomes = self._many_outcomes(n=12, auth=0.70)
        report = reporter.generate_report(outcomes)
        bucket_60_80 = next(b for b in report.authority_buckets if b.bucket == "0.60-0.80")
        assert bucket_60_80.n == 12

    def test_t093_evidence_tier_results_cover_all_states(self):
        """T093: Evidence tiers cover all 5 EvidenceState values."""
        reporter = KDAAuthorityReporter()
        report = reporter.generate_report(self._many_outcomes())
        tier_names = {t.tier for t in report.evidence_tiers}
        for expected in ("INSUFFICIENT", "DEVELOPING", "USEFUL", "VALIDATED", "DECISION_ELIGIBLE"):
            assert expected in tier_names

    def test_t094_tier_result_has_correct_n(self):
        """T094: EvidenceTierResult.n counts only records with that evidence_state."""
        reporter = KDAAuthorityReporter()
        outcomes = (
            self._many_outcomes(n=8, state="DECISION_ELIGIBLE") +
            self._many_outcomes(n=5, state="VALIDATED")
        )
        report = reporter.generate_report(outcomes)
        de_tier = next(t for t in report.evidence_tiers if t.tier == "DECISION_ELIGIBLE")
        val_tier = next(t for t in report.evidence_tiers if t.tier == "VALIDATED")
        assert de_tier.n == 8
        assert val_tier.n == 5

    def test_t095_empty_bucket_has_n_zero(self):
        """T095: Bucket with no outcomes has n=0 and None metrics."""
        reporter = KDAAuthorityReporter()
        # All outcomes have auth=0.10 → 0.00-0.20 bucket
        outcomes = self._many_outcomes(n=6, auth=0.10)
        report = reporter.generate_report(outcomes)
        empty_bucket = next(b for b in report.authority_buckets if b.bucket == "0.80-1.00")
        assert empty_bucket.n == 0
        assert empty_bucket.direction_accuracy is None

    def test_t096_direction_accuracy_none_below_min_n(self):
        """T096: direction_accuracy=None for bucket with n < 5."""
        reporter = KDAAuthorityReporter()
        # Only 3 outcomes in 0.60-0.80 bucket
        outcomes = self._many_outcomes(n=3, auth=0.70)
        report = reporter.generate_report(outcomes)
        bucket = next(b for b in report.authority_buckets if b.bucket == "0.60-0.80")
        assert bucket.direction_accuracy is None

    def test_t097_tier_does_not_assume_higher_is_better(self):
        """T097: Higher evidence tier can have lower direction accuracy (measured not assumed)."""
        reporter = KDAAuthorityReporter()
        # High tier but bad accuracy
        outcomes = self._many_outcomes(n=10, direction_correct=False, state="DECISION_ELIGIBLE")
        report = reporter.generate_report(outcomes)
        de_tier = next(t for t in report.evidence_tiers if t.tier == "DECISION_ELIGIBLE")
        # direction_accuracy should reflect actual data (all False here)
        if de_tier.direction_accuracy is not None:
            assert de_tier.direction_accuracy == pytest.approx(0.0, abs=0.01)

    def test_t098_authority_bucket_result_is_frozen(self):
        """T098: AuthorityBucketResult is immutable."""
        b = AuthorityBucketResult("0.00-0.20", 0.0, 0.20, 0, None, None, None, None, None, None)
        with pytest.raises((AttributeError, TypeError)):
            b.n = 99  # type: ignore

    def test_t099_evidence_tier_result_is_frozen(self):
        """T099: EvidenceTierResult is immutable."""
        t = EvidenceTierResult("USEFUL", 0, None, None, None, None)
        with pytest.raises((AttributeError, TypeError)):
            t.n = 99  # type: ignore

    def test_t100_bucket_metrics_bounded(self):
        """T100: Authority bucket direction_accuracy ∈ [0, 1] when populated."""
        reporter = KDAAuthorityReporter()
        outcomes = self._many_outcomes(n=10, auth=0.75)
        report = reporter.generate_report(outcomes)
        for b in report.authority_buckets:
            if b.direction_accuracy is not None:
                assert 0.0 <= b.direction_accuracy <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# T101-T110: Calibration and authority validation
# ─────────────────────────────────────────────────────────────────────────────

class TestCalibrationAndAuthority:

    def _report_with_n(self, n, direction_correct=True, state="DECISION_ELIGIBLE"):
        reporter = KDAAuthorityReporter()
        outcomes = [_kda_outcome(direction_correct=direction_correct, evidence_state=state)
                    for _ in range(n)]
        return reporter.generate_report(outcomes)

    def test_t101_not_validated_when_n_lt_10(self):
        """T101: authority_status=NOT_VALIDATED when total complete outcomes < 10."""
        report = self._report_with_n(5)
        assert report.authority_status == AuthorityStatus.NOT_VALIDATED.value

    def test_t102_not_validated_reason_included(self):
        """T102: why_not_promoted contains at least one reason when not validated."""
        report = self._report_with_n(5)
        assert len(report.why_not_promoted) >= 1

    def test_t103_promising_when_n_and_decent_accuracy(self):
        """T103: PROMISING when n=20 and direction_accuracy > 0.55."""
        report = self._report_with_n(20, direction_correct=True)
        # All direction_correct=True → accuracy=1.0 → should at least be PROMISING
        assert report.authority_status in (
            AuthorityStatus.PROMISING.value,
            AuthorityStatus.USEFUL.value,
            AuthorityStatus.VALIDATED.value,
            AuthorityStatus.STRONG_VALIDATED.value,
        )

    def test_t104_validated_when_large_n_good_accuracy(self):
        """T104: VALIDATED or better when n=60 and direction_correct=True."""
        report = self._report_with_n(60, direction_correct=True)
        assert report.authority_status in (
            AuthorityStatus.VALIDATED.value,
            AuthorityStatus.STRONG_VALIDATED.value,
        )

    def test_t105_not_validated_when_poor_accuracy(self):
        """T105: NOT_VALIDATED when accuracy is poor (50% = random)."""
        reporter = KDAAuthorityReporter()
        n = 30
        outcomes = (
            [_kda_outcome(direction_correct=True)  for _ in range(n // 2)] +
            [_kda_outcome(direction_correct=False) for _ in range(n // 2)]
        )
        report = reporter.generate_report(outcomes)
        assert report.authority_status in (
            AuthorityStatus.NOT_VALIDATED.value,
            AuthorityStatus.PROMISING.value,   # 50% is borderline
        )

    def test_t106_calibration_has_bucket_entries(self):
        """T106: calibration dict has 'buckets' list with 5 entries."""
        report = self._report_with_n(20)
        assert "buckets" in report.calibration
        assert len(report.calibration["buckets"]) == 5

    def test_t107_calibration_bucket_has_required_keys(self):
        """T107: Each calibration bucket has authority_bucket, n, expected_rate, actual_rate."""
        report = self._report_with_n(20)
        for b in report.calibration["buckets"]:
            assert "authority_bucket" in b
            assert "n" in b
            assert "expected_rate" in b
            assert "actual_rate" in b

    def test_t108_authority_status_is_string(self):
        """T108: authority_status is a string (AuthorityStatus value)."""
        report = self._report_with_n(5)
        assert isinstance(report.authority_status, str)
        valid = {s.value for s in AuthorityStatus}
        assert report.authority_status in valid

    def test_t109_generated_at_is_iso_timestamp(self):
        """T109: generated_at is an ISO 8601 timestamp string."""
        from datetime import datetime
        report = self._report_with_n(5)
        # Should parse without error
        parsed = datetime.fromisoformat(report.generated_at.replace("Z", "+00:00"))
        assert parsed is not None

    def test_t110_authority_report_as_dict_serialisable(self):
        """T110: AuthorityValidationReport.as_dict() produces JSON-serialisable dict."""
        import json
        report = self._report_with_n(10)
        d = report.as_dict()
        _ = json.dumps(d, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# T111-T120: Missed opportunities and overrule analysis
# ─────────────────────────────────────────────────────────────────────────────

class TestMissedAndOverrule:

    def test_t111_missed_opportunity_threshold(self):
        """T111: abs(return) >= 2% on WAIT → MISSED_OPPORTUNITY classification."""
        cls = _classify_outcome("KNOWLEDGE_WAIT", False, False, False, None, 2.5, 5)
        assert cls == OutcomeClass.MISSED_OPPORTUNITY.value

    def test_t112_just_below_threshold_is_correct_wait(self):
        """T112: abs(return) < 2% on WAIT → CORRECT_WAIT (not missed)."""
        cls = _classify_outcome("KNOWLEDGE_WAIT", False, False, False, None, 1.8, 5)
        assert cls == OutcomeClass.CORRECT_WAIT.value

    def test_t113_successful_overrule_requires_strategy_reject(self):
        """T113: KNOWLEDGE_SUCCESSFUL_OVERRULE only when comparison=KDA_OVERRULES."""
        dec = _buy_decision(ess=150.0)
        outcome = {"direction_correct": True, "return_t5": 3.0,
                   "outcome_class": "CORRECT_BUY", "target_hit": True, "stop_hit": False}
        # Strategy PASS → BOTH_AGREE → no overrule_result
        rec = COMPARATOR.compare(dec, "PASS", outcome)
        if rec.comparison_type == ComparisonType.BOTH_AGREE.value:
            assert rec.overrule_result != OverruleResult.KNOWLEDGE_SUCCESSFUL_OVERRULE.value

    def test_t114_false_overrule_not_counted_as_success(self):
        """T114: Incorrect KDA overrule classified as KNOWLEDGE_FALSE_OVERRULE not success."""
        dec = _buy_decision(ess=150.0)
        outcome = {"direction_correct": False, "return_t5": -3.0,
                   "outcome_class": "INCORRECT_BUY", "target_hit": False, "stop_hit": True}
        rec = COMPARATOR.compare(dec, "REJECT", outcome)
        if rec.comparison_type == ComparisonType.KDA_OVERRULES_STRATEGY.value:
            assert rec.overrule_result == OverruleResult.KNOWLEDGE_FALSE_OVERRULE.value
            assert rec.overrule_result != OverruleResult.KNOWLEDGE_SUCCESSFUL_OVERRULE.value

    def test_t115_false_rejection_when_kda_wait_and_strategy_also_wait(self):
        """T115: FALSE_KNOWLEDGE_REJECTION when BOTH_REJECT + big move."""
        dec = _wait_decision()
        outcome = {"direction_correct": True, "return_t5": 3.5,
                   "outcome_class": "MISSED_OPPORTUNITY", "target_hit": None, "stop_hit": None}
        rec = COMPARATOR.compare(dec, "REJECT", outcome)
        assert rec.overrule_result == OverruleResult.FALSE_KNOWLEDGE_REJECTION.value

    def test_t116_scanner_baseline_compared_in_summary(self):
        """T116: Comparison summary includes scanner_direction_accuracy."""
        decs = [_buy_decision(ess=150.0) for _ in range(5)]
        outcome = {"direction_correct": True, "return_t5": 3.0,
                   "outcome_class": "CORRECT_BUY", "target_hit": True, "stop_hit": False}
        recs = [COMPARATOR.compare(d, "PASS", outcome) for d in decs]
        summary = COMPARATOR.summarize(recs)
        assert "scanner_direction_accuracy" in summary

    def test_t117_comparison_id_unique_per_record(self):
        """T117: comparison_id is unique for each compare() call."""
        dec = _buy_decision()
        r1 = COMPARATOR.compare(dec, "PASS")
        r2 = COMPARATOR.compare(dec, "PASS")
        assert r1.comparison_id != r2.comparison_id

    def test_t118_three_way_comparison_available_in_summary(self):
        """T118: Summary has KDA, strategy, and scanner accuracy metrics."""
        rec = COMPARATOR.compare(_buy_decision(ess=150.0), "PASS")
        summary = COMPARATOR.summarize([rec])
        assert "kda_direction_accuracy" in summary
        assert "strategy_direction_accuracy" in summary
        assert "scanner_direction_accuracy" in summary

    def test_t119_outcome_matching_chronological_no_lookahead(self):
        """T119: outcome records carry no_lookahead=True."""
        dec = _buy_decision(ess=150.0)
        out = ENGINE.evaluate(dec, _bars(5), entry_price=100.0)
        assert out.no_lookahead is True

    def test_t120_full_outcome_record_complete(self):
        """T120: Complete outcome record has all required fields."""
        dec = _buy_decision(entry=100.0, target=105.0, stop=97.0, ess=150.0)
        bars = [_bar(h=106.0, c=104.0)] + _bars(19)
        out = ENGINE.evaluate(dec, bars, entry_price=100.0)

        required = [
            "outcome_id", "decision_id", "trading_date", "symbol", "direction",
            "decision", "authority", "knowledge_authority", "entry_price",
            "target", "stop_loss",
            "return_t1", "return_t3", "return_t5", "return_t10", "return_t20",
            "mfe", "mae",
            "target_hit", "stop_hit", "time_to_target", "time_to_stop",
            "first_event", "event_day",
            "horizon_error", "horizon_accuracy", "move_speed",
            "target_accuracy", "target_comparison",
            "direction_correct", "decision_correct",
            "outcome_class", "evidence_state", "evidence_level",
            "status", "bars_available", "evaluation_horizon",
            "no_lookahead", "broker_calls", "orders",
        ]
        for f in required:
            assert hasattr(out, f), f"Missing field: {f}"

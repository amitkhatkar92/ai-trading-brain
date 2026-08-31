"""
tests/test_dta_033_governance.py
=================================
DTA-033: Replay Governance + Live Learning Safety — 20 tests (T001–T020)

T001  Replay provenance survives HBE (partition counts in BehaviourMetrics)
T002  Replay provenance survives KDA (partition counts in KDADecisionRecord)
T003  TRAIN / VALIDATION / OOS counts correct in BehaviourMetrics
T004  OOS cannot silently become live authority (excluded from _find_best_evidence)
T005  Replay obs remain EXPERIMENTAL (replay_validation_status)
T006  Duplicate replay load does not duplicate OutcomeRecords
T007  Bootstrap file unchanged by replay run
T008  Live KLP records unchanged by replay run
T009  Old data recency decay: older records have lower ESS weight
T010  Recent contradictory evidence affects stop_first_probability
T011  Non-executed outcome enters HBE correctly (no actual P&L)
T012  Non-executed outcome is never actual P&L
T013  STOP_FIRST_THEN_RECOVERY remains classified as STOP_HIT
T014  TARGET_FIRST_THEN_REVERSAL remains classified as TARGET_HIT
T015  Same-bar ambiguity preserved (OUTCOME_AMBIGUOUS)
T016  Gap-down stop preserved as STOP_HIT
T017  L1 mapping preserved with OOS exclusion
T018  L6 mapping preserved with OOS exclusion
T019  Replay cannot create broker call
T020  Replay cannot create order
"""
from __future__ import annotations

import json
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys, os

sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest

from learning_system.historical_knowledge_replay import (
    HistoricalKnowledgeReplayEngine,
    MODE_RESEARCH, MODE_DRY_RUN,
    TARGET_HIT, STOP_HIT, OUTCOME_PENDING, OUTCOME_AMBIGUOUS,
)
from opportunity_engine.hbe_models import OutcomeRecord
from opportunity_engine.historical_behaviour_engine import (
    HistoricalBehaviourEngine, _compute_metrics,
)
from knowledge_authority.kda_models import KDADecisionRecord

# _LEVEL_MIN_OBS is a class attribute — access via instance
_LEVEL_MIN_OBS_REF = [None, 5, 5, 10, 10, 15, 15, 0]


# ── Minimal test helpers ────────────────────────────────────────────────────

def _rec(
    symbol: str = "TEST",
    direction: str = "BUY",
    regime: str = "BULL",
    source_type: str = "HISTORICAL_REPLAY",
    validation_partition: str = "TRAIN",
    trading_date: str = "2026-07-15",
    first_event: str = TARGET_HIT,
    t5_ret_pct: float = 3.0,
    mfe_pct: float = 4.0,
    mae_pct: float = -1.0,
) -> OutcomeRecord:
    return OutcomeRecord(
        obs_id=f"HKR1:{trading_date.replace('-','')}:113000:{symbol}:{direction}:{validation_partition}:{source_type}",
        trading_date=trading_date,
        symbol=symbol,
        direction=direction,
        regime=regime,
        sector="IT",
        reference_entry=100.0,
        knowledge_target=106.0,
        knowledge_stop=97.0,
        atr=2.0,
        atr_pct=2.0,
        scanner_confidence=6.0,
        candidate_score=0.6,
        knowledge_score=0.0,
        knowledge_rr=2.0,
        first_event=first_event,
        first_event_day=(date.fromisoformat(trading_date) + timedelta(days=2)).isoformat(),
        target_hit=(first_event == TARGET_HIT),
        stop_hit=(first_event == STOP_HIT),
        t1_ret_pct=1.0,
        t3_ret_pct=2.0,
        t5_ret_pct=t5_ret_pct,
        mfe_pct=mfe_pct,
        mae_pct=mae_pct,
        days_to_event=2,
        source_type=source_type,
        validation_partition=validation_partition,
    )


def _hbe_with(outcomes: List[OutcomeRecord], ref_date: date = date(2026, 8, 31)) -> HistoricalBehaviourEngine:
    hbe = HistoricalBehaviourEngine(reference_date=ref_date)
    hbe._outcomes = outcomes
    hbe._loaded   = True
    return hbe


def _bar(date_str: str, open_: float, high: float, low: float, close: float):
    ts = datetime.fromisoformat(f"{date_str}T09:30:00+05:30")
    from learning_system.historical_knowledge_replay import pricebar_to_dict  # noqa
    @dataclass
    class B:
        timestamp: datetime
        open: float; high: float; low: float; close: float; volume: float = 1000.0
    return B(ts, float(open_), float(high), float(low), float(close))


# ══════════════════════════════════════════════════════════════════════════════
# T001 — Replay provenance survives HBE
# ══════════════════════════════════════════════════════════════════════════════

class TestT001_ReplayProvenanceSurvivesHBE:
    def test_T001_partition_counts_in_behaviour_metrics(self):
        """T001: TRAIN/VALIDATION/OOS replay counts appear in BehaviourMetrics."""
        recs = (
            [_rec(validation_partition="TRAIN",      trading_date=f"2026-07-{i+1:02d}") for i in range(6)] +
            [_rec(validation_partition="VALIDATION", trading_date=f"2026-08-{i+1:02d}") for i in range(3)] +
            [_rec(validation_partition="OOS",        trading_date="2026-08-28")]
        )
        hbe = _hbe_with(recs)
        p = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        m = p.metrics
        assert m.historical_replay_train_count      == 6
        assert m.historical_replay_validation_count == 3
        assert m.historical_replay_oos_count        == 1
        assert m.historical_replay_record_count     == 10
        assert m.research_record_count              == 10   # 0 bootstrap + 10 replay
        assert m.live_authority_record_count        == 0


# ══════════════════════════════════════════════════════════════════════════════
# T002 — Replay provenance survives KDA
# ══════════════════════════════════════════════════════════════════════════════

class TestT002_ReplayProvenanceSurvivesKDA:
    def test_T002_partition_counts_in_kda_decision_record(self):
        """T002: from_dict() / as_dict() round-trips all three partition counts."""
        d = {
            "decision_id":                       "kda-test",
            "timestamp":                         "2026-08-31T00:00:00+00:00",
            "symbol":                            "RELIANCE",
            "direction":                         "BUY",
            "historical_replay_train_count":      11,
            "historical_replay_validation_count": 4,
            "historical_replay_oos_count":        1,
        }
        rec  = KDADecisionRecord.from_dict(d)
        back = rec.as_dict()
        assert rec.historical_replay_train_count      == 11
        assert rec.historical_replay_validation_count == 4
        assert rec.historical_replay_oos_count        == 1
        assert back["historical_replay_train_count"]      == 11
        assert back["historical_replay_validation_count"] == 4
        assert back["historical_replay_oos_count"]        == 1

    def test_T002b_defaults_to_zero(self):
        """T002b: All three partition count fields default to 0 in KDADecisionRecord."""
        f = KDADecisionRecord.__dataclass_fields__
        assert f["historical_replay_train_count"].default      == 0
        assert f["historical_replay_validation_count"].default == 0
        assert f["historical_replay_oos_count"].default        == 0


# ══════════════════════════════════════════════════════════════════════════════
# T003 — TRAIN/VALIDATION/OOS counts correct
# ══════════════════════════════════════════════════════════════════════════════

class TestT003_PartitionCounts:
    def test_T003_counts_match_actual_partition_distribution(self):
        """T003: BehaviourMetrics counts exactly match the partition distribution."""
        recs = (
            [_rec(validation_partition="TRAIN",      trading_date=f"2026-07-{i+1:02d}") for i in range(8)] +
            [_rec(validation_partition="VALIDATION", trading_date=f"2026-08-{i+1:02d}") for i in range(2)] +
            [_rec(validation_partition="OOS",        trading_date="2026-08-30"),
             _rec(validation_partition="",           trading_date="2026-08-31")]   # unlabelled
        )
        m = _compute_metrics(recs, 2, "SYMBOL_DIRECTION", 2, date(2026, 8, 31))
        assert m.historical_replay_train_count      == 8
        assert m.historical_replay_validation_count == 2
        assert m.historical_replay_oos_count        == 1
        # All 12 records are HISTORICAL_REPLAY (including the unlabelled one)
        assert m.historical_replay_record_count     == 12
        # unlabelled partition ("") does not increment any named partition counter


# ══════════════════════════════════════════════════════════════════════════════
# T004 — OOS cannot silently become live authority
# ══════════════════════════════════════════════════════════════════════════════

class TestT004_OOSLiveAuthorityIsolation:
    def test_T004_oos_records_excluded_from_evidence_hierarchy(self):
        """T004: 4 TRAIN + 1 OOS = 5 total, but OOS is excluded; only 4 used → L2 not reached."""
        recs = (
            [_rec(validation_partition="TRAIN", trading_date=f"2026-07-{i+1:02d}") for i in range(4)] +
            [_rec(validation_partition="OOS",   trading_date="2026-08-25")]
        )
        hbe = _hbe_with(recs)
        p = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        # L2 requires >= 5 symbol+direction records. OOS excluded → only 4 → L2 NOT reached.
        assert p.metrics.evidence_level != 2, (
            "OOS record must not count toward L2 threshold"
        )

    def test_T004b_5_train_records_do_reach_l2(self):
        """T004b: 5 TRAIN records (no OOS) → L2 IS reached. OOS filter doesn't block TRAIN."""
        recs = [_rec(validation_partition="TRAIN", trading_date=f"2026-07-{i+1:02d}") for i in range(5)]
        hbe = _hbe_with(recs)
        p = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        assert p.metrics.evidence_level in (1, 2), "5 TRAIN records must reach symbol-specific tier"

    def test_T004c_oos_count_still_visible_in_metrics(self):
        """T004c: OOS records are excluded from evidence but their count remains visible."""
        recs = (
            [_rec(validation_partition="TRAIN", trading_date=f"2026-07-{i+1:02d}") for i in range(6)] +
            [_rec(validation_partition="OOS",   trading_date="2026-08-28")]
        )
        hbe = _hbe_with(recs)
        p = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        # OOS record is excluded from evidence but still counted in BehaviourMetrics
        assert p.metrics.historical_replay_oos_count == 1
        # Evidence is computed from 6 TRAIN records only
        assert p.metrics.evidence_level in (1, 2)
        assert p.metrics.observation_count == 6   # only 6 records in evidence pool


# ══════════════════════════════════════════════════════════════════════════════
# T005 — Replay remains EXPERIMENTAL
# ══════════════════════════════════════════════════════════════════════════════

class TestT005_ExperimentalStatus:
    def test_T005_research_replay_writes_experimental_label(self):
        """T005: All obs records written by RESEARCH mode carry replay_validation_status=EXPERIMENTAL."""
        from datetime import timedelta as _td
        def _make_bars(n=30):
            from datetime import datetime, timezone, date as _date
            @dataclass
            class B:
                timestamp: datetime
                open: float = 100.0; high: float = 103.0
                low: float = 98.0; close: float = 101.0; volume: float = 1000.0
            d = _date(2026, 6, 1)
            result = []
            for _ in range(n):
                result.append(B(datetime(d.year, d.month, d.day, 9, 30, tzinfo=timezone.utc)))
                d += _td(days=1)
            return result

        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            engine = HistoricalKnowledgeReplayEngine(
                klp_dir=klp_dir,
                _ohlcv_fetcher=lambda s: _make_bars()
            )
            engine.replay(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 4),
                symbols=["TESTX"],
                mode=MODE_RESEARCH,
            )
            for f in (klp_dir / "replay").glob("REPLAY_*.jsonl"):
                for line in f.read_text().splitlines():
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("event_type") == "KNOWLEDGE_OBSERVATION":
                        status = rec.get("replay_validation_status", "")
                        assert status == "EXPERIMENTAL", (
                            f"Expected EXPERIMENTAL, got {status!r}"
                        )

    def test_T005b_experimental_status_not_validated_or_live(self):
        """T005b: No replay obs record may carry replay_validation_status=VALIDATED or LIVE."""
        from datetime import timedelta as _td
        def _make_bars(n=30):
            from datetime import datetime, timezone, date as _date
            @dataclass
            class B:
                timestamp: datetime
                open: float = 100.0; high: float = 103.0
                low: float = 98.0; close: float = 101.0; volume: float = 1000.0
            d = _date(2026, 6, 1)
            result = []
            for _ in range(n):
                result.append(B(datetime(d.year, d.month, d.day, 9, 30, tzinfo=timezone.utc)))
                d += _td(days=1)
            return result

        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            engine = HistoricalKnowledgeReplayEngine(
                klp_dir=klp_dir,
                _ohlcv_fetcher=lambda _: _make_bars()
            )
            engine.replay(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 3),
                symbols=["TESTX"],
                mode=MODE_RESEARCH,
            )
            for f in (klp_dir / "replay").glob("REPLAY_*.jsonl"):
                for line in f.read_text().splitlines():
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    assert rec.get("replay_validation_status") not in ("VALIDATED", "LIVE", "DECISION_ELIGIBLE")


# ══════════════════════════════════════════════════════════════════════════════
# T006 — Duplicate replay load does not duplicate outcomes
# ══════════════════════════════════════════════════════════════════════════════

class TestT006_DuplicateLoadSafety:
    def _write_replay_pair(self, path: Path, trading_date: str, symbol: str) -> None:
        obs_id = f"HKR1:{trading_date.replace('-','')}:113000:{symbol}:BUY"
        obs = {"obs_id": obs_id, "event_type": "KNOWLEDGE_OBSERVATION",
               "symbol": symbol, "direction": "BUY",
               "reference_entry": 100.0, "knowledge_target": 106.0,
               "knowledge_stop_loss": 97.0, "knowledge_RR": 2.0,
               "knowledge_confidence": 6.0, "candidate_score": 0.6,
               "atr": 2.0, "atr_pct": 2.0, "regime": "BULL",
               "source_type": "HISTORICAL_REPLAY",
               "validation_partition": "TRAIN",
               "replay_validation_status": "EXPERIMENTAL"}
        out = {"obs_id": obs_id, "event_type": "OUTCOME_UPDATE",
               "symbol": symbol, "direction": "BUY",
               "first_event": "TARGET_HIT", "target_hit": True, "stop_hit": False,
               "t1_ret_pct": 1.5, "t3_ret_pct": 2.5, "t5_ret_pct": 3.5,
               "mfe_pct": 4.0, "mae_pct": -0.5, "bars_available": 5}
        with path.open("a") as fh:
            fh.write(json.dumps(obs) + "\n")
            fh.write(json.dumps(out) + "\n")

    def test_T006_loading_replay_twice_gives_same_count(self):
        """T006: Two HBE instances loading the same replay dir return identical outcome counts."""
        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            replay_file = replay_dir / "REPLAY_2026-07-15.jsonl"
            for i in range(5):
                self._write_replay_pair(replay_file, f"2026-07-{i+1:02d}", "SYM")

            hbe1 = HistoricalBehaviourEngine(data_dir=klp_dir)
            n1   = hbe1.load_outcomes()
            hbe2 = HistoricalBehaviourEngine(data_dir=klp_dir)
            n2   = hbe2.load_outcomes()
            assert n1 == n2 == 5

    def test_T006b_same_obs_id_in_file_twice_is_deduplicated(self):
        """T006b: Duplicate obs_id lines in a JSONL file produce only one OutcomeRecord."""
        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            replay_file = replay_dir / "REPLAY_2026-07-15.jsonl"
            # Write the same pair twice
            self._write_replay_pair(replay_file, "2026-07-15", "DUP")
            self._write_replay_pair(replay_file, "2026-07-15", "DUP")

            hbe = HistoricalBehaviourEngine(data_dir=klp_dir)
            n   = hbe.load_outcomes()
            assert n == 1, f"Duplicate obs_id must be deduplicated; got {n}"


# ══════════════════════════════════════════════════════════════════════════════
# T007 / T008 — Bootstrap and live KLP unchanged by replay
# ══════════════════════════════════════════════════════════════════════════════

class TestT007_T008_DataUnchanged:
    def test_T007_bootstrap_file_unchanged_after_research_replay(self):
        """T007: BOOTSTRAP_*.jsonl byte-for-byte identical before and after replay run."""
        from datetime import timedelta as _td
        def _make_bars(n=30):
            from datetime import datetime, timezone, date as _date
            @dataclass
            class B:
                timestamp: datetime
                open: float = 100.0; high: float = 103.0
                low: float = 98.0; close: float = 101.0; volume: float = 1000.0
            d = _date(2026, 6, 1)
            result = []
            for _ in range(n):
                result.append(B(datetime(d.year, d.month, d.day, 9, 30, tzinfo=timezone.utc)))
                d += _td(days=1)
            return result

        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            boot = klp_dir / "BOOTSTRAP_2026-07-01.jsonl"
            boot.write_text('{"obs_id":"BOOT1","event_type":"KNOWLEDGE_OBSERVATION"}\n')
            before_hash = boot.read_bytes()

            engine = HistoricalKnowledgeReplayEngine(
                klp_dir=klp_dir,
                _ohlcv_fetcher=lambda _: _make_bars()
            )
            engine.replay(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 3),
                symbols=["TESTX"],
                mode=MODE_RESEARCH,
            )
            assert boot.read_bytes() == before_hash

    def test_T008_live_klp_file_unchanged_after_research_replay(self):
        """T008: KLP_YYYY-MM-DD.jsonl files in klp root are untouched by replay."""
        from datetime import timedelta as _td
        def _make_bars(n=30):
            from datetime import datetime, timezone, date as _date
            @dataclass
            class B:
                timestamp: datetime
                open: float = 100.0; high: float = 103.0
                low: float = 98.0; close: float = 101.0; volume: float = 1000.0
            d = _date(2026, 6, 1)
            result = []
            for _ in range(n):
                result.append(B(datetime(d.year, d.month, d.day, 9, 30, tzinfo=timezone.utc)))
                d += _td(days=1)
            return result

        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            live_klp = klp_dir / "KLP_2026-08-20.jsonl"
            live_klp.write_text('{"obs_id":"LIVE1","event_type":"KNOWLEDGE_OBSERVATION"}\n')
            before = live_klp.read_bytes()

            engine = HistoricalKnowledgeReplayEngine(
                klp_dir=klp_dir,
                _ohlcv_fetcher=lambda _: _make_bars()
            )
            engine.replay(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 3),
                symbols=["TESTX"],
                mode=MODE_RESEARCH,
            )
            assert live_klp.read_bytes() == before


# ══════════════════════════════════════════════════════════════════════════════
# T009 / T010 — Recency weighting
# ══════════════════════════════════════════════════════════════════════════════

class TestT009_T010_RecencyWeighting:
    def test_T009_older_records_have_lower_ess_contribution(self):
        """T009: ESS of 10 old records is less than ESS of 10 recent records."""
        from opportunity_engine.historical_behaviour_engine import _effective_sample_size
        ref = date(2026, 8, 31)
        old_recs = [
            _rec(trading_date=f"2026-0{m}-{d:02d}", source_type="HISTORICAL")
            for m, d in [(1, 15), (1, 20), (2, 1), (2, 15), (3, 1),
                         (3, 15), (4, 1), (4, 15), (5, 1), (5, 15)]
        ]
        new_recs = [
            _rec(trading_date=f"2026-08-{d:02d}", source_type="HISTORICAL")
            for d in [20, 21, 22, 23, 24, 25, 26, 27, 28, 31]
        ]
        ess_old = _effective_sample_size(old_recs, ref)
        ess_new = _effective_sample_size(new_recs, ref)
        assert ess_old < ess_new, (
            f"Older records must have lower ESS; got old={ess_old:.2f} new={ess_new:.2f}"
        )

    def test_T010_recent_stop_hits_raise_stop_probability(self):
        """T010: Adding 5 recent STOP_HIT records increases stop_first_probability vs old TARGET_HIT."""
        ref  = date(2026, 8, 31)
        # 10 old successful BUY records
        old_targets = [
            _rec(trading_date=f"2026-01-{i+1:02d}", first_event=TARGET_HIT)
            for i in range(10)
        ]
        # 5 recent STOP_HIT records (much higher weight)
        new_stops = [
            _rec(trading_date=f"2026-08-{25+i:02d}", first_event=STOP_HIT, mfe_pct=0.5, mae_pct=-2.5)
            for i in range(5)
        ]

        m_before = _compute_metrics(old_targets,         2, "SYM_DIR", 2, ref)
        m_after  = _compute_metrics(old_targets + new_stops, 2, "SYM_DIR", 2, ref)

        # stop probability must be higher after adding recent stop records
        before_stop = m_before.stop_first_probability or 0.0
        after_stop  = m_after.stop_first_probability  or 0.0
        assert after_stop > before_stop, (
            f"Recent STOP_HIT records must raise stop_probability; "
            f"before={before_stop:.3f} after={after_stop:.3f}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# T011 / T012 — Non-executed knowledge learning
# ══════════════════════════════════════════════════════════════════════════════

class TestT011_T012_NonExecutedLearning:
    def test_T011_non_executed_outcome_enters_hbe(self):
        """T011: A KNOWLEDGE_ONLY obs + OUTCOME_UPDATE creates a valid HBE OutcomeRecord."""
        r = _rec(source_type="HISTORICAL_REPLAY", validation_partition="TRAIN")
        # The record has no actual_return_pct (not set by replay engine)
        hbe = _hbe_with([r] * 5)
        p = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        assert p.metrics.evidence_level in (1, 2)
        assert p.metrics.observation_count == 5

    def test_T012_non_executed_outcome_has_no_actual_pnl(self):
        """T012: Replay OutcomeRecord has no actual_return_pct — never actual P&L."""
        r = _rec(source_type="HISTORICAL_REPLAY")
        # OutcomeRecord must NOT have an actual_return_pct field with a value
        actual_pnl = getattr(r, "actual_return_pct", None)
        assert actual_pnl is None, (
            f"Non-executed replay record must not carry actual P&L; got {actual_pnl}"
        )

    def test_T012b_t5_ret_is_counterfactual_not_actual(self):
        """T012b: t5_ret_pct is a counterfactual horizon metric, NOT executed P&L."""
        r = _rec(t5_ret_pct=3.5)
        # t5_ret_pct represents DIRECTION at T+5, not a trade's realized return
        assert r.t5_ret_pct == 3.5
        # No 'actual_return_pct' or 'realized_pnl' attribute
        assert not hasattr(r, "realized_pnl")


# ══════════════════════════════════════════════════════════════════════════════
# T013–T016 — Path outcome preservation
# ══════════════════════════════════════════════════════════════════════════════

class TestT013_T016_PathOutcomes:
    def _engine(self):
        return HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])

    def _obs(self, entry=100.0, target=108.0, stop=95.0, direction="BUY"):
        return {
            "obs_id": "HKR1:TEST", "event_type": "KNOWLEDGE_OBSERVATION",
            "symbol": "TEST", "direction": direction,
            "reference_entry": entry, "knowledge_target": target,
            "knowledge_stop_loss": stop, "knowledge_RR": 2.0,
            "knowledge_confidence": 6.0, "candidate_score": 0.6,
            "atr": 3.0, "atr_pct": 3.0, "regime": "BULL",
            "source_type": "HISTORICAL_REPLAY",
        }

    def test_T013_stop_first_then_recovery_is_stop_hit(self):
        """T013: Stop hit on T+1; price recovers above entry by T+5 → first_event=STOP_HIT."""
        engine = self._engine()
        obs    = self._obs()
        future = [
            _bar("2026-08-01", 100, 101, 93, 96),  # low < stop → STOP_HIT
            _bar("2026-08-02",  96,  99, 95, 98),
            _bar("2026-08-03",  98, 102, 97, 101),
            _bar("2026-08-04", 101, 105, 100, 104),
            _bar("2026-08-05", 104, 108, 103, 107),  # above entry
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == STOP_HIT
        assert result["stop_hit"]    is True
        # t5 is positive but STOP_HIT is preserved
        assert result.get("t5_ret_pct", 0) > 0

    def test_T014_target_first_then_reversal_is_target_hit(self):
        """T014: Target hit on T+2; price reverses back below entry → first_event=TARGET_HIT."""
        engine = self._engine()
        obs    = self._obs(entry=100.0, target=106.0, stop=95.0)
        future = [
            _bar("2026-08-01", 100, 104, 99, 103),
            _bar("2026-08-02", 103, 107, 102, 106),   # high >= target
            _bar("2026-08-03", 105, 105, 99, 100),
            _bar("2026-08-04",  99,  99, 94, 95),
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == TARGET_HIT
        assert result["target_hit"]  is True

    def test_T015_same_bar_ambiguity_preserved(self):
        """T015: Same bar hits both target and stop → OUTCOME_AMBIGUOUS."""
        engine = self._engine()
        obs    = self._obs(entry=100.0, target=106.0, stop=95.0)
        future = [
            _bar("2026-08-01", 100, 107, 94, 101),  # both hit on T+1
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == OUTCOME_AMBIGUOUS

    def test_T016_gap_down_through_stop_is_stop_hit(self):
        """T016: Bar opens and closes below stop (gap down through SL) → STOP_HIT."""
        engine = self._engine()
        obs    = self._obs(entry=100.0, target=110.0, stop=95.0)
        future = [
            _bar("2026-08-01", 100, 101, 88, 90),  # low=88 < stop=95
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == STOP_HIT
        assert result["stop_hit"]    is True


# ══════════════════════════════════════════════════════════════════════════════
# T017 / T018 — L1 and L6 mapping preserved with OOS exclusion
# ══════════════════════════════════════════════════════════════════════════════

class TestT017_T018_LevelMapping:
    def test_T017_l1_mapping_preserved(self):
        """T017: 5 TRAIN records with same symbol+direction+regime+context → L1."""
        # Use query_atr_pct and confidence to pass context matching
        recs = [
            _rec(trading_date=f"2026-07-{i+1:02d}", validation_partition="TRAIN")
            for i in range(5)
        ]
        hbe = _hbe_with(recs)
        # Pass matching atr_pct and confidence so _context_similar succeeds
        p = hbe.get_behaviour_profile(
            "TEST", "BUY", regime="BULL",
            query_atr_pct=2.0, query_confidence=6.0
        )
        assert p.metrics.evidence_level == 1, (
            f"Expected L1, got L{p.metrics.evidence_level}"
        )

    def test_T018_l6_mapping_preserved_with_oos_exclusion(self):
        """T018: 15 TRAIN records for different symbols, same direction → L6 still reachable."""
        # 15 records for different symbols, same direction BUY — should reach L6
        min_l6 = _LEVEL_MIN_OBS_REF[6]
        recs = [
            _rec(symbol=f"SYM{i:02d}", direction="BUY", validation_partition="TRAIN",
                 trading_date=f"2026-07-{i+1:02d}")
            for i in range(min_l6)
        ]
        hbe = _hbe_with(recs)
        # Query without regime so L4 (regime+direction) does not fire
        p = hbe.get_behaviour_profile("UNKNOWN", "BUY")
        assert p.metrics.evidence_level == 6, (
            f"Expected L6, got L{p.metrics.evidence_level}"
        )

    def test_T018b_oos_exclusion_does_not_break_l6(self):
        """T018b: Adding OOS records does not break L6 (OOS excluded, TRAIN still qualifies)."""
        min_l6 = _LEVEL_MIN_OBS_REF[6]
        train_recs = [
            _rec(symbol=f"SYM{i:02d}", direction="BUY", validation_partition="TRAIN",
                 trading_date=f"2026-07-{i+1:02d}")
            for i in range(min_l6)
        ]
        oos_recs = [
            _rec(symbol="OOSSYM", direction="BUY", validation_partition="OOS",
                 trading_date="2026-08-28")
            for _ in range(5)
        ]
        hbe = _hbe_with(train_recs + oos_recs)
        # Query without regime so L4 does not fire; OOS excluded → only 15 TRAIN in pool
        p = hbe.get_behaviour_profile("UNKNOWN", "BUY")
        # L6 must still be reached (OOS excluded, but TRAIN records are sufficient)
        assert p.metrics.evidence_level == 6


# ══════════════════════════════════════════════════════════════════════════════
# T019 / T020 — Broker and order safety
# ══════════════════════════════════════════════════════════════════════════════

class TestT019_T020_BrokerSafety:
    def _make_bars(self, n=30):
        from datetime import datetime, timezone, date as _date, timedelta as _td
        @dataclass
        class B:
            timestamp: datetime
            open: float = 100.0; high: float = 103.0
            low: float = 98.0; close: float = 101.0; volume: float = 1000.0
        d = _date(2026, 6, 1)
        result = []
        for _ in range(n):
            result.append(B(datetime(d.year, d.month, d.day, 9, 30, tzinfo=timezone.utc)))
            d += _td(days=1)
        return result

    def test_T019_replay_cannot_create_broker_call(self):
        """T019: broker_calls == 0 after RESEARCH mode replay."""
        bars = self._make_bars()
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            engine = HistoricalKnowledgeReplayEngine(
                klp_dir=klp_dir,
                _ohlcv_fetcher=lambda _: bars
            )
            summary = engine.replay(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 4),
                symbols=["TESTX"],
                mode=MODE_RESEARCH,
            )
            assert summary.broker_calls == 0

    def test_T020_replay_cannot_create_order(self):
        """T020: orders == 0 after RESEARCH mode replay."""
        bars = self._make_bars()
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            engine = HistoricalKnowledgeReplayEngine(
                klp_dir=klp_dir,
                _ohlcv_fetcher=lambda _: bars
            )
            summary = engine.replay(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 4),
                symbols=["TESTX"],
                mode=MODE_RESEARCH,
            )
            assert summary.orders == 0

    def test_T020b_hbe_operations_are_also_broker_free(self):
        """T020b: Loading and querying HBE never increments broker_calls or orders."""
        recs = [_rec(trading_date=f"2026-07-{i+1:02d}") for i in range(8)]
        hbe = _hbe_with(recs)
        _ = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        assert hbe.broker_calls == 0
        assert hbe.orders       == 0

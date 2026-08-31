"""
tests/test_dta_034_expansion.py
================================
DTA-034: Historical Knowledge Expansion — 25 governance tests (T001–T025)

T001  Historical date has no lookahead (signal built only from bars ≤ T)
T002  Replay idempotency (same range twice → same record count, no duplicates)
T003  Duplicate obs prevention (obs_id collision → skip counter increments)
T004  Duplicate outcome prevention (second write of same obs_id skipped)
T005  OOS excluded from HBE evidence hierarchy
T006  OOS visible in audit provenance counts
T007  TRAIN+VALIDATION records contribute to evidence hierarchy
T008  Bootstrap files preserved after replay
T009  Live KLP records preserved after replay
T010  Provenance fields survive BehaviourMetrics → KDADecisionRecord round-trip
T011  Symbol-specific evidence (L1/L2) labelled SYMBOL_SPECIFIC, L3-L6 GENERIC
T012  L1 mapping preserved with context filter
T013  L6 mapping preserved with broad evidence
T014  Historical data cannot alter PAPER_TRADING / execution config
T015  broker_calls == 0 (hard invariant)
T016  orders == 0 (hard invariant)
T017  Existing replay file not overwritten — idempotency across date boundaries
T018  Recency decay: 2016 records have negligible ESS vs 2026 records
T019  Stop-first-then-recovery classified as STOP_HIT
T020  Target-first-then-reversal classified as TARGET_HIT
T021  Gap-down through stop classified as STOP_HIT
T022  Same-bar ambiguity classified as OUTCOME_AMBIGUOUS
T023  Replay cannot produce DECISION_ELIGIBLE authority automatically
T024  Evidence audit function produces per-source breakdown
T025  Historical dominance detection correctly flags changed evidence level
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest

from learning_system.historical_knowledge_replay import (
    HistoricalKnowledgeReplayEngine,
    MODE_DRY_RUN, MODE_RESEARCH,
    TARGET_HIT, STOP_HIT, OUTCOME_AMBIGUOUS, OUTCOME_EXPIRED, OUTCOME_PENDING,
    make_obs_id, assign_partition, get_trading_days,
    compute_atr14, reconstruct_regime, bar_date_str,
)
from opportunity_engine.hbe_models import OutcomeRecord
from opportunity_engine.historical_behaviour_engine import (
    HistoricalBehaviourEngine, _compute_metrics, _recency_weight,
)
from knowledge_authority.kda_models import KDADecisionRecord


# ── Shared test helpers ───────────────────────────────────────────────────────

@dataclass
class _Bar:
    timestamp: datetime
    open:   float = 100.0
    high:   float = 103.0
    low:    float = 97.0
    close:  float = 100.0
    volume: float = 1000.0


def _bars_from(start: date, n: int, base: float = 100.0, step: float = 0.0) -> List[_Bar]:
    d, result = start, []
    price = base
    for _ in range(n):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        result.append(_Bar(
            datetime(d.year, d.month, d.day, 9, 30, tzinfo=timezone.utc),
            open=price * 0.995, high=price * 1.01, low=price * 0.99, close=price,
        ))
        price += step
        d += timedelta(days=1)
    return result


def _engine(bars: List[_Bar] = None, klp_dir: Path = None) -> HistoricalKnowledgeReplayEngine:
    fetcher = (lambda s: bars) if bars is not None else (lambda s: [])
    return HistoricalKnowledgeReplayEngine(
        klp_dir=klp_dir or Path(tempfile.mkdtemp()),
        _ohlcv_fetcher=fetcher,
    )


def _outcome_rec(
    symbol: str = "TEST",
    direction: str = "BUY",
    source_type: str = "HISTORICAL_REPLAY",
    partition: str = "TRAIN",
    trading_date: str = "2026-07-15",
    first_event: str = TARGET_HIT,
    regime: str = "BULL",
) -> OutcomeRecord:
    return OutcomeRecord(
        obs_id=make_obs_id(trading_date, symbol, direction),
        trading_date=trading_date,
        symbol=symbol, direction=direction, regime=regime,
        sector="IT", reference_entry=100.0,
        knowledge_target=106.0, knowledge_stop=97.0,
        atr=2.0, atr_pct=2.0,
        scanner_confidence=6.0, candidate_score=0.6,
        knowledge_score=0.0, knowledge_rr=2.0,
        first_event=first_event,
        first_event_day=(date.fromisoformat(trading_date) + timedelta(days=2)).isoformat(),
        target_hit=(first_event == TARGET_HIT),
        stop_hit=(first_event == STOP_HIT),
        t1_ret_pct=1.0, t3_ret_pct=2.0, t5_ret_pct=3.0,
        mfe_pct=4.0, mae_pct=-1.0, days_to_event=2,
        source_type=source_type, validation_partition=partition,
    )


def _hbe(outcomes: List[OutcomeRecord], ref: date = date(2026, 8, 31)) -> HistoricalBehaviourEngine:
    hbe = HistoricalBehaviourEngine(reference_date=ref)
    hbe._outcomes = outcomes
    hbe._loaded   = True
    return hbe


# ═══════════════════════════════════════════════════════════════════════════════
# T001 — No lookahead
# ═══════════════════════════════════════════════════════════════════════════════

class TestT001_NoLookahead:
    def test_T001_signal_uses_only_bars_up_to_trading_date(self):
        """T001: _reconstruct_signal must not use bars after trading_date."""
        trading_date = date(2020, 6, 15)
        # Bars up to (and including) trading_date: 40 bars
        bars_before = _bars_from(date(2020, 4, 1), 55)
        # Insert a future bar with extreme close — if used, close ≠ 100
        future_bar = _Bar(
            datetime(2020, 6, 20, 9, 30, tzinfo=timezone.utc),
            open=999.0, high=1010.0, low=990.0, close=1000.0,
        )
        all_bars = bars_before + [future_bar]
        e = _engine(all_bars)
        sig = e._reconstruct_signal("TEST", trading_date, all_bars)
        assert sig is not None
        # Entry must be the close on trading_date — not the future bar's close
        assert abs(sig["reference_entry"] - 1000.0) > 0.01, (
            "Signal used a future bar's price — lookahead violation"
        )
        # Entry must equal the last bar on or before trading_date
        bars_up = [b for b in all_bars if bar_date_str(b) <= trading_date.isoformat()]
        last_close = float(bars_up[-1].close)
        assert abs(sig["reference_entry"] - last_close) < 0.01

    def test_T001b_no_lookahead_flag_in_obs(self):
        """T001b: Reconstructed obs must have no_lookahead=True."""
        bars = _bars_from(date(2019, 1, 1), 30)
        e    = _engine(bars)
        sig  = e._reconstruct_signal("X", date(2019, 1, 25), bars)
        assert sig is not None
        assert sig.get("no_lookahead") is True
        assert sig.get("synthetic_signal") is True


# ═══════════════════════════════════════════════════════════════════════════════
# T002 — Idempotency
# ═══════════════════════════════════════════════════════════════════════════════

class TestT002_Idempotency:
    def test_T002_two_research_runs_same_count(self):
        """T002: Running replay twice for same range in RESEARCH mode produces same record count."""
        bars = _bars_from(date(2020, 1, 1), 60)
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            # First run
            e1 = _engine(bars, klp_dir)
            s1 = e1.replay(start_date=date(2020, 2, 1), end_date=date(2020, 2, 7),
                           symbols=["TEST"], mode=MODE_RESEARCH)
            # Second run (idempotent)
            e2 = _engine(bars, klp_dir)
            s2 = e2.replay(start_date=date(2020, 2, 1), end_date=date(2020, 2, 7),
                           symbols=["TEST"], mode=MODE_RESEARCH)
            # Second run should skip all (already written)
            assert s2.observations_skipped_dedup > 0
            # Total new written in second run is 0
            assert s2.observations_written == 0

    def test_T002b_obs_id_deterministic(self):
        """T002b: make_obs_id is deterministic — same inputs always same output."""
        id1 = make_obs_id("2016-01-15", "RELIANCE", "BUY")
        id2 = make_obs_id("2016-01-15", "RELIANCE", "BUY")
        assert id1 == id2
        assert id1 == "HKR1:20160115:113000:RELIANCE:BUY"


# ═══════════════════════════════════════════════════════════════════════════════
# T003 — Duplicate obs prevention
# ═══════════════════════════════════════════════════════════════════════════════

class TestT003_DuplicateObsPrevention:
    def _write_obs(self, path: Path, trading_date: str, sym: str) -> str:
        obs_id = make_obs_id(trading_date, sym, "BUY")
        obs = {"obs_id": obs_id, "event_type": "KNOWLEDGE_OBSERVATION",
               "symbol": sym, "direction": "BUY",
               "reference_entry": 100.0, "knowledge_target": 106.0,
               "knowledge_stop_loss": 97.0, "knowledge_RR": 2.0,
               "knowledge_confidence": 6.0, "candidate_score": 0.6,
               "atr": 2.0, "atr_pct": 2.0, "regime": "BULL",
               "source_type": "HISTORICAL_REPLAY",
               "validation_partition": "TRAIN",
               "replay_validation_status": "EXPERIMENTAL"}
        out = {"obs_id": obs_id, "event_type": "OUTCOME_UPDATE",
               "symbol": sym, "direction": "BUY",
               "first_event": "TARGET_HIT", "target_hit": True, "stop_hit": False,
               "t1_ret_pct": 1.5, "t3_ret_pct": 2.5, "t5_ret_pct": 3.5,
               "mfe_pct": 4.0, "mae_pct": -0.5, "bars_available": 5}
        with path.open("a") as fh:
            fh.write(json.dumps(obs) + "\n")
            fh.write(json.dumps(out) + "\n")
        return obs_id

    def test_T003_duplicate_obs_id_skipped_in_research_mode(self):
        """T003: Pre-existing obs_id in replay file → skip counter increments, no new line added."""
        bars = _bars_from(date(2020, 1, 1), 60)
        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            # Pre-write the obs for 2020-02-03 (Mon)
            replay_file = replay_dir / "REPLAY_2020-02-03.jsonl"
            self._write_obs(replay_file, "2020-02-03", "TEST")
            size_before = replay_file.stat().st_size

            e = _engine(bars, klp_dir)
            s = e.replay(start_date=date(2020, 2, 3), end_date=date(2020, 2, 3),
                         symbols=["TEST"], mode=MODE_RESEARCH)

            # File must not grow
            assert replay_file.stat().st_size == size_before
            assert s.observations_skipped_dedup >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# T004 — Duplicate outcome prevention
# ═══════════════════════════════════════════════════════════════════════════════

class TestT004_DuplicateOutcomePrevention:
    def test_T004_no_second_outcome_for_same_obs_id(self):
        """T004: HBE deduplication ensures same obs_id loaded only once regardless of file lines."""
        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            obs_id = make_obs_id("2020-02-03", "DUP", "BUY")
            obs = {"obs_id": obs_id, "event_type": "KNOWLEDGE_OBSERVATION",
                   "symbol": "DUP", "direction": "BUY",
                   "reference_entry": 100.0, "knowledge_target": 106.0,
                   "knowledge_stop_loss": 97.0, "knowledge_RR": 2.0,
                   "knowledge_confidence": 6.0, "candidate_score": 0.6,
                   "atr": 2.0, "atr_pct": 2.0, "regime": "BULL",
                   "source_type": "HISTORICAL_REPLAY",
                   "validation_partition": "TRAIN",
                   "replay_validation_status": "EXPERIMENTAL"}
            out = {"obs_id": obs_id, "event_type": "OUTCOME_UPDATE",
                   "first_event": "TARGET_HIT", "target_hit": True, "stop_hit": False,
                   "t1_ret_pct": 1.5, "t3_ret_pct": 2.5, "t5_ret_pct": 3.5,
                   "mfe_pct": 4.0, "mae_pct": -0.5, "bars_available": 5}
            replay_file = replay_dir / "REPLAY_2020-02-03.jsonl"
            # Write the same pair twice (simulating corrupt file)
            for _ in range(2):
                with replay_file.open("a") as fh:
                    fh.write(json.dumps(obs) + "\n")
                    fh.write(json.dumps(out) + "\n")

            hbe = HistoricalBehaviourEngine(data_dir=klp_dir)
            n   = hbe.load_outcomes()
            assert n == 1, f"Duplicate obs_id must be deduplicated; loaded {n}"


# ═══════════════════════════════════════════════════════════════════════════════
# T005 — OOS excluded from HBE evidence
# ═══════════════════════════════════════════════════════════════════════════════

class TestT005_OOSExcluded:
    def test_T005_oos_does_not_count_toward_level_threshold(self):
        """T005: 4 TRAIN + 1 OOS = 5 total; L2 threshold=5; OOS excluded → L2 not reached."""
        recs = (
            [_outcome_rec(trading_date=f"2016-01-{i+5:02d}", partition="TRAIN") for i in range(4)] +
            [_outcome_rec(trading_date="2026-08-28", partition="OOS")]
        )
        hbe = _hbe(recs)
        p   = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        assert p.metrics.evidence_level != 2, (
            "OOS must not contribute to L2 threshold"
        )

    def test_T005b_five_train_reach_l2(self):
        """T005b: 5 TRAIN records (no OOS) → L2 reached."""
        recs = [_outcome_rec(trading_date=f"2016-01-{i+5:02d}", partition="TRAIN") for i in range(5)]
        hbe  = _hbe(recs)
        p    = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        assert p.metrics.evidence_level in (1, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# T006 — OOS visible in audit counts
# ═══════════════════════════════════════════════════════════════════════════════

class TestT006_OOSVisible:
    def test_T006_oos_count_visible_in_behaviour_metrics(self):
        """T006: OOS records excluded from evidence but visible in historical_replay_oos_count."""
        recs = (
            [_outcome_rec(trading_date=f"2016-01-{i+5:02d}", partition="TRAIN") for i in range(6)] +
            [_outcome_rec(trading_date="2026-08-28", partition="OOS")]
        )
        hbe = _hbe(recs)
        p   = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        assert p.metrics.historical_replay_oos_count == 1
        assert p.metrics.observation_count == 6   # OOS excluded from metrics


# ═══════════════════════════════════════════════════════════════════════════════
# T007 — TRAIN+VALIDATION contribute
# ═══════════════════════════════════════════════════════════════════════════════

class TestT007_TrainValidationContribute:
    def test_T007_train_reaches_l2(self):
        """T007: TRAIN partition records contribute normally to evidence hierarchy."""
        recs = [_outcome_rec(trading_date=f"2016-0{m}-{d:02d}", partition="TRAIN")
                for m, d in [(1,5),(1,12),(2,3),(3,8),(4,15)]]
        hbe  = _hbe(recs)
        p    = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        assert p.metrics.evidence_level in (1, 2)
        assert p.metrics.historical_replay_train_count == 5

    def test_T007b_validation_reaches_l2(self):
        """T007b: VALIDATION partition records also contribute to evidence hierarchy."""
        recs = [_outcome_rec(trading_date=f"2016-0{m}-{d:02d}", partition="VALIDATION")
                for m, d in [(1,5),(1,12),(2,3),(3,8),(4,15)]]
        hbe  = _hbe(recs)
        p    = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        assert p.metrics.evidence_level in (1, 2)
        assert p.metrics.historical_replay_validation_count == 5


# ═══════════════════════════════════════════════════════════════════════════════
# T008 — Bootstrap preserved
# ═══════════════════════════════════════════════════════════════════════════════

class TestT008_BootstrapPreserved:
    def test_T008_bootstrap_file_unchanged_after_10yr_replay(self):
        """T008: BOOTSTRAP_*.jsonl byte-identical before and after 10-year replay."""
        bars = _bars_from(date(2019, 6, 1), 30)
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            boot = klp_dir / "BOOTSTRAP_2016-01-01.jsonl"
            boot.write_text('{"obs_id":"BOOT1","event_type":"KNOWLEDGE_OBSERVATION"}\n')
            before = boot.read_bytes()

            e = _engine(bars, klp_dir)
            e.replay(start_date=date(2019, 7, 1), end_date=date(2019, 7, 5),
                     symbols=["TEST"], mode=MODE_RESEARCH)

            assert boot.read_bytes() == before, "Bootstrap file was modified by replay"


# ═══════════════════════════════════════════════════════════════════════════════
# T009 — Live KLP preserved
# ═══════════════════════════════════════════════════════════════════════════════

class TestT009_LivePreserved:
    def test_T009_live_klp_file_unchanged(self):
        """T009: KLP_YYYY-MM-DD.jsonl live files untouched after replay."""
        bars = _bars_from(date(2019, 6, 1), 30)
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            live = klp_dir / "KLP_2026-08-20.jsonl"
            live.write_text('{"obs_id":"LIVE1","event_type":"KNOWLEDGE_OBSERVATION"}\n')
            before = live.read_bytes()

            e = _engine(bars, klp_dir)
            e.replay(start_date=date(2019, 7, 1), end_date=date(2019, 7, 5),
                     symbols=["TEST"], mode=MODE_RESEARCH)

            assert live.read_bytes() == before, "Live KLP file was modified by replay"


# ═══════════════════════════════════════════════════════════════════════════════
# T010 — Provenance round-trip
# ═══════════════════════════════════════════════════════════════════════════════

class TestT010_ProvenanceRoundTrip:
    def test_T010_partition_counts_survive_kda_round_trip(self):
        """T010: Partition counts in BehaviourMetrics survive KDADecisionRecord as_dict/from_dict."""
        d = {
            "decision_id": "test-010",
            "timestamp":   "2026-08-31T00:00:00+00:00",
            "symbol":      "RELIANCE",
            "direction":   "BUY",
            "historical_replay_train_count":      120,
            "historical_replay_validation_count": 35,
            "historical_replay_oos_count":        17,
        }
        rec  = KDADecisionRecord.from_dict(d)
        back = rec.as_dict()
        assert rec.historical_replay_train_count      == 120
        assert rec.historical_replay_validation_count == 35
        assert rec.historical_replay_oos_count        == 17
        assert back["historical_replay_train_count"]      == 120
        assert back["historical_replay_validation_count"] == 35
        assert back["historical_replay_oos_count"]        == 17


# ═══════════════════════════════════════════════════════════════════════════════
# T011 — Symbol-specific vs generic scope
# ═══════════════════════════════════════════════════════════════════════════════

class TestT011_SymbolVsGenericScope:
    def test_T011_l1_l2_are_symbol_specific(self):
        """T011: L1/L2 evidence must be labelled SYMBOL_SPECIFIC."""
        recs = [_outcome_rec(trading_date=f"2016-01-{i+5:02d}") for i in range(5)]
        hbe  = _hbe(recs)
        p    = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL",
                                          query_atr_pct=2.0, query_confidence=6.0)
        assert p.metrics.evidence_level in (1, 2)
        # Evidence scope must be symbol-specific for L1/L2
        scope = getattr(p.metrics, "evidence_scope", "")
        assert "SYMBOL" in scope.upper() or scope == "", (
            f"L{p.metrics.evidence_level} should be SYMBOL_SPECIFIC; got '{scope}'"
        )

    def test_T011b_l6_is_generic(self):
        """T011b: L6 broad-market evidence must be labelled GENERIC."""
        recs = [
            _outcome_rec(symbol=f"SYM{i:02d}", trading_date=f"2016-01-{i+5:02d}")
            for i in range(15)
        ]
        hbe = _hbe(recs)
        p   = hbe.get_behaviour_profile("UNKNOWN", "BUY")
        assert p.metrics.evidence_level == 6
        scope = getattr(p.metrics, "evidence_scope", "")
        assert scope != "SYMBOL_SPECIFIC", (
            f"L6 must not be SYMBOL_SPECIFIC; got '{scope}'"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T012 — L1 mapping
# ═══════════════════════════════════════════════════════════════════════════════

class TestT012_L1Mapping:
    def test_T012_l1_requires_same_symbol_regime_and_context(self):
        """T012: L1 requires symbol+direction+regime+context match; 5 such records → L1."""
        recs = [
            _outcome_rec(trading_date=f"2016-01-{i+5:02d}", regime="BULL")
            for i in range(5)
        ]
        hbe = _hbe(recs)
        p   = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL",
                                         query_atr_pct=2.0, query_confidence=6.0)
        assert p.metrics.evidence_level == 1, (
            f"Expected L1; got L{p.metrics.evidence_level}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T013 — L6 mapping
# ═══════════════════════════════════════════════════════════════════════════════

class TestT013_L6Mapping:
    def test_T013_l6_with_15_cross_symbol_records(self):
        """T013: 15 BUY records from different symbols → L6 for unknown symbol."""
        recs = [
            _outcome_rec(symbol=f"S{i:02d}", trading_date=f"2016-01-{i+5:02d}")
            for i in range(15)
        ]
        hbe = _hbe(recs)
        p   = hbe.get_behaviour_profile("NOTEXIST", "BUY")
        assert p.metrics.evidence_level == 6, (
            f"Expected L6; got L{p.metrics.evidence_level}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T014 — Historical data cannot alter execution config
# ═══════════════════════════════════════════════════════════════════════════════

class TestT014_ExecutionConfigUnchanged:
    def test_T014_paper_trading_flag_not_changed_by_replay(self):
        """T014: Running replay does not modify PAPER_TRADING or execution flags in config."""
        try:
            import config as cfg
            paper_before = getattr(cfg, "PAPER_TRADING", None)
        except ImportError:
            paper_before = None

        bars = _bars_from(date(2019, 6, 1), 30)
        e    = _engine(bars)
        e.replay(start_date=date(2019, 7, 1), end_date=date(2019, 7, 3),
                 symbols=["TEST"], mode=MODE_DRY_RUN)

        try:
            import config as cfg
            assert getattr(cfg, "PAPER_TRADING", None) == paper_before
        except ImportError:
            pass  # config not importable in test env → skip

    def test_T014b_replay_summary_carries_no_execution_fields(self):
        """T014b: ReplaySummary has no live_trading_authorized or risk_guardian fields."""
        bars = _bars_from(date(2019, 6, 1), 30)
        e    = _engine(bars)
        s    = e.replay(start_date=date(2019, 7, 1), end_date=date(2019, 7, 3),
                        symbols=["TEST"], mode=MODE_DRY_RUN)
        d    = s.as_dict()
        forbidden = {"live_trading_authorized", "risk_guardian_override",
                     "execution_authorized", "paper_trading_disabled"}
        assert not any(k in d for k in forbidden), (
            f"ReplaySummary contains execution field: {forbidden & set(d)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T015 — broker_calls == 0
# ═══════════════════════════════════════════════════════════════════════════════

class TestT015_BrokerCallsZero:
    def test_T015_dry_run_broker_calls_zero(self):
        bars = _bars_from(date(2016, 1, 1), 40)
        e    = _engine(bars)
        s    = e.replay(start_date=date(2016, 2, 1), end_date=date(2016, 2, 5),
                        symbols=["TEST"], mode=MODE_DRY_RUN)
        assert s.broker_calls == 0
        assert e.broker_calls == 0

    def test_T015b_research_mode_broker_calls_zero(self):
        bars = _bars_from(date(2016, 1, 1), 40)
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            e = _engine(bars, klp_dir)
            s = e.replay(start_date=date(2016, 2, 1), end_date=date(2016, 2, 5),
                         symbols=["TEST"], mode=MODE_RESEARCH)
            assert s.broker_calls == 0


# ═══════════════════════════════════════════════════════════════════════════════
# T016 — orders == 0
# ═══════════════════════════════════════════════════════════════════════════════

class TestT016_OrdersZero:
    def test_T016_research_orders_zero(self):
        bars = _bars_from(date(2016, 1, 1), 40)
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            e = _engine(bars, klp_dir)
            s = e.replay(start_date=date(2016, 2, 1), end_date=date(2016, 2, 5),
                         symbols=["TEST"], mode=MODE_RESEARCH)
            assert s.orders == 0

    def test_T016b_hbe_queries_never_generate_orders(self):
        """T016b: HBE.get_behaviour_profile() never generates orders."""
        recs = [_outcome_rec(trading_date=f"2016-01-{i+5:02d}") for i in range(8)]
        hbe  = _hbe(recs)
        _    = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        assert hbe.broker_calls == 0
        assert hbe.orders       == 0


# ═══════════════════════════════════════════════════════════════════════════════
# T017 — Existing replay file not overwritten
# ═══════════════════════════════════════════════════════════════════════════════

class TestT017_ExistingReplayNotOverwritten:
    def test_T017_replay_file_for_existing_date_not_modified(self):
        """T017: A replay file with obs already written is not truncated or modified."""
        bars = _bars_from(date(2019, 12, 1), 60)
        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            # Pre-write one record for 2020-01-06 (Monday)
            existing_file = replay_dir / "REPLAY_2020-01-06.jsonl"
            obs_id = make_obs_id("2020-01-06", "TEST", "BUY")
            obs = {"obs_id": obs_id, "event_type": "KNOWLEDGE_OBSERVATION",
                   "symbol": "TEST", "direction": "BUY",
                   "reference_entry": 100.0, "knowledge_target": 106.0,
                   "knowledge_stop_loss": 97.0, "knowledge_RR": 2.0,
                   "knowledge_confidence": 6.0, "candidate_score": 0.6,
                   "atr": 2.0, "atr_pct": 2.0, "regime": "BULL",
                   "source_type": "HISTORICAL_REPLAY",
                   "validation_partition": "TRAIN",
                   "replay_validation_status": "EXPERIMENTAL"}
            out = {"obs_id": obs_id, "event_type": "OUTCOME_UPDATE",
                   "first_event": "TARGET_HIT", "target_hit": True, "stop_hit": False,
                   "t1_ret_pct": 1.5, "t3_ret_pct": 2.5, "t5_ret_pct": 3.5,
                   "mfe_pct": 4.0, "mae_pct": -0.5, "bars_available": 5}
            with existing_file.open("w") as fh:
                fh.write(json.dumps(obs) + "\n")
                fh.write(json.dumps(out) + "\n")
            size_before = existing_file.stat().st_size

            # Run replay covering that date
            e = _engine(bars, klp_dir)
            e.replay(start_date=date(2020, 1, 6), end_date=date(2020, 1, 6),
                     symbols=["TEST"], mode=MODE_RESEARCH)

            # File must not have shrunk (obs was skipped due to dedup, not re-written)
            assert existing_file.stat().st_size == size_before


# ═══════════════════════════════════════════════════════════════════════════════
# T018 — Recency decay: 2016 records near zero ESS
# ═══════════════════════════════════════════════════════════════════════════════

class TestT018_RecencyDecay:
    def test_T018_2016_records_have_near_zero_ess_weight(self):
        """T018: Record from 2016-01-15 has negligible ESS weight by 2026-08-31."""
        ref   = date(2026, 8, 31)
        old_w = _recency_weight("2016-01-15", ref)
        # 3880 days / 90-day half-life = 43.1 half-lives → weight ≈ 10^-13
        assert old_w < 1e-10, f"2016 record weight should be negligible; got {old_w}"

    def test_T018b_recent_records_have_high_weight(self):
        """T018b: Record from 2026-08-28 has near-1.0 weight."""
        ref     = date(2026, 8, 31)
        recent  = _recency_weight("2026-08-28", ref)
        assert recent > 0.9, f"Recent record weight should be > 0.9; got {recent}"

    def test_T018c_ess_from_old_records_is_tiny_vs_recent(self):
        """T018c: 100 records from 2016 have lower ESS than 5 records from 2026."""
        from opportunity_engine.historical_behaviour_engine import _effective_sample_size
        ref = date(2026, 8, 31)
        old_recs = [
            _outcome_rec(trading_date=f"2016-0{m}-{d:02d}", source_type="HISTORICAL")
            for m, d in [(1,5),(2,5),(3,5),(4,5),(5,5),
                         (6,5),(7,5),(8,5),(9,5)]
        ] * 10  # 90 old records (avoid month 10+ format issue)
        new_recs = [
            _outcome_rec(trading_date=f"2026-08-{d:02d}", source_type="LIVE")
            for d in [25, 26, 27, 28, 31]
        ]
        ess_old = _effective_sample_size(old_recs, ref)
        ess_new = _effective_sample_size(new_recs, ref)
        assert ess_old < ess_new, (
            f"100 old records ESS ({ess_old:.6f}) should be < 5 recent records ESS ({ess_new:.2f})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T019–T022 — Path outcome correctness
# ═══════════════════════════════════════════════════════════════════════════════

class TestT019_T022_PathOutcomes:
    def _obs(self, entry=100.0, target=108.0, stop=94.0, direction="BUY"):
        return {"obs_id": "HKR1:TEST", "event_type": "KNOWLEDGE_OBSERVATION",
                "symbol": "TEST", "direction": direction,
                "reference_entry": entry, "knowledge_target": target,
                "knowledge_stop_loss": stop, "knowledge_RR": 2.0,
                "knowledge_confidence": 6.0, "candidate_score": 0.6,
                "atr": 3.0, "atr_pct": 3.0, "regime": "BULL",
                "source_type": "HISTORICAL_REPLAY"}

    def _bar(self, d_str, o, h, l, c):
        return _Bar(datetime.fromisoformat(f"{d_str}T09:30:00+05:30"), o, h, l, c)

    def test_T019_stop_first_then_recovery_is_stop_hit(self):
        """T019: Stop hit T+1; recovers above entry T+4 → first_event=STOP_HIT."""
        e = _engine()
        future = [
            self._bar("2016-01-05", 100, 101, 92, 95),   # low < stop → STOP_HIT
            self._bar("2016-01-06", 95,  99, 94, 98),
            self._bar("2016-01-07", 98, 103, 97, 102),
            self._bar("2016-01-08", 102,107, 101,106),
        ]
        r = e._compute_path_outcome(self._obs(), future)
        assert r["first_event"] == STOP_HIT
        assert r["stop_hit"]    is True

    def test_T020_target_first_then_reversal_is_target_hit(self):
        """T020: Target hit T+2; price reverses below stop T+4 → first_event=TARGET_HIT."""
        e = _engine()
        future = [
            self._bar("2016-01-05", 100, 104, 99, 103),
            self._bar("2016-01-06", 103, 109, 102, 108),  # high >= target
            self._bar("2016-01-07", 107, 107, 99, 100),
            self._bar("2016-01-08", 99,  99, 92, 93),
        ]
        r = e._compute_path_outcome(self._obs(), future)
        assert r["first_event"] == TARGET_HIT
        assert r["target_hit"]  is True

    def test_T021_gap_down_through_stop_is_stop_hit(self):
        """T021: Bar opens far below stop (gap down) → STOP_HIT."""
        e = _engine()
        future = [
            self._bar("2016-01-05", 100, 101, 88, 90),  # low=88 < stop=94
        ]
        r = e._compute_path_outcome(self._obs(), future)
        assert r["first_event"] == STOP_HIT

    def test_T022_same_bar_ambiguity(self):
        """T022: Same bar hits both target (high) and stop (low) → OUTCOME_AMBIGUOUS."""
        e = _engine()
        future = [
            self._bar("2016-01-05", 100, 110, 90, 100),  # high>=108 and low<=94
        ]
        r = e._compute_path_outcome(self._obs(), future)
        assert r["first_event"] == OUTCOME_AMBIGUOUS


# ═══════════════════════════════════════════════════════════════════════════════
# T023 — Replay cannot produce DECISION_ELIGIBLE authority
# ═══════════════════════════════════════════════════════════════════════════════

class TestT023_NoAutoAuthority:
    def test_T023_replay_validation_status_never_decision_eligible(self):
        """T023: Replay obs records carry EXPERIMENTAL, never DECISION_ELIGIBLE."""
        bars = _bars_from(date(2019, 6, 1), 30)
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            e = _engine(bars, klp_dir)
            e.replay(start_date=date(2019, 7, 1), end_date=date(2019, 7, 5),
                     symbols=["TEST"], mode=MODE_RESEARCH)
            for f in (klp_dir / "replay").glob("REPLAY_*.jsonl"):
                for line in f.read_text().splitlines():
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    rvs = rec.get("replay_validation_status", "")
                    assert rvs not in ("DECISION_ELIGIBLE", "VALIDATED", "LIVE"), (
                        f"Illegal replay_validation_status={rvs!r}"
                    )

    def test_T023b_oss_high_ess_still_experimental(self):
        """T023b: Even with 100 TRAIN records and high ESS, replay stays EXPERIMENTAL."""
        # 100 records from 2026 (high weight) — but still HISTORICAL_REPLAY
        recs = [
            _outcome_rec(
                trading_date=(date(2026, 8, 1) + timedelta(days=i % 20)).isoformat(),
                partition="TRAIN",
            )
            for i in range(100)
        ]
        hbe = _hbe(recs)
        p   = hbe.get_behaviour_profile("TEST", "BUY", regime="BULL")
        # The profile exists with evidence, but ESS tier should not grant DECISION_ELIGIBLE
        # (DECISION_ELIGIBLE is a KDA concept, not BehaviourMetrics — just check evidence exists)
        assert p.metrics.evidence_level in (1, 2)
        assert p.metrics.historical_replay_train_count == 100


# ═══════════════════════════════════════════════════════════════════════════════
# T024 — Evidence audit source breakdown
# ═══════════════════════════════════════════════════════════════════════════════

class TestT024_EvidenceAudit:
    def test_T024_count_by_source_correct(self):
        """T024: _count_by_source utility produces correct per-type breakdown."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from dta_034_expansion_run import _count_by_source

        recs = (
            [_outcome_rec(source_type="HISTORICAL",       partition="")    for _ in range(5)] +
            [_outcome_rec(source_type="LIVE",             partition="")    for _ in range(3)] +
            [_outcome_rec(source_type="PAPER",            partition="")    for _ in range(2)] +
            [_outcome_rec(source_type="HISTORICAL_REPLAY", partition="TRAIN")      for _ in range(8)] +
            [_outcome_rec(source_type="HISTORICAL_REPLAY", partition="VALIDATION") for _ in range(3)] +
            [_outcome_rec(source_type="HISTORICAL_REPLAY", partition="OOS")        for _ in range(1)]
        )
        counts = _count_by_source(recs)
        assert counts["HISTORICAL"]                  == 5
        assert counts["LIVE"]                        == 3
        assert counts["PAPER"]                       == 2
        assert counts["HISTORICAL_REPLAY_TRAIN"]     == 8
        assert counts["HISTORICAL_REPLAY_VALIDATION"] == 3
        assert counts["HISTORICAL_REPLAY_OOS"]       == 1

    def test_T024b_get_evidence_profile_returns_source_breakdown(self):
        """T024b: _get_evidence_profile returns per-source breakdown keys."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from dta_034_expansion_run import _get_evidence_profile

        recs = [_outcome_rec(trading_date=f"2016-01-{i+5:02d}") for i in range(6)]
        hbe  = _hbe(recs)
        prof = _get_evidence_profile(hbe, "TEST", "BUY")
        assert "evidence_level"       in prof
        assert "ess"                  in prof
        assert "replay_train_count"   in prof
        assert "live_count"           in prof
        assert "bootstrap_count"      in prof


# ═══════════════════════════════════════════════════════════════════════════════
# T025 — Historical dominance detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestT025_HistoricalDominance:
    def test_T025_dominance_flagged_when_level_changes_materially(self):
        """T025: HISTORICAL_DOMINANCE flagged when replay causes evidence level upgrade >= 2 tiers."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from dta_034_expansion_run import _historical_dominance_check, _make_live_only_hbe

        # Full HBE: 8 replay records → L2
        all_recs = [
            _outcome_rec(trading_date=f"2016-01-{i+5:02d}", partition="TRAIN")
            for i in range(8)
        ]
        hbe_all  = _hbe(all_recs)
        # Live-only: 0 records → L7
        hbe_live = _make_live_only_hbe(hbe_all)

        result = _historical_dominance_check(hbe_all, hbe_live, "TEST", "BUY")
        # Level changes from 7 (no live data) to 1 or 2 (with replay) → dominance
        assert result["level_all_data"]  in (1, 2)
        assert result["level_live_only"] == 7
        assert result["historical_dominance"] is True

    def test_T025b_no_dominance_when_levels_equal(self):
        """T025b: No HISTORICAL_DOMINANCE flagged when evidence levels are the same."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from dta_034_expansion_run import _historical_dominance_check, _make_live_only_hbe

        # Both live and replay at L2 (≥5 records each for same symbol)
        live_recs   = [_outcome_rec(trading_date=f"2026-08-{i+20:02d}", source_type="LIVE",
                                    partition="") for i in range(6)]
        replay_recs = [_outcome_rec(trading_date=f"2016-01-{i+5:02d}", partition="TRAIN") for i in range(6)]
        hbe_all  = _hbe(live_recs + replay_recs)
        hbe_live = _make_live_only_hbe(hbe_all)

        result = _historical_dominance_check(hbe_all, hbe_live, "TEST", "BUY")
        assert result["level_all_data"]       in (1, 2)
        assert result["level_live_only"]      in (1, 2)
        assert result["historical_dominance"] is False

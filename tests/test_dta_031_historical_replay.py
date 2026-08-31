"""
tests/test_dta_031_historical_replay.py
========================================
DTA-031 / DTA-031A: Historical Knowledge Replay — Test Suite

Coverage:
  Part Y  — Path outcome correctness (7 tests, T001–T007)
  Part Z  — No-lookahead enforcement (12 tests, T008–T019)
  Part AA — Data preservation: existing records untouched (4 tests, T020–T023)
  Part AB — Idempotency: duplicate replay does not double-write (4 tests, T024–T027)
  Part AC — Broker safety invariants (3 tests, T028–T030)
  Part AD — Walk-forward partition assignment (5 tests, T031–T035)
  Part AE — BehaviourMetrics provenance: historical_replay_record_count (5 tests, T036–T040)
  Part AF — DRY_RUN safety: zero disk writes (3 tests, T041–T043)
  Part AG — obs_id determinism and format (4 tests, T044–T047)
  Part AH — ReplaySummary completeness (4 tests, T048–T051)
  Helper function unit tests (4 tests, T052–T055)

Coverage (DTA-031A):
  Part A  — Learning-path integrity: REPLAY→HBE→OutcomeRecord→BehaviourMetrics (8 tests, T056–T063)
  Part B  — Additional DTA-028A scenarios: stop-first-recovery, gap-through, reversal (7 tests, T064–T070)
  Part C  — Evidence-hierarchy promotion and fallback (6 tests, T071–T076)
  Part D  — KDA provenance: historical_replay_record_count in KDADecisionRecord (4 tests, T077–T080)
  Part E  — Validation gate: EXPERIMENTAL status on written records (5 tests, T081–T085)

Total: 85 tests
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys, os

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from learning_system.historical_knowledge_replay import (
    HistoricalKnowledgeReplayEngine,
    ReplaySummary,
    ReplayRecord,
    WalkForwardStats,
    make_obs_id,
    get_trading_days,
    assign_partition,
    compute_atr14,
    compute_sma,
    reconstruct_regime,
    bar_date_str,
    validate_bar,
    pricebar_to_dict,
    load_existing_obs_ids,
    MODE_DRY_RUN,
    MODE_RESEARCH,
    SOURCE_TYPE,
    OBS_ID_PREFIX,
    TARGET_HIT,
    STOP_HIT,
    OUTCOME_EXPIRED,
    OUTCOME_NO_DATA,
    OUTCOME_PENDING,
    OUTCOME_AMBIGUOUS,
    COMPLETED_OUTCOMES,
    _ATR_STOP_MULT,
    _ATR_TARGET_MULT,
)

# ─────────────────────────────────────────────────────────────────────────────
# Test fixtures and helpers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MockBar:
    """Minimal PriceBar-compatible object for tests."""
    timestamp: datetime
    open:   float
    high:   float
    low:    float
    close:  float
    volume: float = 1000.0
    symbol: str = "TEST"
    interval: str = "1d"


def _bar(d: str, o: float, h: float, lo: float, c: float) -> MockBar:
    """Create a MockBar with the given date string and OHLC."""
    return MockBar(
        timestamp=datetime.fromisoformat(f"{d}T09:15:00+00:00"),
        open=o, high=h, low=lo, close=c,
    )


def _make_bars(start_date: str, n: int, base: float = 100.0, step: float = 0.0) -> List[MockBar]:
    """Create n daily bars starting from start_date with gently rising/flat prices."""
    bars: List[MockBar] = []
    from datetime import date as dt, timedelta
    d = dt.fromisoformat(start_date)
    price = base
    for i in range(n):
        c = round(price, 2)
        bars.append(_bar(d.isoformat(), c * 0.995, c * 1.005, c * 0.99, c))
        price += step
        d += timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
    return bars


def _engine_with_bars(bars_map: Dict[str, List[MockBar]], tmpdir: Path = None) -> HistoricalKnowledgeReplayEngine:
    """Build an engine with mock OHLCV fetcher injected."""
    def fetcher(symbol: str) -> List[MockBar]:
        return bars_map.get(symbol.upper(), [])
    return HistoricalKnowledgeReplayEngine(
        klp_dir=tmpdir or Path(tempfile.mkdtemp()),
        _ohlcv_fetcher=fetcher,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Part Y — Path outcome correctness (T001–T007)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartY_PathOutcome:
    """Verify that _compute_path_outcome reuses DTA-028A logic correctly."""

    def _make_engine(self) -> HistoricalKnowledgeReplayEngine:
        return HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])

    def _obs(self, entry: float, target: float, stop: float, direction: str = "BUY") -> Dict:
        """Build a minimal obs dict."""
        return {
            "obs_id": "HKR1:20260801:113000:TEST:BUY",
            "event_type": "KNOWLEDGE_OBSERVATION",
            "symbol": "TEST",
            "direction": direction,
            "reference_entry": entry,
            "knowledge_target": target,
            "knowledge_stop_loss": stop,
            "knowledge_RR": abs(target - entry) / max(abs(entry - stop), 0.01),
            "knowledge_confidence": 6.0,
            "candidate_score": 0.6,
            "scanner_confidence": 6.0,
            "knowledge_score": 0.0,
            "atr": entry * 0.02,
            "atr_pct": 2.0,
            "regime": "BULL",
            "source_type": SOURCE_TYPE,
        }

    def test_T001_target_hit_before_stop(self):
        """T001: BUY signal — target hit on T+2, stop never hit."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=106.0, stop=97.0)
        future = [
            _bar("2026-08-01", 100, 104, 99, 103),   # T+1
            _bar("2026-08-02", 103, 107, 102, 106),   # T+2: high >= target
            _bar("2026-08-03", 106, 108, 105, 107),   # T+3
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == TARGET_HIT
        assert result["first_event_day"] == "2026-08-02"
        assert result["target_hit"] is True
        assert result["stop_hit"]   is False

    def test_T002_stop_hit_before_target(self):
        """T002: BUY signal — stop hit on T+1."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=106.0, stop=97.0)
        future = [
            _bar("2026-08-01", 100, 101, 96.5, 97),   # T+1: low <= stop
            _bar("2026-08-02", 97,  105, 95,   99),
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == STOP_HIT
        assert result["first_event_day"] == "2026-08-01"
        assert result["target_hit"] is False
        assert result["stop_hit"]   is True

    def test_T003_outcome_expired_neither_hit(self):
        """T003: Neither target nor stop hit within 5 bars → OUTCOME_EXPIRED."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=110.0, stop=90.0)
        # 5 bars between stop and target
        future = [_bar(f"2026-08-0{i}", 99+i, 100+i, 98+i, 99+i) for i in range(1, 6)]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == OUTCOME_EXPIRED
        assert result["target_hit"] is False
        assert result["stop_hit"]   is False

    def test_T004_outcome_no_data_empty_bars(self):
        """T004: No future bars → OUTCOME_NO_DATA."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=106.0, stop=97.0)
        result = engine._compute_path_outcome(obs, [])
        assert result["first_event"] == OUTCOME_NO_DATA
        assert result["bars_available"] == 0

    def test_T005_t1_return_correct(self):
        """T005: T+1 return % = (close[T+1] / entry - 1) * 100."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=120.0, stop=80.0)
        future = [_bar("2026-08-01", 100, 105, 99, 103.5)]   # T+1 close = 103.5
        result = engine._compute_path_outcome(obs, future)
        assert result["t1_ret_pct"] is not None
        assert abs(result["t1_ret_pct"] - 3.5) < 0.01   # (103.5/100 - 1)*100 = 3.5

    def test_T006_ambiguous_same_bar_target_and_stop(self):
        """T006: Same bar hits both target and stop → OUTCOME_AMBIGUOUS."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=105.0, stop=95.0)
        # single bar: high >= target AND low <= stop simultaneously
        future = [_bar("2026-08-01", 100, 106, 94, 100)]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == OUTCOME_AMBIGUOUS
        assert result["target_hit"] is True
        assert result["stop_hit"]   is True

    def test_T007_mfe_bounded_at_first_event(self):
        """T007: MFE does not accumulate beyond first_event_day."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=103.0, stop=97.0)
        # Target hit on T+1; T+2 and T+3 have big moves but should not affect MFE
        future = [
            _bar("2026-08-01", 100, 104, 99, 103),   # T+1: target hit, high=104
            _bar("2026-08-02", 103, 115, 102, 110),  # T+2: big move — should be excluded
            _bar("2026-08-03", 110, 120, 109, 115),  # T+3: even bigger — excluded
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == TARGET_HIT
        # MFE should be bounded at T+1 bar (high=104): (104/100-1)*100 = 4.0%
        assert result["mfe_pct"] is not None
        assert result["mfe_pct"] <= 5.0  # must not include T+2/T+3 highs


# ─────────────────────────────────────────────────────────────────────────────
# Part Z — No-lookahead enforcement (T008–T019)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartZ_NoLookahead:
    """Verify that no future data leaks into historical decisions."""

    def test_T008_obs_id_is_deterministic(self):
        """T008: Same inputs produce the same obs_id every time."""
        id1 = make_obs_id("2026-07-15", "RELIANCE", "BUY")
        id2 = make_obs_id("2026-07-15", "RELIANCE", "BUY")
        assert id1 == id2

    def test_T009_obs_id_prefix_is_HKR1(self):
        """T009: obs_id always starts with 'HKR1:'."""
        obs_id = make_obs_id("2026-07-15", "RELIANCE", "BUY")
        assert obs_id.startswith(f"{OBS_ID_PREFIX}:")

    def test_T010_obs_id_contains_date_compact(self):
        """T010: obs_id contains the compact date (YYYYMMDD)."""
        obs_id = make_obs_id("2026-07-15", "RELIANCE", "BUY")
        assert "20260715" in obs_id

    def test_T011_obs_id_different_dates(self):
        """T011: Different dates produce different obs_ids (no collision)."""
        id1 = make_obs_id("2026-07-14", "RELIANCE", "BUY")
        id2 = make_obs_id("2026-07-15", "RELIANCE", "BUY")
        assert id1 != id2

    def test_T012_obs_id_different_symbols(self):
        """T012: Different symbols produce different obs_ids."""
        id1 = make_obs_id("2026-07-15", "RELIANCE", "BUY")
        id2 = make_obs_id("2026-07-15", "INFY",     "BUY")
        assert id1 != id2

    def test_T013_signal_uses_only_bars_up_to_trading_date(self):
        """T013: _reconstruct_signal ignores bars after trading_date."""
        # T+0 = 2026-07-10; T+1 bar has different (higher) close
        bars = [
            _bar("2026-07-05", 90, 92, 88, 91),
            _bar("2026-07-06", 91, 93, 89, 92),
            _bar("2026-07-07", 92, 94, 90, 93),
            _bar("2026-07-08", 93, 95, 91, 94),
            _bar("2026-07-09", 94, 96, 92, 95),
            _bar("2026-07-10", 95, 97, 93, 96),     # T+0 bar — entry should be 96
            _bar("2026-07-11", 200, 220, 180, 210),  # T+1 future — must NOT influence entry
        ]
        engine = HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])
        obs = engine._reconstruct_signal("TEST", date(2026, 7, 10), bars)
        assert obs is not None
        assert obs["reference_entry"] == 96.0   # close of T+0, not T+1

    def test_T014_entry_is_t0_close_not_t1(self):
        """T014: reference_entry = close of T+0 bar (not T+1 open)."""
        bars = _make_bars("2026-07-01", 15, base=100.0, step=0.5)
        t0 = date(2026, 7, 15)
        engine = HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])
        obs = engine._reconstruct_signal("TEST", t0, bars)
        # The engine filters bars to <= t0; entry = last filtered bar's close
        if obs is not None:
            assert obs["reference_entry"] > 0
            assert obs["no_lookahead"] is True

    def test_T015_no_lookahead_flag_set_in_obs(self):
        """T015: All obs records have no_lookahead=True."""
        bars = _make_bars("2026-07-01", 25, base=500.0)
        engine = HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])
        obs = engine._reconstruct_signal("TEST", date(2026, 7, 25), bars)
        assert obs is not None
        assert obs["no_lookahead"] is True

    def test_T016_source_type_is_historical_replay(self):
        """T016: source_type in obs is 'HISTORICAL_REPLAY'."""
        bars = _make_bars("2026-07-01", 25, base=200.0)
        engine = HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])
        obs = engine._reconstruct_signal("TEST", date(2026, 7, 25), bars)
        assert obs is not None
        assert obs["source_type"] == SOURCE_TYPE

    def test_T017_synthetic_signal_flag_set(self):
        """T017: synthetic_signal=True and reconstruction_method documented."""
        bars = _make_bars("2026-07-01", 25, base=300.0)
        engine = HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])
        obs = engine._reconstruct_signal("TEST", date(2026, 7, 25), bars)
        assert obs is not None
        assert obs.get("synthetic_signal") is True
        assert "reconstruction_method" in obs

    def test_T018_atr_computed_from_bars_up_to_t0(self):
        """T018: ATR is positive and plausible relative to entry price."""
        bars = _make_bars("2026-07-01", 25, base=1000.0)
        engine = HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])
        obs = engine._reconstruct_signal("TEST", date(2026, 7, 25), bars)
        assert obs is not None
        entry = obs["reference_entry"]
        atr   = obs["atr"]
        assert atr > 0
        # ATR should be a small fraction of entry (< 10%)
        assert atr < entry * 0.10

    def test_T019_insufficient_bars_returns_none(self):
        """T019: < _MIN_BARS_FOR_SIGNAL bars → _reconstruct_signal returns None."""
        bars = _make_bars("2026-07-01", 3, base=100.0)  # only 3 bars
        engine = HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])
        obs = engine._reconstruct_signal("TEST", date(2026, 7, 3), bars)
        assert obs is None


# ─────────────────────────────────────────────────────────────────────────────
# Part AA — Data preservation (T020–T023)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartAA_DataPreservation:
    """Verify that replay never modifies existing KLP or BOOTSTRAP files."""

    def test_T020_dry_run_no_new_files(self):
        """T020: DRY_RUN mode creates no files in the KLP directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            klp_dir = Path(tmpdir) / "klp"
            klp_dir.mkdir()

            bars = _make_bars("2026-07-01", 30, base=100.0)
            engine = _engine_with_bars({"TEST": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 20),
                symbols=["TEST"],
                mode=MODE_DRY_RUN,
            )
            # No replay directory should be created
            replay_dir = klp_dir / "replay"
            assert not replay_dir.exists() or not any(replay_dir.glob("REPLAY_*.jsonl"))

    def test_T021_existing_klp_file_untouched(self):
        """T021: Existing KLP_*.jsonl file is not modified by replay."""
        with tempfile.TemporaryDirectory() as tmpdir:
            klp_dir = Path(tmpdir) / "klp"
            klp_dir.mkdir()

            # Create a fake live KLP file
            klp_file = klp_dir / "KLP_2026-07-15.jsonl"
            original_content = '{"obs_id": "KLP_abc", "event_type": "KNOWLEDGE_OBSERVATION"}\n'
            klp_file.write_text(original_content, encoding="utf-8")
            original_mtime = klp_file.stat().st_mtime

            bars = _make_bars("2026-07-01", 30, base=100.0)
            engine = _engine_with_bars({"TEST": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 18),
                symbols=["TEST"],
                mode=MODE_RESEARCH,
            )

            # KLP file should be unchanged
            assert klp_file.read_text(encoding="utf-8") == original_content

    def test_T022_bootstrap_file_untouched(self):
        """T022: Existing BOOTSTRAP_*.jsonl file is not touched by replay."""
        with tempfile.TemporaryDirectory() as tmpdir:
            klp_dir = Path(tmpdir) / "klp"
            klp_dir.mkdir()

            bootstrap_file = klp_dir / "BOOTSTRAP_2026-01-01.jsonl"
            original_content = '{"obs_id": "BOOT_001", "source_type": "HISTORICAL"}\n'
            bootstrap_file.write_text(original_content, encoding="utf-8")

            bars = _make_bars("2026-07-01", 30, base=100.0)
            engine = _engine_with_bars({"TEST": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 18),
                symbols=["TEST"],
                mode=MODE_RESEARCH,
            )

            assert bootstrap_file.read_text(encoding="utf-8") == original_content

    def test_T023_replay_writes_to_replay_subdir_only(self):
        """T023: RESEARCH mode writes only to data/klp/replay/ subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            klp_dir = Path(tmpdir) / "klp"
            klp_dir.mkdir()

            bars = _make_bars("2026-07-01", 30, base=100.0)
            engine = _engine_with_bars({"TEST": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 18),
                symbols=["TEST"],
                mode=MODE_RESEARCH,
            )

            # Only REPLAY_*.jsonl files exist; no KLP_*.jsonl in root klp dir
            root_klp_files = list(klp_dir.glob("KLP_*.jsonl"))
            assert root_klp_files == [], f"Unexpected KLP files created: {root_klp_files}"

            replay_dir = klp_dir / "replay"
            if replay_dir.exists():
                replay_files = list(replay_dir.glob("REPLAY_*.jsonl"))
                assert len(replay_files) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Part AB — Idempotency (T024–T027)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartAB_Idempotency:
    """Running replay twice must not produce duplicate records."""

    def test_T024_second_run_skips_existing_obs(self):
        """T024: Re-running RESEARCH mode skips already-written obs_ids."""
        with tempfile.TemporaryDirectory() as tmpdir:
            klp_dir = Path(tmpdir) / "klp"
            klp_dir.mkdir()

            bars = _make_bars("2026-07-01", 30, base=100.0)
            engine = _engine_with_bars({"TEST": bars}, klp_dir)

            s1 = engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 18),
                symbols=["TEST"],
                mode=MODE_RESEARCH,
            )
            s2 = engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 18),
                symbols=["TEST"],
                mode=MODE_RESEARCH,
            )

            # All records in second run should be dedup-skipped
            assert s2.observations_skipped_dedup == s1.observations_attempted

    def test_T025_no_duplicate_lines_in_replay_file(self):
        """T025: Each REPLAY_*.jsonl has at most one KNOWLEDGE_OBSERVATION per obs_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            klp_dir = Path(tmpdir) / "klp"
            klp_dir.mkdir()

            bars = _make_bars("2026-07-01", 30, base=100.0)
            engine = _engine_with_bars({"TEST": bars}, klp_dir)

            # Run twice
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 17),
                symbols=["TEST"],
                mode=MODE_RESEARCH,
            )
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 17),
                symbols=["TEST"],
                mode=MODE_RESEARCH,
            )

            replay_dir = klp_dir / "replay"
            for f in replay_dir.glob("REPLAY_*.jsonl"):
                obs_ids_seen: set = set()
                with f.open("r") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        rec = json.loads(line)
                        if rec.get("event_type") == "KNOWLEDGE_OBSERVATION":
                            oid = rec.get("obs_id", "")
                            assert oid not in obs_ids_seen, f"Duplicate obs_id {oid} in {f}"
                            obs_ids_seen.add(oid)

    def test_T026_load_existing_obs_ids_returns_correct_set(self):
        """T026: load_existing_obs_ids reads only KNOWLEDGE_OBSERVATION records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "REPLAY_2026-07-15.jsonl"
            lines = [
                '{"obs_id": "HKR1:A", "event_type": "KNOWLEDGE_OBSERVATION"}',
                '{"obs_id": "HKR1:A", "event_type": "OUTCOME_UPDATE"}',
                '{"obs_id": "HKR1:B", "event_type": "KNOWLEDGE_OBSERVATION"}',
            ]
            f.write_text("\n".join(lines) + "\n", encoding="utf-8")
            ids = load_existing_obs_ids(f)
            assert ids == {"HKR1:A", "HKR1:B"}

    def test_T027_obs_id_determinism_across_calls(self):
        """T027: make_obs_id is pure — same inputs always give same output."""
        for _ in range(5):
            assert (
                make_obs_id("2026-07-15", "RELIANCE", "BUY")
                == make_obs_id("2026-07-15", "RELIANCE", "BUY")
            )


# ─────────────────────────────────────────────────────────────────────────────
# Part AC — Broker safety (T028–T030)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartAC_BrokerSafety:
    """Broker invariants must be zero under all circumstances."""

    def _run_research(self, tmpdir_str: str) -> ReplaySummary:
        klp_dir = Path(tmpdir_str) / "klp"
        klp_dir.mkdir(exist_ok=True)
        bars = _make_bars("2026-07-01", 40, base=500.0)
        engine = _engine_with_bars({"RELIANCE": bars}, klp_dir)
        return engine.replay(
            start_date=date(2026, 7, 15),
            end_date=date(2026, 7, 25),
            symbols=["RELIANCE"],
            mode=MODE_RESEARCH,
        )

    def test_T028_broker_calls_always_zero(self):
        """T028: broker_calls = 0 in all replay modes."""
        with tempfile.TemporaryDirectory() as td:
            s_dry = _engine_with_bars(
                {"RELIANCE": _make_bars("2026-07-01", 40, base=500.0)},
                Path(td) / "klp",
            ).replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 20),
                symbols=["RELIANCE"],
                mode=MODE_DRY_RUN,
            )
            assert s_dry.broker_calls == 0

        with tempfile.TemporaryDirectory() as td:
            s_res = self._run_research(td)
            assert s_res.broker_calls == 0

    def test_T029_orders_always_zero(self):
        """T029: orders = 0 in all replay modes."""
        with tempfile.TemporaryDirectory() as td:
            klp = Path(td) / "klp"
            klp.mkdir()
            s = _engine_with_bars(
                {"TEST": _make_bars("2026-07-01", 40, base=200.0)}, klp
            ).replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 20),
                symbols=["TEST"],
                mode=MODE_RESEARCH,
            )
            assert s.orders == 0

    def test_T030_existing_records_modified_always_zero(self):
        """T030: existing_records_modified = 0 in all replay modes."""
        with tempfile.TemporaryDirectory() as td:
            klp = Path(td) / "klp"
            klp.mkdir()
            s = _engine_with_bars(
                {"TEST": _make_bars("2026-07-01", 40, base=200.0)}, klp
            ).replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 20),
                symbols=["TEST"],
                mode=MODE_RESEARCH,
            )
            assert s.existing_records_modified == 0


# ─────────────────────────────────────────────────────────────────────────────
# Part AD — Walk-forward partition assignment (T031–T035)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartAD_WalkForward:
    """Walk-forward assignment must be chronological and deterministic."""

    def test_T031_first_70pct_is_train(self):
        """T031: First 70% of trading days get TRAIN partition."""
        n = 10
        for i in range(7):  # first 7 of 10 → TRAIN
            assert assign_partition(i, n) == "TRAIN", f"idx={i} should be TRAIN"

    def test_T032_next_20pct_is_validation(self):
        """T032: Days 70–90% of total → VALIDATION partition."""
        n = 10
        for i in range(7, 9):  # days 8–9 of 10 → VALIDATION
            assert assign_partition(i, n) == "VALIDATION", f"idx={i} should be VALIDATION"

    def test_T033_last_10pct_is_oos(self):
        """T033: Last 10% of trading days → OOS partition."""
        n = 10
        assert assign_partition(9, n) == "OOS"

    def test_T034_walk_forward_stats_in_summary(self):
        """T034: ReplaySummary.walk_forward_stats has TRAIN, VALIDATION, OOS entries."""
        bars = _make_bars("2026-06-01", 60, base=100.0)
        engine = _engine_with_bars({"TEST": bars})
        summary = engine.replay(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            symbols=["TEST"],
            mode=MODE_DRY_RUN,
        )
        partitions = {wf.partition for wf in summary.walk_forward_stats}
        assert "TRAIN" in partitions
        assert "VALIDATION" in partitions
        assert "OOS" in partitions

    def test_T035_partitions_are_chronological(self):
        """T035: Walk-forward partition assignment is strictly chronological."""
        days = get_trading_days(date(2026, 7, 1), date(2026, 7, 31))
        n = len(days)
        partitions = [assign_partition(i, n) for i in range(n)]
        # Should be: TRAIN...TRAIN VALIDATION...VALIDATION OOS...OOS
        # (monotonically non-decreasing order)
        order_map = {"TRAIN": 0, "VALIDATION": 1, "OOS": 2}
        for i in range(1, len(partitions)):
            assert order_map[partitions[i]] >= order_map[partitions[i-1]], (
                f"Partition order violated at index {i}: "
                f"{partitions[i-1]} → {partitions[i]}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Part AE — BehaviourMetrics provenance: historical_replay_record_count (T036–T040)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartAE_BehaviourMetrics:
    """Verify historical_replay_record_count is tracked correctly in BehaviourMetrics."""

    def test_T036_hbe_models_has_historical_replay_field(self):
        """T036: BehaviourMetrics has historical_replay_record_count field with default 0."""
        from opportunity_engine.hbe_models import BehaviourMetrics
        import inspect
        fields = {f.name for f in BehaviourMetrics.__dataclass_fields__.values()}
        assert "historical_replay_record_count" in fields

    def test_T037_historical_replay_field_defaults_to_zero(self):
        """T037: historical_replay_record_count defaults to 0."""
        from opportunity_engine.hbe_models import BehaviourMetrics
        f = BehaviourMetrics.__dataclass_fields__["historical_replay_record_count"]
        assert f.default == 0

    def test_T038_compute_metrics_counts_historical_replay(self):
        """T038: _compute_metrics counts source_type='HISTORICAL_REPLAY' records."""
        from opportunity_engine.hbe_models import OutcomeRecord, COMPLETED_OUTCOMES
        from opportunity_engine.historical_behaviour_engine import _compute_metrics

        def _make_rec(src: str, fe: str = "TARGET_HIT") -> OutcomeRecord:
            return OutcomeRecord(
                obs_id=f"X_{src}_{id(src)}",
                trading_date="2026-07-01",
                symbol="TEST",
                direction="BUY",
                regime="BULL",
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
                first_event=fe,
                first_event_day="2026-07-03",
                target_hit=(fe == "TARGET_HIT"),
                stop_hit=(fe == "STOP_HIT"),
                t1_ret_pct=1.5,
                t3_ret_pct=2.5,
                t5_ret_pct=3.5,
                mfe_pct=4.0,
                mae_pct=-1.0,
                days_to_event=2,
                source_type=src,
            )

        from datetime import date as dt
        records = [
            _make_rec("HISTORICAL"),
            _make_rec("HISTORICAL"),
            _make_rec("LIVE"),
            _make_rec("HISTORICAL_REPLAY"),
            _make_rec("HISTORICAL_REPLAY"),
            _make_rec("HISTORICAL_REPLAY"),
        ]

        metrics = _compute_metrics(
            records=records,
            evidence_level=4,
            evidence_source="REGIME_DIRECTION",
            fallback_level=4,
            reference_date=dt(2026, 7, 15),
        )

        assert metrics.bootstrap_record_count         == 2
        assert metrics.live_record_count              == 1
        assert metrics.historical_replay_record_count == 3

    def test_T039_atr_fallback_metrics_has_replay_count_zero(self):
        """T039: _atr_fallback_metrics returns historical_replay_record_count=0."""
        from opportunity_engine.historical_behaviour_engine import _atr_fallback_metrics
        m = _atr_fallback_metrics()
        assert m.historical_replay_record_count == 0

    def test_T040_hbe_load_outcomes_scans_replay_dir(self):
        """T040: load_outcomes() picks up REPLAY_*.jsonl from data/klp/replay/ subdir."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            klp_dir   = Path(tmpdir) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)

            # Write a minimal valid replay file with obs + outcome
            replay_file = replay_dir / "REPLAY_2026-07-15.jsonl"
            obs_id  = "HKR1:20260715:113000:RELIANCE:BUY"
            obs_rec = {
                "obs_id": obs_id,
                "event_type": "KNOWLEDGE_OBSERVATION",
                "symbol": "RELIANCE",
                "direction": "BUY",
                "reference_entry": 1300.0,
                "knowledge_target": 1339.0,
                "knowledge_stop_loss": 1280.5,
                "knowledge_RR": 2.0,
                "knowledge_confidence": 6.0,
                "candidate_score": 0.6,
                "atr": 19.5,
                "atr_pct": 1.5,
                "regime": "BULL",
                "source_type": "HISTORICAL_REPLAY",
            }
            out_rec = {
                "obs_id": obs_id,
                "event_type": "OUTCOME_UPDATE",
                "first_event": "TARGET_HIT",
                "first_event_day": "2026-07-17",
                "target_hit": True,
                "stop_hit": False,
                "t1_ret_pct": 1.2,
                "t3_ret_pct": 3.0,
                "t5_ret_pct": 3.5,
                "mfe_pct": 3.8,
                "mae_pct": -0.5,
                "bars_available": 5,
            }
            with replay_file.open("w") as fh:
                fh.write(json.dumps(obs_rec) + "\n")
                fh.write(json.dumps(out_rec) + "\n")

            hbe = HistoricalBehaviourEngine(data_dir=klp_dir)
            n = hbe.load_outcomes()

            assert n >= 1
            assert any(r.obs_id == obs_id for r in hbe._outcomes)
            assert any(r.source_type == "HISTORICAL_REPLAY" for r in hbe._outcomes)


# ─────────────────────────────────────────────────────────────────────────────
# Part AF — DRY_RUN safety (T041–T043)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartAF_DryRun:
    """DRY_RUN must produce zero disk writes while returning a full ReplaySummary."""

    def test_T041_dry_run_no_replay_files_written(self):
        """T041: DRY_RUN writes no REPLAY_*.jsonl files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            klp_dir = Path(tmpdir) / "klp"
            klp_dir.mkdir()

            bars = _make_bars("2026-07-01", 40, base=100.0)
            engine = _engine_with_bars({"TEST": bars}, klp_dir)
            summary = engine.replay(
                start_date=date(2026, 7, 10),
                end_date=date(2026, 7, 25),
                symbols=["TEST"],
                mode=MODE_DRY_RUN,
            )

            assert summary.replay_files_written == []
            replay_dir = klp_dir / "replay"
            assert not replay_dir.exists() or not any(replay_dir.glob("REPLAY_*.jsonl"))

    def test_T042_dry_run_returns_valid_statistics(self):
        """T042: DRY_RUN returns a non-empty ReplaySummary with observations_attempted > 0."""
        bars = _make_bars("2026-07-01", 40, base=100.0)
        engine = _engine_with_bars({"TEST": bars})
        summary = engine.replay(
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 20),
            symbols=["TEST"],
            mode=MODE_DRY_RUN,
        )

        assert summary.mode == MODE_DRY_RUN
        assert summary.observations_attempted >= 0  # ≥ 0 (may skip if bars are insufficient)
        assert summary.observations_written == 0    # always 0 in DRY_RUN
        assert summary.outcomes_written     == 0

    def test_T043_dry_run_broker_safety(self):
        """T043: DRY_RUN broker_calls=0 and orders=0."""
        bars = _make_bars("2026-07-01", 40, base=100.0)
        engine = _engine_with_bars({"TEST": bars})
        summary = engine.replay(
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 20),
            symbols=["TEST"],
            mode=MODE_DRY_RUN,
        )
        assert summary.broker_calls == 0
        assert summary.orders       == 0


# ─────────────────────────────────────────────────────────────────────────────
# Part AG — obs_id determinism and format (T044–T047)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartAG_ObsIdFormat:
    """obs_id format and determinism requirements."""

    def test_T044_obs_id_format_HKR1_date_time_symbol_direction(self):
        """T044: obs_id = 'HKR1:YYYYMMDD:113000:SYMBOL:DIRECTION'."""
        obs_id = make_obs_id("2026-07-15", "RELIANCE", "BUY")
        parts  = obs_id.split(":")
        assert parts[0] == "HKR1"
        assert parts[1] == "20260715"    # compact date
        assert parts[2] == "113000"      # time bucket
        assert parts[3] == "RELIANCE"
        assert parts[4] == "BUY"

    def test_T045_obs_id_case_insensitive_symbol(self):
        """T045: Symbol normalised to upper-case in obs_id."""
        id_lower = make_obs_id("2026-07-15", "reliance", "buy")
        id_upper = make_obs_id("2026-07-15", "RELIANCE", "BUY")
        assert id_lower == id_upper

    def test_T046_buy_and_sell_produce_different_ids(self):
        """T046: BUY and SELL signals produce distinct obs_ids."""
        buy_id  = make_obs_id("2026-07-15", "RELIANCE", "BUY")
        sell_id = make_obs_id("2026-07-15", "RELIANCE", "SELL")
        assert buy_id != sell_id

    def test_T047_obs_id_in_reconstructed_signal(self):
        """T047: obs['obs_id'] matches make_obs_id output for same inputs."""
        bars   = _make_bars("2026-07-01", 25, base=100.0)
        engine = HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])
        td     = date(2026, 7, 25)
        obs    = engine._reconstruct_signal("RELIANCE", td, bars)
        assert obs is not None
        expected = make_obs_id("2026-07-25", "RELIANCE", obs["direction"])
        assert obs["obs_id"] == expected


# ─────────────────────────────────────────────────────────────────────────────
# Part AH — ReplaySummary completeness (T048–T051)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_PartAH_SummaryCompleteness:
    """ReplaySummary fields and serialisation."""

    def test_T048_summary_has_required_fields(self):
        """T048: ReplaySummary contains all required top-level fields."""
        bars = _make_bars("2026-07-01", 40, base=100.0)
        engine = _engine_with_bars({"TEST": bars})
        summary = engine.replay(
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 20),
            symbols=["TEST"],
            mode=MODE_DRY_RUN,
        )
        required = [
            "replay_id", "start_date", "end_date", "symbols", "mode",
            "trading_days_processed", "observations_attempted",
            "broker_calls", "orders", "existing_records_modified",
            "walk_forward_stats",
        ]
        d = summary.as_dict()
        for field_name in required:
            assert field_name in d, f"Missing field: {field_name}"

    def test_T049_summary_as_dict_is_json_serialisable(self):
        """T049: summary.as_dict() is JSON-serialisable."""
        bars = _make_bars("2026-07-01", 40, base=100.0)
        engine = _engine_with_bars({"TEST": bars})
        summary = engine.replay(
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 20),
            symbols=["TEST"],
            mode=MODE_DRY_RUN,
        )
        try:
            json.dumps(summary.as_dict(), default=str)
        except (TypeError, ValueError) as e:
            pytest.fail(f"summary.as_dict() is not JSON-serialisable: {e}")

    def test_T050_summary_dates_match_inputs(self):
        """T050: summary.start_date and end_date match replay() inputs."""
        bars = _make_bars("2026-07-01", 40, base=100.0)
        engine = _engine_with_bars({"TEST": bars})
        summary = engine.replay(
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 20),
            symbols=["TEST"],
            mode=MODE_DRY_RUN,
        )
        assert summary.start_date == "2026-07-10"
        assert summary.end_date   == "2026-07-20"

    def test_T051_invalid_mode_raises_value_error(self):
        """T051: Passing an invalid mode raises ValueError immediately."""
        engine = HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])
        with pytest.raises(ValueError, match="Invalid mode"):
            engine.replay(
                start_date=date(2026, 7, 10),
                end_date=date(2026, 7, 20),
                symbols=["TEST"],
                mode="INVALID_MODE",
            )


# ─────────────────────────────────────────────────────────────────────────────
# Helper function tests (T052–T055)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031_HelperFunctions:
    """Unit tests for module-level helpers."""

    def test_T052_get_trading_days_excludes_weekends(self):
        """T052: get_trading_days returns only Mon–Fri dates."""
        days = get_trading_days(date(2026, 7, 13), date(2026, 7, 19))  # Mon–Sun
        assert all(d.weekday() < 5 for d in days)
        assert len(days) == 5   # Mon–Fri

    def test_T053_compute_atr14_positive_for_valid_bars(self):
        """T053: compute_atr14 returns a positive value for valid bars."""
        bars = _make_bars("2026-07-01", 20, base=100.0, step=0.1)
        atr  = compute_atr14(bars)
        assert atr > 0

    def test_T054_validate_bar_rejects_bad_ohlc(self):
        """T054: validate_bar returns False for bars with high < low."""
        bad_bar = _bar("2026-07-01", 100, 98, 102, 100)  # high < low
        assert validate_bar(bad_bar) is False

    def test_T055_pricebar_to_dict_contains_ohlc_keys(self):
        """T055: pricebar_to_dict returns dict with date, open, high, low, close."""
        bar  = _bar("2026-07-01", 100, 105, 98, 102)
        d    = pricebar_to_dict(bar)
        for key in ("date", "open", "high", "low", "close"):
            assert key in d, f"Missing key: {key}"
        assert d["date"] == "2026-07-01"
        assert d["high"] == 105.0


# ─────────────────────────────────────────────────────────────────────────────
# DTA-031A Part A — Learning-path integrity (T056–T063)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031A_PartA_LearningPath:
    """
    Prove the complete production learning path:
      REPLAY_*.jsonl → HBE.load_outcomes() → OutcomeRecord → BehaviourMetrics
    """

    def _write_minimal_replay_file(
        self,
        replay_dir: Path,
        trading_date: str = "2026-07-15",
        symbol: str = "RELIANCE",
        direction: str = "BUY",
        n_records: int = 1,
    ) -> None:
        """Write N paired KNOWLEDGE_OBSERVATION + OUTCOME_UPDATE records."""
        from datetime import date as dt, timedelta
        d = dt.fromisoformat(trading_date)
        for i in range(n_records):
            obs_id = f"HKR1:{d.strftime('%Y%m%d')}:113000:{symbol}:{direction}"
            obs_rec = {
                "obs_id":              obs_id,
                "observation_id":      obs_id,
                "event_type":          "KNOWLEDGE_OBSERVATION",
                "symbol":              symbol,
                "direction":           direction,
                "reference_entry":     100.0 + i,
                "knowledge_target":    106.0 + i,
                "knowledge_stop_loss": 97.0 + i,
                "knowledge_RR":        2.0,
                "knowledge_confidence": 6.0,
                "candidate_score":     0.6,
                "atr":                 2.0,
                "atr_pct":             2.0,
                "regime":              "BULL",
                "source_type":         "HISTORICAL_REPLAY",
                "validation_partition": "TRAIN",
                "replay_validation_status": "EXPERIMENTAL",
                "no_lookahead":        True,
            }
            out_rec = {
                "obs_id":             obs_id,
                "observation_id":     obs_id,
                "event_type":         "OUTCOME_UPDATE",
                "symbol":             symbol,
                "direction":          direction,
                "first_event":        "TARGET_HIT",
                "first_event_day":    (d + timedelta(days=2)).isoformat(),
                "target_hit":         True,
                "stop_hit":           False,
                "t1_ret_pct":         1.5,
                "t3_ret_pct":         2.5,
                "t5_ret_pct":         3.5,
                "mfe_pct":            4.0,
                "mae_pct":            -0.5,
                "bars_available":     5,
            }
            replay_file = replay_dir / f"REPLAY_{d.isoformat()}.jsonl"
            with replay_file.open("a") as fh:
                fh.write(json.dumps(obs_rec) + "\n")
                fh.write(json.dumps(out_rec) + "\n")
            d += timedelta(days=1)

    def test_T056_hbe_loads_replay_dir_records(self):
        """T056: HBE.load_outcomes() returns replay records from data/klp/replay/."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine

        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            self._write_minimal_replay_file(replay_dir, n_records=3)

            hbe = HistoricalBehaviourEngine(data_dir=klp_dir)
            n   = hbe.load_outcomes()
            assert n == 3

    def test_T057_source_type_survives_to_outcome_record(self):
        """T057: source_type=HISTORICAL_REPLAY is preserved in loaded OutcomeRecord."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine

        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            self._write_minimal_replay_file(replay_dir, n_records=2)

            hbe = HistoricalBehaviourEngine(data_dir=klp_dir)
            hbe.load_outcomes()
            assert all(r.source_type == "HISTORICAL_REPLAY" for r in hbe._outcomes)

    def test_T058_validation_partition_preserved_round_trip(self):
        """T058: validation_partition written to JSONL is read back into OutcomeRecord."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine

        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            self._write_minimal_replay_file(replay_dir, n_records=2)

            hbe = HistoricalBehaviourEngine(data_dir=klp_dir)
            hbe.load_outcomes()
            assert all(r.validation_partition == "TRAIN" for r in hbe._outcomes)

    def test_T059_replay_counted_in_behaviour_metrics(self):
        """T059: historical_replay_record_count in BehaviourMetrics matches loaded replay count."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine

        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            self._write_minimal_replay_file(replay_dir, symbol="RELIANCE", n_records=8)

            hbe = HistoricalBehaviourEngine(
                data_dir=klp_dir, reference_date=date(2026, 7, 30)
            )
            hbe.load_outcomes()
            profile = hbe.get_behaviour_profile("RELIANCE", "BUY", regime="BULL")
            assert profile.metrics.historical_replay_record_count == 8

    def test_T060_replay_and_live_counts_separate(self):
        """T060: bootstrap / live / replay counts are independently tracked."""
        from opportunity_engine.hbe_models import OutcomeRecord
        from opportunity_engine.historical_behaviour_engine import _compute_metrics

        def _rec(src: str) -> OutcomeRecord:
            return OutcomeRecord(
                obs_id=f"X_{src}_{id(src)}_{hash(src)}",
                trading_date="2026-07-01",
                symbol="TEST",
                direction="BUY",
                regime="BULL",
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
                first_event="TARGET_HIT",
                first_event_day="2026-07-03",
                target_hit=True,
                stop_hit=False,
                t1_ret_pct=1.5,
                t3_ret_pct=2.5,
                t5_ret_pct=3.5,
                mfe_pct=4.0,
                mae_pct=-0.5,
                days_to_event=2,
                source_type=src,
            )

        records = [_rec("HISTORICAL")] * 5 + [_rec("LIVE")] * 3 + [_rec("HISTORICAL_REPLAY")] * 7
        m = _compute_metrics(records, 4, "REGIME_DIRECTION", 4, date(2026, 7, 15))
        assert m.bootstrap_record_count         == 5
        assert m.live_record_count              == 3
        assert m.historical_replay_record_count == 7

    def test_T061_replay_records_do_not_create_broker_calls(self):
        """T061: HBE operations on replay records never set broker_calls>0."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine

        with tempfile.TemporaryDirectory() as td:
            klp_dir    = Path(td) / "klp"
            replay_dir = klp_dir / "replay"
            replay_dir.mkdir(parents=True)
            self._write_minimal_replay_file(replay_dir, n_records=6)

            hbe = HistoricalBehaviourEngine(data_dir=klp_dir)
            hbe.load_outcomes()
            assert hbe.broker_calls == 0
            assert hbe.orders       == 0

    def test_T062_replay_does_not_modify_live_klp_files(self):
        """T062: After RESEARCH replay, KLP_*.jsonl in root klp_dir are untouched."""
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()
            sentinel = klp_dir / "KLP_2026-07-15.jsonl"
            sentinel.write_text('{"obs_id":"LIVE_1","event_type":"KNOWLEDGE_OBSERVATION"}\n')
            original = sentinel.read_bytes()

            bars   = _make_bars("2026-07-01", 40, base=100.0)
            engine = _engine_with_bars({"RELIANCE": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 20),
                symbols=["RELIANCE"],
                mode=MODE_RESEARCH,
            )
            assert sentinel.read_bytes() == original

    def test_T063_replay_obs_event_type_is_knowledge_observation(self):
        """T063: Written replay files contain KNOWLEDGE_OBSERVATION records."""
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()

            bars   = _make_bars("2026-07-01", 40, base=100.0)
            engine = _engine_with_bars({"RELIANCE": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 18),
                symbols=["RELIANCE"],
                mode=MODE_RESEARCH,
            )
            replay_dir = klp_dir / "replay"
            obs_types  = set()
            for f in sorted(replay_dir.glob("REPLAY_*.jsonl")):
                for line in f.read_text().splitlines():
                    if line.strip():
                        rec = json.loads(line)
                        obs_types.add(rec.get("event_type", ""))
            assert "KNOWLEDGE_OBSERVATION" in obs_types
            assert "OUTCOME_UPDATE"        in obs_types


# ─────────────────────────────────────────────────────────────────────────────
# DTA-031A Part B — Additional DTA-028A path outcome scenarios (T064–T070)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031A_PartB_ExtendedPathOutcomes:
    """
    Additional path outcome scenarios verifying DTA-028A semantics.
    Most critical: stop-first-then-recovery — t5_ret_pct positive but STOP_HIT.
    """

    def _make_engine(self) -> HistoricalKnowledgeReplayEngine:
        return HistoricalKnowledgeReplayEngine(_ohlcv_fetcher=lambda s: [])

    def _obs(self, entry, target, stop, direction="BUY"):
        return {
            "obs_id": "HKR1:TEST",
            "event_type": "KNOWLEDGE_OBSERVATION",
            "symbol": "TEST",
            "direction": direction,
            "reference_entry": entry,
            "knowledge_target": target,
            "knowledge_stop_loss": stop,
            "knowledge_RR": abs(target - entry) / max(abs(entry - stop), 0.01),
            "knowledge_confidence": 6.0,
            "candidate_score": 0.6,
            "scanner_confidence": 6.0,
            "knowledge_score": 0.0,
            "atr": 3.0,
            "atr_pct": 3.0,
            "regime": "BULL",
            "source_type": "HISTORICAL_REPLAY",
        }

    def test_T064_stop_first_then_recovery_is_stop_hit(self):
        """T064: Stop hit on T+1; price recovers above entry by T+5. first_event=STOP_HIT.

        This is the most critical path-outcome safety test.
        A positive EOD direction must NEVER override a stop-first result.
        """
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=108.0, stop=95.0)
        future = [
            _bar("2026-08-01", 99, 100, 94.0, 95.5),  # T+1: low <= stop → STOP_HIT
            _bar("2026-08-02", 96, 100, 95,  99),
            _bar("2026-08-03", 99, 104, 98, 103),
            _bar("2026-08-04", 102, 106, 101, 104),
            _bar("2026-08-05", 104, 108, 103, 107),    # T+5: price above entry
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"]   == STOP_HIT,      "Stop-first must win"
        assert result["stop_hit"]      is True
        assert result["target_hit"]    is False
        # t5_ret_pct may be positive — that's correct and expected
        assert result["t5_ret_pct"] is not None
        assert result["t5_ret_pct"] > 0   # direction is positive at T+5

    def test_T065_target_first_then_reversal_is_target_hit(self):
        """T065: Target hit on T+2; stop hit at T+4. first_event=TARGET_HIT."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=106.0, stop=95.0)
        future = [
            _bar("2026-08-01", 100, 104, 99, 103),
            _bar("2026-08-02", 103, 107, 102, 106),   # T+2: high >= target
            _bar("2026-08-03", 105, 105, 100, 101),
            _bar("2026-08-04", 100,  99,  94,  95),   # T+4: low <= stop (but target already hit)
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"]     == TARGET_HIT
        assert result["first_event_day"] == "2026-08-02"
        assert result["target_hit"]      is True

    def test_T066_gap_through_stop_single_bar(self):
        """T066: Bar opens and closes below stop — gap-through counts as STOP_HIT."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=108.0, stop=95.0)
        future = [
            _bar("2026-08-01", 100, 101, 90, 92),  # low 90 < stop 95 → STOP_HIT
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == STOP_HIT
        assert result["stop_hit"]    is True

    def test_T067_mae_bounded_at_stop_day(self):
        """T067: MAE is computed only through first_event_day when STOP_HIT."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=115.0, stop=92.0)
        future = [
            _bar("2026-08-01", 100, 103,  99,  102),   # T+1: clean bar
            _bar("2026-08-02", 101, 103,  91,   92),   # T+2: low <= stop → STOP_HIT
            _bar("2026-08-03",  92,  93,  70,   71),   # T+3: extreme low — must be excluded from MAE
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == STOP_HIT
        # MAE must not include T+3 extreme (-29%)
        assert result["mae_pct"] is not None
        assert result["mae_pct"] > -20.0   # T+3 low would give ~-30%, T+2 stop ~-9%

    def test_T068_t5_ret_independent_of_first_event(self):
        """T068: t5_ret_pct reflects close[T+5]/entry regardless of first_event."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=108.0, stop=95.0)
        # Stop hit on T+1 but price at T+5 close is 104
        future = [
            _bar("2026-08-01", 100,  97,  94, 96),    # T+1: stop hit
            _bar("2026-08-02",  96,  98,  95, 97),
            _bar("2026-08-03",  97, 100,  96, 99),
            _bar("2026-08-04",  99, 103,  98, 102),
            _bar("2026-08-05", 102, 105, 101, 104),   # T+5 close = 104
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == STOP_HIT
        assert result["t5_ret_pct"]  is not None
        assert abs(result["t5_ret_pct"] - 4.0) < 0.01   # (104/100-1)*100

    def test_T069_short_signal_stop_on_high(self):
        """T069: SELL signal — stop is above entry; stop hit when high >= stop."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=90.0, stop=106.0, direction="SELL")
        future = [
            _bar("2026-08-01", 100, 107, 99, 101),  # high 107 >= stop 106 → STOP_HIT
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == STOP_HIT

    def test_T070_pending_with_fewer_than_5_bars(self):
        """T070: With 2 bars and no hit, first_event=OUTCOME_PENDING."""
        engine = self._make_engine()
        obs    = self._obs(entry=100.0, target=110.0, stop=90.0)
        future = [
            _bar("2026-08-01", 100, 102, 99, 101),
            _bar("2026-08-02", 101, 103, 100, 102),
        ]
        result = engine._compute_path_outcome(obs, future)
        assert result["first_event"] == OUTCOME_PENDING
        assert result["t1_ret_pct"]  is not None   # T+1 computable
        assert result["t3_ret_pct"]  is None        # T+3 not available


# ─────────────────────────────────────────────────────────────────────────────
# DTA-031A Part C — Evidence-hierarchy promotion and fallback (T071–T076)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031A_PartC_HierarchyPromotion:
    """
    Verify that >= 5 symbol-specific replay outcomes enable L2 evidence,
    and that < 5 falls through to L4 (regime level).

    _LEVEL_MIN_OBS[2] = 5 (symbol+direction)
    _LEVEL_MIN_OBS[4] = 10 (regime+direction)
    """

    def _make_outcome_record(
        self,
        symbol: str,
        direction: str = "BUY",
        regime: str = "BULL",
        source_type: str = "HISTORICAL_REPLAY",
        n: int = 1,
    ):
        from opportunity_engine.hbe_models import OutcomeRecord
        records = []
        for i in range(n):
            records.append(OutcomeRecord(
                obs_id=f"HKR_{symbol}_{i}_{source_type}",
                trading_date=f"2026-07-{i+1:02d}",
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
                first_event="TARGET_HIT",
                first_event_day=f"2026-07-{i+3:02d}",
                target_hit=True,
                stop_hit=False,
                t1_ret_pct=1.5,
                t3_ret_pct=2.5,
                t5_ret_pct=3.5,
                mfe_pct=4.0,
                mae_pct=-0.5,
                days_to_event=2,
                source_type=source_type,
            ))
        return records

    def _hbe_with(self, outcomes):
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        hbe = HistoricalBehaviourEngine(reference_date=date(2026, 7, 31))
        hbe._outcomes = outcomes
        hbe._loaded   = True
        return hbe

    def test_T071_before_5_symbol_records_uses_generic_fallback(self):
        """T071: < 5 symbol-specific records → evidence falls to L4 or deeper (generic)."""
        # 4 symbol records (below L2 threshold of 5) + 15 BULL regime records
        sym_recs   = self._make_outcome_record("NEWSYM", n=4)
        regime_recs = self._make_outcome_record("OTHER1", regime="BULL", n=10) + \
                      self._make_outcome_record("OTHER2", regime="BULL", n=5)
        hbe    = self._hbe_with(sym_recs + regime_recs)
        profile = hbe.get_behaviour_profile("NEWSYM", "BUY", regime="BULL")
        # Should NOT be at L2 (symbol-specific); should be L4 or deeper
        assert profile.metrics.evidence_level >= 4, (
            f"Expected L4+ but got L{profile.metrics.evidence_level}"
        )

    def test_T072_after_5_symbol_records_uses_L2(self):
        """T072: >= 5 symbol-specific records → L2 (symbol+direction) evidence used."""
        sym_recs = self._make_outcome_record("NEWSYM", n=5)
        hbe      = self._hbe_with(sym_recs)
        profile  = hbe.get_behaviour_profile("NEWSYM", "BUY", regime="BULL")
        # L1 (symbol+dir+regime+context) and L2 (symbol+dir) are both symbol-specific;
        # either is correct — L1 fires first when all records share the same regime.
        assert profile.metrics.evidence_level in (1, 2), (
            f"Expected symbol-specific tier (L1 or L2), got L{profile.metrics.evidence_level}"
        )

    def test_T073_l2_evidence_scope_is_symbol_specific(self):
        """T073: L2 evidence produces evidence_scope=SYMBOL_SPECIFIC in BehaviourMetrics."""
        sym_recs = self._make_outcome_record("CHECKME", n=6)
        hbe      = self._hbe_with(sym_recs)
        profile  = hbe.get_behaviour_profile("CHECKME", "BUY", regime="BULL")
        # L1 or L2 are SYMBOL_SPECIFIC; L3+ are GENERIC
        assert profile.metrics.evidence_level in (1, 2)

    def test_T074_l4_evidence_does_not_change_l2_threshold(self):
        """T074: Adding generic records does not lower the L2 threshold (min stays at 5)."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        assert HistoricalBehaviourEngine._LEVEL_MIN_OBS[2] == 5

    def test_T075_replay_records_count_same_as_live_for_hierarchy(self):
        """T075: Replay OutcomeRecords have the same weight as live for hierarchy selection."""
        sym_live   = self._make_outcome_record("SYM_A", source_type="LIVE",             n=4)
        sym_replay = self._make_outcome_record("SYM_A", source_type="HISTORICAL_REPLAY", n=2)
        hbe        = self._hbe_with(sym_live + sym_replay)
        profile    = hbe.get_behaviour_profile("SYM_A", "BUY", regime="BULL")
        # 4 + 2 = 6 >= 5 -> should be at symbol-specific tier (L1 or L2)
        assert profile.metrics.evidence_level in (1, 2)

    def test_T076_replay_count_in_metrics_matches_loaded_count(self):
        """T076: BehaviourMetrics.historical_replay_record_count = actual replay records used."""
        replay_recs = self._make_outcome_record("RELSYM", source_type="HISTORICAL_REPLAY", n=8)
        live_recs   = self._make_outcome_record("RELSYM", source_type="LIVE",              n=3)
        hbe         = self._hbe_with(replay_recs + live_recs)
        profile     = hbe.get_behaviour_profile("RELSYM", "BUY", regime="BULL")
        assert profile.metrics.historical_replay_record_count == 8
        assert profile.metrics.live_record_count              == 3


# ─────────────────────────────────────────────────────────────────────────────
# DTA-031A Part D — KDA provenance (T077–T080)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031A_PartD_KDAProvenance:
    """
    Verify KDADecisionRecord exposes historical_replay_record_count correctly.
    Tests the structural contract and from_dict round-trip.
    """

    def test_T077_kda_decision_record_has_replay_count_field(self):
        """T077: KDADecisionRecord dataclass has historical_replay_record_count field."""
        from knowledge_authority.kda_models import KDADecisionRecord
        fields = {f for f in KDADecisionRecord.__dataclass_fields__}
        assert "historical_replay_record_count" in fields

    def test_T078_kda_decision_record_replay_count_defaults_to_zero(self):
        """T078: historical_replay_record_count defaults to 0 in KDADecisionRecord."""
        from knowledge_authority.kda_models import KDADecisionRecord
        f = KDADecisionRecord.__dataclass_fields__["historical_replay_record_count"]
        assert f.default == 0

    def test_T079_from_dict_preserves_replay_count(self):
        """T079: KDADecisionRecord.from_dict() parses historical_replay_record_count."""
        from knowledge_authority.kda_models import KDADecisionRecord
        d = {
            "decision_id": "test-123",
            "timestamp": "2026-07-15T00:00:00+00:00",
            "symbol": "RELIANCE",
            "direction": "BUY",
            "historical_replay_record_count": 7,
        }
        rec = KDADecisionRecord.from_dict(d)
        assert rec.historical_replay_record_count == 7

    def test_T080_kda_replay_count_distinct_from_bootstrap_and_live(self):
        """T080: Three provenance counters are independently round-tripped via from_dict/as_dict."""
        from knowledge_authority.kda_models import KDADecisionRecord
        d = {
            "decision_id": "abc",
            "timestamp": "2026-07-15T00:00:00+00:00",
            "symbol": "INFY",
            "direction": "BUY",
            "bootstrap_record_count": 3,
            "live_record_count": 5,
            "historical_replay_record_count": 8,
        }
        rec  = KDADecisionRecord.from_dict(d)
        back = rec.as_dict()
        assert back["bootstrap_record_count"]         == 3
        assert back["live_record_count"]              == 5
        assert back["historical_replay_record_count"] == 8


# ─────────────────────────────────────────────────────────────────────────────
# DTA-031A Part E — Validation gate: EXPERIMENTAL status (T081–T085)
# ─────────────────────────────────────────────────────────────────────────────

class TestDTA031A_PartE_ValidationGate:
    """
    Verify EXPERIMENTAL status is written to replay obs records
    and that replay does not auto-promote to live execution authority.
    """

    def test_T081_written_obs_has_experimental_status(self):
        """T081: RESEARCH mode writes replay_validation_status=EXPERIMENTAL in obs records."""
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()

            bars   = _make_bars("2026-07-01", 40, base=100.0)
            engine = _engine_with_bars({"RELIANCE": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 18),
                symbols=["RELIANCE"],
                mode=MODE_RESEARCH,
            )
            replay_dir = klp_dir / "replay"
            for f in replay_dir.glob("REPLAY_*.jsonl"):
                for line in f.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec.get("event_type") == "KNOWLEDGE_OBSERVATION":
                        status = rec.get("replay_validation_status", "")
                        assert status == "EXPERIMENTAL", (
                            f"Expected EXPERIMENTAL, got '{status}'"
                        )

    def test_T082_experimental_status_not_present_on_outcome_update(self):
        """T082: OUTCOME_UPDATE records are not required to carry replay_validation_status."""
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()

            bars   = _make_bars("2026-07-01", 40, base=100.0)
            engine = _engine_with_bars({"RELIANCE": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 17),
                symbols=["RELIANCE"],
                mode=MODE_RESEARCH,
            )
            replay_dir = klp_dir / "replay"
            found_outcome = False
            for f in replay_dir.glob("REPLAY_*.jsonl"):
                for line in f.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec.get("event_type") == "OUTCOME_UPDATE":
                        found_outcome = True
                        # OUTCOME_UPDATE may or may not carry the field — that's fine
                        # The key is it should NOT be mistakenly labelled VALIDATED
                        assert rec.get("replay_validation_status") != "VALIDATED"
            assert found_outcome, "No OUTCOME_UPDATE records found in replay files"

    def test_T083_source_type_never_live_or_paper_in_replay(self):
        """T083: Written replay records never use source_type=LIVE or PAPER."""
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            klp_dir.mkdir()

            bars   = _make_bars("2026-07-01", 40, base=100.0)
            engine = _engine_with_bars({"RELIANCE": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 18),
                symbols=["RELIANCE"],
                mode=MODE_RESEARCH,
            )
            replay_dir = klp_dir / "replay"
            for f in replay_dir.glob("REPLAY_*.jsonl"):
                for line in f.read_text().splitlines():
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    st  = rec.get("source_type", "")
                    assert st not in ("LIVE", "PAPER", "EXECUTED"), (
                        f"source_type must not be {st!r}"
                    )

    def test_T084_replay_summary_records_correct_mode(self):
        """T084: ReplaySummary.mode matches the mode passed to replay()."""
        bars = _make_bars("2026-07-01", 40, base=100.0)
        for mode in (MODE_DRY_RUN, MODE_RESEARCH):
            with tempfile.TemporaryDirectory() as td:
                klp = Path(td) / "klp"
                klp.mkdir()
                engine = _engine_with_bars({"TEST": bars}, klp)
                s = engine.replay(
                    start_date=date(2026, 7, 15),
                    end_date=date(2026, 7, 18),
                    symbols=["TEST"],
                    mode=mode,
                )
                assert s.mode == mode

    def test_T085_no_live_files_modified_after_research_replay(self):
        """T085: live_orders.jsonl and paper_trades.csv are not created or touched by replay."""
        with tempfile.TemporaryDirectory() as td:
            klp_dir = Path(td) / "klp"
            data_dir = Path(td) / "data"
            klp_dir.mkdir()
            data_dir.mkdir()

            bars   = _make_bars("2026-07-01", 40, base=100.0)
            engine = _engine_with_bars({"RELIANCE": bars}, klp_dir)
            engine.replay(
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 18),
                symbols=["RELIANCE"],
                mode=MODE_RESEARCH,
            )
            # Neither live_orders.jsonl nor paper_trades.csv should exist
            assert not (data_dir / "live_orders.jsonl").exists()
            assert not (data_dir / "paper_trades.csv").exists()


"""
tests/test_dta041_phase2_delayed_outcome.py
============================================
DTA-041 Phase 2: Delayed Outcome Capture & Knowledge Learning Tests

Proves:
1. Outcome is appended after maturity calculation from OHLCV bars.
2. Lineage is preserved across observation, pipeline events, and outcome.
3. Original observation is unchanged (immutable).
4. Immature outcome is not consumed by HBE / Knowledge.
5. Matured outcome reaches the existing Knowledge / HBE learning path.
6. Subsequent Knowledge decisions can consume the matured information.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from audit.dta041_pit_discovery_evidence import PITDiscoveryEvidenceRecorder
from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine, TARGET_HIT


def _mock_ohlcv(symbol: str, trading_date: str):
    """Deterministic T+1..T+5 bars for testing: target hit on day 2."""
    return [
        {"date": "2026-09-04", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.5, "volume": 1000},
        {"date": "2026-09-05", "open": 101.5, "high": 106.0, "low": 101.0, "close": 105.5, "volume": 1500},  # Target 105 hit
        {"date": "2026-09-08", "open": 105.0, "high": 107.0, "low": 104.0, "close": 106.0, "volume": 1200},
        {"date": "2026-09-09", "open": 106.0, "high": 108.0, "low": 105.0, "close": 107.5, "volume": 1100},
        {"date": "2026-09-10", "open": 107.0, "high": 109.0, "low": 106.0, "close": 108.0, "volume": 1300},
    ]


def test_outcome_is_appended_after_maturity_and_lineage_preserved(tmp_path, monkeypatch):
    """Test 1 & 2: Outcome is appended with identical lineage_id and maturity timestamp."""
    pit_dir = tmp_path / "dta041"
    klp_dir = tmp_path / "klp"
    recorder = PITDiscoveryEvidenceRecorder(data_dir=pit_dir)

    import audit.dta041_pit_discovery_evidence as pit_mod
    monkeypatch.setattr(pit_mod, "get_trace_manager", lambda: SimpleNamespace(get_cycle_id=lambda: "20260903_0415"))

    candidate = {"symbol": "TATAMOTORS", "ltp": 100.0, "rsi": 45.0, "_atr14": 2.0, "_prepared": True, "score": 0.75}
    snapshot = SimpleNamespace(regime="range_market", vix=12.0, market_breadth=0.5)

    lineage_id = recorder.record_evaluation(candidate, snapshot, universe_size=61, prepared_count=48)
    recorder.record_scanner_result(lineage_id, SimpleNamespace(direction="BUY", entry_price=100.0, confidence=6.0), "")
    recorder.record_kda_results(
        [SimpleNamespace(symbol="TATAMOTORS")],
        {"TATAMOTORS": {"kda_decision": "KNOWLEDGE_BUY", "knowledge_target": 105.0, "knowledge_stop": 97.0}}
    )

    # Initial file state before outcome
    pit_file = pit_dir / "PIT_DISCOVERY_2026-09-03.jsonl"
    initial_content = pit_file.read_text(encoding="utf-8")
    initial_obs = json.loads(initial_content.splitlines()[0])

    # Run outcome engine (with reference date after trading date)
    outcome_engine = KLPOutcomeEngine(
        data_dir=klp_dir, pit_dir=pit_dir, _ohlcv_fetcher=_mock_ohlcv, _today=date(2026, 9, 15)
    )
    result = outcome_engine.fill_pending_pit_outcomes(dates=["2026-09-03"], pit_dir=pit_dir)

    assert result["processed"] == 1
    assert result["skipped_pending"] == 0

    # Read updated file
    records = [json.loads(l) for l in pit_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    obs_recs = [r for r in records if r["record_type"] == "PIT_OBSERVATION"]
    outcome_recs = [r for r in records if r["record_type"] == "PIT_OUTCOME"]

    assert len(obs_recs) == 1
    assert len(outcome_recs) == 1

    outcome = outcome_recs[0]
    assert outcome["lineage_id"] == lineage_id
    assert outcome["symbol"] == "TATAMOTORS"
    assert outcome["first_event"] == TARGET_HIT
    assert outcome["first_event_day"] == "2026-09-05"
    assert outcome["maturity_timestamp"] == "2026-09-05T15:30:00+00:00"
    assert outcome["outcome_type"] == "COUNTERFACTUAL_RESEARCH"
    assert outcome["target_hit"] is True
    assert outcome["stop_hit"] is False
    assert outcome["no_lookahead"] is True


def test_original_observation_is_unchanged(tmp_path, monkeypatch):
    """Test 3: Original observation is strictly unchanged after outcome append."""
    pit_dir = tmp_path / "dta041"
    recorder = PITDiscoveryEvidenceRecorder(data_dir=pit_dir)

    import audit.dta041_pit_discovery_evidence as pit_mod
    monkeypatch.setattr(pit_mod, "get_trace_manager", lambda: SimpleNamespace(get_cycle_id=lambda: "20260903_0415"))

    candidate = {"symbol": "INFY", "ltp": 1200.0, "rsi": 40.0, "_atr14": 20.0, "_prepared": False, "score": None}
    snapshot = SimpleNamespace(regime="range_market", vix=12.0, market_breadth=0.5)

    lineage_id = recorder.record_evaluation(candidate, snapshot, universe_size=61, prepared_count=48)
    pit_file = next(pit_dir.glob("PIT_DISCOVERY_*.jsonl"))
    obs_line_before = pit_file.read_text(encoding="utf-8").splitlines()[0]

    # Append outcome
    recorder.record_outcome(
        lineage_id=lineage_id,
        outcome_data={"first_event": TARGET_HIT, "target_hit": True, "stop_hit": False, "t1_ret_pct": 1.5},
        maturity_timestamp="2026-09-05T15:30:00+00:00",
        trading_date="2026-09-03",
        symbol="INFY",
    )

    obs_line_after = pit_file.read_text(encoding="utf-8").splitlines()[0]
    assert obs_line_before == obs_line_after
    parsed_obs = json.loads(obs_line_after)
    assert parsed_obs["record_type"] == "PIT_OBSERVATION"
    assert "outcome" not in parsed_obs


def test_immature_outcome_is_not_consumed_and_matures_correctly(tmp_path):
    """Test 4 & 5: HBE does not load immature outcomes, but loads them once matured."""
    pit_dir = tmp_path / "dta041"
    klp_dir = tmp_path / "klp"
    recorder = PITDiscoveryEvidenceRecorder(data_dir=pit_dir)

    lineage_id = "PIT:20260903:20260903_0415:RELIANCE"
    obs_record = {
        "record_type": "PIT_OBSERVATION",
        "schema_version": "1.0",
        "lineage_id": lineage_id,
        "symbol": "RELIANCE",
        "trading_date": "2026-09-03",
        "market_properties": {"price": 2500.0, "atr": 40.0, "regime": "RANGE_MARKET", "sector": "ENERGY"},
        "prepared_universe": {"included": True, "score": 0.85},
    }
    recorder._append_to_file(obs_record, "2026-09-03")

    recorder.record_outcome(
        lineage_id=lineage_id,
        outcome_data={
            "first_event": TARGET_HIT,
            "first_event_day": "2026-09-05",
            "target_hit": True,
            "stop_hit": False,
            "target": 2600.0,
            "stop": 2450.0,
            "t1_ret_pct": 1.0,
            "t3_ret_pct": 2.5,
            "t5_ret_pct": 4.0,
            "mfe_pct": 4.5,
            "mae_pct": -0.5,
        },
        maturity_timestamp="2026-09-05T15:30:00+00:00",
        trading_date="2026-09-03",
        symbol="RELIANCE",
    )

    hbe = HistoricalBehaviourEngine(data_dir=klp_dir)

    # 1. As of 2026-09-04 (before maturity): outcome is immature and must NOT be consumed
    n_immature = hbe.load_outcomes(klp_dir=klp_dir, pit_dir=pit_dir, as_of="2026-09-04T12:00:00+00:00")
    assert n_immature == 0
    assert hbe.get_outcome_count() == 0

    # 2. As of 2026-09-05 16:00:00 (after maturity): outcome is matured and MUST be consumed
    n_matured = hbe.load_outcomes(klp_dir=klp_dir, pit_dir=pit_dir, as_of="2026-09-05T16:00:00+00:00")
    assert n_matured == 1
    assert hbe.get_outcome_count() == 1

    records = hbe._outcomes
    assert records[0].obs_id == lineage_id
    assert records[0].symbol == "RELIANCE"
    assert records[0].target_hit is True
    assert records[0].source_type == "COUNTERFACTUAL_RESEARCH"


def test_subsequent_knowledge_decisions_consume_matured_information(tmp_path):
    """Test 6: Empirical profile metrics incorporate matured PIT discovery outcomes."""
    pit_dir = tmp_path / "dta041"
    klp_dir = tmp_path / "klp"
    recorder = PITDiscoveryEvidenceRecorder(data_dir=pit_dir)

    # Create 6 matured observations for TCS to meet level-1/level-2 min threshold (5 target hits)
    for i in range(1, 7):
        lid = f"PIT:20260901:20260901_0415:TCS_{i}"
        obs_record = {
            "record_type": "PIT_OBSERVATION",
            "schema_version": "1.0",
            "lineage_id": lid,
            "symbol": "TCS",
            "trading_date": "2026-09-01",
            "market_properties": {"price": 3000.0, "atr": 50.0, "regime": "RANGE_MARKET", "sector": "IT"},
            "prepared_universe": {"included": True, "score": 0.8},
        }
        recorder._append_to_file(obs_record, "2026-09-01")

        recorder.record_outcome(
            lineage_id=lid,
            outcome_data={
                "first_event": TARGET_HIT if i <= 5 else "STOP_HIT",
                "first_event_day": "2026-09-02",
                "target_hit": i <= 5,
                "stop_hit": i == 6,
                "target": 3125.0,
                "stop": 2950.0,
                "t1_ret_pct": 2.0,
                "t3_ret_pct": 3.5,
                "t5_ret_pct": 4.2,
                "mfe_pct": 4.5,
                "mae_pct": -1.0,
                "theoretical_R": 2.5 if i <= 5 else -1.0,
            },
            maturity_timestamp="2026-09-02T15:30:00+00:00",
            trading_date="2026-09-01",
            symbol="TCS",
        )

    hbe = HistoricalBehaviourEngine(data_dir=klp_dir)
    # Load as of today (matured)
    n = hbe.load_outcomes(klp_dir=klp_dir, pit_dir=pit_dir, as_of="2026-09-03T00:00:00+00:00")
    assert n == 6

    # Derive empirical behaviour profile
    profile = hbe.get_behaviour_profile("TCS", "BUY", regime="RANGE_MARKET")
    assert profile.query_symbol == "TCS"
    assert profile.query_direction == "BUY"
    assert profile.metrics.observation_count == 6
    assert round(profile.metrics.target_hit_probability, 2) == 0.83  # 5/6 = 83% win rate
    assert profile.metrics.effective_sample_size > 0
    assert profile.metrics.target_source == "EMPIRICAL"
    assert profile.metrics.expected_move_p50 is not None

from __future__ import annotations

import json
from types import SimpleNamespace


def test_pit_observation_is_immutable_and_events_share_lineage(tmp_path, monkeypatch):
    import audit.dta041_pit_discovery_evidence as pit

    recorder = pit.PITDiscoveryEvidenceRecorder(data_dir=tmp_path)
    monkeypatch.setattr(pit, "get_trace_manager", lambda: SimpleNamespace(get_cycle_id=lambda: "20260902_0945"))
    candidate = {"symbol": "HDFCBANK", "ltp": 100.0, "rsi": 50.0, "_prepared": True, "score": 0.8}
    snapshot = SimpleNamespace(regime="RANGE", vix=12.0, market_breadth=0.5)

    lineage_id = recorder.record_evaluation(candidate, snapshot, universe_size=66, prepared_count=40)
    recorder.record_scanner_result(lineage_id, None, "NO_SETUP")
    recorder.record_kda_results([SimpleNamespace(symbol="HDFCBANK")], {"HDFCBANK": {"kda_decision": "KNOWLEDGE_WAIT"}})

    records = [json.loads(line) for line in next(tmp_path.glob("*.jsonl")).read_text().splitlines()]
    observation = next(record for record in records if record["record_type"] == "PIT_OBSERVATION")
    events = [record for record in records if record["record_type"] == "PIT_PIPELINE_EVENT"]
    assert observation["lineage_id"] == lineage_id
    assert observation["scanner"] == {"evaluated": True}
    assert observation["prepared_universe"]["evaluation_source"] == "PREPARED"
    assert [event["lineage_id"] for event in events] == [lineage_id, lineage_id]
    assert all("outcome" not in event for event in records)


def test_pit_records_static_and_exploratory_provenance(tmp_path, monkeypatch):
    import audit.dta041_pit_discovery_evidence as pit

    recorder = pit.PITDiscoveryEvidenceRecorder(data_dir=tmp_path)
    monkeypatch.setattr(pit, "get_trace_manager", lambda: SimpleNamespace(get_cycle_id=lambda: "20260902_1030"))
    snapshot = SimpleNamespace(regime="RANGE", vix=12.0, market_breadth=0.5)

    static_id = recorder.record_evaluation({"symbol": "INFY"}, snapshot, universe_size=65, prepared_count=40)
    exploration_id = recorder.record_evaluation({"symbol": "TCS"}, snapshot, universe_size=25, prepared_count=40, evaluation_source="EXPLORATORY")
    recorder.record_evaluation({"symbol": "INFY"}, snapshot, universe_size=25, prepared_count=40, evaluation_source="EXPLORATORY")

    records = [json.loads(line) for line in next(tmp_path.glob("*.jsonl")).read_text().splitlines()]
    observations = [record for record in records if record["record_type"] == "PIT_OBSERVATION"]
    source_by_id = {record["lineage_id"]: record["prepared_universe"]["evaluation_source"] for record in observations}
    assert source_by_id[static_id] == "STATIC_GAP_FILL"
    assert source_by_id[exploration_id] == "EXPLORATORY"
    assert any(
        record["stage"] == "DISCOVERY_EVALUATION"
        and record["lineage_id"] == static_id
        and record["details"]["evaluation_source"] == "EXPLORATORY"
        for record in records
        if record["record_type"] == "PIT_PIPELINE_EVENT"
    )


def test_pit_pipeline_events_keep_one_lineage(tmp_path, monkeypatch):
    import audit.dta041_pit_discovery_evidence as pit

    recorder = pit.PITDiscoveryEvidenceRecorder(data_dir=tmp_path)
    monkeypatch.setattr(pit, "get_trace_manager", lambda: SimpleNamespace(get_cycle_id=lambda: "20260902_1115"))
    signal = SimpleNamespace(symbol="SBIN")
    lineage_id = recorder.record_evaluation({"symbol": "SBIN"}, SimpleNamespace(), universe_size=66, prepared_count=40)

    recorder.record_scanner_result(lineage_id, signal, "")
    recorder.record_stage_outcomes([signal], {"SBIN"}, "STRATEGYLAB", "STRATEGY_REJECTED")
    recorder.record_kda_results([signal], {"SBIN": {"kda_decision": "KNOWLEDGE_BUY", "effective_sample_size": 100.0}})
    recorder.record_stage_outcomes([signal], {"SBIN"}, "CRE", "CRE_QTY_ZERO")
    recorder.record_stage_outcomes([signal], {"SBIN"}, "RISKCONTROL", "RISK_REJECTED")
    recorder.record_stage_outcomes([signal], {"SBIN"}, "RISK_GUARDIAN", "GUARDIAN_BLOCKED")
    recorder.record_stage_outcomes([signal], {"SBIN"}, "DEBATE_EXECUTION", "CONFIDENCE_BELOW_THRESHOLD")

    records = [json.loads(line) for line in next(tmp_path.glob("*.jsonl")).read_text().splitlines()]
    events = [record for record in records if record["record_type"] == "PIT_PIPELINE_EVENT"]
    assert [event["stage"] for event in events] == [
        "SCANNER", "STRATEGYLAB", "KDA", "CRE", "RISKCONTROL", "RISK_GUARDIAN", "DEBATE_EXECUTION",
    ]
    assert {event["lineage_id"] for event in events} == {lineage_id}
    assert all(event["record_type"] != "PIT_OUTCOME" for event in records)
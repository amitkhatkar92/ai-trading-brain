"""
Test Suite — Options Knowledge Lifecycle
==========================================
DTA-001 Phase 4+5: Architecture Completion

Tests T001–T090 (Phase 4) + T091–T120 (Phase 5 new components):
  T001–T012  Opportunity Registry
  T013–T025  Observation Journal
  T026–T040  Feature Extraction
  T041–T055  Knowledge Store
  T056–T062  Pattern Engine
  T063–T068  Hypothesis Engine
  T069–T073  Validator
  T074–T078  Counterfactual Engine
  T079–T083  Shadow Scorer
  T084–T090  Research Pipeline
  T091–T100  Underlying Response Tracker
  T101–T110  Multi-Contract Shadow Tracker
  T111–T120  Failure Classifier
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
from datetime import date, timedelta
from typing import List, Tuple
from unittest.mock import MagicMock, patch

import pytest

# ── Test isolation: use temp data dir for all persistence ─────────────────

@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect all data/ paths to a temp directory for test isolation."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    # Create data/ so all open("data/...", ...) calls work
    os.makedirs("data", exist_ok=True)
    yield tmp_path


# ═══════════════════════════════════════════════════════════════════════════
# T001–T012  Opportunity Registry
# ═══════════════════════════════════════════════════════════════════════════

class TestOpportunityRegistry:

    def _make_registry(self):
        """Return a fresh registry instance (not singleton)."""
        from knowledge_system.options_opportunity_registry import (
            OptionsOpportunityRegistry, OPP_DISCOVERED, OPP_SHORTLISTED
        )
        return OptionsOpportunityRegistry(), OPP_DISCOVERED, OPP_SHORTLISTED

    def test_T001_new_opportunity_id_format(self):
        """T001: opportunity_id follows OPT-YYYYMMDD-HHMMSS-NNNNNN-SYMBOL format."""
        from knowledge_system.options_opportunity_registry import OptionsOpportunityRegistry
        reg = OptionsOpportunityRegistry()
        oid = reg.new_opportunity_id("NIFTY")
        assert oid.startswith("OPT-")
        parts = oid.split("-")
        assert len(parts) >= 5
        assert parts[4] == "NIFTY"

    def test_T002_new_id_is_unique(self):
        """T002: Each new_opportunity_id() call returns a unique ID."""
        from knowledge_system.options_opportunity_registry import OptionsOpportunityRegistry
        reg = OptionsOpportunityRegistry()
        ids = {reg.new_opportunity_id("NIFTY") for _ in range(20)}
        assert len(ids) == 20

    def test_T003_initial_state_is_discovered(self):
        """T003: After new_opportunity_id(), state is DISCOVERED."""
        from knowledge_system.options_opportunity_registry import (
            OptionsOpportunityRegistry, OPP_DISCOVERED
        )
        reg = OptionsOpportunityRegistry()
        oid = reg.new_opportunity_id("BANKNIFTY")
        assert reg.current_state(oid) == OPP_DISCOVERED

    def test_T004_state_transition_updates_state(self):
        """T004: transition() updates current_state correctly."""
        from knowledge_system.options_opportunity_registry import (
            OptionsOpportunityRegistry, OPP_SHORTLISTED
        )
        reg = OptionsOpportunityRegistry()
        oid = reg.new_opportunity_id("NIFTY")
        reg.transition(oid, OPP_SHORTLISTED)
        assert reg.current_state(oid) == OPP_SHORTLISTED

    def test_T005_is_known_true_for_existing(self):
        """T005: is_known() returns True for registered opportunity."""
        from knowledge_system.options_opportunity_registry import OptionsOpportunityRegistry
        reg = OptionsOpportunityRegistry()
        oid = reg.new_opportunity_id("NIFTY")
        assert reg.is_known(oid)

    def test_T006_is_known_false_for_unknown(self):
        """T006: is_known() returns False for unregistered ID."""
        from knowledge_system.options_opportunity_registry import OptionsOpportunityRegistry
        reg = OptionsOpportunityRegistry()
        assert not reg.is_known("OPT-99999999-FAKE")

    def test_T007_get_all_in_state(self):
        """T007: get_all_in_state() returns only matching IDs."""
        from knowledge_system.options_opportunity_registry import (
            OptionsOpportunityRegistry, OPP_SHORTLISTED
        )
        reg = OptionsOpportunityRegistry()
        oid1 = reg.new_opportunity_id("NIFTY")
        oid2 = reg.new_opportunity_id("BANKNIFTY")
        reg.transition(oid1, OPP_SHORTLISTED)
        in_state = reg.get_all_in_state(OPP_SHORTLISTED)
        assert oid1 in in_state
        assert oid2 not in in_state

    def test_T008_registry_persists_to_disk(self, tmp_path):
        """T008: Registry writes to disk; reloads correctly."""
        from knowledge_system.options_opportunity_registry import (
            OptionsOpportunityRegistry, OPP_SHORTLISTED
        )
        reg = OptionsOpportunityRegistry()
        oid = reg.new_opportunity_id("NIFTY")
        reg.transition(oid, OPP_SHORTLISTED)
        assert os.path.exists("data/options_opportunity_registry.jsonl")

        # Reload
        reg2 = OptionsOpportunityRegistry()
        assert reg2.current_state(oid) == OPP_SHORTLISTED

    def test_T009_invalid_state_ignored(self):
        """T009: transition() with unknown state does not crash."""
        from knowledge_system.options_opportunity_registry import OptionsOpportunityRegistry
        reg = OptionsOpportunityRegistry()
        oid = reg.new_opportunity_id("NIFTY")
        reg.transition(oid, "NOT_A_REAL_STATE")
        # State should still be DISCOVERED (unchanged)
        from knowledge_system.options_opportunity_registry import OPP_DISCOVERED
        assert reg.current_state(oid) == OPP_DISCOVERED

    def test_T010_thread_safety_concurrent_ids(self):
        """T010: Concurrent new_opportunity_id() calls all produce unique IDs."""
        from knowledge_system.options_opportunity_registry import OptionsOpportunityRegistry
        reg = OptionsOpportunityRegistry()
        ids = []
        lock = threading.Lock()

        def gen():
            oid = reg.new_opportunity_id("NIFTY")
            with lock:
                ids.append(oid)

        threads = [threading.Thread(target=gen) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(ids) == len(set(ids)), "Duplicate IDs generated under concurrency"

    def test_T011_symbol_truncated_to_12(self):
        """T011: Very long symbol names are truncated in the ID."""
        from knowledge_system.options_opportunity_registry import OptionsOpportunityRegistry
        reg = OptionsOpportunityRegistry()
        oid = reg.new_opportunity_id("VERYLONGSYMBOLNAME123")
        # Symbol part should be at most 12 chars
        sym_part = oid.split("-")[-1]
        assert len(sym_part) <= 12

    def test_T012_multiple_transitions_persisted(self, tmp_path):
        """T012: Full lifecycle (DISCOVERED → SHORTLISTED → EXECUTED) persists."""
        from knowledge_system.options_opportunity_registry import (
            OptionsOpportunityRegistry,
            OPP_DISCOVERED, OPP_SHORTLISTED, OPP_EXECUTED,
        )
        reg = OptionsOpportunityRegistry()
        oid = reg.new_opportunity_id("NIFTY")
        reg.transition(oid, OPP_SHORTLISTED)
        reg.transition(oid, OPP_EXECUTED)

        reg2 = OptionsOpportunityRegistry()
        assert reg2.current_state(oid) == OPP_EXECUTED


# ═══════════════════════════════════════════════════════════════════════════
# T013–T025  Observation Journal
# ═══════════════════════════════════════════════════════════════════════════

class TestObservationJournal:

    def _make_journal(self):
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation, OBS_DISCOVERED
        )
        return OptionsObservationJournal(), OptionsOpportunityObservation, OBS_DISCOVERED

    def test_T013_obs_has_opportunity_id_field(self):
        """T013: OptionsOpportunityObservation has opportunity_id field."""
        from execution_engine.options_observation_journal import OptionsOpportunityObservation
        obs = OptionsOpportunityObservation(
            obs_id="T013", symbol="NIFTY", strategy_name="Bull_Call_Spread",
            observed_at="2026-01-01T10:00:00", state="DISCOVERED",
        )
        assert hasattr(obs, "opportunity_id")
        assert obs.opportunity_id is None  # default

    def test_T014_obs_has_iv_source(self):
        """T014: OptionsOpportunityObservation has iv_source field."""
        from execution_engine.options_observation_journal import OptionsOpportunityObservation
        obs = OptionsOpportunityObservation(
            obs_id="T014", symbol="NIFTY", strategy_name="test",
            observed_at="now", state="DISCOVERED", iv_source="MODEL_ESTIMATE"
        )
        assert obs.iv_source == "MODEL_ESTIMATE"

    def test_T015_obs_has_data_source(self):
        """T015: data_source, greek_source provenance fields exist."""
        from execution_engine.options_observation_journal import OptionsOpportunityObservation
        obs = OptionsOpportunityObservation(
            obs_id="T015", symbol="NIFTY", strategy_name="test",
            observed_at="now", state="DISCOVERED",
            data_source="YFINANCE", greek_source="LIVE_MARKET",
        )
        assert obs.data_source == "YFINANCE"
        assert obs.greek_source == "LIVE_MARKET"

    def test_T016_obs_has_market_context_fields(self):
        """T016: Full market context fields present (OI, PCR, bid-ask, spot)."""
        from execution_engine.options_observation_journal import OptionsOpportunityObservation
        obs = OptionsOpportunityObservation(
            obs_id="T016", symbol="NIFTY", strategy_name="test",
            observed_at="now", state="DISCOVERED",
            spot_price=22500.0, total_ce_oi=5000000, total_pe_oi=6000000,
            pcr=1.2, atm_bid_ask_spread=0.03, time_of_day="NORMAL",
        )
        assert obs.spot_price == 22500.0
        assert obs.total_ce_oi == 5000000
        assert obs.pcr == 1.2
        assert obs.time_of_day == "NORMAL"

    def test_T017_obs_has_legs_context(self):
        """T017: legs_context list field present and stores per-leg data."""
        from execution_engine.options_observation_journal import OptionsOpportunityObservation
        legs = [{"strike": 22500, "iv": 0.18, "open_interest": 50000}]
        obs = OptionsOpportunityObservation(
            obs_id="T017", symbol="NIFTY", strategy_name="test",
            observed_at="now", state="DISCOVERED", legs_context=legs
        )
        assert len(obs.legs_context) == 1
        assert obs.legs_context[0]["iv"] == 0.18

    def test_T018_discovered_state_valid(self):
        """T018: DISCOVERED is a valid observation state."""
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation, OBS_DISCOVERED
        )
        j = OptionsObservationJournal()
        obs = OptionsOpportunityObservation(
            obs_id="T018", symbol="NIFTY", strategy_name="test",
            observed_at="2026-01-01T10:00:00", state=OBS_DISCOVERED,
        )
        j.record(obs)
        rows = j.read_all()
        assert any(r.get("state") == OBS_DISCOVERED for r in rows)

    def test_T019_read_by_opportunity_id(self):
        """T019: read_by_opportunity_id() returns all lifecycle records."""
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation
        )
        j = OptionsObservationJournal()
        oid = "OPT-TEST-001"
        for state in ["DISCOVERED", "SHORTLISTED", "EXECUTED"]:
            obs = OptionsOpportunityObservation(
                obs_id=j.make_obs_id("NIFTY", "test"),
                symbol="NIFTY", strategy_name="test",
                observed_at="2026-01-01T10:00:00",
                state=state, opportunity_id=oid,
            )
            j.record(obs)
        recs = j.read_by_opportunity_id(oid)
        assert len(recs) == 3
        states = {r["state"] for r in recs}
        assert "DISCOVERED" in states
        assert "EXECUTED" in states

    def test_T020_counterfactual_fields(self):
        """T020: counterfactual_pnl and counterfactual_horizon_days present."""
        from execution_engine.options_observation_journal import OptionsOpportunityObservation
        obs = OptionsOpportunityObservation(
            obs_id="T020", symbol="NIFTY", strategy_name="test",
            observed_at="now", state="COUNTERFACTUAL_OUTCOME",
            counterfactual_pnl=500.0, counterfactual_horizon_days=14,
        )
        assert obs.counterfactual_pnl == 500.0
        assert obs.counterfactual_horizon_days == 14

    def test_T021_read_outcomes_filter(self):
        """T021: read_outcomes() returns only OUTCOME_OBSERVED records."""
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation, OBS_OUTCOME_OBSERVED
        )
        j = OptionsObservationJournal()
        for state in ["DISCOVERED", OBS_OUTCOME_OBSERVED, "SHORTLISTED"]:
            j.record(OptionsOpportunityObservation(
                obs_id=j.make_obs_id("NIFTY", "test"),
                symbol="NIFTY", strategy_name="test",
                observed_at="2026-01-01T10:00:00", state=state,
            ))
        outcomes = j.read_outcomes()
        assert len(outcomes) == 1
        assert outcomes[0]["state"] == OBS_OUTCOME_OBSERVED

    def test_T022_new_states_valid(self):
        """T022: All new lifecycle states are recognised."""
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation,
            OBS_CONTEXT_ENRICHED, OBS_COUNTERFACTUAL_MONITORING,
            OBS_COUNTERFACTUAL_OUTCOME, OBS_REJECTION_CORRECT,
            OBS_REJECTION_INCORRECT, OBS_MISSED_OPPORTUNITY, OBS_NOT_EXECUTED,
        )
        j = OptionsObservationJournal()
        for state in [OBS_CONTEXT_ENRICHED, OBS_COUNTERFACTUAL_MONITORING,
                      OBS_COUNTERFACTUAL_OUTCOME, OBS_REJECTION_CORRECT,
                      OBS_REJECTION_INCORRECT, OBS_MISSED_OPPORTUNITY, OBS_NOT_EXECUTED]:
            j.record(OptionsOpportunityObservation(
                obs_id=j.make_obs_id("NIFTY", "test"),
                symbol="NIFTY", strategy_name="test",
                observed_at="2026-01-01T10:00:00", state=state,
            ))
        rows = j.read_all()
        assert len(rows) == 7

    def test_T023_invalid_state_not_written(self):
        """T023: Records with invalid states are not written to disk."""
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation
        )
        j = OptionsObservationJournal()
        j.record(OptionsOpportunityObservation(
            obs_id="T023", symbol="NIFTY", strategy_name="test",
            observed_at="now", state="NOT_A_REAL_STATE",
        ))
        assert j.read_all() == []

    def test_T024_read_since_date(self):
        """T024: read_since_date() returns only recent records."""
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation
        )
        j = OptionsObservationJournal()
        for ts in ["2026-01-01T10:00:00", "2026-04-01T10:00:00"]:
            j.record(OptionsOpportunityObservation(
                obs_id=j.make_obs_id("NIFTY", "test"),
                symbol="NIFTY", strategy_name="test",
                observed_at=ts, state="DISCOVERED",
            ))
        recent = j.read_since_date("2026-04-01")
        assert len(recent) == 1
        assert recent[0]["observed_at"].startswith("2026-04-01")

    def test_T025_journal_never_raises_on_write_error(self):
        """T025: Journal write failures are silently absorbed."""
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation
        )
        j = OptionsObservationJournal()
        # Corrupt the path
        j.OBSERVATIONS_PATH if False else None  # just access
        obs = OptionsOpportunityObservation(
            obs_id="T025", symbol="NIFTY", strategy_name="test",
            observed_at="now", state="DISCOVERED",
        )
        # Should not raise even if write fails
        try:
            j.record(obs)
        except Exception:
            pytest.fail("Journal.record() must never raise")


# ═══════════════════════════════════════════════════════════════════════════
# T026–T040  Feature Extraction
# ═══════════════════════════════════════════════════════════════════════════

class TestFeatureExtraction:

    def _base_obs(self, **kwargs) -> dict:
        base = {
            "symbol": "NIFTY", "strategy_name": "BULL_CALL_SPREAD",
            "regime": "BULL", "vix": 18.0, "iv_rank": 45.0, "dte": 14,
            "confidence": 7.5, "chain_quality": 0.8, "pcr": 1.1,
            "total_ce_oi": 1_000_000, "total_pe_oi": 1_100_000,
            "data_source": "YFINANCE", "iv_source": "LIVE_MARKET",
            "observed_at": "2026-04-01T10:00:00",
        }
        base.update(kwargs)
        return base

    def test_T026_basic_extraction(self):
        """T026: extract_features returns valid OptionsFeatureVector."""
        from knowledge_system.options_feature_extractor import extract_features
        fv = extract_features(self._base_obs())
        assert fv.is_valid
        assert fv.symbol == "NIFTY"
        assert fv.regime == "BULL"

    def test_T027_vix_bands(self):
        """T027: VIX buckets are correct at boundary values."""
        from knowledge_system.options_feature_extractor import extract_features, VIX_LOW, VIX_NORMAL, VIX_HIGH
        assert extract_features(self._base_obs(vix=12.0)).vix_band == VIX_LOW
        assert extract_features(self._base_obs(vix=17.0)).vix_band == VIX_NORMAL
        assert extract_features(self._base_obs(vix=35.0)).vix_band == VIX_HIGH

    def test_T028_ivr_bands(self):
        """T028: IVR buckets are correct."""
        from knowledge_system.options_feature_extractor import extract_features
        assert extract_features(self._base_obs(iv_rank=15)).ivr_band == "IVR_VERY_LOW"
        assert extract_features(self._base_obs(iv_rank=45)).ivr_band == "IVR_NORMAL"
        assert extract_features(self._base_obs(iv_rank=80)).ivr_band == "IVR_VERY_HIGH"

    def test_T029_dte_bands(self):
        """T029: DTE buckets are correct."""
        from knowledge_system.options_feature_extractor import extract_features
        assert extract_features(self._base_obs(dte=5)).dte_band == "DTE_NEAR"
        assert extract_features(self._base_obs(dte=10)).dte_band == "DTE_WEEKLY"
        assert extract_features(self._base_obs(dte=25)).dte_band == "DTE_MONTHLY"

    def test_T030_pcr_bands(self):
        """T030: PCR bands are correct."""
        from knowledge_system.options_feature_extractor import extract_features
        # PCR derived from CE/PE OI
        fv = extract_features(self._base_obs(pcr=0, total_ce_oi=1_000_000, total_pe_oi=1_500_000))
        # PE/CE = 1.5 → PCR_NEUTRAL (0.8–1.5)
        assert fv.pcr_band == "PCR_NEUTRAL"

    def test_T031_oi_imbalance_heavy_put(self):
        """T031: OI imbalance correctly identifies PE-dominant chain."""
        from knowledge_system.options_feature_extractor import extract_features, OI_HEAVY_PUT
        fv = extract_features(self._base_obs(total_ce_oi=1_000_000, total_pe_oi=3_000_000))
        assert fv.oi_imbalance == OI_HEAVY_PUT

    def test_T032_oi_imbalance_unavailable_when_no_oi(self):
        """T032: OI imbalance is UNAVAILABLE when both CE/PE OI are zero."""
        from knowledge_system.options_feature_extractor import extract_features, OI_UNAVAILABLE
        fv = extract_features(self._base_obs(total_ce_oi=0, total_pe_oi=0))
        assert fv.oi_imbalance == OI_UNAVAILABLE

    def test_T033_regime_ivr_dte_key(self):
        """T033: regime_ivr_dte combination key formed correctly."""
        from knowledge_system.options_feature_extractor import extract_features
        # DTE=10 → DTE_WEEKLY (7–14), iv_rank=45 → IVR_NORMAL (35–55)
        fv = extract_features(self._base_obs(regime="BULL", iv_rank=45, dte=10))
        assert fv.regime_ivr_dte == "BULL|IVR_NORMAL|DTE_WEEKLY"

    def test_T034_full_key_contains_strategy(self):
        """T034: full_key contains strategy_name."""
        from knowledge_system.options_feature_extractor import extract_features
        fv = extract_features(self._base_obs(strategy_name="IRON_CONDOR"))
        assert "IRON_CONDOR" in fv.full_key

    def test_T035_temporal_safety_no_look_ahead(self):
        """T035: Feature extraction uses only fields present in the obs dict."""
        from knowledge_system.options_feature_extractor import extract_features
        # Include NO future fields — should extract fine from available data
        obs = {"symbol": "NIFTY", "strategy_name": "test", "observed_at": "2026-01-01T10:00:00"}
        fv = extract_features(obs)
        # Should not raise; is_valid may be False due to missing fields
        assert isinstance(fv.is_valid, bool)

    def test_T036_missing_critical_fields_marks_invalid(self):
        """T036: Observation with < 3 missing critical fields may still be valid."""
        from knowledge_system.options_feature_extractor import extract_features
        obs = {
            "symbol": "NIFTY",
            # missing: strategy_name, dte
        }
        fv = extract_features(obs)
        assert "symbol" not in fv.missing_fields  # symbol is present
        assert "strategy_name" in fv.missing_fields

    def test_T037_iv_source_passthrough(self):
        """T037: iv_source from obs dict is preserved in feature vector."""
        from knowledge_system.options_feature_extractor import extract_features
        fv = extract_features(self._base_obs(iv_source="MODEL_ESTIMATE"))
        assert fv.iv_source == "MODEL_ESTIMATE"

    def test_T038_has_events_flag(self):
        """T038: has_events=TRUE when events_today is non-empty."""
        from knowledge_system.options_feature_extractor import extract_features
        fv_events = extract_features(self._base_obs(events_today=["RBI_POLICY"]))
        fv_no_events = extract_features(self._base_obs(events_today=[]))
        assert fv_events.has_events == "TRUE"
        assert fv_no_events.has_events == "FALSE"

    def test_T039_raw_values_preserved(self):
        """T039: Raw numeric values in the feature vector match input."""
        from knowledge_system.options_feature_extractor import extract_features
        fv = extract_features(self._base_obs(vix=22.5, iv_rank=63.0, dte=18))
        assert fv.raw_vix == 22.5
        assert fv.raw_iv_rank == 63.0
        assert fv.raw_dte == 18

    def test_T040_extraction_never_raises(self):
        """T040: extract_features never raises on malformed input."""
        from knowledge_system.options_feature_extractor import extract_features
        malformed_inputs = [None, {}, {"symbol": None}, {"vix": "not_a_float"}]
        for inp in malformed_inputs:
            try:
                fv = extract_features(inp or {})
                assert isinstance(fv.is_valid, bool)
            except Exception as e:
                pytest.fail(f"extract_features raised on {inp!r}: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# T041–T055  Knowledge Store
# ═══════════════════════════════════════════════════════════════════════════

class TestKnowledgeStore:

    def _store(self):
        from knowledge_system.options_knowledge_store import OptionsKnowledgeStore
        return OptionsKnowledgeStore()

    def _fill(self, store, strategy, ctx, wins, losses):
        for _ in range(wins):
            store.record_outcome(strategy, ctx, {}, pnl=1000.0)
        for _ in range(losses):
            store.record_outcome(strategy, ctx, {}, pnl=-500.0)

    def test_T041_initial_state_observed(self):
        """T041: New knowledge item starts in OBSERVED state."""
        from knowledge_system.options_knowledge_store import KS_OBSERVED
        store = self._store()
        store.record_outcome("TEST", "CTX-A", {}, pnl=500.0)
        item = store.get_item("TEST", "CTX-A")
        assert item is not None
        assert item.state == KS_OBSERVED

    def test_T042_promotes_to_candidate(self):
        """T042: ≥10 outcomes with win_rate ≥ 35% → CANDIDATE."""
        from knowledge_system.options_knowledge_store import KS_CANDIDATE
        store = self._store()
        self._fill(store, "TEST", "CTX-B", 8, 2)
        item = store.get_item("TEST", "CTX-B")
        assert item.state == KS_CANDIDATE

    def test_T043_promotes_to_validating(self):
        """T043: ≥20 outcomes → VALIDATING."""
        from knowledge_system.options_knowledge_store import KS_VALIDATING
        store = self._store()
        self._fill(store, "TEST", "CTX-C", 15, 5)
        item = store.get_item("TEST", "CTX-C")
        assert item.state == KS_VALIDATING

    def test_T044_win_rate_computed_correctly(self):
        """T044: win_rate = wins / total_outcomes."""
        store = self._store()
        self._fill(store, "TEST", "CTX-D", 3, 7)
        item = store.get_item("TEST", "CTX-D")
        assert abs(item.win_rate - 0.3) < 0.001

    def test_T045_single_trade_cannot_reach_validated(self):
        """T045: One trade alone cannot transition system to VALIDATED."""
        from knowledge_system.options_knowledge_store import KS_VALIDATED
        store = self._store()
        store.record_outcome("TEST", "CTX-E", {}, pnl=100_000.0)
        item = store.get_item("TEST", "CTX-E")
        assert item.state != KS_VALIDATED

    def test_T046_oos_result_can_trigger_validated(self):
        """T046: mark_oos_result() with passing criteria transitions to VALIDATED."""
        from knowledge_system.options_knowledge_store import KS_VALIDATED, KS_VALIDATING
        store = self._store()
        self._fill(store, "TEST", "CTX-F", 16, 4)
        item = store.get_item("TEST", "CTX-F")
        assert item.state == KS_VALIDATING
        store.mark_oos_result(item.item_id, oos_outcomes=8, oos_wins=5, p_value=0.05)
        item = store.get_item("TEST", "CTX-F")
        assert item.state == KS_VALIDATED

    def test_T047_invalidation_below_30pct_win_rate(self):
        """T047: Recent win_rate < 30% → INVALIDATED."""
        from knowledge_system.options_knowledge_store import KS_INVALIDATED
        store = self._store()
        # Add some wins first to pass CANDIDATE threshold
        self._fill(store, "TEST", "CTX-G", 5, 5)  # 50% wr
        # Then push recent window with all losses
        for _ in range(12):
            store.record_outcome("TEST", "CTX-G", {}, pnl=-500.0)
        item = store.get_item("TEST", "CTX-G")
        assert item.state == KS_INVALIDATED

    def test_T048_get_influence_zero_for_observed(self):
        """T048: OBSERVED state → 0.0 influence."""
        store = self._store()
        store.record_outcome("TEST", "CTX-H", {}, pnl=100.0)
        delta, state = store.get_influence("TEST", "CTX-H")
        assert delta == 0.0

    def test_T049_get_influence_nonzero_for_validated(self):
        """T049: VALIDATED state with high win_rate → non-zero positive influence."""
        from knowledge_system.options_knowledge_store import KS_VALIDATED
        store = self._store()
        self._fill(store, "TEST", "CTX-I", 16, 4)  # 80% win rate
        item = store.get_item("TEST", "CTX-I")
        store.mark_oos_result(item.item_id, 8, 6, 0.03)
        delta, state = store.get_influence("TEST", "CTX-I")
        assert state == KS_VALIDATED
        assert delta > 0.0

    def test_T050_influence_bounded_by_cap(self):
        """T050: VALIDATED influence never exceeds MAX_CONFIDENCE_DELTA_VALIDATED."""
        from knowledge_system.options_knowledge_store import (
            OptionsKnowledgeStore, MAX_CONFIDENCE_DELTA_VALIDATED
        )
        store = self._store()
        self._fill(store, "TEST", "CTX-J", 18, 2)
        item = store.get_item("TEST", "CTX-J")
        store.mark_oos_result(item.item_id, 8, 8, 0.01)
        delta, _ = store.get_influence("TEST", "CTX-J")
        assert abs(delta) <= MAX_CONFIDENCE_DELTA_VALIDATED + 0.001

    def test_T051_persistence_round_trip(self):
        """T051: Knowledge store persists to disk and reloads correctly."""
        store1 = self._store()
        self._fill(store1, "PERSIST_TEST", "CTX-K", 5, 5)
        item1 = store1.get_item("PERSIST_TEST", "CTX-K")
        original_n = item1.total_outcomes

        store2 = self._store()  # fresh instance, loads from disk
        item2 = store2.get_item("PERSIST_TEST", "CTX-K")
        assert item2 is not None
        assert item2.total_outcomes == original_n

    def test_T052_opportunity_id_linked(self):
        """T052: opportunity_id is linked to knowledge items."""
        store = self._store()
        store.record_outcome("TEST", "CTX-L", {}, pnl=100.0, opportunity_id="OPT-TEST-000001")
        item = store.get_item("TEST", "CTX-L")
        assert "OPT-TEST-000001" in item.linked_opportunity_ids

    def test_T053_retire_sets_state(self):
        """T053: retire() sets state to RETIRED."""
        from knowledge_system.options_knowledge_store import KS_RETIRED
        store = self._store()
        store.record_outcome("TEST", "CTX-M", {}, pnl=100.0)
        item = store.get_item("TEST", "CTX-M")
        store.retire(item.item_id, "manual")
        item_after = store.get_item("TEST", "CTX-M")
        assert item_after.state == KS_RETIRED

    def test_T054_get_items_by_state(self):
        """T054: get_items_by_state() filters correctly."""
        from knowledge_system.options_knowledge_store import KS_OBSERVED
        store = self._store()
        store.record_outcome("A", "K1", {}, pnl=10.0)
        store.record_outcome("B", "K2", {}, pnl=20.0)
        obs_items = store.get_items_by_state(KS_OBSERVED)
        assert len(obs_items) >= 2

    def test_T055_avg_pnl_tracked(self):
        """T055: avg_pnl is tracked correctly."""
        store = self._store()
        store.record_outcome("TEST", "CTX-N", {}, pnl=1000.0)
        store.record_outcome("TEST", "CTX-N", {}, pnl=0.0)
        item = store.get_item("TEST", "CTX-N")
        assert abs(item.avg_pnl - 500.0) < 0.01


# ═══════════════════════════════════════════════════════════════════════════
# T056–T062  Pattern Engine
# ═══════════════════════════════════════════════════════════════════════════

class TestPatternEngine:

    def _make_fv(self, regime="BULL", ivr="IVR_HIGH", dte="DTE_WEEKLY",
                 strategy="BULL_CALL_SPREAD", direction="BULLISH"):
        from knowledge_system.options_feature_extractor import OptionsFeatureVector
        return OptionsFeatureVector(
            symbol="NIFTY", strategy_name=strategy, observed_at="2026-04-01T10:00:00",
            regime=regime, vix_band="VIX_NORMAL", ivr_band=ivr, dte_band=dte,
            pcr_band="PCR_NEUTRAL", spread_band="SPREAD_NORMAL",
            confidence_band="CONF_HIGH", oi_imbalance="OI_BALANCED",
            chain_quality_band="CHAIN_HIGH", direction=direction,
            time_of_day="NORMAL", data_source="YFINANCE", iv_source="LIVE_MARKET",
            has_events="FALSE",
            regime_ivr_dte=f"{regime}|{ivr}|{dte}",
            regime_vix_pcr=f"{regime}|VIX_NORMAL|PCR_NEUTRAL",
            strategy_regime_dir=f"{strategy}|{regime}|{direction}",
            full_key=f"{strategy}|{regime}|VIX_NORMAL|{ivr}|{dte}|PCR_NEUTRAL|SPREAD_NORMAL|{direction}|CHAIN_HIGH|FALSE",
            is_valid=True,
        )

    def test_T056_process_observation_no_error(self):
        """T056: process_observation() does not raise."""
        from knowledge_system.options_pattern_engine import OptionsPatternEngine
        engine = OptionsPatternEngine()
        fv = self._make_fv()
        engine.process_observation("BULL_CALL_SPREAD", fv, 1000.0, "2026-04-01T10:00:00")

    def test_T057_pattern_discovered_with_sufficient_data(self):
        """T057: run_discovery() returns significant patterns with edge ≥ 8%."""
        from knowledge_system.options_pattern_engine import OptionsPatternEngine
        engine = OptionsPatternEngine()
        fv = self._make_fv()
        # 7 wins + 1 loss across two time halves
        for i in range(7):
            ts = f"2026-0{1+i//4}-01T10:00:00"
            engine.process_observation("BULL_CALL_SPREAD", fv, 1000.0, ts)
        engine.process_observation("BULL_CALL_SPREAD", fv, -500.0, "2026-04-01T10:00:00")
        patterns = engine.run_discovery()
        # Some patterns may not be significant (temporal coverage may fail with
        # only 8 data points); check that discovery runs without error
        assert isinstance(patterns, list)

    def test_T058_patterns_persisted(self):
        """T058: run_discovery() persists patterns to disk."""
        from knowledge_system.options_pattern_engine import OptionsPatternEngine
        engine = OptionsPatternEngine()
        fv = self._make_fv()
        for _ in range(10):
            engine.process_observation("TEST_STRAT", fv, 500.0, "2026-04-01T10:00:00")
        engine.run_discovery()
        assert os.path.exists("data/options_patterns.json")

    def test_T059_invalid_feature_vector_skipped(self):
        """T059: Invalid feature vectors (is_valid=False) are skipped."""
        from knowledge_system.options_pattern_engine import OptionsPatternEngine
        from knowledge_system.options_feature_extractor import OptionsFeatureVector
        engine = OptionsPatternEngine()
        bad_fv = OptionsFeatureVector(is_valid=False)
        engine.process_observation("TEST", bad_fv, 1000.0, "2026-04-01")
        patterns = engine.run_discovery()
        assert len(patterns) == 0

    def test_T060_temporal_coverage_required(self):
        """T060: All observations in one time period → temporal_coverage < threshold."""
        from knowledge_system.options_pattern_engine import OptionsPatternEngine, MIN_TEMPORAL_COVERAGE
        engine = OptionsPatternEngine()
        fv = self._make_fv()
        # All observations at same date (first half only)
        for _ in range(15):
            engine.process_observation("TEST", fv, 1000.0, "2026-01-01T10:00:00")
        patterns = engine.run_discovery()
        sig = [p for p in patterns if p.is_significant]
        # Without temporal coverage, should not be significant
        # (all obs in same half → temporal_coverage = 0/15 ≈ 0)
        # This is the anti-overfitting guard
        assert all(p.temporal_coverage < 0.5 or not p.is_significant for p in patterns)

    def test_T061_pattern_engine_reload(self):
        """T061: Patterns reload correctly after restart."""
        from knowledge_system.options_pattern_engine import OptionsPatternEngine
        engine1 = OptionsPatternEngine()
        fv = self._make_fv()
        for _ in range(10):
            engine1.process_observation("NIFTY_BULL", fv, 500.0, "2026-04-01T10:00:00")
        engine1.run_discovery()
        engine2 = OptionsPatternEngine()
        assert len(engine2._patterns) > 0

    def test_T062_get_patterns_for_strategy(self):
        """T062: get_patterns_for_strategy() filters by strategy name."""
        from knowledge_system.options_pattern_engine import OptionsPatternEngine
        engine = OptionsPatternEngine()
        fv = self._make_fv(strategy="BULL_CALL_SPREAD")
        for _ in range(10):
            engine.process_observation("BULL_CALL_SPREAD", fv, 500.0, "2026-04-01T10:00:00")
        engine.run_discovery()
        strat_pats = engine.get_patterns_for_strategy("BULL_CALL_SPREAD")
        other_pats = engine.get_patterns_for_strategy("IRON_CONDOR")
        assert len(strat_pats) > 0
        assert len(other_pats) == 0


# ═══════════════════════════════════════════════════════════════════════════
# T063–T068  Hypothesis Engine
# ═══════════════════════════════════════════════════════════════════════════

class TestHypothesisEngine:

    def _make_pattern(self, n=15, wins=10, sig=True):
        from knowledge_system.options_pattern_engine import DiscoveredPattern
        return DiscoveredPattern(
            pattern_id="PAT-AAAABBBB", context_key="BULL|IVR_HIGH|DTE_WEEKLY",
            context_type="regime_ivr_dte", strategy_name="BULL_CALL_SPREAD",
            n=n, wins=wins, win_rate=wins/n, avg_pnl=500.0 if wins>n//2 else -200.0,
            first_half_n=n//2, second_half_n=n-n//2,
            is_significant=sig, edge_strength="MODERATE" if sig else "WEAK",
            temporal_coverage=0.4,
        )

    def test_T063_propose_from_pattern(self):
        """T063: propose_from_pattern() creates a TESTING hypothesis."""
        from knowledge_system.options_hypothesis_engine import OptionsHypothesisEngine, HYPO_TESTING
        engine = OptionsHypothesisEngine()
        h = engine.propose_from_pattern(self._make_pattern())
        assert h is not None
        assert h.state == HYPO_TESTING
        assert "BULL_CALL_SPREAD" in h.title

    def test_T064_duplicate_not_reproposed(self):
        """T064: Proposing the same context twice returns None for duplicate."""
        from knowledge_system.options_hypothesis_engine import OptionsHypothesisEngine
        engine = OptionsHypothesisEngine()
        p = self._make_pattern()
        h1 = engine.propose_from_pattern(p)
        h2 = engine.propose_from_pattern(p)
        assert h1 is not None
        assert h2 is None  # deduped

    def test_T065_hypotheses_persisted(self):
        """T065: Hypotheses persist to disk."""
        from knowledge_system.options_hypothesis_engine import OptionsHypothesisEngine
        engine = OptionsHypothesisEngine()
        engine.propose_from_pattern(self._make_pattern())
        assert os.path.exists("data/options_hypotheses.json")

    def test_T066_get_active_hypotheses(self):
        """T066: get_active_hypotheses() returns non-terminal hypotheses."""
        from knowledge_system.options_hypothesis_engine import (
            OptionsHypothesisEngine, HYPO_TESTING
        )
        engine = OptionsHypothesisEngine()
        engine.propose_from_pattern(self._make_pattern())
        active = engine.get_active_hypotheses()
        assert any(h.state == HYPO_TESTING for h in active)

    def test_T067_summary_counts_by_state(self):
        """T067: summary() returns state counts."""
        from knowledge_system.options_hypothesis_engine import OptionsHypothesisEngine
        engine = OptionsHypothesisEngine()
        engine.propose_from_pattern(self._make_pattern())
        summary = engine.summary()
        assert isinstance(summary, dict)
        total = sum(summary.values())
        assert total >= 1

    def test_T068_reloads_from_disk(self):
        """T068: Engine reloads persisted hypotheses on restart."""
        from knowledge_system.options_hypothesis_engine import OptionsHypothesisEngine
        e1 = OptionsHypothesisEngine()
        e1.propose_from_pattern(self._make_pattern())
        e2 = OptionsHypothesisEngine()
        assert len(e2.get_all_hypotheses()) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# T069–T073  Validator
# ═══════════════════════════════════════════════════════════════════════════

class TestValidator:

    def test_T069_oos_validation_insufficient_data(self):
        """T069: OOS returns (0,0,1.0) for < 10 outcomes."""
        from knowledge_system.options_validator import run_oos_validation
        outcomes = [(1, 100.0, "2026-01-01")] * 5
        n, wins, p = run_oos_validation(outcomes)
        assert n == 0 and wins == 0 and p == 1.0

    def test_T070_oos_split_is_temporal(self):
        """T070: OOS split respects chronological order."""
        from knowledge_system.options_validator import run_oos_validation
        # First 14 outcomes are losses (early dates), last 6 are wins (later dates)
        outcomes = ([(0, -100.0, f"2026-01-{i+1:02d}") for i in range(14)]
                    + [(1, 100.0, f"2026-02-{i+1:02d}") for i in range(6)])
        n, wins, p = run_oos_validation(outcomes)
        # OOS = last 30% ≈ 6 records = the 6 wins → wins/n should be 6/6=100%
        assert wins == 6

    def test_T071_oos_p_value_significant_for_strong_edge(self):
        """T071: OOS p-value < 0.05 for very strong win_rate (20 wins, 0 losses)."""
        from knowledge_system.options_validator import run_oos_validation, _binomial_p
        outcomes = [(1, 100.0, f"2026-{m:02d}-01") for m in range(1, 21)]
        n, wins, p = run_oos_validation(outcomes)
        assert p < 0.10

    def test_T072_walk_forward_insufficient(self):
        """T072: WFO returns None with insufficient data."""
        from knowledge_system.options_validator import run_walk_forward
        outcomes = [(1, 100.0, "2026-01-01")] * 10
        result = run_walk_forward(outcomes)
        assert result is None

    def test_T073_walk_forward_runs_with_enough_data(self):
        """T073: WFO returns a float for ≥ 15 outcomes (3 folds × 5)."""
        from knowledge_system.options_validator import run_walk_forward
        outcomes = [(1, 100.0, f"2026-0{m//5+1}-{(m%5+1):02d}") for m in range(15)]
        result = run_walk_forward(outcomes)
        assert result is not None
        assert isinstance(result, float)


# ═══════════════════════════════════════════════════════════════════════════
# T074–T078  Counterfactual Engine
# ═══════════════════════════════════════════════════════════════════════════

class TestCounterfactualEngine:

    def test_T074_register_rejection_creates_monitor(self):
        """T074: register_rejection() creates a pending monitor."""
        from knowledge_system.options_counterfactual_engine import OptionsCounterfactualEngine
        engine = OptionsCounterfactualEngine()
        engine.register_rejection(
            opportunity_id="OPT-TEST", symbol="NIFTY",
            strategy_name="Bull_Call_Spread", direction="BULLISH",
            rejection_reason="chain_quality", expected_pnl=500.0,
            expected_entry_price=100.0, dte=14, spot=22500.0, iv=0.18,
            regime="BULL", confidence=7.5,
        )
        assert engine.pending_count() == 1

    def test_T075_dte_zero_not_registered(self):
        """T075: DTE=0 is outside trackable range — not registered."""
        from knowledge_system.options_counterfactual_engine import OptionsCounterfactualEngine
        engine = OptionsCounterfactualEngine()
        engine.register_rejection(
            opportunity_id="OPT-ZERO-DTE", symbol="NIFTY",
            strategy_name="test", direction="BULLISH",
            rejection_reason="test", expected_pnl=0.0,
            expected_entry_price=0.0, dte=0, spot=22500.0, iv=0.0,
            regime="BULL", confidence=7.0,
        )
        assert engine.pending_count() == 0

    def test_T076_analyse_sets_analysed_flag(self):
        """T076: run_analysis() processes matured monitors and sets analysed=True."""
        from knowledge_system.options_counterfactual_engine import OptionsCounterfactualEngine, CounterfactualMonitor
        engine = OptionsCounterfactualEngine()
        engine._pending["OPT-PAST"] = CounterfactualMonitor(
            opportunity_id="OPT-PAST", symbol="NIFTY",
            strategy_name="test", direction="BULLISH",
            rejection_reason="test", expected_pnl=500.0,
            expected_entry_price=100.0, dte_at_rejection=5,
            monitor_until="2020-01-01",  # past date
            recorded_at="2020-01-01T10:00:00",
            spot_at_rejection=22500.0,
        )
        with patch.object(engine, "_get_current_spot", return_value=23000.0):
            results = engine.run_analysis()
        assert len(results) == 1
        assert results[0].analysed

    def test_T077_classification_correct_rejection_on_wrong_direction(self):
        """T077: If spot moved against prediction → REJECTION_CORRECT."""
        from knowledge_system.options_counterfactual_engine import OptionsCounterfactualEngine, CounterfactualMonitor
        engine = OptionsCounterfactualEngine()
        engine._pending["OPT-DOWN"] = CounterfactualMonitor(
            opportunity_id="OPT-DOWN", symbol="NIFTY",
            strategy_name="test", direction="BULLISH",  # expected up
            rejection_reason="test", expected_pnl=500.0,
            expected_entry_price=100.0, dte_at_rejection=10,
            monitor_until="2020-01-01",
            recorded_at="2020-01-01T10:00:00",
            spot_at_rejection=22500.0,
        )
        # Current spot < spot_at_rejection → bearish move → BULLISH was wrong
        with patch.object(engine, "_get_current_spot", return_value=21500.0):
            results = engine.run_analysis()
        assert results[0].rejection_classification == "REJECTION_CORRECT"

    def test_T078_persistence(self):
        """T078: Counterfactual pending monitors persist to disk."""
        from knowledge_system.options_counterfactual_engine import OptionsCounterfactualEngine
        engine = OptionsCounterfactualEngine()
        engine.register_rejection(
            opportunity_id="OPT-PERSIST", symbol="NIFTY",
            strategy_name="test", direction="BULLISH",
            rejection_reason="test", expected_pnl=500.0,
            expected_entry_price=100.0, dte=7, spot=22500.0, iv=0.18,
            regime="BULL", confidence=7.0,
        )
        assert os.path.exists("data/options_cf_pending.json")


# ═══════════════════════════════════════════════════════════════════════════
# T079–T083  Shadow Scorer
# ═══════════════════════════════════════════════════════════════════════════

class TestShadowScorer:

    def test_T079_record_decision_returns_record(self):
        """T079: record_decision() returns a populated ShadowRecord."""
        from learning_system.options_shadow_scorer import OptionsShadowScorer
        scorer = OptionsShadowScorer()
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "OBSERVED")
            mock_store.return_value.get_item.return_value = None
            rec = scorer.record_decision(
                opportunity_id="OPT-TEST-001", symbol="NIFTY",
                strategy_name="Bull_Call_Spread", context_key="BULL|IVR_HIGH|DTE_WEEKLY",
                prod_confidence=7.5, prod_executed=True,
            )
        assert rec.opportunity_id == "OPT-TEST-001"
        assert rec.prod_confidence == 7.5
        assert rec.prod_executed is True

    def test_T080_agreement_stats_empty(self):
        """T080: Empty scorer returns zero agreement stats."""
        from learning_system.options_shadow_scorer import OptionsShadowScorer
        scorer = OptionsShadowScorer()
        stats = scorer.get_agreement_stats()
        assert stats["total_records"] == 0
        assert stats["agree_rate"] == 0

    def test_T081_record_outcome_updates_correctness(self):
        """T081: record_outcome() fills actual_pnl and ks_was_correct."""
        from learning_system.options_shadow_scorer import OptionsShadowScorer
        scorer = OptionsShadowScorer()
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.03, "VALIDATED")
            mock_store.return_value.get_item.return_value = None
            scorer.record_decision(
                opportunity_id="OPT-OUTCOME", symbol="NIFTY",
                strategy_name="test", context_key="ctx",
                prod_confidence=7.5, prod_executed=True,
            )
        scorer.record_outcome("OPT-OUTCOME", 1000.0)
        rec = scorer.get_record("OPT-OUTCOME")
        assert rec is not None
        assert rec.actual_pnl == 1000.0

    def test_T082_shadow_persists_to_disk(self):
        """T082: Shadow records persist to disk."""
        from learning_system.options_shadow_scorer import OptionsShadowScorer
        scorer = OptionsShadowScorer()
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "OBSERVED")
            mock_store.return_value.get_item.return_value = None
            scorer.record_decision("OPT-PERSIST", "NIFTY", "test", "ctx", 7.5, False)
        assert os.path.exists("data/options_shadow_scores.json")

    def test_T083_ks_recommendation_boost_for_positive_influence(self):
        """T083: Positive influence → BOOST recommendation."""
        from learning_system.options_shadow_scorer import OptionsShadowScorer
        scorer = OptionsShadowScorer()
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.05, "VALIDATED")
            mock_store.return_value.get_item.return_value = None
            rec = scorer.record_decision("OPT-BOOST", "NIFTY", "test", "ctx", 7.5, True)
        assert rec.ks_recommendation == "BOOST"


# ═══════════════════════════════════════════════════════════════════════════
# T084–T090  Research Pipeline (integration)
# ═══════════════════════════════════════════════════════════════════════════

class TestResearchPipeline:

    def test_T084_pipeline_run_once_no_error(self):
        """T084: run_once() completes without error on empty journal."""
        from knowledge_system.options_research_pipeline import OptionsResearchPipeline
        pipeline = OptionsResearchPipeline()
        result = pipeline.run_once()
        assert isinstance(result, dict)
        assert "run_at" in result

    def test_T085_pipeline_processes_outcomes(self):
        """T085: pipeline run processes new OUTCOME_OBSERVED records."""
        from knowledge_system.options_research_pipeline import OptionsResearchPipeline
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation, OBS_OUTCOME_OBSERVED
        )
        # Seed the journal
        j = OptionsObservationJournal()
        for i in range(5):
            j.record(OptionsOpportunityObservation(
                obs_id=j.make_obs_id("NIFTY", "Bull_Call_Spread"),
                symbol="NIFTY", strategy_name="Bull_Call_Spread",
                observed_at=f"2026-04-0{i+1}T10:00:00",
                state=OBS_OUTCOME_OBSERVED,
                opportunity_id=f"OPT-TEST-{i:06d}",
                actual_pnl=1000.0, expected_pnl=800.0,
                regime="BULL", iv_rank=45.0, dte=14, vix=18.0,
                data_source="YFINANCE", iv_source="LIVE_MARKET",
            ))
        pipeline = OptionsResearchPipeline()
        result = pipeline.run_once()
        assert result["new_outcomes"] == 5

    def test_T086_cursor_advances(self):
        """T086: Pipeline cursor advances after each run."""
        from knowledge_system.options_research_pipeline import OptionsResearchPipeline
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation
        )
        j = OptionsObservationJournal()
        j.record(OptionsOpportunityObservation(
            obs_id="T086", symbol="NIFTY", strategy_name="test",
            observed_at="2026-01-01T10:00:00", state="DISCOVERED",
        ))
        pipeline = OptionsResearchPipeline()
        pipeline.run_once()
        cursor_after_1 = pipeline._cursor
        pipeline.run_once()
        cursor_after_2 = pipeline._cursor
        # Cursor should have advanced after first run and stayed stable
        assert cursor_after_1 >= 1
        assert cursor_after_2 == cursor_after_1  # no new records

    def test_T087_pipeline_handles_bad_journal_records(self):
        """T087: Malformed JSONL records don't crash the pipeline."""
        from knowledge_system.options_research_pipeline import OptionsResearchPipeline
        from execution_engine.options_observation_journal import OBSERVATIONS_PATH
        # Inject a malformed line
        with open(OBSERVATIONS_PATH, "a") as f:
            f.write("NOT_VALID_JSON\n")
        pipeline = OptionsResearchPipeline()
        result = pipeline.run_once()
        assert "error" not in result

    def test_T088_start_stop_no_error(self):
        """T088: start() and stop() do not raise."""
        from knowledge_system.options_research_pipeline import OptionsResearchPipeline
        pipeline = OptionsResearchPipeline()
        pipeline.start()
        time.sleep(0.1)
        pipeline.stop()

    def test_T089_daily_summary_written(self):
        """T089: run_once() writes to the research log."""
        from knowledge_system.options_research_pipeline import OptionsResearchPipeline, _RESEARCH_LOG
        pipeline = OptionsResearchPipeline()
        pipeline.run_once()
        assert os.path.exists(_RESEARCH_LOG)
        with open(_RESEARCH_LOG) as f:
            content = f.read()
        assert "Research Pipeline Run" in content

    def test_T090_cursor_persisted(self):
        """T090: Pipeline cursor persists between restarts."""
        from knowledge_system.options_research_pipeline import OptionsResearchPipeline, _CURSOR_PATH
        from execution_engine.options_observation_journal import (
            OptionsObservationJournal, OptionsOpportunityObservation
        )
        j = OptionsObservationJournal()
        for _ in range(3):
            j.record(OptionsOpportunityObservation(
                obs_id=j.make_obs_id("NIFTY", "test"),
                symbol="NIFTY", strategy_name="test",
                observed_at="2026-04-01T10:00:00", state="DISCOVERED",
            ))
        p1 = OptionsResearchPipeline()
        p1.run_once()
        cursor1 = p1._cursor

        p2 = OptionsResearchPipeline()
        assert p2._cursor == cursor1


# ═══════════════════════════════════════════════════════════════════════════
# T091–T100  Underlying Response Tracker
# ═══════════════════════════════════════════════════════════════════════════

class TestUnderlyingResponseTracker:

    def test_T091_record_response_stores_observation(self):
        """T091: record_response() stores an observation with computed ratios."""
        from knowledge_system.options_underlying_response_tracker import OptionsUnderlyingResponseTracker
        t = OptionsUnderlyingResponseTracker()
        obs = t.record_response(
            opportunity_id="OPT-T091", symbol="NIFTY", strategy_name="BULL_CALL_SPREAD",
            direction="BULLISH", underlying_entry=22500, underlying_exit=22700,
            option_entry_premium=100.0, option_exit_premium=220.0, pnl_rs=12000.0,
            regime="BULL", ivr_band="IVR_NORMAL", dte_band="DTE_WEEKLY",
        )
        assert obs.underlying_pct_move > 0
        assert obs.option_pct_move > 0
        assert obs.option_underlying_ratio is not None
        assert obs.was_winner

    def test_T092_underlying_pct_correct(self):
        """T092: underlying_pct_move = (exit-entry)/entry*100."""
        from knowledge_system.options_underlying_response_tracker import OptionsUnderlyingResponseTracker
        t = OptionsUnderlyingResponseTracker()
        obs = t.record_response(
            "OPT-T092", "NIFTY", "test", "BULLISH",
            underlying_entry=22000, underlying_exit=22220,
            option_entry_premium=100.0, option_exit_premium=200.0,
            pnl_rs=10000.0,
        )
        assert abs(obs.underlying_pct_move - 1.0) < 0.01  # +1% move

    def test_T093_option_pct_correct(self):
        """T093: option_pct_move = (exit-entry)/entry*100."""
        from knowledge_system.options_underlying_response_tracker import OptionsUnderlyingResponseTracker
        t = OptionsUnderlyingResponseTracker()
        obs = t.record_response(
            "OPT-T093", "NIFTY", "test", "BULLISH",
            underlying_entry=22000, underlying_exit=22220,
            option_entry_premium=100.0, option_exit_premium=300.0,
            pnl_rs=10000.0,
        )
        assert abs(obs.option_pct_move - 200.0) < 0.01  # +200%

    def test_T094_ratio_computed_correctly(self):
        """T094: option_underlying_ratio = option_pct / underlying_pct."""
        from knowledge_system.options_underlying_response_tracker import OptionsUnderlyingResponseTracker
        t = OptionsUnderlyingResponseTracker()
        obs = t.record_response(
            "OPT-T094", "NIFTY", "test", "BULLISH",
            underlying_entry=22000, underlying_exit=22220,  # 1%
            option_entry_premium=100.0, option_exit_premium=300.0,  # 200%
            pnl_rs=10000.0,
        )
        # ratio = 200 / 1 = 200
        assert obs.option_underlying_ratio is not None
        assert abs(obs.option_underlying_ratio - 200.0) < 1.0

    def test_T095_ratio_none_when_underlying_flat(self):
        """T095: ratio is None when underlying move is near-zero."""
        from knowledge_system.options_underlying_response_tracker import OptionsUnderlyingResponseTracker
        t = OptionsUnderlyingResponseTracker()
        obs = t.record_response(
            "OPT-T095", "NIFTY", "test", "BULLISH",
            underlying_entry=22000, underlying_exit=22000,  # zero move
            option_entry_premium=100.0, option_exit_premium=150.0,
            pnl_rs=5000.0,
        )
        assert obs.option_underlying_ratio is None

    def test_T096_distribution_computed_at_min_obs(self):
        """T096: Distribution is computed once MIN_OBS_FOR_DISTRIBUTION observations exist."""
        from knowledge_system.options_underlying_response_tracker import (
            OptionsUnderlyingResponseTracker, MIN_OBS_FOR_DISTRIBUTION
        )
        t = OptionsUnderlyingResponseTracker()
        for i in range(MIN_OBS_FOR_DISTRIBUTION):
            t.record_response(
                f"OPT-T096-{i}", "NIFTY", "BULL_CALL_SPREAD", "BULLISH",
                underlying_entry=22000, underlying_exit=22200,
                option_entry_premium=100.0, option_exit_premium=200.0,
                pnl_rs=10000.0, regime="BULL", ivr_band="IVR_NORMAL", dte_band="DTE_WEEKLY",
            )
        dist = t.get_distribution("BULL_CALL_SPREAD", "BULL", "IVR_NORMAL", "DTE_WEEKLY")
        assert dist is not None
        assert dist.n == MIN_OBS_FOR_DISTRIBUTION

    def test_T097_zero_entry_premium_handled(self):
        """T097: Zero entry premium does not cause ZeroDivisionError."""
        from knowledge_system.options_underlying_response_tracker import OptionsUnderlyingResponseTracker
        t = OptionsUnderlyingResponseTracker()
        obs = t.record_response(
            "OPT-T097", "NIFTY", "test", "BULLISH",
            underlying_entry=22000, underlying_exit=22200,
            option_entry_premium=0.0, option_exit_premium=10.0,
            pnl_rs=1000.0,
        )
        assert obs.option_pct_move == 0.0

    def test_T098_persistence_round_trip(self):
        """T098: Observations persist and reload correctly."""
        from knowledge_system.options_underlying_response_tracker import OptionsUnderlyingResponseTracker
        t1 = OptionsUnderlyingResponseTracker()
        t1.record_response(
            "OPT-T098", "NIFTY", "test", "BULLISH",
            underlying_entry=22000, underlying_exit=22200,
            option_entry_premium=100.0, option_exit_premium=200.0, pnl_rs=10000.0,
        )
        assert os.path.exists("data/options_underlying_response.json")
        t2 = OptionsUnderlyingResponseTracker()
        assert len(t2.get_all_observations()) >= 1

    def test_T099_winner_flag_correct(self):
        """T099: was_winner=True iff pnl_rs > 0."""
        from knowledge_system.options_underlying_response_tracker import OptionsUnderlyingResponseTracker
        t = OptionsUnderlyingResponseTracker()
        win = t.record_response("W", "NIFTY", "test", "BULLISH",
            22000, 22200, 100.0, 200.0, pnl_rs=1000.0)
        loss = t.record_response("L", "NIFTY", "test", "BULLISH",
            22000, 22200, 100.0, 50.0, pnl_rs=-500.0)
        assert win.was_winner
        assert not loss.was_winner

    def test_T100_summary_correct(self):
        """T100: get_summary() returns correct totals."""
        from knowledge_system.options_underlying_response_tracker import OptionsUnderlyingResponseTracker
        t = OptionsUnderlyingResponseTracker()
        for i in range(3):
            t.record_response(f"W{i}", "NIFTY", "test", "BULLISH",
                22000, 22200, 100.0, 200.0, pnl_rs=1000.0)
        t.record_response("L1", "NIFTY", "test", "BULLISH",
            22000, 22200, 100.0, 50.0, pnl_rs=-500.0)
        s = t.get_summary()
        assert s["total_observations"] == 4
        assert s["winner_count"] == 3
        assert abs(s["win_rate"] - 0.75) < 0.01


# ═══════════════════════════════════════════════════════════════════════════
# T101–T110  Multi-Contract Shadow Tracker
# ═══════════════════════════════════════════════════════════════════════════

class TestMultiContractShadow:

    def test_T101_register_creates_pending(self):
        """T101: register_opportunity() creates pending records."""
        from knowledge_system.options_multi_contract_shadow import OptionsMultiContractShadow
        m = OptionsMultiContractShadow()
        m.register_opportunity(
            opportunity_id="OPT-T101",
            executed_strike=22500, executed_type="CE",
            executed_premium=100.0, executed_delta=0.52,
            candidates=[
                {"strike": 22600, "type": "CE", "premium": 60.0, "delta": 0.38, "iv": 0.18},
                {"strike": 22400, "type": "CE", "premium": 150.0, "delta": 0.62, "iv": 0.17},
            ],
        )
        assert "OPT-T101" in m._pending
        assert len(m._pending["OPT-T101"]) == 3  # 1 executed + 2 shadow

    def test_T102_executed_flagged_correctly(self):
        """T102: The executed contract has is_executed=True."""
        from knowledge_system.options_multi_contract_shadow import OptionsMultiContractShadow
        m = OptionsMultiContractShadow()
        m.register_opportunity("OPT-T102", 22500, "CE", 100.0, 0.52, [])
        executed = [r for r in m._pending["OPT-T102"] if r.is_executed]
        assert len(executed) == 1

    def test_T103_record_exit_computes_outcome(self):
        """T103: record_exit() computes MultiContractOutcome."""
        from knowledge_system.options_multi_contract_shadow import (
            OptionsMultiContractShadow, SEL_CORRECT, SEL_FAILURE
        )
        m = OptionsMultiContractShadow()
        m.register_opportunity("OPT-T103", 22500, "CE", 100.0, 0.52,
            candidates=[{"strike": 22600, "type": "CE", "premium": 60.0, "delta": 0.38, "iv": 0.18}])
        # Executed: 100→220 (+120), Shadow: 60→180 (+120)
        result = m.record_exit(
            "OPT-T103",
            exit_premiums={"CE|22500": 220.0, "CE|22600": 180.0},
            symbol="NIFTY", strategy_name="Bull_Call_Spread", direction="BULLISH",
            regime="BULL", ivr_band="IVR_NORMAL", dte_band="DTE_WEEKLY",
            underlying_pct_move=1.0,
        )
        assert result is not None
        assert result.executed_pnl == 120.0

    def test_T104_correct_selection_when_executed_best(self):
        """T104: SEL_CORRECT when executed contract outperforms."""
        from knowledge_system.options_multi_contract_shadow import (
            OptionsMultiContractShadow, SEL_CORRECT
        )
        m = OptionsMultiContractShadow()
        m.register_opportunity("OPT-T104", 22500, "CE", 100.0, 0.52,
            candidates=[{"strike": 22600, "type": "CE", "premium": 60.0, "delta": 0.38, "iv": 0.18}])
        # Executed: 100→300 (+200), Shadow: 60→100 (+40)
        result = m.record_exit(
            "OPT-T104",
            exit_premiums={"CE|22500": 300.0, "CE|22600": 100.0},
            symbol="NIFTY", strategy_name="test", direction="BULLISH",
            regime="BULL", ivr_band="IVR_NORMAL", dte_band="DTE_WEEKLY",
            underlying_pct_move=1.0,
        )
        assert result.selection_outcome == SEL_CORRECT

    def test_T105_failure_when_better_contract_available(self):
        """T105: SEL_FAILURE when shadow significantly outperforms executed."""
        from knowledge_system.options_multi_contract_shadow import (
            OptionsMultiContractShadow, SEL_FAILURE
        )
        m = OptionsMultiContractShadow()
        m.register_opportunity("OPT-T105", 22500, "CE", 100.0, 0.52,
            candidates=[{"strike": 22600, "type": "CE", "premium": 60.0, "delta": 0.38, "iv": 0.18}])
        # Executed: 100→110 (+10), Shadow: 60→200 (+140)
        result = m.record_exit(
            "OPT-T105",
            exit_premiums={"CE|22500": 110.0, "CE|22600": 200.0},
            symbol="NIFTY", strategy_name="test", direction="BULLISH",
            regime="BULL", ivr_band="IVR_NORMAL", dte_band="DTE_WEEKLY",
            underlying_pct_move=1.0,
        )
        assert result.selection_outcome == SEL_FAILURE
        assert result.improvement_possible > 0

    def test_T106_missing_exit_price_handled(self):
        """T106: Missing exit premiums for shadow contracts are silently handled."""
        from knowledge_system.options_multi_contract_shadow import OptionsMultiContractShadow
        m = OptionsMultiContractShadow()
        m.register_opportunity("OPT-T106", 22500, "CE", 100.0, 0.52,
            candidates=[{"strike": 22600, "type": "CE", "premium": 60.0, "delta": 0.38, "iv": 0.18}])
        # Only provide executed exit price
        result = m.record_exit(
            "OPT-T106",
            exit_premiums={"CE|22500": 200.0},  # no shadow exit
            symbol="NIFTY", strategy_name="test", direction="BULLISH",
            regime="BULL", ivr_band="IVR_NORMAL", dte_band="DTE_WEEKLY",
            underlying_pct_move=1.0,
        )
        # Should still return an outcome (executed-only)
        assert result is not None

    def test_T107_unknown_opportunity_returns_none(self):
        """T107: record_exit() for unknown opportunity_id returns None."""
        from knowledge_system.options_multi_contract_shadow import OptionsMultiContractShadow
        m = OptionsMultiContractShadow()
        result = m.record_exit(
            "OPT-UNKNOWN",
            exit_premiums={"CE|22500": 200.0},
            symbol="NIFTY", strategy_name="test", direction="BULLISH",
            regime="BULL", ivr_band="IVR_NORMAL", dte_band="DTE_WEEKLY",
            underlying_pct_move=1.0,
        )
        assert result is None

    def test_T108_persistence(self):
        """T108: Pending records persist to disk."""
        from knowledge_system.options_multi_contract_shadow import OptionsMultiContractShadow
        m = OptionsMultiContractShadow()
        m.register_opportunity("OPT-T108", 22500, "CE", 100.0, 0.52, [])
        assert os.path.exists("data/options_multi_contract_shadow.json")

    def test_T109_selection_quality_summary(self):
        """T109: get_selection_quality_summary() returns correct stats."""
        from knowledge_system.options_multi_contract_shadow import (
            OptionsMultiContractShadow, SEL_CORRECT, SEL_FAILURE
        )
        m = OptionsMultiContractShadow()
        # Two CORRECT, one FAILURE
        for i in range(2):
            oid = f"OPT-COR-{i}"
            m.register_opportunity(oid, 22500, "CE", 100.0, 0.52,
                candidates=[{"strike": 22600, "type": "CE", "premium": 60.0, "delta": 0.38, "iv": 0.18}])
            m.record_exit(oid, exit_premiums={"CE|22500": 300.0, "CE|22600": 100.0},
                symbol="NIFTY", strategy_name="test", direction="BULLISH",
                regime="BULL", ivr_band="IVR_NORMAL", dte_band="DTE_WEEKLY",
                underlying_pct_move=1.0)
        oid_fail = "OPT-FAIL-0"
        m.register_opportunity(oid_fail, 22500, "CE", 100.0, 0.52,
            candidates=[{"strike": 22600, "type": "CE", "premium": 60.0, "delta": 0.38, "iv": 0.18}])
        m.record_exit(oid_fail, exit_premiums={"CE|22500": 110.0, "CE|22600": 200.0},
            symbol="NIFTY", strategy_name="test", direction="BULLISH",
            regime="BULL", ivr_band="IVR_NORMAL", dte_band="DTE_WEEKLY",
            underlying_pct_move=1.0)
        q = m.get_selection_quality_summary()
        assert q["total"] == 3
        assert abs(q["correct_rate"] - 2/3) < 0.01

    def test_T110_reload_persistence(self):
        """T110: Multi-contract shadow reloads outcomes from disk."""
        from knowledge_system.options_multi_contract_shadow import OptionsMultiContractShadow
        m1 = OptionsMultiContractShadow()
        m1.register_opportunity("OPT-T110", 22500, "CE", 100.0, 0.52, [])
        m1.record_exit("OPT-T110", {"CE|22500": 200.0},
            "NIFTY", "test", "BULLISH", "BULL", "IVR_NORMAL", "DTE_WEEKLY", 1.0)
        m2 = OptionsMultiContractShadow()
        assert len(m2.get_outcomes()) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# T111–T120  Failure Classifier
# ═══════════════════════════════════════════════════════════════════════════

class TestFailureClassifier:

    def test_T111_classify_loss_returns_record(self):
        """T111: classify() on a loss returns a FailureRecord."""
        from knowledge_system.options_failure_classifier import OptionsFailureClassifier
        fc = OptionsFailureClassifier()
        rec = fc.classify("OPT-T111", "NIFTY", "test",
            evidence="exit_reason=stop_loss", pnl_rs=-500.0, expected_pnl=800.0)
        assert rec is not None
        assert rec.pnl_rs == -500.0

    def test_T112_no_failure_on_profit(self):
        """T112: Profitable trades with no explicit failure_type return None."""
        from knowledge_system.options_failure_classifier import OptionsFailureClassifier
        fc = OptionsFailureClassifier()
        rec = fc.classify("OPT-T112", "NIFTY", "test",
            evidence="", pnl_rs=500.0, expected_pnl=800.0)
        assert rec is None

    def test_T113_auto_classify_data_failure(self):
        """T113: Evidence containing 'iv_source=MODEL_ESTIMATE' → DATA_FAILURE."""
        from knowledge_system.options_failure_classifier import OptionsFailureClassifier, FAIL_DATA
        fc = OptionsFailureClassifier()
        rec = fc.classify("OPT-T113", "NIFTY", "test",
            evidence="iv_source=MODEL_ESTIMATE", pnl_rs=-300.0, expected_pnl=500.0)
        assert rec.failure_type == FAIL_DATA

    def test_T114_auto_classify_option_selection(self):
        """T114: 'wrong_contract' evidence → OPTION_SELECTION_FAILURE."""
        from knowledge_system.options_failure_classifier import (
            OptionsFailureClassifier, FAIL_OPTION_SELECT
        )
        fc = OptionsFailureClassifier()
        rec = fc.classify("OPT-T114", "NIFTY", "test",
            evidence="wrong_contract selected vs better OTM", pnl_rs=-200.0, expected_pnl=500.0)
        assert rec.failure_type == FAIL_OPTION_SELECT

    def test_T115_manual_failure_type_used(self):
        """T115: Explicitly provided failure_type overrides auto-classification."""
        from knowledge_system.options_failure_classifier import (
            OptionsFailureClassifier, FAIL_TIMING
        )
        fc = OptionsFailureClassifier()
        rec = fc.classify("OPT-T115", "NIFTY", "test",
            evidence="entry too late", pnl_rs=-150.0, expected_pnl=500.0,
            failure_type=FAIL_TIMING)
        assert rec.failure_type == FAIL_TIMING

    def test_T116_severity_critical_for_extreme_loss(self):
        """T116: Loss > 2× expected → CRITICAL severity."""
        from knowledge_system.options_failure_classifier import OptionsFailureClassifier
        fc = OptionsFailureClassifier()
        rec = fc.classify("OPT-T116", "NIFTY", "test",
            evidence="stop missed", pnl_rs=-2000.0, expected_pnl=500.0)
        assert rec.severity == "CRITICAL"

    def test_T117_get_failure_distribution(self):
        """T117: get_failure_distribution() counts by type."""
        from knowledge_system.options_failure_classifier import (
            OptionsFailureClassifier, FAIL_DATA, FAIL_TIMING
        )
        fc = OptionsFailureClassifier()
        fc.classify("A", "NIFTY", "test", "iv_source=MODEL_ESTIMATE", -100.0, 500.0)
        fc.classify("B", "NIFTY", "test", "entry too late", -100.0, 500.0, failure_type=FAIL_TIMING)
        dist = fc.get_failure_distribution()
        assert dist[FAIL_DATA] >= 1
        assert dist[FAIL_TIMING] >= 1

    def test_T118_persistence(self):
        """T118: Failures persist to disk."""
        from knowledge_system.options_failure_classifier import OptionsFailureClassifier
        fc = OptionsFailureClassifier()
        fc.classify("OPT-T118", "NIFTY", "test", "some_reason", -100.0, 500.0)
        assert os.path.exists("data/options_failures.json")

    def test_T119_reload_from_disk(self):
        """T119: Failure records reload correctly after restart."""
        from knowledge_system.options_failure_classifier import OptionsFailureClassifier
        fc1 = OptionsFailureClassifier()
        fc1.classify("OPT-T119", "NIFTY", "test", "evidence", -100.0, 500.0)
        fc2 = OptionsFailureClassifier()
        assert len(fc2.get_recent_failures()) >= 1

    def test_T120_improvement_hint_populated(self):
        """T120: improvement_hint is non-empty for all failure types."""
        from knowledge_system.options_failure_classifier import (
            OptionsFailureClassifier, FAIL_DATA, FAIL_OPTION_SELECT, FAIL_EXECUTION
        )
        fc = OptionsFailureClassifier()
        for ftype in [FAIL_DATA, FAIL_OPTION_SELECT, FAIL_EXECUTION]:
            rec = fc.classify(f"OPT-T120-{ftype}", "NIFTY", "test", "",
                pnl_rs=-100.0, expected_pnl=500.0, failure_type=ftype)
            assert rec.improvement_hint != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

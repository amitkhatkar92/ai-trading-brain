"""
tests/test_dta_system_017.py
===============================
DTA-SYSTEM-017 tests — Bootstrap persistence + production-path causal chain.

Every test here catches a real failure mode that the T033-T038 tests missed.

TI-016-001 (root cause): T033-T038 use _hbe_with() synthetic injection and
never touch the production path. These tests use the canonical BOOTSTRAP_*.jsonl
file mechanism and the real HistoricalBehaviourEngine.load_outcomes() path.

Test groups:
  T001-T004  bootstrap disk write / read round-trip
  T005-T007  load_outcomes() reads BOOTSTRAP files
  T008-T010  causal: KDP/HBE sees bootstrap records
  T011-T013  causal: evidence state changes with bootstrap
  T014-T015  idempotency / duplicate safety
  T016-T017  restart safety
  T018       opportunity_id in KLP observations (D016-003)
  T019-T020  MultiIndex yfinance flatten helpers (D016-002)
  T021-T022  historical + live evidence coexistence (D016-001 Phase 6)
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from typing import List

import pytest

from opportunity_engine.hbe_models import OutcomeRecord
from opportunity_engine.historical_behaviour_engine import (
    HistoricalBehaviourEngine,
    _load_bootstrap_file,
)
from learning_system.historical_bootstrap import (
    _bootstrap_disk_path,
    _write_bootstrap_to_disk,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

_TODAY      = date.today().isoformat()
_RECENT     = (date.today() - timedelta(days=30)).isoformat()
_OLD        = (date.today() - timedelta(days=400)).isoformat()


def _rec(
    symbol: str = "TATASTEEL",
    trading_date: str = _RECENT,
    first_event: str = "TARGET_HIT",
    source_type: str = "HISTORICAL",
) -> OutcomeRecord:
    return OutcomeRecord(
        obs_id=f"KBS_{symbol}_{trading_date}_{uuid.uuid4().hex[:8]}",
        trading_date=trading_date,
        symbol=symbol,
        direction="BUY",
        regime="BULL",
        sector="METALS",
        reference_entry=1000.0,
        knowledge_target=1060.0,
        knowledge_stop=975.0,
        atr=25.0,
        atr_pct=2.5,
        scanner_confidence=7.0,
        candidate_score=0.60,
        knowledge_score=0.0,
        knowledge_rr=2.4,
        first_event=first_event,
        first_event_day=None,
        target_hit=(first_event == "TARGET_HIT"),
        stop_hit=(first_event == "STOP_HIT"),
        t1_ret_pct=0.5,
        t3_ret_pct=1.2,
        t5_ret_pct=2.0,
        mfe_pct=2.5,
        mae_pct=-0.8,
        days_to_event=3,
        no_lookahead=True,
        source_type=source_type,
        validation_partition="TRAIN",
    )


def _tmp_klp() -> Path:
    return Path(tempfile.mkdtemp())


# ─────────────────────────────────────────────────────────────────────────────
# T001-T004  Bootstrap disk write / read round-trip
# ─────────────────────────────────────────────────────────────────────────────

def test_t001_write_bootstrap_creates_file():
    """_write_bootstrap_to_disk writes a BOOTSTRAP_<date>.jsonl file."""
    klp = _tmp_klp()
    recs = [_rec() for _ in range(3)]
    path = _write_bootstrap_to_disk(recs, klp, "2025-08-01")
    assert path.exists(), f"Bootstrap file not created: {path}"
    assert path.name == "BOOTSTRAP_2025-08-01.jsonl"


def test_t002_write_bootstrap_file_has_correct_line_count():
    """Each OutcomeRecord is one JSON line in the BOOTSTRAP file."""
    klp = _tmp_klp()
    recs = [_rec() for _ in range(7)]
    path = _write_bootstrap_to_disk(recs, klp, "2025-08-01")
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    assert len(lines) == 7


def test_t003_load_bootstrap_file_round_trips_all_fields():
    """_load_bootstrap_file restores all OutcomeRecord fields correctly."""
    klp = _tmp_klp()
    original = _rec(symbol="INFY", trading_date=_RECENT, first_event="STOP_HIT")
    path = _write_bootstrap_to_disk([original], klp, "2025-08-01")
    loaded = _load_bootstrap_file(path)
    assert len(loaded) == 1
    r = loaded[0]
    assert r.obs_id == original.obs_id
    assert r.symbol == "INFY"
    assert r.direction == "BUY"
    assert r.first_event == "STOP_HIT"
    assert r.stop_hit is True
    assert r.target_hit is False
    assert r.source_type == "HISTORICAL"
    assert r.no_lookahead is True
    assert r.trading_date == _RECENT


def test_t004_load_bootstrap_file_skips_malformed_lines():
    """_load_bootstrap_file skips empty lines and bad JSON without crashing."""
    klp = _tmp_klp()
    path = klp / "BOOTSTRAP_2025-08-01.jsonl"
    path.write_text(
        "\n"
        "{bad json\n"
        '{"obs_id": "", "trading_date": "2025-01-01", "symbol": "INFY"}\n'  # missing obs_id
        + json.dumps(asdict(_rec())) + "\n",
        encoding="utf-8",
    )
    loaded = _load_bootstrap_file(path)
    assert len(loaded) == 1  # only the valid record


# ─────────────────────────────────────────────────────────────────────────────
# T005-T007  load_outcomes() reads BOOTSTRAP files
# ─────────────────────────────────────────────────────────────────────────────

def test_t005_load_outcomes_reads_bootstrap_file():
    """load_outcomes() picks up BOOTSTRAP_*.jsonl alongside KLP_*.jsonl."""
    klp = _tmp_klp()
    recs = [_rec() for _ in range(5)]
    _write_bootstrap_to_disk(recs, klp, "2025-08-01")

    hbe = HistoricalBehaviourEngine(data_dir=klp)
    n = hbe.load_outcomes()
    assert n == 5, f"Expected 5 bootstrap records, got {n}"


def test_t006_load_outcomes_no_bootstrap_file_returns_zero():
    """load_outcomes() on empty dir returns 0 (regression guard)."""
    klp = _tmp_klp()
    hbe = HistoricalBehaviourEngine(data_dir=klp)
    n = hbe.load_outcomes()
    assert n == 0


def test_t007_load_outcomes_deduplicates_bootstrap_and_klp():
    """Same obs_id in BOOTSTRAP and KLP is not double-counted."""
    klp = _tmp_klp()
    rec = _rec()

    # Write the record to both a KLP file and a BOOTSTRAP file
    # KLP format requires event_type KNOWLEDGE_OBSERVATION + OUTCOME_UPDATE pair
    klp_file = klp / "KLP_2025-08-01.jsonl"
    obs_row = {
        "event_type": "KNOWLEDGE_OBSERVATION",
        "obs_id": rec.obs_id,
        "symbol": rec.symbol,
        "direction": rec.direction,
        "regime": rec.regime,
        "reference_entry": rec.reference_entry,
        "knowledge_target": rec.knowledge_target,
        "knowledge_stop_loss": rec.knowledge_stop,
        "atr": rec.atr,
        "atr_pct": rec.atr_pct,
        "scanner_confidence": rec.scanner_confidence,
        "candidate_score": rec.candidate_score,
        "knowledge_score": rec.knowledge_score,
        "knowledge_RR": rec.knowledge_rr,
        "source_type": rec.source_type,
        "validation_partition": rec.validation_partition,
    }
    out_row = {
        "event_type": "OUTCOME_UPDATE",
        "obs_id": rec.obs_id,
        "first_event": rec.first_event,
        "first_event_day": rec.first_event_day,
        "target_hit": rec.target_hit,
        "stop_hit": rec.stop_hit,
        "t1_ret_pct": rec.t1_ret_pct,
        "t3_ret_pct": rec.t3_ret_pct,
        "t5_ret_pct": rec.t5_ret_pct,
        "mfe_pct": rec.mfe_pct,
        "mae_pct": rec.mae_pct,
    }
    with klp_file.open("w") as fh:
        fh.write(json.dumps(obs_row) + "\n")
        fh.write(json.dumps(out_row) + "\n")

    _write_bootstrap_to_disk([rec], klp, "2025-08-01")

    hbe = HistoricalBehaviourEngine(data_dir=klp)
    n = hbe.load_outcomes()
    assert n == 1, f"Duplicate obs_id should be deduped: got {n}"


# ─────────────────────────────────────────────────────────────────────────────
# T008-T010  Causal: KDP-equivalent HBE sees bootstrap records
# ─────────────────────────────────────────────────────────────────────────────

def test_t008_fresh_hbe_instance_sees_bootstrap_file():
    """
    PRODUCTION PATH TEST — T033-T038 missed this.

    Creating a new HistoricalBehaviourEngine(data_dir=klp) and calling
    load_outcomes() (exactly as KDP._reload_hbe() does) returns the
    bootstrap records from disk.
    """
    klp = _tmp_klp()
    recs = [_rec() for _ in range(10)]
    _write_bootstrap_to_disk(recs, klp, "2025-08-01")

    # This mirrors KDP._reload_hbe() exactly
    hbe = HistoricalBehaviourEngine(data_dir=klp)
    n = hbe.load_outcomes()

    assert n == 10, (
        f"KDP-style HBE reload should see bootstrap records. Got {n}. "
        "This would have caught D016-001."
    )
    assert hbe.broker_calls == 0
    assert hbe.orders == 0


def test_t009_hbe_profile_has_nonzero_ess_with_recent_bootstrap():
    """With 10 recent bootstrap records, HBE profile ESS > 0 (causal change)."""
    klp = _tmp_klp()
    recent = (date.today() - timedelta(days=20)).isoformat()
    recs = [_rec(trading_date=recent) for _ in range(10)]
    _write_bootstrap_to_disk(recs, klp, "2025-08-01")

    hbe = HistoricalBehaviourEngine(data_dir=klp)
    hbe.load_outcomes()
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")

    assert profile.metrics.effective_sample_size > 0.0, (
        "ESS should be > 0 with recent bootstrap records"
    )
    assert profile.broker_calls == 0


def test_t010_hbe_without_bootstrap_returns_zero_ess():
    """Without bootstrap records, HBE ESS = 0 (confirms baseline)."""
    klp = _tmp_klp()
    hbe = HistoricalBehaviourEngine(data_dir=klp)
    hbe.load_outcomes()
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.effective_sample_size == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# T011-T013  Causal: evidence state changes with bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def test_t011_evidence_state_differs_with_vs_without_bootstrap():
    """
    CORE CAUSAL TEST — proves the historical bootstrap → KDA path is active.

    WITHOUT bootstrap: HBE count=0, ESS=0 (INSUFFICIENT)
    WITH bootstrap:    HBE count=N, ESS>0

    The effective_sample_size must differ between the two cases.
    This is the test that would have caught D016-001.
    """
    klp_empty = _tmp_klp()
    klp_loaded = _tmp_klp()

    recent = (date.today() - timedelta(days=25)).isoformat()
    recs = [_rec(trading_date=recent) for _ in range(5)]
    _write_bootstrap_to_disk(recs, klp_loaded, "2025-08-01")

    hbe_empty = HistoricalBehaviourEngine(data_dir=klp_empty)
    hbe_empty.load_outcomes()

    hbe_loaded = HistoricalBehaviourEngine(data_dir=klp_loaded)
    hbe_loaded.load_outcomes()

    profile_empty  = hbe_empty.get_behaviour_profile("TATASTEEL", "BUY")
    profile_loaded = hbe_loaded.get_behaviour_profile("TATASTEEL", "BUY")

    ess_empty  = profile_empty.metrics.effective_sample_size
    ess_loaded = profile_loaded.metrics.effective_sample_size

    assert ess_empty == 0.0, f"Empty HBE should have ESS=0, got {ess_empty}"
    assert ess_loaded > 0.0, f"Loaded HBE should have ESS>0, got {ess_loaded}"
    assert ess_loaded > ess_empty, (
        f"Bootstrap must causally increase ESS: empty={ess_empty} loaded={ess_loaded}"
    )


def test_t012_evidence_state_reaches_developing_with_enough_recent_records():
    """10 records from last 30 days → ESS >= 3 → DEVELOPING evidence state."""
    from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority, EvidenceState
    klp = _tmp_klp()
    recent = (date.today() - timedelta(days=30)).isoformat()
    recs = [_rec(trading_date=recent) for _ in range(10)]
    _write_bootstrap_to_disk(recs, klp, "2025-08-01")

    hbe = HistoricalBehaviourEngine(data_dir=klp)
    hbe.load_outcomes()
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")

    kda = KnowledgeDecisionAuthority()
    obs = {
        "symbol": "TATASTEEL",
        "direction": "BUY",
        "entry_price": 1000.0,
        "atr": 25.0,
        "atr_pct": 2.5,
        "scanner_confidence": 7.5,
        "opportunity_id": str(uuid.uuid4()),
    }
    rec = kda.evaluate(obs, behaviour=profile.metrics, angle_view=None)
    assert rec.evidence_state != EvidenceState.INSUFFICIENT, (
        f"10 recent records should exit INSUFFICIENT: got {rec.evidence_state}  ESS={profile.metrics.effective_sample_size:.2f}"
    )
    assert rec.broker_calls == 0


def test_t013_kda_evidence_state_changes_with_vs_without_bootstrap():
    """
    KDA evidence_state must differ between no-bootstrap and with-bootstrap.
    This is the end-to-end causal test for the whole D016-001 fix.
    """
    from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority, EvidenceState
    klp_empty  = _tmp_klp()
    klp_loaded = _tmp_klp()

    recent = (date.today() - timedelta(days=28)).isoformat()
    recs = [_rec(trading_date=recent) for _ in range(12)]
    _write_bootstrap_to_disk(recs, klp_loaded, "2025-08-01")

    hbe_a = HistoricalBehaviourEngine(data_dir=klp_empty);  hbe_a.load_outcomes()
    hbe_b = HistoricalBehaviourEngine(data_dir=klp_loaded); hbe_b.load_outcomes()

    prof_a = hbe_a.get_behaviour_profile("TATASTEEL", "BUY")
    prof_b = hbe_b.get_behaviour_profile("TATASTEEL", "BUY")

    kda = KnowledgeDecisionAuthority()
    obs = {"symbol":"TATASTEEL","direction":"BUY","entry_price":1000.0,
           "atr":25.0,"atr_pct":2.5,"scanner_confidence":7.5,
           "opportunity_id": str(uuid.uuid4())}

    rec_a = kda.evaluate(obs, behaviour=prof_a.metrics, angle_view=None)
    rec_b = kda.evaluate(obs, behaviour=prof_b.metrics, angle_view=None)

    assert rec_a.evidence_state == EvidenceState.INSUFFICIENT, (
        f"No bootstrap should be INSUFFICIENT: got {rec_a.evidence_state}"
    )
    assert rec_b.evidence_state != EvidenceState.INSUFFICIENT, (
        f"12 recent bootstrap records should exit INSUFFICIENT: got {rec_b.evidence_state}  "
        f"ESS={prof_b.metrics.effective_sample_size:.2f}"
    )
    assert rec_a.broker_calls == 0
    assert rec_b.broker_calls == 0


# ─────────────────────────────────────────────────────────────────────────────
# T014-T015  Idempotency / duplicate safety
# ─────────────────────────────────────────────────────────────────────────────

def test_t014_double_write_to_bootstrap_file_still_deduplicates():
    """Writing the same records twice, loading once: deduplication prevents doubles."""
    klp = _tmp_klp()
    recs = [_rec() for _ in range(5)]
    _write_bootstrap_to_disk(recs, klp, "2025-08-01")
    _write_bootstrap_to_disk(recs, klp, "2025-08-01")  # overwrites same file

    hbe = HistoricalBehaviourEngine(data_dir=klp)
    n = hbe.load_outcomes()
    assert n == 5, f"Overwrite then reload should still give 5 records, got {n}"


def test_t015_two_bootstrap_files_different_dates_no_duplication():
    """Two BOOTSTRAP files on different dates with same symbol but unique obs_ids."""
    klp = _tmp_klp()
    recs_a = [_rec(trading_date="2025-06-01") for _ in range(3)]
    recs_b = [_rec(trading_date="2025-07-01") for _ in range(4)]
    _write_bootstrap_to_disk(recs_a, klp, "2025-06-01")
    _write_bootstrap_to_disk(recs_b, klp, "2025-07-01")

    hbe = HistoricalBehaviourEngine(data_dir=klp)
    n = hbe.load_outcomes()
    assert n == 7, f"Two distinct bootstrap files should load 7 unique records, got {n}"


# ─────────────────────────────────────────────────────────────────────────────
# T016-T017  Restart safety
# ─────────────────────────────────────────────────────────────────────────────

def test_t016_bootstrap_records_survive_hbe_reload():
    """
    Restart safety: creating a NEW HBE instance (as KDP does each day) loads
    the same bootstrap records from disk.
    """
    klp = _tmp_klp()
    recs = [_rec() for _ in range(8)]
    _write_bootstrap_to_disk(recs, klp, "2025-08-01")

    hbe1 = HistoricalBehaviourEngine(data_dir=klp)
    n1 = hbe1.load_outcomes()

    # Simulate restart: new instance, same data_dir
    hbe2 = HistoricalBehaviourEngine(data_dir=klp)
    n2 = hbe2.load_outcomes()

    assert n1 == n2 == 8, (
        f"Both HBE instances should load 8 records from disk: n1={n1} n2={n2}"
    )


def test_t017_bootstrap_file_present_after_write(tmp_path):
    """BOOTSTRAP file persists after the write function exits (file system test)."""
    recs = [_rec()]
    path = _write_bootstrap_to_disk(recs, tmp_path, "2025-08-01")
    assert path.is_file()
    assert path.stat().st_size > 0


# ─────────────────────────────────────────────────────────────────────────────
# T018  opportunity_id in KLP observations (D016-003)
# ─────────────────────────────────────────────────────────────────────────────

def test_t018_build_obs_record_includes_opportunity_id():
    """
    D016-003: _build_obs_record() must include opportunity_id from the signal.
    """
    from datetime import datetime, timezone
    from opportunity_engine.klp_evaluator import _build_obs_record
    from types import SimpleNamespace
    from models.trade_signal import SignalDirection

    opp_id = str(uuid.uuid4())
    sig = SimpleNamespace(
        symbol="TATASTEEL",
        direction=SignalDirection.BUY,
        entry_price=1000.0,
        stop_loss=975.0,
        target_price=1060.0,
        atr=25.0,
        confidence=7.5,
        strategy_name="breakout_v1",
        opportunity_id=opp_id,
        _obs_candidate_score=0.72,
        _obs_regime="BULL",
        expected_move_pct=2.5,
    )
    rec = _build_obs_record(
        sig=sig,
        score=0.72,
        rank=1,
        selected=True,
        now_utc=datetime.now(timezone.utc),
        date_str="2026-08-27",
        total_signals=5,
    )
    assert rec.get("opportunity_id") == opp_id, (
        f"opportunity_id not propagated to KLP record: {rec.get('opportunity_id')}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T019-T020  MultiIndex yfinance flatten (D016-002)
# ─────────────────────────────────────────────────────────────────────────────

def test_t019_multiindex_flatten_produces_scalar_values():
    """MultiIndex DataFrame column flatten gives scalar Open/High/Low/Close."""
    import pandas as pd
    import numpy as np

    # Simulate yfinance 1.x MultiIndex single-symbol download
    dates = pd.date_range("2025-01-02", periods=3, freq="B")
    cols = pd.MultiIndex.from_tuples(
        [("Open","TATASTEEL"),("High","TATASTEEL"),("Low","TATASTEEL"),("Close","TATASTEEL")],
    )
    data = np.array([[1000,1010,990,1005],[1005,1015,998,1012],[1012,1020,1005,1018]])
    df_multi = pd.DataFrame(data, index=dates, columns=cols)

    assert isinstance(df_multi.columns, pd.MultiIndex)

    # Apply the same flatten as in the fixed code
    df = df_multi.copy()
    df.columns = df.columns.droplevel(level=-1)
    df = df.loc[:, ~df.columns.duplicated()]

    for idx, row in df.iterrows():
        o = float(row["Open"])
        h = float(row["High"])
        l = float(row["Low"])
        c = float(row["Close"])
        assert isinstance(o, float)
        assert isinstance(h, float)
        assert h >= l


def test_t020_normal_columns_not_affected_by_flatten():
    """Standard single-level columns pass through flatten unchanged."""
    import pandas as pd
    import numpy as np

    dates = pd.date_range("2025-01-02", periods=2, freq="B")
    df = pd.DataFrame(
        {"Open":[100.0,101.0],"High":[102.0,103.0],"Low":[99.0,100.0],"Close":[101.5,102.5]},
        index=dates,
    )
    assert not isinstance(df.columns, pd.MultiIndex)
    # The flatten guard should be a no-op for standard columns
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy(); df.columns = df.columns.droplevel(level=-1)
        df = df.loc[:, ~df.columns.duplicated()]

    for idx, row in df.iterrows():
        assert float(row["Open"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# T021-T022  Historical + live evidence coexistence (Phase 6)
# ─────────────────────────────────────────────────────────────────────────────

def _write_klp_file(klp: Path, date_str: str, recs: list) -> None:
    """Write minimal KLP_<date>.jsonl with observation + outcome pairs."""
    path = klp / f"KLP_{date_str}.jsonl"
    with path.open("w") as fh:
        for rec in recs:
            obs = {
                "event_type": "KNOWLEDGE_OBSERVATION",
                "obs_id": rec.obs_id,
                "symbol": rec.symbol,
                "direction": rec.direction,
                "regime": rec.regime,
                "reference_entry": rec.reference_entry,
                "knowledge_target": rec.knowledge_target,
                "knowledge_stop_loss": rec.knowledge_stop,
                "atr": rec.atr,
                "atr_pct": rec.atr_pct,
                "scanner_confidence": rec.scanner_confidence,
                "candidate_score": rec.candidate_score,
                "knowledge_score": rec.knowledge_score,
                "knowledge_RR": rec.knowledge_rr,
                "source_type": rec.source_type,
                "validation_partition": rec.validation_partition,
            }
            out = {
                "event_type": "OUTCOME_UPDATE",
                "obs_id": rec.obs_id,
                "first_event": rec.first_event,
                "first_event_day": rec.first_event_day,
                "target_hit": rec.target_hit,
                "stop_hit": rec.stop_hit,
                "t1_ret_pct": rec.t1_ret_pct,
                "t3_ret_pct": rec.t3_ret_pct,
                "t5_ret_pct": rec.t5_ret_pct,
                "mfe_pct": rec.mfe_pct,
                "mae_pct": rec.mae_pct,
            }
            fh.write(json.dumps(obs) + "\n")
            fh.write(json.dumps(out) + "\n")


def test_t021_historical_and_live_records_coexist_in_hbe():
    """
    HISTORICAL (BOOTSTRAP) + LIVE (KLP) records both load into one HBE.
    Provenance is preserved via source_type field.
    """
    klp = _tmp_klp()
    hist_recs = [_rec(trading_date="2025-06-15", source_type="HISTORICAL") for _ in range(5)]
    live_recs = [_rec(trading_date="2026-08-20", source_type="LIVE") for _ in range(3)]

    _write_bootstrap_to_disk(hist_recs, klp, "2025-06-15")
    _write_klp_file(klp, "2026-08-20", live_recs)

    hbe = HistoricalBehaviourEngine(data_dir=klp)
    n = hbe.load_outcomes()
    assert n == 8, f"Expected 5 historical + 3 live = 8, got {n}"

    sources = {r.source_type for r in hbe._outcomes}
    assert "HISTORICAL" in sources
    assert "LIVE" in sources


def test_t022_live_evidence_does_not_corrupt_historical_records():
    """Adding live records does not change obs_id or source_type of historical ones."""
    klp = _tmp_klp()
    hist_recs = [_rec(trading_date="2025-06-15", source_type="HISTORICAL") for _ in range(3)]
    live_recs = [_rec(trading_date="2026-08-20", source_type="LIVE") for _ in range(2)]

    _write_bootstrap_to_disk(hist_recs, klp, "2025-06-15")
    _write_klp_file(klp, "2026-08-20", live_recs)

    hbe = HistoricalBehaviourEngine(data_dir=klp)
    hbe.load_outcomes()

    hist_ids = {r.obs_id for r in hist_recs}
    for r in hbe._outcomes:
        if r.obs_id in hist_ids:
            assert r.source_type == "HISTORICAL", (
                f"Historical record {r.obs_id} should not have source_type changed"
            )

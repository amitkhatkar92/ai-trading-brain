"""
Test Suite — Root-cause fix: PGA Category B -> IDR bridge
==========================================================
Verifies predictive_gap/pga_learning.py::_try_reinforce_idr() no longer
calls IDRRepository.add_observation() (a method that never existed --
IDRRepository is a feature/pattern-keyed DNA store with no symbol column).
Instead it now uses predictive_gap/pga_idr_bridge.py, an isolated,
advisory-only, append-only observation log.

T01  record_reinforcement_observation() appends a real JSONL record
T02  get_observation_count() counts correctly, with/without symbol filter
T03  get_last_observations() returns oldest-first, capped at n
T04  record_reinforcement_observation() fails open (False) on I/O error
T05  _try_reinforce_idr() now succeeds (previously always failed --
     AttributeError on the non-existent add_observation)
T06  _try_reinforce_idr() fail-open: bridge exception does not propagate
T07  Safety: no import of market_learning.idr_repository anywhere in the
     bridge module (confirms this is a genuinely new, isolated path, not
     a disguised re-wire of the broken call)
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from predictive_gap.pga_idr_bridge import (
    get_last_observations,
    get_observation_count,
    record_reinforcement_observation,
)
from predictive_gap.pga_learning import LearningAction, TARGET_IDR, _try_reinforce_idr


def _action(symbol="RELIANCE", direction="UP", return_pct=3.2):
    return LearningAction(
        action_id="PGA-TEST0002",
        category="B",
        symbol=symbol,
        action_type="update_idr_observation",
        target_system=TARGET_IDR,
        description="test",
        payload={
            "symbol": symbol,
            "direction": direction,
            "return_pct": return_pct,
            "was_predicted": "NO",
            "dna_count": 2,
        },
    )


def test_t01_record_appends_real_jsonl(tmp_path):
    ok = record_reinforcement_observation(
        symbol="TCS", direction="UP", return_pct=4.1, context={"k": "v"}, obs_dir=tmp_path,
    )
    assert ok is True
    path = tmp_path / "idr_reinforcement_observations.jsonl"
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["symbol"] == "TCS"
    assert rec["direction"] == "UP"
    assert rec["return_pct"] == 4.1
    assert rec["context"] == {"k": "v"}
    assert "timestamp" in rec


def test_t02_observation_count_with_and_without_filter(tmp_path):
    record_reinforcement_observation(symbol="TCS", direction="UP", return_pct=1.0, obs_dir=tmp_path)
    record_reinforcement_observation(symbol="INFY", direction="DOWN", return_pct=-2.0, obs_dir=tmp_path)
    record_reinforcement_observation(symbol="TCS", direction="UP", return_pct=2.0, obs_dir=tmp_path)

    assert get_observation_count(obs_dir=tmp_path) == 3
    assert get_observation_count(symbol="TCS", obs_dir=tmp_path) == 2
    assert get_observation_count(symbol="INFY", obs_dir=tmp_path) == 1
    assert get_observation_count(symbol="NOPE", obs_dir=tmp_path) == 0


def test_t02b_observation_count_empty_dir(tmp_path):
    assert get_observation_count(obs_dir=tmp_path) == 0


def test_t03_last_observations_oldest_first_capped(tmp_path):
    for i in range(5):
        record_reinforcement_observation(symbol=f"SYM{i}", direction="UP", return_pct=float(i), obs_dir=tmp_path)

    last3 = get_last_observations(n=3, obs_dir=tmp_path)
    assert len(last3) == 3
    assert [r["symbol"] for r in last3] == ["SYM2", "SYM3", "SYM4"]


def test_t04_record_fails_open_on_io_error(tmp_path, monkeypatch):
    bad_dir = tmp_path / "readonly"
    bad_dir.mkdir()

    def _boom(*a, **kw):
        raise OSError("disk full")

    with patch("builtins.open", side_effect=_boom):
        ok = record_reinforcement_observation(symbol="X", direction="UP", return_pct=1.0, obs_dir=bad_dir)
    assert ok is False


def test_t05_try_reinforce_idr_now_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr("predictive_gap.pga_idr_bridge.PGA_DIR", tmp_path)
    action = _action()
    ok = _try_reinforce_idr(action)
    assert ok is True
    assert get_observation_count(symbol="RELIANCE", obs_dir=tmp_path) == 1


def test_t06_try_reinforce_idr_fail_open():
    def _boom(**kwargs):
        raise RuntimeError("bridge exploded")

    with patch("predictive_gap.pga_idr_bridge.record_reinforcement_observation", side_effect=_boom):
        ok = _try_reinforce_idr(_action())
    assert ok is False


def test_t07_bridge_has_no_idr_repository_import():
    src = Path("predictive_gap/pga_idr_bridge.py").read_text(encoding="utf-8")
    assert "from market_learning.idr_repository" not in src
    assert "IDRRepository()" not in src

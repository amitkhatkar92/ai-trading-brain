"""The invalid-trade correction removes exactly one trade, safely and only once."""
from __future__ import annotations

import json
import os

import pytest

from scripts.repairs import correct_invalid_exit_trade as fix

R = -5.9198216457235615
ORDER = "221261001665703"


def _performance() -> dict:
    return {
        "KDA_AUTHORITY": {
            "name": "KDA_AUTHORITY", "total_trades": 37, "wins": 11, "losses": 26,
            "total_r": -27.784383500189833, "win_r": 1.8363991163960565,
            "loss_r": 29.620782616585892, "consec_losses": 2, "enabled": False,
            "disabled_reason": "win_rate=30%<35%", "official_trades": 37,
            "prepared_universe_trades": 37,
            "last_trades": [-1.16, -0.52, R, -0.97, 1.5, -0.66],
        },
        "Mean_Reversion": {
            "name": "Mean_Reversion", "total_trades": 27, "wins": 8, "losses": 19,
            "total_r": -16.82, "win_r": 0.27, "loss_r": 17.09, "last_trades": [R + 1],
        },
    }


def _sizing(extra_matches: int = 0) -> list:
    rows = [json.dumps({"strategy": "KDA_AUTHORITY", "perf_weight": 1.0, "r_multiple": 0.0, "won": False}),
            json.dumps({"strategy": "KDA_AUTHORITY", "perf_weight": 0.5, "r_multiple": R, "won": False}),
            json.dumps({"strategy": "Mean_Reversion", "perf_weight": 0.5, "r_multiple": R, "won": False})]
    return rows + rows[1:2] * extra_matches


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "risk_control" / "sizing_calibration").mkdir(parents=True)
    (tmp_path / fix.PERFORMANCE_FILE).write_text(json.dumps(_performance()))
    (tmp_path / fix.SIZING_FILE).write_text("\n".join(_sizing()) + "\n")
    return str(tmp_path)


def test_correction_removes_exactly_one_losing_trade_and_keeps_totals_consistent():
    corrected = fix.correct_strategy_performance(_performance(), "KDA_AUTHORITY", R)
    entry = corrected["KDA_AUTHORITY"]
    assert (entry["total_trades"], entry["wins"], entry["losses"]) == (36, 11, 25)
    assert entry["total_r"] == pytest.approx(-27.784383500189833 + 5.9198216457235615)
    assert entry["loss_r"] == pytest.approx(29.620782616585892 - 5.9198216457235615)
    assert entry["total_r"] == pytest.approx(entry["win_r"] - entry["loss_r"])
    assert R not in entry["last_trades"] and len(entry["last_trades"]) == 5
    assert entry["official_trades"] == entry["prepared_universe_trades"] == 36
    assert entry["wins"] == 11 and entry["disabled_reason"] == "win_rate=30%<35%"


def test_other_strategies_and_the_input_are_untouched():
    original = _performance()
    corrected = fix.correct_strategy_performance(original, "KDA_AUTHORITY", R)
    assert corrected["Mean_Reversion"] == original["Mean_Reversion"]
    assert original == _performance()


@pytest.mark.parametrize("strategy,r", [("Nope", R), ("KDA_AUTHORITY", -9.99), ("KDA_AUTHORITY", 0.5)])
def test_unrecognised_or_unsafe_requests_are_refused(strategy, r):
    with pytest.raises(fix.CorrectionError):
        fix.correct_strategy_performance(_performance(), strategy, r)


def test_inconsistent_aggregates_are_refused_rather_than_made_worse():
    broken = _performance()
    broken["KDA_AUTHORITY"]["wins"] = 5
    with pytest.raises(fix.CorrectionError):
        fix.correct_strategy_performance(broken, "KDA_AUTHORITY", R)


def test_sizing_evidence_removes_only_the_matching_strategy_record():
    kept, removed = fix.filter_sizing_evidence(_sizing(), "KDA_AUTHORITY", R)
    assert removed == 1 and len(kept) == 2
    assert any("Mean_Reversion" in line for line in kept)


@pytest.mark.parametrize("extra", [1])
def test_sizing_evidence_refuses_when_the_match_is_not_unique(extra):
    with pytest.raises(fix.CorrectionError):
        fix.filter_sizing_evidence(_sizing(extra), "KDA_AUTHORITY", R)


def test_dry_run_changes_nothing(data_dir):
    before = open(os.path.join(data_dir, fix.PERFORMANCE_FILE)).read()
    result = fix.run(data_dir, ORDER, "KDA_AUTHORITY", R, "bad price", apply=False)
    assert result["status"] == "DRY_RUN" and result["total_trades"] == [37, 36]
    assert open(os.path.join(data_dir, fix.PERFORMANCE_FILE)).read() == before
    assert not os.path.exists(os.path.join(data_dir, fix.AUDIT_FILE))


def test_apply_backs_up_writes_audit_and_is_idempotent(data_dir):
    original = open(os.path.join(data_dir, fix.PERFORMANCE_FILE)).read()
    result = fix.run(data_dir, ORDER, "KDA_AUTHORITY", R, "exit booked at 819.05", apply=True)
    assert result["status"] == "APPLIED" and len(result["backups"]) == 2
    assert open(result["backups"][0]).read() == original
    corrected = json.load(open(os.path.join(data_dir, fix.PERFORMANCE_FILE)))
    assert corrected["KDA_AUTHORITY"]["total_trades"] == 36
    sizing = open(os.path.join(data_dir, fix.SIZING_FILE)).read().splitlines()
    assert len(sizing) == 2
    audit = json.loads(open(os.path.join(data_dir, fix.AUDIT_FILE)).read())
    assert audit["order_id"] == ORDER and audit["reason"] == "exit booked at 819.05"
    again = fix.run(data_dir, ORDER, "KDA_AUTHORITY", R, "exit booked at 819.05", apply=True)
    assert again["status"] == "ALREADY_APPLIED"
    assert json.load(open(os.path.join(data_dir, fix.PERFORMANCE_FILE)))["KDA_AUTHORITY"]["total_trades"] == 36


def test_a_refused_correction_writes_nothing(data_dir):
    with open(os.path.join(data_dir, fix.SIZING_FILE), "a") as handle:
        handle.write(_sizing()[1] + "\n")          # makes the sizing match non-unique
    before = open(os.path.join(data_dir, fix.PERFORMANCE_FILE)).read()
    with pytest.raises(fix.CorrectionError):
        fix.run(data_dir, ORDER, "KDA_AUTHORITY", R, "x", apply=True)
    assert open(os.path.join(data_dir, fix.PERFORMANCE_FILE)).read() == before
    assert not os.path.exists(os.path.join(data_dir, fix.AUDIT_FILE))


def test_command_line_reports_refusal_with_a_nonzero_exit(data_dir, capsys):
    code = fix.main(["--data-dir", data_dir, "--order-id", ORDER, "--strategy", "KDA_AUTHORITY",
                     "--r-multiple", "-9.99", "--reason", "x"])
    assert code == 2 and "REFUSED" in capsys.readouterr().err

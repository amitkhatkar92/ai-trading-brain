"""Options observation: BANKNIFTY (monthly expiries only) fell back to a synthetic chain because the
expiry closest to the 20-day target was 5 days out, and funds-blocked structures were registered
for virtual marking with an empty expiry because the metadata key is "expiry", not "expiry_date"."""
from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from data_feeds import dhan_feed
from data_feeds.dhan_feed import DhanFeed, _safe_dte


def _iso(days):
    return (date.today() + timedelta(days=days)).isoformat()


def _selected_expiry(available_days, dte_target):
    feed = DhanFeed.__new__(DhanFeed)
    feed._live = True
    feed._dhan_opt_attempts = 0
    feed._context = None
    feed._lookup = lambda symbol: {"security_id": "25", "segment": "IDX_I"}
    feed._dhan = MagicMock()
    feed._dhan.expiry_list.return_value = {"status": "success", "data": {"data": [_iso(d) for d in available_days]}}
    feed._dhan.option_chain.side_effect = RuntimeError("stop after expiry selection")
    try:
        feed.get_options_chain("BANKNIFTY", dte_target=dte_target)
    except Exception:
        pass
    call = feed._dhan.option_chain.call_args
    return call.kwargs.get("expiry") if call else None


def test_a_near_term_monthly_is_skipped_for_a_far_target_when_a_later_expiry_exists():
    assert _selected_expiry([5, 41, 68], dte_target=20) == _iso(41)


def test_selection_is_unchanged_when_the_closest_expiry_is_already_usable_or_the_target_is_short():
    assert _selected_expiry([5, 13, 20], dte_target=20) == _iso(20)
    assert _selected_expiry([5, 41], dte_target=5) == _iso(5)
    assert _selected_expiry([3, 4], dte_target=20) == _iso(4)          # nothing usable: keep the old behaviour


def test_safe_dte_handles_bad_input():
    assert _safe_dte(_iso(9), date.today()) == 9 and _safe_dte("not-a-date", date.today()) is None


def test_funds_blocked_structure_is_registered_with_its_expiry_so_it_can_be_priced():
    from orchestrator.master_orchestrator import MasterOrchestrator
    engine = MagicMock()
    signal = MagicMock()
    signal.symbol, signal.strategy_name, signal.entry_price = "NIFTY", "Iron_Condor_Range", 42.4
    signal.confidence, signal.stop_loss, signal.target_price = 8.3, 84.8, 10.6
    signal.direction.value, signal.expiry = "SELL", None
    signal.notes = json.dumps({
        "opportunity_id": "OPT-1", "expiry": "2026-12-08", "dte": 19, "spot": 25265.0, "lots": 2, "lot_size": 65,
        "is_live": True, "legs": [{"type": "CE", "strike": 25300.0, "direction": "SELL", "bid": 320.5, "ask": 322.2}]})
    snapshot = MagicMock()
    snapshot.regime.value = "range_market"
    orchestrator = MasterOrchestrator.__new__(MasterOrchestrator)
    with patch("knowledge_system.options_counterfactual_engine.get_options_counterfactual_engine", return_value=engine), \
         patch("knowledge_system.option_research_observer.observe_rejection"):
        orchestrator._register_options_counterfactual(signal, snapshot, "INSUFFICIENT_FUNDS: required=1 available=0")
    assert engine.register_rejection.call_args.kwargs["expiry_date"] == "2026-12-08"
    assert engine.register_rejection.call_args.kwargs["entry_quotes_live"] is True


def test_an_unfunded_options_account_is_logged_as_observation_only_not_as_an_error():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "execution_engine" / "options_order_manager.py").read_text(encoding="utf-8")
    assert "[ObservationOnly]" in source and source.index("[ObservationOnly]") < source.index("[LivePlacementFailed]")

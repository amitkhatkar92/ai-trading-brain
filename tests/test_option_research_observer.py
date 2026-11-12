"""No real orders, network requests or production research files in these tests."""
from datetime import timedelta
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from knowledge_system import option_research_observer as research


@pytest.fixture
def observer(tmp_path, monkeypatch):
    observer = research.OptionResearchObserver(tmp_path / "research.json")
    monkeypatch.setattr("models.transaction_costs.get_cost_model",
                        lambda: SimpleNamespace(compute=lambda **kw: SimpleNamespace(total_cost=1.0)))
    monkeypatch.setattr("data_feeds.dhan_fno_security_map.get_fno_security_map",
                        lambda: SimpleNamespace(get_lot_size=lambda symbol: 10))
    return observer


def contract(strike=100, bid=10, ask=12, kind="CE", expiry=None, **kw):
    fields = dict(strike=strike, bid=bid, ask=ask, option_type=kind, is_live=True,
                  expiry=expiry or research._now().date() + timedelta(days=10))
    fields.update(kw)
    return SimpleNamespace(**fields)


def chain(contracts=None, **kw):
    fields = dict(symbol="TEST", expiry=research._now().date() + timedelta(days=10),
                  is_live=True, fetched_at=research._now(), data_source="DHAN")
    fields.update(kw)
    contracts = contracts or [contract(expiry=fields["expiry"])]
    calls = [c for c in contracts if c.option_type == "CE"]
    puts = [c for c in contracts if c.option_type == "PE"]
    return SimpleNamespace(**fields, calls=calls, puts=puts,
                           atm_call=lambda: calls[0] if calls else None,
                           atm_put=lambda: puts[0] if puts else None)


def record(**kw):
    fields = dict(order_id="E1", symbol="TEST", direction="BUY", fill_status="FILLED",
                  actual_fill_price=100, filled_quantity=2, placed_at=research._now())
    fields.update(kw)
    return SimpleNamespace(**fields)


def signal(legs=None, **overrides):
    meta = dict(
        opportunity_id="O1", lot_size=10, lots=1,
        _research_contract=dict(expiry=(research._now().date() + timedelta(days=10)).isoformat(),
                                fetched_at=research._now().isoformat(), is_live=True, source="DHAN"),
        legs=legs or [
            dict(type="CE", strike=100, direction="SELL", bid=100, ask=102),
            dict(type="CE", strike=110, direction="BUY", bid=50, ask=52),
        ],
    )
    meta.update(overrides)
    return SimpleNamespace(symbol="TEST", strategy_name="Iron_Condor_Range",
                           notes=json.dumps(meta), stop_loss=100, target_price=8)


def only(observer):
    return next(iter(observer.snapshot().values()))


def test_stock_entry_exit_prices_original_option_and_records_both_returns(observer, monkeypatch):
    monkeypatch.setattr(research, "_chain", lambda *args: chain())
    rec = record()
    observer.record_equity_entry(rec)
    observer.process_events()
    assert only(observer)["legs"][0]["entry_price"] == 12
    observer.record_equity_exit(rec, 110, "TARGET_HIT")
    calls = []

    def exit_chain(symbol, expiry):
        calls.append(expiry)
        return chain([contract(bid=18, ask=20)])

    monkeypatch.setattr(research, "_chain", exit_chain)
    observer.process_events()
    row = only(observer)
    assert calls == [row["expiry"]]
    assert row["status"] == "CLOSED"
    assert row["stock_return_pct"] == pytest.approx(10)
    assert row["option_return_pct"] == pytest.approx(50)
    assert row["stock_gross_pnl"] == 20
    assert row["gross_pnl"] == 60
    assert row["net_pnl"] == 59
    assert row["legs"][0]["strike"] == 100


def test_short_stock_uses_put_and_directional_stock_return(observer, monkeypatch):
    monkeypatch.setattr(research, "_chain", lambda *args: chain([contract(kind="PE")]))
    rec = record(direction="SHORT")
    observer.record_equity_entry(rec)
    observer.process_events()
    observer.record_equity_exit(rec, 90, "TARGET_HIT")
    observer.process_events()
    assert only(observer)["legs"][0]["type"] == "PE"
    assert only(observer)["stock_return_pct"] == pytest.approx(10)


@pytest.mark.parametrize("fill_status", ["PENDING", "UNRESOLVED", "PAPER", "SIM", "REJECTED"])
def test_non_fills_do_not_create_stock_comparison(observer, fill_status):
    observer.record_equity_entry(record(fill_status=fill_status))
    assert observer.snapshot() == {}


def test_equity_entry_and_exit_dedup_and_restart(observer, monkeypatch):
    rec = record()
    monkeypatch.setattr(research, "_chain", lambda *args: chain())
    observer.record_equity_entry(rec)
    observer.record_equity_entry(rec)
    restored = research.OptionResearchObserver(observer.path)
    restored.process_events()
    restored.record_equity_exit(rec, 102, "EARLY_LOSS")
    restored.record_equity_exit(rec, 999, "DUPLICATE")
    restored.process_events()
    assert len(restored.snapshot()) == 1
    assert only(restored)["stock_exit"] == 102
    assert only(restored)["status"] == "CLOSED"


def test_close_arriving_during_entry_fetch_is_not_lost(observer, monkeypatch):
    rec = record()
    observer.record_equity_entry(rec)

    def delayed_entry(*args):
        observer.record_equity_exit(rec, 102, "EARLY_LOSS")
        return chain()

    monkeypatch.setattr(research, "_chain", delayed_entry)
    observer.process_events()
    assert only(observer)["status"] == "EXIT_PENDING"
    monkeypatch.setattr(research, "_chain", lambda *args: chain())
    observer.process_events()
    assert only(observer)["status"] == "CLOSED"


def test_historical_entry_cannot_be_reconstructed(observer):
    observer.record_equity_entry(record(placed_at=research._now() - timedelta(days=1)))
    assert only(observer)["status"] == "ENTRY_UNAVAILABLE"


@pytest.mark.parametrize("bad_chain", [
    lambda: chain(is_live=False),
    lambda: chain(fetched_at=research._now() - timedelta(minutes=6)),
    lambda: chain([contract(bid=0)]),
    lambda: chain([contract(is_live=False)]),
])
def test_unusable_entry_quotes_never_invent_pnl(observer, monkeypatch, bad_chain):
    monkeypatch.setattr(research, "_chain", lambda *args: bad_chain())
    # Synthetic chain validation also occurs in the real _chain wrapper.
    if not bad_chain().is_live:
        monkeypatch.setattr(research, "_chain", lambda *args: (_ for _ in ()).throw(ValueError("synthetic")))
    observer.record_equity_entry(record())
    observer.process_events()
    row = only(observer)
    assert row["status"] == "ENTRY_UNAVAILABLE"
    assert "net_pnl" not in row


def test_missing_original_exit_strike_never_selects_new_atm(observer, monkeypatch):
    monkeypatch.setattr(research, "_chain", lambda *args: chain())
    observer.record_equity_entry(record())
    observer.process_events()
    observer.record_equity_exit(record(), 110, "TARGET_HIT")
    monkeypatch.setattr(research, "_chain", lambda *args: chain([contract(strike=110)]))
    observer.process_events()
    assert only(observer)["status"] == "EXIT_UNAVAILABLE"
    assert "net_pnl" not in only(observer)


def test_event_window_expired_never_uses_later_quote(observer, monkeypatch):
    observer.record_equity_entry(record())
    observer.rows["equity:E1"]["entry_at"] = (research._now() - timedelta(seconds=61)).isoformat()
    monkeypatch.setattr(research, "_chain", lambda *args: chain())
    observer.process_events()
    assert only(observer)["status"] == "ENTRY_UNAVAILABLE"


def test_rejected_credit_structure_combines_leg_cashflows_and_costs(observer, monkeypatch):
    observer.record_rejection(signal(), "INSUFFICIENT_FUNDS")
    monkeypatch.setattr(research, "_chain",
                        lambda *args: chain([contract(bid=70, ask=72),
                                            contract(strike=110, bid=65, ask=67)]))
    observer.refresh()
    row = only(observer)
    assert row["status"] == "CLOSED"
    assert row["close_reason"] == "TARGET_HIT"
    assert row["is_credit"]
    assert row["gross_pnl"] == 410
    assert row["net_pnl"] == 408
    assert [leg["gross_pnl"] for leg in row["legs"]] == [280, 130]
    assert sum(leg["net_pnl"] for leg in row["legs"]) == row["net_pnl"]


def test_rejected_debit_spread_is_not_classified_by_bearish_view(observer, monkeypatch):
    sig = signal([dict(type="PE", strike=100, direction="BUY", bid=10, ask=12),
                  dict(type="PE", strike=90, direction="SELL", bid=4, ask=5)])
    sig.strategy_name = "Bear_Put_Spread"
    sig.stop_loss, sig.target_price = 4, 16
    observer.record_rejection(sig, "OPTIONS_CAPITAL_CAPACITY_INSUFFICIENT")
    monkeypatch.setattr(research, "_chain",
                        lambda *args: chain([contract(kind="PE", bid=20, ask=21),
                                            contract(strike=90, kind="PE", bid=3, ask=4)]))
    observer.refresh()
    assert not only(observer)["is_credit"]
    assert only(observer)["close_reason"] == "TARGET_HIT"
    assert only(observer)["gross_pnl"] == 80


def test_same_structure_quote_changes_dedup_and_keep_first_entry(observer):
    observer.record_rejection(signal(), "INSUFFICIENT_FUNDS")
    changed = signal()
    meta = json.loads(changed.notes)
    meta["legs"][0]["bid"] = 200
    changed.notes = json.dumps(meta)
    observer.record_rejection(changed, "OPTIONS_POSITION_LIMIT")
    assert len(observer.snapshot()) == 1
    assert only(observer)["legs"][0]["entry_price"] == 100
    assert only(observer)["rejection_reasons"] == ["INSUFFICIENT_FUNDS", "OPTIONS_POSITION_LIMIT"]


def test_unpriced_rejection_does_not_block_a_later_quoted_proposal(observer):
    bad = signal()
    meta = json.loads(bad.notes)
    meta["_research_contract"]["is_live"] = False
    bad.notes = json.dumps(meta)
    observer.record_rejection(bad, "BUDGET")
    observer.record_rejection(signal(), "BUDGET")
    observer.record_rejection(signal(), "ANOTHER_REASON")
    assert sorted(row["status"] for row in observer.snapshot().values()) == ["ENTRY_UNAVAILABLE", "OPEN"]


@pytest.mark.parametrize("field,value", [("is_live", False), ("expiry", ""),
                                       ("fetched_at", "invalid")])
def test_invalid_rejection_still_recorded_but_unpriced(observer, field, value):
    sig = signal()
    meta = json.loads(sig.notes)
    meta["_research_contract"][field] = value
    sig.notes = json.dumps(meta)
    observer.record_rejection(sig, "BUDGET")
    assert only(observer)["status"] == "ENTRY_UNAVAILABLE"
    assert "net_pnl" not in only(observer)


def test_missing_mark_retries_then_expiry_is_explicit_unpriced(observer, monkeypatch):
    observer.record_rejection(signal(), "BUDGET")
    monkeypatch.setattr(research, "_chain", lambda *args: (_ for _ in ()).throw(ValueError("no chain")))
    observer.refresh()
    assert only(observer)["status"] == "OPEN"
    assert "net_pnl" not in only(observer)
    key = next(iter(observer.rows))
    observer.rows[key]["expiry"] = (research._now().date() - timedelta(days=1)).isoformat()
    observer.refresh()
    assert only(observer)["status"] == "EXIT_UNAVAILABLE"


def test_ratios_and_explicit_leg_quantities_preserved(observer):
    sig = signal([dict(type="CE", strike=100, direction="BUY", bid=10, ask=12, ratio=2),
                  dict(type="CE", strike=110, direction="SELL", bid=4, ask=5, quantity=30)])
    observer.record_rejection(sig, "BUDGET")
    assert [leg["quantity"] for leg in only(observer)["legs"]] == [20, 30]


def test_four_leg_hedge_kept_together_and_missing_leg_cannot_close(observer, monkeypatch):
    legs = [
        dict(type="CE", strike=100, direction="SELL", bid=100, ask=102),
        dict(type="CE", strike=110, direction="BUY", bid=50, ask=52),
        dict(type="PE", strike=90, direction="SELL", bid=100, ask=102),
        dict(type="PE", strike=80, direction="BUY", bid=50, ask=52),
    ]
    sig = signal(legs)
    observer.record_rejection(sig, "INSUFFICIENT_FUNDS")
    assert len(only(observer)["legs"]) == 4
    contracts = [contract(bid=70, ask=72), contract(strike=110, bid=65, ask=67),
                 contract(strike=90, kind="PE", bid=70, ask=72),
                 contract(strike=80, kind="PE", bid=65, ask=67)]
    monkeypatch.setattr(research, "_chain", lambda *args: chain(contracts[:-1]))
    observer.refresh()
    assert only(observer)["status"] == "OPEN"
    assert "net_pnl" not in only(observer)
    monkeypatch.setattr(research, "_chain", lambda *args: chain(contracts))
    # Liquidation cost 14/unit, beyond this setup's original target of 8.
    observer.rows[next(iter(observer.rows))]["target_premium"] = 16
    observer.refresh()
    row = only(observer)
    assert row["status"] == "CLOSED"
    assert len(row["legs"]) == 4
    assert row["gross_pnl"] == 820
    assert row["net_pnl"] == 816


@pytest.mark.parametrize("quantity", [0.5, 0, float("nan")])
def test_invalid_contract_quantities_cannot_create_virtual_pnl(observer, quantity):
    observer.record_rejection(signal(lot_size=quantity), "BUDGET")
    assert only(observer)["status"] == "ENTRY_UNAVAILABLE"
    assert "net_pnl" not in only(observer)


def test_dte_exit_uses_existing_engine_threshold(observer, monkeypatch):
    from execution_engine.options_order_manager import DTE_EXIT_DAYS
    sig = signal()
    meta = json.loads(sig.notes)
    meta["_research_contract"]["expiry"] = (research._now().date() + timedelta(days=DTE_EXIT_DAYS)).isoformat()
    sig.notes = json.dumps(meta)
    observer.record_rejection(sig, "BUDGET")
    expiry = research._now().date() + timedelta(days=DTE_EXIT_DAYS)
    monkeypatch.setattr(research, "_chain",
                        lambda *args: chain([contract(bid=98, ask=100, expiry=expiry),
                                            contract(strike=110, bid=52, ask=54, expiry=expiry)],
                                           expiry=expiry))
    observer.refresh()
    assert only(observer)["close_reason"] == "DTE_EXIT"


def test_bounded_round_robin_refresh(observer, monkeypatch):
    for i in range(research.MAX_REFRESH_ITEMS + 2):
        sig = signal()
        sig.symbol = f"TEST{i}"
        observer.record_rejection(sig, "BUDGET")
    visited = []

    def mark(row, event_at):
        visited.append(row["symbol"])
        row["liquidation_premium"] = 40

    monkeypatch.setattr(observer, "_mark", mark)
    observer.refresh()
    assert len(visited) == research.MAX_REFRESH_ITEMS
    observer.refresh()
    assert len(set(visited)) == research.MAX_REFRESH_ITEMS + 2


def test_corrupt_store_is_not_silently_overwritten(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        research.OptionResearchObserver(path)
    assert path.read_text() == "{"


def test_production_wrappers_suppress_test_file_and_network_side_effects(monkeypatch):
    getter = MagicMock()
    monkeypatch.setattr(research, "get_option_research_observer", getter)
    research.observe_equity_entry(record())
    research.observe_equity_exit(record(), 110, "TARGET_HIT")
    research.observe_rejection(signal(), "BUDGET")
    research.start_option_research()
    getter.assert_not_called()


def test_worker_starts_and_stops_without_orders(observer, monkeypatch):
    ran = research.threading.Event()
    monkeypatch.setattr(observer, "process_events", lambda: ran.set())
    monkeypatch.setattr(observer, "refresh", lambda: None)
    observer.start()
    try:
        assert ran.wait(timeout=2)
        assert observer._thread.is_alive()
    finally:
        observer.stop()
    assert not observer._thread.is_alive()


def test_exact_expiry_and_live_chain_guard(monkeypatch):
    feed = MagicMock()
    monkeypatch.setattr("data_feeds.options_feed.get_options_feed", lambda: feed)
    expiry = (research._now().date() + timedelta(days=10)).isoformat()
    feed.get_chain.return_value = chain(expiry=research._now().date() + timedelta(days=11))
    with pytest.raises(ValueError, match="exact expiry"):
        research._chain("TEST", expiry)
    feed.get_chain.return_value = chain(is_live=False)
    with pytest.raises(ValueError, match="live option"):
        research._chain("TEST", expiry)


def test_no_trading_or_learning_consumers_and_all_hooks_exist():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    source = (root / "knowledge_system" / "option_research_observer.py").read_text(encoding="utf-8")
    for forbidden in ("place_order(", "record_outcome(", "get_options_knowledge_store",
                      "knowledge_decision_authority", "approve_and_size("):
        assert forbidden not in source
    om = (root / "execution_engine" / "order_manager.py").read_text(encoding="utf-8")
    assert "observe_equity_entry(rec)" in om
    assert 'observe_equity_exit(rec, exit_price, "SESSION_EXPIRED")' in om
    assert "observe_equity_exit(rec, exit_price, reason)" in om
    hedge = (root / "knowledge_system" / "equity_hedge_shadow_engine.py").read_text(encoding="utf-8")
    assert "observe_rejection(signal, risk_engine.last_rejection_detail" in hedge
    assert "observe_rejection(signal, order_mgr.last_rejection_detail" in hedge

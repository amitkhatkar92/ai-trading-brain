"""Shadow-learning tests for options candidates that never reach execution."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from data_feeds.options_feed import OptionContract, OptionsChain
from knowledge_system.options_counterfactual_engine import (
    CounterfactualMonitor,
    OptionsCounterfactualEngine,
)


def _contract(strike: float, option_type: str, bid: float, ask: float) -> OptionContract:
    return OptionContract(
        strike=strike,
        expiry=date.today() + timedelta(days=10),
        option_type=option_type,
        premium=(bid + ask) / 2,
        bid=bid,
        ask=ask,
        iv=0.2,
        delta=0.5,
        gamma=0.001,
        theta=-1.0,
        vega=1.0,
        open_interest=1000,
        volume=1000,
        is_live=True,
    )


def _engine(tmp_path, monkeypatch) -> OptionsCounterfactualEngine:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "knowledge_system.options_counterfactual_engine._CF_PENDING_PATH",
        str(tmp_path / "options_cf_pending.json"),
    )
    return OptionsCounterfactualEngine()


def _register(
    engine: OptionsCounterfactualEngine,
    opportunity_id: str,
    symbol: str = "NIFTY",
) -> None:
    expiry = date.today() + timedelta(days=10)
    engine.register_rejection(
        opportunity_id=opportunity_id,
        symbol=symbol,
        strategy_name="Iron_Condor_Range",
        direction="SELL",
        rejection_reason="INSUFFICIENT_FUNDS",
        expected_pnl=0.0,
        expected_entry_price=48.0,
        dte=10,
        spot=22500.0,
        iv=0.2,
        iv_rank=60.0,
        regime="RANGE_MARKET",
        confidence=8.0,
        lots=1,
        lot_size=10,
        expiry_date=expiry.isoformat(),
        stop_premium=100.0,
        target_premium=8.0,
        entry_quotes_live=True,
        entry_quote_source="DHAN",
        legs=[
            {"strike": 22000, "type": "CE", "direction": "SELL", "bid": 100, "ask": 102},
            {"strike": 22100, "type": "CE", "direction": "BUY", "bid": 50, "ask": 52},
        ],
    )


def _exit_chain(
    is_live: bool = True,
    symbol: str = "NIFTY",
    short_bid: float = 70,
    short_ask: float = 72,
    long_bid: float = 65,
    long_ask: float = 67,
) -> OptionsChain:
    expiry = date.today() + timedelta(days=10)
    return OptionsChain(
        symbol=symbol,
        spot=22050.0,
        expiry=expiry,
        dte=10,
        calls=[
            _contract(22000, "CE", short_bid, short_ask),
            _contract(22100, "CE", long_bid, long_ask),
        ],
        puts=[],
        atm_iv=0.2,
        is_live=is_live,
        fetched_at=datetime.now(),
        data_source="DHAN" if is_live else "SYNTHETIC",
    )


def test_rejected_live_legs_close_as_cost_adjusted_virtual_trade(tmp_path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    _register(engine, "OPT-SHADOW-GOOD")
    feed = MagicMock()
    feed.get_chain.return_value = _exit_chain()
    with patch("data_feeds.options_feed.get_options_feed", return_value=feed):
        results = engine.run_analysis()

    assert len(results) == 1
    result = results[0]
    assert result.pnl_method == "LIVE_OPTION_QUOTES_NET_ESTIMATED_COSTS"
    assert result.gross_hypothetical_pnl == 410.0
    assert result.estimated_transaction_cost > 0
    assert result.hypothetical_pnl == round(
        result.gross_hypothetical_pnl - result.estimated_transaction_cost, 2
    )
    assert result.decision_grade == "GOOD"
    assert "fees" not in result.analysis_notes


def test_live_shadow_monitor_waits_for_live_chain_not_synthetic(tmp_path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    _register(engine, "OPT-SHADOW-WAIT")
    feed = MagicMock()
    feed.get_chain.return_value = _exit_chain(is_live=False)

    with patch("data_feeds.options_feed.get_options_feed", return_value=feed):
        results = engine.run_analysis()

    assert results == []
    monitor = engine._pending["OPT-SHADOW-WAIT"]
    assert not monitor.analysed
    assert monitor.pnl_method == "LIVE_OPTION_QUOTES_PENDING"
    assert monitor.hypothetical_pnl is None


def test_same_day_identical_shadow_structure_is_not_double_counted(tmp_path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    _register(engine, "OPT-SHADOW-FIRST")
    _register(engine, "OPT-SHADOW-DUPLICATE")

    assert engine.pending_count() == 1
    assert "OPT-SHADOW-FIRST" in engine._pending
    assert "OPT-SHADOW-DUPLICATE" not in engine._pending


def test_shadow_decision_grade_distinguishes_good_average_and_bad(tmp_path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    _register(engine, "OPT-SHADOW-AVERAGE")
    _register(engine, "OPT-SHADOW-BAD", symbol="BANKNIFTY")
    average = engine._pending["OPT-SHADOW-AVERAGE"]
    average.lot_size = 1
    average.target_premium = 48.0
    bad = engine._pending["OPT-SHADOW-BAD"]
    bad.lot_size = 1
    bad.stop_premium = 60.0

    def chain_for(symbol, dte_target):
        if symbol == "NIFTY":
            # Short leg earns 2 points, long leg loses 1: gross +1, below fees.
            return _exit_chain(short_bid=97, short_ask=98, long_bid=51, long_ask=52)
        return _exit_chain(short_bid=119, short_ask=120, long_bid=49, long_ask=50)

    feed = MagicMock()
    feed.get_chain.side_effect = chain_for
    with patch("data_feeds.options_feed.get_options_feed", return_value=feed):
        # Both monitors use the same underlying; dispatch exact quotes in call order.
        feed.get_chain.side_effect = [
            _exit_chain(short_bid=97, short_ask=98, long_bid=51, long_ask=52),
            _exit_chain(
                symbol="BANKNIFTY",
                short_bid=119,
                short_ask=120,
                long_bid=49,
                long_ask=50,
            ),
        ]
        results = engine.run_analysis()

    assert len(results) == 2
    by_id = {result.opportunity_id: result for result in results}
    assert by_id["OPT-SHADOW-AVERAGE"].decision_grade == "AVERAGE"
    assert by_id["OPT-SHADOW-AVERAGE"].gross_hypothetical_pnl > 0
    assert by_id["OPT-SHADOW-AVERAGE"].hypothetical_pnl <= 0
    assert by_id["OPT-SHADOW-BAD"].decision_grade == "BAD"
    assert by_id["OPT-SHADOW-BAD"].gross_hypothetical_pnl < 0


def test_underlying_estimate_is_not_inserted_into_knowledge_store():
    from knowledge_system.options_research_pipeline import OptionsResearchPipeline

    pipeline = OptionsResearchPipeline.__new__(OptionsResearchPipeline)
    estimated = CounterfactualMonitor(
        opportunity_id="OPT-ESTIMATE",
        symbol="NIFTY",
        strategy_name="Iron_Condor_Range",
        direction="SELL",
        rejection_reason="C4",
        expected_pnl=0.0,
        expected_entry_price=50.0,
        dte_at_rejection=10,
        monitor_until="2020-01-01",
        recorded_at="2020-01-01T10:00:00",
        analysed=True,
        hypothetical_pnl=25.0,
        rejection_classification="REJECTION_INCORRECT",
        pnl_method="UNDERLYING_DIRECTIONAL_ESTIMATE",
    )
    engine = MagicMock()
    engine.run_analysis.return_value = [estimated]
    store = MagicMock()
    with patch(
        "knowledge_system.options_counterfactual_engine.get_options_counterfactual_engine",
        return_value=engine,
    ), patch(
        "knowledge_system.options_knowledge_store.get_options_knowledge_store",
        return_value=store,
    ):
        pipeline._step_counterfactual()

    store.record_outcome.assert_not_called()


def test_quote_verified_win_and_loss_both_feed_options_knowledge():
    from knowledge_system.options_research_pipeline import OptionsResearchPipeline

    pipeline = OptionsResearchPipeline.__new__(OptionsResearchPipeline)
    results = [
        CounterfactualMonitor(
            opportunity_id=f"OPT-SHADOW-{pnl}",
            symbol="NIFTY",
            strategy_name="Iron_Condor_Range",
            direction="SELL",
            rejection_reason="INSUFFICIENT_FUNDS",
            expected_pnl=0.0,
            expected_entry_price=50.0,
            dte_at_rejection=10,
            monitor_until="2020-01-01",
            recorded_at="2020-01-01T10:00:00",
            analysed=True,
            hypothetical_pnl=pnl,
            rejection_classification="REJECTION_INCORRECT" if pnl > 0 else "REJECTION_CORRECT",
            pnl_method="LIVE_OPTION_QUOTES_NET_ESTIMATED_COSTS",
            iv_rank_at_rejection=60.0,
        )
        for pnl in (100.0, -50.0)
    ]
    engine = MagicMock()
    engine.run_analysis.return_value = results
    store = MagicMock()
    scorer = MagicMock()
    with patch(
        "knowledge_system.options_counterfactual_engine.get_options_counterfactual_engine",
        return_value=engine,
    ), patch(
        "knowledge_system.options_knowledge_store.get_options_knowledge_store",
        return_value=store,
    ), patch(
        "knowledge_system.options_feature_extractor.extract_features",
        return_value=SimpleNamespace(is_valid=True, regime_ivr_dte="RANGE|IVR_HIGH|DTE_WEEKLY"),
    ), patch(
        "learning_system.options_shadow_scorer.get_options_shadow_scorer",
        return_value=scorer,
    ):
        pipeline._step_counterfactual()

    assert [call.kwargs["pnl"] for call in store.record_outcome.call_args_list] == [100.0, -50.0]
    assert all(
        call.kwargs["feature_components"]["evidence_source"] == "LIVE_OPTION_QUOTES_SHADOW"
        for call in store.record_outcome.call_args_list
    )
    assert scorer.record_outcome.call_count == 2


def test_shadow_outcome_never_looks_like_a_real_executed_fill(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from learning_system.options_shadow_scorer import OptionsShadowScorer

    scorer = OptionsShadowScorer()
    with patch(
        "knowledge_system.options_knowledge_store.get_options_knowledge_store"
    ) as store:
        store.return_value.get_influence.return_value = (0.0, "OBSERVED")
        store.return_value.get_item.return_value = None
        scorer.record_decision(
            opportunity_id="OPT-SHADOW-NO-FILL",
            symbol="NIFTY",
            strategy_name="Iron_Condor_Range",
            context_key="RANGE|IVR_HIGH|DTE_MONTHLY",
            prod_confidence=8.0,
            prod_executed=False,
        )

    scorer.record_outcome(
        "OPT-SHADOW-NO-FILL",
        -125.0,
        outcome_source="SHADOW_LIVE_OPTION_QUOTES",
    )
    record = scorer.get_record("OPT-SHADOW-NO-FILL")
    stats = scorer.get_agreement_stats()

    assert record is not None
    assert record.actual_pnl is None
    assert record.shadow_pnl == -125.0
    assert record.prod_was_correct is None
    assert stats["executed_outcomes"] == 0
    assert stats["shadow_outcomes"] == 1


def test_knowledge_item_tracks_actual_and_shadow_sources_separately(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from knowledge_system.options_knowledge_store import OptionsKnowledgeStore

    store = OptionsKnowledgeStore()
    shadow_item = store.record_outcome(
        strategy_name="Iron_Condor_Range",
        context_key="RANGE|IVR_HIGH|DTE_MONTHLY",
        feature_components={"evidence_source": "LIVE_OPTION_QUOTES_SHADOW"},
        pnl=125.0,
        opportunity_id="OPT-SHADOW-001",
        evidence_source="SHADOW_LIVE_OPTION_QUOTES",
    )
    actual_item = store.record_outcome(
        strategy_name="Iron_Condor_Range",
        context_key="RANGE|IVR_HIGH|DTE_MONTHLY",
        feature_components={},
        pnl=-25.0,
        opportunity_id="OPT-ACTUAL-001",
    )

    assert shadow_item is actual_item
    assert actual_item.total_outcomes == 2
    assert actual_item.shadow_outcomes == 1
    assert actual_item.actual_outcomes == 1
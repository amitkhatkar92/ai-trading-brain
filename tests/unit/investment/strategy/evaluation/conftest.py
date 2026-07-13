"""tests/unit/investment/strategy/evaluation/conftest.py
Shared fixtures for evaluation engine tests.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import List

import pytest

from iios.investment.strategy.evaluation.trade import Trade
from iios.investment.strategy.evaluation.equity_curve import EquityCurve, EquityPoint
from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput


def _dt(days_offset: int) -> datetime:
    return datetime(2023, 1, 1, tzinfo=timezone.utc) + timedelta(days=days_offset)


def make_trade(
    i: int,
    pnl: float,
    pnl_pct: float = 0.01,
    holding: int = 3,
    symbol: str = "RELIANCE",
    entry_slip: float = 0.0,
    commission: float = 10.0,
) -> Trade:
    side = "LONG" if pnl >= 0 else "LONG"
    entry_price = 1000.0
    exit_price = entry_price + pnl / 10.0  # 10 shares
    return Trade(
        strategy_id="test-strat",
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=10.0,
        entry_time=_dt(i * (holding + 1)),
        exit_time=_dt(i * (holding + 1) + holding),
        gross_pnl=pnl + commission,
        commission=commission,
        net_pnl=pnl,
        pnl_pct=pnl_pct,
        entry_slippage=entry_slip,
        exit_slippage=entry_slip,
    )


def make_equity_curve(
    values: List[float], start_days: int = 0
) -> EquityCurve:
    pts = [
        EquityPoint(timestamp=_dt(start_days + i), value=v)
        for i, v in enumerate(values)
    ]
    return EquityCurve(pts)


def make_evaluation_input(
    n_trades: int = 50,
    win_rate: float = 0.55,
    avg_win: float = 200.0,
    avg_loss: float = -120.0,
    eq_values: List[float] | None = None,
) -> EvaluationInput:
    trades = []
    for i in range(n_trades):
        if (i / n_trades) < win_rate:
            trades.append(make_trade(i, avg_win, pnl_pct=0.02))
        else:
            trades.append(make_trade(i, avg_loss, pnl_pct=-0.012))

    if eq_values is None:
        # Build a mildly upward-drifting curve
        v = 100_000.0
        eq_values = []
        for t in trades:
            v += t.net_pnl
            eq_values.append(v)

    curve = make_equity_curve(eq_values)
    return EvaluationInput(
        strategy_id="test-strat",
        strategy_name="Test Strategy",
        trades=trades,
        equity_curve=curve,
        risk_free_rate=0.06,
    )

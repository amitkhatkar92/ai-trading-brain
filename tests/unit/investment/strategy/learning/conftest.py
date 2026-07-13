"""tests/unit/investment/strategy/learning/conftest.py
Shared fixtures for Learning Engine tests.
"""
import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation


def make_observation(
    sid:            str   = "s1",
    strategy_name:  str   = "TestStrategy",
    eval_score:     float = 70.0,
    sharpe:         float = 1.2,
    max_dd:         float = 0.12,
    win_rate:       float = 0.55,
    profit_factor:  float = 1.5,
    risk_score:     float = 35.0,
    vol_level:      str   = "normal",
    regime:         str   = "trending",
    opportunity_score: float = 60.0,
    portfolio_weight:  float = 0.05,
    portfolio_size:    int   = 10,
    risk_grade:        str   = "B",
    health_status:     str   = "healthy",
    trade_count:       int   = 20,
    winning_trades:    int   = 11,
    losing_trades:     int   = 9,
    avg_win:           float = 0.02,
    avg_loss:          float = 0.01,
    largest_win:       float = 0.05,
    largest_loss:      float = -0.03,
    annualized_return: float = 0.18,
    observed_at:       Optional[datetime] = None,
    asset_types:       Optional[List[str]] = None,
    sectors:           Optional[List[str]] = None,
    tags:              Optional[List[str]] = None,
) -> LearningObservation:
    """
    Factory for LearningObservation test instances.
    All parameters have sensible defaults for a healthy, profitable strategy.
    """
    return LearningObservation(
        strategy_id=sid,
        strategy_name=strategy_name,
        evaluation_score=eval_score,
        sharpe_ratio=sharpe,
        max_drawdown=max_dd,
        win_rate=win_rate,
        profit_factor=profit_factor,
        robustness_score=65.0,
        confidence_score=70.0,
        annualized_return=annualized_return,
        annualized_vol=0.14,
        opportunity_score=opportunity_score,
        portfolio_weight=portfolio_weight,
        portfolio_size=portfolio_size,
        risk_score=risk_score,
        risk_grade=risk_grade,
        health_status=health_status,
        current_regime=regime,
        current_volatility_level=vol_level,
        market_liquidity="high",
        asset_types=asset_types or ["equity"],
        sectors=sectors or ["technology"],
        tags=tags or ["momentum"],
        supported_regimes=["trending", "volatile"],
        supported_timeframes=["1d", "1h"],
        trade_count=trade_count,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        avg_win_size=avg_win,
        avg_loss_size=avg_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
        observed_at=observed_at or datetime.now(timezone.utc),
    )


def make_observations_series(
    sid:   str = "s1",
    n:     int = 20,
    score: float = 70.0,
    jitter: float = 5.0,
    regime: str = "trending",
) -> List[LearningObservation]:
    """
    Build a sequence of observations with slight jitter, spaced 1 day apart.
    """
    base_time = datetime.now(timezone.utc) - timedelta(days=n)
    obs = []
    import math
    for i in range(n):
        # Sine jitter so some observations are above/below mean
        jit = jitter * math.sin(i * 0.5)
        obs.append(make_observation(
            sid=sid,
            eval_score=max(0.0, min(100.0, score + jit)),
            observed_at=base_time + timedelta(days=i),
            regime=regime,
        ))
    return obs


@pytest.fixture
def single_obs() -> LearningObservation:
    return make_observation()


@pytest.fixture
def obs_series_10() -> List[LearningObservation]:
    return make_observations_series(n=10)


@pytest.fixture
def obs_series_20() -> List[LearningObservation]:
    return make_observations_series(n=20)


@pytest.fixture
def obs_series_50() -> List[LearningObservation]:
    return make_observations_series(n=50)


@pytest.fixture
def degraded_obs_series() -> List[LearningObservation]:
    """20 observations: first 10 good (75), last 10 degraded (40)."""
    base_time = datetime.now(timezone.utc) - timedelta(days=20)
    return [
        make_observation(
            sid="s_deg",
            eval_score=75.0 if i < 10 else 40.0,
            risk_score=30.0 if i < 10 else 65.0,
            sharpe=1.5 if i < 10 else 0.4,
            observed_at=base_time + timedelta(days=i),
        )
        for i in range(20)
    ]


@pytest.fixture
def mixed_regime_series() -> List[LearningObservation]:
    """30 observations across 3 regimes."""
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    regimes = ["trending", "volatile", "ranging"]
    return [
        make_observation(
            sid="s_regime",
            eval_score=80.0 if regimes[i % 3] == "trending" else 50.0,
            regime=regimes[i % 3],
            observed_at=base_time + timedelta(days=i),
        )
        for i in range(30)
    ]

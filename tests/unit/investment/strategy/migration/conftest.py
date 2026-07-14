"""Shared fixtures for migration framework tests."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from iios.investment.strategy.migration.legacy_metadata import (
    EntryCondition,
    LegacyHealthStatus,
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
)
from iios.investment.strategy.migration.behavior_validator import BehaviorTestCase


def _make_metadata(
    name:              str                  = "Test_Breakout",
    strategy_id:       str                  = "test-id-001",
    source:            LegacyStrategySource = LegacyStrategySource.STRATEGY_GENERATOR,
    strategy_type:     LegacyStrategyType   = LegacyStrategyType.CODE_BASED,
    min_rr:            float                = 2.0,
    max_loss_pct:      float                = 0.02,
    stop_loss_pct:     float                = 0.015,
    target_multiplier: float                = 2.0,
    category:          str                  = "breakout",
    direction:         str                  = "BUY",
    is_approved:       bool                 = True,
    entry_conditions:  list                 = None,
    preferred_regimes: list                 = None,
    precision:         float | None         = 0.62,
    sharpe_ratio:      float | None         = 1.1,
    max_drawdown:      float | None         = 0.08,
) -> LegacyStrategyMetadata:
    return LegacyStrategyMetadata(
        strategy_id=strategy_id,
        strategy_name=name,
        source=source,
        strategy_type=strategy_type,
        min_rr=min_rr,
        max_loss_pct=max_loss_pct,
        stop_loss_pct=stop_loss_pct,
        target_multiplier=target_multiplier,
        base_strategy="",
        category=category,
        direction=direction,
        precision=precision,
        support=50,
        sharpe_ratio=sharpe_ratio,
        oos_win_rate=0.55,
        avg_return_r=1.8,
        max_drawdown=max_drawdown,
        composite_score=0.70,
        expectancy_r=0.9,
        preferred_regimes=preferred_regimes or ["bull_trend"],
        compatible_regimes=["bull_trend", "range_market"],
        entry_conditions=entry_conditions or [],
        health_status=LegacyHealthStatus.ACTIVE,
        is_approved=is_approved,
        live_trades=10,
        live_wins=6,
        description="Test strategy",
        pattern_id="",
        tags=["test"],
        discovered_at=datetime.now(timezone.utc),
        last_tested=datetime.now(timezone.utc),
        source_path="",
        raw_definition={},
    )


@pytest.fixture
def basic_metadata():
    return _make_metadata()


@pytest.fixture
def json_metadata():
    conds = [
        EntryCondition(feature="rsi", operator="<", threshold=30.0),
        EntryCondition(feature="volume_ratio", operator=">", threshold=1.5),
    ]
    return _make_metadata(
        name="Test_MeanRev",
        strategy_id="json-id-001",
        source=LegacyStrategySource.DISCOVERED_EDGES,
        strategy_type=LegacyStrategyType.JSON_BASED,
        entry_conditions=conds,
    )


@pytest.fixture
def invalid_metadata():
    return _make_metadata(min_rr=-1.0, max_loss_pct=0.0)


@pytest.fixture
def behavior_test_cases():
    """Standard test cases matching fixture metadata entry conditions."""
    return [
        BehaviorTestCase(
            test_id="tc-01",
            features={"rsi": 25.0, "volume_ratio": 2.0},
            expected_entry_result=True,
        ),
        BehaviorTestCase(
            test_id="tc-02",
            features={"rsi": 50.0, "volume_ratio": 0.8},
            expected_entry_result=False,
        ),
        BehaviorTestCase(
            test_id="tc-03",
            features={"rsi": 28.0, "volume_ratio": 1.2},
            expected_entry_result=False,
        ),
    ]

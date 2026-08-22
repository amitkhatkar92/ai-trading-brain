"""iios/investment/strategy/strategy_factory.py
Convenience factory for constructing strategy domain objects.
"""
from __future__ import annotations

from typing import Any

from iios.investment.strategy.strategy_constants import (
    AssetClass,
    MarketRegime,
    StrategyCategory,
    StrategyGrade,
    StrategyRecommendation,
    StrategyRiskLevel,
    StrategyStatus,
    StrategyTimeframe,
)
from iios.investment.strategy.strategy_intelligence import StrategyIntelligence
from iios.investment.strategy.core.strategy_definition import StrategyDefinition
from iios.investment.strategy.core.strategy_metadata import StrategyMetadata
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot
from iios.investment.strategy.evaluation.strategy_score import StrategyScore
from iios.investment.strategy.performance.performance_record import PerformanceRecord


class StrategyFactory:
    """Stateless factory — all methods are static."""

    @staticmethod
    def make_definition(
        strategy_id:   str,
        name:          str,
        category:      StrategyCategory     = StrategyCategory.UNKNOWN,
        asset_class:   AssetClass           = AssetClass.UNKNOWN,
        timeframe:     StrategyTimeframe    = StrategyTimeframe.UNKNOWN,
        risk_level:    StrategyRiskLevel    = StrategyRiskLevel.UNKNOWN,
        description:   str                  = "",
        author:        str                  = "",
        parameters:    dict[str, Any]       | None = None,
        preferred_regimes: list[MarketRegime] | None = None,
        **kwargs: Any,
    ) -> StrategyDefinition:
        return StrategyDefinition(
            strategy_id       = strategy_id,
            name              = name,
            category          = category,
            asset_class       = asset_class,
            timeframe         = timeframe,
            risk_level        = risk_level,
            description       = description,
            author            = author,
            parameters        = parameters or {},
            preferred_regimes = preferred_regimes or [],
            min_holding_days  = int(kwargs.get("min_holding_days", 1)),
            max_holding_days  = int(kwargs.get("max_holding_days", 30)),
            tags              = list(kwargs.get("tags", [])),
            version           = str(kwargs.get("version", "1.0.0")),
        )

    @staticmethod
    def make_metadata(
        strategy_id: str,
        display_name: str = "",
        description:  str = "",
        author:       str = "",
        **kwargs: Any,
    ) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_id  = strategy_id,
            display_name = display_name,
            description  = description,
            author       = author,
            tags         = list(kwargs.get("tags", [])),
            notes        = list(kwargs.get("notes", [])),
        )

    @staticmethod
    def make_profile(
        definition: StrategyDefinition,
        metadata:   StrategyMetadata | None = None,
    ) -> StrategyProfile:
        if metadata is None:
            metadata = StrategyMetadata(
                strategy_id  = definition.strategy_id,
                display_name = definition.name,
                description  = definition.description,
                author       = definition.author,
                tags         = list(definition.tags),
            )
        return StrategyProfile(
            strategy_id      = definition.strategy_id,
            definition       = definition,
            meta             = metadata,
            lifecycle_status = definition.initial_status,
        )

    @staticmethod
    def make_snapshot(
        strategy_id: str,
        status:      StrategyStatus = StrategyStatus.DRAFT,
        **kwargs: Any,
    ) -> StrategySnapshot:
        return StrategySnapshot(
            strategy_id   = strategy_id,
            status        = status,
            win_rate      = kwargs.get("win_rate"),
            sharpe_ratio  = kwargs.get("sharpe_ratio"),
            max_drawdown  = kwargs.get("max_drawdown"),
            total_trades  = int(kwargs.get("total_trades", 0)),
            overall_score = kwargs.get("overall_score"),
            grade         = kwargs.get("grade", StrategyGrade.UNKNOWN),
            active_params = dict(kwargs.get("active_params", {})),
        )

    @staticmethod
    def make_performance_record(
        strategy_id: str,
        pnl:         float = 0.0,
        is_win:      bool  = False,
        **kwargs: Any,
    ) -> PerformanceRecord:
        return PerformanceRecord(
            strategy_id   = strategy_id,
            pnl           = pnl,
            is_win        = is_win,
            entry_price   = float(kwargs.get("entry_price", 0.0)),
            exit_price    = float(kwargs.get("exit_price", 0.0)),
            duration_days = float(kwargs.get("duration_days", 1.0)),
            symbol        = str(kwargs.get("symbol", "")),
        )

    @staticmethod
    def make_intelligence(
        strategy_id:   str,
        strategy_name: str         = "",
        score:         StrategyScore | None = None,
        **kwargs: Any,
    ) -> StrategyIntelligence:
        return StrategyIntelligence(
            strategy_id      = strategy_id,
            strategy_name    = strategy_name,
            score            = score or StrategyScore(strategy_id=strategy_id),
            category         = kwargs.get("category", StrategyCategory.UNKNOWN),
            status           = kwargs.get("status", StrategyStatus.UNKNOWN),
            recommendation   = kwargs.get("recommendation", StrategyRecommendation.UNKNOWN),
            grade            = kwargs.get("grade", StrategyGrade.UNKNOWN),
        )

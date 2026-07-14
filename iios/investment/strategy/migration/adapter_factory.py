"""iios/investment/strategy/migration/adapter_factory.py
Factory that creates the appropriate adapter for any legacy strategy.
"""
from __future__ import annotations

from typing import Dict, Optional, Type

from iios.investment.strategy.migration.legacy_metadata import (
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
)
from iios.investment.strategy.migration.strategy_adapter import (
    AdaptationMode,
    LegacyStrategyAdapter,
)
from iios.investment.strategy.migration.compatibility_layer import CompatibilityLayer


# ── Adaptation mode decision rules ────────────────────────────────────────────
def _choose_mode(metadata: LegacyStrategyMetadata) -> AdaptationMode:
    """
    Choose the most appropriate AdaptationMode for a legacy strategy.

    Rules (in priority order):
    1. JSON strategies with entry conditions → BEHAVIOR_DELEGATE (logic must be preserved exactly)
    2. Code-based strategies from STRATEGY_PARAMS → PARAMETER_BRIDGE (params only)
    3. Evolved strategies → FULL_WRAP (full wrapping with inherited params)
    4. Unknown/hybrid → FULL_WRAP
    """
    if (metadata.strategy_type in (LegacyStrategyType.JSON_BASED,
                                    LegacyStrategyType.PATTERN_ONLY)
            and metadata.entry_conditions):
        return AdaptationMode.BEHAVIOR_DELEGATE

    if metadata.source == LegacyStrategySource.STRATEGY_GENERATOR:
        return AdaptationMode.PARAMETER_BRIDGE

    if metadata.source == LegacyStrategySource.EVOLVED_STRATEGIES:
        return AdaptationMode.FULL_WRAP

    return AdaptationMode.FULL_WRAP


class AdapterFactory:
    """
    Creates LegacyStrategyAdapter instances from LegacyStrategyMetadata.

    Applies:
    - Compatibility gap filling (safe defaults for missing fields)
    - Mode selection based on strategy type
    - Parameter translation via CompatibilityLayer
    """

    def create(
        self,
        metadata:        LegacyStrategyMetadata,
        mode:            Optional[AdaptationMode] = None,
        strategy_id_override: Optional[str]       = None,
    ) -> LegacyStrategyAdapter:
        """
        Create a LegacyStrategyAdapter for the given metadata.

        Args:
            metadata: The legacy strategy metadata to adapt.
            mode: Override the automatically selected adaptation mode.
            strategy_id_override: Use a specific strategy ID instead of the default.

        Returns:
            A LegacyStrategyAdapter wrapping the legacy strategy.
        """
        chosen_mode = mode or _choose_mode(metadata)

        # Apply gap-filling defaults
        metadata = self._fill_gaps(metadata)

        return LegacyStrategyAdapter(
            metadata=metadata,
            adaptation_mode=chosen_mode,
            strategy_id=strategy_id_override,
        )

    def create_batch(
        self,
        strategies: list,
        mode:       Optional[AdaptationMode] = None,
    ) -> Dict[str, LegacyStrategyAdapter]:
        """Create adapters for multiple strategies. Returns name → adapter dict."""
        return {
            meta.strategy_name: self.create(meta, mode=mode)
            for meta in strategies
        }

    def describe_adaptation(self, metadata: LegacyStrategyMetadata) -> Dict:
        """Describe how a strategy would be adapted without creating the adapter."""
        mode = _choose_mode(metadata)
        gaps = CompatibilityLayer.check_interface_gaps(metadata)
        return {
            "strategy_name":    metadata.strategy_name,
            "source":           metadata.source.value,
            "type":             metadata.strategy_type.value,
            "chosen_mode":      mode.value,
            "interface_gaps":   gaps,
            "gap_count":        len(gaps),
            "can_adapt":        True,
        }

    @staticmethod
    def _fill_gaps(metadata: LegacyStrategyMetadata) -> LegacyStrategyMetadata:
        """
        Return a copy of metadata with sensible defaults for any missing fields.
        Never modifies the original.
        """
        from dataclasses import replace

        changes: Dict = {}

        if metadata.stop_loss_pct <= 0:
            changes["stop_loss_pct"] = metadata.max_loss_pct

        if metadata.target_multiplier <= 0:
            changes["target_multiplier"] = metadata.min_rr

        if not changes:
            return metadata

        return LegacyStrategyMetadata(
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            source=metadata.source,
            strategy_type=metadata.strategy_type,
            min_rr=metadata.min_rr,
            max_loss_pct=metadata.max_loss_pct,
            stop_loss_pct=changes.get("stop_loss_pct", metadata.stop_loss_pct),
            target_multiplier=changes.get("target_multiplier", metadata.target_multiplier),
            base_strategy=metadata.base_strategy,
            category=metadata.category,
            direction=metadata.direction,
            precision=metadata.precision,
            support=metadata.support,
            sharpe_ratio=metadata.sharpe_ratio,
            oos_win_rate=metadata.oos_win_rate,
            avg_return_r=metadata.avg_return_r,
            max_drawdown=metadata.max_drawdown,
            composite_score=metadata.composite_score,
            expectancy_r=metadata.expectancy_r,
            preferred_regimes=metadata.preferred_regimes,
            compatible_regimes=metadata.compatible_regimes,
            entry_conditions=metadata.entry_conditions,
            health_status=metadata.health_status,
            is_approved=metadata.is_approved,
            live_trades=metadata.live_trades,
            live_wins=metadata.live_wins,
            description=metadata.description,
            pattern_id=metadata.pattern_id,
            tags=metadata.tags,
            discovered_at=metadata.discovered_at,
            last_tested=metadata.last_tested,
            source_path=metadata.source_path,
            raw_definition=metadata.raw_definition,
        )

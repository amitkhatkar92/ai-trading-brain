"""iios/investment/market/integration/conflict_resolution.py
Deterministic resolution strategies for known conflict types.
Unresolvable conflicts are flagged for escalation.
"""
from __future__ import annotations

import logging
from typing import List

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import Conflict, ConflictSeverity, ConflictType

log = logging.getLogger(__name__)

# Resolution priority: higher-priority engine wins when signals conflict.
# Regime > Breadth > Trend > Sector > Opportunity
_AUTHORITY = {
    ConflictType.TREND_REGIME:       ("market_regime", "trend"),
    ConflictType.TREND_VOLATILITY:   ("volatility",    "trend"),
    ConflictType.BREADTH_SECTOR:     ("breadth",       "sector_rotation"),
    ConflictType.CORRELATION_REGIME: ("market_regime", "correlation"),
    ConflictType.OPPORTUNITY_RISK:   ("market_regime", "opportunity"),
    ConflictType.BREAKOUT_LIQUIDITY: ("volume_liquidity", "opportunity"),
    ConflictType.CROSS_ENGINE:       ("market_regime", "breadth"),
}

# Conflicts whose severity is LOW or MEDIUM can always be auto-resolved;
# HIGH and CRITICAL require explicit strategy.
_AUTO_RESOLVE_MAX = ConflictSeverity.MEDIUM


class ConflictResolver:
    """Attempts deterministic resolution; marks unresolvable conflicts."""

    def resolve(
        self,
        conflicts: List[Conflict],
        state:     AggregationState,
    ) -> List[Conflict]:
        for conflict in conflicts:
            self._try_resolve(conflict, state)
        return conflicts

    def _try_resolve(self, conflict: Conflict, state: AggregationState) -> None:
        authority = _AUTHORITY.get(conflict.conflict_type)
        if authority is None:
            conflict.resolution = "no resolution strategy; escalated"
            return

        authoritative_engine, subordinate_engine = authority

        # Low/medium conflicts: auto-resolve by deferring to authoritative engine
        severity_order = [
            ConflictSeverity.LOW, ConflictSeverity.MEDIUM,
            ConflictSeverity.HIGH, ConflictSeverity.CRITICAL,
        ]
        if severity_order.index(conflict.severity) <= severity_order.index(_AUTO_RESOLVE_MAX):
            conflict.resolved  = True
            conflict.resolution = (
                f"Auto-resolved: {authoritative_engine} takes precedence over "
                f"{subordinate_engine}"
            )
            return

        # HIGH: resolve with explicit state-based check
        if conflict.conflict_type is ConflictType.TREND_REGIME:
            self._resolve_trend_regime(conflict, state)
        elif conflict.conflict_type is ConflictType.CORRELATION_REGIME:
            self._resolve_correlation_regime(conflict, state)
        elif conflict.conflict_type is ConflictType.OPPORTUNITY_RISK:
            self._resolve_opportunity_risk(conflict, state)
        elif conflict.conflict_type is ConflictType.BREAKOUT_LIQUIDITY:
            self._resolve_breakout_liquidity(conflict, state)
        else:
            conflict.resolution = (
                f"Unresolved: {conflict.conflict_type.value} severity={conflict.severity.value}; "
                "escalated to oversight"
            )

    # ── resolution strategies ─────────────────────────────────────────────────

    @staticmethod
    def _resolve_trend_regime(conflict: Conflict, state: AggregationState) -> None:
        # Regime is authoritative.  If breadth corroborates regime → resolve.
        breadth_corroborates = (
            state.breadth_regime is not None
            and (
                (state.market_regime == "bear" and state.breadth_regime == "negative")
                or (state.market_regime == "bull" and state.breadth_regime == "positive")
            )
        )
        if breadth_corroborates:
            conflict.resolved   = True
            conflict.resolution = (
                f"Resolved: regime={state.market_regime} confirmed by breadth={state.breadth_regime}"
            )
        else:
            conflict.resolution = "Unresolved: breadth does not confirm regime; escalated"

    @staticmethod
    def _resolve_correlation_regime(conflict: Conflict, state: AggregationState) -> None:
        if state.correlation_regime == "crisis" and state.volatility_regime in ("elevated", "extreme"):
            conflict.resolved   = True
            conflict.resolution = (
                "Resolved: correlation crisis corroborated by elevated/extreme volatility; "
                "correlation regime overrides market regime label"
            )
        else:
            conflict.resolution = "Unresolved: cannot reconcile correlation vs regime; escalated"

    @staticmethod
    def _resolve_opportunity_risk(conflict: Conflict, state: AggregationState) -> None:
        if state.market_regime == "crisis":
            conflict.resolved   = True
            conflict.resolution = (
                "Resolved: crisis regime suppresses opportunity signals; "
                "downstream systems should ignore opportunities"
            )
        else:
            conflict.resolution = "Unresolved: opportunity vs risk cannot be auto-reconciled"

    @staticmethod
    def _resolve_breakout_liquidity(conflict: Conflict, state: AggregationState) -> None:
        if state.liquidity_regime == "crisis":
            conflict.resolved   = True
            conflict.resolution = (
                "Resolved: liquidity crisis invalidates breakout signals; "
                "do not execute breakout trades"
            )
        else:
            conflict.resolution = "Unresolved: partial liquidity constraint; escalated"

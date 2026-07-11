"""iios/investment/market/correlation/cross_asset_analysis.py
Cross-asset correlation analysis: detects anomalies and regime signals
by comparing current correlations against canonical intermarket expectations.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from iios.investment.market.correlation.models import (
    AssetClass,
    CorrelationMatrix,
    IntermarketAnalysis,
    IntermarketRelationship,
    MultiAssetSnapshot,
    PriceObservation,
    RelationshipType,
)
from iios.investment.market.correlation import market_relationship as mr


class CrossAssetAnalyzer:
    """
    Stateless per-bar cross-asset analysis.
    Builds an IntermarketAnalysis from the current CorrelationMatrix and
    the asset-class metadata from the MultiAssetSnapshot.
    """

    def analyze(
        self,
        matrix: CorrelationMatrix,
        snapshot: MultiAssetSnapshot,
    ) -> IntermarketAnalysis:
        asset_classes = {o.symbol: o.asset_class for o in snapshot.observations}

        relationships = self._build_relationships(matrix, asset_classes)
        anomalies = [r for r in relationships if not r.is_typical]

        # Risk-on/off proxy from equity-bond, equity-vol, equity-gold
        eq_bond, eq_vol, eq_gold = self._canonical_correlations(
            matrix, asset_classes
        )

        risk_on  = self._count_risk_on(relationships)
        risk_off = self._count_risk_off(relationships)
        fts      = mr._triple_flight_to_safety(eq_bond, eq_vol, eq_gold)

        return IntermarketAnalysis(
            relationships=relationships,
            anomalies=anomalies,
            risk_on_signals=risk_on,
            risk_off_signals=risk_off,
            flight_to_safety=fts,
            bar_index=matrix.bar_index,
            timestamp=matrix.timestamp,
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _build_relationships(
        self,
        matrix: CorrelationMatrix,
        asset_classes: Dict[str, str],
    ) -> List[IntermarketRelationship]:
        syms = matrix.symbols
        seen: set = set()
        result: List[IntermarketRelationship] = []

        for i, sa in enumerate(syms):
            for sb in syms[i + 1:]:
                ca = asset_classes.get(sa, AssetClass.UNKNOWN.value)
                cb = asset_classes.get(sb, AssetClass.UNKNOWN.value)
                pair_key = (min(ca, cb), max(ca, cb))
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                corr = matrix.get(sa, sb)
                if corr is None:
                    continue

                expected, desc = mr._get_canonical_entry(ca, cb)
                typical  = mr.is_typical_correlation(ca, cb, corr)
                anom     = mr.anomaly_score(ca, cb, corr)

                result.append(IntermarketRelationship(
                    asset_a=sa,
                    asset_b=sb,
                    asset_class_a=ca,
                    asset_class_b=cb,
                    expected_type=expected,
                    current_correlation=corr,
                    historical_avg=corr,   # no historical avg without long state
                    is_typical=typical,
                    anomaly_score=anom,
                    description=desc,
                ))
        return result

    def _canonical_correlations(
        self,
        matrix: CorrelationMatrix,
        asset_classes: Dict[str, str],
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Extract equity-bond, equity-vol, equity-gold correlations."""
        equity_syms  = [s for s, c in asset_classes.items()
                        if c in (AssetClass.EQUITY.value, AssetClass.INDEX.value)]
        bond_syms    = [s for s, c in asset_classes.items()
                        if c == AssetClass.BOND.value]
        vol_syms     = [s for s, c in asset_classes.items()
                        if c == AssetClass.VOLATILITY.value]
        gold_syms    = [s for s, c in asset_classes.items()
                        if c == AssetClass.PRECIOUS_METAL.value]

        eq_bond = self._avg_corr(matrix, equity_syms, bond_syms)
        eq_vol  = self._avg_corr(matrix, equity_syms, vol_syms)
        eq_gold = self._avg_corr(matrix, equity_syms, gold_syms)
        return eq_bond, eq_vol, eq_gold

    def _avg_corr(
        self,
        matrix: CorrelationMatrix,
        group_a: List[str],
        group_b: List[str],
    ) -> Optional[float]:
        vals = []
        for sa in group_a:
            for sb in group_b:
                v = matrix.get(sa, sb)
                if v is not None:
                    vals.append(v)
        return sum(vals) / len(vals) if vals else None

    def _count_risk_on(self, rels: List[IntermarketRelationship]) -> int:
        count = 0
        for r in rels:
            if (r.asset_class_a in (AssetClass.EQUITY.value, AssetClass.INDEX.value)
                    and r.asset_class_b == AssetClass.VOLATILITY.value
                    and r.current_correlation < -0.40):
                count += 1
            if (r.expected_type == RelationshipType.INVERSE
                    and not r.is_typical
                    and r.current_correlation > 0.30):
                # Inverse relationship going positive = anomaly toward risk-on
                count += 1
        return count

    def _count_risk_off(self, rels: List[IntermarketRelationship]) -> int:
        count = 0
        for r in rels:
            if (r.asset_class_a in (AssetClass.EQUITY.value, AssetClass.INDEX.value)
                    and r.asset_class_b == AssetClass.BOND.value
                    and r.current_correlation < -0.40):
                count += 1
            if (r.asset_class_a in (AssetClass.EQUITY.value, AssetClass.INDEX.value)
                    and r.asset_class_b == AssetClass.PRECIOUS_METAL.value
                    and r.current_correlation < -0.40):
                count += 1
        return count

"""iios/investment/company/business_quality/peer_comparison.py
Peer comparison — benchmarks this company against provided peer snapshots.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.company.business_quality.competitive_position import (
    PeerComparisonProfile, PeerMetric,
)
from iios.investment.company.business_quality.quality_statistics import (
    percentile_rank, safe_mean, clamp,
)


_COMPARE_FIELDS = [
    ("avg_roic",            "avg_roic"),
    ("avg_gross_margin",    "avg_gross_margin"),
    ("avg_net_margin",      "avg_net_margin"),
    ("avg_roe",             "avg_roe"),
]


class PeerComparisonAnalyzer:
    """
    Compares this company's profitability against a peer group.
    Peer snapshots are BusinessQualitySnapshot objects passed to the engine.
    """

    def analyze(
        self,
        ticker:         str,
        own_snapshot:   Any,             # BusinessQualitySnapshot
        peer_snapshots: List[Any],       # List[BusinessQualitySnapshot]
    ) -> PeerComparisonProfile:
        p = PeerComparisonProfile(
            peer_count   = len(peer_snapshots),
            peer_tickers = [ps.ticker for ps in peer_snapshots if hasattr(ps, "ticker")],
        )

        if not peer_snapshots:
            p.competitive_score_vs_peers = 50.0
            return p

        # ── Build own values ───────────────────────────────────────────────────
        own_prof = None
        peer_prof_list = []

        try:
            own_prof = own_snapshot.operational.capital_efficiency
        except Exception:
            pass

        for ps in peer_snapshots:
            try:
                peer_prof_list.append(ps.operational.capital_efficiency)
            except Exception:
                pass

        if own_prof is None or not peer_prof_list:
            p.competitive_score_vs_peers = 50.0
            return p

        # ── Rank on key metrics ────────────────────────────────────────────────
        ranks: List[float] = []
        metrics: List[PeerMetric] = []

        metric_attrs = [
            ("avg_roic",            "avg_roic"),
            ("avg_fcf_margin",      "avg_fcf_margin"),
            ("capital_efficiency_score", "capital_efficiency_score"),
        ]
        for label, attr in metric_attrs:
            own_val = getattr(own_prof, attr, None)
            peer_vals = [
                v for pp in peer_prof_list
                if (v := getattr(pp, attr, None)) is not None
            ]
            if own_val is None or not peer_vals:
                continue
            pct_rank = percentile_rank(own_val, peer_vals)
            peer_med = safe_mean(peer_vals)
            vs_med   = (
                (own_val - peer_med) / abs(peer_med) * 100
                if peer_med else None
            )
            metrics.append(PeerMetric(
                field_name=label,
                own_value=own_val,
                peer_median=peer_med,
                percentile=pct_rank,
                vs_median_pct=vs_med,
            ))
            ranks.append(pct_rank)

        p.metrics = metrics

        if ranks:
            avg_rank = sum(ranks) / len(ranks)
            p.profitability_rank  = avg_rank
            p.efficiency_rank     = avg_rank
            p.quality_rank        = avg_rank
            p.competitive_score_vs_peers = clamp(avg_rank)
        else:
            p.competitive_score_vs_peers = 50.0

        if p.competitive_score_vs_peers >= 75.0:
            p.flags.append("top_quartile_vs_peers")
        elif p.competitive_score_vs_peers < 25.0:
            p.flags.append("bottom_quartile_vs_peers")

        return p

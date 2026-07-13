"""iios/investment/company/ownership/insider_activity.py
Insider activity aggregation engine.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.investment.company.ownership.ownership_profile import (
    InsiderActivityProfile, InsiderActivityLabel,
)
from iios.investment.company.ownership.insider_transactions import build_transaction_log
from iios.investment.company.ownership.executive_trading import analyze_executive_trading
from iios.investment.company.ownership.director_trading import analyze_director_trading
from iios.investment.company.ownership.ownership_statistics import (
    clamp, score_insider_holding, score_insider_buying, pct_to_100,
)


class InsiderActivityEngine:
    """Aggregates executive and director insider activity into InsiderActivityProfile."""

    def compute(
        self,
        insider_data: Optional[Dict],
        management_snapshot: Any = None,   # Optional[ManagementSnapshot]
    ) -> InsiderActivityProfile:

        d = insider_data or {}
        profile = InsiderActivityProfile()
        expl: list[str] = []

        # ── Executive and director profiles ───────────────────────────────────
        exec_profile = analyze_executive_trading(d)
        dir_profile  = analyze_director_trading(d)

        # ── Build transaction log from raw transactions ───────────────────────
        tx_log = build_transaction_log(d.get("recent_transactions"))

        # ── Copy key fields ───────────────────────────────────────────────────
        profile.ceo_ownership_pct         = exec_profile.ceo_ownership_pct
        profile.cfo_ownership_pct         = exec_profile.cfo_ownership_pct
        profile.board_total_ownership_pct = dir_profile.board_total_ownership_pct
        profile.esop_outstanding_pct      = exec_profile.esop_outstanding_pct

        v = d.get("insider_ownership_pct")
        profile.insider_ownership_pct = pct_to_100(float(v)) if v is not None else None

        # ── Aggregate transaction data ─────────────────────────────────────────
        # Use transaction log if populated; fall back to summary counts in dict
        if tx_log.total_count > 0:
            profile.insider_buy_count_6m  = tx_log.buy_count
            profile.insider_sell_count_6m = tx_log.sell_count
            profile.net_insider_sentiment = _compute_sentiment(
                tx_log.buy_count, tx_log.sell_count, tx_log.net_buy_ratio
            )
        else:
            profile.insider_buy_count_6m  = int(d.get("insider_buy_count_6m") or 0)
            profile.insider_sell_count_6m = int(d.get("insider_sell_count_6m") or 0)
            net_raw = d.get("net_insider_buying_6m")
            if net_raw is not None:
                import math
                n = float(net_raw)
                ref = max(abs(n), 1000)
                profile.net_insider_sentiment = clamp(math.tanh(n / ref * 3) * 100, -100, 100)
            else:
                total = profile.insider_buy_count_6m + profile.insider_sell_count_6m
                if total > 0:
                    profile.net_insider_sentiment = (
                        profile.insider_buy_count_6m / total - 0.5
                    ) * 200
                else:
                    profile.net_insider_sentiment = 0.0

        # ── Activity label ────────────────────────────────────────────────────
        profile.insider_activity_label = _classify_activity(
            profile.net_insider_sentiment,
            profile.insider_buy_count_6m,
            profile.insider_sell_count_6m,
        )

        # ── Scores ────────────────────────────────────────────────────────────
        # Insider holding score: best available ownership figure
        best_ownership = (
            profile.insider_ownership_pct
            or profile.ceo_ownership_pct
            or exec_profile.ceo_ownership_pct
        )
        profile.insider_holding_score = score_insider_holding(best_ownership)

        profile.insider_buying_score = score_insider_buying(
            profile.insider_buy_count_6m,
            profile.insider_sell_count_6m,
            profile.net_insider_sentiment,
        )

        # Alignment score: combine exec alignment + director conviction + holding
        profile.alignment_score = clamp(
            exec_profile.exec_alignment_score * 0.50
            + dir_profile.board_conviction_score  * 0.30
            + profile.insider_holding_score       * 0.20
        )

        # Management governance cross-check
        if management_snapshot is not None:
            mgmt_q = getattr(management_snapshot, "management_quality", None)
            lts = getattr(mgmt_q, "long_term_orientation_score", None)
            if lts is not None and lts >= 70:
                profile.alignment_score = clamp(profile.alignment_score + 5.0)
                expl.append("Alignment boosted by strong long-term management orientation.")

        profile.explanation = expl
        return profile


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_sentiment(
    buy_count: int, sell_count: int, buy_ratio: float
) -> float:
    if buy_count == 0 and sell_count == 0:
        return 0.0
    return (buy_ratio - 0.5) * 200


def _classify_activity(
    sentiment: float,
    buy_count: int,
    sell_count: int,
) -> InsiderActivityLabel:
    if buy_count == 0 and sell_count == 0:
        return InsiderActivityLabel.UNKNOWN
    if sentiment >= 60:
        return InsiderActivityLabel.ACCUMULATING
    if sentiment >= 20:
        return InsiderActivityLabel.STEADY
    if sentiment >= -20:
        return InsiderActivityLabel.NEUTRAL
    if sentiment >= -60:
        return InsiderActivityLabel.DISTRIBUTING
    return InsiderActivityLabel.LIQUIDATING

"""
market_sentiment_engine.py — iios.market.analytics
====================================================
Market sentiment analysis sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List

from .constants import SentimentCategory
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import SentimentResult


class MarketSentimentEngine:
    """
    Stateless sentiment analysis sub-engine.

    Reads optional keys from ``breadth_data``, ``volatility_data``,
    and ``global_data`` to estimate a composite sentiment score.
    """

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> SentimentResult:
        bd  = request_data.get("breadth_data",    {})
        vd  = request_data.get("volatility_data", {})
        gd  = request_data.get("global_data",     {})

        put_call_ratio   = float(bd.get("put_call_ratio",      1.0))
        adv_pct          = float(bd.get("advancing_pct",       0.5))
        fear_greed_input = float(gd.get("fear_greed_index",    50.0))
        impl_vol         = float(vd.get("implied_vol",         0.15))

        # -------------- composite sentiment score 0..100 ----------------
        # Lower PCR = bullish sentiment (investors buying calls)
        pcr_score = max(0.0, min(100.0, (2.0 - put_call_ratio) / 2.0 * 100.0))
        adv_score = adv_pct * 100.0
        vol_score = max(0.0, min(100.0, (1.0 - impl_vol / 0.40) * 100.0))

        sentiment_score = (pcr_score + adv_score + fear_greed_input + vol_score) / 4.0
        sentiment_score = max(0.0, min(100.0, sentiment_score))

        # Institutional bias: positive = bullish tilt
        inst_bias = (adv_pct - 0.5) * 2.0

        category = self._categorise(sentiment_score)

        return SentimentResult(
            category          = category,
            sentiment_score   = sentiment_score,
            put_call_ratio    = put_call_ratio,
            fear_greed_index  = fear_greed_input,
            institutional_bias = inst_bias,
            description       = (
                f"Sentiment: {category.value} "
                f"(score={sentiment_score:.1f}, PCR={put_call_ratio:.2f})"
            ),
        )

    @staticmethod
    def _categorise(score: float) -> SentimentCategory:
        if score >= 80.0:
            return SentimentCategory.EXTREME_GREED
        if score >= 65.0:
            return SentimentCategory.GREED
        if score >= 40.0:
            return SentimentCategory.NEUTRAL
        if score >= 25.0:
            return SentimentCategory.FEAR
        return SentimentCategory.EXTREME_FEAR

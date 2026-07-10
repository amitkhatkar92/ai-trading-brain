"""iios/integration/news/sentiment/sentiment_statistics.py

Aggregated sentiment tracking across articles.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import SentimentLabel


@dataclass
class SentimentStatistics:
    stat_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    subject_id:    str   = ""       # ticker, sector, or "market"
    period_start:  float = 0.0
    period_end:    float = 0.0
    total_analyzed: int  = 0
    avg_score:     float = 0.0
    min_score:     float = 0.0
    max_score:     float = 0.0
    bullish_count: int   = 0
    bearish_count: int   = 0
    neutral_count: int   = 0
    unknown_count: int   = 0
    computed_at:   float = field(default_factory=time.time)
    metadata:      dict[str, Any] = field(default_factory=dict)

    # Accumulated for running average
    _total_score:  float = field(default=0.0, repr=False)

    def add_score(self, score: float, label: SentimentLabel) -> None:
        self.total_analyzed += 1
        self._total_score   += score
        self.avg_score       = self._total_score / self.total_analyzed
        if score < self.min_score or self.total_analyzed == 1:
            self.min_score = score
        if score > self.max_score or self.total_analyzed == 1:
            self.max_score = score
        match label:
            case SentimentLabel.BULLISH | SentimentLabel.VERY_BULLISH:
                self.bullish_count += 1
            case SentimentLabel.BEARISH | SentimentLabel.VERY_BEARISH:
                self.bearish_count += 1
            case SentimentLabel.NEUTRAL:
                self.neutral_count += 1
            case _:
                self.unknown_count += 1

    def sentiment_ratio(self) -> float:
        """
        Returns bullish / (bullish + bearish) in [0, 1].
        Returns 0.5 if neither is non-zero.
        """
        total = self.bullish_count + self.bearish_count
        return self.bullish_count / total if total > 0 else 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat_id":        self.stat_id,
            "subject_id":     self.subject_id,
            "total_analyzed": self.total_analyzed,
            "avg_score":      round(self.avg_score, 4),
            "bullish":        self.bullish_count,
            "bearish":        self.bearish_count,
            "neutral":        self.neutral_count,
            "ratio":          round(self.sentiment_ratio(), 4),
            "computed_at":    self.computed_at,
        }

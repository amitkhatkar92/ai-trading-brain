"""iios/integration/news/sentiment/sentiment_result.py

Result object from a sentiment analysis run.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import SentimentLabel, SentimentScope


@dataclass
class SentimentResult:
    """
    Sentiment analysis output for one subject (article, company, sector, etc.)
    """

    result_id:   str            = field(default_factory=lambda: str(uuid.uuid4()))
    analyzer_id: str            = ""      # which SentimentProvider produced this
    scope:       SentimentScope = SentimentScope.NEWS
    subject_id:  str            = ""      # article_id / ticker / sector

    # Core result
    score:       float          = 0.0     # [-1.0, +1.0]
    label:       SentimentLabel = SentimentLabel.UNKNOWN
    confidence:  float          = 0.0     # [0.0, 1.0]

    # Breakdown (optional — provided by some analyzers)
    positive:    float          = 0.0
    negative:    float          = 0.0
    neutral:     float          = 0.0

    # Source span (optional — for explainability)
    excerpt:     str            = ""
    keywords:    list[str]      = field(default_factory=list)

    analyzed_at: float          = field(default_factory=time.time)
    metadata:    dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.label == SentimentLabel.UNKNOWN and self.score != 0.0:
            self.label = self._score_to_label(self.score)

    @staticmethod
    def _score_to_label(score: float) -> SentimentLabel:
        if score >= 0.5:
            return SentimentLabel.VERY_BULLISH
        if score >= 0.1:
            return SentimentLabel.BULLISH
        if score <= -0.5:
            return SentimentLabel.VERY_BEARISH
        if score <= -0.1:
            return SentimentLabel.BEARISH
        return SentimentLabel.NEUTRAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":   self.result_id,
            "analyzer_id": self.analyzer_id,
            "scope":       self.scope.value,
            "subject_id":  self.subject_id,
            "score":       round(self.score, 4),
            "label":       self.label.value,
            "confidence":  round(self.confidence, 4),
            "analyzed_at": self.analyzed_at,
        }

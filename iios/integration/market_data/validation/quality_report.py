"""iios/integration/market_data/validation/quality_report.py

Data quality report produced by the validation pipeline.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.market_data.market_data_constants import AnomalyType


@dataclass
class QualityIssue:
    anomaly_type: AnomalyType = AnomalyType.PRICE_SPIKE
    symbol:       str         = ""
    field_name:   str         = ""
    message:      str         = ""
    severity:     str         = "warning"   # "info" | "warning" | "error"
    value:        Any         = None


@dataclass
class QualityReport:
    """
    Aggregated data quality assessment.
    Produced per-batch or per-provider summary window.
    """

    report_id:       str               = field(default_factory=lambda: str(uuid.uuid4()))
    provider_id:     str               = ""
    symbol:          str               = ""
    period_start:    float             = 0.0
    period_end:      float             = 0.0

    total_records:   int               = 0
    valid_records:   int               = 0
    invalid_records: int               = 0
    duplicate_count: int               = 0
    gap_count:       int               = 0
    anomaly_count:   int               = 0

    issues:          list[QualityIssue] = field(default_factory=list)
    quality_score:   float             = 1.0    # [0.0 – 1.0]
    generated_at:    float             = field(default_factory=time.time)

    def add_issue(self, issue: QualityIssue) -> None:
        self.issues.append(issue)
        if issue.anomaly_type == AnomalyType.DUPLICATE:
            self.duplicate_count += 1
        elif issue.anomaly_type == AnomalyType.GAP_IN_SERIES:
            self.gap_count += 1
        else:
            self.anomaly_count += 1

    def compute_score(self) -> float:
        """
        Score = valid / total.  Deduct 0.01 per anomaly (capped at 50%).
        """
        if self.total_records == 0:
            self.quality_score = 1.0
            return self.quality_score
        base = self.valid_records / self.total_records
        penalty = min(0.5, self.anomaly_count * 0.01)
        self.quality_score = max(0.0, base - penalty)
        return self.quality_score

    def is_acceptable(self, min_score: float = 0.70) -> bool:
        return self.quality_score >= min_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":       self.report_id,
            "provider_id":     self.provider_id,
            "symbol":          self.symbol,
            "total_records":   self.total_records,
            "valid_records":   self.valid_records,
            "invalid_records": self.invalid_records,
            "duplicate_count": self.duplicate_count,
            "gap_count":       self.gap_count,
            "anomaly_count":   self.anomaly_count,
            "quality_score":   round(self.quality_score, 4),
            "issue_count":     len(self.issues),
            "generated_at":    self.generated_at,
        }

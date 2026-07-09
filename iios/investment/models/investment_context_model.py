"""iios/investment/models/investment_context_model.py
InvestmentContext — accumulator passed through the workflow pipeline.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.investment_constants import AssetClass, IntelligenceType


@dataclass
class InvestmentContext:
    """
    Mutable context object passed between workflow stages.

    Domain engines write their partial results here so that later
    stages can consume them without re-fetching.
    """

    context_id:           str                   = field(default_factory=lambda: str(uuid.uuid4()))
    session_id:           str                   = ""
    request_id:           str                   = ""
    asset_class:          AssetClass            = AssetClass.EQUITY
    symbols:              list[str]             = field(default_factory=list)
    intelligence_results: dict[str, Any]        = field(default_factory=dict)
    metadata:             dict                  = field(default_factory=dict)
    created_at:           float                 = field(default_factory=time.time)

    def set_result(self, intelligence_type: IntelligenceType, value: Any) -> None:
        self.intelligence_results[intelligence_type.value] = value

    def get_result(self, intelligence_type: IntelligenceType, default: Any = None) -> Any:
        return self.intelligence_results.get(intelligence_type.value, default)

    def to_dict(self) -> dict:
        return {
            "context_id":           self.context_id,
            "session_id":           self.session_id,
            "request_id":           self.request_id,
            "asset_class":          self.asset_class.value,
            "symbols":              self.symbols,
            "intelligence_results": {k: str(v) for k, v in self.intelligence_results.items()},
            "created_at":           self.created_at,
        }

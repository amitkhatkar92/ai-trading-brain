"""iios/investment/company/models/company_signal.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class CompanySignalType:
    FINANCIAL        = "financial"
    VALUATION        = "valuation"
    OWNERSHIP        = "ownership"
    GOVERNANCE       = "governance"
    GROWTH           = "growth"
    CORPORATE_ACTION = "corporate_action"
    CUSTOM           = "custom"


class CompanySignalStrength:
    STRONG   = "strong"
    MODERATE = "moderate"
    WEAK     = "weak"


@dataclass
class CompanySignal:
    signal_id:   str           = field(default_factory=lambda: str(uuid.uuid4()))
    company_id:  str           = ""
    signal_type: str           = CompanySignalType.CUSTOM
    label:       str           = ""
    description: str           = ""
    strength:    str           = CompanySignalStrength.MODERATE
    confidence:  float         = 0.5     # 0–1
    direction:   str           = "neutral"  # positive / negative / neutral
    value:       float | None  = None
    metadata:    dict[str, Any] = field(default_factory=dict)
    timestamp:   float         = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id":   self.signal_id,
            "company_id":  self.company_id,
            "signal_type": self.signal_type,
            "label":       self.label,
            "description": self.description,
            "strength":    self.strength,
            "confidence":  self.confidence,
            "direction":   self.direction,
            "value":       self.value,
            "metadata":    self.metadata,
            "timestamp":   self.timestamp,
        }

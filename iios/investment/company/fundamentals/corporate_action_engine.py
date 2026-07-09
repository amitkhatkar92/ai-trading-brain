"""iios/investment/company/fundamentals/corporate_action_engine.py"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import CorporateActionType


@dataclass
class CorporateAction:
    """Single corporate action record."""

    action_id:   str                = field(default_factory=lambda: str(uuid.uuid4()))
    company_id:  str                = ""
    action_type: CorporateActionType = CorporateActionType.OTHER
    date:        str                = ""
    value:       float | None       = None
    description: str                = ""
    metadata:    dict[str, Any]      = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id":   self.action_id,
            "company_id":  self.company_id,
            "action_type": self.action_type.value,
            "date":        self.date,
            "value":       self.value,
            "description": self.description,
            "metadata":    self.metadata,
        }


@dataclass
class CorporateActionsAnalysis:
    actions:              list[CorporateAction] = field(default_factory=list)
    recent_dividends:     list[CorporateAction] = field(default_factory=list)
    recent_buybacks:      list[CorporateAction] = field(default_factory=list)
    recent_bonuses:       list[CorporateAction] = field(default_factory=list)
    has_regular_dividends: bool                 = False
    has_bonus:            bool                  = False
    has_split:            bool                  = False
    dividend_yield_est:   float                 = 0.0
    metadata:             dict[str, Any]         = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_actions":        len(self.actions),
            "recent_dividends":     [a.to_dict() for a in self.recent_dividends],
            "recent_buybacks":      [a.to_dict() for a in self.recent_buybacks],
            "recent_bonuses":       [a.to_dict() for a in self.recent_bonuses],
            "has_regular_dividends": self.has_regular_dividends,
            "has_bonus":            self.has_bonus,
            "has_split":            self.has_split,
            "dividend_yield_est":   self.dividend_yield_est,
            "metadata":             self.metadata,
        }


class CorporateActionEngine:
    """
    Parses and summarises a list of raw corporate action dicts.

    Each raw dict is expected to contain:
      action_type  — str matching CorporateActionType member names (case-insensitive)
      date         — ISO date string, optional
      value        — numeric amount (dividend amount, ratio, etc.), optional
      description  — free text, optional
    """

    def analyze(
        self,
        company_id: str,
        raw_actions: list[dict[str, Any]],
    ) -> CorporateActionsAnalysis:
        if not raw_actions:
            return CorporateActionsAnalysis()

        parsed: list[CorporateAction] = []
        for item in raw_actions:
            parsed.append(self._parse(company_id, item))

        dividends = [a for a in parsed if a.action_type == CorporateActionType.DIVIDEND]
        buybacks  = [a for a in parsed if a.action_type == CorporateActionType.BUYBACK]
        bonuses   = [a for a in parsed if a.action_type == CorporateActionType.BONUS]
        splits    = [a for a in parsed if a.action_type == CorporateActionType.SPLIT]

        has_reg_div = len(dividends) >= 3   # 3+ dividends = regular
        div_yield   = dividends[-1].value if dividends and dividends[-1].value else 0.0

        return CorporateActionsAnalysis(
            actions               = parsed,
            recent_dividends      = dividends[-5:],
            recent_buybacks       = buybacks[-3:],
            recent_bonuses        = bonuses[-3:],
            has_regular_dividends = has_reg_div,
            has_bonus             = bool(bonuses),
            has_split             = bool(splits),
            dividend_yield_est    = float(div_yield),
            metadata              = {"total_actions": len(parsed)},
        )

    @staticmethod
    def _parse(company_id: str, raw: dict[str, Any]) -> CorporateAction:
        type_str = str(raw.get("action_type", "OTHER")).upper().replace(" ", "_")
        try:
            action_type = CorporateActionType[type_str]
        except KeyError:
            action_type = CorporateActionType.OTHER

        value = raw.get("value")
        if value is not None:
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = None

        return CorporateAction(
            company_id  = company_id,
            action_type = action_type,
            date        = str(raw.get("date", "") or ""),
            value       = value,
            description = str(raw.get("description", "") or ""),
            metadata    = {k: v for k, v in raw.items()
                          if k not in {"action_type", "date", "value", "description"}},
        )

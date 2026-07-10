"""core/backtest_request.py — Request to run a backtest."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.backtesting.core.backtest_configuration import BacktestConfiguration


@dataclass
class BacktestRequest:
    """
    A request submitted to BacktestManager.  Separates *what* to run
    from the backtest entity that tracks execution progress.
    """

    strategy_id:   str                  = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_name: str                  = ""
    configuration: BacktestConfiguration = field(default_factory=BacktestConfiguration)
    priority:      int                  = 5      # 1 (highest) … 10 (lowest)
    owner:         str                  = ""
    description:   str                  = ""
    tags:          list[str]            = field(default_factory=list)
    extra:         dict[str, Any]       = field(default_factory=dict)
    request_id:    str                  = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:    float                = field(default_factory=time.time)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.strategy_id:
            errors.append("strategy_id must not be empty")
        errors.extend(self.configuration.validate())
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "strategy_id":   self.strategy_id,
            "strategy_name": self.strategy_name,
            "configuration": self.configuration.to_dict(),
            "priority":      self.priority,
            "owner":         self.owner,
            "description":   self.description,
            "tags":          list(self.tags),
            "extra":         dict(self.extra),
            "created_at":    self.created_at,
        }

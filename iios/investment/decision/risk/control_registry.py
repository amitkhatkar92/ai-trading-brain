"""iios/investment/decision/risk/control_registry.py
ControlRegistry — thread-safe store with pre-loaded default controls.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.decision.risk.risk_constants import RiskDimension
from iios.investment.decision.risk.risk_controls import RiskControl


_DEFAULT_CONTROLS: List[RiskControl] = [
    RiskControl(
        control_id="ctrl_overall_max",
        name="Maximum Overall Risk",
        description="Overall risk must not exceed 70.",
        dimension=RiskDimension.MARKET,   # general — arbitrarily mapped to MARKET
        max_allowed=70.0,
        is_hard_limit=True,
    ),
    RiskControl(
        control_id="ctrl_market_max",
        name="Maximum Market Risk",
        description="Market dimension risk must not exceed 80.",
        dimension=RiskDimension.MARKET,
        max_allowed=80.0,
        is_hard_limit=True,
    ),
    RiskControl(
        control_id="ctrl_company_max",
        name="Maximum Company Risk",
        description="Company dimension risk must not exceed 80.",
        dimension=RiskDimension.COMPANY,
        max_allowed=80.0,
        is_hard_limit=False,
    ),
    RiskControl(
        control_id="ctrl_execution_warn",
        name="Execution Risk Warning",
        description="Execution risk above 65 triggers a warning.",
        dimension=RiskDimension.EXECUTION,
        max_allowed=65.0,
        is_hard_limit=False,
    ),
]


class ControlRegistry:
    """Thread-safe registry of RiskControls."""

    def __init__(self, load_defaults: bool = True) -> None:
        self._lock     = threading.RLock()
        self._controls: Dict[str, RiskControl] = {}
        if load_defaults:
            for c in _DEFAULT_CONTROLS:
                self._controls[c.control_id] = c

    def register(self, control: RiskControl) -> None:
        with self._lock:
            self._controls[control.control_id] = control

    def get(self, control_id: str) -> Optional[RiskControl]:
        with self._lock:
            return self._controls.get(control_id)

    def all_controls(self) -> List[RiskControl]:
        with self._lock:
            return list(self._controls.values())

    def remove(self, control_id: str) -> None:
        with self._lock:
            self._controls.pop(control_id, None)

    def count(self) -> int:
        with self._lock:
            return len(self._controls)

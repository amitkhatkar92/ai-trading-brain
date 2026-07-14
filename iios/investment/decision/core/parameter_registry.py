"""iios/investment/decision/core/parameter_registry.py
ParameterRegistry — defines and stores parameter descriptors.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ParameterDescriptor:
    """Describes one configuration parameter."""
    key:           str
    display_name:  str
    description:   str
    param_type:    type
    default_value: Any
    min_value:     Optional[float]
    max_value:     Optional[float]
    is_required:   bool
    unit:          str   # e.g. "%" | "seconds" | ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key":           self.key,
            "display_name":  self.display_name,
            "description":   self.description,
            "param_type":    self.param_type.__name__,
            "default_value": self.default_value,
            "min_value":     self.min_value,
            "max_value":     self.max_value,
            "is_required":   self.is_required,
            "unit":          self.unit,
        }


class ParameterRegistry:
    """Thread-safe registry of ParameterDescriptors."""

    def __init__(self) -> None:
        self._lock:  threading.RLock               = threading.RLock()
        self._params: Dict[str, ParameterDescriptor] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        defaults = [
            ParameterDescriptor("approval_threshold",       "Approval Threshold",
                                "Minimum score for approval.",
                                float, 65.0, 0.0, 100.0, True, "%"),
            ParameterDescriptor("confidence_threshold",     "Confidence Threshold",
                                "Minimum confidence for publishing.",
                                float, 50.0, 0.0, 100.0, True, "%"),
            ParameterDescriptor("risk_threshold",           "Risk Threshold",
                                "Maximum acceptable risk score.",
                                float, 70.0, 0.0, 100.0, True, "%"),
            ParameterDescriptor("evidence_timeout_seconds", "Evidence Timeout",
                                "Max seconds to wait for evidence.",
                                float, 300.0, 1.0, 3600.0, False, "seconds"),
            ParameterDescriptor("max_age_seconds",          "Max Decision Age",
                                "Seconds before a decision expires.",
                                float, 86400.0, 60.0, None, False, "seconds"),
            ParameterDescriptor("auto_approve",             "Auto Approve",
                                "Automatically approve decisions meeting threshold.",
                                bool, False, None, None, False, ""),
        ]
        for p in defaults:
            self._params[p.key] = p

    def register(self, param: ParameterDescriptor, overwrite: bool = False) -> None:
        with self._lock:
            if param.key in self._params and not overwrite:
                return
            self._params[param.key] = param

    def get(self, key: str) -> Optional[ParameterDescriptor]:
        with self._lock:
            return self._params.get(key)

    def all(self) -> List[ParameterDescriptor]:
        with self._lock:
            return list(self._params.values())

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._params.keys())

    def defaults(self) -> Dict[str, Any]:
        with self._lock:
            return {k: p.default_value for k, p in self._params.items()}

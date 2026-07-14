"""iios/investment/decision/core/configuration_engine.py
ConfigurationEngine — manages, validates, and applies decision configurations.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.decision.core.decision_configuration import (
    BACKTEST_CONFIG,
    DEVELOPMENT_CONFIG,
    LIVE_CONFIG,
    PAPER_CONFIG,
    DecisionConfiguration,
)
from iios.investment.decision.core.decision_constants import (
    DEFAULT_APPROVAL_THRESHOLD,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_EVIDENCE_TIMEOUT_SECS,
    DEFAULT_RISK_THRESHOLD,
    MAX_DECISION_AGE_SECS,
    EnvironmentProfile,
)
from iios.investment.decision.core.configuration_version import ConfigurationVersion
from iios.investment.decision.core.parameter_registry import ParameterRegistry
from iios.investment.decision.core.parameter_validation import ParameterValidator


_ENV_DEFAULTS: Dict[EnvironmentProfile, DecisionConfiguration] = {
    EnvironmentProfile.DEVELOPMENT: DEVELOPMENT_CONFIG,
    EnvironmentProfile.PAPER:       PAPER_CONFIG,
    EnvironmentProfile.LIVE:        LIVE_CONFIG,
    EnvironmentProfile.BACKTEST:    BACKTEST_CONFIG,
}


class ConfigurationEngine:
    """
    Manages decision configurations:
    - Default configurations per environment profile
    - Named configurations for specific decision types
    - Parameter validation before applying
    - Version history for audit trail
    """

    def __init__(
        self,
        param_registry: Optional[ParameterRegistry] = None,
        validator:      Optional[ParameterValidator] = None,
    ) -> None:
        self._lock       = threading.RLock()
        self._registry   = param_registry or ParameterRegistry()
        self._validator  = validator      or self._build_default_validator()
        self._named:     Dict[str, DecisionConfiguration]   = {}
        self._versions:  Dict[str, ConfigurationVersion]    = {}

    def _build_default_validator(self) -> ParameterValidator:
        v = ParameterValidator()
        v.add_range("approval_threshold",       0.0, 100.0)
        v.add_range("confidence_threshold",     0.0, 100.0)
        v.add_range("risk_threshold",           0.0, 100.0)
        v.add_positive("evidence_timeout_seconds")
        v.add_positive("max_age_seconds")
        v.add_type("auto_approve", bool)
        return v

    # ----------------------------------------------------------------- CRUD

    def get_default(self, env: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT) -> DecisionConfiguration:
        return _ENV_DEFAULTS.get(env, DEVELOPMENT_CONFIG)

    def register(
        self,
        name:   str,
        config: DecisionConfiguration,
        author: str = "system",
        note:   str = "",
    ) -> None:
        with self._lock:
            self._named[name] = config
            if name not in self._versions:
                self._versions[name] = ConfigurationVersion(config.to_dict(), author)
            else:
                self._versions[name].commit(config.to_dict(), author, note or f"updated {name}")

    def get(self, name: str) -> Optional[DecisionConfiguration]:
        with self._lock:
            return self._named.get(name)

    def get_or_default(
        self,
        name: str,
        env:  EnvironmentProfile = EnvironmentProfile.DEVELOPMENT,
    ) -> DecisionConfiguration:
        cfg = self.get(name)
        return cfg if cfg is not None else self.get_default(env)

    def all_names(self) -> List[str]:
        with self._lock:
            return list(self._named.keys())

    # ----------------------------------------------------------------- validation

    def validate(self, config: DecisionConfiguration) -> tuple:
        """Returns (is_valid, list_of_error_messages)."""
        return self._validator.is_valid(config.to_dict())

    # ----------------------------------------------------------------- versioning

    def version_history(self, name: str):
        with self._lock:
            cv = self._versions.get(name)
            return cv.history() if cv else []

    def rollback(self, name: str, version: int, author: str = "system") -> Optional[DecisionConfiguration]:
        with self._lock:
            cv = self._versions.get(name)
            if cv is None:
                return None
            snap = cv.rollback(version, author)
            if snap is None:
                return None
            # Rebuild DecisionConfiguration from stored dict
            d = snap.config_data
            config = DecisionConfiguration(
                approval_threshold=d.get("approval_threshold", DEFAULT_APPROVAL_THRESHOLD),
                confidence_threshold=d.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD),
                risk_threshold=d.get("risk_threshold", DEFAULT_RISK_THRESHOLD),
                evidence_timeout_seconds=d.get("evidence_timeout_seconds", DEFAULT_EVIDENCE_TIMEOUT_SECS),
                max_age_seconds=d.get("max_age_seconds", MAX_DECISION_AGE_SECS),
                auto_approve=d.get("auto_approve", False),
                environment=EnvironmentProfile(d.get("environment", "development")),
                policies=d.get("policies", {}),
            )
            self._named[name] = config
            return config

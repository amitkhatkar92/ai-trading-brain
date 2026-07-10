"""training/hyperparameter_manager.py — Hyperparameter search space and sampling."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class HyperparameterSpec:
    """Definition of a single hyperparameter search dimension."""
    name:        str
    param_type:  str           # "float" | "int" | "categorical" | "log_float"
    low:         Optional[float]
    high:        Optional[float]
    choices:     list[Any]
    default:     Any

    @classmethod
    def float(cls, name: str, low: float, high: float, default: float) -> "HyperparameterSpec":
        return cls(name=name, param_type="float", low=low, high=high, choices=[], default=default)

    @classmethod
    def log_float(cls, name: str, low: float, high: float, default: float) -> "HyperparameterSpec":
        return cls(name=name, param_type="log_float", low=low, high=high, choices=[], default=default)

    @classmethod
    def integer(cls, name: str, low: int, high: int, default: int) -> "HyperparameterSpec":
        return cls(name=name, param_type="int", low=low, high=high, choices=[], default=default)

    @classmethod
    def categorical(cls, name: str, choices: list[Any], default: Any) -> "HyperparameterSpec":
        return cls(name=name, param_type="categorical", low=None, high=None, choices=choices, default=default)


class HyperparameterManager:
    """
    Manages the hyperparameter search space and generates trial configs.

    Does NOT depend on any specific optimisation library — all sampling is
    done with Python's built-in ``random`` module (grid / random search only).
    Bayesian / evolutionary search can be added by consumers via the
    ``register_spec`` + ``sample`` interface.
    """

    def __init__(self, seed: int = 42) -> None:
        self._specs: dict[str, HyperparameterSpec] = {}
        self._rng   = random.Random(seed)
        self._trials: list[dict[str, Any]] = []

    # ── Space definition ──────────────────────────────────────────────────────

    def register_spec(self, spec: HyperparameterSpec) -> None:
        self._specs[spec.name] = spec

    def register_specs(self, specs: list[HyperparameterSpec]) -> None:
        for spec in specs:
            self.register_spec(spec)

    def spec_names(self) -> list[str]:
        return list(self._specs.keys())

    # ── Sampling ──────────────────────────────────────────────────────────────

    def defaults(self) -> dict[str, Any]:
        return {name: spec.default for name, spec in self._specs.items()}

    def sample_random(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, spec in self._specs.items():
            if spec.param_type == "float":
                result[name] = self._rng.uniform(spec.low, spec.high)  # type: ignore[arg-type]
            elif spec.param_type == "log_float":
                import math
                log_low  = math.log(spec.low)   # type: ignore[arg-type]
                log_high = math.log(spec.high)  # type: ignore[arg-type]
                result[name] = math.exp(self._rng.uniform(log_low, log_high))
            elif spec.param_type == "int":
                result[name] = self._rng.randint(int(spec.low), int(spec.high))  # type: ignore[arg-type]
            elif spec.param_type == "categorical":
                result[name] = self._rng.choice(spec.choices)
            else:
                result[name] = spec.default
        self._trials.append(result)
        return result

    def sample_grid(self, n: int) -> list[dict[str, Any]]:
        """Return n random samples (grid search via random strategy)."""
        return [self.sample_random() for _ in range(n)]

    def trial_count(self) -> int:
        return len(self._trials)

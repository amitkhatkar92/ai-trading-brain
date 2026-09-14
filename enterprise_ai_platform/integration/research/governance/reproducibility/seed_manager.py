"""reproducibility/seed_manager.py — Deterministic random-seed registry."""
from __future__ import annotations

import random
import threading
from typing import Any, Optional


class SeedManager:
    """
    Manages random seeds for research entities.

    Seeds are stored per entity and applied on demand to Python's ``random``
    module (and ``numpy`` when available).
    """

    def __init__(self, default_seed: int = 42) -> None:
        self._default   = default_seed
        self._seeds:    dict[str, int] = {}
        self._counter   = 0
        self._lock      = threading.RLock()

    def register(self, entity_id: str, seed: int) -> None:
        with self._lock:
            self._seeds[entity_id] = seed

    def get_seed(self, entity_id: str) -> Optional[int]:
        with self._lock:
            return self._seeds.get(entity_id)

    def apply_seed(self, entity_id: str) -> int:
        """Apply the registered seed (or default) and return the value used."""
        with self._lock:
            seed = self._seeds.get(entity_id, self._default)
        random.seed(seed)
        try:
            import numpy as np  # type: ignore
            np.random.seed(seed % (2**32))
        except ImportError:
            pass
        return seed

    def generate_seed(self) -> int:
        """Return a deterministic seed based on an internal counter."""
        with self._lock:
            seed = (self._default + self._counter * 1_000_003) % (2**31)
            self._counter += 1
        return seed

    def remove(self, entity_id: str) -> None:
        with self._lock:
            self._seeds.pop(entity_id, None)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered":    len(self._seeds),
                "default_seed":  self._default,
                "counter":       self._counter,
            }

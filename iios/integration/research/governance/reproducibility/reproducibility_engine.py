"""reproducibility/reproducibility_engine.py — Reproducibility orchestrator."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import ReproducibilityStatus
from iios.integration.research.governance.reproducibility.environment_snapshot    import EnvironmentSnapshot
from iios.integration.research.governance.reproducibility.configuration_snapshot import ConfigurationSnapshot
from iios.integration.research.governance.reproducibility.seed_manager            import SeedManager
from iios.integration.research.governance.reproducibility.reproduction_runner     import ReproductionRunner, ReproductionResult


class ReproducibilityEngine:
    """Facade for environment snapshots, configuration snapshots, and seed management."""

    def __init__(self, default_seed: int = 42) -> None:
        self._env_snapshots:  dict[str, EnvironmentSnapshot]     = {}
        self._cfg_snapshots:  dict[str, ConfigurationSnapshot]   = {}
        self._repr_results:   dict[str, list[ReproductionResult]] = {}
        self._seed_manager    = SeedManager(default_seed)
        self._runner          = ReproductionRunner()
        self._lock            = threading.RLock()

    # ── Environment ───────────────────────────────────────────────────────────

    def snapshot_environment(
        self,
        entity_id: str,
        *,
        include_env_vars: bool = False,
    ) -> EnvironmentSnapshot:
        snap = EnvironmentSnapshot.capture(include_env_vars=include_env_vars)
        with self._lock:
            self._env_snapshots[entity_id] = snap
        return snap

    def get_env_snapshot(self, entity_id: str) -> Optional[EnvironmentSnapshot]:
        with self._lock:
            return self._env_snapshots.get(entity_id)

    # ── Configuration ─────────────────────────────────────────────────────────

    def snapshot_config(
        self,
        entity_id: str,
        config:    dict[str, Any],
        **kwargs:  Any,
    ) -> ConfigurationSnapshot:
        snap = ConfigurationSnapshot.capture(entity_id, config, **kwargs)
        with self._lock:
            self._cfg_snapshots[entity_id] = snap
        return snap

    def get_config_snapshot(self, entity_id: str) -> Optional[ConfigurationSnapshot]:
        with self._lock:
            return self._cfg_snapshots.get(entity_id)

    # ── Seeds ─────────────────────────────────────────────────────────────────

    def register_seed(self, entity_id: str, seed: int) -> None:
        self._seed_manager.register(entity_id, seed)

    def get_seed(self, entity_id: str) -> Optional[int]:
        return self._seed_manager.get_seed(entity_id)

    def apply_seed(self, entity_id: str) -> int:
        return self._seed_manager.apply_seed(entity_id)

    def generate_seed(self) -> int:
        return self._seed_manager.generate_seed()

    # ── Reproduction runs ─────────────────────────────────────────────────────

    async def run_reproduction(
        self,
        entity_id:      str,
        fn:             Any,
        *,
        reference_hash: Optional[str] = None,
        timeout_sec:    float = 300.0,
    ) -> ReproductionResult:
        with self._lock:
            attempt = len(self._repr_results.get(entity_id, [])) + 1
        result = await self._runner.run(
            entity_id, fn,
            reference_hash=reference_hash,
            attempt=attempt,
            timeout_sec=timeout_sec,
        )
        with self._lock:
            self._repr_results.setdefault(entity_id, []).append(result)
        return result

    def check_reproducibility(self, entity_id: str) -> ReproducibilityStatus:
        with self._lock:
            runs = self._repr_results.get(entity_id, [])
        if not runs:
            return ReproducibilityStatus.UNKNOWN
        last = runs[-1]
        return last.status

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "env_snapshots":  len(self._env_snapshots),
                "cfg_snapshots":  len(self._cfg_snapshots),
                "repr_entities":  len(self._repr_results),
                "repr_runs":      sum(len(v) for v in self._repr_results.values()),
                "seed_manager":   self._seed_manager.stats(),
            }

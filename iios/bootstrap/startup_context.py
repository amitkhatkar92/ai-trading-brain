"""
iios/bootstrap/startup_context.py
===================================
Central context object passed through every bootstrap stage.

``StartupContext`` is the single source of truth for the bootstrap engine:
it accumulates configuration, validation results, loaded modules, registered
services, and timing information as each stage completes.

Architecture Reference: IIOS-BSS-001 §2.2 Context Model
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .startup_state import StartupStageResult, SystemPhase, ValidationFinding

__all__ = ["StartupContext"]


@dataclass
class StartupContext:
    """Mutable context accumulated across all 45 bootstrap stages.

    All stage handlers receive this object and write their results back into it.
    The bootstrap engine reads it to make go/no-go decisions between stages.

    Thread safety: not thread-safe by design — the bootstrap sequence is
    intentionally single-threaded. Concurrent access during startup is
    an architectural error.
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    run_id: str = ""                            # UUID assigned at engine start
    started_at: float = field(default_factory=time.monotonic)
    started_at_wall: str = ""                   # ISO-8601 wall clock string

    # ── Environment ──────────────────────────────────────────────────────────
    iios_env: str = "development"               # IIOS_ENV value
    paper_trading: bool = True                  # IIOS_PAPER_TRADING
    log_level: str = "INFO"                     # IIOS_LOG_LEVEL
    log_file: str = "logs/iios.log"
    db_path: str = "data/iios.db"
    paper_trades_path: str = "data/paper_trades.csv"
    env_file_loaded: str = ""                   # Which .env file was loaded
    env_vars: dict[str, str] = field(default_factory=dict)  # All loaded vars

    # ── Configuration ─────────────────────────────────────────────────────────
    # Mirrors config.py; populated by ConfigurationLoader
    decision_threshold: float = 6.5
    vix_threshold: float = 45.0
    daily_loss_pct: float = 0.02
    debate_agents: int = 5
    layers: int = 17
    config_module_loaded: bool = False
    config_attributes: dict[str, Any] = field(default_factory=dict)

    # ── Repository ────────────────────────────────────────────────────────────
    repo_root: Path = field(default_factory=lambda: Path(".").resolve())
    python_version: str = ""
    python_version_ok: bool = False

    # ── Validation ────────────────────────────────────────────────────────────
    findings: list[ValidationFinding] = field(default_factory=list)
    validation_passed: bool = False

    # ── Dependencies ─────────────────────────────────────────────────────────
    installed_packages: dict[str, str] = field(default_factory=dict)  # name → version
    missing_packages: list[str] = field(default_factory=list)
    optional_missing: list[str] = field(default_factory=list)

    # ── Loaded Modules ────────────────────────────────────────────────────────
    loaded_modules: dict[str, Any] = field(default_factory=dict)   # name → module
    failed_modules: dict[str, str] = field(default_factory=dict)   # name → error

    # ── Service Registry ─────────────────────────────────────────────────────
    # Populated by ServiceLoader; maps service name → instance
    services: dict[str, Any] = field(default_factory=dict)
    service_errors: dict[str, str] = field(default_factory=dict)

    # ── Database ──────────────────────────────────────────────────────────────
    db_connection: Optional[Any] = None        # sqlite3.Connection when open
    db_initialized: bool = False
    db_schema_version: int = 0

    # ── Stage Results ─────────────────────────────────────────────────────────
    stage_results: list[StartupStageResult] = field(default_factory=list)
    current_stage: int = 0
    total_stages: int = 45

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    current_phase: SystemPhase = SystemPhase.UNINITIALIZED
    operational: bool = False

    # ── Health ────────────────────────────────────────────────────────────────
    health_checks: dict[str, bool] = field(default_factory=dict)   # check → ok/fail
    health_details: dict[str, str] = field(default_factory=dict)   # check → detail

    # ── Flags set by individual stages ───────────────────────────────────────
    flags: dict[str, Any] = field(default_factory=dict)

    # ─────────────────────────────────────────────────────────────────────────
    # Convenience methods
    # ─────────────────────────────────────────────────────────────────────────

    def add_finding(self, finding: ValidationFinding) -> None:
        """Append a validation finding."""
        self.findings.append(finding)

    def blocking_findings(self) -> list[ValidationFinding]:
        """Return findings that must be resolved before startup can proceed."""
        return [f for f in self.findings if f.blocks_startup]

    def record_stage(self, result: StartupStageResult) -> None:
        """Append a stage result and advance ``current_stage``."""
        self.stage_results.append(result)
        self.current_stage = result.stage_number

    def get_stage_result(self, stage_number: int) -> Optional[StartupStageResult]:
        """Return the result for ``stage_number``, or None."""
        for r in self.stage_results:
            if r.stage_number == stage_number:
                return r
        return None

    def stage_succeeded(self, stage_number: int) -> bool:
        """Return True if stage ``stage_number`` completed or was skipped."""
        r = self.get_stage_result(stage_number)
        return r is not None and r.succeeded

    @property
    def elapsed_ms(self) -> float:
        """Wall-clock elapsed time since bootstrap started, in milliseconds."""
        return (time.monotonic() - self.started_at) * 1000.0

    @property
    def failed_stages(self) -> list[StartupStageResult]:
        from .startup_state import StageStatus
        return [r for r in self.stage_results if r.status == StageStatus.FAILED]

    @property
    def completed_stages(self) -> int:
        from .startup_state import StageStatus
        return sum(
            1 for r in self.stage_results
            if r.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
        )

    def set_service(self, name: str, instance: Any) -> None:
        """Register a service instance."""
        self.services[name] = instance

    def get_service(self, name: str, default: Any = None) -> Any:
        """Retrieve a registered service by name."""
        return self.services.get(name, default)

    def set_flag(self, key: str, value: Any) -> None:
        self.flags[key] = value

    def get_flag(self, key: str, default: Any = None) -> Any:
        return self.flags.get(key, default)

    def summary(self) -> dict[str, Any]:
        """Return a concise summary dict suitable for logging."""
        return {
            "run_id": self.run_id,
            "env": self.iios_env,
            "paper_trading": self.paper_trading,
            "phase": self.current_phase.value,
            "stages_completed": self.completed_stages,
            "stages_total": self.total_stages,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "findings": len(self.findings),
            "blocking_findings": len(self.blocking_findings()),
            "services": list(self.services.keys()),
            "health": {k: ("ok" if v else "fail") for k, v in self.health_checks.items()},
        }

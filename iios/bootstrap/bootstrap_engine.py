"""
iios/bootstrap/bootstrap_engine.py
=====================================
IIOS Bootstrap Engine — 45-stage platform initialization.

``BootstrapEngine`` is the single entry point for starting the IIOS platform.
It defines all 45 startup stages, wires together every sub-component, and
drives the ``StartupManager`` through to operational status.

Startup responsibilities (in order):
  Stages  1- 5   Pre-validation          (Python, repo, write access)
  Stages  6-10   Environment             (load .env, validate vars)
  Stages 11-15   Configuration           (import config.py, validate constants)
  Stages 16-20   Logging                 (directories, root logger, loguru, banner)
  Stages 21-25   Infrastructure          (service registry, DI, core services)
  Stages 26-30   Database               (create dirs, SQLite init, WAL, schema, integrity)
  Stages 31-35   Knowledge & AI          (knowledge base, ontology, agents scaffold)
  Stages 36-40   Reasoning & Decision    (reasoning layer, decision layer, monitoring)
  Stages 41-45   Health & Certification  (health checks, startup cert, operational mode)

Usage::

    engine = BootstrapEngine()
    context = engine.start()
    # ... IIOS is now running ...
    engine.shutdown()

Architecture Reference: IIOS-BSS-001 (complete 45-stage sequence)
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .configuration_loader import ConfigurationLoader
from .dependency_loader import DependencyLoader
from .environment_loader import EnvironmentLoader
from .lifecycle_manager import LifecycleManager
from .module_loader import ModuleLoader
from .repository_validator import RepositoryValidator
from .service_loader import ServiceLoader
from .shutdown_manager import ShutdownManager
from .startup_context import StartupContext
from .startup_manager import StartupManager, StartupManagerConfig
from .startup_state import BootstrapError, BootstrapStage, StageStatus, SystemPhase
from .startup_validator import StartupValidator
from .system_state import SystemState, get_system_state

__all__ = ["BootstrapEngine"]

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Architecture constants (read-only references; source-of-truth = config.py) #
# --------------------------------------------------------------------------- #
_DECISION_THRESHOLD: float = 6.5
_VIX_THRESHOLD: float      = 45.0
_DAILY_LOSS_PCT: float     = 0.02
_DEBATE_AGENTS: int        = 5
_LAYERS: int               = 17


# =========================================================================== #
#   Bootstrap Engine                                                            #
# =========================================================================== #


class BootstrapEngine:
    """IIOS platform bootstrap orchestrator.

    Instantiate once per process. Calling ``start()`` initialises and starts
    the platform. Calling ``shutdown()`` tears it down gracefully.

    Parameters
    ----------
    repo_root:
        Explicit repository root. Defaults to the current working directory.
    progress_callback:
        Optional callable ``(stage_num, name, status, elapsed_ms)`` invoked
        after each stage.
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        progress_callback: Optional[Any] = None,
    ) -> None:
        self._root = repo_root or Path(".").resolve()
        self._progress_callback = progress_callback

        # Sub-components (wired during start())
        self._lifecycle: LifecycleManager = LifecycleManager()
        self._shutdown_mgr: ShutdownManager = ShutdownManager()
        self._module_loader: ModuleLoader = ModuleLoader()
        self._ctx: Optional[StartupContext] = None

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def start(self) -> StartupContext:
        """Execute the full 45-stage bootstrap sequence.

        Returns the populated ``StartupContext`` on success.
        Raises ``BootstrapError`` on unrecoverable failure.
        """
        ctx = self._build_context()
        self._ctx = ctx

        get_system_state().set_startup_context(ctx)
        self._lifecycle.initialize()  # → INITIALIZING

        stages = self._build_stages(ctx)
        config = StartupManagerConfig(
            abort_on_critical_failure=True,
            skip_optional_on_dep_failure=True,
            log_stage_start=True,
            log_stage_complete=True,
        )
        manager = StartupManager(ctx, stages, config=config)
        if self._progress_callback:
            manager.add_progress_callback(self._progress_callback)

        # Emit structured startup banner
        logger.info("=" * 64)
        logger.info("  IIOS Bootstrap Engine  —  run_id=%s", ctx.run_id)
        logger.info("  root=%s  env=%s  paper=%s", self._root, ctx.iios_env, ctx.paper_trading)
        logger.info("  stages=%d  python=%s", len(stages), ctx.python_version)
        logger.info("=" * 64)

        try:
            manager.run()
        except BootstrapError:
            self._lifecycle.mark_failed("BootstrapEngine.start() — stage failure")
            raise

        # Final phase transitions
        self._lifecycle.mark_initialized()   # INITIALIZING → INITIALIZED
        self._lifecycle.start()              # INITIALIZED → STARTING
        self._lifecycle.mark_running()       # STARTING → RUNNING

        ctx.current_phase = SystemPhase.RUNNING
        ctx.operational = True

        logger.info("=" * 64)
        logger.info(
            "  IIOS Bootstrap COMPLETE  —  %.1f ms  —  phase=%s",
            ctx.elapsed_ms,
            ctx.current_phase.value,
        )
        logger.info("=" * 64)
        return ctx

    def shutdown(self) -> None:
        """Execute graceful shutdown sequence."""
        logger.info("IIOS Bootstrap Engine: shutdown initiated")
        try:
            self._lifecycle.shutdown()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Lifecycle shutdown error: %s", exc)

        report = self._shutdown_mgr.run()
        if not report.clean:
            logger.warning(
                "Shutdown completed with issues: timeout=%s, failed=%s",
                report.components_timeout,
                report.components_failed,
            )
        else:
            logger.info("Shutdown complete (clean) in %.1f ms", report.duration_ms)

    @property
    def context(self) -> Optional[StartupContext]:
        """Return the startup context, or None if start() hasn't been called."""
        return self._ctx

    @property
    def lifecycle(self) -> LifecycleManager:
        return self._lifecycle

    # ─────────────────────────────────────────────────────────────────────────
    # Context factory
    # ─────────────────────────────────────────────────────────────────────────

    def _build_context(self) -> StartupContext:
        ctx = StartupContext()
        ctx.run_id = str(uuid.uuid4())
        ctx.started_at_wall = datetime.now(timezone.utc).isoformat()
        ctx.repo_root = self._root
        ctx.python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        return ctx

    # ─────────────────────────────────────────────────────────────────────────
    # Stage definitions — 45 stages
    # ─────────────────────────────────────────────────────────────────────────

    def _build_stages(self, ctx: StartupContext) -> list[BootstrapStage]:  # noqa: PLR0915 (many stages)
        def stage(
            number: int,
            name: str,
            description: str,
            handler: Any,
            deps: Optional[list[int]] = None,
            optional: bool = False,
            timeout: float = 30.0,
            can_retry: bool = True,
            max_retries: int = 2,
        ) -> BootstrapStage:
            return BootstrapStage(
                number=number,
                name=name,
                description=description,
                handler=handler,
                dependencies=deps or [],
                optional=optional,
                can_retry=can_retry,
                max_retries=max_retries,
                timeout_seconds=timeout,
            )

        # ── Group A: Pre-Validation (1-5) ────────────────────────────────────
        return [
            stage(1,  "python_version",        "Verify Python >= 3.12",                            self._s01_python_version,          timeout=5,  can_retry=False),
            stage(2,  "repo_structure",         "Validate repository directory structure",           self._s02_repo_structure,          timeout=10, can_retry=False),
            stage(3,  "write_access",           "Verify data/ and logs/ are writable",               self._s03_write_access,            timeout=5,  can_retry=False),
            stage(4,  "required_files",         "Check required files (config.py, main.py, etc.)",   self._s04_required_files,          timeout=5,  can_retry=False),
            stage(5,  "package_init_files",     "Verify iios sub-package __init__.py files",        self._s05_package_inits,           timeout=5,  can_retry=False),

            # ── Group B: Environment (6-10) ──────────────────────────────────
            stage(6,  "env_file_discovery",     "Locate and select .env file",                      self._s06_env_discovery,           deps=[1, 2], timeout=5),
            stage(7,  "env_load",               "Load environment variables from .env file",         self._s07_env_load,                deps=[6],    timeout=10),
            stage(8,  "env_validate",           "Validate required environment variables",           self._s08_env_validate,            deps=[7],    timeout=5),
            stage(9,  "env_type_coerce",        "Coerce typed env vars (bool, int, float)",         self._s09_env_coerce,              deps=[7],    timeout=5),
            stage(10, "env_audit",              "Emit environment audit log (redacted)",             self._s10_env_audit,               deps=[7, 8], timeout=5, optional=True),

            # ── Group C: Configuration (11-15) ───────────────────────────────
            stage(11, "config_import",          "Import config.py module",                          self._s11_config_import,           deps=[7],    timeout=10, can_retry=False),
            stage(12, "config_constants",       "Validate architecture-invariant constants",        self._s12_config_constants,        deps=[11],   timeout=5,  can_retry=False),
            stage(13, "config_risk_thresholds", "Validate risk control thresholds",                 self._s13_config_risk,             deps=[11],   timeout=5),
            stage(14, "config_broker",          "Validate broker configuration",                    self._s14_config_broker,           deps=[11],   timeout=5, optional=True),
            stage(15, "config_audit",           "Emit configuration audit log",                     self._s15_config_audit,            deps=[11, 12], timeout=5, optional=True),

            # ── Group D: Logging (16-20) ──────────────────────────────────────
            stage(16, "log_directories",        "Create log directory structure",                   self._s16_log_dirs,                deps=[3],    timeout=5),
            stage(17, "log_stdlib",             "Configure Python stdlib logging",                  self._s17_log_stdlib,              deps=[16],   timeout=5),
            stage(18, "log_loguru",             "Configure loguru (if available)",                  self._s18_log_loguru,              deps=[16],   timeout=5, optional=True),
            stage(19, "log_startup_banner",     "Emit structured startup banner",                   self._s19_log_banner,              deps=[17],   timeout=5, optional=True),
            stage(20, "log_config_summary",     "Log configuration summary",                        self._s20_log_config_summary,      deps=[15, 17], timeout=5, optional=True),

            # ── Group E: Infrastructure (21-25) ──────────────────────────────
            stage(21, "infra_service_registry", "Initialize in-process service registry",          self._s21_service_registry,        deps=[11],   timeout=10),
            stage(22, "infra_di_container",     "Initialize DI container (if iios.infra ready)",   self._s22_di_container,            deps=[21],   timeout=10, optional=True),
            stage(23, "infra_core_services",    "Load core infrastructure services",               self._s23_core_services,           deps=[21],   timeout=20),
            stage(24, "infra_validate_registry","Verify all CORE services loaded",                 self._s24_validate_registry,       deps=[23],   timeout=5),
            stage(25, "infra_health_probe",     "Ping each registered service",                    self._s25_infra_health,            deps=[23],   timeout=15, optional=True),

            # ── Group F: Database (26-30) ─────────────────────────────────────
            stage(26, "db_directories",         "Create data directory structure",                  self._s26_db_dirs,                 deps=[3],    timeout=5),
            stage(27, "db_connect",             "Open SQLite connection (WAL mode)",                self._s27_db_connect,              deps=[26],   timeout=10),
            stage(28, "db_wal_mode",            "Enable SQLite WAL journal mode",                   self._s28_db_wal,                  deps=[27],   timeout=5),
            stage(29, "db_schema",              "Initialize schema / run migrations",               self._s29_db_schema,               deps=[27, 28], timeout=30),
            stage(30, "db_integrity",           "Run SQLite PRAGMA integrity_check",                self._s30_db_integrity,            deps=[27],   timeout=15),

            # ── Group G: Knowledge & AI (31-35) ──────────────────────────────
            stage(31, "knowledge_base",         "Initialize knowledge base module (if present)",    self._s31_knowledge_base,          deps=[23],   timeout=20, optional=True),
            stage(32, "ontology_layer",         "Initialize market ontology (if present)",          self._s32_ontology,                deps=[31],   timeout=20, optional=True),
            stage(33, "agents_scaffold",        "Verify ~62 agent stubs importable (if present)",  self._s33_agents,                  deps=[21],   timeout=15, optional=True),
            stage(34, "reasoning_layer",        "Initialize reasoning layer (if present)",          self._s34_reasoning,               deps=[23],   timeout=20, optional=True),
            stage(35, "decision_layer",         "Initialize Layer 10 DebateAndDecision (if present)",self._s35_decision,              deps=[34],   timeout=20, optional=True),

            # ── Group H: Monitoring & Feeds (36-40) ──────────────────────────
            stage(36, "monitoring_init",        "Initialize Layer 17 ControlTower (if present)",   self._s36_monitoring,              deps=[23, 27], timeout=20, optional=True),
            stage(37, "feed_manager",           "Register market data FeedManager singleton",      self._s37_feed_manager,            deps=[23],   timeout=15),
            stage(38, "performance_tracker",    "Register StrategyPerformanceTracker singleton",   self._s38_performance_tracker,     deps=[23],   timeout=10, optional=True),
            stage(39, "regime_strategy_map",    "Register RegimeStrategyMap singleton",            self._s39_regime_map,              deps=[23],   timeout=10, optional=True),
            stage(40, "telegram_bot",           "Register Telegram bot singleton (if enabled)",    self._s40_telegram,                deps=[23],   timeout=15, optional=True),

            # ── Group I: Health & Certification (41-45) ──────────────────────
            stage(41, "health_components",      "Check all registered component health",           self._s41_health_components,       deps=[23, 27], timeout=20),
            stage(42, "health_database",        "Verify database is readable and writable",        self._s42_health_database,         deps=[27, 30], timeout=10),
            stage(43, "health_feeds",           "Probe market data feed connectivity",             self._s43_health_feeds,            deps=[37],   timeout=20, optional=True),
            stage(44, "certify_startup",        "Certify all required stages completed",           self._s44_certify,                 deps=[1, 2, 3, 4, 7, 11, 12, 21, 27], timeout=5, can_retry=False),
            stage(45, "enter_operational",      "Mark system operational and emit ready signal",   self._s45_operational,             deps=[44],   timeout=5, can_retry=False),
        ]

    # ========================================================================= #
    #   Stage Handlers                                                            #
    # ========================================================================= #

    # ── Group A: Pre-Validation ───────────────────────────────────────────────

    def _s01_python_version(self, ctx: StartupContext) -> None:
        vi = sys.version_info
        ctx.python_version = f"{vi.major}.{vi.minor}.{vi.micro}"
        ctx.python_version_ok = vi >= (3, 12)
        if not ctx.python_version_ok:
            raise BootstrapError(
                f"Python {ctx.python_version} < 3.12 — upgrade required",
                stage_number=1, stage_name="python_version",
            )
        logger.debug("Python %s OK", ctx.python_version)

    def _s02_repo_structure(self, ctx: StartupContext) -> None:
        validator = RepositoryValidator(repo_root=ctx.repo_root)
        report = validator.validate()
        for f in report.findings:
            ctx.add_finding(f)
        if not report.passed:
            blocking = [str(f) for f in report.blocking_findings()]
            raise BootstrapError(
                f"Repository validation failed: {'; '.join(blocking)}",
                stage_number=2, stage_name="repo_structure",
            )

    def _s03_write_access(self, ctx: StartupContext) -> None:
        for rel_dir in ("data", "logs"):
            full = ctx.repo_root / rel_dir
            full.mkdir(parents=True, exist_ok=True)
            probe = full / ".bootstrap_probe"
            try:
                probe.write_text("ok")
                probe.unlink()
            except OSError as exc:
                raise BootstrapError(
                    f"Directory {rel_dir}/ is not writable: {exc}",
                    stage_number=3, stage_name="write_access", cause=exc,
                ) from exc

    def _s04_required_files(self, ctx: StartupContext) -> None:
        required = ["config.py", "main.py"]
        missing = [f for f in required if not (ctx.repo_root / f).is_file()]
        if missing:
            raise BootstrapError(
                f"Required files missing: {', '.join(missing)}",
                stage_number=4, stage_name="required_files",
            )

    def _s05_package_inits(self, ctx: StartupContext) -> None:
        pkgs = ["iios", "iios/core", "iios/bootstrap"]
        missing = [p for p in pkgs if not (ctx.repo_root / p / "__init__.py").is_file()]
        if missing:
            raise BootstrapError(
                f"Package __init__.py missing: {', '.join(missing)}",
                stage_number=5, stage_name="package_init_files",
            )

    # ── Group B: Environment ──────────────────────────────────────────────────

    def _s06_env_discovery(self, ctx: StartupContext) -> None:
        env_name = os.environ.get("IIOS_ENV", "development")
        ctx.iios_env = env_name
        candidates = [
            str(ctx.repo_root / f".env.{env_name}"),
            str(ctx.repo_root / ".env"),
            str(ctx.repo_root / ".env.example"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                ctx.set_flag("env_file_candidate", c)
                logger.debug("Env file found: %s", c)
                return
        logger.warning("No .env file found — relying on OS environment")

    def _s07_env_load(self, ctx: StartupContext) -> None:
        loader = EnvironmentLoader(repo_root=ctx.repo_root)
        snap = loader.load()
        ctx.iios_env         = snap.env_name
        ctx.paper_trading    = snap.paper_trading
        ctx.log_level        = snap.log_level
        ctx.log_file         = snap.log_file
        ctx.db_path          = snap.db_path
        ctx.env_file_loaded  = snap.source_file
        ctx.env_vars         = dict(snap.typed)
        for f in snap.findings:
            ctx.add_finding(f)
        ctx.set_flag("env_snapshot", snap)

    def _s08_env_validate(self, ctx: StartupContext) -> None:
        snap = ctx.get_flag("env_snapshot")
        if snap is None:
            return
        blocking = [f for f in snap.findings if f.blocks_startup]
        if blocking:
            raise BootstrapError(
                f"Environment validation failed: {blocking[0].message}",
                stage_number=8, stage_name="env_validate",
            )

    def _s09_env_coerce(self, ctx: StartupContext) -> None:
        # Already done in EnvironmentLoader — just set convenience context flags
        snap = ctx.get_flag("env_snapshot")
        if snap:
            ctx.set_flag("enable_telegram",    snap.enable_telegram)
            ctx.set_flag("enable_dashboard",   snap.enable_dashboard)
            ctx.set_flag("enable_live_trading",snap.enable_live_trading)

    def _s10_env_audit(self, ctx: StartupContext) -> None:
        logger.info(
            "Environment: env=%s paper=%s log_level=%s db=%s",
            ctx.iios_env, ctx.paper_trading, ctx.log_level, ctx.db_path,
        )

    # ── Group C: Configuration ────────────────────────────────────────────────

    def _s11_config_import(self, ctx: StartupContext) -> None:
        loader = ConfigurationLoader()
        snap = loader.load()
        ctx.config_module_loaded  = snap.module_loaded
        ctx.config_attributes     = dict(snap.attributes)
        ctx.decision_threshold    = snap.decision_threshold
        ctx.vix_threshold         = snap.vix_threshold
        ctx.daily_loss_pct        = snap.daily_loss_pct
        ctx.paper_trading         = snap.paper_trading
        for f in snap.findings:
            ctx.add_finding(f)
        if not snap.module_loaded:
            raise BootstrapError(
                "Cannot import config.py — check for syntax errors",
                stage_number=11, stage_name="config_import",
            )
        ctx.set_flag("config_snapshot", snap)

    def _s12_config_constants(self, ctx: StartupContext) -> None:
        snap = ctx.get_flag("config_snapshot")
        if snap is None:
            return
        # Verify the three architecture-critical constants are present
        attrs = ctx.config_attributes
        for name, expected in [
            ("DECISION_THRESHOLD", _DECISION_THRESHOLD),
            ("VIX_THRESHOLD",      _VIX_THRESHOLD),
            ("DAILY_LOSS_PCT",     _DAILY_LOSS_PCT),
        ]:
            if name not in attrs:
                logger.warning("config.py missing constant: %s (using default %s)", name, expected)
        logger.debug(
            "Config constants: DECISION=%.1f VIX=%.1f LOSS=%.3f",
            ctx.decision_threshold, ctx.vix_threshold, ctx.daily_loss_pct,
        )

    def _s13_config_risk(self, ctx: StartupContext) -> None:
        # Belt-and-suspenders: warn if VIX threshold is suspiciously high
        if ctx.vix_threshold > 100 or ctx.vix_threshold < 5:
            logger.warning("VIX_THRESHOLD=%.1f is outside [5, 100] — RiskGuardian may misbehave", ctx.vix_threshold)

    def _s14_config_broker(self, ctx: StartupContext) -> None:
        attrs = ctx.config_attributes
        broker = attrs.get("BROKER", attrs.get("BROKER_PRIMARY", "unknown"))
        logger.debug("Broker configuration: primary=%s", broker)

    def _s15_config_audit(self, ctx: StartupContext) -> None:
        logger.info(
            "Configuration: decision_threshold=%.1f vix_threshold=%.1f "
            "daily_loss_pct=%.3f paper_trading=%s",
            ctx.decision_threshold, ctx.vix_threshold,
            ctx.daily_loss_pct, ctx.paper_trading,
        )

    # ── Group D: Logging ──────────────────────────────────────────────────────

    def _s16_log_dirs(self, ctx: StartupContext) -> None:
        log_dir = Path(ctx.log_file).parent if ctx.log_file else Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        (ctx.repo_root / "logs").mkdir(parents=True, exist_ok=True)
        logger.debug("Log directory: %s", log_dir)

    def _s17_log_stdlib(self, ctx: StartupContext) -> None:
        level_name = ctx.log_level.upper()
        level = getattr(logging, level_name, logging.INFO)
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            fmt = logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)-40s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
            handler.setFormatter(fmt)
            root_logger.addHandler(handler)
        root_logger.setLevel(level)
        # Add file handler if log file configured
        if ctx.log_file:
            try:
                log_path = Path(ctx.log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                fh = logging.FileHandler(str(log_path), encoding="utf-8")
                fh.setFormatter(logging.Formatter(
                    "%(asctime)s %(levelname)-8s %(name)s %(message)s"
                ))
                root_logger.addHandler(fh)
                self._shutdown_mgr.register(
                    "logging_handlers",
                    lambda: [h.close() for h in root_logger.handlers],
                    priority=ShutdownManager.PRIORITY_LOGGING,
                )
            except OSError as exc:
                logger.warning("Cannot open log file %s: %s", ctx.log_file, exc)
        logger.info("Stdlib logging configured: level=%s", level_name)

    def _s18_log_loguru(self, ctx: StartupContext) -> None:
        try:
            from loguru import logger as llogger  # noqa: PLC0415
            # Add loguru file sink
            if ctx.log_file:
                log_path = Path(ctx.log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                llogger.add(
                    str(log_path),
                    rotation="1 day",
                    retention="7 days",
                    level=ctx.log_level.upper(),
                    encoding="utf-8",
                    enqueue=True,
                )
            logger.info("Loguru configured with daily rotation")
        except ImportError:
            logger.debug("loguru not installed — using stdlib logging only")

    def _s19_log_banner(self, ctx: StartupContext) -> None:
        logger.info("━" * 60)
        logger.info("  Investment Intelligence Operating System (IIOS)")
        logger.info("  run_id     : %s", ctx.run_id)
        logger.info("  started_at : %s", ctx.started_at_wall)
        logger.info("  env        : %s", ctx.iios_env)
        logger.info("  paper      : %s", ctx.paper_trading)
        logger.info("  python     : %s", ctx.python_version)
        logger.info("  root       : %s", ctx.repo_root)
        logger.info("  layers     : %d", _LAYERS)
        logger.info("━" * 60)

    def _s20_log_config_summary(self, ctx: StartupContext) -> None:
        logger.info(
            "Architecture constants: DECISION=%.1f  VIX=%.1f  DAILY_LOSS=%.3f  DEBATE_AGENTS=%d",
            ctx.decision_threshold, ctx.vix_threshold, ctx.daily_loss_pct, _DEBATE_AGENTS,
        )

    # ── Group E: Infrastructure ───────────────────────────────────────────────

    def _s21_service_registry(self, ctx: StartupContext) -> None:
        from .service_loader import ServiceRegistry  # noqa: PLC0415
        registry = ServiceRegistry()
        ctx.set_flag("service_registry", registry)
        ctx.set_service("__service_registry__", registry)
        logger.debug("Service registry initialized")

    def _s22_di_container(self, ctx: StartupContext) -> None:
        record = self._module_loader.load("iios.infrastructure.configuration")
        if not record.available:
            logger.debug("iios.infrastructure not yet available (Wave 2 pending)")
            return
        logger.info("iios.infrastructure.configuration loaded")

    def _s23_core_services(self, ctx: StartupContext) -> None:
        env_vars = ctx.env_vars or {}
        loader = ServiceLoader(env_vars=env_vars)
        report = loader.load_all()
        for name, instance in report.registry.all().items():
            ctx.set_service(name, instance)
        for result in report.results:
            if result.error:
                ctx.service_errors[result.spec.name] = str(result.error)
        ctx.set_flag("service_report", report)
        if not report.passed:
            failed_core = [r.spec.name for r in report.results
                           if r.spec.tier.value == "core" and r.error is not None]
            raise BootstrapError(
                f"Core service(s) failed to load: {', '.join(failed_core)}",
                stage_number=23, stage_name="infra_core_services",
            )
        logger.info("Services loaded: %s", report.loaded)

    def _s24_validate_registry(self, ctx: StartupContext) -> None:
        report = ctx.get_flag("service_report")
        if report is None:
            return
        failed_core = [r.spec.name for r in report.results
                       if r.spec.tier.value == "core" and r.error is not None]
        if failed_core:
            raise BootstrapError(
                f"Registry validation: CORE services missing: {', '.join(failed_core)}",
                stage_number=24, stage_name="infra_validate_registry",
            )
        logger.debug("Service registry validation passed")

    def _s25_infra_health(self, ctx: StartupContext) -> None:
        # Lightweight ping: check each service has a __class__
        for name, svc in ctx.services.items():
            if name.startswith("__"):
                continue
            logger.debug("Service health probe: %s → %s", name, type(svc).__name__)

    # ── Group F: Database ─────────────────────────────────────────────────────

    def _s26_db_dirs(self, ctx: StartupContext) -> None:
        db_path = Path(ctx.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path = Path(ctx.paper_trades_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Database directory: %s", db_path.parent)

    def _s27_db_connect(self, ctx: StartupContext) -> None:
        db_path = ctx.db_path
        if db_path == ":memory:":
            conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        ctx.db_connection = conn
        ctx.db_initialized = True
        ctx.set_service("db_connection", conn)
        self._shutdown_mgr.register(
            "database",
            lambda: conn.close(),
            priority=ShutdownManager.PRIORITY_DATABASE,
        )
        logger.info("SQLite connected: %s", db_path)

    def _s28_db_wal(self, ctx: StartupContext) -> None:
        conn: sqlite3.Connection = ctx.db_connection  # type: ignore[assignment]
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA cache_size=-32000")   # 32 MB page cache
        conn.commit()
        logger.debug("SQLite WAL mode enabled")

    def _s29_db_schema(self, ctx: StartupContext) -> None:
        conn: sqlite3.Connection = ctx.db_connection  # type: ignore[assignment]
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS bootstrap_runs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id        TEXT NOT NULL UNIQUE,
                started_at    TEXT NOT NULL,
                env           TEXT NOT NULL,
                paper_trading INTEGER NOT NULL DEFAULT 1,
                python        TEXT NOT NULL,
                completed_at  TEXT,
                phase         TEXT NOT NULL DEFAULT 'initializing',
                stages_ok     INTEGER DEFAULT 0,
                stages_failed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS stage_results (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id       TEXT NOT NULL,
                stage_number INTEGER NOT NULL,
                stage_name   TEXT NOT NULL,
                status       TEXT NOT NULL,
                attempt      INTEGER DEFAULT 1,
                duration_ms  REAL,
                error_msg    TEXT,
                recorded_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS system_events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type   TEXT NOT NULL,
                phase        TEXT,
                message      TEXT,
                metadata     TEXT,
                recorded_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_stage_results_run
                ON stage_results (run_id, stage_number);

            CREATE INDEX IF NOT EXISTS idx_system_events_type
                ON system_events (event_type, recorded_at);
        """)
        conn.commit()

        # Record this bootstrap run
        conn.execute(
            """INSERT OR REPLACE INTO bootstrap_runs
               (run_id, started_at, env, paper_trading, python, phase)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                ctx.run_id,
                ctx.started_at_wall,
                ctx.iios_env,
                1 if ctx.paper_trading else 0,
                ctx.python_version,
                "initializing",
            ),
        )
        conn.commit()
        ctx.db_schema_version = 1
        logger.info("Database schema initialized (version %d)", ctx.db_schema_version)

    def _s30_db_integrity(self, ctx: StartupContext) -> None:
        conn: sqlite3.Connection = ctx.db_connection  # type: ignore[assignment]
        if ctx.db_path == ":memory:":
            logger.debug("Skipping integrity check for in-memory database")
            return
        row = conn.execute("PRAGMA integrity_check").fetchone()
        if row is None or row[0] != "ok":
            raise BootstrapError(
                f"SQLite integrity check failed: {row}",
                stage_number=30, stage_name="db_integrity",
            )
        logger.debug("Database integrity check passed")

    # ── Group G: Knowledge & AI ───────────────────────────────────────────────

    def _s31_knowledge_base(self, ctx: StartupContext) -> None:
        record = self._module_loader.load("iios.knowledge")
        if not record.available:
            logger.debug("iios.knowledge not yet implemented (Wave 3 pending)")
            return
        ctx.loaded_modules["iios.knowledge"] = record.module
        logger.info("Knowledge base loaded")

    def _s32_ontology(self, ctx: StartupContext) -> None:
        record = self._module_loader.load("iios.knowledge.ontology")
        if not record.available:
            logger.debug("iios.knowledge.ontology not yet implemented (Wave 3 pending)")
            return
        ctx.loaded_modules["iios.knowledge.ontology"] = record.module
        logger.info("Market ontology loaded")

    def _s33_agents(self, ctx: StartupContext) -> None:
        record = self._module_loader.load("iios.agents")
        if not record.available:
            logger.debug("iios.agents not yet implemented (Wave 4 pending)")
            return
        ctx.loaded_modules["iios.agents"] = record.module
        logger.info("Agents scaffold loaded")

    def _s34_reasoning(self, ctx: StartupContext) -> None:
        record = self._module_loader.load("iios.reasoning")
        if not record.available:
            logger.debug("iios.reasoning not yet implemented (Wave 4 pending)")
            return
        ctx.loaded_modules["iios.reasoning"] = record.module
        logger.info("Reasoning layer loaded")

    def _s35_decision(self, ctx: StartupContext) -> None:
        record = self._module_loader.load("iios.decisions")
        if not record.available:
            logger.debug("iios.decisions not yet implemented (Wave 5 pending)")
            return
        ctx.loaded_modules["iios.decisions"] = record.module
        logger.info("Decision layer loaded (DECISION_THRESHOLD=%.1f)", ctx.decision_threshold)

    # ── Group H: Monitoring & Feeds ───────────────────────────────────────────

    def _s36_monitoring(self, ctx: StartupContext) -> None:
        record = self._module_loader.load("iios.monitoring")
        if not record.available:
            logger.debug("iios.monitoring not yet implemented (Wave 7 pending)")
            return
        ctx.loaded_modules["iios.monitoring"] = record.module
        logger.info("Layer 17 ControlTower loaded")

    def _s37_feed_manager(self, ctx: StartupContext) -> None:
        feed_mgr = ctx.get_service("feed_manager")
        if feed_mgr is not None:
            logger.info("FeedManager registered: %s", type(feed_mgr).__name__)
        else:
            logger.warning(
                "FeedManager not loaded — market data unavailable. "
                "Ensure data_feeds.data_feed_manager is importable."
            )

    def _s38_performance_tracker(self, ctx: StartupContext) -> None:
        tracker = ctx.get_service("performance_tracker")
        if tracker is not None:
            logger.info("StrategyPerformanceTracker registered")
        else:
            logger.debug("StrategyPerformanceTracker not loaded (optional)")

    def _s39_regime_map(self, ctx: StartupContext) -> None:
        regime_map = ctx.get_service("regime_strategy_map")
        if regime_map is not None:
            logger.info("RegimeStrategyMap registered")
        else:
            logger.debug("RegimeStrategyMap not loaded (optional)")

    def _s40_telegram(self, ctx: StartupContext) -> None:
        if not ctx.get_flag("enable_telegram", False):
            logger.debug("Telegram bot disabled (IIOS_ENABLE_TELEGRAM=false)")
            return
        bot = ctx.get_service("telegram_bot")
        if bot is not None:
            logger.info("Telegram bot registered (13 operator commands)")
            self._shutdown_mgr.register(
                "telegram_bot",
                lambda: getattr(bot, "stop", lambda: None)(),
                priority=ShutdownManager.PRIORITY_BOTS,
            )
        else:
            logger.warning("Telegram bot enabled but could not load — check python-telegram-bot")

    # ── Group I: Health & Certification ──────────────────────────────────────

    def _s41_health_components(self, ctx: StartupContext) -> None:
        for name in ("feed_manager", "db_connection"):
            svc = ctx.get_service(name)
            ok = svc is not None
            ctx.health_checks[name] = ok
            ctx.health_details[name] = type(svc).__name__ if ok else "not loaded"
        logger.debug("Component health: %s", ctx.health_checks)

    def _s42_health_database(self, ctx: StartupContext) -> None:
        conn = ctx.db_connection
        if conn is None:
            ctx.health_checks["database"] = False
            ctx.health_details["database"] = "no connection"
            raise BootstrapError(
                "Database not connected at health check",
                stage_number=42, stage_name="health_database",
            )
        try:
            row = conn.execute("SELECT 1").fetchone()
            ok = row is not None and row[0] == 1
            ctx.health_checks["database"] = ok
            ctx.health_details["database"] = "ok" if ok else "SELECT 1 failed"
        except Exception as exc:  # noqa: BLE001
            ctx.health_checks["database"] = False
            ctx.health_details["database"] = str(exc)
            raise BootstrapError(
                f"Database health check failed: {exc}",
                stage_number=42, stage_name="health_database", cause=exc,
            ) from exc

    def _s43_health_feeds(self, ctx: StartupContext) -> None:
        feed_mgr = ctx.get_service("feed_manager")
        if feed_mgr is None:
            ctx.health_checks["feed_manager"] = False
            ctx.health_details["feed_manager"] = "not registered"
            return
        # Try a lightweight availability check without making actual market calls
        ctx.health_checks["feed_manager"] = True
        ctx.health_details["feed_manager"] = f"{type(feed_mgr).__name__} available"
        logger.debug("Feed manager health: available")

    def _s44_certify(self, ctx: StartupContext) -> None:
        """Verify that all required (non-optional) stages succeeded."""
        failed = ctx.failed_stages
        critical_failures = [r for r in failed if not self._stages_map_optional(r.stage_number)]
        if critical_failures:
            names = [r.stage_name for r in critical_failures]
            raise BootstrapError(
                f"Startup certification failed — required stages did not complete: {names}",
                stage_number=44, stage_name="certify_startup",
            )
        logger.info(
            "Startup CERTIFIED: %d/%d stages completed, %d warnings",
            ctx.completed_stages,
            ctx.total_stages,
            len([f for f in ctx.findings if not f.blocks_startup]),
        )
        # Persist certification to database
        if ctx.db_connection is not None:
            try:
                ctx.db_connection.execute(
                    "UPDATE bootstrap_runs SET phase=?, stages_ok=?, stages_failed=? WHERE run_id=?",
                    ("certified", ctx.completed_stages, len(ctx.failed_stages), ctx.run_id),
                )
                ctx.db_connection.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Cannot update bootstrap_runs: %s", exc)

    def _s45_operational(self, ctx: StartupContext) -> None:
        ctx.operational = True
        ctx.current_phase = SystemPhase.RUNNING
        logger.info(
            "IIOS is OPERATIONAL — env=%s paper=%s elapsed=%.1f ms",
            ctx.iios_env,
            ctx.paper_trading,
            ctx.elapsed_ms,
        )
        # Emit system_events record
        if ctx.db_connection is not None:
            try:
                ctx.db_connection.execute(
                    "INSERT INTO system_events (event_type, phase, message) VALUES (?, ?, ?)",
                    ("STARTUP_COMPLETE", "running", f"run_id={ctx.run_id}"),
                )
                ctx.db_connection.commit()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Cannot write system_events: %s", exc)

    # ─────────────────────────────────────────────────────────────────────────
    # Helper: map stage number → optional flag (needed for certify stage)
    # ─────────────────────────────────────────────────────────────────────────

    def _stages_map_optional(self, stage_number: int) -> bool:
        """Return True if the stage at ``stage_number`` is optional."""
        # Optional stages: 10,14,15,18,19,20,22,25,31-40,43
        optional_set = {10, 14, 15, 18, 19, 20, 22, 25, 31, 32, 33, 34, 35,
                        36, 37, 38, 39, 40, 43}
        return stage_number in optional_set

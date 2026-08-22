# iios.bootstrap

> **Status:** IMPLEMENTED — Wave 2 complete  
> **Spec:** IIOS-BSS-001 | **Foundation:** IIOS-FCR-001 (CERTIFIED)

The **Bootstrap Engine** initialises the entire IIOS platform in 45 ordered stages.
It is the authoritative entry point for starting, pausing, resuming, and shutting
down the system.

---

## Quick Start

```python
from iios.bootstrap import BootstrapEngine

engine = BootstrapEngine()
context = engine.start()      # runs all 45 stages
# IIOS is now in SystemPhase.RUNNING
engine.shutdown()             # graceful teardown
```

---

## Package Contents

| Module | Purpose |
|--------|---------|
| `bootstrap_engine.py` | Main orchestrator — 45-stage startup pipeline |
| `startup_manager.py` | Executes stages in order with retry and dependency logic |
| `shutdown_manager.py` | Ordered graceful shutdown with per-component timeouts |
| `lifecycle_manager.py` | Lifecycle state machine (Initialize→Start→Run→Stop→Shutdown) |
| `startup_context.py` | Mutable context object accumulated across all stages |
| `startup_state.py` | Enums, result types, stage descriptors, BootstrapError |
| `startup_validator.py` | Orchestrates all pre-startup validation checks |
| `system_state.py` | Thread-safe global phase singleton (`get_system_state()`) |
| `repository_validator.py` | Validates repository structure and write access |
| `environment_loader.py` | Loads and validates .env files |
| `configuration_loader.py` | Imports config.py and validates architecture constants |
| `dependency_loader.py` | Probes installed packages by tier (CRITICAL/REQUIRED/OPTIONAL) |
| `module_loader.py` | Dynamic module loading with registry and reload support |
| `service_loader.py` | Loads IIOS services via canonical factory functions |

---

## 45-Stage Startup Sequence

### Group A: Pre-Validation (Stages 1–5)
| # | Stage | Description |
|---|-------|-------------|
| 1 | `python_version` | Verify Python >= 3.12 |
| 2 | `repo_structure` | Validate directory structure |
| 3 | `write_access` | Verify data/ and logs/ are writable |
| 4 | `required_files` | Check config.py, main.py exist |
| 5 | `package_init_files` | Verify iios/__init__.py files |

### Group B: Environment (Stages 6–10)
| # | Stage | Description |
|---|-------|-------------|
| 6 | `env_file_discovery` | Locate .env.development / .env |
| 7 | `env_load` | Load variables from .env file |
| 8 | `env_validate` | Validate required env vars |
| 9 | `env_type_coerce` | Coerce typed vars (bool, int, float) |
| 10 | `env_audit` | Emit environment audit log (optional) |

### Group C: Configuration (Stages 11–15)
| # | Stage | Description |
|---|-------|-------------|
| 11 | `config_import` | Import config.py module |
| 12 | `config_constants` | Validate DECISION_THRESHOLD, VIX_THRESHOLD, DAILY_LOSS_PCT |
| 13 | `config_risk_thresholds` | Sanity check risk parameters |
| 14 | `config_broker` | Validate broker config (optional) |
| 15 | `config_audit` | Log configuration summary (optional) |

### Group D: Logging (Stages 16–20)
| # | Stage | Description |
|---|-------|-------------|
| 16 | `log_directories` | Create logs/ directory |
| 17 | `log_stdlib` | Configure Python stdlib logging |
| 18 | `log_loguru` | Configure loguru with daily rotation (optional) |
| 19 | `log_startup_banner` | Emit structured startup banner (optional) |
| 20 | `log_config_summary` | Log architecture constants (optional) |

### Group E: Infrastructure (Stages 21–25)
| # | Stage | Description |
|---|-------|-------------|
| 21 | `infra_service_registry` | Initialize in-process service registry |
| 22 | `infra_di_container` | Initialize DI container (optional, Wave 2) |
| 23 | `infra_core_services` | Load core services via factory functions |
| 24 | `infra_validate_registry` | Verify all CORE services loaded |
| 25 | `infra_health_probe` | Ping each registered service (optional) |

### Group F: Database (Stages 26–30)
| # | Stage | Description |
|---|-------|-------------|
| 26 | `db_directories` | Create data/ directory |
| 27 | `db_connect` | Open SQLite connection |
| 28 | `db_wal_mode` | Enable WAL journal mode |
| 29 | `db_schema` | Initialize schema / run migrations |
| 30 | `db_integrity` | PRAGMA integrity_check |

### Group G: Knowledge & AI (Stages 31–35, all optional until Wave 4+)
| # | Stage | Description |
|---|-------|-------------|
| 31 | `knowledge_base` | Load iios.knowledge (Wave 3) |
| 32 | `ontology_layer` | Load iios.knowledge.ontology (Wave 3) |
| 33 | `agents_scaffold` | Probe iios.agents (Wave 4) |
| 34 | `reasoning_layer` | Load iios.reasoning (Wave 4) |
| 35 | `decision_layer` | Load iios.decisions with DECISION_THRESHOLD=6.5 (Wave 5) |

### Group H: Monitoring & Feeds (Stages 36–40)
| # | Stage | Description |
|---|-------|-------------|
| 36 | `monitoring_init` | Load Layer 17 ControlTower (Wave 7, optional) |
| 37 | `feed_manager` | Register FeedManager singleton |
| 38 | `performance_tracker` | Register StrategyPerformanceTracker singleton |
| 39 | `regime_strategy_map` | Register RegimeStrategyMap singleton |
| 40 | `telegram_bot` | Register Telegram bot if IIOS_ENABLE_TELEGRAM=true |

### Group I: Health & Certification (Stages 41–45)
| # | Stage | Description |
|---|-------|-------------|
| 41 | `health_components` | Check all component health |
| 42 | `health_database` | Verify database SELECT 1 |
| 43 | `health_feeds` | Probe feed manager connectivity (optional) |
| 44 | `certify_startup` | Assert all required stages completed |
| 45 | `enter_operational` | Set operational=True, emit ready signal |

---

## Lifecycle State Machine

```
UNINITIALIZED
    → INITIALIZING  (engine.start() called)
    → INITIALIZED   (pre-validation complete)
    → STARTING      (stages executing)
    → RUNNING       (all required stages done)
    → CERTIFIED     (SYSTEM_CERTIFIED criteria met)
    → PAUSING → PAUSED → RESUMING → RUNNING
    → STOPPING → STOPPED → SHUTTING_DOWN → SHUTDOWN
    → FAILED → RECOVERY → INITIALIZING | RUNNING
    → MAINTENANCE → RUNNING | STOPPING
```

All transitions are validated. Invalid transitions raise `LifecycleError`.

---

## Architecture Invariants

These constants are validated in stage 12 and must not be changed without Architecture Council approval:

| Constant | Value | Rule |
|----------|-------|------|
| `DECISION_THRESHOLD` | 6.5 | FC-RULE-017 |
| `VIX_THRESHOLD` | 45.0 | FC-RULE-018 |
| `DAILY_LOSS_PCT` | 0.02 | FC-RULE-018 |

---

## Recovery Procedure

If the engine fails during startup:

```python
from iios.bootstrap import BootstrapEngine, get_system_state, SystemPhase

state = get_system_state()
print(state.current_phase)        # SystemPhase.FAILED

# Option 1: Reset and retry
state.reset()
engine = BootstrapEngine()
ctx = engine.start()

# Option 2: Enter recovery mode via LifecycleManager
engine.lifecycle.enter_recovery()
# investigate ctx.failed_stages
# fix the root cause
engine.lifecycle.initialize()
# ... re-run specific stages
```

---

## Testing

```powershell
# Unit tests only (fast, < 3s)
pytest tests/unit/bootstrap/ -v

# Integration tests (runs real engine against repo)
pytest tests/unit/bootstrap/ -m integration -v
```

Current status: **97/97 tests passing**

---

*Architecture Reference: IIOS-BSS-001*  
*Foundation: IIOS-FCR-001 (CERTIFIED)*
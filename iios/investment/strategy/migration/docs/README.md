# Strategy Migration Framework

## Overview

The Strategy Migration Framework provides a deterministic, reversible, versioned, and auditable
pathway for migrating legacy strategies into the IIOS (Institutional Investment Operating System)
framework.

**Key Principle**: This framework does NOT redesign existing strategies.
It wraps them in IIOS-compatible interfaces while preserving all original logic.

---

## Package Structure

```
iios/investment/strategy/migration/
│
├── __init__.py                    # Public API exports
│
├── migration_status.py            # Enums: MigrationStatus, CompatibilityLevel, etc.
├── migration_events.py            # MigrationEventBus for lifecycle events
│
├── legacy_metadata.py             # LegacyStrategyMetadata dataclass
├── legacy_registry.py             # In-memory registry of code-based strategies
├── legacy_catalog.py              # Searchable catalog across all sources
├── legacy_discovery.py            # Scans all legacy sources
│
├── strategy_adapter.py            # LegacyStrategyAdapter(BaseStrategy)
├── adapter_registry.py            # Thread-safe adapter store
├── adapter_factory.py             # Creates the right adapter mode
├── compatibility_layer.py         # Parameter/regime translation utilities
│
├── validation_report.py           # ValidationCheck, ValidationReport types
├── compatibility_validator.py     # 6-category compatibility checks
├── migration_validator.py         # Metadata + adapter validation
│
├── migration_steps.py             # Step types and step executor
├── migration_statistics.py        # Thread-safe counters
├── migration_session.py           # Per-strategy state machine
├── migration_pipeline.py          # Multi-strategy orchestrator
│
├── signal_comparator.py           # Field-by-field parameter comparison
├── signal_equivalence.py          # Signal equivalence check
├── behavior_validator.py          # Behavior equivalence from test cases
├── result_comparator.py           # Aggregated comparison result
│
├── migration_report.py            # MigrationReport (immutable)
├── migration_summary.py           # Aggregated batch summary
├── migration_audit.py             # Append-only audit log
├── migration_confidence.py        # Weighted confidence scorer
│
└── strategy_migration_engine.py   # Main facade (use this)
```

---

## Quick Start

```python
from iios.investment.strategy.migration import StrategyMigrationEngine

# 1. Create engine
engine = StrategyMigrationEngine()

# 2. Discover all legacy strategies
result = engine.discover()
print(f"Found {result.total_discovered} strategies")

# 3. Migrate one strategy
session = engine.migrate("Breakout_Volume")
print(session.status)  # COMPLETED or APPROVAL_PENDING

# 4. Migrate all (approved only)
sessions = engine.migrate_all(approved_only=True)

# 5. Get a report
report = engine.get_report("Breakout_Volume")
print(report.approval_recommendation)  # APPROVE / REVIEW / REJECT

# 6. Full summary
summary = engine.summary()
print(summary.to_dict())
```

---

## Migration Pipeline Phases

| Phase | Description |
|---|---|
| DISCOVERY | Locate strategy metadata |
| VALIDATION | Compatibility checks (6 categories) |
| PREPARATION | Create LegacyStrategyAdapter |
| MIGRATION | Register adapter |
| VERIFICATION | Behavior equivalence check |
| APPROVAL | Auto or manual approval |
| ROLLBACK | Undo migration from checkpoint |
| ARCHIVE | Archive completed sessions |

---

## Compatibility Levels

| Level | Meaning |
|---|---|
| FULL | All parameters map directly, no gaps |
| PARTIAL | Minor warnings, no blocking issues |
| REQUIRES_ADAPTER | Gaps found, adapter needed |
| INCOMPATIBLE | Blocking errors — manual review required |

---

## Sources Supported

| Source | Location |
|---|---|
| `STRATEGY_GENERATOR` | `STRATEGY_PARAMS` dict in `strategy_lab/strategy_generator_ai.py` |
| `META_CONTROLLER` | `_REGIME_MAP` in `strategy_lab/meta_strategy_controller.py` |
| `DISCOVERED_EDGES` | `data/discovered_edges.json` |
| `EVOLVED_STRATEGIES` | `data/evolved_strategies.json` |

---

## Tests

```powershell
cd "C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain"
.venv\Scripts\python.exe -m pytest tests/unit/investment/strategy/migration/ -v
```

180 tests, all passing.

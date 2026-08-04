# Technical Debt Register
## AR-001 Part 11: Legacy Code, Patches, Duplicate Calculations, Obsolete Modules

**Date:** 2026-08-04

---

## 1. Register Format

Each item includes:
- **ID** — Unique identifier
- **Location** — File / package
- **Type** — `Legacy` | `Patch` | `Duplicate` | `Obsolete` | `Design`
- **Description** — What the problem is
- **Risk** — `Critical` | `High` | `Medium` | `Low`
- **Effort** — `High` | `Medium` | `Low`

---

## 2. Critical Items

### TD-001 — MLS not wired to trading (Design)
**Location:** `market_learning/`, `orchestrator/master_orchestrator.py`  
**Type:** Design gap  
**Risk:** Critical — 8 phases of work produce zero trading influence  
**Effort:** Medium  
**Description:** All MLS phases (1–5B) produce results that are not consumed
by the trading path. DNA patterns, PMCI scores, CDS relevance — all generated,
none consumed. This is the single largest technical debt in the system.  
**Resolution path:** PMCI_INTEGRATION_REVIEW.md steps 1–5.

---

### TD-002 — `master_orchestrator.py` god object (Design)
**Location:** `orchestrator/master_orchestrator.py` (5,900+ LOC)  
**Type:** Design / legacy  
**Risk:** High — monolithic failure point, untestable in isolation  
**Effort:** High  
**Description:** The orchestrator imports from 15+ packages, contains
scheduling logic, coordination logic, recovery logic, and error handling
all in one file. Any change risks breaking another section.  
**Resolution path:** Extract `MarketCoordinator`, `TradingCoordinator`,
`LearningCoordinator` as per R-002.

---

## 3. High Items

### TD-003 — CorrelationEngine triplicated (Duplicate)
**Location:** `global_intelligence/`, `capital_risk_engine/`, `risk_control/`  
**Type:** Duplicate  
**Risk:** High — divergent formulae risk numerical inconsistency  
**Effort:** Medium  
**Description:** Three copies of correlation logic with independent maintenance.
See INTELLIGENCE_DUPLICATION_AUDIT.md.  
**Resolution path:** Merge to `analytics/correlation_engine.py`.

---

### TD-004 — `strategy_performance.db` legacy SQLite (Legacy)
**Location:** `data/strategy_performance.db`  
**Type:** Legacy  
**Risk:** High — tools may query stale DB instead of live JSON  
**Effort:** Low  
**Description:** `StrategyPerformanceTracker` uses `strategy_performance.json`
as primary store. The SQLite DB appears to be from an earlier implementation.
It may contain stale data that confuses any tool iterating `data/` databases.  
**Resolution path:** Verify DB is empty/stale; rename to `strategy_performance.db.archive`.

---

### TD-005 — `AngelOneBroker` loaded but inactive (Obsolete)
**Location:** `execution_engine/brokers/angelone_broker.py`  
**Type:** Obsolete  
**Risk:** Medium — adds import overhead and confusion  
**Effort:** Low  
**Description:** AngelOne is not listed as `ACTIVE_BROKER` in `config.py`.
The broker is imported at startup. If `angelone_feed.py` has side effects
(e.g., tries to connect) this is wasteful.  
**Resolution path:** Guard imports with `ACTIVE_BROKER` check.

---

### TD-006 — Three WalkForward implementations (Duplicate)
**Location:** `strategy_lab/backtesting_ai.py`, `validation_engine/walkforward_test.py`,
`performance/walk_forward_tester.py`  
**Type:** Duplicate  
**Risk:** Medium — different split logic may produce inconsistent OOS periods  
**Effort:** Medium  
**Description:** Three implementations of IS/OOS date splitting. No guarantee
they use the same boundary calculation.  
**Resolution path:** Extract `split_oos(prices, is_ratio=0.70)` to
`utils/walk_forward_split.py`.

---

### TD-007 — Hardcoded 14 scenarios in SimulationEngine (Design)
**Location:** `market_simulation/scenario_generator.py`  
**Type:** Design  
**Risk:** Medium — new market regimes require code changes not config changes  
**Effort:** Low  
**Description:** The 14 scenarios are hardcoded. Adding a 15th scenario
(e.g., crypto contagion) requires modifying the scenario generator code.  
**Resolution path:** Move scenario definitions to `config/scenarios.json`.

---

## 4. Medium Items

### TD-008 — `data/study002_results.json` and `data/study002a_results.json` orphaned (Obsolete)
**Location:** `data/`  
**Type:** Obsolete  
**Risk:** Low — disk space, clarity  
**Effort:** Low  
**Resolution path:** Archive to `data/archive/ar_studies/`.

---

### TD-009 — `study002_replay.db` and `re001_replay.db` orphaned (Obsolete)
**Location:** `data/`  
**Type:** Obsolete  
**Risk:** Low — same as TD-008  
**Effort:** Low  
**Resolution path:** Archive to `data/archive/ar_studies/`.

---

### TD-010 — `candidates.json` full-rewrite every 30s (Performance)
**Location:** `opportunity_engine/candidate_store.py`  
**Type:** Performance / design  
**Risk:** Medium — unnecessary I/O, file contention under concurrent reads  
**Effort:** Low  
**Resolution path:** Move candidates to SQLite table in `trading_brain.db`;
use incremental UPSERT instead of full JSON rewrite.

---

### TD-011 — `AgentMemory` has no eviction policy (Performance)
**Location:** `communication/agent_memory.py`  
**Type:** Performance  
**Risk:** Medium — memory growth over multi-day runs  
**Effort:** Low  
**Resolution path:** Add `maxlen=10000` deque eviction or TTL of 24 hours.

---

### TD-012 — `research_integrity.py` legacy weight functions (Legacy)
**Location:** `learning_system/research_integrity.py`  
**Type:** Legacy  
**Risk:** Low — `RESEARCH_WEIGHT_LEGACY_STATIC = 0.25` is frozen  
**Effort:** Low  
**Description:** Legacy weight functions pre-date the prepared universe.
The file mixes architecture-generation tagging with legacy weight constants.  
**Resolution path:** Extract tagging to its own file; retire legacy constants
(they are never used when `USE_PREPARED_UNIVERSE = True`).

---

### TD-013 — `api_tokens.json` plaintext credentials (Security)
**Location:** `config/api_tokens.json`  
**Type:** Security debt  
**Risk:** High — credentials exposed if `config/` is accidentally committed  
**Effort:** Medium  
**Description:** API credentials stored in plaintext JSON.
Mitigation: `.gitignore` should exclude `config/`. But `.gitignore` does
not protect against directory listing or accidental expose.  
**Resolution path:** Move to OS keyring or environment variables;
read via `os.getenv()` with fallback to file.

---

## 5. Low Items

### TD-014 — `analysis/` tooling not tested (Legacy)
**Location:** `analysis/` (57 files)  
**Type:** Legacy tooling  
**Risk:** Low — tooling, not production path  
**Effort:** Low  
**Description:** 57 analysis files with no test suite. These are ad-hoc
audit scripts. If any are used in production reporting, they need tests.

---

### TD-015 — `iios/` skeleton not activated (Design)
**Location:** `iios/`  
**Type:** Future state, not yet active  
**Risk:** Low  
**Description:** The IIOS framework skeleton (`agents/`, `api/`, `decision/`,
`knowledge/`, `market/`, `workflow/`) exists but is not imported by
any production code. The `iios.db` may be written by the skeleton.  
**Resolution path:** Activate as `ScientificDirector` prerequisite (TD in COORDINATOR_READINESS.md).

---

## 6. Summary by Risk

| Risk | Count | IDs |
|---|---|---|
| Critical | 1 | TD-001 |
| High | 4 | TD-002, TD-003, TD-004, TD-013 |
| Medium | 6 | TD-005, TD-006, TD-007, TD-010, TD-011, TD-012 |
| Low | 4 | TD-008, TD-009, TD-014, TD-015 |

**Total: 15 technical debt items**

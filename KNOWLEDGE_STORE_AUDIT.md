# Knowledge Store Audit
## AR-001 Part 5: Every JSON/SQLite/CSV/Memory/Cache/Temp Store

**Date:** 2026-08-04

---

## 1. SQLite Databases (14 files in `data/`)

| # | Database | Size class | Owner | Write frequency | Status |
|---|---|---|---|---|---|
| 1 | `trading_brain.db` | Core | `DBManager` | Every trade | Active |
| 2 | `control_tower.db` | Core | `SystemMonitor` | Every cycle | Active |
| 3 | `options_audit.db` | Options | `OptionsRiskEngine` | Every options trade | Active |
| 4 | `trade_quality.db` | Quality | `TradeClassifier` | Per trade | Active |
| 5 | `iios.db` | IIOS | IIOS framework | Infrequent | Active (sparse) |
| 6 | `live_observations.db` | MLS | `MarketObserver` | Daily | Active |
| 7 | `news_audit.db` | Events | `EventDetectionAI` | Daily | Active |
| 8 | `recommendations.db` | Research | `ResearchLab` | Per promotion | Active |
| 9 | `real_options_audit.db` | Options | `OptionsOrderManager` | Per options order | Active |
| 10 | `replay.db` | Replay | Replay engine | On replay runs | Active |
| 11 | `study002_replay.db` | Research | AR Study 002 | Historical | **Historical only** |
| 12 | `re001_replay.db` | Research | RE001 | Historical | **Historical only** |
| 13 | `strategy_performance.db` | Learning | LearningSystem | Legacy | **LEGACY** |
| 14 | `rejection_audit.db` | Audit | `OpportunityEngine` | Per rejection | Active |

### Observations

**Issue SK-001:** `strategy_performance.db` appears to be a legacy database.
`StrategyPerformanceTracker` uses `strategy_performance.json` (JSON file) as primary.
The SQLite DB may be stale. **Recommend: verify and archive if unused.**

**Issue SK-002:** Two study databases (`study002_replay.db`, `re001_replay.db`)
are historical artefacts from specific AR studies. These consume disk space and
may confuse tools that iterate all DBs. **Recommend: move to `data/archive/`.**

**Issue SK-003:** 14 separate SQLite files risks cross-DB transaction atomicity.
No mechanism ensures that `trading_brain.db` (trade result) and
`control_tower.db` (telemetry) are written atomically after a trade.
**Recommend:** Consolidate to 4 databases (see R-005).

---

## 2. JSON Files (18 files in `data/` and `config/`)

### Configuration (3 files)

| File | Owner | Content | Sensitivity |
|---|---|---|---|
| `config/api_tokens.json` | Manual | API credentials (Dhan, Zerodha, AngelOne) | 🔴 HIGH |
| `config/dhan_oauth_config.json` | OAuth manager | Dhan OAuth settings, redirect URI | 🔴 HIGH |
| `config/kill_switch.json` | `utils/kill_switch.py` | `trading_enabled: bool` | 🟡 MEDIUM |

**Issue SK-004:** `config/api_tokens.json` stores credentials in plaintext.
These should be environment variables or an encrypted vault.
Current mitigations: `.gitignore` should exclude `config/`.

---

### Strategy & Performance State (6 files)

| File | Owner | Content | Write pattern |
|---|---|---|---|
| `data/strategy_performance.json` | `StrategyPerformanceTracker` | Win rate, Sharpe, DD per strategy | EOD write |
| `data/stability_ledger.json` | `StabilityLedger` | Stability score per strategy | EOD write |
| `data/options_outcomes.json` | `OptionsPerformanceTracker` | Options trade history | Per trade |
| `data/options_weights.json` | `OptionsPerformanceTracker` | Options strategy weights | Per update |
| `data/evolved_strategies.json` | `StrategyGeneratorAI` | Evolved strategy parameters | Per evolution run |
| `data/paper_trading_daily.json` | Orchestrator | Daily trade snapshot | Daily |

---

### Operational State (6 files)

| File | Owner | Content | Write pattern |
|---|---|---|---|
| `data/candidates.json` | `CandidateStore` | Live candidate lifecycle state | Per scan |
| `data/invalidation_tracker.json` | `InvalidationTracker` | Breakout invalidation events | Per event |
| `data/regime_probability_history.json` | `RegimeProbabilityModel` | Historical regime probabilities | Daily |
| `data/improvement_backlog.json` | `ImprovementBacklog` | Issue backlog | Per issue |
| `data/odm_state.json` | `OpportunityDensityMonitor` | Budget enforcement state | Per scan |
| `data/scanner_memory.json` | Scanner | Universe scan state | Per scan |

---

### Research & Discovery (3 files)

| File | Owner | Content | Write pattern |
|---|---|---|---|
| `data/discovered_edges.json` | `EdgeDiscoveryEngine` | Discovered market edges | Per discovery run |
| `data/study002_results.json` | AR Study 002 | Study results | Historical |
| `data/study002a_results.json` | AR Study 002A | Study 002A results | Historical |

**Issue SK-005:** Study result files are one-time artefacts with no reader in
the production trading path. **Recommend: archive to `data/archive/ar_studies/`.**

---

## 3. CSV Files (1 file)

| File | Owner | Content | Write pattern |
|---|---|---|---|
| `data/paper_trades.csv` | `OrderManager`, `PaperTradeLogger` | Paper trade journal | Per paper order |

**Note:** This is the primary paper trading record. It is also read by
`_do_eod_learning()` in `master_orchestrator.py` to recover trades post-restart.
Write contention is low (one writer, one reader at EOD).

---

## 4. In-Memory Caches (ephemeral)

| Component | Cache content | TTL / Eviction |
|---|---|---|
| `GlobalDataAI` | GlobalSnapshot (S&P, Nikkei, FX) | 5 minutes |
| `DataFeedManager` | Quote cache | Per request (short TTL) |
| `RegimeStrategyMap` | Regime→strategy map | In-memory, persisted on update |
| `CandidateStore` | Ranked candidates | Updated each scan |
| `CDSEngine._context_history` | Last 200 MCIContext objects | `deque(maxlen=200)` — auto-evict |
| `MCIEngine._context_cache` | Computed contexts | In-memory, deque |
| `PMCIEngine` | PMCI result cache | In-memory |

---

## 5. Log Files

| Path | Content | Rotation |
|---|---|---|
| `logs/trading_brain.log` | Main system log | Daily rotation (DailyFileHandler) |
| `logs/` (per-agent) | Agent-specific logs | Daily rotation |
| `simulation_logs/` | Monte Carlo traces, decision JSON | Per simulation run |

---

## 6. Knowledge Store Consolidation Recommendation

Current state: **14 SQLite + 18 JSON + 1 CSV + N log files = ~34 persistent stores**

**Target state:**

| Database | Merges |
|---|---|
| `trading_brain.db` | trades, positions, signals, orders, trade_quality, rejections |
| `learning_brain.db` | strategy_performance, stability_ledger, options_outcomes, eod_eval |
| `control_tower.db` | events, layer_timings, health, news, recommendations |
| `research_brain.db` | iios, live_observations, discovered_edges, replay |

JSON files: Keep operational state JSON files (candidates, invalidation, regime,
scanner_memory). Archive study/historical files. Merge performance JSONs into SQLite.

**Benefit:** Reduces store count by ~60%, eliminates legacy DB confusion,
enables atomic cross-table writes within each domain.

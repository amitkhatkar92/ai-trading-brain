# DATABASE PERSISTENCE ARCHITECTURE

**Document Series:** Investment Intelligence Operating System — Engineering Document Library
**Document Number:** 6 of 10
**Document Class:** Persistence Engineering Architecture
**Status:** Authoritative
**Version:** 1.0.0
**Date:** 2026-07-02
**Authors:** Human Principal / Engineering Foundation
**Governs:** Every storage layer, repository, data lifecycle, and persistence policy in the IIOS

---

## Scope and Authority

This document is the authoritative engineering design for all persistence concerns in the Investment Intelligence Operating System. It defines how every piece of information — from a market data tick to a 10-year strategy evolution trace — is stored, accessed, protected, versioned, and eventually archived or destroyed.

This document does **NOT** contain:
- SQL schema definitions
- ORM class definitions
- Table column specifications
- Database migration scripts
- Implementation code of any kind

This document **DOES** contain:
- The philosophical and engineering rationale for every persistence decision
- The complete map of all storage layers and their responsibilities
- The repository pattern design governing every data access boundary
- The complete data lifecycle for every domain entity
- The performance, backup, governance, and security architecture for persistence
- 75 mandatory persistence rules forming the Persistence Constitution

---

## Parent Documents

| Document | Authority |
|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | Engineering design bridge |
| `ENGINEERING_STANDARDS.md` | Mandatory engineering standards |
| `REPOSITORY_ARCHITECTURE.md` | Repository and package design |
| `CORE_FRAMEWORK_ARCHITECTURE.md` | Core framework and base classes |

---

## System Persistence Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 IIOS PERSISTENCE ARCHITECTURE                           │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Cognitive  │  │  Knowledge  │  │   Learning  │  │    Audit    │   │
│  │   Cycle     │  │  & Memory   │  │  & Evolution│  │  & Compliance│   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │
│         │                │                │                │           │
│  ┌──────▼──────────────────────────────────────────────────▼──────┐   │
│  │                  REPOSITORY LAYER (BaseRepository)              │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────▼──────────────────────────────────┐   │
│  │                     STORAGE LAYERS                              │   │
│  │  Operational  │  Historical  │  Knowledge  │  Cache  │  Archive │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────▼──────────────────────────────────┐   │
│  │                   PHYSICAL STORAGE                              │   │
│  │  SQLite (Primary) │ SQLite (History) │ JSON Files │ CSV │ Logs  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

- [Part I — Persistence Philosophy](#part-i)
- [Part II — Persistence Layers](#part-ii)
- [Part III — Storage Domains](#part-iii)
- [Part IV — Database Architecture](#part-iv)
- [Part V — Repository Pattern](#part-v)
- [Part VI — Data Lifecycle](#part-vi)
- [Part VII — Performance Strategy](#part-vii)
- [Part VIII — Backup and Recovery](#part-viii)
- [Part IX — Persistence Governance](#part-ix)
- [Part X — Persistence Constitution](#part-x)
- [Document Footer](#document-footer)
- [Supplement A — Domain Retention Matrix](#supplement-a)
- [Supplement B — Repository Interface Catalogue](#supplement-b)
- [Supplement C — Backup Schedule Matrix](#supplement-c)
- [Supplement D — Data Classification Framework](#supplement-d)
- [Supplement E — Persistence Governance Decision Records](#supplement-e)

---
## PART I — PERSISTENCE PHILOSOPHY

### 1.1 Purpose of Persistence in the IIOS

Persistence is not a technical afterthought in the Investment Intelligence Operating System. It is a first-class architectural concern, equal in importance to the intelligence of the AI agents, the reliability of the execution engine, and the integrity of the risk controls.

The IIOS is a system that **learns, evolves, and improves over time**. That evolution is only possible if the system can:
- Remember every decision it has ever made
- Understand why it made those decisions
- Measure whether those decisions were right or wrong
- Carry forward what it has learned into future decisions

Without persistence, the IIOS is a stateless computation engine — powerful in a single cycle, but unable to grow. With persistence designed correctly, the IIOS becomes an increasingly intelligent trading organism with an expanding institutional memory.

Every component of the system generates data worth preserving:
- **Market data** — the raw reality against which strategies are evaluated
- **Decisions** — the reasoning chains that produce or reject trade signals
- **Orders** — the intentions sent to execution; the record of operational actions
- **Trades** — the outcomes that generate P&L, the ultimate measure of system quality
- **Learning artefacts** — the evolved knowledge that differentiates this system from a static rule engine
- **Audit records** — the tamper-evident chain of all significant events
- **Configuration history** — the evolution of system parameters over time
- **Agent opinions** — the granular debate records that explain every conviction score

The purpose of the IIOS persistence architecture is to make all of this available, reliable, searchable, and protected — now and for the entire operational life of the system.

---

### 1.2 Reliability as the Foundation

A persistence layer that occasionally loses data is worse than no persistence layer. A trading system that silently corrupts its trade journal or drops audit records is not a trading system — it is a liability.

The IIOS persistence architecture is designed around one principle before all others: **reliability**. Every write must succeed or raise an exception that is handled. Every read must return what was written or raise an exception that is handled. Data loss — silent or detected — is never an acceptable outcome.

Reliability is achieved through:

| Mechanism | Description |
|---|---|
| Write-ahead logging (WAL) | The primary database uses WAL mode so writes are atomic and crash-safe |
| Synchronous I/O for critical writes | Audit records, trade records, and kill-switch events are written with `PRAGMA synchronous = FULL` |
| Append-only structures | Historical records, audit logs, and trade journals are append-only — no updates, no deletes |
| Checksums on critical files | Daily backup files carry SHA-256 checksums verified at write and at restore time |
| Retry with backoff | All persistence writes operate under the `DATABASE_RETRY_POLICY` — transient failures are retried |
| Circuit breaker | Repeated persistence failures trip the database circuit breaker and alert via Telegram |

---

### 1.3 Durability Guarantees

Durability means that once a write is acknowledged, the data survives a process crash, a system restart, a power loss, and a hardware failure.

**Durability tiers in the IIOS:**

| Tier | Examples | Guarantee |
|---|---|---|
| Tier 1 — Durable | Trade records, audit events, kill-switch state | Survive process crash + OS restart. Written with `FULL` sync. |
| Tier 2 — Persistent | Strategy state, learning artefacts, performance metrics | Survive process restart. Written with `NORMAL` sync. Daily backup. |
| Tier 3 — Session | In-cycle context, cache, pre-warmed data | Not required to survive restart. Rebuilt on next cycle. |
| Tier 4 — Ephemeral | In-memory scores, temporary arrays | Intentionally transient. No persistence. |

The separation of durability tiers prevents over-engineering (no need to write every in-memory array to disk) while ensuring that no critical data is vulnerable to loss.

---

### 1.4 Scalability as a Design Input

The IIOS currently operates on a single VPS with one SQLite database per domain. Scalability is not today's problem — but it must not be tomorrow's crisis.

Every architectural decision is evaluated against this question: **Will this decision constrain us when volume grows 10x?**

Scalability-oriented decisions embedded in this architecture:

| Decision | Scalability Benefit |
|---|---|
| Repository pattern | Swap storage backend without touching business logic |
| Domain-separated databases | Move any domain to a dedicated server without full migration |
| Append-only historical storage | Time-series partition is trivial on append-only data |
| Time-indexed market data | Supports partitioning by date with no schema change |
| Event-sourced audit log | Append-only event stream scales linearly |
| JSON serialisation for knowledge | Knowledge domain can move to a document store without re-architecture |

Scalability decisions are made once, during architecture, not during firefighting.

---

### 1.5 Availability

The IIOS must be able to read from its storage during every cognitive cycle. The system must never enter a state where the inability to read persisted data prevents a cycle from running.

**Availability design decisions:**

| Decision | Availability Benefit |
|---|---|
| Local SQLite (no network call) | Zero network latency; no remote DB outage risk |
| In-memory TTL cache for hot reads | Cycle-critical reads served from cache, not disk |
| Graceful degradation on read failure | If historical data cannot be read, cycle proceeds with reduced context rather than aborting |
| Read replicas for analytics | Analytics queries run against a separate read-only snapshot, never the primary database |
| Background pre-warm | Global data and sector context are pre-loaded before the cycle begins |

**Unacceptable availability patterns** (explicitly prohibited):
- Blocking the cognitive cycle on a slow database query
- Synchronously waiting for a backup to complete before continuing
- Reading the same record multiple times per cycle (use the context cache)
- Opening a new database connection for every query (use the connection pool)

---

### 1.6 Consistency Model

The IIOS uses a **strong consistency** model for operational data and an **eventual consistency** model for analytical and knowledge data.

| Data Category | Consistency Model | Rationale |
|---|---|---|
| Trade records | Strong (serialisable) | Financial record integrity; no partial writes |
| Order records | Strong (serialisable) | Execution state must be authoritative |
| Audit records | Strong (append-only) | Tamper evidence requires strict ordering |
| Kill-switch state | Strong | Safety-critical; must be the same in every read |
| Strategy performance metrics | Eventual | Aggregated over time; temporary inconsistency is acceptable |
| Learning artefacts | Eventual | Updated by background learning; delays are acceptable |
| Market data cache | Eventual | Staleness is managed by TTL, not consistency protocol |
| Knowledge store | Eventual | Reasoning traces and context evolve asynchronously |

Strong consistency is achieved through SQLite's serialised write mode. Eventual consistency is achieved by design: background processes update knowledge and analytics domains asynchronously, and callers read whatever version is currently available.

---

### 1.7 Performance Philosophy

**The persistence layer must never be the bottleneck in a cognitive cycle.**

Current cycle targets:
- Full cycle: < 5,000ms (current: 172ms)
- Per-layer: < 2,000ms (current: 17–19ms per layer)
- Persistence read within a cycle: < 50ms (cached), < 500ms (cold)

Performance design principles:

| Principle | Implementation |
|---|---|
| Read-heavy cycles use in-memory cache | TTL cache in `cache_utils` is used for all cycle-critical reads |
| Writes are never blocking in the hot path | All non-critical writes are queued to an async writer thread |
| Audit and learning writes are batched | Flush every 60 seconds, not after every event |
| Market data is pre-warmed before the cycle | `GlobalDataPrewarmer` runs every 300 seconds |
| Database connections are pooled | No new connection per query; connection reused from pool |
| Indexes support the exact query patterns used | Index design is based on observed query access patterns, not anticipated ones |

---

### 1.8 Historical Preservation

The IIOS is built to operate for **10 years**. Every market data point, every trade, every agent opinion, every learning event, every audit record must be retrievable 10 years from now.

Historical preservation requirements:

| Domain | Preservation Guarantee | Medium |
|---|---|---|
| Trade records | Permanent (10+ years) | Primary DB → Annual archive file |
| Audit log | Permanent (10+ years) | Append-only CSV → Annual archive |
| Market data | 5 years rolling | Historical DB → Annual archive |
| Agent opinions | 3 years | Knowledge DB → Annual archive |
| Strategy performance | Permanent | Learning DB → Annual archive |
| Configuration history | Permanent | Configuration DB → Annual archive |
| System metrics | 1 year rolling | Metrics DB → Monthly archive |

Historical preservation is not a backup problem. It is an **architecture problem**. Data structures must be designed to remain queryable and meaningful 10 years from now, even if the system has evolved significantly.

This requires:
- Schema version numbers on all persisted objects
- Human-readable formats (JSON, CSV) for long-term archives
- Semantic labels on all IDs (cycle IDs, strategy IDs, order IDs) so records can be understood without the live system

---

### 1.9 Auditability

Every financial system that operates autonomously must be auditable. "Auditability" means that for any trade the system has ever executed, a human can answer the following questions with complete certainty:

1. What was the market state at the time of the decision?
2. What did each of the 62 agents opine?
3. What was the conviction score and why?
4. Who approved the trade (which decision rule)?
5. What was the risk calculation and position size?
6. What were the entry, stop-loss, and target prices?
7. When was the order submitted and at what price was it filled?
8. When was the trade closed and at what price?
9. What was the P&L?
10. What did the system learn from this trade?

The persistence architecture must make every one of these questions answerable from stored data alone, without relying on logs, without reconstructing inference, and without guessing.

This is a **complete audit trail**, not a log file.

---

### 1.10 Knowledge Preservation and Long-Term Evolution

The most valuable output of the IIOS is not today's P&L. It is the accumulated knowledge that makes the system progressively better over time. That knowledge lives in:

- Strategy performance records (win rates, Sharpe ratios, max drawdowns by regime)
- Regime-to-strategy maps (learned over hundreds of market cycles)
- Agent calibration records (which agents predict well in which regimes)
- Walk-forward test results (how strategies perform out-of-sample)
- Stress test results (how the portfolio behaves in adversarial scenarios)
- Hypothesis lineage records (how evolved strategies descend from seed strategies)

The loss of this knowledge — even temporary — represents an irreplaceable loss of institutional memory. Knowledge must be:
- Versioned (every update creates a new version, the old is preserved)
- Replicated (at least one off-system copy exists at all times)
- Human-readable in archive form (JSON, not binary)
- Tagged with provenance (which cycle, which strategy, which market regime produced this knowledge)

---

## PART II — PERSISTENCE LAYERS

### 2.1 Persistence Layer Architecture

The IIOS persistence architecture is organised into 15 distinct storage layers. Each layer has exactly one responsibility, one write owner, and one clear boundary.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IIOS PERSISTENCE LAYERS                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L1 OPERATIONAL   │ Active trades, orders, positions, kill-switch   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L2 KNOWLEDGE     │ Strategies, regimes, hypotheses, agent states   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L3 MEMORY        │ Session context, cognitive state, pre-warm data │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L4 LEARNING      │ Win rates, Sharpe, drawdown, calibration data   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L5 AUDIT         │ Immutable event log, decision records           │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L6 MARKET DATA   │ OHLCV bars, option chains, index levels, FX     │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L7 REFERENCE     │ Symbols, sectors, indices, calendar, holidays   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L8 CONFIGURATION │ System parameters, feature flags, schedules     │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L9 LOGS          │ Structured application log files                │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L10 REPORTS      │ Daily EOD, weekly, monthly performance reports  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L11 ARCHIVE      │ Compressed annual data archives                 │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L12 BACKUP       │ Daily encrypted backup files                    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L13 TEMPORARY    │ Intermediate analysis results, scratch space    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L14 CACHE        │ TTL-based in-memory read-through cache          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  L15 METADATA     │ Storage layer health, write counts, checksums   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 L1 — Operational Storage

**Responsibility:** Manage all live operational state — the data the system needs to make decisions and execute orders right now.

**Write Owner:** ExecutionEngine, RiskGuardian, OrderManager, TradeMonitor
**Read Owners:** All 17 layers (via repository interfaces)
**Durability Tier:** Tier 1 — Durable

**Contents:**
- Active order records (orders submitted, pending, filled, cancelled)
- Open position records (symbol, direction, quantity, entry price, stop, target)
- Kill-switch state (active/inactive, reason, activated at)
- Portfolio state (capital available, current exposure, daily P&L)
- Session health record (latest heartbeat, system state, last cycle timestamp)
- Risk metrics snapshot (VIX level, daily loss amount, exposure ratio)

**Lifecycle:** Records are created when operational events occur. They are updated as orders progress through states. They are moved to Historical Storage at end-of-day or when the position is closed. They are never deleted from the primary store — they age to history.

**Access Pattern:** Hot — accessed every cycle. Cache-eligible (TTL 15 seconds).

**Retention:** 90 days in operational storage. Moved to Historical Storage after 90 days. Permanently archived at end of each year.

---

### 2.3 L2 — Knowledge Storage

**Responsibility:** Preserve the institutional knowledge of the IIOS — everything the system has learned about markets, strategies, regimes, and its own performance.

**Write Owner:** StrategyLab, MetaLearning, ResearchLab, LearningSystem
**Read Owners:** All strategy-related layers (L3–L10), DebateAndDecision (L10), MetaLearning (L3)
**Durability Tier:** Tier 2 — Persistent

**Contents:**
- Strategy registry (all known strategies, their parameters, their current state)
- Regime-to-strategy maps (which strategies work in which regimes)
- Agent calibration data (historical accuracy of each agent's opinions)
- Evolved strategy lineage records (parent-child evolution chains)
- Hypothesis templates (reusable trade hypothesis patterns)
- Market insight records (accumulated market observations by regime)
- Walk-forward test results (strategy out-of-sample performance snapshots)
- Promotion and demotion records (when and why strategies changed rank)

**Lifecycle:** Knowledge records are versioned. Every update creates a new version. The old version is preserved. Knowledge is never overwritten or deleted. The latest version is read by default; historical versions are accessible for research.

**Access Pattern:** Warm — read at the start of each cycle, not during hot execution. Cache-eligible (TTL 300 seconds).

**Retention:** Permanent. Versioned knowledge is the most valuable long-term asset. Annual archive created. No deletion.

---

### 2.4 L3 — Memory Storage

**Responsibility:** Provide fast, temporary storage for cognitive session state — the working memory of a running cycle.

**Write Owner:** MasterOrchestrator, ApplicationContext
**Read Owners:** All layers within a cycle
**Durability Tier:** Tier 3 — Session (rebuilt on restart)

**Contents:**
- Current `ApplicationContext` snapshot (per-cycle accumulated outputs from L1–L17)
- Pre-warmed global data (GlobalSnapshot, cached between cycles)
- In-cycle hypothesis pool (candidates being evaluated in the current cycle)
- In-cycle debate transcripts (agent opinions for current hypotheses)
- Market session context (today's regime signal, sector state, liquidity reading)

**Lifecycle:** Memory records are created at cycle start, populated during execution, and flushed at cycle end. Pre-warm records persist between cycles with TTL. Nothing in Memory Storage is expected to survive a process restart.

**Access Pattern:** Ultra-hot — every layer reads from this during execution. Entirely in-memory. No disk I/O during cycle execution.

**Retention:** Single cycle or pre-warm TTL (typically 5 minutes for global data, 30 seconds for market data).

---

### 2.5 L4 — Learning Storage

**Responsibility:** Persist all data produced by the LearningSystem — the statistical performance records that drive strategy improvement, agent calibration, and regime adaptation.

**Write Owner:** LearningEngine, StrategyPerformanceTracker, AgentCalibrator
**Read Owners:** MetaLearning (L3), StrategyLab (L5), ResearchLab (L15), ValidationEngine (L16)
**Durability Tier:** Tier 2 — Persistent

**Contents:**
- Strategy performance records (win rate, average P&L, Sharpe ratio, max drawdown, trade count by regime)
- Trade outcome records (the learning-relevant representation of each closed trade)
- Agent prediction accuracy records (per-agent accuracy by regime and by signal type)
- k-NN weight calibration records (training sets for the MetaLearning weight predictor)
- Regime performance cross-references (which regime did each strategy perform in)
- Auto-disable records (when and why strategies were automatically disabled)
- Auto-enable records (when strategies were restored after recovery)
- Backtesting result snapshots (strategy performance on historical data at each evolution generation)

**Lifecycle:** Learning records are created when the LearningEngine processes closed trades (EOD or triggered). Records are additive — new performance data is appended, not merged into existing records. Aggregates are computed on read, not on write.

**Access Pattern:** Warm on write (EOD), warm on read (strategy selection). Cache-eligible for aggregates (TTL 600 seconds).

**Retention:** Permanent. Strategy learning is cumulative and irreplaceable. Annual archive created. No deletion.

---

### 2.6 L5 — Audit Storage

**Responsibility:** Provide a tamper-evident, append-only record of every significant operational event in the IIOS.

**Write Owner:** AuditService (sole writer — no other component writes directly)
**Read Owners:** ControlTower (L17), Compliance review, Human Principal
**Durability Tier:** Tier 1 — Durable (FULL synchronous write)

**Contents:**
- Cycle audit records (every cycle start, end, result, duration)
- Decision audit records (every approved/rejected hypothesis with full conviction breakdown)
- Order audit records (every order submitted, filled, cancelled, rejected)
- Trade audit records (every trade opened and closed with P&L)
- Risk event audit records (kill-switch activations, daily loss limits, VIX spikes)
- Configuration change records (every parameter change with before/after values)
- Strategy state change records (enable/disable/promote/demote with reasons)
- Human command records (every Telegram command received, by whom, result)
- System lifecycle records (startup, shutdown, restart, version changes)
- Security event records (authentication attempts, permission violations)

**Lifecycle:** Audit records are append-only. They are never modified, never soft-deleted, never hard-deleted. Audit records are written synchronously before the operation they record is considered complete.

**Access Pattern:** Write-heavy, read-rare. No cache. Direct append to rolling audit log file.

**Retention:** Permanent. Annual archive created and retained indefinitely. Audit integrity requires no gaps in the historical record.

---

### 2.7 L6 — Market Data Storage

**Responsibility:** Persist all market data required for strategy analysis, backtesting, walk-forward testing, and regime detection.

**Write Owner:** DataFeedManager, GlobalDataAI, MarketIntelligence
**Read Owners:** All strategy-related layers, StrategyLab (L5), ValidationEngine (L16), ResearchLab (L15)
**Durability Tier:** Tier 2 — Persistent

**Contents:**
- OHLCV price bars (daily, 1-hour, 15-minute, 5-minute for all tracked symbols)
- NIFTY50 and BANKNIFTY index levels (intraday + end-of-day)
- VIX index levels (daily closing values)
- Option chain snapshots (at key times each trading day)
- Global market snapshots (S&P 500, Nikkei, FTSE, USD/INR, Gold, Crude, Bond yields)
- Sector ETF performance records (NIFTY IT, NIFTY Bank, NIFTY Auto, etc.)
- Corporate action records (splits, dividends, rights — for price adjustment)
- Market calendar records (trading holidays, expiry dates, settlement dates)

**Lifecycle:** Market data is immutable once written. Price bars are written once per time interval and never modified. Corporate actions trigger an adjustment record, not a modification to historical bars. Market data older than 5 years is moved to the Archive layer.

**Access Pattern:** Warm for strategy analysis, cold for backtesting. Cache-eligible for intraday reads (TTL 300 seconds).

**Retention:** 5 years in active storage. Permanent in archive. No deletion.

---

### 2.8 L7 — Reference Data Storage

**Responsibility:** Persist all reference data that the system uses to interpret market data and route operations.

**Write Owner:** RefDataManager (only — manual update process)
**Read Owners:** All layers (via read-only reference repositories)
**Durability Tier:** Tier 2 — Persistent

**Contents:**
- Symbol master (NSE symbol, ISIN, exchange, instrument type, lot size)
- Sector classification (which symbol belongs to which NIFTY sector)
- Index composition (which symbols are in NIFTY50, BANKNIFTY, MIDCAP150)
- Expiry calendar (all known F&O expiry dates for the next 3 years)
- Exchange calendar (all NSE trading holidays for the next 3 years)
- Broker instrument map (Dhan instrument ID ↔ NSE symbol ↔ ISIN)
- Margin requirements (SPAN + exposure margin per instrument by category)
- Circuit breaker thresholds (upper/lower circuit limits per symbol)
- Option strike intervals (standard strike gap per underlying)

**Lifecycle:** Reference data is versioned. When the exchange changes index composition, a new version of the composition record is created with an effective date. The old composition is preserved. Reference data is updated weekly or on corporate action events.

**Access Pattern:** Very hot (accessed every cycle for symbol routing). Fully cached in memory at startup. Re-loaded weekly or on update.

**Retention:** Permanent. Reference data history is needed for correct backtesting of historical periods.

---

### 2.9 L8 — Configuration Storage

**Responsibility:** Persist the history of all system configuration values, enabling full reconstruction of the system's configuration state at any point in time.

**Write Owner:** ConfigurationManager (sole writer)
**Read Owners:** ConfigurationManager, ControlTower (L17), Human Principal
**Durability Tier:** Tier 2 — Persistent

**Contents:**
- Configuration version records (every configuration change with timestamp, author, before, after)
- Feature flag history (when each flag was enabled/disabled, by whom)
- Schedule change records (when scheduling slots were changed)
- Capital limit history (changes to capital allocation limits)
- Risk threshold history (changes to VIX threshold, daily loss limit, position limits)
- Strategy parameter snapshots (per-strategy parameter values at each version)
- Environment variable change records (changes to deployment environment)

**Lifecycle:** Every configuration change creates a new record. Old records are never modified. This makes configuration fully auditable and reversible. Configuration is restored by replaying the version history.

**Access Pattern:** Read at startup (load latest version). Written on change (rare). Cold — not read during cycle execution.

**Retention:** Permanent. Configuration history is a regulatory and operational audit requirement.

---

### 2.10 L9 — Logs Storage

**Responsibility:** Persist structured application log output for operational troubleshooting and post-incident analysis.

**Write Owner:** LoggingService (sole writer, via Python logging handlers)
**Read Owners:** Engineering team, ControlTower diagnostics
**Durability Tier:** Tier 2 — Persistent (rotating daily files)

**Contents:**
- Application log files (DEBUG, INFO, WARNING, ERROR, CRITICAL level entries)
- Structured log entries (JSON-formatted: timestamp, level, module, message, context fields)
- Startup/shutdown banners
- Scheduler execution logs (job start/end, duration, result)
- Data feed logs (feed requests, responses, latencies, failover events)
- Error stack traces

**Lifecycle:** Logs rotate daily. Each day's log is a separate file named `trading_brain_YYYY-MM-DD.log`. Files are compressed after 7 days. Files are moved to archive after 90 days. Files older than 1 year are purged.

**Access Pattern:** Write-continuous (every operation logs). Read-rare (post-incident). No cache.

**Retention:** 90 days active, 1 year compressed archive, purged after 1 year.

---

### 2.11 L10 — Reports Storage

**Responsibility:** Persist generated performance reports for human review and long-term performance tracking.

**Write Owner:** PerformanceAnalytics (L14), ControlTower (L17)
**Read Owners:** Human Principal, Telegram bot
**Durability Tier:** Tier 2 — Persistent

**Contents:**
- Daily EOD performance reports (P&L, trades opened/closed, signal count, regime, top movers)
- Weekly performance summaries (cumulative P&L, win rate, Sharpe, drawdown)
- Monthly performance reports (detailed attribution, strategy breakdown, agent accuracy)
- Walk-forward test reports (per strategy, per regime)
- Drawdown analysis reports (peak-to-trough events, duration, recovery)
- Risk attribution reports (P&L by strategy, by regime, by sector)
- System health reports (latency, error rates, feed quality)

**Lifecycle:** Reports are generated by scheduled jobs. Once generated, they are immutable. Old reports are never overwritten. Each report is named with date and report type.

**Access Pattern:** Write-once (generated by job), read-rarely (human review). No cache.

**Retention:** 5 years active, permanent archive.

---

### 2.12 L11 — Archive Storage

**Responsibility:** Preserve all data beyond its active retention period in a compressed, verifiable, and human-readable form.

**Write Owner:** ArchiveService (automated annual archival process)
**Read Owners:** Human Principal, disaster recovery process
**Durability Tier:** Tier 1 — Durable (stored on primary VPS + off-site copy)

**Contents:**
- Annual market data archive files (all OHLCV for the year, per symbol)
- Annual trade record archive files (all trades for the year)
- Annual audit log archive files (all audit events for the year)
- Annual strategy performance archives (all learning data for the year)
- Annual configuration history archives
- Compressed database snapshots (end-of-year SQLite files)

**Lifecycle:** Archive files are created by the annual archival job (runs on January 1 each year). Archive files are immutable — once created, they are never modified. Archive files carry SHA-256 checksums and are verified monthly.

**Access Pattern:** Write-once-per-year. Read-rare (disaster recovery or deep research). No cache.

**Retention:** Permanent. Archive files are never deleted.

---

### 2.13 L13 — Temporary Storage

**Responsibility:** Provide scratch space for intermediate analysis results that do not need to survive a process restart.

**Write Owner:** Any component performing multi-step analysis
**Read Owners:** The component that wrote the data (private)
**Durability Tier:** Tier 4 — Ephemeral

**Contents:**
- Monte Carlo simulation intermediate results
- Walk-forward test run artefacts (before final result is written to Learning Storage)
- Backtesting scratch data (intermediate per-bar P&L before finalisation)
- Strategy evolution population files (current generation chromosomes)
- Stress test scenario results (before aggregation)

**Lifecycle:** Created at the start of an analysis job. Deleted when the job completes (success or failure). If the process crashes mid-job, temporary files are cleaned up at the next startup. Files older than 24 hours are deleted on startup.

**Access Pattern:** Hot during the job, deleted after. No cache.

**Retention:** Duration of the analysis job. Maximum 24 hours.

---

### 2.14 L14 — Cache Layer

**Responsibility:** Provide fast, TTL-governed in-memory storage for frequently read values that are expensive to compute or fetch.

**Write Owner:** Any component that is also the cache miss handler
**Read Owners:** All components (via `cache_utils.TTLCache`)
**Durability Tier:** Tier 4 — Ephemeral (in-memory)

**Cache Entries and TTLs:**

| Cache Key | TTL | Source of Truth | Reason for Caching |
|---|---|---|---|
| `global_snapshot` | 300 seconds | GlobalDataAI | Expensive remote fetch |
| `regime_signal` | 60 seconds | MarketIntelligence | 60s scan interval |
| `sector_context` | 60 seconds | MarketIntelligence | 60s scan interval |
| `reference_data` | 3600 seconds | RefDataRepository | Stable; weekly updates |
| `strategy_list` | 300 seconds | KnowledgeRepository | Rarely changes mid-day |
| `portfolio_context` | 15 seconds | OperationalRepository | Updated by monitor |
| `kill_switch_state` | 5 seconds | OperationalRepository | Safety critical — short TTL |
| `agent_weights` | 600 seconds | LearningRepository | Computed at EOD |
| `feature_flags` | 120 seconds | ConfigurationManager | Rarely changes |

**Lifecycle:** Cache entries are created on first miss. They expire after TTL. They can be invalidated explicitly on write. The cache is never persisted — rebuilt entirely on startup.

**Access Pattern:** Ultra-hot. All reads are O(1). No I/O.

---

### 2.15 L15 — Metadata Layer

**Responsibility:** Track the health, integrity, and operational status of all other storage layers.

**Write Owner:** StorageHealthMonitor (background service)
**Read Owners:** ControlTower (L17), DiagnosticsService
**Durability Tier:** Tier 2 — Persistent

**Contents:**
- Per-layer write count (total writes to each storage layer since last restart)
- Per-layer error count (failed writes or reads)
- Database file size records (trend over time)
- Last backup timestamp and checksum
- Last archive timestamp
- Storage layer health status (HEALTHY, DEGRADED, CRITICAL)
- Retention job last run timestamps
- Cache hit/miss ratios

**Access Pattern:** Written every 60 seconds by background monitor. Read by diagnostics and Telegram `/status` command.

---
## PART III — STORAGE DOMAINS

### 3.1 Domain Overview

A storage domain is a bounded context of data ownership. Each domain owns its data completely: it decides what is stored, who can write, who can read, how long it is retained, and what happens when it ages.

The IIOS has 26 defined storage domains:

| # | Domain | Primary Layer | Primary Database | Retention |
|---|---|---|---|---|
| 1 | Information | L1 Operational | `trading_brain.db` | 90 days active |
| 2 | Entities | L1 Operational | `trading_brain.db` | Permanent |
| 3 | Relationships | L2 Knowledge | `knowledge.db` | Permanent |
| 4 | Events | L5 Audit | `audit.db` | Permanent |
| 5 | Knowledge | L2 Knowledge | `knowledge.db` | Permanent |
| 6 | Reasoning | L2 Knowledge | `knowledge.db` | 3 years active |
| 7 | Decisions | L5 Audit | `audit.db` | Permanent |
| 8 | Learning | L4 Learning | `learning.db` | Permanent |
| 9 | Memory | L3 Memory | In-memory | Session |
| 10 | Portfolio | L1 Operational | `trading_brain.db` | 90 days active |
| 11 | Orders | L1 Operational | `trading_brain.db` | Permanent |
| 12 | Trades | L1 Operational | `trading_brain.db` | Permanent |
| 13 | Execution | L1 Operational | `trading_brain.db` | 1 year active |
| 14 | Risk | L1 Operational | `trading_brain.db` | Permanent |
| 15 | Scheduler | L8 Configuration | `trading_brain.db` | 90 days active |
| 16 | Monitoring | L15 Metadata | `telemetry.db` | 90 days active |
| 17 | Notifications | L5 Audit | `audit.db` | 90 days |
| 18 | AI Agents | L2 Knowledge | `knowledge.db` | Permanent |
| 19 | Prompts | L2 Knowledge | `knowledge.db` | Permanent |
| 20 | Models | L4 Learning | `learning.db` | Permanent |
| 21 | Configurations | L8 Configuration | `configuration.db` | Permanent |
| 22 | Users | L8 Configuration | `configuration.db` | Permanent |
| 23 | Permissions | L8 Configuration | `configuration.db` | Permanent |
| 24 | Sessions | L3 Memory | In-memory | Session |
| 25 | Audit | L5 Audit | `audit.db` | Permanent |
| 26 | Metrics | L15 Metadata | `telemetry.db` | 1 year rolling |

---

### 3.2 Domain: Information

**Responsibility:** Persist all raw market and world information that enters the system through data feeds.

**Write Owner:** DataFeedManager, GlobalDataAI, MarketIntelligence
**Dependencies:** L6 Market Data (for historical), L7 Reference Data (for symbol routing)

**Information sub-types:**

| Information Type | Source | Update Frequency | Cache TTL |
|---|---|---|---|
| NIFTY50 level | Yahoo Finance / Dhan | Real-time (every 30s) | 30 seconds |
| BANKNIFTY level | Yahoo Finance / Dhan | Real-time (every 30s) | 30 seconds |
| VIX level | Yahoo Finance | Daily | 300 seconds |
| S&P 500 level | Yahoo Finance | Daily | 300 seconds |
| USD/INR rate | Yahoo Finance | Daily | 300 seconds |
| Gold price | Yahoo Finance | Daily | 300 seconds |
| Crude oil price | Yahoo Finance | Daily | 300 seconds |
| US 10Y bond yield | Yahoo Finance | Daily | 300 seconds |
| Nikkei 225 level | Yahoo Finance | Daily | 300 seconds |
| NSE Advance/Decline | Calculated from feed | Every 30s during market | 30 seconds |
| Sector ETF levels | Yahoo Finance | Real-time (market hours) | 60 seconds |

**Retention:** Information is retained for 5 years in Market Data Storage. After 5 years, moved to archive.

**Archival:** Annual archive of all information records. Human-readable JSON format with per-record checksums.

---

### 3.3 Domain: Entities

**Responsibility:** Persist all domain entities that represent the primary nouns of the trading system.

**Core entities:**

| Entity | Identity | Lifecycle | Retention |
|---|---|---|---|
| `Strategy` | `strategy_id` (UUID) | Created by StrategyLab; disabled/re-enabled; never deleted | Permanent |
| `Hypothesis` | `hypothesis_id` (UUID) | Created per cycle; evaluated; approved or rejected | 3 years |
| `Order` | `order_id` (UUID) | Created on approval; progresses through states | Permanent |
| `Trade` | `trade_id` (UUID) | Created on fill; closed on exit | Permanent |
| `Position` | `position_id` (UUID) | Created on trade open; closed on trade close | Permanent |
| `Symbol` | NSE symbol string | Created on reference data load; versioned | Permanent |
| `Agent` | `agent_name` string | Defined at startup; never deleted | Permanent |
| `Regime` | Enum value + date | Created when MarketIntelligence identifies regime | 5 years |
| `Portfolio` | Singleton per run | One portfolio per process; state updated continuously | Permanent |

**Entity versioning:** Every mutable entity carries a `version` integer. Each update increments the version and writes a new version record. The latest version is the current state. Historical versions are accessible for research.

---

### 3.4 Domain: Relationships

**Responsibility:** Persist all known relationships between entities.

**Relationship types:**

| Relationship | From Entity | To Entity | Cardinality | Notes |
|---|---|---|---|---|
| `Strategy GENERATES Hypothesis` | Strategy | Hypothesis | 1:N | One strategy generates many hypotheses |
| `Hypothesis BECOMES Order` | Hypothesis | Order | 1:0-1 | Only approved hypotheses become orders |
| `Order RESULTS IN Trade` | Order | Trade | 1:0-1 | Only filled orders become trades |
| `Trade BELONGS TO Portfolio` | Trade | Portfolio | N:1 | All trades belong to one portfolio |
| `Trade TEACHES Learning` | Trade | LearningRecord | 1:1 | Each closed trade produces one learning record |
| `Strategy EVOLVED FROM Strategy` | Strategy | Strategy | N:1 | Strategy lineage tracking |
| `Agent OPINES ON Hypothesis` | Agent | Hypothesis | N:N | Each agent opines on each evaluated hypothesis |
| `Regime ACTIVATES Strategy` | Regime | Strategy | N:N | Regime selection activates strategies |
| `Symbol BELONGS TO Sector` | Symbol | Sector | N:1 | Sector classification |
| `Symbol CONSTITUENT OF Index` | Symbol | Index | N:N | Index composition |

**Relationship persistence:** Relationships are stored as explicit records (relationship table with `from_id`, `to_id`, `relationship_type`, `created_at`, `metadata`). Implicit relationships (foreign keys) exist in domain records but are also available as first-class relationship records for graph-style queries.

**Retention:** Permanent. Relationship history is part of the audit and learning record.

---

### 3.5 Domain: Events

**Responsibility:** Persist every significant system event in the order it occurred, with enough context to reconstruct the system state at that point.

**Event classification:**

| Event Class | Examples | Audit Level | Retention |
|---|---|---|---|
| `CYCLE` | CycleStarted, CycleCompleted, CycleFailed | Full | Permanent |
| `TRADE` | TradeOpened, TradeClosed, TradeModified | Full | Permanent |
| `ORDER` | OrderSubmitted, OrderFilled, OrderCancelled, OrderRejected | Full | Permanent |
| `RISK` | KillSwitchActivated, DailyLossLimitReached, PositionLimitReached | Full | Permanent |
| `SYSTEM` | SystemStartup, SystemShutdown, FeedFailover, StrategyDisabled | Full | Permanent |
| `HUMAN` | TelegramCommand, ManualOverride, ConfigurationChange | Full | Permanent |
| `LEARNING` | StrategyUpdated, AgentCalibrated, WalkForwardCompleted | Summary | 5 years |
| `MONITORING` | LayerTimeout, HealthCheckFailed, CircuitBreakerOpened | Summary | 1 year |
| `NOTIFICATION` | TelegramMessageSent, AlertTriggered | Metadata only | 90 days |

**Event record structure:** Every event record carries:
- `event_id` (UUID4)
- `event_type` (enum)
- `event_class` (enum)
- `occurred_at` (UTC datetime with millisecond precision)
- `cycle_id` (if in cycle context)
- `layer_name` (if in layer context)
- `actor` (who or what caused the event)
- `payload` (JSON-serialised event-specific data)
- `previous_state` (JSON-serialised state before event, for mutable domain events)
- `next_state` (JSON-serialised state after event, for mutable domain events)

**Retention:** CYCLE, TRADE, ORDER, RISK, SYSTEM, HUMAN events: Permanent. Others as per table above.

---

### 3.6 Domain: Knowledge

**Responsibility:** Preserve the IIOS's accumulated understanding of markets, strategies, and its own performance.

**Knowledge artefact types:**

| Artefact Type | Description | Versioned | Retention |
|---|---|---|---|
| `StrategyKnowledge` | Parameters, performance history, regime affinity | Yes | Permanent |
| `RegimeKnowledge` | Characteristics of each identified regime | Yes | Permanent |
| `SectorKnowledge` | Sector rotation patterns, correlation matrices | Yes | 5 years |
| `AgentKnowledge` | Per-agent accuracy profile by regime and signal type | Yes | Permanent |
| `MarketInsight` | Recurring patterns identified by ResearchLab | Yes | Permanent |
| `HypothesisTemplate` | Reusable hypothesis pattern with proven R:R expectations | Yes | Permanent |
| `EvolvedStrategyDNA` | Genetic encoding of evolved strategy variants | Yes | Permanent |

**Knowledge versioning model:**

```
Knowledge Record Version History:
  
  v1 (2024-01-15): Initial strategy knowledge — win_rate=0.0 (no data)
  v2 (2024-02-01): First 30-day performance batch — win_rate=0.53
  v3 (2024-03-01): Second batch — win_rate=0.55
  v4 (2024-04-01): Regime affinity discovered — BULL_TRENDING: win_rate=0.72
  v5 (2024-04-15): Strategy promoted to Tier 1 (win_rate≥0.50, Sharpe>0.8)
  
  Read: Latest version (v5) returned by default
  Research: Any historical version accessible by version number
```

---

### 3.7 Domain: Reasoning

**Responsibility:** Persist the complete reasoning chain that led to each trade decision.

**Reasoning record types:**

| Record Type | Contents | Retention |
|---|---|---|
| `DebateTranscript` | All agent opinions for one hypothesis, including scores and explanations | 3 years |
| `ConvictionBreakdown` | Final conviction score with per-agent weight and contribution | 3 years |
| `RiskCalculation` | Position sizing inputs and outputs for approved hypotheses | 3 years |
| `RegimeAssessment` | MarketIntelligence regime determination with supporting evidence | 3 years |
| `StressTestResult` | Monte Carlo stress test result for the current portfolio | 1 year |
| `ScenarioAnalysis` | Per-scenario P&L expectation for approved hypothesis | 1 year |

**Value of reasoning records:** Reasoning records answer "why did the system make this decision?" They are essential for strategy improvement (understanding which factors drove good vs bad trades) and for debugging (identifying when the reasoning process malfunctions).

---

### 3.8 Domain: Decisions

**Responsibility:** Persist every decision made by the system with enough information to reconstruct and audit the decision independently.

**Decision record:**

| Field | Description |
|---|---|
| `decision_id` | UUID4 |
| `cycle_id` | Parent cycle |
| `hypothesis_id` | The hypothesis being decided on |
| `decision_type` | `APPROVE` or `REJECT` |
| `conviction_score` | Final score (0.0–10.0) |
| `conviction_threshold` | Threshold in effect at decision time |
| `decision_rule` | The rule that triggered the decision |
| `agent_opinions` | JSON: per-agent scores and explanations |
| `risk_assessment` | JSON: risk parameters and sizing decision |
| `override_active` | Whether any kill-switch or override affected this decision |
| `decided_at` | UTC timestamp |
| `market_state_snapshot` | Key market state fields at decision time |

**Decision retention:** Permanent. Decisions are the primary audit record for trade selection. No decision is ever deleted.

---

### 3.9 Domain: Learning

**Responsibility:** Persist all machine learning inputs, training data, calibration data, and model state that the IIOS uses to improve over time.

**Learning artefact types:**

| Artefact | Description | Update Trigger | Retention |
|---|---|---|---|
| `StrategyPerformanceRecord` | Win rate, Sharpe, drawdown by strategy and regime | EOD (after trade close) | Permanent |
| `AgentPredictionRecord` | Per-agent prediction vs actual outcome | EOD | Permanent |
| `kNNTrainingSet` | Feature vectors and labels for MetaLearning weight predictor | Updated with each trade | Permanent |
| `EvolvedVariant` | Evolved strategy parameter set from StrategyLab | After each evolution run | Permanent |
| `BacktestSnapshot` | Strategy performance on the latest 2-year historical window | Weekly | 5 years |
| `WalkForwardResult` | Out-of-sample test result for each strategy | Weekly | Permanent |
| `DisableRecord` | When and why a strategy was auto-disabled | On disable event | Permanent |
| `EnableRecord` | When and why a strategy was re-enabled | On enable event | Permanent |

---

### 3.10 Domain: Portfolio

**Responsibility:** Persist the portfolio state — the aggregate view of all positions, capital, and P&L.

**Portfolio state components:**

| Component | Update Frequency | Durability | Cache TTL |
|---|---|---|---|
| Total capital | On trade open/close | Tier 1 | 15 seconds |
| Available capital | On order submit/fill | Tier 1 | 15 seconds |
| Open position count | Continuous | Tier 1 | 15 seconds |
| Total exposure | Continuous | Tier 1 | 15 seconds |
| Daily realised P&L | On trade close | Tier 1 | 15 seconds |
| Daily unrealised P&L | Every 30 seconds | Tier 2 | 30 seconds |
| Per-strategy allocation | On strategy state change | Tier 2 | 300 seconds |
| Historical daily P&L | EOD | Tier 2 | — |

**Portfolio snapshot:** A complete portfolio snapshot is taken at EOD and stored as an immutable daily record. The snapshot serves as the ground truth for the learning system's performance calculations.

---

### 3.11 Domains: Orders and Trades

**Orders domain:**

| State | Description | Transition |
|---|---|---|
| `PENDING` | Created, not yet submitted to broker | → `SUBMITTED` or `CANCELLED` |
| `SUBMITTED` | Sent to broker | → `FILLED`, `REJECTED`, `CANCELLED` |
| `FILLED` | Confirmed filled by broker | → Terminal |
| `REJECTED` | Rejected by broker | → Terminal |
| `CANCELLED` | Cancelled before fill | → Terminal |
| `PAPER_EXECUTED` | Executed in paper mode (simulated fill) | → Terminal |

Every order state transition produces an audit event and updates the order record. Order records are permanent and immutable at the field level (status is updated, but the record's financial fields never change after creation).

**Trades domain:**

| Field | Immutability | Description |
|---|---|---|
| Trade entry fields | Immutable after creation | Symbol, direction, quantity, strategy, cycle_id |
| Entry price | Immutable after fill | Actual fill price |
| Entry timestamp | Immutable after fill | Timestamp of fill |
| Exit price | Immutable after close | Actual exit fill price |
| Exit timestamp | Immutable after close | Timestamp of exit fill |
| Realised P&L | Immutable after close | Calculated P&L (never recalculated after record is closed) |
| Stop-loss price | Mutable while open | Can be updated by TradeMonitor (trailing stop) |
| Target price | Mutable while open | Can be updated (partial profit scenario) |

---

### 3.12 Domain: Execution

**Responsibility:** Persist all execution-related metadata — broker communications, fill confirmations, latency measurements.

**Execution domain records:**

| Record Type | Description | Retention |
|---|---|---|
| `BrokerRequest` | Raw request sent to broker (JSON) | 1 year |
| `BrokerResponse` | Raw response from broker (JSON) | 1 year |
| `FillConfirmation` | Parsed fill details with price and timestamp | Permanent |
| `RejectionRecord` | Rejection reason from broker | 1 year |
| `ExecutionLatencyRecord` | Round-trip latency per order submission | 1 year |
| `PaperExecutionRecord` | Simulated execution details (paper mode) | 1 year |
| `SlippageRecord` | Difference between expected and actual fill price | Permanent |

---

### 3.13 Domain: Risk

**Responsibility:** Persist all risk-related records — kill-switch state, VIX readings, daily loss tracking, and position limit checks.

**Risk domain records:**

| Record Type | Description | Retention |
|---|---|---|
| `KillSwitchRecord` | Activation/deactivation events with reason | Permanent |
| `DailyRiskSnapshot` | Daily VIX, loss, exposure, position count | Permanent |
| `RiskLimitBreachRecord` | Any risk limit breach with context | Permanent |
| `StressTestRecord` | Portfolio stress test result | 1 year |
| `ScenarioOutcome` | Per-scenario Monte Carlo outcome | 1 year |
| `MarginRecord` | Margin requirements per position | 90 days |

---

### 3.14 Domains: Monitoring, AI Agents, Prompts, Models

**Monitoring domain:**

| Record | Description | Retention |
|---|---|---|
| `LayerTimingRecord` | Per-layer execution time per cycle | 90 days |
| `CycleHealthRecord` | Overall cycle health assessment | 90 days |
| `FeedHealthRecord` | Data feed quality and latency per interval | 90 days |
| `SystemHealthRecord` | Overall system health score | 90 days |

**AI Agents domain:**

| Record | Description | Retention |
|---|---|---|
| `AgentDefinition` | Agent name, role, weight, description | Permanent |
| `AgentCalibrationRecord` | Accuracy by regime and signal type | Permanent |
| `AgentOpinionRecord` | Per-agent opinion on each evaluated hypothesis | 3 years |
| `AgentWeightRecord` | MetaLearning-computed weights per regime | Permanent |

**Prompts domain:**
- All prompt templates used by AI reasoning components are versioned and stored
- Each prompt version is immutable — changes create a new version
- The mapping of which prompt version was used in each cycle is preserved

**Models domain:**
- All trained or evolved model artefacts (k-NN training sets, evolution population files) are versioned
- Model evaluation results are stored alongside the model record
- Model lineage (parent model → child model) is tracked as a relationship

---

### 3.15 Domains: Configurations, Users, Permissions, Sessions

**Configurations domain:**
- Full version history of all configuration values (see Section 2.9)
- Configuration is a Tier 1 audit concern — every change is permanent and attributed to an actor

**Users domain:**
- Authorised Telegram user IDs and their roles
- User activity records (commands issued, times, results)
- No passwords, no credentials — authentication is by Telegram `chat_id` only

**Permissions domain:**
- Role definitions (Human Principal, Observer)
- Permission assignments (which role can issue which commands)
- Permission change records (when assignments changed)

**Sessions domain:**
- Active session records (one per running process)
- Session start time, version, environment, initial configuration snapshot
- Session is purely in-memory — not persisted across restarts
- On restart, a new session record is created; the old one is closed in the session log

---
## PART IV — DATABASE ARCHITECTURE

### 4.1 Database Architecture Overview

The IIOS uses multiple purpose-built databases rather than a single monolithic database. This separation ensures that:
- Each database can be independently backed up, restored, and replaced
- Analytical queries never compete with operational writes for I/O
- Historical data growth never degrades operational database performance
- Different durability, consistency, and retention policies apply per database

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       IIOS DATABASE ARCHITECTURE                           │
│                                                                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  trading_brain  │  │   knowledge.db  │  │   learning.db   │            │
│  │  .db (Primary)  │  │ (Knowledge DB)  │  │  (Learning DB)  │            │
│  │                 │  │                 │  │                 │            │
│  │ - Orders        │  │ - Strategies    │  │ - Performance   │            │
│  │ - Trades        │  │ - Regimes       │  │   Records       │            │
│  │ - Positions     │  │ - Agents        │  │ - Calibration   │            │
│  │ - Portfolio     │  │ - Hypotheses    │  │ - kNN datasets  │            │
│  │ - Risk state    │  │ - Reasoning     │  │ - Backtest      │            │
│  │ - Kill-switch   │  │ - Relationships │  │   snapshots     │            │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │
│           │                   │                    │                      │
│  ┌────────┴────────┐  ┌────────┴────────┐  ┌────────┴────────┐            │
│  │   audit.db      │  │  telemetry.db   │  │ configuration   │            │
│  │  (Audit DB)     │  │ (Analytics DB)  │  │    .db          │            │
│  │                 │  │                 │  │                 │            │
│  │ - Audit events  │  │ - Layer timing  │  │ - Config ver.   │            │
│  │ - Decisions     │  │ - Metrics       │  │ - Feature flags │            │
│  │ - Event log     │  │ - Health        │  │ - Users         │            │
│  │ - Human cmds    │  │ - Feed stats    │  │ - Permissions   │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                    history/ (Historical DB)                        │   │
│  │   market_YYYY.db | trades_YYYY.db | audit_YYYY.db | perf_YYYY.db  │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                   In-Memory Layer                                   │   │
│  │              TTLCache | ApplicationContext | RefData               │   │
│  └────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.2 Primary Database — `trading_brain.db`

**Technology:** SQLite 3 with WAL mode enabled

**Purpose:** The operational heart of the IIOS. This database holds all data needed to make real-time trading decisions and execute orders.

**Why SQLite?**
- Zero-latency access (same process, no network)
- ACID compliance with WAL mode (concurrent reads + serial writes)
- No separate database server process to manage or fail
- File-based — trivially backed up with a file copy
- Proven reliability in embedded systems for 20+ years
- Sufficient write throughput for the IIOS's 30-second cycle interval

**Key Operational Characteristics:**

| Parameter | Value | Reason |
|---|---|---|
| Journal mode | WAL | Concurrent reads without blocking writes |
| Synchronous | NORMAL for most, FULL for Tier-1 writes | Balance performance and durability |
| Cache size | 64MB | Reduce disk reads for hot tables |
| Busy timeout | 5,000ms | Tolerate brief write contention |
| Foreign keys | ON | Enforce relationship integrity |
| Auto-vacuum | INCREMENTAL | Prevent unbounded growth |

**Write throughput expectation:**
- Maximum order throughput: 5 orders per minute (practical limit of a retail trading account)
- Maximum audit write throughput: 50 records per minute (batched by AuditService)
- Maximum monitoring write: 1 record per 30 seconds per layer (17 layers)
- Total expected write load: < 200 writes per minute — well within SQLite limits

**Size management:**
- Operational records older than 90 days are moved to the Historical Database
- The primary database target size: < 500MB
- Monthly size check; alert if > 400MB

---

### 4.3 Knowledge Database — `knowledge.db`

**Technology:** SQLite 3 with WAL mode

**Purpose:** Preserve the institutional knowledge of the IIOS — strategy intelligence, regime maps, agent profiles, reasoning traces.

**Why separate from primary?**
- Knowledge records grow unboundedly over time (permanent retention)
- Knowledge queries are analytical (complex joins, aggregations) and should not compete with operational writes
- Knowledge can be restored to a snapshot without affecting operational state
- The backup and restore cycle for knowledge differs from operational data

**Key Design Characteristics:**

| Characteristic | Design Decision |
|---|---|
| Versioning | All knowledge records are versioned; each update is a new row |
| JSON columns | Structured knowledge is stored as JSON for human readability and flexibility |
| Immutability | No rows are ever deleted or overwritten |
| Full-text search | Knowledge records support keyword search for research queries |
| Read replicas | Research and analytics tools read a daily snapshot copy, not the live database |

**Size management:**
- Knowledge grows permanently — no archival cutoff
- Estimated growth: 500KB/month (100 strategies × 5KB of knowledge updates per month)
- Annual archive snapshot taken and compressed
- Target maximum size before maintenance: 2GB

---

### 4.4 Learning Database — `learning.db`

**Technology:** SQLite 3 with WAL mode

**Purpose:** Store all quantitative learning data produced by the LearningSystem and used by MetaLearning.

**Why separate from knowledge?**
- Learning data is highly structured and numerical (win rates, Sharpe ratios, training vectors)
- Learning data is updated frequently at EOD by batch processes
- Learning data is the input to predictive models — its integrity is performance-critical
- A corruption in learning data affects the intelligence of every future cycle

**Key Design Characteristics:**

| Characteristic | Design Decision |
|---|---|
| Append-only records | Each EOD update appends new performance data; never modifies historical data |
| Regime indexing | All records are indexed by `regime_id` for fast regime-aware queries |
| Strategy indexing | All records are indexed by `strategy_id` for fast per-strategy learning queries |
| CSV export | Daily export of key learning tables to `data/learning_snapshot.csv` for human review |
| Checkpoint | Daily backup before EOD update; rollback available if update corrupts data |

---

### 4.5 Audit Database — `audit.db`

**Technology:** SQLite 3 with `PRAGMA synchronous = FULL` + WAL mode

**Purpose:** Provide a tamper-evident, append-only, permanent record of every significant event.

**Why FULL synchronous?**
Audit records are the legal and operational record of system behaviour. A crash that loses audit records is worse than a crash that loses temporary calculation results. FULL synchronous mode ensures that every audit write is physically committed to disk before the operation it records is considered complete.

**Key Design Characteristics:**

| Characteristic | Design Decision |
|---|---|
| Append-only | No UPDATE or DELETE operations permitted on the audit database |
| Sorted by event time | Primary index on `occurred_at` for time-ordered retrieval |
| Cyclo-indexed | Secondary index on `cycle_id` for per-cycle audit retrieval |
| Immutable writes | AuditService is the sole writer; no other component can write to audit.db |
| Rolling daily backup | Audit database is backed up at end of each trading day |
| Annual archival | Each year's audit records archived to `audit_YYYY.db.gz` |

**Performance note:** The FULL synchronous write mode adds approximately 10–20ms latency per write. This is acceptable because audit writes are batched (not per-event) and occur on a background thread, not in the cognitive cycle hot path.

---

### 4.6 Telemetry Database — `telemetry.db`

**Technology:** SQLite 3 with WAL mode

**Purpose:** Store operational metrics, layer timing, system health, and feed quality data for the Streamlit dashboard and diagnostic queries.

**Why separate from primary?**
- Telemetry data is high-volume (writes every 30 seconds from 17 layers)
- Telemetry data has short retention (90 days rolling)
- Telemetry queries are read-heavy analytics that would block operational writes
- The dashboard reads telemetry; it should never read the primary operational database

**Key Design Characteristics:**

| Characteristic | Design Decision |
|---|---|
| Rolling retention | Records older than 90 days are deleted on a weekly cleanup job |
| Time-partitioned queries | All queries are bounded by time range (last 7 days, last 30 days) |
| Pre-aggregated summaries | Summary tables (daily, weekly) are maintained for faster dashboard queries |
| Read-only for dashboard | The Streamlit dashboard opens telemetry.db in read-only mode |
| No business data | No order, trade, or financial data exists in telemetry.db |

---

### 4.7 Configuration Database — `configuration.db`

**Technology:** SQLite 3 with WAL mode

**Purpose:** Persist the full history of system configuration, user records, and permission assignments.

**Key Design Characteristics:**

| Characteristic | Design Decision |
|---|---|
| Version history | Every configuration change creates a new version record |
| Audit tagged | Every change is attributed to an actor (human or automatic) |
| Read-cached | ConfigurationManager caches all active configuration in memory at startup |
| Change notification | On write, ConfigurationManager invalidates the relevant cache entry |
| Bootstrap independent | configuration.db must be readable before any other component starts |

---

### 4.8 Historical Databases — `history/`

**Technology:** SQLite 3 files, read-only after creation

**Purpose:** Store data that has aged out of active databases. Historical databases are partitioned by year and domain.

**File naming convention:**

| File | Contents |
|---|---|
| `history/market_2024.db` | All market data for calendar year 2024 |
| `history/market_2025.db` | All market data for calendar year 2025 |
| `history/trades_2024.db` | All trade records for 2024 |
| `history/audit_2024.db` | All audit records for 2024 |
| `history/performance_2024.db` | All learning/performance records for 2024 |

**Access:** Historical databases are opened in read-only mode. No writes. Backtesting and walk-forward testing read directly from historical database files.

**Retention:** Historical database files are retained permanently. They are additionally archived as `.gz` compressed files for off-site storage.

---

### 4.9 In-Memory Layer

**Technology:** Python `dict` + custom `TTLCache` from `cache_utils`

**Purpose:** Provide zero-latency access to the values most frequently read during cognitive cycles.

**What lives in the in-memory layer:**

| Item | Expires | Population |
|---|---|---|
| Reference data (full symbol master) | Weekly refresh | At startup |
| Feature flags | 120 seconds | On access miss |
| Active strategy list | 300 seconds | On access miss |
| Global snapshot | 300 seconds | By GlobalDataPrewarmer |
| Regime signal | 60 seconds | By MarketMonitor |
| Portfolio context | 15 seconds | By TradeMonitor |
| Kill-switch state | 5 seconds | On access miss |
| `ApplicationContext` | Per cycle | By MasterOrchestrator |

**Key guarantee:** The in-memory layer is never the source of truth. It is always a read-through cache backed by a persistent store. An in-memory entry expiry results in a database read — never a data loss event.

---

### 4.10 Cold Archive and Backup Repository

**Cold Archive (object storage):**
- Compressed annual database files (`*.db.gz`)
- Annual audit log archives (`audit_YYYY.csv.gz`)
- Annual market data archives (`market_YYYY.csv.gz`)
- Stored on the VPS in `/root/ai-trading-brain/archive/` and optionally mirrored off-site

**Backup Repository:**
- Daily encrypted backup files
- Stored in `/root/ai-trading-brain/backups/`
- Retained for 30 days (rolling)
- Off-site copy recommended (manual process, not automated)
- Naming: `backup_YYYY-MM-DD_HH-MM-SS.tar.gz`

---

## PART V — REPOSITORY PATTERN

### 5.1 Repository Architecture Philosophy

The Repository Pattern is the boundary between the IIOS's business logic and its storage implementation. Every domain entity is accessed through a repository. No component reads from a database directly. No component constructs queries. No component knows the name of a database file.

This boundary provides four guarantees:

| Guarantee | Description |
|---|---|
| **Replaceability** | The storage backend (SQLite, Postgres, cloud DB) can be replaced by reimplementing the repository, leaving all business logic unchanged |
| **Testability** | Test code uses in-memory repository implementations — no database needed for unit tests |
| **Security** | All query parameterisation, path validation, and access control live in the repository |
| **Observability** | Repository operations are instrumented — latency, error rate, and cache hit ratio are measured |

---

### 5.2 Repository Hierarchy

```
BaseRepository (abstract)
├── ReadRepository (abstract — read operations only)
│   ├── TradeReadRepository
│   ├── OrderReadRepository
│   ├── StrategyReadRepository
│   ├── KnowledgeReadRepository
│   ├── MarketDataReadRepository
│   └── AuditReadRepository
│
├── WriteRepository (abstract — write operations only)
│   ├── TradeWriteRepository
│   ├── OrderWriteRepository
│   ├── StrategyWriteRepository
│   └── KnowledgeWriteRepository
│
├── HistoricalRepository (abstract — read-only historical data)
│   ├── HistoricalMarketDataRepository
│   ├── HistoricalTradeRepository
│   └── HistoricalAuditRepository
│
├── ArchiveRepository (abstract — read-only archive data)
│   └── ArchiveRepository
│
├── KnowledgeRepository (versioned reads and writes)
│   ├── StrategyKnowledgeRepository
│   ├── RegimeKnowledgeRepository
│   └── AgentKnowledgeRepository
│
├── MemoryRepository (in-memory, session-scoped)
│   └── ApplicationContextRepository
│
├── LearningRepository
│   ├── PerformanceRepository
│   ├── CalibrationRepository
│   └── BacktestRepository
│
├── DecisionRepository
│
├── AuditRepository (append-only)
│
└── ConfigurationRepository (versioned, read-cached)
```

---

### 5.3 `ReadRepository` Design

**Purpose:** Provide safe, parameterised, cached read access to a domain's data.

**Core interface methods:**

| Method | Signature | Returns | Description |
|---|---|---|---|
| `find_by_id` | `(entity_id: str) -> Optional[Entity]` | Entity or None | Fetch by primary key |
| `find_where` | `(criteria: List[Criteria]) -> List[Entity]` | Entity list | Parameterised query with criteria |
| `find_all` | `() -> List[Entity]` | Entity list | Return all active records |
| `exists` | `(entity_id: str) -> bool` | Boolean | Check existence without loading |
| `count` | `(criteria: List[Criteria] = None) -> int` | Integer | Count matching records |
| `find_latest` | `(limit: int = 10) -> List[Entity]` | Entity list | N most recent records |
| `find_in_range` | `(from_dt: datetime, to_dt: datetime) -> List[Entity]` | Entity list | Time-range bounded query |

**Caching behaviour:**
- `find_by_id` checks TTL cache before reading the database
- Cache is keyed by `{repository_name}:{entity_id}`
- Cache TTL is defined per repository (not globally)
- Cache is invalidated when `WriteRepository.save()` writes to the same key

---

### 5.4 `WriteRepository` Design

**Purpose:** Provide safe, audited, parameterised write access to a domain's data.

**Core interface methods:**

| Method | Signature | Returns | Description |
|---|---|---|---|
| `save` | `(entity: Entity) -> Entity` | Saved entity | Insert or update the entity |
| `save_all` | `(entities: List[Entity]) -> List[Entity]` | Saved entities | Batch insert |
| `soft_delete` | `(entity_id: str) -> bool` | Success flag | Set `is_deleted=True` (never physical delete) |
| `begin_transaction` | `() -> None` | None | Begin DB transaction scope |
| `commit_transaction` | `() -> None` | None | Commit DB transaction |
| `rollback_transaction` | `() -> None` | None | Roll back DB transaction |

**Write safety rules:**
- Every `save()` call validates the entity's invariants before writing (`entity.validate()`)
- Every `save()` call emits an audit event via `AuditService`
- Every `save()` call updates `updated_at` and increments `version`
- No `save()` call modifies immutable fields (fields designated as immutable after first write)
- Failed writes trigger `DATABASE_RETRY_POLICY`; exhausted retries trip the database circuit breaker

---

### 5.5 `HistoricalRepository` Design

**Purpose:** Provide read-only access to historical databases for backtesting, walk-forward testing, and research.

**Core interface methods:**

| Method | Signature | Returns | Description |
|---|---|---|---|
| `find_for_date` | `(date: date) -> List[Entity]` | Entity list | All records for a trading date |
| `find_for_range` | `(from_date: date, to_date: date) -> List[Entity]` | Entity list | Time range bounded query |
| `find_for_year` | `(year: int) -> List[Entity]` | Entity list | Full year's records |
| `get_available_years` | `() -> List[int]` | Year list | Which years have historical data |
| `get_data_quality_report` | `(year: int) -> DataQualityReport` | Report | Completeness and integrity report |

**Key design decisions:**
- Historical repositories open database files in read-only mode (no accidental writes)
- Historical repositories support streaming (large year datasets are not loaded into memory at once)
- Historical repositories verify the database checksum before returning any data
- A missing historical file results in `HistoricalDataUnavailableError`, not silent empty results

---

### 5.6 `ArchiveRepository` Design

**Purpose:** Provide read access to compressed archive files.

**Core interface methods:**

| Method | Signature | Returns | Description |
|---|---|---|---|
| `find_archive` | `(domain: str, year: int) -> ArchiveRef` | Archive reference | Locate archive file for domain+year |
| `extract_to_temp` | `(archive: ArchiveRef) -> Path` | Temp path | Decompress to temporary location |
| `verify_archive` | `(archive: ArchiveRef) -> bool` | Integrity flag | Verify archive checksum |
| `list_archives` | `() -> List[ArchiveRef]` | Archive list | All known archives |

**Archive access pattern:** Archives are never kept open. Each access decompresses the archive to a temporary file, reads the required data, and deletes the temporary file. This prevents accidental modification and limits disk space usage.

---

### 5.7 `KnowledgeRepository` Design

**Purpose:** Provide versioned read and write access to the IIOS knowledge store.

**Core interface methods (additional to ReadRepository):**

| Method | Signature | Returns | Description |
|---|---|---|---|
| `find_latest_version` | `(knowledge_id: str) -> Optional[KnowledgeRecord]` | Latest record | Current version of a knowledge record |
| `find_version` | `(knowledge_id: str, version: int) -> Optional[KnowledgeRecord]` | Specific version | Historical version |
| `find_all_versions` | `(knowledge_id: str) -> List[KnowledgeRecord]` | All versions | Full version history |
| `save_new_version` | `(record: KnowledgeRecord) -> KnowledgeRecord` | New version | Always creates a new version |
| `find_by_type` | `(knowledge_type: str) -> List[KnowledgeRecord]` | Records | All latest versions of a type |
| `diff_versions` | `(id: str, v1: int, v2: int) -> KnowledgeDiff` | Diff | What changed between versions |

---

### 5.8 `LearningRepository` Design

**Purpose:** Provide access to all machine learning training data and performance records.

**Key methods:**

| Method | Description |
|---|---|
| `get_performance_summary(strategy_id, regime)` | Latest computed performance metrics for a strategy in a regime |
| `append_trade_outcome(outcome)` | Append a closed trade outcome (never modify existing) |
| `get_training_set(regime)` | All feature vectors and labels for the regime-specific k-NN model |
| `get_agent_accuracy(agent_name, regime)` | Agent's historical prediction accuracy by regime |
| `find_underperforming_strategies(threshold)` | Strategies below win-rate or Sharpe threshold |
| `get_strategy_lineage(strategy_id)` | Full evolution chain from seed to current |
| `save_backtest_result(result)` | Append new backtest result (never overwrite) |
| `get_latest_backtest(strategy_id)` | Most recent backtest result for a strategy |

---

### 5.9 `AuditRepository` Design

**Purpose:** Provide append-only write access and time-ordered read access to the audit log.

**Core interface:**

| Method | Description |
|---|---|
| `append_event(event)` | Append one audit event (FULL synchronous write) |
| `append_events_batch(events)` | Append a batch of events in one transaction |
| `find_for_cycle(cycle_id)` | All audit events for a specific cycle |
| `find_for_range(from_dt, to_dt)` | All events in a time range |
| `find_by_type(event_type, from_dt, to_dt)` | Filtered events by type |
| `find_for_entity(entity_id)` | All events referencing a specific entity |
| `get_event_count(from_dt, to_dt)` | Count of events in range |
| `verify_integrity(from_dt, to_dt)` | Verify no gaps in the event sequence |

**Append-only guarantee:** The `AuditRepository` never calls UPDATE or DELETE. It raises `AuditIntegrityError` if asked to modify an existing record.

---

### 5.10 `ConfigurationRepository` Design

**Purpose:** Provide versioned read/write access to configuration with change attribution.

**Core interface:**

| Method | Description |
|---|---|
| `get_current_config()` | Full current configuration as `ConfigSnapshot` |
| `get_value(key)` | Current value of one configuration key |
| `set_value(key, value, actor)` | Create new version with updated value |
| `get_history(key)` | All versions of one configuration key |
| `get_version(snapshot_version)` | Full configuration snapshot at a version |
| `rollback_to_version(version, actor)` | Create new version that matches a historical version |

**Cache behaviour:** `get_current_config()` and `get_value()` are served from the in-memory ConfigurationManager cache. Cache is invalidated on every `set_value()` call.

---
## PART VI — DATA LIFECYCLE

### 6.1 Data Lifecycle Overview

Every piece of data in the IIOS travels through a defined lifecycle from creation to eventual archival. The lifecycle is not optional — every data entity follows it, and every stage is governed by the policies in this document.

```
          CREATE                VALIDATE
            │                      │
            ▼                      ▼
      ┌──────────┐         ┌──────────────┐
      │  Draft   │────────>│  Validated   │──── FAIL ──> ValidationError
      └──────────┘         └──────┬───────┘
                                  │ PASS
                                  ▼
                           ┌──────────────┐
                           │   Persisted  │<──── WRITE
                           └──────┬───────┘
                                  │
                    ┌─────────────┴──────────────┐
                    ▼                            ▼
            ┌──────────────┐           ┌──────────────────┐
            │   Active     │           │     Versioned    │
            │  (mutable)   │──UPDATE──>│  (new version    │
            └──────┬───────┘           │   created)       │
                   │                   └──────────────────┘
                   │ RETENTION EXPIRES
                   ▼
          ┌──────────────────┐
          │  Historical      │<──── MOVE
          │  (read-only)     │
          └──────┬───────────┘
                 │ YEAR BOUNDARY
                 ▼
          ┌──────────────────┐
          │   Archived       │<──── COMPRESS + VERIFY
          │   (compressed)   │
          └──────┬───────────┘
                 │ (permanent)
                 ▼
          ┌──────────────────┐
          │   Cold Archive   │ (never deleted — permanent)
          └──────────────────┘
```

---

### 6.2 Creation Stage

**Definition:** The moment a new data entity comes into existence.

**Triggers:**
- A cognitive cycle begins (creates `CycleRecord`, `ApplicationContext`)
- An agent produces an opinion (creates `AgentOpinionRecord`)
- A hypothesis is formed (creates `HypothesisRecord`)
- A decision is made (creates `DecisionRecord`)
- An order is submitted (creates `OrderRecord`)
- A trade is opened (creates `TradeRecord`)
- An audit event occurs (creates `AuditEventRecord`)
- A learning batch runs (creates `PerformanceRecord`)

**Creation rules:**

| Rule | Description |
|---|---|
| CR-01 | Every new entity is assigned a UUID4 `entity_id` at creation time, before any write |
| CR-02 | Every new entity is assigned a `created_at` UTC timestamp at creation time |
| CR-03 | Every new entity has an initial `version` of 1 |
| CR-04 | Every new entity includes a `cycle_id` if created during a cognitive cycle |
| CR-05 | No entity is written to the database until it has passed validation |
| CR-06 | If creation fails after the ID is assigned, the creation failure is logged with the ID |

---

### 6.3 Validation Stage

**Definition:** The process of verifying that a new entity satisfies all invariants before it can be persisted.

**Validation checks by entity type:**

| Entity | Validation Checks |
|---|---|
| `TradeRecord` | Symbol valid, direction valid, quantity > 0, entry price > 0, stop-loss set, target set, R:R ≥ MIN_SIGNAL_RR |
| `OrderRecord` | Symbol valid, direction valid, quantity > 0, order type valid, hypotheis_id set, strategy_id set |
| `HypothesisRecord` | Symbol valid, entry zone valid, stop-loss set, target set, R:R ≥ 1.5, strategy_id set |
| `AuditEventRecord` | Event type valid, occurred_at set, payload is valid JSON, event_id unique |
| `StrategyRecord` | Strategy ID unique, all required parameters set, entry condition defined, exit condition defined |
| `PerformanceRecord` | Strategy_id set, regime set, trade_count ≥ 0, win_rate in [0.0, 1.0] |

**Validation failure policy:**
- Validation failures raise `ValidationError` with a detailed `ValidationResult`
- Validation failures are logged at WARNING level
- Validation failures are counted as a metric (`validation_failures_total`)
- A cascade of validation failures (> 5 in 10 minutes) triggers a Telegram alert

---

### 6.4 Storage Stage

**Definition:** The moment a validated entity is written to its target storage layer.

**Storage stage rules:**

| Rule | Description |
|---|---|
| ST-01 | The repository writes the entity atomically — it either fully succeeds or fully rolls back |
| ST-02 | After a successful write, the repository emits a cache invalidation for the entity's key |
| ST-03 | After a successful write, the repository emits an audit event (except for audit records themselves) |
| ST-04 | After a successful write, the `EventBus` receives a domain event (e.g., `TRADE_OPENED`) |
| ST-05 | A failed write triggers `DATABASE_RETRY_POLICY` — up to 3 retries with exponential backoff |
| ST-06 | After 3 failed retries, the circuit breaker opens and the failure is escalated |
| ST-07 | The entity's `created_at` (for new records) or `updated_at` (for updates) is set by the repository |

---

### 6.5 Versioning Stage

**Definition:** The mechanism by which changes to mutable entities are tracked without overwriting history.

**Versioning models in the IIOS:**

| Model | Used For | Mechanism |
|---|---|---|
| Field versioning | Operational entities (trades, orders, positions) | `version` integer incremented per update; old values not preserved at field level |
| Record versioning | Knowledge entities (strategies, agents, regime maps) | Each update creates a new row with `version+1`; old rows preserved |
| Snapshot versioning | Configuration | Each change creates a full snapshot record |
| Event sourcing | Audit events | No updates; only new events appended |
| Immutable records | Audit, trade final record | Once terminal state reached, record is locked |

**Version conflict resolution:**
- IIOS is single-writer per domain — no optimistic locking needed
- The repository holds a module-level write lock per database for multi-threaded safety
- If two threads attempt concurrent writes, the second waits for the first to complete

---

### 6.6 Access Stage

**Definition:** The patterns by which components read persisted data.

**Access patterns:**

| Pattern | Description | Examples |
|---|---|---|
| Direct read | Repository `find_by_id()` with cache check | Kill-switch state, portfolio context |
| Criteria query | Repository `find_where()` with parameterised criteria | Strategies by regime, trades by date |
| Streaming read | Iterator over large result sets (no full load into memory) | Backtesting over a year of market data |
| Aggregate read | Pre-computed aggregate (count, sum, average) | Win rate, total P&L, cycle count |
| Cache read | TTLCache lookup before any DB access | Reference data, global snapshot |
| Snapshot read | Full entity snapshot at a point in time | Configuration at a past version |

**Access control:**
- ReadRepository is the only type accessible outside the domain that owns the data
- WriteRepository is accessible only within the domain service that owns the data
- AuditRepository's read interface is accessible to ControlTower and Compliance only

---

### 6.7 Update Stage

**Definition:** The process of modifying a mutable entity after its initial creation.

**Updateable fields by entity:**

| Entity | Updateable Fields | Immutable After Creation |
|---|---|---|
| `TradeRecord` | `stop_loss`, `target`, `exit_price`, `exit_timestamp`, `status`, `pnl` (on close) | `entry_price`, `entry_timestamp`, `symbol`, `direction`, `quantity`, `strategy_id` |
| `OrderRecord` | `status`, `filled_price`, `filled_at`, `rejection_reason` | `symbol`, `direction`, `quantity`, `type`, `hypothesis_id` |
| `StrategyRecord` | `status`, `last_used`, `win_rate`, `version` | `strategy_id`, `created_at`, `seed_hypothesis` |
| `KillSwitchRecord` | Not updateable — events only (activate/deactivate are separate records) | All fields |
| `AuditEventRecord` | Not updateable — append-only | All fields |

**Update procedure:**
1. Load current entity from repository (cache check first)
2. Apply change to entity (via entity method, not direct field assignment)
3. Entity calls `validate()` to verify invariants after change
4. Call `repository.save(entity)` — version incremented, `updated_at` set
5. Cache invalidated for this entity's key
6. Audit event appended for the change (field, before value, after value)

---

### 6.8 Snapshot Stage

**Definition:** The creation of a point-in-time immutable snapshot of an entity or collection.

**Snapshot types:**

| Snapshot | Trigger | Contents | Retention |
|---|---|---|---|
| EOD Portfolio Snapshot | End of trading day | Full portfolio state, open positions, daily P&L | Permanent |
| Configuration Snapshot | On any configuration change | Complete active configuration | Permanent |
| Strategy Snapshot | Weekly | All strategies' current state and parameters | 5 years |
| Knowledge Snapshot | Monthly | Full knowledge database serialised to JSON | 5 years |
| Database Snapshot | Daily (backup) | SQLite file copy | 30 days rolling |
| Annual Snapshot | January 1 each year | Compressed full-year archive per domain | Permanent |

---

### 6.9 Archive Stage

**Definition:** The movement of data from active storage to compressed, read-only historical storage.

**Archive triggers:**

| Domain | Archive Trigger | Archive Target | Verification |
|---|---|---|---|
| Market data | > 5 years old | `archive/market_YYYY.csv.gz` | SHA-256 checksum |
| Trade records | > 1 year old | `history/trades_YYYY.db` | Row count match |
| Audit records | > 1 year old | `history/audit_YYYY.db` | Event count match |
| Logs | > 90 days old | `archive/logs_YYYY-MM.gz` | File size match |
| Reports | > 1 year old | `archive/reports_YYYY.tar.gz` | File count match |
| Performance data | > 1 year old | `history/performance_YYYY.db` | Row count match |

**Archive process (per domain, per year):**

```
Step 1: Identify records eligible for archival (date range check)
Step 2: Export records to staging file (CSV or SQLite)
Step 3: Verify staging file row count matches database query count
Step 4: Compress staging file with gzip
Step 5: Compute and store SHA-256 checksum of compressed file
Step 6: Move compressed file to archive directory
Step 7: Verify compressed file is readable and decompresses correctly
Step 8: Delete original records from active database (only after Step 7 passes)
Step 9: Run VACUUM on active database to reclaim space
Step 10: Log archive completion event to AuditService
```

---

### 6.10 Deletion Policy

**The IIOS has a strict no-deletion policy for all financial and audit records.**

| Entity Class | Deletion Allowed? | Alternative |
|---|---|---|
| Trade records | Never | Archived to historical DB |
| Order records | Never | Archived to historical DB |
| Audit events | Never | Archived to historical DB |
| Strategy records | Never | Soft-disabled; status set to `RETIRED` |
| Agent records | Never | Status set to `INACTIVE` |
| Configuration records | Never | Superseded by new version |
| Knowledge records | Never | Superseded by new version |
| Market data | Never (after 5 years → archive) | Compressed archive |
| Logs | After 1 year | Compressed archive after 90 days |
| Telemetry | After 90 days rolling | Aggregate summaries retained |
| Temporary files | On job completion | 24-hour maximum lifetime |
| Cache entries | On TTL expiry | Rebuilt on next access miss |

**Physical delete exceptions (the only cases where rows are physically deleted):**
1. Rolling window telemetry cleanup (> 90 days) — approved by design
2. Temporary analysis files (> 24 hours) — approved by design
3. Cache evictions — in-memory only, never touches persistent storage

---

### 6.11 Retention Policy

**Retention policy by domain:**

| Domain | Active Retention | Historical | Archive | Deletion |
|---|---|---|---|---|
| Orders | 90 days in primary DB | Permanent in history DB | Permanent | Never |
| Trades | 90 days in primary DB | Permanent in history DB | Permanent | Never |
| Audit events | 90 days in primary DB | Permanent in history DB | Permanent | Never |
| Market data (daily) | 5 years in market DB | N/A | Permanent | Never |
| Market data (intraday) | 90 days in market DB | 5 years in history | Permanent after 5y | Never |
| Strategy performance | Active in learning DB | Permanent | Permanent | Never |
| Agent opinions | 90 days in primary | 3 years in history | Permanent after 3y | Never |
| Configuration | Active in config DB | Permanent | Permanent | Never |
| Logs | 90 days active | 90–365 days compressed | After 1 year | After 1 year |
| Telemetry | 90 days rolling | N/A | N/A | After 90 days |
| Reports | 5 years active | N/A | Permanent | Never |
| Reasoning records | 3 years active | 3–5 years in history | Permanent after 5y | Never |

---

### 6.12 Recovery Stage

**Definition:** The process of restoring data from backup or archive when data is lost, corrupted, or incorrectly written.

**Recovery scenarios:**

| Scenario | Recovery Method | RTO | RPO |
|---|---|---|---|
| Process crash (SQLite WAL) | Automatic WAL recovery on next open | < 30 seconds | Zero (committed data preserved) |
| Corrupted database file | Restore from most recent daily backup | < 10 minutes | 24 hours maximum |
| Accidental wrong write | Roll back to previous version (for versioned entities) | < 5 minutes | Zero (old version preserved) |
| Disk failure on VPS | Restore from off-site backup | < 2 hours | 24 hours maximum |
| Learning data corruption | Restore from pre-EOD checkpoint | < 5 minutes | Zero |
| Audit log gap detected | Restore from archive for the affected period | < 30 minutes | Zero (archives preserved) |

**RTO**: Recovery Time Objective (time to restore service)
**RPO**: Recovery Point Objective (maximum data loss window)

---
## PART VII — PERFORMANCE STRATEGY

### 7.1 Performance Design Principles

The IIOS persistence layer is designed to never be the bottleneck in a cognitive cycle. With a full cycle target of < 5,000ms (current: 172ms), persistence operations must be fast, predictable, and bounded.

**Performance targets by operation type:**

| Operation | Target | Maximum | Current Baseline |
|---|---|---|---|
| Cache read (hit) | < 1ms | 5ms | < 1ms |
| Cache read (miss) → DB read | < 50ms | 200ms | ~15ms |
| Write to operational DB | < 20ms | 100ms | ~12ms |
| Write to audit DB | < 50ms | 200ms | ~25ms |
| Historical read (backtesting) | < 500ms | 2,000ms | ~200ms |
| EOD learning batch write | < 5,000ms | 30,000ms | ~1,200ms |
| Daily backup (full) | < 60,000ms | 300,000ms | ~8,000ms |

---

### 7.2 Read Optimisation

**Strategy 1: TTL Cache as Primary Read Layer**

Every cycle-critical read goes through the TTL cache. A cache hit requires no database I/O at all. The cache eliminates the database as a latency source for the hot path.

| Benefit | Impact |
|---|---|
| Zero DB reads for hot cache entries | Cycle latency reduction of 30–100ms |
| O(1) lookup time | Predictable, jitter-free |
| TTL governs data freshness | No stale reads beyond the TTL window |

**Strategy 2: Targeted Indexes**

Indexes are created only for query patterns that are actually used. Over-indexing degrades write performance. Under-indexing degrades read performance.

**Index design philosophy:**
- Every query that runs during a cognitive cycle must use an index
- Indexes are designed from observed `EXPLAIN QUERY PLAN` output, not from guessing
- Composite indexes support compound filter queries (e.g., `strategy_id + regime + date`)
- Text searches use full-text search indexes (SQLite FTS5), not LIKE scans

**Strategy 3: Read Replicas for Analytics**

The Streamlit dashboard and research tools read from a daily snapshot copy of the relevant databases, not the live operational databases. This prevents analytics queries from competing with operational writes.

**Strategy 4: Paginated Results for Large Datasets**

Historical read methods never return unbounded result sets. Every historical query is paginated or streamed. The maximum in-memory dataset for a single query is bounded by `CoreConstants.MAX_QUERY_RESULT_ROWS`.

**Strategy 5: Pre-computation of Expensive Aggregates**

Win rates, Sharpe ratios, and regime performance aggregates are computed by the LearningEngine at EOD and stored as pre-computed values. During cycles, these are read directly — no runtime aggregation.

---

### 7.3 Write Optimisation

**Strategy 1: Asynchronous Write Queue**

Non-critical writes (telemetry, agent opinions, monitoring records) are queued to a background writer thread. The cognitive cycle places the write request in the queue and continues. The background writer drains the queue and commits writes in batches.

**Write queue design:**

| Parameter | Value |
|---|---|
| Queue type | `threading.Queue` (thread-safe, FIFO) |
| Maximum queue depth | 1,000 records |
| Flush interval | Every 30 seconds, or when queue reaches 100 records |
| Flush on shutdown | Yes — all queued writes are flushed before process exit |
| Alert if queue full | Telegram alert when queue > 800 records (80% capacity) |

**Strategy 2: Batch Writes for Audit**

Audit events are the most frequent write type. Rather than flushing each event individually, `AuditService` accumulates events in memory for up to 60 seconds and writes them in a single batch transaction. This reduces I/O from N individual commits to one batch commit per minute.

**Batch write design:**

| Parameter | Value |
|---|---|
| Batch size trigger | 50 events OR 60 seconds, whichever comes first |
| Safety flush on SIGTERM | Yes — all pending audit events flushed on shutdown |
| Safety flush on ERROR | Yes — if an error is logged at ERROR level, audit is flushed immediately |
| Transaction timeout | 5 seconds (fail fast if DB contended) |

**Strategy 3: Write-Ahead Logging Mode**

All databases use SQLite WAL mode. WAL mode allows:
- Simultaneous reads and writes (readers don't block writers)
- Crash recovery without data loss (WAL file contains uncommitted changes)
- Larger write batches without blocking readers

**Strategy 4: Connection Pooling**

Each database has a single shared connection managed by the repository. No new connections are created per query. Connection setup cost (typically 1–5ms) is paid once at startup, not per query.

---

### 7.4 Caching Strategy

**Cache architecture:**

```
                              ┌────────────────────┐
  Repository.find_by_id() ──>│   TTLCache.get()   │──── HIT ──> Return cached value
                              │                    │
                              └─────────┬──────────┘
                                        │ MISS
                                        ▼
                              ┌────────────────────┐
                              │  Database Query    │
                              └─────────┬──────────┘
                                        │
                                        ▼
                              ┌────────────────────┐
                              │  TTLCache.set()    │ (store for TTL)
                              └─────────┬──────────┘
                                        │
                                        ▼
                                 Return value
```

**Cache invalidation strategy:**

| Invalidation Trigger | Method | Scope |
|---|---|---|
| TTL expiry | Automatic by TTLCache | Single entry |
| Repository write | Explicit `cache.invalidate(key)` | Single entry |
| Full knowledge reload | `cache.flush_pattern("knowledge:*")` | All knowledge entries |
| Feature flag change | `cache.invalidate("feature_flags")` | Feature flags entry |
| Shutdown | `cache.clear()` | Entire cache |

**Cache sizing:** The in-memory cache is bounded. Maximum entries and maximum memory usage are defined in `CoreConstants`. If the cache exceeds the maximum, the oldest entries are evicted regardless of TTL.

---

### 7.5 Compression Strategy

**When to compress:**

| Data Type | Compression Applied | Format | Reason |
|---|---|---|---|
| Log files > 7 days | Yes | gzip | Logs are text — compress 80–90% |
| Archive database files | Yes | gzip | SQLite compresses 60–70% |
| CSV archives | Yes | gzip | CSV compresses 85–95% |
| Backup files | Yes | gzip | Reduce backup storage costs |
| Active databases | No | Native SQLite | Compression would degrade query performance |
| In-memory cache | No | Native Python objects | Serialisation overhead exceeds saving |

**Compression standards:**
- All compressed archives use gzip (not bzip2, not zstd) for maximum tool compatibility
- Compression level: 6 (balanced speed vs ratio)
- Every compressed file has an accompanying `.sha256` checksum file
- Compressed files are never read without first verifying the checksum

---

### 7.6 Partitioning Strategy

**Time-based partitioning:**

The IIOS partitions historical data by year at the database file level. Each year's data lives in a separate database file. This provides:
- Bounded database file size (each year's file stabilises in size)
- Parallel reads across years (each file opens independently)
- Easy archival (the entire year's file can be compressed and moved)
- No performance degradation as history grows (old year files are never queried during cycles)

**Domain-based partitioning:**

Each domain has its own database. This provides:
- Independent backup and restore per domain
- Independent size management per domain
- Prevention of inter-domain query coupling
- Ability to move any domain to a different server without migrating all data

---

### 7.7 Index Philosophy

**Indexes are created for reads that happen during cognitive cycles, not for reads that might happen in the future.**

**Cognitive cycle read patterns (must have supporting indexes):**

| Query | Index Required |
|---|---|
| Kill-switch state (current) | `kill_switch ON (is_active, created_at DESC)` |
| Open positions (active) | `positions ON (status, updated_at DESC)` |
| Active strategies by regime | `strategies ON (status, regime_affinity)` |
| Today's trade outcomes | `trades ON (status, closed_at)` where `closed_at > today` |
| Agent weights by regime | `agent_weights ON (regime_id, updated_at DESC)` |
| Portfolio P&L (today) | `portfolio_snapshots ON (snapshot_date DESC)` |

**Index governance rules:**

| Rule | Description |
|---|---|
| IDX-01 | No index is created without an observed query pattern that needs it |
| IDX-02 | Every index is named descriptively: `idx_{table}_{columns}` |
| IDX-03 | Composite indexes are ordered by selectivity (highest selectivity first) |
| IDX-04 | All primary keys have implicit indexes |
| IDX-05 | Every foreign key has a supporting index (SQLite does not auto-create these) |
| IDX-06 | Partial indexes are used where only a subset of rows is ever queried |

---

### 7.8 Historical Data Optimisation

Historical databases (used for backtesting and walk-forward testing) have different performance requirements than operational databases. Their primary access pattern is large sequential reads, not point lookups.

**Historical read optimisation:**

| Technique | Description |
|---|---|
| Pre-sorted data | Historical database rows are pre-sorted by `(symbol, date)` at archival time |
| Memory-mapped I/O | Large backtesting reads use memory-mapped file access |
| Streaming cursor | Historical repositories use cursor-based streaming, not full result set loading |
| Year-scoped files | Each year is a separate file — backtest reads open only the needed year files |
| Compressed columnar | Future: move historical market data to columnar format for analytical reads |
| Cache large reads | Frequently used historical windows (e.g., last 2 years for WFT) are cached after first load |

---

### 7.9 Backup Optimisation

**Backup design for performance:**

| Technique | Description |
|---|---|
| Incremental-style backup | Only databases that changed today are backed up in full |
| SQLite `.backup()` API | Uses the SQLite online backup API — no table locks needed during backup |
| Background backup thread | Backup runs on a dedicated thread; does not delay cognitive cycles |
| Compression pipeline | Backup file is compressed immediately on completion |
| Checksum on write | SHA-256 is computed during compression — no separate read needed |
| Staggered daily backup | Backup starts at 16:30 IST (after market close) — minimal I/O competition |

---

## PART VIII — BACKUP AND RECOVERY

### 8.1 Backup Policy Overview

**Core backup principle: If it cannot be restored, it does not count as a backup.**

Every backup file in the IIOS is:
- Created on a defined schedule
- Compressed and checksummed at creation
- Verified automatically after creation
- Tested for restore integrity weekly
- Retained for the policy-defined period

---

### 8.2 Backup Schedule

| Database | Backup Frequency | Backup Time | Retention | Format |
|---|---|---|---|---|
| `trading_brain.db` | Daily | 16:30 IST | 30 days | `trading_brain_YYYY-MM-DD.db.gz` |
| `knowledge.db` | Daily | 16:35 IST | 30 days | `knowledge_YYYY-MM-DD.db.gz` |
| `learning.db` | Daily | 16:40 IST | 30 days | `learning_YYYY-MM-DD.db.gz` |
| `audit.db` | Daily | 16:45 IST | 60 days | `audit_YYYY-MM-DD.db.gz` |
| `telemetry.db` | Weekly (Sunday) | 03:00 IST | 30 days | `telemetry_YYYY-WNN.db.gz` |
| `configuration.db` | On every change + daily | 16:50 IST | 90 days | `config_YYYY-MM-DD.db.gz` |
| All databases | Weekly (Sunday) | 02:00 IST | 90 days | `full_backup_YYYY-MM-DD.tar.gz` |
| All databases | Annual (Jan 1) | 01:00 IST | Permanent | `annual_YYYY.tar.gz` |

---

### 8.3 Backup Process

**Standard daily backup process:**

```
Step 1:  Create backup directory for today if not exists
Step 2:  For each database:
   2a:   Open source database in read-only mode
   2b:   Execute SQLite online backup API to a staging file
   2c:   Verify staging file can be opened and passes PRAGMA integrity_check
   2d:   Compress staging file to final .db.gz
   2e:   Compute SHA-256 of compressed file
   2f:   Write checksum to .sha256 companion file
   2g:   Log backup completion to AuditService
   2h:   Delete staging file
   2i:   Alert if file size is < 80% of previous backup (potential data loss warning)
Step 3:  Send Telegram notification: "Daily backup complete. N databases. Total size: X MB"
Step 4:  Update L15 Metadata layer with backup timestamps and checksums
Step 5:  Delete backups older than retention period
```

---

### 8.4 Recovery Policy

**Recovery decision matrix:**

| Scenario | Detected By | Recovery Method | RTO | Data at Risk |
|---|---|---|---|---|
| SQLite WAL crash recovery | Automatic on next open | WAL replay | < 30s | None (committed data safe) |
| Corrupted operational DB | PRAGMA integrity_check on startup | Restore from yesterday's backup | < 15min | Up to 24h of operational data |
| Corrupted audit DB | Row count mismatch check | Restore from yesterday's backup | < 15min | Up to 24h of audit events |
| Corrupted knowledge DB | Version sequence check | Restore from yesterday's backup | < 15min | Up to 24h of knowledge updates |
| VPS disk failure | External monitoring | Restore from off-site backup | < 2h | Up to 24h of all data |
| Accidental drop table | Custom watch in startup check | Restore from yesterday's backup | < 15min | Up to 24h |
| Accidental bad write (wrong value) | Versioned entity rollback | `ConfigurationRepository.rollback_to_version()` | < 5min | None (old version preserved) |

---

### 8.5 Point-in-Time Recovery

The IIOS supports a form of point-in-time recovery for versioned domains:

| Domain | PITR Method | Granularity |
|---|---|---|
| Configuration | Version rollback via `ConfigurationRepository` | Every change event |
| Knowledge | Version rollback to any past version number | Every update event |
| Audit | Restore from daily backup + append missing hours from log | Daily |
| Trade records | Restore from daily backup; re-apply today's EOD batch | Daily |
| Portfolio snapshot | EOD snapshot per day; restore to any EOD state | Daily |

For domains without fine-grained PITR, the minimum recovery point is the previous daily backup.

---

### 8.6 Disaster Recovery

**Disaster recovery scenarios and procedures:**

| Disaster | Detection | Recovery Steps |
|---|---|---|
| VPS hardware failure | Monitoring alert (heartbeat loss) | 1. Provision new VPS. 2. Restore from latest backup. 3. Deploy latest Docker image. 4. Verify all databases. 5. Resume trading (next market session). |
| Ransomware/data corruption | Startup integrity checks fail | 1. Kill process. 2. Isolate VPS. 3. Restore from off-site backup. 4. Full integrity check. 5. Resume when verified. |
| Docker image corruption | Container health check fails | 1. `docker compose build --no-cache`. 2. `docker compose up -d`. 3. Verify health. |
| Accidental `git push --force` on main | Git history audit | 1. Restore from backup branch. 2. Re-apply legitimate commits. |
| Database file deleted | Startup `FileNotFoundError` | 1. Restore from yesterday's backup. 2. Log recovery event. 3. Alert Human Principal. |

**Disaster recovery documentation:**
A complete Disaster Recovery Runbook is maintained in `DEPLOYMENT_GUIDE.md`. The runbook is tested quarterly by simulating a VPS recovery from backup.

---

### 8.7 Replication

**Current replication status:**
The IIOS currently operates on a single VPS without real-time database replication. This is intentional for the current operational scale.

**Replication design for future scale:**

| Option | When Appropriate | Description |
|---|---|---|
| SQLite + rsync replication | Current to 3 months | Daily rsync of all `.db` files to a secondary storage location |
| Primary + read replica (Postgres) | > 6 months, > 1,000 trades/day | Streaming replication to a read replica; analytics reads from replica |
| Multi-region replication | Live trading at scale | Synchronous replication to a geographically separate VPS |

**Current compensating control:** Daily off-site backup (manual rsync or managed storage service). This provides RPO of 24 hours and RTO of 2–4 hours.

---

### 8.8 Integrity Verification

**Automated integrity checks (run at startup and daily):**

| Check | Method | Alert if Fails |
|---|---|---|
| SQLite file integrity | `PRAGMA integrity_check` on each database | Yes — CRITICAL alert |
| Row count continuity | Audit event count vs expected minimum | Yes — WARNING alert |
| Backup checksum verification | SHA-256 of backup file vs stored checksum | Yes — WARNING alert |
| Database file size trend | Alert if > 10% smaller than yesterday | Yes — WARNING alert |
| Foreign key consistency | `PRAGMA foreign_key_check` | Yes — WARNING alert |
| WAL checkpoint | `PRAGMA wal_checkpoint(FULL)` on startup | Log result; alert if WAL > 50MB |

**Weekly integrity jobs:**
- Restore a randomly selected daily backup to a temporary location and verify it opens
- Verify archive checksums for all archives created in the last 30 days
- Run a sample of historical queries and compare results to cached snapshots

---

### 8.9 Backup Validation

**Backup validation is not optional.** An unverified backup is not a backup — it is a false sense of security.

**Validation steps performed automatically:**

| Step | When | Method |
|---|---|---|
| Post-write checksum verification | Immediately after each backup | `sha256sum backup_file == stored_checksum` |
| SQLite open test | Immediately after each backup | Open backup file, run `PRAGMA user_version` |
| Integrity check on backup | Within 1 hour of backup | `PRAGMA integrity_check` on backup file |
| Weekly restore test | Sunday 04:00 IST | Restore yesterday's backup to temp dir, open, query |
| Monthly full restore test | First Sunday of month | Restore full backup set, run all startup checks |

**Backup validation alerts:**
- Checksum mismatch → CRITICAL Telegram alert
- Backup file fails to open → CRITICAL alert
- Integrity check fails → CRITICAL alert
- Backup file missing → CRITICAL alert (backup job may have failed)
- Weekly restore test fails → CRITICAL alert

---
## PART IX — PERSISTENCE GOVERNANCE

### 9.1 Governance Philosophy

Persistence governance answers the question: **Who has the right to read, write, modify, or delete each piece of data in the IIOS, and under what conditions?**

Without persistence governance:
- Any component can read any data at any time (coupling, security risk)
- Any component can write any data at any time (corruption risk, audit gap)
- Data schemas change without consideration for readers (compatibility break)
- Data grows without bound (storage exhaustion)
- Old data cannot be confidently understood (schema version unknown)

With persistence governance:
- Every write has exactly one owner
- Every read is through a defined interface
- Every change is versioned and attributed
- Every schema change is documented before it is deployed
- Every storage layer has a defined retention and archival policy

---

### 9.2 Ownership Policy

**Write Ownership: Every data record has exactly one write owner.**

| Domain | Write Owner | Prohibited Writers |
|---|---|---|
| Operational data (trades, orders, positions) | OrderManager, TradeMonitor | All other components |
| Audit records | AuditService | All other components |
| Knowledge records | StrategyLab, MetaLearning, ResearchLab | All other components |
| Learning records | LearningEngine, StrategyPerformanceTracker | All other components |
| Configuration records | ConfigurationManager | All other components |
| Market data | DataFeedManager | All other components |
| Reference data | RefDataManager | All other components |
| Telemetry records | MonitoringService, MetricsCollector | All other components |
| Risk records | RiskGuardian, RiskManagerAI | All other components |

**Read Access: Reads are governed by domain and sensitivity.**

| Data Sensitivity | Read Access | Method |
|---|---|---|
| Public operational data (strategies, portfolio state) | All 17 layers | ReadRepository interface |
| Financial records (trades, orders, P&L) | Restricted to Execution, Risk, Learning layers + Human Principal | ReadRepository + access check |
| Audit records | ControlTower + Human Principal only | AuditRepository read interface |
| Secrets / credentials | SecretsManager only | Never via repository |
| User / permission records | ConfigurationManager only | ConfigurationRepository |

---

### 9.3 Access Policy

**Access control matrix:**

| Actor | Operational Data | Financial Records | Audit Records | Knowledge | Configuration |
|---|---|---|---|---|---|
| Cognitive cycle layers (L1–L17) | Read | Read-restricted | None | Read | Read |
| OrderManager | Read + Write | Write | None | Read | Read |
| TradeMonitor | Read + Write | Write | None | None | Read |
| AuditService | None | None | Write | None | None |
| ControlTower | Read | Read | Read | Read | Read |
| LearningEngine | Read | Read | None | Write | Read |
| RiskGuardian | Read | Read | None | None | Read |
| Telegram bot | None (via service) | Read summary | None | None | Read summary |
| Streamlit dashboard | Read (telemetry only) | Read summary | None | Read | None |
| Human Principal (Telegram) | Read + limited write | Read | Read | Read + write | Read + write |
| Automated backup process | Read all | Read all | Read all | Read all | Read all |

---

### 9.4 Schema Versioning

**Every database in the IIOS carries a `schema_version` integer stored in SQLite's `PRAGMA user_version`.**

| Event | Schema Version Action |
|---|---|
| New database created | `user_version` set to 1 |
| Compatible schema change (new optional field) | `user_version` incremented by 1 |
| Breaking schema change | `user_version` incremented by 10 (signals major break) |
| Database opened | Version read and compared to `CoreConstants.DB_SCHEMA_VERSION` |
| Version mismatch (older) | Migration runner executes the required migration steps |
| Version mismatch (newer) | Process logs ERROR and exits — downgrade not supported |

**Schema versioning rule:** Every schema migration is:
1. Defined in a migration file named `migration_{old_version}_to_{new_version}.py`
2. Idempotent (can be run twice without error)
3. Tested on a copy of production data before deployment
4. Committed to version control before the code that requires it

---

### 9.5 Migration Policy

**When a schema change is required:**

| Step | Action | Responsibility |
|---|---|---|
| 1 | Identify all affected tables and queries | Engineering Lead |
| 2 | Write the migration | Engineering Lead |
| 3 | Test migration on a backup of production data | Engineering Lead |
| 4 | Document the migration in `docs/engineering/migrations/` | Engineering Lead |
| 5 | Deploy migration before the code that depends on it | CI/CD pipeline |
| 6 | Verify migration result via startup check | Automated |
| 7 | Log migration event to AuditService | Automated |

**Breaking migration policy:**
- Breaking schema changes require Human Principal approval
- Breaking changes must include a backfill or data transformation plan
- Breaking changes must include a rollback plan
- The old schema must remain readable by the new code for at least one release cycle (for rollback support)

---

### 9.6 Compatibility Policy

**Forward compatibility:** New code must read data written by the previous version without error. If a new field is added, old records without that field must be handled with a default value.

**Backward compatibility:** Old code reading data written by new code should either succeed or fail gracefully. This is less critical (we do not run multiple versions simultaneously) but informs schema design.

**Compatibility rules:**

| Change Type | Compatibility Impact | Allowed? |
|---|---|---|
| Add new optional field | Forward compatible | Yes (with default value in code) |
| Add new required field | Breaking — old records missing field | Only with migration that backfills default |
| Remove field | Breaking — code using field fails | Only with deprecation + migration |
| Rename field | Breaking | Only with alias + migration |
| Change field type | Breaking | Only with migration and data conversion |
| Add new table | Fully compatible | Yes |
| Remove table | Breaking | Only with migration and data archival |

---

### 9.7 Retention Governance

**Retention is a governance decision, not a storage optimisation.**

Retention decisions are made based on:
- **Regulatory relevance:** Financial audit records must be retained for the duration of the system's operation
- **Operational utility:** Telemetry data older than 90 days has diminishing operational utility
- **Learning value:** Trade outcomes older than 5 years may be less relevant to current market conditions
- **Storage economics:** Market data intraday bars have lower long-term value; daily bars have higher value

**Retention change policy:**
- Any reduction in retention must be approved by Human Principal
- Retention increases require no approval (they are additive)
- Retention changes are recorded in the configuration history
- No retention reduction applies to records already created (change is forward-only)

---

### 9.8 Compliance Requirements

The IIOS persistence architecture is designed to meet the following compliance requirements:

| Requirement | Mechanism |
|---|---|
| Complete audit trail for all trades | Permanent append-only AuditService records |
| Attribution of all financial decisions | Decision records with actor, cycle_id, agent opinions |
| Tamper-evident audit log | Append-only, checksummed, off-site backup |
| Configuration change tracking | Full version history in ConfigurationRepository |
| Reproducible decision audit | Complete reasoning records for each decision |
| No permanent deletion of financial records | Soft-delete + archival only |
| Recovery capability | Tested backup and restore procedures |
| Secret handling compliance | Secrets never written to any persistent store |

---

### 9.9 Security Policy for Persistence

**Persistence-specific security rules:**

| Security Rule | Description |
|---|---|
| PSEC-01 | Database files are stored with filesystem permissions 600 (owner read/write only) |
| PSEC-02 | Backup files are encrypted at rest using AES-256 before off-site transfer |
| PSEC-03 | No secrets, credentials, or API keys appear in any database or log |
| PSEC-04 | All SQL queries are parameterised — no string interpolation into queries |
| PSEC-05 | Database connection strings are loaded from `SecretsManager`, not config files |
| PSEC-06 | AuditRepository write interface is not exposed outside AuditService |
| PSEC-07 | Historical databases are opened read-only — no accidental writes to historical data |
| PSEC-08 | Archive files are checksummed; corrupted archives are quarantined and reported |
| PSEC-09 | Repository `clear()` method is only available in test mode — disabled in production |
| PSEC-10 | Telegram messages never contain full trade details, P&L amounts > threshold, or database paths |

---

## PART X — PERSISTENCE CONSTITUTION

### 10.1 Constitutional Authority

The Persistence Constitution is the supreme set of engineering rules governing how every data record in the IIOS is created, stored, accessed, modified, archived, and protected.

These rules apply to every engineer, every tool, every component, and every automated process in the AI Trading Brain project.

No rule is waivable under time pressure. No rule is subject to individual discretion. Deviation requires an Architecture Decision Record and Human Principal approval.

---

### 10.2 Section A — Foundational Persistence Rules

| Rule ID | Rule |
|---|---|
| PDB-A-01 | Every piece of data in the IIOS is owned by exactly one domain. No data is shared at the storage level between domains. |
| PDB-A-02 | Every write to any domain's storage is made through that domain's repository. No component writes directly to a database file. |
| PDB-A-03 | Every read from any domain's storage is made through that domain's repository. No component queries a database file directly. |
| PDB-A-04 | Every database is purpose-built for one domain or domain group. No cross-domain tables exist in any single database. |
| PDB-A-05 | Every persistent record has a UUID4 primary key, a `created_at` timestamp, and a `version` integer. |
| PDB-A-06 | Every persistent record carries a `schema_version` that identifies the version of the schema under which it was written. |
| PDB-A-07 | Every database file has a `PRAGMA user_version` that is checked at startup against the expected schema version. |
| PDB-A-08 | Schema mismatches are resolved by the migration runner before any component reads data. The system never runs with a mismatched schema. |
| PDB-A-09 | No database is accessed before `validate_config()` completes and confirms all required database paths exist. |
| PDB-A-10 | The L14 Cache layer is always a read-through cache backed by a persistent store. A cache miss results in a database read. A cache miss never results in returning an empty or default value as if real data was returned. |

---

### 10.3 Section B — Immutability and History Rules

| Rule ID | Rule |
|---|---|
| PDB-B-01 | History is immutable. No historical record is ever modified after it is written. |
| PDB-B-02 | Nothing is permanently deleted. All records are soft-deleted (status flag) or archived. Physical deletion is permitted only for telemetry, logs, and temporary files past their retention period. |
| PDB-B-03 | Financial records (orders, trades, positions, P&L) are never deleted under any circumstances. |
| PDB-B-04 | Audit records are never deleted, modified, or soft-deleted. They are permanent and append-only. |
| PDB-B-05 | Every change to a mutable entity creates a new version. The previous version is preserved in the repository. |
| PDB-B-06 | Immutable fields are enforced at the repository level. Any attempt to modify an immutable field after the entity's first write raises `ImmutabilityViolationError`. |
| PDB-B-07 | The `entry_price` and `entry_timestamp` of a trade are immutable after the fill is confirmed. No reconciliation, correction, or backdating is permitted. |
| PDB-B-08 | Every archival operation is verified before the source records are deleted. Verification failure stops the deletion and alerts the Human Principal. |
| PDB-B-09 | Archive files are immutable once created. They are never modified after creation. |
| PDB-B-10 | The `AuditRepository` has no UPDATE or DELETE methods. These operations do not exist in its interface. |

---

### 10.4 Section C — Auditability Rules

| Rule ID | Rule |
|---|---|
| PDB-C-01 | Every significant operational event generates an audit record. The definition of "significant" is exhaustive in Section 3.5 and cannot be reduced without ADR approval. |
| PDB-C-02 | Every audit record carries: `event_id`, `event_type`, `occurred_at`, `cycle_id` (if applicable), `actor`, `payload`. Missing fields are validation failures. |
| PDB-C-03 | Audit records are written before the operation they record is considered complete. An operation is not audited after the fact. |
| PDB-C-04 | The AuditService is the sole writer of audit records. No other component writes to the audit database directly. |
| PDB-C-05 | Every trade that is opened has a corresponding AuditEventRecord of type `TRADE_OPENED`. Every trade that is closed has a corresponding `TRADE_CLOSED` record. No gap between these two events is permissible. |
| PDB-C-06 | Every decision (approve or reject) has a corresponding `DecisionRecord` that includes all agent opinions, the conviction score, and the decision rule. |
| PDB-C-07 | For any trade, a human must be able to reconstruct the full decision chain from audit records alone — without relying on in-memory state, logs, or inference. |
| PDB-C-08 | Audit integrity is verified at startup. Any gap in the event sequence (missing cycle IDs, missing decision records) generates a WARNING and is added to the diagnostic report. |
| PDB-C-09 | Human commands (Telegram) are audited with `actor=chat_id` and `payload=full_command_string`. Human commands are never attributed to "unknown". |
| PDB-C-10 | Every kill-switch activation is audited with: the reason, the VIX level at activation, the daily P&L at activation, and the `cycle_id` of the cycle that triggered it. |

---

### 10.5 Section D — Consistency Rules

| Rule ID | Rule |
|---|---|
| PDB-D-01 | Financial records use strong (serialisable) consistency. No partial writes to trade or order records. |
| PDB-D-02 | A trade record is created atomically with its initial audit event. Both succeed or both fail. There is no state where a trade exists without an audit event. |
| PDB-D-03 | Portfolio state is always consistent with the sum of all open trade records. If discrepancy is detected, `RiskGuardian` halts trading and alerts. |
| PDB-D-04 | The kill-switch state is the single source of truth. No component makes its own copy of the kill-switch state. |
| PDB-D-05 | Cache consistency is governed by TTL and explicit invalidation. A component that writes to a domain must invalidate the corresponding cache entry. |
| PDB-D-06 | Knowledge record consistency is maintained by the append-only version model. Reads always get the latest version. Old versions are never surfaced as current. |
| PDB-D-07 | Configuration consistency is maintained by the in-memory cache loaded at startup. The cache is the source of truth for all reads. The database is the source of truth for all cache misses and on restart. |
| PDB-D-08 | Historical database files are opened in read-only mode. A write attempt to a historical file raises `ReadOnlyStorageError`. |
| PDB-D-09 | Archive files are immutable on the filesystem (set to read-only permission after creation). |
| PDB-D-10 | A database that fails `PRAGMA integrity_check` is never used. The process exits and alerts are sent before any business logic runs. |

---

### 10.6 Section E — Performance Rules

| Rule ID | Rule |
|---|---|
| PDB-E-01 | No persistence operation in the cognitive cycle hot path may block for more than 50ms. Queries that exceed this threshold are logged at WARNING level and measured as a latency metric. |
| PDB-E-02 | Every cycle-critical read is cache-backed. Direct database reads in the cycle hot path (without cache) are prohibited. |
| PDB-E-03 | Unbounded query results are prohibited. Every `find_where()` and `find_all()` call is bounded by a maximum result count. |
| PDB-E-04 | Analytical queries (aggregations over large date ranges) are never executed against the primary operational database. They run against historical databases or pre-computed summaries. |
| PDB-E-05 | The Streamlit dashboard never opens a live operational database. It reads from the telemetry database and pre-generated report files only. |
| PDB-E-06 | Backup operations run on a dedicated background thread. They never share CPU or I/O resources with cognitive cycle execution. |
| PDB-E-07 | The write queue must never fill completely. If the queue reaches 80% capacity, an alert is sent and the write batch size is increased. |
| PDB-E-08 | All database connections are pooled. New connections are not created per query. |

---

### 10.7 Section F — Retention and Archival Rules

| Rule ID | Rule |
|---|---|
| PDB-F-01 | Every storage domain has a defined retention policy. No domain stores data indefinitely without an explicit retention decision. |
| PDB-F-02 | Retention policies are not subject to ad hoc modification. Changes require ADR and Human Principal approval. |
| PDB-F-03 | Archival is always verified before source records are removed. |
| PDB-F-04 | Archive files are stored in a format that can be read by standard tools without the IIOS system (gzip + CSV or gzip + SQLite). |
| PDB-F-05 | Every archive file has an accompanying `.sha256` checksum file. |
| PDB-F-06 | Archive checksums are verified monthly. A failed verification triggers a CRITICAL alert. |
| PDB-F-07 | Annual archive runs on January 1 each year. The annual archival job is the highest-priority maintenance task of the new year. |
| PDB-F-08 | No data that has been archived is re-imported into active storage (except for disaster recovery). |

---

### 10.8 Section G — Backup and Recovery Rules

| Rule ID | Rule |
|---|---|
| PDB-G-01 | Every database has a defined backup schedule. No database is backed up on an ad hoc basis only. |
| PDB-G-02 | Every backup is verified immediately after creation using the four-step verification process (checksum, open, integrity check, row count). |
| PDB-G-03 | Unverified backups are not counted as valid backups. A backup that fails verification generates a CRITICAL alert. |
| PDB-G-04 | Backup retention is not subject to ad hoc reduction. Reducing backup retention requires ADR approval. |
| PDB-G-05 | The recovery procedure for each database is documented in the Disaster Recovery Runbook and is tested quarterly. |
| PDB-G-06 | A weekly restore test is performed for the previous day's backup. If the restore test fails, a CRITICAL alert is generated. |
| PDB-G-07 | The Human Principal is notified within 5 minutes of any backup failure. |
| PDB-G-08 | The system never starts in production with a backup that is more than 48 hours old. If the most recent backup is > 48 hours old, a WARNING is generated and the backup is triggered immediately. |
| PDB-G-09 | Off-site backup copies are maintained for at minimum the last 7 daily backups. |

---

### 10.9 Section H — Security and Compliance Rules

| Rule ID | Rule |
|---|---|
| PDB-H-01 | Database files are stored with filesystem permissions 600 (owner read/write only). Any misconfigured permissions are detected and corrected at startup. |
| PDB-H-02 | No secret, credential, API key, or authentication token is written to any persistent store. |
| PDB-H-03 | All SQL is parameterised. String interpolation into SQL queries is a constitution violation. |
| PDB-H-04 | Backup files that will be transferred off-site are encrypted with AES-256 before transfer. |
| PDB-H-05 | Sensitive log messages are sanitised before writing. Log files must not contain secrets, even in error messages. |
| PDB-H-06 | Telegram notification messages must not contain full P&L figures (use threshold-triggered summaries), full trade details, or any database file paths. |
| PDB-H-07 | Historical databases are opened in read-only mode. Write attempts are rejected by the repository, not by SQLite's file permissions (defence in depth). |
| PDB-H-08 | Database integrity is checked at system startup before any component initialises. |

---

### 10.10 Persistence Constitution Reference Table

| ID | Category | Rule Summary | Enforcement |
|---|---|---|---|
| PDB-A-01 | Foundation | One domain, one owner | PR review |
| PDB-A-02 | Foundation | All writes via repository | PR review |
| PDB-A-03 | Foundation | All reads via repository | PR review |
| PDB-A-04 | Foundation | One database per domain | Architecture review |
| PDB-A-05 | Foundation | UUID4 + created_at + version | CI type check |
| PDB-A-06 | Foundation | Schema version on all records | PR review |
| PDB-A-07 | Foundation | PRAGMA user_version checked at startup | CI test |
| PDB-A-08 | Foundation | Migration before code | CI pipeline |
| PDB-A-09 | Foundation | No DB access before validate_config | PR review |
| PDB-A-10 | Foundation | Cache is always read-through | PR review |
| PDB-B-01 | Immutability | History is immutable | PR review |
| PDB-B-02 | Immutability | No permanent deletion | PR review |
| PDB-B-03 | Immutability | Financial records never deleted | Governance |
| PDB-B-04 | Immutability | Audit records append-only | PR review |
| PDB-B-05 | Immutability | Changes create new version | PR review |
| PDB-B-06 | Immutability | Immutable fields enforced at repo layer | CI type check |
| PDB-B-07 | Immutability | Trade entry price/time immutable | PR review + test |
| PDB-B-08 | Immutability | Archival verified before source delete | Process design |
| PDB-B-09 | Immutability | Archive files immutable after creation | Process design |
| PDB-B-10 | Immutability | AuditRepository has no UPDATE/DELETE | CI type check |
| PDB-C-01 | Auditability | Every significant event audited | PR review |
| PDB-C-02 | Auditability | Audit record required fields | CI validation |
| PDB-C-03 | Auditability | Audit before operation completes | PR review |
| PDB-C-04 | Auditability | AuditService sole writer | PR review |
| PDB-C-05 | Auditability | No trade without audit event | CI test |
| PDB-C-06 | Auditability | Every decision has full record | CI test |
| PDB-C-07 | Auditability | Decision chain reconstructable from records | PR review |
| PDB-C-08 | Auditability | Audit gap detection at startup | CI test |
| PDB-C-09 | Auditability | Human commands attributed to chat_id | CI test |
| PDB-C-10 | Auditability | Kill-switch activation fully audited | CI test |
| PDB-D-01 | Consistency | Financial writes are serialisable | Process design |
| PDB-D-02 | Consistency | Trade record + audit event atomic | CI test |
| PDB-D-03 | Consistency | Portfolio = sum of open trades | CI test |
| PDB-D-04 | Consistency | Kill-switch state is single source of truth | PR review |
| PDB-D-05 | Consistency | Writer invalidates cache | PR review |
| PDB-D-06 | Consistency | Knowledge reads return latest version | CI test |
| PDB-D-07 | Consistency | Config cache is source of truth | PR review |
| PDB-D-08 | Consistency | Historical DB is read-only | CI test |
| PDB-D-09 | Consistency | Archive files read-only on filesystem | Process design |
| PDB-D-10 | Consistency | Integrity check failure stops process | CI test |
| PDB-E-01 | Performance | Hot path writes < 50ms | CI performance test |
| PDB-E-02 | Performance | Cycle-critical reads are cache-backed | PR review |
| PDB-E-03 | Performance | Queries are bounded | PR review |
| PDB-E-04 | Performance | Analytics not on primary DB | Architecture review |
| PDB-E-05 | Performance | Dashboard reads telemetry only | PR review |
| PDB-E-06 | Performance | Backups on dedicated thread | PR review |
| PDB-E-07 | Performance | Write queue never fills | CI test |
| PDB-E-08 | Performance | Connections are pooled | PR review |
| PDB-F-01 | Retention | Every domain has retention policy | Architecture review |
| PDB-F-02 | Retention | Retention changes via ADR | Governance |
| PDB-F-03 | Retention | Archival verified before source delete | CI test |
| PDB-F-04 | Retention | Archives readable without IIOS | PR review |
| PDB-F-05 | Retention | SHA-256 companion file per archive | Process design |
| PDB-F-06 | Retention | Checksums verified monthly | CI scheduled job |
| PDB-F-07 | Retention | Annual archive on Jan 1 | CI scheduled job |
| PDB-F-08 | Retention | No re-import of archived data | Governance |
| PDB-G-01 | Backup | Every DB has backup schedule | Architecture review |
| PDB-G-02 | Backup | Every backup verified on creation | CI test |
| PDB-G-03 | Backup | Unverified backup generates alert | CI test |
| PDB-G-04 | Backup | Backup retention via ADR | Governance |
| PDB-G-05 | Backup | Recovery procedure documented + tested | Process design |
| PDB-G-06 | Backup | Weekly restore test | CI scheduled job |
| PDB-G-07 | Backup | Backup failure alert in 5 minutes | CI test |
| PDB-G-08 | Backup | No start with backup > 48h old | Startup check |
| PDB-G-09 | Backup | 7 days off-site backup | Process design |
| PDB-H-01 | Security | DB files are permission 600 | Startup check |
| PDB-H-02 | Security | No secrets in persistent stores | CI secret scan |
| PDB-H-03 | Security | All SQL parameterised | PR review + test |
| PDB-H-04 | Security | Off-site backups encrypted | Process design |
| PDB-H-05 | Security | Log sanitisation | CI test |
| PDB-H-06 | Security | Telegram message content limits | CI test |
| PDB-H-07 | Security | Historical DB read-only in code | CI test |
| PDB-H-08 | Security | Integrity check before any init | CI test |

**Total mandatory rules: 75**

---
## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document title | DATABASE PERSISTENCE ARCHITECTURE |
| Document version | 1.0.0 |
| Date | 2026-07-02 |
| Parts | 10 (I–X) |
| Mandatory rules | 75 (PDB-A-01 through PDB-H-08) |
| Rule categories | 8 (Foundation, Immutability, Auditability, Consistency, Performance, Retention, Backup, Security) |
| Persistence layers | 15 (L1 Operational through L15 Metadata) |
| Storage domains | 26 |
| Databases defined | 6 (trading_brain, knowledge, learning, audit, telemetry, configuration) + historical partitions |
| Repository types | 10 (Read, Write, Historical, Archive, Knowledge, Memory, Learning, Decision, Audit, Configuration) |
| Lifecycle stages | 12 (Create, Validate, Store, Version, Access, Update, Snapshot, Archive, Restore, Delete, Retention, Recovery) |
| Backup schedules | 8 (daily per database + weekly full + annual) |
| Retention policies | 14 (one per domain category) |
| Cache entries defined | 9 |
| Governance tiers | 3 (L1 Human Principal, L2 Engineering Lead, L3 Automated) |
| Recovery scenarios | 7 |
| Disaster recovery scenarios | 5 |
| Security rules | 10 (PSEC-01 through PSEC-10) |
| Index governance rules | 6 (IDX-01 through IDX-06) |
| Thread safety rules | 8 (TH-01 through TH-08 from Core Framework) |

---

### Master Compliance Checklist

**Before creating any new persistent data record:**
- [ ] Domain identified — which of the 26 domains owns this record?
- [ ] Write owner confirmed — is the writing component the designated write owner?
- [ ] Repository used — is access via the appropriate repository type?
- [ ] Entity fields — UUID4 id, created_at, version all present?
- [ ] Validation called — `entity.validate()` passes before any write?
- [ ] Audit event — does this write generate an audit record?
- [ ] Cache invalidation — is the relevant cache key invalidated after write?

**Before modifying any persistent data record:**
- [ ] Field mutability confirmed — is the field designated as mutable?
- [ ] New version created — does the update create a new version record?
- [ ] Old version preserved — is the previous state accessible?
- [ ] Audit event — does this modification generate a change audit event?

**Before archiving data:**
- [ ] Retention period confirmed — is the data past its active retention?
- [ ] Archive verified — has the staging file been checksummed and opened?
- [ ] Row count match — does the archive row count equal the DB query count?
- [ ] Source not deleted until archive verified — confirmed?

**Before performing any backup:**
- [ ] Backup schedule followed — is this the scheduled backup time?
- [ ] Post-backup verification — checksum, open, integrity check, row count?
- [ ] Alert on failure — is the failure alert pathway tested?

**Before changing any schema:**
- [ ] Migration written and tested — on a backup of production data?
- [ ] Migration documented — in `docs/engineering/migrations/`?
- [ ] Compatibility assessed — forward compatible or breaking?
- [ ] ADR written — if breaking, ADR approved?
- [ ] Backfill plan — if new required field, backfill prepared?

---

### Version History

| Version | Date | Author | Change Summary |
|---|---|---|---|
| 1.0.0 | 2026-07-02 | Human Principal | Initial authoritative release |

---

### Governing Documents

| Document | Role |
|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | Engineering design bridge |
| `ENGINEERING_STANDARDS.md` | Mandatory engineering standards |
| `REPOSITORY_ARCHITECTURE.md` | Repository and package design |
| `CORE_FRAMEWORK_ARCHITECTURE.md` | Core framework and base classes |
| `DATABASE_PERSISTENCE_ARCHITECTURE.md` | This document — persistence design authority |

---

### Closing Statement

Every trade this system ever executes, every decision it ever makes, every insight it ever learns — all of it is only as good as the persistence architecture that stores it. Without reliable, durable, auditable, and recoverable storage, intelligence is ephemeral. With it, intelligence compounds.

The persistence architecture is not the foundation on which the system runs. It is the long-term memory in which the system's intelligence accumulates. Design it wrong, and the system forgets everything it ever learned. Design it right, and the system becomes smarter with every trade, every regime, every market cycle.

This document is that design.

---
## SUPPLEMENT A — DOMAIN RETENTION MATRIX

### A.1 Complete Retention Matrix

This matrix is the authoritative reference for how long every type of data is retained at each stage of its lifecycle.

| Domain | Entity Type | Active Retention | Historical DB | Archive | Physical Delete |
|---|---|---|---|---|---|
| Information | Market tick / intraday bar | 90 days | 5 years | Permanent | Never |
| Information | Daily OHLCV bar | 5 years | N/A | Permanent | Never |
| Information | Global snapshot (S&P, FX, bonds) | 90 days | 5 years | Permanent | Never |
| Entities | Trade record | 90 days active | Permanent | Permanent | Never |
| Entities | Order record | 90 days active | Permanent | Permanent | Never |
| Entities | Position record | 90 days active | Permanent | Permanent | Never |
| Entities | Strategy record | Active (no age-out) | N/A | Permanent | Never (retire only) |
| Entities | Hypothesis record | 90 days | 3 years | Permanent | Never |
| Entities | Symbol master | Active (weekly refresh) | N/A | Annual snapshot | Never |
| Relationships | Strategy → Hypothesis | 90 days | 3 years | Permanent | Never |
| Relationships | Trade → Portfolio | Permanent | N/A | Permanent | Never |
| Relationships | Trade → LearningRecord | Permanent | N/A | Permanent | Never |
| Relationships | Agent → Hypothesis | 90 days | 3 years | Permanent | Never |
| Events | CYCLE events | 90 days | Permanent | Permanent | Never |
| Events | TRADE events | 90 days | Permanent | Permanent | Never |
| Events | ORDER events | 90 days | Permanent | Permanent | Never |
| Events | RISK events | 90 days | Permanent | Permanent | Never |
| Events | SYSTEM events | 90 days | Permanent | Permanent | Never |
| Events | HUMAN commands | 90 days | Permanent | Permanent | Never |
| Events | LEARNING events | 90 days | 5 years | Permanent | Never |
| Events | MONITORING events | 90 days | 1 year | Permanent | After 1 year |
| Events | NOTIFICATION metadata | 90 days | N/A | N/A | After 90 days |
| Knowledge | Strategy knowledge (versioned) | Active | N/A | Annual snapshot | Never |
| Knowledge | Regime knowledge | Active | N/A | Annual snapshot | Never |
| Knowledge | Agent calibration | Active | N/A | Annual snapshot | Never |
| Knowledge | Hypothesis templates | Active | N/A | Permanent | Never |
| Knowledge | Evolved strategy DNA | Active | N/A | Permanent | Never |
| Reasoning | Debate transcripts | 90 days | 3 years | Permanent | Never |
| Reasoning | Conviction breakdowns | 90 days | 3 years | Permanent | Never |
| Reasoning | Risk calculations | 90 days | 3 years | Permanent | Never |
| Reasoning | Stress test results | 90 days | 1 year | After 5 years | Never |
| Decisions | Decision records | 90 days | Permanent | Permanent | Never |
| Learning | Performance records | Active | Permanent | Permanent | Never |
| Learning | Trade outcomes | Active | Permanent | Permanent | Never |
| Learning | k-NN training sets | Active | 5 years | Permanent | Never |
| Learning | Backtest snapshots | Active | 5 years | Permanent | Never |
| Learning | Walk-forward results | Active | Permanent | Permanent | Never |
| Learning | Disable/enable records | Active | Permanent | Permanent | Never |
| Memory | ApplicationContext | Session | N/A | N/A | On cycle end |
| Memory | Pre-warm data | 5-min TTL | N/A | N/A | On TTL expiry |
| Portfolio | Daily EOD snapshot | 5 years | Permanent | Permanent | Never |
| Portfolio | Intraday state | 90 days | 1 year | After 5 years | Never |
| Orders | All order states | 90 days | Permanent | Permanent | Never |
| Trades | All trade records | 90 days | Permanent | Permanent | Never |
| Execution | Broker requests/responses | 90 days | 1 year | After 5 years | Never |
| Execution | Fill confirmations | 90 days | Permanent | Permanent | Never |
| Execution | Slippage records | 90 days | Permanent | Permanent | Never |
| Risk | Kill-switch records | Active | Permanent | Permanent | Never |
| Risk | Daily risk snapshots | 1 year | Permanent | Permanent | Never |
| Risk | Risk limit breaches | 90 days | Permanent | Permanent | Never |
| Risk | Stress test results | 90 days | 1 year | After 5 years | Never |
| Scheduler | Job execution records | 90 days rolling | N/A | N/A | After 90 days |
| Monitoring | Layer timing | 90 days rolling | N/A | N/A | After 90 days |
| Monitoring | System health | 90 days rolling | N/A | N/A | After 90 days |
| Monitoring | Feed health | 90 days rolling | N/A | N/A | After 90 days |
| Notifications | Telegram message metadata | 90 days | N/A | N/A | After 90 days |
| AI Agents | Agent definitions | Permanent | N/A | Annual snapshot | Never |
| AI Agents | Opinion records | 90 days | 3 years | Permanent | Never |
| AI Agents | Weight records | Active | Permanent | Permanent | Never |
| Prompts | Prompt templates (versioned) | Active | Permanent | Permanent | Never |
| Models | k-NN training data | Active | 5 years | Permanent | Never |
| Configurations | All config versions | Active | Permanent | Permanent | Never |
| Users | User records | Active | Permanent | Permanent | Never |
| Permissions | Permission records | Active | Permanent | Permanent | Never |
| Sessions | Session records | Session | N/A | N/A | On process exit |
| Audit | All audit events | 90 days primary | Permanent | Permanent | Never |
| Metrics | System metrics | 90 days rolling | N/A | N/A | After 90 days |
| Logs | Application logs | 90 days | 1 year compressed | N/A | After 1 year |

---

## SUPPLEMENT B — REPOSITORY INTERFACE CATALOGUE

### B.1 Complete Repository Method Reference

This catalogue lists every defined repository method across all repository types.

**`ReadRepository` — Methods available on all read repositories:**

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `find_by_id` | `entity_id: str` | `Optional[Entity]` | Fetch by primary key; cache check first |
| `find_where` | `criteria: List[Criteria], limit: int = 100` | `List[Entity]` | Parameterised filtered query |
| `find_all` | `limit: int = 100` | `List[Entity]` | All active records (bounded) |
| `exists` | `entity_id: str` | `bool` | Existence check without full load |
| `count` | `criteria: List[Criteria] = None` | `int` | Count matching records |
| `find_latest` | `limit: int = 10` | `List[Entity]` | N most recent records |
| `find_in_range` | `from_dt: datetime, to_dt: datetime, limit: int = 1000` | `List[Entity]` | Time-bounded query |
| `find_today` | None | `List[Entity]` | Today's records (shortcut) |
| `get_cache_stats` | None | `CacheStats` | Hit rate, miss rate, entry count |
| `get_query_latency` | None | `LatencyStats` | P50, P95, P99 query latency |

**`WriteRepository` — Methods available on all write repositories:**

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `save` | `entity: Entity` | `Entity` | Insert or update; validates first |
| `save_all` | `entities: List[Entity]` | `List[Entity]` | Batch insert in one transaction |
| `soft_delete` | `entity_id: str` | `bool` | Set `is_deleted=True` (no physical delete) |
| `begin_transaction` | None | `None` | Open DB transaction |
| `commit_transaction` | None | `None` | Commit open transaction |
| `rollback_transaction` | None | `None` | Roll back open transaction |
| `get_write_count` | None | `int` | Total writes since startup |
| `get_error_count` | None | `int` | Failed writes since startup |

**`AuditRepository` — Methods unique to audit:**

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `append_event` | `event: AuditEventRecord` | `None` | Single event append (FULL sync) |
| `append_events_batch` | `events: List[AuditEventRecord]` | `int` | Batch append; returns count |
| `find_for_cycle` | `cycle_id: str` | `List[AuditEventRecord]` | All events for a cycle |
| `find_for_range` | `from_dt, to_dt: datetime` | `List[AuditEventRecord]` | Time-bounded |
| `find_by_type` | `event_type: str, from_dt, to_dt: datetime` | `List[AuditEventRecord]` | Type-filtered |
| `find_for_entity` | `entity_id: str` | `List[AuditEventRecord]` | Entity-referenced events |
| `get_event_count` | `from_dt, to_dt: datetime` | `int` | Count events in range |
| `verify_integrity` | `from_dt, to_dt: datetime` | `IntegrityReport` | Gap and sequence check |
| `get_pending_flush_count` | None | `int` | Events in batch buffer not yet flushed |
| `flush_pending` | None | `int` | Force flush; returns flushed count |

**`KnowledgeRepository` — Methods unique to knowledge:**

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `find_latest_version` | `knowledge_id: str` | `Optional[KnowledgeRecord]` | Current version |
| `find_version` | `knowledge_id: str, version: int` | `Optional[KnowledgeRecord]` | Specific historical version |
| `find_all_versions` | `knowledge_id: str` | `List[KnowledgeRecord]` | Full version history |
| `save_new_version` | `record: KnowledgeRecord` | `KnowledgeRecord` | Always creates new version |
| `find_by_type` | `knowledge_type: str` | `List[KnowledgeRecord]` | All latest of a type |
| `diff_versions` | `id: str, v1: int, v2: int` | `KnowledgeDiff` | Field-level diff |
| `search_knowledge` | `query: str, knowledge_type: str = None` | `List[KnowledgeRecord]` | Full-text search |
| `get_version_count` | `knowledge_id: str` | `int` | Total version count for an entity |

**`LearningRepository` — Methods unique to learning:**

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `get_performance_summary` | `strategy_id: str, regime: str = None` | `PerformanceSummary` | Aggregated performance |
| `append_trade_outcome` | `outcome: TradeOutcome` | `None` | Append closed trade (no overwrite) |
| `get_training_set` | `regime: str, max_rows: int = 10000` | `TrainingSet` | k-NN training data |
| `get_agent_accuracy` | `agent_name: str, regime: str` | `AgentAccuracy` | Per-agent accuracy |
| `find_underperforming_strategies` | `win_rate_threshold: float, sharpe_threshold: float` | `List[StrategyPerformance]` | Below-threshold strategies |
| `get_strategy_lineage` | `strategy_id: str` | `List[StrategyRecord]` | Full evolution chain |
| `save_backtest_result` | `result: BacktestResult` | `None` | Append new backtest (no overwrite) |
| `get_latest_backtest` | `strategy_id: str` | `Optional[BacktestResult]` | Most recent backtest |
| `get_agent_weight_history` | `agent_name: str, regime: str` | `List[AgentWeightRecord]` | Weight over time |

**`HistoricalRepository` — Methods unique to historical access:**

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `find_for_date` | `date: date` | `List[Entity]` | All records for a trading date |
| `find_for_range` | `from_date: date, to_date: date` | `List[Entity]` | Date-range query |
| `find_for_year` | `year: int` | `Iterator[Entity]` | Streaming year access |
| `get_available_years` | None | `List[int]` | Years with data |
| `get_data_quality_report` | `year: int` | `DataQualityReport` | Completeness check |
| `verify_database_integrity` | `year: int` | `IntegrityReport` | SQLite integrity check |

**`ConfigurationRepository` — Methods unique to configuration:**

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `get_current_config` | None | `ConfigSnapshot` | Full current configuration |
| `get_value` | `key: str` | `Any` | Single key current value |
| `set_value` | `key: str, value: Any, actor: str` | `ConfigRecord` | Create new version |
| `get_history` | `key: str` | `List[ConfigRecord]` | All versions of a key |
| `get_version` | `snapshot_version: int` | `ConfigSnapshot` | Snapshot at version |
| `rollback_to_version` | `version: int, actor: str` | `ConfigRecord` | Restore prior version |
| `diff_versions` | `v1: int, v2: int` | `ConfigDiff` | Changes between versions |
| `get_latest_version_number` | None | `int` | Current version number |

---

## SUPPLEMENT C — BACKUP SCHEDULE MATRIX

### C.1 Backup Timing and Retention Reference

| Database | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday |
|---|---|---|---|---|---|---|---|
| `trading_brain.db` | 16:30 IST | 16:30 IST | 16:30 IST | 16:30 IST | 16:30 IST | — | — |
| `knowledge.db` | 16:35 IST | 16:35 IST | 16:35 IST | 16:35 IST | 16:35 IST | — | — |
| `learning.db` | 16:40 IST | 16:40 IST | 16:40 IST | 16:40 IST | 16:40 IST | — | — |
| `audit.db` | 16:45 IST | 16:45 IST | 16:45 IST | 16:45 IST | 16:45 IST | — | — |
| `configuration.db` | 16:50 IST | 16:50 IST | 16:50 IST | 16:50 IST | 16:50 IST | — | — |
| `telemetry.db` | — | — | — | — | — | — | 03:00 IST |
| Full backup (all DBs) | — | — | — | — | — | — | 02:00 IST |

### C.2 Backup Retention Schedule

| Backup Type | Files Kept | Total Retention | Delete After |
|---|---|---|---|
| Daily `trading_brain.db` | 30 files | 30 days | 31 days |
| Daily `audit.db` | 60 files | 60 days | 61 days |
| Daily `configuration.db` | 90 files | 90 days | 91 days |
| Daily `knowledge.db` | 30 files | 30 days | 31 days |
| Daily `learning.db` | 30 files | 30 days | 31 days |
| Weekly full backup | 12 files | 90 days | 91 days |
| Annual full backup | Unlimited | Permanent | Never |

### C.3 Backup Verification Schedule

| Verification Type | When | Method | Alert Threshold |
|---|---|---|---|
| Checksum verify | Immediately after each backup | SHA-256 compare | Any mismatch → CRITICAL |
| Open test | Immediately after each backup | `PRAGMA user_version` | Failure → CRITICAL |
| Integrity check | Within 1 hour of backup | `PRAGMA integrity_check` | Failure → CRITICAL |
| Row count check | Within 1 hour of backup | Query vs expected | > 1% deviation → WARNING |
| Restore test | Sunday 04:00 IST (weekly) | Full restore to temp | Failure → CRITICAL |
| Archive checksum verify | First Sunday of month | Re-verify all archives | Any mismatch → CRITICAL |

---

## SUPPLEMENT D — DATA CLASSIFICATION FRAMEWORK

### D.1 Data Sensitivity Classification

All data in the IIOS is classified into one of four sensitivity tiers. The tier determines who can read it, how it is logged, and how it is protected in transit.

| Tier | Name | Examples | Access | Log Policy | Backup Encryption |
|---|---|---|---|---|---|
| S1 | Secret | Broker API keys, Telegram bot token, TOTP seeds | SecretsManager only; never persisted | Never logged | N/A (never stored) |
| S2 | Confidential | Individual trade P&L amounts, position sizes, Telegram chat_id | Domain owners + Human Principal | Masked in logs | Required for off-site |
| S3 | Restricted | Strategy parameters, agent weights, regime maps | All internal components; not external | May appear in debug logs | Required for off-site |
| S4 | Internal | Market data, cycle timings, system health metrics | All components; dashboard visible | Full logging | Optional |

**Classification rules:**

| Rule | Description |
|---|---|
| DC-01 | Every new data field is classified before it is added to any persistent store |
| DC-02 | S1 data is never persisted anywhere — not in databases, not in logs, not in audit records |
| DC-03 | S2 data in Telegram messages uses threshold summaries ("> 1,000 INR profit") not raw amounts |
| DC-04 | S3 data is accessible to all internal components but never transmitted externally in raw form |
| DC-05 | S4 data is freely available to the dashboard and monitoring tools |

### D.2 Data Criticality Classification

Independent of sensitivity, data is also classified by criticality — the impact of losing it.

| Criticality | Examples | Impact of Loss | Durability Tier |
|---|---|---|---|
| C1 — Critical | Trade records, audit events, kill-switch state | Unrecoverable financial and compliance loss | Tier 1 (FULL sync) |
| C2 — High | Knowledge records, learning data, strategy state | Significant intelligence regression | Tier 2 (NORMAL sync) |
| C3 — Medium | Market data, telemetry, reasoning records | Operational degradation; recoverable from sources | Tier 2 |
| C4 — Low | Temporary files, cached data, session state | No impact — rebuilt on restart | Tier 3/4 |

### D.3 Regulatory Classification

| Record Type | Regulatory Category | Retention Requirement | Archival Requirement |
|---|---|---|---|
| Trade records | Financial audit | Permanent | Annual archive |
| Order records | Financial audit | Permanent | Annual archive |
| Decision records | Financial audit + AI transparency | Permanent | Annual archive |
| Audit events | Regulatory compliance | Permanent | Annual archive |
| Configuration history | Operational audit | Permanent | Annual archive |
| Kill-switch records | Safety compliance | Permanent | Annual archive |
| Market data | Market research | 5 years | Annual archive after 5 years |
| System metrics | Operational record | 1 year | N/A |

---

## SUPPLEMENT E — PERSISTENCE GOVERNANCE DECISION RECORDS

### E.1 PGDR-001: SQLite as Primary Database Engine

| Field | Content |
|---|---|
| **ID** | PGDR-001 |
| **Title** | SQLite as the primary database engine for all IIOS databases |
| **Status** | Accepted |
| **Date** | 2024-01-01 |
| **Authors** | Human Principal |

**Context:** The IIOS needs a reliable, ACID-compliant database. Options considered: SQLite, PostgreSQL, MongoDB, Redis.

**Decision:** Use SQLite for all persistent storage. SQLite provides ACID compliance, zero-latency local access, no server process, file-based backup, and proven reliability. The IIOS's write throughput (< 200 writes/minute) is well within SQLite's limits.

**Consequences:**
- Zero database server maintenance
- Trivial backup (file copy)
- No network latency
- Limited to single-process write concurrency (mitigated by write queue)
- Cannot scale to distributed multi-server writes without migration (planned for > 1,000 trades/day)

---

### E.2 PGDR-002: Append-Only Audit Log

| Field | Content |
|---|---|
| **ID** | PGDR-002 |
| **Title** | Audit log is append-only — no UPDATE, no DELETE |
| **Status** | Accepted |
| **Date** | 2024-01-01 |

**Context:** Audit logs must be tamper-evident. If they can be updated, they can be altered to hide system misbehaviour.

**Decision:** The `AuditRepository` interface has no UPDATE or DELETE methods. The SQLite audit database is opened with a pragma that disallows implicit updates. Any attempt to call an update on the audit database raises an exception in the repository before reaching SQLite.

**Consequences:**
- Audit log grows indefinitely (managed by annual archival)
- Complete tamper evidence — any gap or inconsistency is detectable
- Cannot correct a wrong audit record — a correction record must be appended

---

### E.3 PGDR-003: Domain-Separated Databases

| Field | Content |
|---|---|
| **ID** | PGDR-003 |
| **Title** | One database per domain group; no cross-domain tables |
| **Status** | Accepted |
| **Date** | 2024-01-01 |

**Context:** A single database with all tables would couple all domains together — a corruption in one table could damage all, and a schema change would require migrating everything.

**Decision:** Six databases, each owning its domain: `trading_brain.db` (operational), `knowledge.db` (knowledge), `learning.db` (learning), `audit.db` (audit), `telemetry.db` (monitoring), `configuration.db` (config). No cross-database JOIN queries. Domain data shared between components only via repository interfaces.

**Consequences:**
- Independent backup, restore, and archival per domain
- Independent schema evolution per domain
- No cross-domain query performance optimisation (by design — forces domain separation)

---

### E.4 PGDR-004: Repository Pattern as the Exclusive Data Access Boundary

| Field | Content |
|---|---|
| **ID** | PGDR-004 |
| **Title** | All data access via repository pattern — no direct database access |
| **Status** | Accepted |
| **Date** | 2024-01-01 |

**Context:** Without a data access boundary, any component can query any table at any time, creating hidden coupling, security gaps, and unmaintainable dependencies.

**Decision:** All data access goes through typed repository classes that extend `BaseRepository`. No component opens a database connection directly. No component constructs a SQL query. No component knows the name of a database file or table.

**Consequences:**
- All queries are parameterised (security)
- Storage backend is swappable (PostgreSQL migration requires only repository reimplementation)
- All data access is instrumentable and testable
- Slightly more verbose than direct database access

---

### E.5 PGDR-005: No Permanent Deletion of Financial Records

| Field | Content |
|---|---|
| **ID** | PGDR-005 |
| **Title** | Financial records (orders, trades, positions) are never permanently deleted |
| **Status** | Accepted |
| **Date** | 2024-01-01 |

**Context:** Accidental or malicious deletion of trade records would create irrecoverable gaps in the audit trail and would undermine the system's learning capability.

**Decision:** `soft_delete()` sets `is_deleted=True` for soft-removed records. Physical DELETE is never called for financial records. The only physical deletion that occurs is for telemetry, logs, and temporary files past their retention period — all explicitly listed and governed by retention policy.

**Consequences:**
- Database grows over time (managed by archival to historical databases)
- Audit trail is complete and gapless
- Any "deleted" record is recoverable by setting `is_deleted=False`
- Engineers new to the system must learn the soft-delete pattern

---

## SUPPLEMENT F — PERSISTENCE ANTI-PATTERN REFERENCE AND EXPANDED RULES

### F.1 Persistence Anti-Patterns

The following patterns are explicitly prohibited. Each has caused real data loss or corruption in financial systems.

| Anti-Pattern | Why Prohibited | Correct Alternative |
|---|---|---|
| Direct SQLite connection in business logic | Bypasses repository; no parameterisation, no audit, no cache invalidation | Use the typed repository for the domain |
| `f"SELECT * FROM trades WHERE id = {trade_id}"` | SQL injection via Telegram input, symbol names, or IDs | `repo.find_by_id(trade_id)` with parameterised internal query |
| `db.execute("DELETE FROM trades")` | Permanently destroys financial records | `repo.soft_delete(trade_id)` — sets `is_deleted=True` only |
| `json.dump(trade, open("trade.json", "w"))` | No validation, no version, no audit, no checksumming | `repo.save(trade_entity)` through the repository |
| Reading today's trades from the log file | Logs are for humans; they are not a data source | `trade_read_repo.find_today()` |
| Caching the kill-switch state for > 5 seconds | Kill-switch may have been activated within the last 5 seconds by another thread | Use the `kill_switch_state` cache with 5-second TTL |
| Opening the historical database in read-write mode | Risk of accidental write to immutable historical data | Always open historical databases with `read_only=True` |
| Inserting audit records in a transaction that also writes trades | If the transaction rolls back, the audit record is lost | Write audit events in separate transactions; use append-only pattern |
| Storing the Dhan API token in `configuration.db` | Secrets must not be persisted; use environment variables | Load from `SecretsManager.get("DHAN_ACCESS_TOKEN")` |
| Using `time.time()` as a database timestamp | Timezone-unaware; breaks historical queries | Always use UTC datetime: `datetime.now(timezone.utc)` |
| `cursor.executemany()` without transaction wrapper | Partial writes if interrupted | Always wrap batch writes in explicit `BEGIN / COMMIT` |
| Reading market data from the knowledge database | Wrong domain — market data lives in the market data layer | Use `MarketDataReadRepository` for market data |
| `os.path.join(db_dir, user_input)` | Path traversal attack if `user_input` contains `../` | `PathUtility.is_safe_path(path, base_dir)` before all file operations |
| Updating the `entry_price` field after trade fill | Violates immutability; corrupts audit trail | Raise `ImmutabilityViolationError`; never allow this |
| Performing a `VACUUM` on the primary database during market hours | VACUUM acquires exclusive lock, blocking all reads for 10–30 seconds | Schedule VACUUM for after-market hours only (16:00–08:00 IST) |
| Saving Python `datetime` without timezone info | Naive datetimes cause IST/UTC confusion during DST transitions | Always store as UTC ISO-8601 string: `"2026-07-02T10:30:00Z"` |

---

### F.2 Extended Persistence Rules (PDB-X Series)

The following rules extend the Persistence Constitution with operational guidance derived from observed system behaviour.

| Rule ID | Rule |
|---|---|
| PDB-X-01 | The `data/` directory is the root of all persistent storage. No database file, log file, or archive file is created outside this directory tree. |
| PDB-X-02 | Every database file path is configured in `CoreConstants`, not hardcoded in any module. |
| PDB-X-03 | Every repository reads its target database path from `PathUtility.get_db_path()`, not from a string literal. |
| PDB-X-04 | All repositories are registered with `DependencyManager` at startup. No repository is instantiated outside of the startup sequence. |
| PDB-X-05 | Database connections are not shared across threads. Each thread that needs database access obtains its own connection from the connection pool. |
| PDB-X-06 | All database operations have a timeout. No query can block indefinitely. The default timeout is 5,000ms. A timed-out query raises `DatabaseTimeoutError`. |
| PDB-X-07 | The SQLite WAL file is checkpointed at system startup. A WAL file larger than 50MB at startup indicates an unclean previous shutdown and is investigated before proceeding. |
| PDB-X-08 | The startup sequence performs a `PRAGMA integrity_check` on every database before any component initialises. A failed check aborts startup. |
| PDB-X-09 | Every write to `audit.db` is flushed to disk before the function that triggered it returns. The audit trail is never ahead of actual system state. |
| PDB-X-10 | The `learning.db` database is backed up before every EOD learning batch. If the EOD batch corrupts data, the pre-batch backup is used for recovery. |
| PDB-X-11 | The `archive/` directory is separate from the `backups/` directory. Archives are permanent; backups are rolling. They are never mixed. |
| PDB-X-12 | All compressed archive files use `.db.gz` or `.csv.gz` naming. Binary blobs or proprietary formats are prohibited for long-term archives. |
| PDB-X-13 | The knowledge database's version history must never have a gap in version numbers for any entity. A gap (e.g., version 1 then version 3 with no version 2) indicates data corruption and is investigated. |
| PDB-X-14 | `AuditService.flush_pending()` is called as the first step in every graceful shutdown sequence. Audit records in the buffer at shutdown are not lost. |
| PDB-X-15 | Every repository write emits a metric to `MetricsCollector`. Write throughput per domain is visible on the Streamlit dashboard. |

---

### F.3 Storage Layer Dependency Diagram

This diagram shows which storage layers depend on which other layers for reading.

```
                              L14 Cache
                               │
         ┌─────────────────────┼───────────────────┐
         ▼                     ▼                   ▼
    L1 Operational        L2 Knowledge         L4 Learning
         │                     │                   │
         │              L7 Reference               │
         │                     │                   │
    L5 Audit (writes from all) │                   │
         │                     │                   │
    L6 Market Data (feeds all strategy layers)     │
         │                                         │
    L8 Configuration (feeds all at startup)        │
         │                                         │
    L9 Logs (receives from all)                    │
         │                                         │
    L11 Archive ◄── L1, L2, L4, L5, L6 (on age-out)
         │
    L12 Backup ◄── All active databases (daily)
         │
    L15 Metadata ◄── All layers (health reporting)
```

**Dependency rules:**
- L14 (Cache) sits above all persistent layers — it is always the first read attempt
- L5 (Audit) receives writes from all layers but never serves reads to other layers during cycles
- L7 (Reference) is loaded once at startup and fully cached — it never receives cycle-time reads from disk
- L11 (Archive) is write-once and read-rarely — it never participates in cycle execution
- L15 (Metadata) is updated by monitoring and read by diagnostics — it never blocks cycle execution

---

## SUPPLEMENT G — PERSISTENCE GLOSSARY

| Term | Definition |
|---|---|
| Active retention | The period during which a record is kept in its primary database and is available for cycle-time queries. |
| Append-only | A write mode where records can only be added, never updated or deleted. Used for audit logs and event stores. |
| Archive | A compressed, checksummed, immutable snapshot of data that has exceeded its active retention period. Permanent. |
| Backup | A restorable copy of a live database, taken on a scheduled basis. Rolling retention (30–90 days). |
| Cache hit | A read that is satisfied by the in-memory TTL cache without any database I/O. |
| Cache miss | A read that falls through the TTL cache and requires a database query. Triggers a cache population. |
| Circuit breaker | A persistence protection mechanism that stops database writes after repeated failures to prevent overwhelming a degraded database. |
| Cold archive | Storage for data that has been moved out of historical databases and compressed for long-term preservation. |
| Data durability | The guarantee that committed data survives hardware failure, power loss, and process crash. |
| Data lifecycle | The complete sequence of stages a record passes through: creation, validation, storage, versioning, access, update, snapshot, archive, and eventual deletion or permanent retention. |
| Domain | A bounded context of data ownership. Each domain owns its entities, its repositories, and its storage layer. |
| Entity | A domain object with a unique identity, a lifecycle, and a mutable state that is tracked over time. |
| Eventual consistency | A consistency model where a read may return a slightly stale value, but all reads will converge to the latest value within a bounded time window. |
| Hard delete | Physical removal of a row from a database table. Prohibited for financial records in the IIOS. |
| Historical database | A read-only, partitioned database file containing records that have aged out of the primary active database. |
| Immutable record | A record whose fields cannot be changed after its terminal state is reached. Examples: closed trade, filled order, audit event. |
| Parameterised query | A SQL query where user-derived values are passed as bound parameters, never interpolated into the query string. Required for all IIOS queries. |
| Point-in-time recovery | The ability to restore a system to the exact state it was in at a specific moment in the past. |
| Read-through cache | A cache that, on a miss, automatically fetches the value from the backing store and populates itself. |
| Recovery Point Objective (RPO) | The maximum acceptable data loss window. "How much data can we afford to lose?" |
| Recovery Time Objective (RTO) | The maximum acceptable time to restore service after a failure. "How long can we be down?" |
| Repository | A class that provides a typed, safe, parameterised interface to a domain's persistent storage. All database access goes through a repository. |
| Retention period | The defined duration for which a record is kept in a given storage tier before moving to the next tier. |
| Schema version | An integer that identifies the version of the database schema. Stored in `PRAGMA user_version`. |
| Soft delete | Setting `is_deleted=True` on a record without physically removing it. The record remains in the database and is preserved in audit. |
| Strong consistency | A consistency model where every read sees the most recently committed write. Required for financial records. |
| TTL cache | A time-to-live cache where entries automatically expire after a configured duration. |
| Value object | An immutable domain object identified by its value rather than by an identity. Examples: money amount, price range. |
| Versioned record | A record where each update creates a new version, and the previous version is preserved for audit and research. |
| WAL mode | Write-Ahead Logging — a SQLite journal mode that enables concurrent reads without blocking writes, and provides crash-safe commits. |
| Write owner | The single component or service that has write access to a domain's data. All other components are read-only with respect to that domain. |

---
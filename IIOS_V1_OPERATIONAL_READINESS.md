# IIOS Platform V1.0 — Operational Readiness

**Date:** 2026-08-05
**Scope:** Daily operation, failure recovery, telemetry, history, auditability, scientific journal
**Verdict:** OPERATIONALLY READY

---

## 1. Daily Operation

### Scheduler Timeline (IST)

| Time | Job | Owner | Status |
|---|---|---|---|
| 08:00 | Windows Task Scheduler start | `scripts/autostart.bat` | ✅ Configured |
| 08:30–09:00 | Pre-market init (global data, strategy load) | `master_orchestrator._do_premarket_init()` | ✅ Active |
| 09:05–09:15 | Morning watchlist scan | `master_orchestrator._do_morning_scan()` | ✅ Active |
| 09:20–15:30 | Continuous scan (30s interval) | `MarketMonitor` | ✅ Active |
| 09:05 | PIG institutional intelligence warm-up | `PIGTradingAdapter._ensure_init()` | ✅ Active |
| 09:30+ | Full trading cycles (17 layers) | `MasterOrchestrator.run_full_cycle()` | ✅ Active |
| 15:35 | EOD position review | `master_orchestrator._do_eod_review()` | ✅ Active |
| 15:45 | EOD PnL + learning | `master_orchestrator._do_eod_learning()` | ✅ Active |
| 15:45 | Market Learning (via MLC) | `MarketLearningCoordinator.run_learning_pipeline()` | ✅ Active |
| 15:45 | Strategy performance tracking | `StrategyPerformanceTracker` | ✅ Active |

### Trading Cycle (17 layers, target <200ms)

| Stage | Layer(s) | Measured Latency |
|---|---|---|
| GlobalIntelligence | L1 | 17ms (cache + pre-warm) |
| MarketIntelligence | L2 | 19ms |
| All other layers | L3–L17 | Combined ~136ms |
| **Full cycle** | L1–L17 | **172ms** ✅ |

**Performance baseline:** 172ms — HEALTHY. Registered as immutable baseline in `ARCHITECTURE.md`.

### Market-Hours Guard

`run_full_cycle()` is guarded: only executes on weekdays (Monday–Friday) between
09:15 and 15:30 IST. No trades are placed outside market hours.

---

## 2. Failure Recovery

### Process Safety

| Mechanism | File | Status |
|---|---|---|
| PID lock (single instance) | `utils/pid_lock.py` | ✅ Active |
| SIGTERM handler → clean scheduler shutdown | `main.py` | ✅ Active |
| Daily log rotation | `utils/log_rotation.py` | ✅ Active |
| Startup / shutdown banners | `main.py` | ✅ Active |

### Layer-Level Fault Isolation

Every layer runs inside `SystemMonitor.time_layer()`:

- `WARN` threshold: 2,000ms (default); 5,000ms (GlobalIntelligence)
- `CRIT` threshold: 5,000ms (default); 12,000ms (GlobalIntelligence)
- CRIT exceeded → layer aborts current cycle, cycle continues from next layer
- Per-cycle latency logged to `data/control_tower.db`

### Data Feed Failover

| Primary | Fallback | Trigger |
|---|---|---|
| Dhan data API | yfinance | HTTP 451 (access blocked) |
| yfinance history | Cached last-known | Network timeout (8s) |

### MLC Failure Isolation (EOD learning)

Every learning stage in `MarketLearningCoordinator` is independently isolated:

- Stage failure → stage marked `FAILED`, remaining stages continue
- Full pipeline completes even if any one stage fails
- All preceding production results (PnL, strategy stats, telemetry) are committed before MLC runs
- AMLS failure → caught, logged at WARNING, orchestrator continues normally
- DRE failure → caught, logged at WARNING, AMLS results unaffected

### PIG / Knowledge Fallback

`PIGTradingAdapter.evaluate_symbol()` returns `None` on any error.
`pig_enrich_signals()` and `pig_build_vote()` skip gracefully when result is `None`.
Trading continues exactly as pre-MLS when library is empty or PIG is unavailable.

### RiskGuardian Hard Kill-Switch

| Condition | Action |
|---|---|
| VIX > 45 | Cycle abort — no orders |
| Daily loss > 2% of capital | Cycle abort — no orders |

Kill-switch is hard-coded in `risk_guardian/risk_guardian.py` (protected module).
Cannot be softened without explicit operator instruction.

---

## 3. Telemetry

### Structured Log Tags (selection)

| Tag | Meaning |
|---|---|
| `[AMLS]` | Autonomous market learning pipeline run |
| `[DRE]` | DNA reinforcement event |
| `[PIGExplainability]` | 7-field PIG evaluation trace |
| `[BlockerReport]` | Why-no-trade diagnostic summary |
| `[TradeDiagnostic]` | Per-symbol signal diagnostic |
| `[ScalarNormalizationFailure]` | Type coercion event |
| `[ScalarCoverageReport]` | EOD scalar audit summary |
| `[SafeScalarCoverageAudit]` | Per-scan coverage audit |
| `[StrategyBlocked]` | Governance-disabled strategy drop |
| `[CarryReviewDryRun]` | Carry extension score (dry-run only) |
| `[PTUEFallback]` | Static fallback triggered for historical universe |
| `[TradingDayCarry]` | Carry expiry using trading-day count |

### Control Tower (Layer 17)

| Store | Content |
|---|---|
| `data/control_tower.db` | Events, layer timings, health records, recommendations |
| `data/trading_brain.db` | Trades, positions, signals, orders, rejections |
| `data/learning_brain.db` | Strategy performance, EOD evaluation, options audit |
| `data/mls/institutional_dna.db` | Versioned institutional DNA, audit log |
| `logs/` | Rotating daily log files |

### Streamlit Dashboard

`python main.py --dashboard` → Streamlit on `0.0.0.0:8501`

Panels: open positions, closed trades, PnL curve, strategy health,
regime state, learning status, telemetry summary.

---

## 4. Trade History and Auditability

### Trade Lifecycle Trace

Every trade is traceable through the full pipeline:

1. Signal generated (OpportunityEngine) → logged with opportunity_id
2. Enriched by PIG → `[PIGExplainability]` log with 7 fields
3. Debate verdict (5 agents) → logged with agent scores
4. DecisionEngine threshold (6.5) → APPROVE / REJECT logged
5. RiskGuardian gate → PASS / KILL logged
6. OrderManager → paper CSV `data/paper_trades.csv` + SQLite
7. TradeMonitor → carry expiry, position health
8. EOD: LearningEngine learns; MLC reinforces DNA; PTUE provides universe

### Audit Stores

| Store | Purpose | Retention |
|---|---|---|
| `data/paper_trades.csv` | Persistent paper trade journal | Indefinite |
| `data/trading_brain.db` | Full order/trade records | Indefinite |
| `institutional_dna.db` `audit_log` | Every DNA write with operator/reason/timestamp | Indefinite |
| `data/mls/amls/reports/` | Daily AMLS pipeline reports | Rolling |
| `data/mls/dre/history.json` | DRE reinforcement history | Rolling |
| `data/ars/ptue/` | Constituent history JSON per universe | Indefinite |

---

## 5. Scientific Journal

The `ScientificJournal` (part of Scientific Director) records every SD review and decision.

| Property | Value |
|---|---|
| Storage | `data/ars/scientific_journal.json` |
| Format | Append-only, JSON lines |
| Thread-safe | Yes — `threading.Lock()` |
| Records | `ScientificReview` objects and `ScientificDecision` objects |
| Access | `sd.journal.history()`, `sd.journal.search()`, `sd.journal.stats()` |
| Persistence | Loaded on construction, written on every `record_review()` or `record_decision()` |

---

## 6. Research Loop Operational Readiness

| Activity | Mechanism | Frequency | Status |
|---|---|---|---|
| Gap detection | `GapDetector.detect()` called by SD in `daily_review()` | Daily | ✅ Active |
| Hypothesis generation | SD auto-generates hypotheses for actionable gaps | Daily | ✅ Active |
| Class A study approval | SD `approve_study()` auto-delegates to RC | On demand | ✅ Active |
| Class B escalation | SD → human operator notification | On demand | ✅ Active |
| Study execution | RC 8-stage pipeline with PTUE | On demand | ✅ Active |
| Knowledge update | `KnowledgeProvider` reads RC output | Continuous | ✅ Active |
| Roadmap management | `RoadmapManager` tracks priorities | Continuous | ✅ Active |
| Cross-study synthesis | `CrossStudySynthesizer` weekly | Weekly (SD review) | ✅ Active |
| Evidence validation | `EvidenceValidator` gates hypothesis advancement | On hypothesis update | ✅ Active |

---

## 7. Readiness Summary

| Domain | Readiness |
|---|---|
| Trading platform (17 layers) | ✅ READY |
| Market learning (MLS → IDR → PIG) | ✅ READY |
| Research platform (ARS, RC, PTUE) | ✅ READY |
| Scientific governance (SD) | ✅ READY |
| Knowledge flow (end-to-end) | ✅ READY |
| Risk governance (3 layers + kill-switch) | ✅ READY |
| Failure recovery (isolation, fallbacks) | ✅ READY |
| Telemetry and auditability | ✅ READY |
| Scientific journal | ✅ READY |
| Process safety (PID lock, SIGTERM) | ✅ READY |
| VPS deployment (Docker Compose) | ✅ READY |
| IIOS V1 operational readiness | ✅ **OPERATIONALLY READY** |

---

*Issued: 2026-08-05*

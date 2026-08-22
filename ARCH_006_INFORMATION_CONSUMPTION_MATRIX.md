# ARCH-006 Information Consumption Matrix
**Classifies every data source by how it is consumed in the production cycle**

---

## Classification Scheme

| Tag | Meaning |
|---|---|
| `CONSUMED_BY_KNOWLEDGE` | Input to KDA shadow pipeline (KBE/HBE/KFE) |
| `CONSUMED_BY_RISK` | Input to CRE, RiskGuardian, or PortfolioAllocation |
| `CONSUMED_BY_CONTEXT` | Enriches signals but does not gate them |
| `OBSERVATIONAL_ONLY` | Written to disk for research; never read back in production |
| `DEAD_ORPHAN` | Produced but not consumed by any production path |

---

## Layer 1 — GlobalIntelligence

| Source | Tag | Notes |
|---|---|---|
| S&P 500 futures (yfinance) | `CONSUMED_BY_CONTEXT` | GlobalSnapshot.global_bias fed to MarketSnapshot |
| Nikkei 225 (yfinance) | `CONSUMED_BY_CONTEXT` | Part of global_sentiment_score |
| US 10Y bond yield (yfinance) | `CONSUMED_BY_CONTEXT` | Bond stress indicator |
| USD/INR FX rate (yfinance) | `CONSUMED_BY_CONTEXT` | FX bias in GlobalSnapshot |
| VIX India (yfinance) | `CONSUMED_BY_RISK` | MarketSnapshot.vix → RiskGuardian kill-switch at VIX>45 |

---

## Layer 2 — MarketIntelligence

| Source | Tag | Notes |
|---|---|---|
| NIFTY 50 intraday (yfinance) | `CONSUMED_BY_KNOWLEDGE` | RegimeProbabilityModel → KBE evidence |
| BANKNIFTY intraday (yfinance) | `CONSUMED_BY_KNOWLEDGE` | Sector regime input |
| Advance/Decline ratio | `CONSUMED_BY_RISK` | MarketSnapshot.market_breadth |
| Sector rotation data | `CONSUMED_BY_CONTEXT` | MarketSnapshot.sector_leaders |
| PCR (Put/Call Ratio) | `CONSUMED_BY_RISK` | MarketSnapshot.pcr → RiskGuardian |
| Upcoming events | `CONSUMED_BY_CONTEXT` | MarketSnapshot.events_today |

---

## Layer 3 — MetaLearning

| Source | Tag | Notes |
|---|---|---|
| RegimeStrategyMap (SQLite) | `CONSUMED_BY_CONTEXT` | Strategy weight boosts; advisory, not gating |
| k-NN strategy history | `CONSUMED_BY_CONTEXT` | MetaLearning strategy selection hint |

---

## Layer 4 — OpportunityEngine

| Source | Tag | Notes |
|---|---|---|
| EquityScannerAI signal scores | `CONSUMED_BY_KNOWLEDGE` | TradeSignal.confidence fed to KDA |
| _obs_candidate_score (MOP-RC-001) | `OBSERVATIONAL_ONLY` | Written to JSONL; not read back |
| _obs_regime (MOP-RC-001) | `OBSERVATIONAL_ONLY` | Written to JSONL; not read back |
| EdgeTelemetry JSONL | `OBSERVATIONAL_ONLY` | Research artifact |

---

## Layer 5 — StrategyLab

| Source | Tag | Notes |
|---|---|---|
| evolved_strategies/*.json | `CONSUMED_BY_CONTEXT` | Strategy parameters (SL width, R:R) |
| Backtesting results | `CONSUMED_BY_CONTEXT` | Filters strategies by min_rr gate |

---

## Layer 6 — CapitalRiskEngine (CRE)

| Source | Tag | Notes |
|---|---|---|
| TOTAL_CAPITAL (env) | `CONSUMED_BY_RISK` | ₹10,000 pilot capital baseline |
| MAX_POSITIONS (config) | `CONSUMED_BY_RISK` | 3 at ₹10k → hard cap on open positions |
| MAX_RISK_PER_TRADE_PCT | `CONSUMED_BY_RISK` | 0.25% → ₹25 max risk per trade |
| MAX_DRAWDOWN_PCT | `CONSUMED_BY_RISK` | 10% → ₹1,000 halt threshold |
| MarketSnapshot.regime | `CONSUMED_BY_RISK` | BULL_TREND → higher exposure multiplier |
| MarketSnapshot.vix | `CONSUMED_BY_RISK` | HIGH_VIX → lower exposure multiplier |

---

## KDA Pipeline (Knowledge Authority)

| Source | Tag | Notes |
|---|---|---|
| market_behavior.db | `CONSUMED_BY_KNOWLEDGE` | KBE evidence state (SMA cross, volume) |
| Rejection history | `CONSUMED_BY_KNOWLEDGE` | KBE debunks strategies with consistent rejection |
| HorizonBoundaryEngine analysis | `CONSUMED_BY_KNOWLEDGE` | horizon_p50 from forward curves |
| KnowledgeForwardEngine | `CONSUMED_BY_KNOWLEDGE` | ESS score → KNOWLEDGE_BUY/SELL/HOLD |
| ESS threshold (3.0) | `CONSUMED_BY_KNOWLEDGE` | Gate: ESS≥3 → authorize; <3 → HOLD |

---

## Learning System (Layers 13–14)

| Source | Tag | Notes |
|---|---|---|
| StrategyPerformanceTracker CSV | `CONSUMED_BY_CONTEXT` | Win rate → auto-disable at <40% |
| LearningEngine SQLite | `CONSUMED_BY_CONTEXT` | Pattern storage; feeds MetaLearning |
| DrawdownAnalyzer results | `CONSUMED_BY_CONTEXT` | Reported to dashboard; not production-gating |
| WalkForwardTester results | `CONSUMED_BY_CONTEXT` | Feeds StrategyLab evolution |

---

## ResearchLab / OIOS (Layers 15–16)

| Source | Tag | Notes |
|---|---|---|
| ResearchCoordinator 8-stage pipeline | `DEAD_ORPHAN` | Not wired into any production cycle call |
| MOP-RC-001 observer | `OBSERVATIONAL_ONLY` | Append-only JSONL; never read back |
| ValidationEngine 6-stage | `CONSUMED_BY_CONTEXT` | Gate before ResearchLab promotion |
| OIOS DifferentialResearch | `DEAD_ORPHAN` | Weekly OIOS cycle exists but output not consumed |
| knowledge_pattern_miner | `DEAD_ORPHAN` | Module exists but not called in production |
| knowledge_feedback_loop | `DEAD_ORPHAN` | Module exists but not called in production |
| rejection_tracker | `DEAD_ORPHAN` | Writes rejections; KBE reads from different source |

---

## ControlTower (Layer 17)

| Source | Tag | Notes |
|---|---|---|
| SQLite telemetry DB | `OBSERVATIONAL_ONLY` | Dashboard only; no feedback to decision layer |
| EventBus | `CONSUMED_BY_CONTEXT` | Notifications only |
| Streamlit dashboard | `OBSERVATIONAL_ONLY` | Read-only view |

---

## Dead/Orphan Module Disposition

| Module | Status | Recommended Action |
|---|---|---|
| `ResearchCoordinator` | `DEAD_ORPHAN` | KEEP_RESEARCH — valuable for future automation; must NOT be wired into production without separate audit |
| `MOP-RC-001 observer` | `OBSERVATIONAL_ONLY` | KEEP — append-only, safe |
| `knowledge_pattern_miner` | `DEAD_ORPHAN` | KEEP_RESEARCH — not production-critical |
| `knowledge_feedback_loop` | `DEAD_ORPHAN` | KEEP_RESEARCH — connect only after validation |
| `rejection_tracker` | `DEAD_ORPHAN` | DEPRECATE — KBE reads from its own table; redundant |
| `RegimeStrategyMap` | `CONSUMED_BY_CONTEXT` | KEEP — advisory weight boosts |
| `OIOS DifferentialResearch` | `DEAD_ORPHAN` | KEEP_RESEARCH — output not consumed; safe to leave disconnected |

---

*Generated: ARCH-006 Final Pre-Live Closure | Commit: pending*

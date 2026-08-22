# INFORMATION_FLOW_MATRIX.md
## AI Trading Brain — Data Producer → Consumer Map
### Generated: 2026-08-22 | ARCH-001 Section C

---

## RULE: Every source with WRITE → NO CONSUMER must be classified

| Classification | Meaning |
|---|---|
| CONNECT | Should be connected to production; safe to do now |
| CONTEXT | Informs decisions but not on the critical path |
| RESEARCH | Feeds research/learning pipeline only |
| DEPRECATED | No longer needed; safe to remove |

---

## 1. KLP JSONL  (`data/klp/KLP_YYYY-MM-DD.jsonl`)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | KLPEvaluator (KLP-001 intraday) — KNOWLEDGE_OBSERVATION events; KLPEvaluator (KLP-001 after StrategyLab) — STRATEGY_ANNOTATION events; KLPOutcomeEngine (KLP-002 EOD) — OUTCOME_UPDATE events |
| **WHERE STORED?** | `data/klp/KLP_YYYY-MM-DD.jsonl` |
| **WHO READS IT?** | KLPOutcomeEngine (reads pending observations), HistoricalBehaviourEngine (loads via `load_outcomes()`), KnowledgeFusionEngine (reads as one source), KLP→KSL bridge (`ingest_klp_outcomes()`), tests |
| **WHEN READ?** | EOD (KLP-002), Intraday KDA shadow pipeline (HBE/KFE loaded at first signal of day), KSL bridge (EOD) |
| **USED BEFORE DECISION?** | No — KDA is shadow-only; KLP does not gate intraday decisions |
| **USED AFTER DECISION?** | Yes — outcomes measured T+1..T+5 EOD |
| **AFFECTS KNOWLEDGE?** | Yes — feeds HBE → KDA authority evidence |
| **AFFECTS RISK?** | No direct path; rejection patterns in KLP feed KFE → KDA (shadow) |
| **AFFECTS EXECUTION?** | No |
| **FEEDS LEARNING?** | Yes — KLP-002 outcomes → HBE → KDA; also via KLP→KSL bridge |
| **STATUS** | CONNECTED |

---

## 2. HBE BehaviourMetrics  (in-memory)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | HistoricalBehaviourEngine.load_outcomes() + get_behaviour_profile() |
| **WHERE STORED?** | In-memory (no disk write); source data is KLP JSONL |
| **WHO READS IT?** | KnowledgeDecisionPipeline → passed to KDA.evaluate() as `behaviour` |
| **WHEN READ?** | Intraday, once per signal in shadow pipeline |
| **USED BEFORE DECISION?** | Shadow only (does not gate production decision) |
| **USED AFTER DECISION?** | No |
| **AFFECTS KNOWLEDGE?** | Yes — feeds KDA authority score |
| **AFFECTS RISK?** | No |
| **AFFECTS EXECUTION?** | No |
| **FEEDS LEARNING?** | Not directly; KDA outcome engine uses it indirectly |
| **STATUS** | CONNECTED (via KDA-003 shadow pipeline) |

---

## 3. KFE MultiAngleView  (in-memory)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | KnowledgeFusionEngine.analyse_record() |
| **WHERE STORED?** | In-memory; KFE pool loaded from multiple DB sources |
| **WHO READS IT?** | KnowledgeDecisionPipeline → passed to KDA.evaluate() as `angle_view` |
| **WHEN READ?** | Intraday, per signal (from KFE pool loaded once per day) |
| **USED BEFORE DECISION?** | Shadow only |
| **USED AFTER DECISION?** | No |
| **AFFECTS KNOWLEDGE?** | Yes — 16 angles feed KDA confidence score |
| **AFFECTS RISK?** | No |
| **AFFECTS EXECUTION?** | No |
| **FEEDS LEARNING?** | Indirectly through KDA decisions + outcomes |
| **STATUS** | CONNECTED (via KDA-003 shadow pipeline) |
| **NOTE** | KFE reads 7 sources: rejection_audit.db, ct_decisions, ct_cycles, regime_probability_history.json, KLP JSONL, shadow_evidence_ledger.jsonl, market_behavior.db |

---

## 4. KDA Decisions  (`data/klp/kda/kda_decisions_YYYY-MM-DD.jsonl`)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | KDALedger.record() — called by KnowledgeDecisionPipeline per signal |
| **WHERE STORED?** | `data/klp/kda/kda_decisions_YYYY-MM-DD.jsonl` |
| **WHO READS IT?** | KDALedger.load_decisions() — EOD outcome engine; KDA authority reporter |
| **WHEN READ?** | EOD only (KDA-003 run_eod_knowledge_update) |
| **USED BEFORE DECISION?** | No — written intraday, read EOD only |
| **USED AFTER DECISION?** | Yes — outcomes evaluated against T+1..T+20 bars |
| **AFFECTS KNOWLEDGE?** | Yes — feeds KDA authority validation report |
| **AFFECTS RISK?** | No |
| **AFFECTS EXECUTION?** | No |
| **FEEDS LEARNING?** | Yes — KDA authority grows with accumulated decisions → enables future authority escalation |
| **STATUS** | CONNECTED |

---

## 5. KDA Outcome Records  (in-memory + authority JSON)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | KDAOutcomeEngine.evaluate() — EOD |
| **WHERE STORED?** | In-memory during EOD; summary in `data/klp/kda/kda_authority_validation.json` |
| **WHO READS IT?** | KDAComparativeAnalyzer, KDAAuthorityReporter |
| **WHEN READ?** | EOD (same cycle) |
| **USED BEFORE DECISION?** | No |
| **USED AFTER DECISION?** | Yes — measures direction accuracy |
| **AFFECTS KNOWLEDGE?** | Yes — feeds authority gate (NOT_VALIDATED→PROMISING→USEFUL→VALIDATED→STRONG_VALIDATED) |
| **AFFECTS RISK?** | No |
| **AFFECTS EXECUTION?** | No |
| **FEEDS LEARNING?** | Yes — authority accumulation feeds eventual promotion criteria |
| **STATUS** | CONNECTED |

---

## 6. rejection_audit.db

| Field | Value |
|---|---|
| **WHO WRITES IT?** | RejectionTracker.ingest_rejection() — called by RiskManagerAI.filter() and filter_with_heat_split() after each rejection |
| **WHERE STORED?** | `data/rejection_audit.db` (SQLite) |
| **WHO READS IT?** | KnowledgeFusionEngine.load_fusion_records() — REJECTION_HISTORY angle |
| **WHEN READ?** | Intraday (KFE pool loaded once per day at start of KDA shadow pipeline) |
| **USED BEFORE DECISION?** | Shadow only (KFE → KDA shadow, no production authority) |
| **USED AFTER DECISION?** | No |
| **AFFECTS KNOWLEDGE?** | Yes — one of 7 KFE data sources; influences REJECTION_HISTORY angle |
| **AFFECTS RISK?** | No direct path |
| **AFFECTS EXECUTION?** | No |
| **FEEDS LEARNING?** | Yes — rejection patterns visible to KFE → KDA research loop |
| **STATUS** | CONNECTED (writer newly connected in KDA-003) |

---

## 7. market_behavior.db

| Field | Value |
|---|---|
| **WHO WRITES IT?** | OIOS Phase F (run weekly Saturday 17:30) — market_leaders_daily + market_leader_outcomes |
| **WHERE STORED?** | `data/market_behavior.db` (SQLite) |
| **WHO READS IT?** | MarketBehaviorAdapter.load_market_leader_records() → KFE LEADER_OUTCOME angle |
| **WHEN READ?** | When KFE pool is loaded (once per day at KDA shadow pipeline init) |
| **USED BEFORE DECISION?** | Shadow only |
| **USED AFTER DECISION?** | No |
| **AFFECTS KNOWLEDGE?** | Yes — LEADER_OUTCOME is one of KFE's 16 angles |
| **AFFECTS RISK?** | No |
| **AFFECTS EXECUTION?** | No |
| **FEEDS LEARNING?** | No direct path |
| **STATUS** | CONTEXT — written weekly (potentially stale Mon–Fri); staleness logged in pipeline |
| **STALENESS RISK** | Age > 2 days triggers STALE warning in KDA pipeline |

---

## 8. ct_decisions  (SQLite table in `data/control_tower.db`)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | TelemetryLogger via EventBus — one row per trade decision |
| **WHERE STORED?** | `data/control_tower.db` table `ct_decisions` |
| **WHO READS IT?** | KnowledgeFusionEngine.load_fusion_records() — CT_DECISION angle |
| **WHEN READ?** | When KFE pool loaded (daily) |
| **USED BEFORE DECISION?** | Shadow only |
| **AFFECTS KNOWLEDGE?** | Yes — one of 7 KFE sources (past decision patterns) |
| **FEEDS LEARNING?** | Via KFE → KDA shadow research |
| **STATUS** | CONNECTED |

---

## 9. LearningEngine data  (`data/learning_db.json`)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | LearningEngine.learn() — EOD |
| **WHERE STORED?** | `data/learning_db.json` |
| **WHO READS IT?** | LearningEngine (self), StrategyPerformanceTracker (separate mechanism) |
| **WHEN READ?** | Next intraday cycle (StrategyPerformanceTracker.get_disabled_set() read in StrategyLab) |
| **USED BEFORE DECISION?** | Yes — indirectly: disabled strategies excluded from StrategyLab |
| **AFFECTS KNOWLEDGE?** | No direct path to KDA/HBE/KFE/KLP |
| **AFFECTS RISK?** | No |
| **AFFECTS EXECUTION?** | Indirectly — disabling a strategy prevents it from being assigned |
| **FEEDS LEARNING?** | Self-referential only |
| **STATUS** | CONNECTED (to StrategyLab feedback loop via StrategyPerformanceTracker) |
| **GAP** | Learning outcomes do NOT directly feed KLP/HBE evidence pool. HBE reads from KLP JSONL (market outcomes), not from LearningEngine. This means "strategy failed to take profit at target" is in learning_db.json but the empirical T+1..T+5 market move is in KLP JSONL. Two parallel tracks. |

---

## 10. regime_probability_history.json

| Field | Value |
|---|---|
| **WHO WRITES IT?** | RegimeProbabilityModel after each cycle |
| **WHERE STORED?** | `data/regime_probability_history.json` |
| **WHO READS IT?** | KFE (as one input source), RegimeProbabilityModel (for trend analysis) |
| **USED BEFORE DECISION?** | Shadow only (KFE) |
| **AFFECTS KNOWLEDGE?** | Yes — KFE uses regime probability history for context |
| **STATUS** | CONNECTED |

---

## 11. institutional_dna  (`market_behavior.db` or PIG adapter state)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | MarketLearningCoordinator → DRE (DNA Reinforcement Engine) — EOD |
| **WHERE STORED?** | PIG adapter internal state / market_behavior.db |
| **WHO READS IT?** | PIG adapter → pig_enrich_signals() (Opportunity Engine) and pig_build_vote() (Debate) |
| **WHEN READ?** | Intraday (signal enrichment + debate vote injection) |
| **USED BEFORE DECISION?** | Yes — PIG vote injected into debate |
| **AFFECTS KNOWLEDGE?** | No KDA path |
| **AFFECTS EXECUTION?** | Yes — PIG vote can push confidence score |
| **STATUS** | CONNECTED |

---

## 12. knowledge_evidence_ledger.jsonl

| Field | Value |
|---|---|
| **WHO WRITES IT?** | KLP→KSL bridge (run_klp_loop) EOD; shadow_evidence_consumer (local only, gated) |
| **WHERE STORED?** | `data/knowledge_evidence_ledger.jsonl` |
| **WHO READS IT?** | KFE (as shadow_evidence_ledger source), KSL pattern miner, ResearchCoordinator |
| **WHEN READ?** | When KFE pool loaded (daily) |
| **AFFECTS KNOWLEDGE?** | Yes — one of KFE's data sources |
| **STATUS** | CONTEXT — written EOD via KLP→KSL bridge; KFE reads stale version from previous day |

---

## 13. KSL state  (`data/ksl/ksl_state.json`)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | knowledge_feedback_loop_001.py (run_loop or run_klp_loop) |
| **WHERE STORED?** | `data/ksl/ksl_state.json` |
| **WHO READS IT?** | Same loop (restart-safety watermark) |
| **AFFECTS KNOWLEDGE?** | Ensures idempotent reprocessing only |
| **FEEDS LEARNING?** | Indirectly — prevents re-processing of old evidence |
| **STATUS** | CONTEXT |

---

## 14. MOP-RC001 data  (`data/mop_rc001/MOP_RC001_YYYY-MM-DD.json`)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | EquityScannerAI → MOP-RC001 observer (intraday) |
| **WHERE STORED?** | `data/mop_rc001/MOP_RC001_YYYY-MM-DD.json` (append-only JSONL) |
| **WHO READS IT?** | ResearchCoordinator (for research), tests; NOT read back into pipeline |
| **USED BEFORE DECISION?** | No |
| **AFFECTS KNOWLEDGE?** | No direct path to KDA/HBE/KFE |
| **FEEDS LEARNING?** | Research-only |
| **STATUS** | RESEARCH — observational telemetry; consumer is ResearchCoordinator (not scheduled) |
| **CLASSIFICATION** | RESEARCH — keep; wire ResearchCoordinator when evidence warrants |

---

## 15. shadow_evidence_ledger.jsonl (`data/shadow_evidence_ledger.jsonl`)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | shadow_evidence_consumer_001.py (local only, never scheduled on VPS) |
| **WHERE STORED?** | `data/shadow_evidence_ledger.jsonl` |
| **WHO READS IT?** | KFE (as a source) |
| **USED BEFORE DECISION?** | Shadow only |
| **STATUS** | CONTEXT — may be empty on VPS; KFE handles missing gracefully |

---

## 16. research_question_queue.jsonl

| Field | Value |
|---|---|
| **WHO WRITES IT?** | research_question_generator_001.py (via KSL EOD loop) |
| **WHERE STORED?** | `data/research_question_queue.jsonl` |
| **WHO READS IT?** | ResearchCoordinator (manual invocation), tests |
| **USED BEFORE DECISION?** | No |
| **FEEDS LEARNING?** | Research only — feeds ResearchCoordinator input queue |
| **STATUS** | RESEARCH — queue accumulating; consumed manually or when ResearchCoordinator is scheduled |

---

## 17. V3 Shadow Mover records  (`data/mover_discovery_v3_shadow.jsonl`)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | mover_discovery_v3_shadow_runner.py (16:45 IST, post-market Phase D) |
| **WHERE STORED?** | `data/mover_discovery_v3_shadow.jsonl` |
| **WHO READS IT?** | shadow_evidence_consumer_001.py (LOCAL only — not scheduled on VPS) |
| **USED BEFORE DECISION?** | No |
| **AFFECTS KNOWLEDGE?** | Would feed KSL evidence ledger if consumer were scheduled |
| **STATUS** | RESEARCH — generated daily but consumed locally only; VPS has no path to this data |

---

## 18. KDA Authority Validation  (`data/klp/kda/kda_authority_validation.json`)

| Field | Value |
|---|---|
| **WHO WRITES IT?** | KDAAuthorityReporter.save() — EOD KDA-003 pipeline |
| **WHERE STORED?** | `data/klp/kda/kda_authority_validation.json` |
| **WHO READS IT?** | No production consumer yet; tests; manual review |
| **USED BEFORE DECISION?** | No |
| **AFFECTS KNOWLEDGE?** | Will determine when KDA is promoted from shadow to authority |
| **STATUS** | CONTEXT — gate file for future KDA promotion decision; read manually until VALIDATED gate is reached |

---

## WRITE → NO CONSUMER CLASSIFICATION

| Source | Classification | Justification |
|---|---|---|
| MOP-RC001 JSONL | RESEARCH | Observational telemetry; ResearchCoordinator needs scheduling before activation |
| V3 Shadow records | RESEARCH | Valuable but local-only; no VPS transfer mechanism; WAIT_FOR_EVIDENCE |
| research_question_queue.jsonl | RESEARCH | Accumulating; input to ResearchCoordinator when scheduled |
| KDA authority_validation.json | CONTEXT | Promotion gate file; read manually until VALIDATED threshold reached |
| shadow_evidence_ledger.jsonl | CONTEXT | VPS-safe input to KFE; may be empty but handled gracefully |

---

## DATA FRESHNESS SUMMARY

| Source | Update Frequency | Staleness Risk |
|---|---|---|
| KLP JSONL | Every trading cycle + EOD | Fresh |
| KDA decisions | Every trading cycle | Fresh |
| rejection_audit.db | Every rejection event | Fresh |
| market_behavior.db | Weekly (Saturday) | Stale Mon–Thu; LEADER_OUTCOME angle degraded |
| ct_decisions | Every decision | Fresh |
| learning_db.json | EOD | 1 day stale |
| meta_learning_model.pkl | EOD (retrain_if_due) | Up to 1 week stale |
| V3 shadow records | 16:45 IST daily | Fresh on local; absent on VPS |

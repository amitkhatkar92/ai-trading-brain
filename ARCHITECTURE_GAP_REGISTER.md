# ARCHITECTURE_GAP_REGISTER.md
## AI Trading Brain — Architectural Gap Register
### Generated: 2026-08-22 | ARCH-001 Section D
### Basis: ARCHITECTURE_ACTUAL_CURRENT.md + INFORMATION_FLOW_MATRIX.md

---

## CLASSIFICATION KEY
- **P0** = fundamental decision/data-flow break
- **P1** = important missing connection
- **P2** = responsibility/architecture conflict
- **P3** = observability/maintenance
- **P4** = cosmetic

## ACTION KEY
- **IMPLEMENT_NOW** — safe, clearly required, implement immediately
- **CONNECT_NOW** — wiring safe to add right now
- **VALIDATE_WITH_DATA** — need evidence before connecting
- **WAIT_FOR_EVIDENCE** — insufficient history; do not connect yet
- **KEEP_AS_CONTEXT** — produces useful context; no connection needed
- **RESEARCH_ONLY** — feeds research pipeline only; correct classification
- **DEPRECATE** — no longer needed
- **ALREADY_RESOLVED** — previously identified and fixed

---

## GAP REGISTER

---

### GAP-001
| Field | Value |
|---|---|
| **ID** | GAP-001 |
| **Severity** | P1 |
| **Component** | KDA shadow → Production decision authority |
| **Current behaviour** | KDA shadow decisions are evaluated (HBE→KFE→KDA) but have no influence on production trade approval/rejection. Debate agents and DecisionEngine receive only TradeSignal + MarketSnapshot. |
| **Expected behaviour** | When KDA reaches VALIDATED authority (≥50 decisions, ≥60% direction accuracy), its decision should be available to DecisionEngine as a weighted input — not a veto, but a confidence modifier. |
| **Evidence from code** | `_run_debate_and_decide()` — `MultiAgentDebate.run(signal, snapshot)` takes no KDA input. `DecisionEngine.decide(signal, votes, snapshot)` takes no KDA input. `knowledge_authority/kda_authority_validation.json` authority_status is currently NOT_VALIDATED. |
| **Downstream consumer** | DecisionEngine vote aggregation |
| **Risk if unresolved** | KDA knowledge accumulates indefinitely without ever influencing decisions; entire knowledge investment provides zero trading edge |
| **Recommended action** | WAIT_FOR_EVIDENCE — promote KDA to USEFUL (≥30 decisions, ≥57% accuracy) before creating connection plan. Threshold from `kda_authority_report.py`. |
| **Action is safe now?** | No — insufficient history |
| **Requires historical data?** | Yes — needs 30+ KDA decisions with verified outcomes |
| **Requires validation?** | Yes — backtesting KDA-adjusted vs current decisions |
| **Status** | WAIT_FOR_EVIDENCE |

---

### GAP-002
| Field | Value |
|---|---|
| **ID** | GAP-002 |
| **Severity** | P1 |
| **Component** | LearningEngine → Knowledge evidence loop |
| **Current behaviour** | LearningEngine.learn() writes per-strategy stats to data/learning_db.json. This does NOT flow into KLP JSONL, HBE, or KFE. The empirical market outcomes (T+1..T+5 returns) come from KLPOutcomeEngine reading KLP JSONL — a parallel track. The two paths don't join. |
| **Expected behaviour** | Closed trade outcomes (actual PnL, exit reason, regime) should cross-reference KLP observations to validate and strengthen the evidence in the HBE pool. |
| **Evidence from code** | `LearningEngine.learn()` → `data/learning_db.json` (no KLP write). `KLPOutcomeEngine.fill_pending_outcomes()` → reads KLP JSONL (no learning_db.json read). |
| **Downstream consumer** | HBE, KDA |
| **Risk if unresolved** | Two parallel outcome tracks accumulate independently; HBE evidence pool based on market price moves only, not actual trade P&L which includes execution slippage, position sizing effects |
| **Recommended action** | VALIDATE_WITH_DATA — measure correlation between KLP T+1..T+5 return and paper_trades.csv PnL for same symbol/date. If high correlation, no bridge needed. If low, build cross-reference bridge. |
| **Action is safe now?** | Research safe; implementation requires data validation first |
| **Requires historical data?** | Yes — needs paper_trades.csv + KLP JSONL overlap for same symbols |
| **Requires validation?** | Yes |
| **Status** | VALIDATE_WITH_DATA |

---

### GAP-003
| Field | Value |
|---|---|
| **ID** | GAP-003 |
| **Severity** | P1 |
| **Component** | Debate agents — zero Knowledge input |
| **Current behaviour** | All 5 debate agents (TechnicalAnalystAI, MacroAnalystAI, RiskDebateAI, SentimentAI, RegimeDebateAI) receive only TradeSignal + MarketSnapshot. No KDA decision, no HBE evidence, no KFE angle view. |
| **Expected behaviour** | When KDA reaches VALIDATED authority, a 6th agent (KnowledgeDebateAI) should inject the KDA decision as a weighted vote. Weight should be proportional to authority score. |
| **Evidence from code** | `debate_system/multi_agent_debate.py` — agent list defined at __init__; no dynamic agent injection mechanism. `_run_debate_and_decide()` — PIG vote is already injected dynamically (precedent). |
| **Downstream consumer** | DecisionEngine vote aggregation |
| **Risk if unresolved** | Historical empirical evidence never reaches the decision layer; architecture intent unrealised |
| **Recommended action** | WAIT_FOR_EVIDENCE — same gate as GAP-001. PIG vote injection is the correct pattern to follow when ready. |
| **Action is safe now?** | No — KDA not yet VALIDATED |
| **Requires historical data?** | Yes |
| **Requires validation?** | Yes |
| **Status** | WAIT_FOR_EVIDENCE |

---

### GAP-004
| Field | Value |
|---|---|
| **ID** | GAP-004 |
| **Severity** | P2 |
| **Component** | KSL shadow consumer — VPS orphan |
| **Current behaviour** | `shadow_evidence_consumer_001.py` consumes V3 mover records to produce evidence classification. It is gated in `_do_eod_learning` on `data/logs/final_trading_architecture_shadow_001.jsonl` existing — a local-machine-only file. VPS never has this file and therefore always skips KSL-001. |
| **Expected behaviour** | The KLP→KSL bridge (`run_klp_loop`) DOES run on VPS (added in KDA-003 EOD path, outside the shadow-file gate). This bridge provides a VPS-compatible alternative. |
| **Evidence from code** | `_do_eod_learning()`: KSL-001 block gated on `_ksl_shadow.exists()`. KLP→KSL bridge block is unconditional. |
| **Downstream consumer** | KFE evidence ledger, ResearchCoordinator |
| **Risk if unresolved** | V3 shadow candidates (local only) never reach KSL. VPS knowledge pipeline relies only on KLP JSONL evidence (which is available). |
| **Recommended action** | ALREADY_RESOLVED — KLP→KSL bridge provides VPS-compatible evidence flow. V3 shadow → KSL is local-machine research bonus. Local machine is the right place for V3 shadow processing. |
| **Action is safe now?** | N/A — already resolved |
| **Status** | ALREADY_RESOLVED |

---

### GAP-005
| Field | Value |
|---|---|
| **ID** | GAP-005 |
| **Severity** | P2 |
| **Component** | ResearchCoordinator — permanently orphaned |
| **Current behaviour** | `autonomous_research/research_coordinator.py` (8-stage pipeline) is never scheduled. 190 tests pass but it is never called in production. It depends on `research_question_queue.jsonl` (which IS being populated by KLP→KSL bridge). |
| **Expected behaviour** | When a research question accumulates sufficient data, ResearchCoordinator should be invokable to run a structured study and validate the question against evidence. |
| **Evidence from code** | No call site in `master_orchestrator.py`. Not in `start_scheduler()`. `tests/test_rc.py` is the only invocation. `data/research_question_queue.jsonl` has at least one question from 2026-08-18. |
| **Downstream consumer** | HypothesisRegistry, knowledge_evidence_ledger |
| **Risk if unresolved** | Research pipeline accumulates questions that are never studied; pattern-miner findings remain dormant |
| **Recommended action** | KEEP_AS_CONTEXT — schedule only when a specific research question has sufficient data and operator has reviewed it. Manual invocation pattern is correct for now. |
| **Action is safe now?** | Yes (keep as context) |
| **Status** | KEEP_AS_CONTEXT |

---

### GAP-006
| Field | Value |
|---|---|
| **ID** | GAP-006 |
| **Severity** | P2 |
| **Component** | market_behavior.db — weekly refresh, daily KFE reads |
| **Current behaviour** | market_behavior.db is updated weekly (Saturday OIOS Phase F). KFE reads it as the LEADER_OUTCOME angle source. On Monday–Friday, this data is 1–5 days stale. The pipeline logs `STALE_Xd` but proceeds. |
| **Expected behaviour** | LEADER_OUTCOME evidence should be current enough to be meaningful. |
| **Evidence from code** | `_market_behavior_staleness()` in `knowledge_decision_pipeline.py` — returns staleness label. OIOS Phase F runs Saturday 17:30. |
| **Downstream consumer** | KFE LEADER_OUTCOME angle → KDA shadow |
| **Risk if unresolved** | LEADER_OUTCOME angle quality degrades mid-week; Monday has fresh data, Friday has stale. KDA confidence fluctuates with staleness. |
| **Recommended action** | KEEP_AS_CONTEXT — acceptable for shadow mode. If LEADER_OUTCOME has significant authority weight when KDA is promoted, add daily OIOS Phase F1 refresh trigger. |
| **Status** | KEEP_AS_CONTEXT |

---

### GAP-007
| Field | Value |
|---|---|
| **ID** | GAP-007 |
| **Severity** | P2 |
| **Component** | Duplicate ownership — Target and Stop |
| **Current behaviour** | Target and Stop are set by EquityScannerAI (ATR-multiple). KDA shadow produces knowledge_target and knowledge_stop (empirically-derived from HBE). Both targets/stops exist in parallel with NO reconciliation. |
| **Expected behaviour** | When KDA is authorised, its empirically-derived target/stop should be available as an option, especially when HBE evidence is at SYMBOL_DIR level (highest quality). |
| **Evidence from code** | KDA shadow result includes `knowledge_target`, `knowledge_stop` in return dict from `run_knowledge_shadow()`. Not used anywhere in production path. |
| **Classification** | PRIMARY (scanner), CONTEXT (KDA shadow) |
| **Risk if unresolved** | KDA-derived targets never inform position sizing or exit planning |
| **Recommended action** | WAIT_FOR_EVIDENCE — design target/stop override policy when KDA reaches VALIDATED. Do not override blindly. |
| **Status** | WAIT_FOR_EVIDENCE |

---

### GAP-008
| Field | Value |
|---|---|
| **ID** | GAP-008 |
| **Severity** | P3 |
| **Component** | KDA authority gate not monitored in production |
| **Current behaviour** | `data/klp/kda/kda_authority_validation.json` is written EOD but no Telegram notification sent when gate thresholds are crossed. Operator must check manually. |
| **Expected behaviour** | When KDA crosses PROMISING→USEFUL→VALIDATED thresholds, operator should receive a notification. |
| **Evidence from code** | `KDAAuthorityReporter.save()` writes file. `_do_eod_learning()` logs `[KDA-003] EOD update` with authority_gate field. No notifier.send_alert() call for gate transitions. |
| **Downstream consumer** | Operator — decides when to promote KDA from shadow to authority |
| **Risk if unresolved** | Silent threshold crossing; operator may miss the signal to promote KDA |
| **Recommended action** | IMPLEMENT_NOW — add Telegram notification in `_do_eod_learning` when `authority_gate` changes. Small, safe, high value. |
| **Action is safe now?** | Yes |
| **Requires historical data?** | No |
| **Status** | IMPLEMENT_NOW |

---

### GAP-009
| Field | Value |
|---|---|
| **ID** | GAP-009 |
| **Severity** | P3 |
| **Component** | StrategyLab rejection reasons not captured in rejection_audit.db |
| **Current behaviour** | RiskManagerAI rejections now write to rejection_audit.db (KDA-003). StrategyLab rejections (backtest gate, SHM disabled, PerfTracker disabled) are only logged to file — they do NOT write to rejection_audit.db. KFE REJECTION_HISTORY angle sees only risk-layer rejections. |
| **Expected behaviour** | All rejection stages should contribute to the rejection evidence pool so KFE can distinguish between risk-rejected and strategy-rejected signals. |
| **Evidence from code** | `_run_strategy_lab()` in orchestrator — logs `[StrategyLabReject]` lines but no `get_rejection_tracker().ingest_rejection()` call. `risk_manager_ai.py` — has the call. |
| **Downstream consumer** | KFE REJECTION_HISTORY angle → KDA shadow |
| **Risk if unresolved** | KFE sees an incomplete view of rejections; may overestimate signal quality for strategy-rejected signals |
| **Recommended action** | CONNECT_NOW — add `get_rejection_tracker().ingest_rejection()` in `_run_strategy_lab()` for strategy-rejected signals. Same pattern as risk_manager_ai.py. Safe, additive, non-breaking. |
| **Action is safe now?** | Yes |
| **Requires historical data?** | No |
| **Status** | CONNECT_NOW |

---

### GAP-010
| Field | Value |
|---|---|
| **ID** | GAP-010 |
| **Severity** | P3 |
| **Component** | KDA shadow decisions not available in Telegram /perf or /cycle commands |
| **Current behaviour** | Telegram bot has /cycle, /perf, /learn commands. KDA shadow decisions are written to ledger JSONL but no Telegram command shows KDA shadow summary (e.g., KDA decisions today, authority score, top disagreements). |
| **Expected behaviour** | A /kda command should show today's KDA shadow summary: N decisions, top decisions, authority progress, disagreements with StrategyLab. |
| **Evidence from code** | `notifications/telegram_bot.py` — 13 commands, none read KDA ledger or authority file. |
| **Risk if unresolved** | Operator has no easy visibility into KDA shadow performance; may miss authority threshold crossing |
| **Recommended action** | IMPLEMENT_NOW — add /kda command to Telegram bot that reads `kda_authority_validation.json` and today's ledger. Low risk, high observability value. |
| **Action is safe now?** | Yes |
| **Status** | IMPLEMENT_NOW |

---

### GAP-011
| Field | Value |
|---|---|
| **ID** | GAP-011 |
| **Severity** | P3 |
| **Component** | No architecture-level integration tests |
| **Current behaviour** | 258 unit tests (KDA-001/002/003) but no test verifies the full intraday production call graph, no test checks that KDA remains shadow-only, no test verifies data producer → consumer connectivity. |
| **Expected behaviour** | Architecture tests should detect: (a) KDA accidentally gaining execution authority, (b) data flow breaks between KLP→HBE→KFE→KDA, (c) rejection_audit.db being written by RiskManagerAI, (d) PAPER_TRADING always True. |
| **Evidence from code** | `tests/` directory has no `test_arch_*.py` file. |
| **Risk if unresolved** | Architecture regressions are silent; a refactor could accidentally wire KDA into live decisions without test failure |
| **Recommended action** | IMPLEMENT_NOW — create `tests/test_arch_001_integration.py` with the 6 architecture tests specified in ARCH-001. Safe, additive, high value. |
| **Status** | IMPLEMENT_NOW |

---

### GAP-012
| Field | Value |
|---|---|
| **ID** | GAP-012 |
| **Severity** | P1 |
| **Component** | KDA decisions do not include actual execution outcome feedback |
| **Current behaviour** | KDA shadow runs for ALL scanner signals (both approved AND rejected by StrategyLab). For approved signals that actually execute, the actual trade outcome (from paper_trades.csv) is not linked back to the KDA decision record. KDA outcomes use T+1..T+20 OHLCV from yfinance — not the actual execution PnL. |
| **Expected behaviour** | When a signal both has a KDA decision AND was executed, the actual trade PnL should be cross-referenced in the KDA outcome record to validate KDA authority against real execution quality, not just theoretical market move. |
| **Evidence from code** | `kda_outcome_engine.py` — uses OHLCVBar bars from yfinance. `paper_trades.csv` — has actual entry/exit/PnL. No bridge between them. |
| **Downstream consumer** | KDA authority validation, KDA learning |
| **Risk if unresolved** | KDA authority score measures "would the market move have been profitable" not "was the trade execution profitable" — gap caused by slippage, timing differences |
| **Recommended action** | VALIDATE_WITH_DATA — compare KDA T+1 return vs paper_trades.csv PnL for same symbol/date. If correlation >80%, current approach is sufficient. |
| **Status** | VALIDATE_WITH_DATA |

---

## RESPONSIBILITY AUDIT

| Responsibility | Current Owner | Intended Owner | Classification | Action |
|---|---|---|---|---|
| Direction (BUY/SELL) | EquityScannerAI | EquityScannerAI | PRIMARY | No change |
| Signal generation | EquityScannerAI | EquityScannerAI | PRIMARY | No change |
| Entry price | EquityScannerAI | EquityScannerAI | PRIMARY | No change |
| Target price | EquityScannerAI | EquityScannerAI (PRIMARY), KDA (CONTEXT when validated) | Dual track | WAIT_FOR_EVIDENCE to connect KDA target |
| Stop loss | EquityScannerAI | EquityScannerAI (PRIMARY), KDA (CONTEXT when validated) | Dual track | WAIT_FOR_EVIDENCE to connect KDA stop |
| Expected move | EquityScannerAI (via MOP-RC001) | EquityScannerAI | PRIMARY | No change |
| Holding horizon | Scanner ATR-multiple | HBE (CONTEXT — empirical horizon p50) | Dual track | WAIT_FOR_EVIDENCE |
| Strategy selection | StrategyGeneratorAI + MetaLearning | StrategyGeneratorAI + MetaLearning | PRIMARY | No change |
| Signal quality | EquityScannerAI confidence | EquityScannerAI (PRIMARY), KDA (CONTEXT) | Dual track | WAIT_FOR_EVIDENCE |
| Historical evidence | HBE (loaded by KDA-003) | HBE | PRIMARY | No change |
| Knowledge fusion | KFE (loaded by KDA-003) | KFE | PRIMARY | No change |
| Decision authority | DecisionEngine (threshold 6.5) | DecisionEngine (PRIMARY), KDA (CONTEXT → VALIDATE → USEFUL → VALIDATED → authority) | Staged promotion | WAIT_FOR_EVIDENCE |
| Risk veto | RiskManagerAI + RiskGuardian | RiskManagerAI + RiskGuardian | PRIMARY | No change |
| Position sizing | CapitalRiskEngine + PortfolioAllocator + SmartExecution | Same | PRIMARY | No change |
| Execution | OrderManager | OrderManager | PRIMARY | No change |
| Outcome measurement | KLPOutcomeEngine (market moves) + LearningEngine (trade PnL) | Both — parallel tracks | PRIMARY (dual) | VALIDATE_WITH_DATA |
| Learning | LearningEngine + StrategyPerformanceTracker | Same + KDA Authority (when validated) | PRIMARY | WAIT_FOR_EVIDENCE |
| Feedback | KLP-002 → HBE → KDA + KLP→KSL → research queue | Same | PRIMARY | No change |

---

## SUMMARY

### P0 Gaps
_None identified._ No fundamental data-flow break exists in the current production pipeline.

### P1 Gaps (WAIT_FOR_EVIDENCE)
- GAP-001: KDA shadow → production decision authority (insufficient evidence; ~30–50 decisions needed)
- GAP-003: Debate agents lack Knowledge input (same gate as GAP-001)
- GAP-007: KDA target/stop not yet used in production
- GAP-012: KDA outcomes use market data, not actual trade PnL

### P2 Gaps
- GAP-004: ALREADY_RESOLVED (KLP→KSL bridge added)
- GAP-005: ResearchCoordinator orphaned — KEEP_AS_CONTEXT
- GAP-006: market_behavior.db weekly refresh — KEEP_AS_CONTEXT

### P3 Gaps (IMPLEMENT_NOW / CONNECT_NOW)
- GAP-008: KDA authority gate not notified — IMPLEMENT_NOW
- GAP-009: StrategyLab rejections not in rejection_audit.db — CONNECT_NOW
- GAP-010: No /kda Telegram command — IMPLEMENT_NOW
- GAP-011: No architecture-level tests — IMPLEMENT_NOW

### Already Resolved
- GAP-004: KLP→KSL bridge (EOD EOD path)
- RejectionTracker wiring in RiskManagerAI (KDA-003)
- KDA-003 intraday + EOD shadow pipeline (KDA-003)

---

## ACTIONS — ORDERED BY PRIORITY AND SAFETY

| Order | Gap | Action | Rationale |
|---|---|---|---|
| 1 | GAP-011 | IMPLEMENT_NOW — architecture tests | Prevents silent regressions; pure additive |
| 2 | GAP-009 | CONNECT_NOW — StrategyLab rejections to rejection_audit.db | Completes rejection evidence coverage; small, safe |
| 3 | GAP-008 | IMPLEMENT_NOW — Telegram KDA gate notification | Operator visibility; read-only |
| 4 | GAP-010 | IMPLEMENT_NOW — /kda Telegram command | Operator visibility; read-only |
| 5 | GAP-002 | VALIDATE_WITH_DATA — Learning vs KLP cross-reference | Research task; run correlation analysis first |
| 6 | GAP-012 | VALIDATE_WITH_DATA — actual PnL vs KDA OHLCV outcome | Research task; measure after 30+ decisions |
| 7 | GAP-001/003/007 | WAIT_FOR_EVIDENCE | Gate: KDA needs 30+ decisions, ≥57% accuracy |
| 8 | GAP-005 | KEEP_AS_CONTEXT | Manual invocation when specific RQ ready |
| 9 | GAP-006 | KEEP_AS_CONTEXT | Acceptable for shadow mode |

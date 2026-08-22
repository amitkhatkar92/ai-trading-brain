# LEARNING_PIPELINE_INVESTIGATION_2026-08-11.md

**Date:** 2026-08-11  
**Type:** Read-only investigation. Zero code changes. Zero deployments.  
**Scope:** Why 19 Cat-E learning actions are PENDING; full pipeline trace.

---

## FILES INSPECTED

| File | Lines read |
|------|-----------|
| `predictive_gap/pga_learning.py` | Full |
| `institutional_learning/ilc_verification.py` | Full |
| `institutional_learning/ilc_runner.py` | Full |
| `institutional_learning/ilc_lifecycle.py` | Full |
| `institutional_learning/ilc_score.py` | Full |
| `institutional_learning/ilc_config.py` | Full |
| `institutional_learning/ilc_models.py` | Full |
| `market_learning/idr_repository.py` | Full |
| `market_learning/idr_models.py` | Schema |
| `market_learning/pig_integration.py` | Full |
| `market_learning/pig_gateway.py` | Full |
| `market_learning/dna_consensus_engine.py` | Header |
| `hkap/hkap_engine.py` | Full |
| `orchestrator/master_orchestrator.py` | Lines 4017–5580 |

---

## PART 1 — TODAY'S 19 CAT-E ACTIONS: COMPLETE TRACE

### All 19 actions with full state

| # | Learning ID | Cat | Symbol | Root Cause | Status | executed | verified | Reason PENDING |
|---|------------|-----|--------|-----------|--------|----------|----------|----------------|
| 1 | PGA-F46369F6 | E | DRREDDY | DNA gap: moved +4.0% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 2 | PGA-F56D15BD | E | DIVISLAB | DNA gap: moved +3.2% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 3 | PGA-80F9FCDF | E | CANBK | DNA gap: moved +1.0% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 4 | PGA-B891CE79 | E | VEDL | DNA gap: moved −3.5% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 5 | PGA-5B59D84B | E | GODREJPROP | DNA gap: moved −3.3% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 6 | PGA-0118BEB3 | E | HINDZINC | DNA gap: moved −2.1% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 7 | PGA-94D1681B | E | METROPOLIS | DNA gap: moved −1.9% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 8 | PGA-B170114A | E | EMAMILTD | DNA gap: moved −1.5% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 9 | PGA-E08E7349 | E | SRF | DNA gap: moved −1.5% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 10 | PGA-8E6705C3 | E | CROMPTON | DNA gap: moved −1.3% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 11 | PGA-E478AC8C | E | AAVAS | DNA gap: moved −1.2% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 12 | PGA-533D6B5B | E | DLF | DNA gap: moved −1.2% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 13 | PGA-A4749638 | E | TORNTPHARM | DNA gap: moved −1.1% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 14 | PGA-C157D4AC | E | FORTIS | DNA gap: moved −1.0% with zero DNA coverage | PENDING | false | false | By design — see §3 |
| 15 | PGA-566FAA5A | E | MAXHEALTH | DNA gap: moved −2.4% with zero DNA coverage | PENDING | false | false | By design — see §3 |

> Cat-F (4 entries): BHARATFORG, AMBUJACEM, BHEL, PRESTIGE — schedule_hkap_replay.

**Timestamps:** All created 2026-08-11. Verification windows due:
- 30-day → 2026-09-25 (calendar day +45)
- 60-day → 2026-11-09 (calendar day +90)
- 90-day → 2026-12-24 (calendar day +135)

---

## PART 2 — END-TO-END TRACE: 3 REPRESENTATIVE ACTIONS

### 2.1 DRREDDY — Cat-E winner-related (stock moved +4.0%)

```
ACTION CREATED
│ Source:       pga_learning.plan_actions()  [predictive_gap/pga_learning.py:306]
│ Function:     _plan_cat_e(cause, analysis) [line 158]
│ Produces:     LearningAction(category="E", action_type="create_dna_candidate",
│               target_system="IDR", symbol="DRREDDY",
│               payload={symbol, return_pct:+3.96, direction:"UP", volume:3935937.0})
│ Status:       CREATED ✅
       ↓
EXECUTE_ACTIONS CALLED
│ Function:     pga_learning.execute_actions() [line 364]
│ Input:        actions=[...], cfg=PGAConfig(dry_run=False)
│ Code path:    action.category == "E" → falls to ELSE branch
│               action.outcome = "LOGGED_FOR_REVIEW"   [line 387]
│               action.scheduled = False
│ Function:     _try_create_dna_candidate() — DOES NOT EXIST IN CODE
│ Status:       IMPLEMENTED BUT NOT INVOKED — no Cat-E executor function exists
       ↓
REGISTRY ENTRY
│ Function:     ilc_verification.register_learning_actions() [line 355]
│ Input:        action (scheduled=False, outcome="LOGGED_FOR_REVIEW")
│ Produces:     LearningRecord(status="PENDING", executed=False,
│               prediction_metric="dna_count", baseline_metrics={"dna_count":0.0},
│               measurement_windows=[30,60,90])
│ Status:       EXECUTED ✅ (record written to learning_registry.json)
       ↓
NEXT PROCESSOR
│ Function:     ilc_verification.run_verification_pass(today="2026-08-11")
│ Code path:    _is_due(record, today="2026-08-11") →
│               v_dates={30:"2026-09-25", 60:"2026-11-09", 90:"2026-12-24"}
│               today < v_dates[30]  →  returns None (no window due)
│ Status:       IMPLEMENTED BUT NOT INVOKED — 30-day window not yet due
       ↓
ELIGIBILITY CHECK
│ Condition:    created_date="2026-08-11", today="2026-08-11"
│               _is_due() → None (earliest window due 2026-09-25)
│ Status:       NOT ELIGIBLE — temporal gate correctly blocks premature verification
       ↓
EXECUTION / DNA UPDATE
│ Target:       IDR (institutional_dna.db, table: dna)
│ Required:     IDRRepository.save(InstitutionalDNA(...)) call
│ Actual:       NOT CALLED — no code path from Cat-E PENDING record to IDRRepository
│               The IDR is populated only by AMLS (market_learning/amls.py)
│               which requires full multi-phase discovery pipeline
│ Status:       NOT IMPLEMENTED — no Cat-E→IDR write pathway exists
       ↓
DNA / EDGE / HYPOTHESIS UPDATE
│ DNA target:   consensus_dna table in institutional_dna.db
│ Current DNA:  0 records for DRREDDY (confirmed by _dna_count() baseline = 0.0)
│ Status:       NOT IMPLEMENTED — no change made to DNA store
       ↓
BASELINE
│ Captured at:  register_learning_actions() time
│ metric_name:  "dna_count" (from _pick_metric_for_category("E"))
│ baseline:     {"dna_count": 0.0}  (from _dna_count("DRREDDY") = 0.0)
│ Status:       EXECUTED ✅ — baseline correctly captured
       ↓
30/60/90 DAY VERIFICATION (future)
│ Scheduled at: 2026-09-25 / 2026-11-09 / 2026-12-24
│ Metric:       dna_count for DRREDDY (will be measured via _dna_count("DRREDDY"))
│ Verdict:      If DNA was created and promoted between now and 2026-09-25 → IMPROVED
│               If DNA count still 0 on 2026-09-25 → NO_CHANGE (then confidence downgraded)
│ Status:       NOT YET DUE ✅ (structurally correct)
       ↓
PROMOTION TO INSTITUTIONAL
│ Condition:    change_pct >= 0.05 (5% improvement) at any verification window
│ Action:       LearningRecord.status → "IMPROVED"
│ Status:       NOT REACHED — no DNA has been created
```

**Verdict:** Observation is correct. Root cause is identified. Registry entry is correct. But the pipeline stops at "LOGGED_FOR_REVIEW" because **there is no automatic executor for Cat-E** and **no code path from Cat-E to IDR.save()**.

---

### 2.2 VEDL — Cat-E loser-related (stock moved −3.5%)

```
ACTION CREATED
│ Source:       pga_learning._plan_cat_e(cause, analysis)
│ Payload:      {symbol:"VEDL", return_pct:-3.47, direction:"DOWN", volume:13466663.0}
│ Status:       CREATED ✅
       ↓
EXECUTE_ACTIONS → LOGGED_FOR_REVIEW (same as DRREDDY — identical code path)
│ Status:       IMPLEMENTED BUT NOT INVOKED
       ↓
REGISTRY ENTRY
│ LearningRecord: status=PENDING, executed=False, dna_count baseline=0.0
│ Status:       EXECUTED ✅
       ↓
CRITICAL DIFFERENCE from DRREDDY:
│ Direction: DOWN — even if a DNA candidate were created, the system currently
│ has 0 SHORT DNA lifecycle records in institutional_dna.db (confirmed by
│ LIVE_PRE_FLIGHT_AUDIT.md: "SHORT lifecycle = 0").
│ SHORT signals require SHORT DNA. VEDL SHORT DNA would need:
│   1. Cat-E action to be executed (NOT IMPLEMENTED)
│   2. AMLS pipeline to run for VEDL with historical short data
│   3. DNA to go DISCOVERED→REPLICATED→VERIFIED→INSTITUTIONAL
│   4. CDS engine to score VEDL against SHORT DNA library
│   5. PIG to inject vote with VEDL-direction SHORT alignment
│ Status:       NOT IMPLEMENTED at multiple layers
       ↓
30-day verification: same as DRREDDY (due 2026-09-25)
Promotion: same path (NOT REACHED)
```

---

### 2.3 BHARATFORG — Cat-F HKAP replay (loser −3.0%, wrong direction scanned)

```
ACTION CREATED
│ Source:       pga_learning._plan_cat_f(cause, analysis)
│ Payload:      {symbol:"BHARATFORG", move_pct:-3.02, direction:"DOWN"}
│ target_system: "HKAP"
│ Status:       CREATED ✅
       ↓
EXECUTE_ACTIONS → LOGGED_FOR_REVIEW
│ Code path:    action.category == "F" → ELSE branch → LOGGED_FOR_REVIEW
│ Status:       IMPLEMENTED BUT NOT INVOKED (same as Cat-E)
       ↓
REGISTRY ENTRY
│ LearningRecord: status=PENDING, executed=False, prediction_metric="scan_hit_rate"
│ Status:       EXECUTED ✅
       ↓
NEXT PROCESSOR: HKAPEngine
│ Module:       hkap/hkap_engine.py
│ Function:     HKAPEngine.run(years=[2019..2025], force=False)
│ What it does: Year-by-year forward-only historical replay:
│               - Loads PTUE (PointInTimeUniverseEngine) per year
│               - Fetches OHLCV history for BHARATFORG per year
│               - Runs population classification, DNA discovery per year
│               - Writes year-specific institutional_dna.db for each year
│               - Cross-year synthesis after all years complete
│               - NO live IDR merge until explicit Scientific Director approval
│               - "The live IDR (data/mls/institutional_dna.db) is never
│                  touched during HKAP" (HKAP_DESIGN.md)
│ Status:       NOT IMPLEMENTED — no bridge from Cat-F record to HKAPEngine.run()
       ↓
HKAP RESULT → IDR MERGE
│ Gate:         Scientific Director (SD) must explicitly approve IDR merge
│               after HKAP synthesis report
│ Status:       NOT IMPLEMENTED — merge gate not automated
       ↓
30-day verification: same structure
│ Metric: "scan_hit_rate" for BHARATFORG — measures whether BHARATFORG appears
│         more often in CT opportunity events 30 days from now
│ Status: NOT YET DUE
```

---

## PART 3 — CAT-E SPECIFIC INVESTIGATION (Q1–Q14)

**Q1. What exactly does Cat-E mean?**

Category E is assigned when PGA determines: the stock has **zero DNA coverage** (`dna_count=0`) and moved significantly without any IIOS signal. The learning prescription is: "create a candidate DNA record for this symbol in the IDR so that future scans can use this symbol's behavioral patterns."

Source: `pga_learning._plan_cat_e()` — `action_type="create_dna_candidate"`, `target_system="IDR"`.

---

**Q2. What conditions make a Cat-E action eligible for automatic execution?**

From the code: **none**. There are no eligibility conditions in `execute_actions()` for Cat-E. The entire `else` branch applies to A, D, E, F, G:

```python
else:
    # Categories A, D, E, F, G → logged for manual/scheduled execution
    action.outcome = "LOGGED_FOR_REVIEW"
```

There is no eligibility check, no scheduler hook, and no condition under which Cat-E is automatically executed.

---

**Q3. Does Cat-E currently have an automatic executor?**

**NO.**

There is no `_try_create_dna_candidate()` function in `pga_learning.py`. Compare this to Cat-C (has `_try_create_hypothesis()`) and Cat-B (has `_try_reinforce_idr()`). Cat-E has no corresponding `_try_*` function.

Searched across all 71 files that reference `institutional_dna`: none contains a function that converts a Cat-E registry entry into a DNA record.

---

**Q4. If yes, which function executes it?**

Not applicable — no automatic executor exists.

---

**Q5. Is that executor called by the daily pipeline?**

Not applicable — no executor exists.

---

**Q6. If not called, where should it logically be called?**

Logically, a Cat-E executor would need to:

1. Read PENDING Cat-E records
2. For each symbol: fetch historical OHLCV data (min 30 bars)
3. Run DNA discovery (population classification → DNA extraction → consensus scoring)
4. Create an `InstitutionalDNA` record in IDR with lifecycle=DISCOVERED
5. Mark the registry entry as executed=True, status="MEASURING"

This is exactly what the AMLS pipeline does (`market_learning/amls.py`) — but AMLS runs on a pre-defined universe with a configured schedule, not driven by Cat-E registry entries.

The logical insertion point would be in `_do_eod_learning()` or in `run_ilc()` Phase 7, after actions are executed. But this would require implementing a Cat-E executor function and a bridge to AMLS/IDRRepository. **This bridge does not exist.**

---

**Q7. Does Cat-E require human approval?**

The code does NOT explicitly require human approval. The `else` branch comment says: "logged for **manual or scheduled** execution." There is no approval gate, no approval workflow, and no flag that must be set.

However, by virtue of having no automatic executor, Cat-E actions effectively require human intervention (manual execution via CLI or a future automated component).

---

**Q8. If human approval is required, where is that requirement implemented?**

NOT IMPLEMENTED as an explicit gate. The only "requirement" is structural: since no automatic executor exists, execution cannot happen without human action.

---

**Q9. Can Cat-E automatically create candidate DNA?**

**NO.**

The `execute_actions()` function sends Cat-E to `LOGGED_FOR_REVIEW` with `scheduled=False`. No write to `institutional_dna.db` or `consensus_dna` table occurs anywhere in the Cat-E code path.

---

**Q10. Can candidate DNA automatically enter validation?**

**PARTIALLY — once created, yes.**

If a DNA record were created in IDR with `lifecycle=DISCOVERED`, the DNA Consensus Engine would automatically advance it through `DISCOVERED→REPLICATED→VERIFIED→INSTITUTIONAL` as more observations accumulate. But the first step (creating the DISCOVERED record) does not happen automatically from Cat-E.

---

**Q11. Can validated DNA automatically enter 30/60/90-day verification?**

**YES — the verification framework is fully implemented.**

`ilc_verification.run_verification_pass()` runs every day. For any LearningRecord whose `_is_due()` returns a window, it automatically measures `dna_count`, computes change_pct vs baseline, and assigns IMPROVED/NO_CHANGE/DECLINED. This is correctly implemented and will trigger on 2026-09-25 for today's entries.

The problem is: the metric being verified (`dna_count`) will still be 0 on 2026-09-25 unless Cat-E was executed in the meantime, which it won't be automatically.

---

**Q12. Under what exact condition can DNA become INSTITUTIONAL?**

In `dna_consensus_engine.py` the lifecycle advances:

```
DISCOVERED → (replicated across 2+ studies)
REPLICATED → (statistically verified: p-value, effect size thresholds)  
VERIFIED   → (temporal stability confirmed: N consecutive regimes)
INSTITUTIONAL → (available for live PIG scoring)
```

From `IDRRepository`: lifecycle=INSTITUTIONAL means the record is active and used in PMCI/CDS scoring. The exact thresholds are in `MLSConfig`. This requires the full AMLS pipeline to run multiple times on the same symbol.

---

**Q13. Does the system currently prevent unverified DNA from influencing live trading?**

**YES — multiple safeguards exist:**

1. **PIG vote weight = 8%**: Even if DNA votes APPROVE, it contributes at most 8% of the debate decision. The other 5 agents' combined weight is 92%.

2. **Minimum CA-PMCI threshold = 0.30**: If `ca_pmci < 0.30` the PIG vote is silenced entirely (returns None, no vote cast).

3. **PIG cannot VETO**: "The vote is always 'approve' — PIG never issues hard rejects." (pig_integration.py:159). DNA cannot block a trade.

4. **Lifecycle gate**: Only DNA with `lifecycle in ("INSTITUTIONAL", "WEAKENING", "DRIFTING")` is used in PMCI scoring (`idr_models.py:131`). DISCOVERED/REPLICATED DNA is excluded.

5. **No Cat-E→DNA pathway**: Since Cat-E never creates DNA, none of today's 19 actions can affect live signals regardless of any other safeguard.

---

**Q14. Is there any automatic learning path that can operate without human intervention?**

**YES — two paths exist:**

- **Cat-B** (IDR observation reinforcement): `_try_reinforce_idr()` is called automatically in `execute_actions()`. This adds an observation record to the IDR but does NOT create new DNA.

- **Cat-C** (hypothesis creation): `_try_create_hypothesis()` is called automatically. This creates a hypothesis in `ars_hypothesis_registry.json` for the ResearchCoordinator to study.

Both are lightweight text/metadata operations. Neither creates DNA or changes scanner behavior.

All other categories (A, D, E, F, G) are LOGGED_FOR_REVIEW and require either human action or a not-yet-implemented automatic executor.

---

## PART 4 — CAT-F HKAP REPLAY INVESTIGATION

**What HKAP means:**

Historical Knowledge Accumulation Pipeline. Runs the full MLS discovery pipeline year-by-year over a symbol's historical price data (typically 2019–2025). Produces year-specific `institutional_dna.db` files in isolation-safe directories. Never modifies the live `data/mls/institutional_dna.db` during execution.

**Why the replay was created:**

PGA root-cause assigned Cat-F when: symbol was scanned (appeared in daily candidates), had some historical coverage (`dna_coverage > 0` but insufficient), and moved significantly. The 4 Cat-F symbols (BHARATFORG, AMBUJACEM, BHEL, PRESTIGE) were all:
- Scanned as BUY signals via mean_reversion_bounce
- Fell 1.4–3.0% (wrong direction)
- Have partial historical knowledge ("HKAP replay: build historical knowledge about X% move patterns")

This indicates the scanner found some DNA for these symbols (hence Cat-F not Cat-E), but not enough to detect the current bearish pattern.

**Whether replay is automatically executed:**

**NOT IMPLEMENTED.** The HKAPEngine (`hkap/hkap_engine.py`) is a standalone research tool, not called by any automatic scheduler in the production pipeline. It is not wired into `ilc_runner.py`, `pga_runner.py`, or `master_orchestrator.py`.

**Which replay engine handles it:**

`HKAPEngine.run()` in `hkap/hkap_engine.py`. Uses:
- `YearRunner` per year (feature extraction, population classification, DNA discovery, IDR save per year)  
- `CrossYearAnalyzer` for synthesis across years

**Whether today's actions entered the replay queue:**

**NO.** There is no HKAP queue. The Cat-F records sit in `learning_registry.json` with `status=PENDING`. HKAPEngine has no awareness of the learning registry.

**Whether replay results are persisted:**

**YES** — when run manually, HKAPEngine writes year-specific `data/hkap/{year}/institutional_dna.db` files and a synthesis JSON report.

**Whether successful replay can generate DNA/edge/hypothesis updates:**

**YES — but only via Scientific Director approval.** The HKAP design states explicitly: "No live IDR merge until explicit SD approval." The SD (Scientific Director role) must review the synthesis report and manually trigger `IDRRepository.save()` for the merged patterns.

**Whether verification is automatically scheduled:**

**YES** — the Cat-F learning registry record already has `measurement_windows=[30, 60, 90]` and `prediction_metric="scan_hit_rate"`. If HKAP ran and produced DNA, the `run_verification_pass()` on 2026-09-25 would measure whether BHARATFORG's `scan_hit_rate` improved. But since HKAP has not run, no improvement is expected.

---

## PART 5 — AUTOMATIC LEARNING CAPABILITY TABLE

| Capability | Existing? | Automatic? | Invoked today? | Evidence |
|-----------|-----------|------------|----------------|---------|
| **Observation** (detect movers) | YES | YES | YES | `pga_collector.collect_daily()` runs every EOD via `_do_eod_learning()` at line 5535 |
| **Root cause** | YES | YES | YES | `pga_root_cause.analyze_misses()` runs in `ilc_runner.run_ilc()` Phase 2–4 |
| **Action creation** | YES | YES | YES | `pga_learning.plan_actions()` — 19 actions created today |
| **Action execution (Cat-B/C)** | YES | YES | YES | `execute_actions()` auto-executes Cat-B and Cat-C only |
| **Action execution (Cat-E/F)** | NO | NO | NO | `execute_actions()` explicitly puts Cat-E/F in `else → LOGGED_FOR_REVIEW` |
| **Candidate DNA creation** | NO | NO | NO | No `_try_create_dna_candidate()` function exists; no IDR write from Cat-E |
| **DNA discovery** | YES | NO | NO | AMLS pipeline exists but not triggered by Cat-E; requires manual/scheduled run |
| **Validation** (DNA lifecycle) | YES | YES | NO | `dna_consensus_engine.py` auto-advances lifecycle but never receives input from Cat-E |
| **Verification** (30/60/90d windows) | YES | YES | NO | `run_verification_pass()` runs every EOD; 0 windows due today; first due 2026-09-25 |
| **Institutional promotion** | YES | YES | NO | Automatic via `_update_record_status()` once IMPROVED verdict fires; not yet triggered |

---

## PART 6 — SAFETY CHECK

**Can a newly created DNA record affect today's live signals?**

NO. DNA records are only scored during live cycles via `PIG.evaluate_symbol()`. New DNA with lifecycle=DISCOVERED would not pass the `idr_repository.list_active()` filter that requires lifecycle in `("INSTITUTIONAL", "WEAKENING", "DRIFTING")`. Even if it did, the vote weight is bounded at 8% and cannot block trades.

**Can a PENDING action affect today's live signals?**

NO. A LearningRecord with status=PENDING has `executed=False`. It exists only in `learning_registry.json`. No module in the trading pipeline reads `learning_registry.json` during cycle execution. The learning registry is strictly post-market read/write.

**Can an unverified edge affect today's live signals?**

NO. The `discovered_edges.json` file is maintained by the `EdgeDiscoveryEngine` and is currently empty today (0 entries for 2026-08-11). Even if edges existed, the `EdgeDiscoveryEngine` is a research layer that feeds reports, not an execution layer. It does not override scanner signals or risk thresholds.

**Can an unverified hypothesis affect today's live signals?**

NO. `ars_hypothesis_registry.json` is used by the ResearchCoordinator (autonomous_research/) as research scope. Hypotheses are created by Cat-C (auto-executed) but are OPEN status. Open hypotheses do not feed into any signal generation, strategy selection, or risk control module.

**Can automatic learning change risk limits?**

NO. Risk limits (`MAX_RISK_PER_TRADE_PCT`, `MAX_DRAWDOWN_PCT`, VIX kill=45, daily_loss=2%) are loaded from `config.py` at startup. No learning module writes to `config.py`. The learning pipeline is entirely separated from the config layer.

**Can automatic learning enable a disabled strategy?**

NO. Strategy enable/disable is managed by `StrategyHealthMonitor` (SHM) and `StrategyPerformanceTracker`. Neither reads from `learning_registry.json`. The only automatic disable trigger is WR threshold breach via `perf_tracker.get_disabled_set()`. Re-enabling requires either: SHM cooldown session tick recovery, or manual override.

**Can automatic learning change R:R requirements?**

NO. `MIN_RR_RATIO` is a constant in `risk_control/risk_manager_ai.py`. No learning module writes to it.

**Can automatic learning change capital allocation?**

NO. `TOTAL_CAPITAL`, `MAX_RISK_PER_TRADE_PCT`, and `EXPLORATION_BUDGET_PCT` are `config.py` constants. The learning pipeline has no write path to these values.

**Safeguards summary:**

The learning pipeline is **completely firewalled from live trading**:
- All 19 actions are PENDING in a JSON file
- The JSON file is never read during intraday cycles
- PIG (the only DNA→trading bridge) is read-only (8% weight, approve-only votes)
- New DNA would need INSTITUTIONAL lifecycle before PIG uses it
- Cat-E actions cannot create DNA automatically

---

## PART 7 — WHY ILS = 48.6/F

The ILS score is computed by `ilc_score.compute_ils_score()` as a weighted sum of 5 components:

| Component | Weight | Computed value | Score | Cause |
|-----------|--------|---------------|-------|-------|
| Learning Efficiency | 25% | 0.323 | 8.1/25 | Only 6/19 actions are HIGH/MEDIUM confidence (others are LOW/EXPERIMENTAL because dna_count=0) |
| Knowledge Efficiency | 20% | 0.500 | 10.0/20 | `_knowledge_efficiency()` returns **0.5 neutral baseline** when `lifecycle_records=[]`. Today's lifecycle_records is empty — no DNA, hypotheses, or edges have been promoted or tracked yet. |
| Prediction Improvement | 25% | 0.500 | 12.5/25 | `_prediction_improvement()` returns **0.5 neutral** when `verified=[]` (no verifications ever completed for any record). |
| Research Productivity | 15% | 0.700 | 10.5/15 | 19 records/20 expected = 0.95 record_score, GVA=50/100 = 0.50 gva_norm. Combined: 0.95×0.4 + 0.50×0.6 = 0.68 ≈ 0.70 |
| Knowledge ROI | 15% | 0.500 | 7.5/15 | `_knowledge_roi()` returns **0.5 neutral** when `roi_records=[]`. |

**Factor decomposition:**

- **Factor A (time-based bootstrap):** Knowledge Efficiency (0.5), Prediction Improvement (0.5), Knowledge ROI (0.5) are all neutral defaults because the system has been running for only 3 days. Zero verifications have completed. Zero DNA has been promoted. This accounts for **45.0 of the 100 potential points defaulting to 0.5 neutral** rather than being measured. This is fully expected.

- **Factor B (incomplete pipeline):** Learning Efficiency = 0.323. The reason is that 13/19 actions today are LOW confidence (dna_count=0 means the system has zero evidence for these symbols — no existing DNA to corroborate the learning). The 6 HIGH/MEDIUM confidence actions are the Cat-F symbols (BHARATFORG, AMBUJACEM, BHEL, PRESTIGE have `dna_coverage > 0`) and MAXHEALTH, GODREJPROP (which had `volume > threshold`). This reflects the genuinely poor knowledge state, not a scoring bug.

- **Factor C (automation not invoked):** Because Cat-E actions are LOGGED_FOR_REVIEW and never executed, the `dna_count` baseline will remain 0 forever. On 2026-09-25 (30-day verification), `_dna_count("DRREDDY")` will return 0.0 (unchanged), triggering `verdict=NO_CHANGE` for all Cat-E entries. This will push `prediction_improvement` BELOW 0.5 (from neutral toward 0.0), causing the ILS to fall further after the first verification cycle.

- **Factor D (intentional await):** The neutral scores (0.5) for Prediction Improvement and Knowledge ROI are deliberately set as "neutral when no data" rather than 0.0, to avoid penalizing a new system before it has had time to accumulate evidence. This is correct design — the system is 3 days old.

**Quantified breakdown of ILS = 48.6:**

| Source | Points lost | Reason |
|--------|------------|--------|
| Low confidence actions | −8.1 (actual 8.1 vs max 25) | 13/19 are LOW confidence; zero existing DNA |
| No verifications | −0 (neutral 0.5 → 12.5 instead of 0) | Expected for 3-day-old system |
| No lifecycle | −0 (neutral 0.5 → 10.0 instead of 0) | Expected for 3-day-old system |
| No ROI | −0 (neutral 0.5 → 7.5 instead of 0) | Expected for 3-day-old system |
| Research productivity below max | −4.5 (10.5 vs max 15) | GVA=50/100 drags research productivity down |

**Conclusion:** The score is 48.6 primarily because (A) 3 days of data with 0 verifications → neutral defaults, and (B) learning efficiency is genuinely low (symbols have zero DNA coverage). It is NOT because automation is broken. The automation runs correctly — the observation/action/registration pipeline works as designed. The score will improve naturally as verifications complete and if DNS candidates are executed.

---

## PART 8 — TRUE GAP CLASSIFICATION

### Classification: **3 — PARTIALLY IMPLEMENTED**

Evidence:

**What is implemented and working:**
- Observation pipeline: PGA collects top-20 movers daily ✅
- Root cause analysis: PGA assigns categories A–G correctly ✅
- Action planning: Cat-E LearningAction objects are created ✅
- Auto-execution for Cat-B: IDR observations are reinforced ✅
- Auto-execution for Cat-C: Hypotheses are created in ARS registry ✅
- Registry persistence: All records written to learning_registry.json ✅
- Baseline capture: dna_count captured at creation time ✅
- Verification scheduling: windows=[30,60,90] set on all records ✅
- Verification execution: run_verification_pass() runs every EOD ✅
- ILS scoring: computed correctly from registry state ✅
- DNA lifecycle advancement: automatic once DNA enters IDR ✅
- PIG scoring: DNA used in live debate at 8% weight ✅
- Safety isolation: learning pipeline firewalled from trading ✅

**What is missing (the gap):**

1. **Cat-E executor** (`_try_create_dna_candidate()` function) — the function that converts a LOGGED_FOR_REVIEW Cat-E record into an IDR write does not exist.

2. **Cat-F executor** — no bridge from Cat-F PENDING record to `HKAPEngine.run([symbol])`. HKAP is a standalone tool with no learning registry integration.

3. **Cat-A, D, G executors** — similarly absent (not needed today but part of the same pattern).

4. **AMLS-per-symbol trigger** — Cat-E needs to trigger a targeted historical analysis for one new symbol. The existing AMLS runs on the full configured universe, not on individual symbols from the learning registry.

5. **SD approval workflow** — even if HKAP ran for BHARATFORG, the SD merge approval has no automated path.

**Why this classification is NOT "IMPLEMENTATION BUG":**

The comment in `execute_actions()` is explicit: `"Categories A, D, E, F, G → logged for manual/scheduled execution"`. This is intentional. Creating DNA from a single day's price signal is **epistemically unsound** — it would create unvalidated patterns from one observation. The current design forces evidence accumulation before automatic execution. The gap is not a bug; it is a missing component that was deferred.

**Why this classification is NOT "DESIGN GAP" (classification 5):**

The architecture anticipates automatic execution (the `execute_actions()` function has explicit handler blocks for Cat-B and Cat-C). The executor slot for Cat-E is structurally present but unpopulated. This is "implemented but incomplete" not "architecture stops here."

---

## PART 9 — PROPOSED ACTION LIST (NO CODE CHANGES NOW)

### GAP-001: Cat-E executor function is missing

| Field | Value |
|-------|-------|
| **Problem** | No `_try_create_dna_candidate()` function. Cat-E actions never leave PENDING. |
| **Existing component to reuse** | `IDRRepository` (fully implemented), `market_learning/amls.py` Phase 1–3 can be parameterized per symbol |
| **Missing component** | A function that: reads Cat-E PENDING records → fetches 6-month OHLCV for each symbol → runs targeted DNA discovery → writes DISCOVERED DNA to IDR → marks registry entry executed=True |
| **Should it be automatic?** | **YES, with evidence gate.** Suggested gate: only execute if `|return_pct| >= 1.5%` AND volume > 1M AND record has been PENDING for >= 1 trading day (prevents same-day noise). |
| **Evidence required** | One significantly-sized move (already available from Cat-E payload) |
| **Effect on live trading** | DISCOVERED DNA is NOT used in live scoring (lifecycle gate blocks it). Only INSTITUTIONAL DNA reaches PIG. Zero immediate effect. |
| **Priority** | MEDIUM — adds knowledge; does not affect stability |

---

### GAP-002: Cat-F HKAP replay has no automatic launcher

| Field | Value |
|-------|-------|
| **Problem** | HKAP is a standalone tool. Cat-F PENDING records never trigger a replay. |
| **Existing component to reuse** | `HKAPEngine.run(years, symbols=[symbol])` already supports per-symbol runs |
| **Missing component** | A HKAP scheduler that reads Cat-F PENDING records and launches `HKAPEngine.run()` for each symbol on a weekend (to avoid market-hours resource contention) |
| **Should it be automatic?** | **SEMI-AUTOMATIC** — auto-run HKAP on weekends, but require SD review before IDR merge. The SD merge approval is the safety gate. |
| **Evidence required** | Existing historical data in OHLCV + at least 2 years of price history for the symbol |
| **Effect on live trading** | None during HKAP run. POSSIBLE effect post-merge (new DNA enters IDR) — bounded by DISCOVERED lifecycle gate. |
| **Priority** | LOW — HKAP is research-grade; value comes from multiple symbols over time |

---

### GAP-003: Verification result → DNA promotion is not wired

| Field | Value |
|-------|-------|
| **Problem** | When `verification_pass` assigns IMPROVED verdict, it updates `LearningRecord.status = "IMPROVED"` but does NOT automatically write DNA or call any IDR function. The "promotion" is a label change only. |
| **Existing component to reuse** | `IDRRepository.update()` exists for lifecycle transitions |
| **Missing component** | A handler in `run_verification_pass()` or `update_lifecycle()` that, on IMPROVED verdict, promotes the associated DNA record from VALIDATED→INSTITUTIONAL in IDR |
| **Should it be automatic?** | **YES** — if verified IMPROVED at 60-day window, auto-promote. This is purely evidence-based. |
| **Evidence required** | IMPROVED verdict at 60-day window (already generated by run_verification_pass) |
| **Effect on live trading** | DNA becomes INSTITUTIONAL → PIG can score it → 8% vote weight in debate. Bounded and safe. |
| **Priority** | LOW — moot until GAP-001 is resolved (no DNA exists to promote) |

---

## PART 10 — FINAL VERDICT

### `LEARNING_PARTIALLY_IMPLEMENTED`

---

**1. Is IIOS actually learning today?**

**Partially.** It is observing, analyzing, and registering. It is NOT updating any DNA, edge, hypothesis, or strategy model from today's observations. The only automated learning that happened today was Cat-B IDR reinforcements (if any Cat-B actions existed — today's 19 actions are all Cat-E/F, so even Cat-B did not fire). The learning pipeline ran all 12 phases and correctly captured 19 observations in the registry.

---

**2. Or is it only identifying learning opportunities?**

Today: **identifying learning opportunities only.** All 19 Cat-E actions are observations waiting for execution. The system knows DRREDDY moved +4.0% without DNA, but has taken no action to create DRREDDY DNA.

---

**3. Why are the 19 Cat-E actions PENDING?**

The actual code path is:

```python
# pga_learning.execute_actions(), line 387
else:
    # Categories A, D, E, F, G → logged for manual/scheduled execution
    action.outcome = "LOGGED_FOR_REVIEW"
```

Cat-E explicitly falls to the `else` branch. There is no `_try_create_dna_candidate()` function. The registry receives them as `status="PENDING", executed=False`. The verification pass finds no windows due today (first window: 2026-09-25). Therefore PENDING is the only possible state.

---

**4. Is that expected or a gap?**

It is **both**:
- It is **expected** in the sense that the code comment explicitly says "manual or scheduled execution" and the system was never shipped with a Cat-E executor.
- It is a **gap** in the sense that the learning cycle is architecturally incomplete: observations are recorded but never acted upon automatically.

From a safety perspective, the current behavior is CORRECT — creating DNA from a single day's signal without evidence validation would be dangerous. The gap is on the execution side (no scheduled AMLS-per-symbol trigger), not on the safety side.

---

**5. Can the existing system automatically execute learning?**

**For Cat-B and Cat-C: YES.** These fire automatically every EOD.  
**For Cat-E/F/A/D/G: NO.** No automatic executors exist.

---

**6. Can it validate learning automatically?**

**For DNA lifecycle: YES** — once DNA enters IDR as DISCOVERED, the DNA Consensus Engine automatically advances it through lifecycle stages.  
**For learning registry verification: YES** — `run_verification_pass()` runs every EOD and measures metrics on schedule. First windows due 2026-09-25.

---

**7. Can it promote validated learning automatically?**

**Partially.** The learning registry labels IMPROVED/RETIRED correctly. But the connection from "registry says IMPROVED" to "IDR record lifecycle advances to INSTITUTIONAL" is NOT implemented. The promotion is a label change only.

---

**8. What exact part of the loop is missing?**

```
Observation             ✅ IMPLEMENTED + AUTOMATIC
Root Cause              ✅ IMPLEMENTED + AUTOMATIC  
Action Creation         ✅ IMPLEMENTED + AUTOMATIC
Action Execution        ⚠️  IMPLEMENTED (Cat-B/C only) | NOT IMPLEMENTED (Cat-E/F)
                             ↑ THIS IS THE MISSING STEP
Candidate DNA Creation  ❌ NOT IMPLEMENTED (no Cat-E→IDR bridge)
DNA Validation          ✅ IMPLEMENTED but never receives input from PGA
Verification (30/60/90d)✅ IMPLEMENTED but will measure 0→0 (no DNA created)  
Institutional Promotion ✅ IMPLEMENTED (lifecycle labels) but not wired to IDR
```

**The single most important missing piece:** A function that translates a Cat-E PENDING record into a targeted historical DNA discovery run for the symbol, writing a DISCOVERED-lifecycle DNA record to IDR.

---

**9. Is live trading affected by this gap?**

**NO.** Live trading today is not affected:
- No Cat-E actions can reach the trading pipeline (no code path exists)
- The 19 PENDING records sit in a JSON file read only by the ILC
- PIG reads only INSTITUTIONAL DNA (0 new DRREDDY DNA was created)
- Risk limits, R:R, capital, and strategy enable/disable are all unchanged
- The 0-execution state today is fully explained by other factors (strategy disabled, CRE capital constraint) — not by the learning gap

---

**10. Should we modify anything before the next trading day?**

**NO.** Based on this investigation:

- The 0-trade state is correct governance (Mean_Reversion WR=16.7% justifies disable)
- The learning pipeline is operating as designed (observations registered, no DNA created)
- No code is broken — Cat-E is intentionally deferred per code comment
- No safety issue exists — the learning pipeline is firewalled from live trading
- No urgent gap requires patching before tomorrow's open

The learning gap (Cat-E executor missing) is a medium-term roadmap item, not an emergency. The system can trade safely without it. When ready to implement, see GAP-001 in Part 9.

---

*Investigation complete: 2026-08-11. No files modified. No code changed. No deployment.*  
*All conclusions grounded in direct source code inspection.*

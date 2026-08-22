# MARKET_OPPORTUNITY_COVERAGE_AUDIT
**Date:** 2026-08-10  
**Classification:** `PARTIALLY_COVERED`

---

## Final Answer

> **"Can IIOS automatically discover that a stock became a major winner/loser,
> determine whether it was in our watch/selection process, explain why it was
> or was not selected, and feed a genuine missed opportunity into the existing
> learning/verification cycle?"**

**YES — with one material gap.** IIOS automatically discovers major winners and
losers from the full NSE universe, classifies each through a 4-layer decision
chain, explains selection or rejection via 13 root-cause categories, and feeds
genuine misses into the 30/60/90-day learning/verification cycle. The gap is
**depth of coverage**: the root-cause analysis is limited to the top 5 movers
(PGA) or top 20 movers (ILC). Stocks ranked 21–500 by move size have their
prices fetched but receive no root-cause decomposition if they are not in the
top band.

---

## 1. Modules That Provide This Capability

| Module | Location | Role |
|--------|----------|------|
| **PGA** (Predictive Gap Analysis) | `predictive_gap/` | Daily top-5 deep analysis; 13 root causes; 7 learning categories |
| **ILC** (Institutional Learning Cycle) | `institutional_learning/` | Daily top-20 deep analysis; full universe classification; 12 reports; 30/60/90-day verification |
| **ilc_market_audit** | `institutional_learning/ilc_market_audit.py` | Classifies each winner/loser against universe (INSIDE/OUTSIDE_*) |
| **GVA** (Growth Validation Audit) | `growth_validator/` | System-wide platform health (not per-symbol) |
| **DTA** (Decision Traceability Audit) | `decision_tracer/` | Manual per-symbol deep trace; answers 10 audit questions |
| **OIOS** | `oios/` | Captures market leaders daily; computes winner-vs-control differentials |
| **15:35 EOD pipeline** | `orchestrator/master_orchestrator.py` → `run_eod_learning()` → `_do_eod_learning()` | Triggers PGA + ILC + GVA automatically |

---

## 2. Execution Chain

```
15:35 IST
└── orchestrator.run_eod_learning()                       [master_orchestrator.py]
    └── task_queue.submit("LearningEngine", _do_eod_learning)
        ├── Layer 10: LearningEngine.learn(closed_trades)  [learning trades only]
        ├── Layer 11: StrategyPerformanceTracker           [win rates]
        └── Layer 13: [implicitly] PGA + ILC via run_pga / run_ilc

16:45 IST
└── orchestrator._run_post_market_scan()
    ├── Phase D scanner → daily_candidates.json
    ├── OIOS ohlcv_daily refresh
    ├── OIOS outcome_tracker (forward returns)
    ├── OIOS market_leaders_daily (top gainers captured)
    ├── OIOS feature_extractor
    ├── OIOS control_population
    ├── OIOS differential_engine
    └── OIOS Layer 1A + 1B signal scan
```

**Note on PGA/ILC wiring:** `_do_eod_learning()` invokes
`predictive_gap.pga_runner.run_pga()` and
`institutional_learning.ilc_runner.run_ilc()` as part of the 15:35 slot.
Both complete before the TaskQueue worker releases.

---

## 3. Per-Question Coverage Map

### Questions 1–4 (per winner/loser)

| Sub-question | Answered automatically? | How | Gap |
|---|---|---|---|
| Was it in the IIOS eligible universe? | ✅ YES | `ilc_market_audit.py` → INSIDE / OUTSIDE_BY_DESIGN / OUTSIDE_UNEXPECTED / OUTSIDE_UNIVERSE_RULES | None |
| Was it in the active watch/scan list? | ⚠️ PARTIAL | `ct_events` → `equity_opportunity_found` events show which symbols had signals generated; stocks scanned but below threshold leave no event | Cannot distinguish "scanned but scored below threshold" from "never processed" |
| Was it actually scanned? | ⚠️ PARTIAL | Same as above — "scanned_today" = had an opportunity event, not "was in the scan batch" | Same gap |
| Was market intelligence available? | ❌ NO | Not per-symbol. MI (regime, VIX, sector) is global, not per-symbol | Not tracked per-symbol |
| Was a PMCI signal generated? | ⚠️ PARTIAL | Inferred: if symbol is in `ct_events.equity_opportunity_found`, a signal was generated | PMCI state is not stored per-symbol for non-actioned stocks |
| Was a CDS/strategy signal generated? | ⚠️ PARTIAL | `ct_decisions.strategy` field gives the strategy for actioned stocks | Missing for stocks that reached strategy_lab but were filtered there |
| Was DNA matched? | ⚠️ PARTIAL | `institutional_dna.db` → `consensus_dna` count per symbol (used in PGA analysis) | Count of existing DNA ≠ "was DNA matched this cycle" |
| Was IKN/knowledge evidence available? | ❌ NO | Not queried during PGA/ILC analysis | PGA does not query IKN per symbol |
| Was a BUY or SHORT candidate generated? | ✅ YES | `ct_events.equity_opportunity_found` with direction field | None |
| Was the candidate approved? | ✅ YES | `ct_decisions` with `decision='APPROVED'` | None |
| Was it rejected? + rejection reason | ✅ YES | `ct_decisions` with `decision='REJECTED'` + `reasoning` field | None |
| Was it blocked by risk/portfolio/capital? | ✅ YES (partial) | `rejection_reason` includes 'HEAT', 'PORTFOLIO', 'RR', 'POSITION_LIMIT' | Only covers DecisionEngine rejections; StrategyLab and Simulation drops are NOT in ct_decisions |
| Was it outside the universe? | ✅ YES | `ilc_market_audit.py` OUTSIDE_* statuses | None |
| Was it simply not predictable? | ✅ YES | `pga_analyzer.py` → `was_predictable=NOT_PREDICTABLE`; `pga_root_cause.py` → ExternalEvent root cause | None |

### Question 3 — Why a major winner was NOT selected

✅ **Covered.** `pga_root_cause._classify_root_cause()` assigns one of 13 root
causes from a decision tree:

```
Stock not in universe                 → Scanner (improve: E if DNA=0, A otherwise)
In universe, not scanned, DNA=0       → DNA + PMCI (improve: E — create DNA)
In universe, not scanned, DNA>0       → PMCI threshold (improve: A or B)
Scanned, decision rejected, HEAT      → PortfolioConstraint (not improvable — intended)
Scanned, decision rejected, RR        → RiskFilter (improve: A — calibrate)
Scanned, rejected, conf < threshold   → DNA (cat E) or Knowledge (cat B)
Approved, wrong direction             → DNA directional bias (cat B) or WrongThreshold (cat F)
Large move, no evidence               → ExternalEvent (not improvable)
```

### Question 4 — Why a major loser was NOT selected

✅ **Covered via MISS_TYPE taxonomy:**

| User's label | IIOS classification |
|---|---|
| A. Correctly avoided the loss | `MISS_TYPE=CORRECT` for SHORT or `MISS_TYPE=CORRECT` for rejected LONG |
| B. Missed a profitable SHORT | `MISS_TYPE=MISSED_LOSER` (stock fell but IIOS had no SHORT signal) |
| C. Generated wrong BUY direction | `MISS_TYPE=WRONG_DIRECTION` + `decision.approved=True` + `direction=BUY` |
| D. Never scanned the stock | `was_predicted=NO` + `not in scanned_today` + `root_cause=Scanner` |
| E. Lacked knowledge/DNA | `root_cause=DNA` (cat E) or `root_cause=Knowledge` (cat B) |
| F. Rejected by risk/portfolio | `root_cause=PortfolioConstraint` or `RiskFilter` |
| G. Another documented reason | `root_cause=ExternalEvent`, `WrongThreshold`, `MissingHistoricalPattern`, etc. |

---

## 4. Module Coverage per Question 5

| System | What it contributes |
|--------|---------------------|
| **PGA** | Top-5 gainers/losers: was_predicted, was_predictable, root cause (13 categories), learning actions (A–G). Automatic at 15:35. |
| **ILC** | Top-20 gainers/losers: same PGA analysis with top_n=20. Phase 1 classifies all 40 into universe status. 12 reports. 30/60/90-day verification. Automatic at 15:35. |
| **ilc_market_audit** | Every top winner/loser classified: INSIDE / OUTSIDE_BY_DESIGN / OUTSIDE_UNEXPECTED / OUTSIDE_UNIVERSE_RULES. Provides `universe_reason` string. |
| **missed-opportunity taxonomy** | `pga_analyzer.py` constants: MISSED_WINNER, MISSED_LOSER, CORRECT, WRONG_DIRECTION, NO_DATA. `pga_root_cause.py`: 13 root causes. `LEARNING_CATEGORIES`: A–G with EIG weights. |
| **decision_tracer (DTA)** | Manual per-symbol: 10 audit questions including PMCI, CDS, IKN, DNA matches, hypotheses, counterfactual. NOT automatic — CLI only. |
| **GVA** | Aggregate platform health score (Knowledge, Learning, DNA, Scientific, Platform). Not per-symbol. |
| **OIOS / leader_capture** | Captures top gainers daily in `market_leaders_daily`. Computes `outcome_gap_*` vs. controls. Not feeding PGA/ILC directly — parallel research track. |
| **existing market data collectors** | `pga_collector._fetch_price_data()` uses yfinance on the full nifty500 universe to find the day's winners/losers. |
| **existing post-market pipeline** | The 16:45 slot runs OIOS refresh; the 15:35 slot runs PGA + ILC + GVA. Both are wired to the scheduler. |

---

## 5. Automatic Execution at 15:35 IST

✅ **Yes — verified in `orchestrator/master_orchestrator.py`.**

```python
# config.py → SCHEDULE dict (verified)
"eod_learning": 1535,   # fires at 15:35 IST every weekday

# master_orchestrator.py → run_eod_learning()
# → submits _do_eod_learning to LearningEngine worker
# → _do_eod_learning calls run_pga() and run_ilc()
```

The pipeline:
- Skips on NSE holidays (`is_nse_holiday()` guard)
- Runs via TaskQueue background worker (non-blocking)
- Outputs to `data/pga/YYYY-MM-DD/` and `data/ilc/YYYY-MM-DD/`
- GVA writes to `data/gva/YYYY-MM-DD/`

---

## 6. Persistence and Learning System Feed

✅ **Verified.**

| Output | Location | Lifetime |
|--------|----------|---------|
| PGA reports (9 files) | `data/pga/YYYY-MM-DD/` | Permanent |
| ILC reports (12 files) | `data/ilc/YYYY-MM-DD/` | Permanent |
| Learning registry | `data/ilc/learning_registry.json` | Cumulative append |
| Knowledge lifecycle | `data/ilc/knowledge_lifecycle.json` | Cumulative append |
| GVA reports (6 files) | `data/gva/YYYY-MM-DD/` | Permanent |
| OIOS differentials | `oios/db/market_behavior.db` | Permanent (SQLite) |

The `learning_registry.json` is the persistent store for all A–G learning
actions created by PGA/ILC. Each record has `action_id`, `category`, `symbol`,
`action_type`, `target_system`, `scheduled_at`, and `verified_at`.

---

## 7. Learning Actions and 30/60/90-Day Verification

✅ **Verified.**

```python
# institutional_learning/ilc_verification.py
VERIFICATION_WINDOWS = [30, 60, 90]   # trading days
CALENDAR_DAYS_MAP    = {30: 45, 60: 90, 90: 135}
```

**Flow:**
1. PGA root cause assigns improvement category (A–G)
2. `pga_learning.plan_actions()` creates `LearningAction` objects
3. ILC Phase 7 executes B and C actions immediately (auto-execute):
   - Cat B: `update_idr_observation()` writes to IDR knowledge store
   - Cat C: `generate_hypothesis()` registers in `ars_hypothesis_registry.json`
4. ILC Phase 8: `ilc_verification.register_learning_actions()` persists to `learning_registry.json`
5. ILC Phase 8: `ilc_verification.run_verification_pass()` checks 30/60/90-day windows:
   - Compares metric at registration vs. today
   - Assigns verdict: `IMPROVED` / `NO_CHANGE` / `DECLINED`
6. ILC Phase 9: computes ROI per learning action
7. ILC Phase 11: computes ILS (Institutional Learning Score) 0–100 weighting
   learning_efficiency, knowledge_efficiency, prediction_improvement, etc.

---

## 8. The 4-Way Opportunity Distinction

⚠️ **Partially implemented under different names.**

| User's term | IIOS equivalent | Implementation |
|---|---|---|
| MARKET_OPPORTUNITY | Stock moved ≥ `min_move_pct` (1.0%) | `pga_analyzer.py` — any stock with `abs(daily_return_pct) >= min_move_pct` |
| PREDICTABLE_OPPORTUNITY | `was_predictable = PREDICTABLE` or `PARTIALLY_PREDICTABLE` | `pga_analyzer._classify_was_predictable()` — requires `dna_coverage >= dna_coverage_min` AND available historical evidence |
| ACTIONABLE_OPPORTUNITY | `was_predicted = YES` + `decision.approved = True` + correct direction | Derived from `ct_decisions` + move direction match |
| VALIDLY_REJECTED_OPPORTUNITY | `root_cause = PortfolioConstraint` or `RiskFilter` + `can_improve = False` | `pga_root_cause.py` — explicitly marks `can_improve=False` for portfolio heat and RR rejections |

The four categories exist logically but are not surfaced under these exact label
names in any report. The ILC/PGA reports use the MISS_TYPE + root_cause taxonomy
which maps to these four but requires manual cross-reference.

**No code change needed** — the existing taxonomy is functionally equivalent and
more granular.

---

## 9. Full Universe vs. Top-Band Coverage

⚠️ **Partial — this is the primary material gap.**

| Layer | Coverage |
|-------|---------|
| Price data fetch | ✅ FULL — `pga_collector._fetch_price_data()` loads all symbols from `nifty500_universe.json` (up to 500) via yfinance |
| Gainer/loser sorting | ✅ FULL — `all_moves` dict contains every symbol with price data |
| Universe status classification | ✅ FULL — `ilc_market_audit` classifies every top-20 symbol |
| Root-cause analysis | ❌ TOP-BAND ONLY — PGA analyzes top 5; ILC analyzes top 20 |
| Learning actions generated | ❌ TOP-BAND ONLY — only for stocks that enter the top-N analysis |
| OIOS leader capture | ⚠️ PARTIAL — captures top gainers/losers in `market_leaders_daily` without root-cause decomposition |

**A stock ranked 21st by move size (e.g. +4.2% gainer) does not receive
root-cause analysis or learning action generation, even though its price
was fetched and it was classified as a market opportunity.**

The OIOS pipeline does capture it in `market_leaders_daily` and later computes
`outcome_gap_*` vs. a control cohort — but this feeds the research track (Phase F
weekly differential analysis), not the daily learning loop.

---

## 10. Specific Gaps Identified

| # | Gap | Severity | Existing workaround |
|---|-----|----------|---------------------|
| G1 | Root-cause analysis limited to top 5/20 movers | MEDIUM | OIOS captures all leaders; DTA can manually analyze any symbol |
| G2 | "Scanned but scored below threshold" indistinguishable from "not in scan batch" | MEDIUM | Log-level `[StrategyLabReject]` and `[PipelineAttrition]` entries exist but are not fed into PGA/ILC |
| G3 | IKN/knowledge evidence not queried per-symbol in PGA/ILC | LOW | DTA (manual) queries IKN for any symbol |
| G4 | PMCI state not stored per-symbol for non-actioned stocks | LOW | Inferred from absence of ct_events record |
| G5 | 4-way taxonomy (MARKET/PREDICTABLE/ACTIONABLE/VALIDLY_REJECTED) not surfaced as explicit labels in reports | LOW | Logically derivable from MISS_TYPE + root_cause + can_improve |
| G6 | Market intelligence (regime, VIX, sector) not tested per-symbol for missed movers | LOW | MI is global; per-symbol MI is logged in [StrategyLabReject] |

---

## 11. Whether to Implement Anything

**No new system is needed.** The existing gaps are precision gaps, not structural
gaps. The recommended minimum improvements, in order of value:

### G1 — Extend top-band limit (recommended, small change)

PGA is configured at `top_n=5`; ILC at `top_n=20`. Raising ILC to `top_n=50`
would capture any stock ranked 21–50 by move. This is a one-line config change
in `institutional_learning/ilc_config.py`:

```python
ILC_TOP_N = 50   # was 20
```

No architectural change needed.

### G2 — Feed [StrategyLabReject] into PGA collector (medium, non-destructive)

`[StrategyLabReject]` log lines written by `master_orchestrator._run_strategy_lab()`
contain `symbol`, `strategy`, `rejection_reason`, `backtest_score`, `regime_match`.
If these were written to a daily staging file (e.g. `data/strategy_lab_rejects.jsonl`),
`pga_collector.py` could import them so `scanned_today` distinguishes:
- In scan batch → `scanned_today_raw`
- Generated a signal → `scanned_today_signal`
- Rejected at strategy_lab → `rejected_at_strategy_lab`

This is additive — no existing logic changes.

### G3–G6 — Low priority, DTA covers manually

For deep per-symbol analysis, `python -m decision_tracer.dta_runner --symbol X`
answers IKN, PMCI, CDS, DNA, and all 10 audit questions. This is the correct
tool for individual investigation.

---

## 12. Summary Table — Questions 1–10

| Question | Status | Primary module |
|----------|--------|----------------|
| 1. Identify day's major winners/losers | ✅ COVERED | `pga_collector._fetch_price_data()` on full universe |
| 2. 13-point per-stock determination | ✅ MOSTLY COVERED | `pga_analyzer.py` + `pga_root_cause.py` + `ilc_market_audit.py` |
| 3. Why major winner NOT selected | ✅ COVERED | `pga_root_cause._classify_root_cause()` — 13 categories |
| 4. Why major loser NOT selected (A–G) | ✅ COVERED | MISS_TYPE + root_cause taxonomy |
| 5. Provided by existing modules | ✅ YES | PGA, ILC, ilc_market_audit, DTA, GVA, OIOS |
| 6. 15:35 pipeline executes automatically | ✅ YES | `orchestrator.run_eod_learning()` via scheduler |
| 7. Results persisted and learning-accessible | ✅ YES | `learning_registry.json`, `knowledge_lifecycle.json`, `data/pga/`, `data/ilc/` |
| 8. Genuine miss → learning action → 30/60/90-day verification | ✅ YES | `ilc_verification.register_learning_actions()` + `run_verification_pass()` |
| 9. 4-way distinction (MARKET/PREDICTABLE/ACTIONABLE/VALIDLY_REJECTED) | ⚠️ PARTIAL | Logically present in MISS_TYPE + root_cause but not surfaced as those exact labels |
| 10. Full eligible universe covered | ⚠️ PARTIAL | Prices fetched for 500 symbols; root-cause analysis for top 5 (PGA) or top 20 (ILC) only |

---

**Classification: `PARTIALLY_COVERED`**

The system is structurally complete and operationally sound. The two partial
gaps (top-band limit and scanned-vs-scored distinction) do not prevent learning
from occurring — they only limit the depth of automatic root-cause analysis
beyond the 20th mover each day.

# PHASE_D_RECOMMENDATION_001 — Symbol Follow-Through Filter (Shadow Mode)

**Status:** ACTIVE — SHADOW MODE ONLY
**Created:** 2026-06-19
**Evidence basis:** OPS05E_SYMBOL_VELOCITY_PROFILE, OPS05F_SYMBOL_SELECTION_COUNTERFACTUAL
**Files:**
- [`phase_d_sft_recommendation.py`](phase_d_sft_recommendation.py) — implementation
- [`tests/test_phase_d_sft.py`](tests/test_phase_d_sft.py) — verification suite (49 tests)
- `data/phase_d_sft.db` — isolated SQLite store (auto-created on first run)

---

## 1. Recommendation Summary

### The Problem (from forensic evidence)
In 38 closed trades (Apr–May 2026), 19 trades in low-velocity symbols (TATASTEEL,
BHARTIARTL, ULTRACEMCO, AXISBANK, TATAMOTORS) produced **zero wins** and accounted for
100% of the net loss. The top-50% follow-through symbols produced a profitable period
in isolation (WR 52.6%, PF 1.113, +₹70,805).

### The Recommendation
Maintain live Symbol Follow-Through (SFT) scores as trades close. Tag each new trade
candidate with its symbol's SFT class. Record advisory recommendations and counterfactual
outcomes. Do NOT gate, block, or modify any trade.

### Shadow Mode Contract
> **This module generates recommendations only.**
> It does NOT block, modify, re-score, or delay any trade.
> It does NOT write to any system table used by the live trading path.
> It is a passive observer and advisor only.

---

## 2. Architecture

```
[Closed Trade Event]
        │
        ▼
  SFTTracker.ingest_closed_trade()   ← sole write path for metrics
        │
        ▼
  symbol_follow_through_metrics      ← isolated SQLite table (phase_d_sft.db)
  (running aggregates per symbol)
        │
        ├──► compute_symbol_follow_through()   ← pure function, testable
        │              │
        │              └──► SFT score 0-100  →  classify_sft()  →  SFTClass
        │
[New Trade Candidate]
        │
        ▼
  SFTTracker.get_recommendation()    ← read-only from metrics
        │
        ▼
  generate_sft_recommendation()
        │
        ▼
  pending_adjustments                ← shadow-only store (phase_d_sft.db)
  (advisory record, never read by execution)
        │
[Trade Closes]
        │
        ▼
  SFTTracker.record_counterfactual() ← compares actual outcome to recommendation
        │
        ▼
  counterfactual_tracking            ← HELPED / HURT / NO_EFFECT per trade
        │
        ▼
  SFTTracker.generate_shadow_report() → SFT_SHADOW_REPORT.md (periodic)
```

---

## 3. Data Flow

### Step A — Trade closes (ingest trigger)
Caller (MasterOrchestrator EOD hook, or monitoring script) calls:
```python
from phase_d_sft_recommendation import get_sft_tracker

tracker = get_sft_tracker()
tracker.ingest_closed_trade(
    symbol        = "TATASTEEL",
    trade_pnl     = -47_000.0,
    entry_price   = 145.5,
    stop_loss     = 143.2,
    mfe_r         = 0.241,    # from paper_trades or trade monitor
    mae_r         = 0.661,
    reached_025r  = True,
    reached_050r  = False,
    reached_100r  = False,
)
```
This updates `symbol_follow_through_metrics` for TATASTEEL and recomputes its SFT score.

### Step B — Before logging a new candidate (advisory query)
```python
rec = tracker.get_recommendation("COALINDIA")
# rec.recommendation_type  →  "PREFER_HIGH_SFT" | "CAUTION_MEDIUM_SFT" |
#                              "AVOID_LOW_SFT"  | "INSUFFICIENT_DATA"
# rec.sft_score            →  float 0-100
# rec.sft_class            →  "HIGH_SFT" | "MEDIUM_SFT" | "LOW_SFT" | "INSUFFICIENT_DATA"
# rec.confidence           →  float 0-1

# SHADOW ONLY: log to dashboard, Telegram, or monitoring — do NOT gate trade
```

### Step C — After trade closes (counterfactual)
```python
cf = tracker.record_counterfactual(
    symbol    = "TATASTEEL",
    trade_pnl = -47_000.0,
    rec_type  = rec.recommendation_type,
    sft_class = rec.sft_class,
)
# cf.counterfactual_outcome  →  "HELPED" | "HURT" | "NO_EFFECT"
```

---

## 4. SFT Score Formula

```
SFT = (WR_pct × 0.40) + (min(avg_mfe, 3.0) / 3.0 × 30) + (pct_05R × 0.30)
```

| Component | Weight | Input | Rationale |
|---|---|---|---|
| C1: Win Rate | 40% | `win_count / trade_count × 100` | Primary outcome |
| C2: MFE depth | 30% | `min(avg_mfe_r, 3.0) / 3.0 × 100` | How far price actually moves |
| C3: Reach 0.5R | 30% | `reach_050r_count / trade_count × 100` | Setup-to-execution conversion |

**Cap:** MFE is capped at 3.0R to prevent outlier blowout trades from dominating the score.
**Score range:** 0.0 – 100.0 (clamped).
**Minimum trades:** 3 closed trades required before a symbol receives a non-INSUFFICIENT_DATA class.

### Calibration (forensic dataset, 38 trades)

| Symbol | Score | WR | Avg MFE | %→0.5R | Class |
|---|---|---|---|---|---|
| HINDALCO | 94.3 | 100% | 2.427R | 100% | HIGH_SFT |
| BANKBARODA | 83.4 | 100% | 1.335R | 100% | HIGH_SFT |
| COALINDIA | 61.6 | 50% | 1.158R | 100% | MEDIUM_SFT |
| NTPC | 53.2 | 67% | 0.647R | 67% | MEDIUM_SFT |
| TATASTEEL | 8.4 | 0% | 0.241R | 20% | LOW_SFT |
| BHARTIARTL | 0.8 | 0% | 0.080R | 0% | LOW_SFT |

---

## 5. Classification Bands

| Class | Score Threshold | Default | Configurable? |
|---|---|---|---|
| `HIGH_SFT` | score ≥ 70 | `SFT_HIGH_THRESHOLD = 70.0` | ✅ Module constant |
| `MEDIUM_SFT` | score ≥ 40 | `SFT_MEDIUM_THRESHOLD = 40.0` | ✅ Module constant |
| `LOW_SFT` | score < 40 | — | implicit |
| `INSUFFICIENT_DATA` | trade_count < 3 | `MIN_TRADES_FOR_SCORE = 3` | ✅ Module constant |

To change bands without code modification, edit the three module-level constants
at the top of `phase_d_sft_recommendation.py`.

---

## 6. Recommendation Logic

| SFT Class | Recommendation Type | Confidence |
|---|---|---|
| `HIGH_SFT` | `PREFER_HIGH_SFT` | `sft_score / 100` |
| `MEDIUM_SFT` | `CAUTION_MEDIUM_SFT` | `sft_score / 100` |
| `LOW_SFT` | `AVOID_LOW_SFT` | `(100 - sft_score) / 100` |
| `INSUFFICIENT_DATA` | `INSUFFICIENT_DATA` | `0.0` |

The confidence for `AVOID_LOW_SFT` is intentionally inverted — a score of 5.0 produces
avoidance confidence 0.95 (high certainty to avoid). A score of 35.0 produces avoidance
confidence 0.65 (less certain — not far below the medium threshold).

**Advisory intent only:**
- `PREFER_HIGH_SFT` → "This symbol has historically converted setups into profit"
- `CAUTION_MEDIUM_SFT` → "This symbol is borderline — mixed history"
- `AVOID_LOW_SFT` → "This symbol has not converted setups into profit in this period"
- `INSUFFICIENT_DATA` → "Not enough history to classify"

---

## 7. Database Schema

All tables reside exclusively in `data/phase_d_sft.db`. No other database is accessed.

### `symbol_follow_through_metrics`
One row per traded symbol, updated in-place after each closed trade.

| Column | Type | Description |
|---|---|---|
| `symbol` | TEXT (PK) | Ticker symbol |
| `trade_count` | INTEGER | Total closed trades |
| `win_count` | INTEGER | Winning trades (pnl > 0) |
| `loss_count` | INTEGER | Losing trades (pnl < 0) |
| `win_rate` | REAL | win_count / trade_count × 100 |
| `avg_mfe` | REAL | Running average MFE in R-multiples |
| `avg_mae` | REAL | Running average MAE in R-multiples |
| `pct_reach_025r` | REAL | % trades reaching +0.25R |
| `pct_reach_050r` | REAL | % trades reaching +0.50R |
| `pct_reach_100r` | REAL | % trades reaching +1.00R |
| `follow_through_score` | REAL | SFT score 0–100 |
| `sft_class` | TEXT | HIGH_SFT / MEDIUM_SFT / LOW_SFT / INSUFFICIENT_DATA |
| `last_updated` | TEXT | ISO-8601 UTC timestamp |

### `pending_adjustments`
Advisory recommendations (shadow store — never read by execution layer).

| Column | Type | Description |
|---|---|---|
| `recommendation_id` | TEXT (PK) | UUID |
| `symbol` | TEXT | Ticker symbol |
| `recommendation_type` | TEXT | PREFER_HIGH_SFT / CAUTION / AVOID / INSUFFICIENT_DATA |
| `sft_score` | REAL | Score at time of recommendation |
| `sft_class` | TEXT | Classification at time of recommendation |
| `confidence` | REAL | Confidence 0–1 |
| `supporting_metrics` | TEXT | JSON snapshot of SFTMetrics |
| `created_at` | TEXT | ISO-8601 UTC timestamp |

### `counterfactual_tracking`
Post-trade outcome vs recommendation comparison.

| Column | Type | Description |
|---|---|---|
| `record_id` | TEXT (PK) | UUID |
| `symbol` | TEXT | Ticker symbol |
| `trade_pnl` | REAL | Actual realised PnL |
| `trade_win` | INTEGER | 1 if win, 0 if loss |
| `sft_class_at_entry` | TEXT | Classification when trade was entered |
| `recommendation_type` | TEXT | Recommendation in effect at entry |
| `counterfactual_outcome` | TEXT | HELPED / HURT / NO_EFFECT |
| `recorded_at` | TEXT | ISO-8601 UTC timestamp |

### `shadow_mode_log`
Internal audit trail — every significant action (INIT, INGEST, RECOMMEND, COUNTERFACTUAL, REPORT).

---

## 8. Counterfactual Tracking Rules

| Recommendation | Outcome | Counterfactual |
|---|---|---|
| `AVOID_LOW_SFT` | Trade lost | **HELPED** — recommendation would have avoided the loss |
| `AVOID_LOW_SFT` | Trade won | **HURT** — recommendation would have missed a win |
| `PREFER_HIGH_SFT` | Trade won | **HELPED** — recommendation correctly identified winner |
| `PREFER_HIGH_SFT` | Trade lost | **NO_EFFECT** — preferred but still lost |
| `CAUTION_MEDIUM_SFT` | Any | **NO_EFFECT** — neutral advisory, not directional |
| `INSUFFICIENT_DATA` | Any | **NO_EFFECT** — no actionable recommendation |

**Net counterfactual benefit = Σ(HELPED PnL recovered) − Σ(HURT PnL missed)**

If this value is consistently positive across 30+ observations, it supports Phase D
escalation from shadow to active gating.

---

## 9. Shadow Guarantees

The following is verified by the test suite and enforced by architecture:

| Guarantee | Verification method |
|---|---|
| No imports from execution_engine, risk_control, decision_ai, opportunity_engine | `test_module_does_not_import_protected_layers` (AST parse) |
| Only writes to its own `phase_d_sft.db` | `test_tracker_db_has_only_sft_tables` |
| Does not open `paper_trades.csv` | `test_paper_trades_csv_not_opened` (mock) |
| `get_recommendation()` does not mutate metrics | `test_get_recommendation_does_not_modify_metrics` |
| `order_manager.py` does not reference this module | `test_pending_adjustments_table_not_read_by_execution` |
| `SFTRecommendation` has no execute/submit/apply/block method | `test_recommendation_has_no_execute_method` |
| `SFTRecommendation` is a pure data container | `test_recommendation_is_data_only` |

---

## 10. Validation Plan

### Phase D-α (Current): Shadow observation (0–30 trades)
- Record SFT recommendations for every closed trade
- Track counterfactual outcomes
- Do NOT act on recommendations
- Monitor: % HELPED vs % HURT among LOW_SFT-tagged trades

**Escalation trigger for Phase D-β:** After 30 closed trades:
- If `pct(HELPED) ≥ 70%` among AVOID_LOW_SFT recommendations
- AND net counterfactual benefit is positive (HELPED PnL > HURT PnL)
- → Eligible to discuss Phase D-β (active advisory flag in dashboard)

### Phase D-β (Future, requires explicit approval): Active advisory
- Surface SFT classification in Telegram bot on every trade open event
- Example: `🟡 TATASTEEL — LOW_SFT (score 8.4) — historical WR 0%, 10 trades`
- Still no execution gating

### Phase D-γ (Future, requires explicit approval): Confidence-weighted position sizing
- Scenario D from OPS05F: 1.25× for HIGH_SFT, 0.75× for LOW_SFT
- Requires: 50+ shadow observations with ≥70% HELPED rate

### Phase D-Ω (Future, explicit approval + governance review): Symbol gating
- Block LOW_SFT symbols from new entries (Scenario C from OPS05F)
- Requires: 100+ shadow observations, ≥80% HELPED rate, net_cf_benefit > ₹2L

---

## 11. Integration Hint (non-mandatory, additive only)

When the MasterOrchestrator runs its EOD learning cycle (`_do_eod_learning`), it may
optionally call the SFT tracker. This is additive — it does not modify the existing
learning cycle behaviour.

```python
# In orchestrator/master_orchestrator.py, inside _do_eod_learning() — optional addition:
# (This is illustrative. Do not add without explicit instruction.)

# from phase_d_sft_recommendation import get_sft_tracker
# tracker = get_sft_tracker()
# for trade in today_closed_trades:
#     tracker.ingest_closed_trade(
#         symbol=trade.symbol, trade_pnl=trade.pnl,
#         entry_price=trade.entry_price, stop_loss=trade.stop_loss,
#         mfe_r=trade.mfe_r, mae_r=trade.mae_r,
#         reached_025r=trade.reached_025r,
#         reached_050r=trade.reached_050r,
#         reached_100r=trade.reached_100r,
#     )
```

The hint is documented here — it must NOT be applied until explicitly requested.

---

## 12. Test Suite Summary

**File:** [`tests/test_phase_d_sft.py`](tests/test_phase_d_sft.py)
**Tests:** 49 | **Pass:** 49 | **Fail:** 0

| Suite | Tests | Coverage |
|---|---|---|
| `TestScoreCalculation` | 10 | Formula accuracy, calibration vs forensic data, edge cases |
| `TestClassification` | 8 | All band boundaries, INSUFFICIENT_DATA transitions |
| `TestRecommendationGeneration` | 7 | Type mapping, confidence range, uniqueness |
| `TestShadowIsolation` | 5 | No protected imports (AST), no paper_trades access, own-DB-only |
| `TestNoExecutionInfluence` | 3 | No execute/submit/block method, order_manager isolation |
| `TestCounterfactualTracking` | 8 | All HELPED/HURT/NO_EFFECT paths, persistence, aggregation |
| `TestIntegration` | 8 | Full TATASTEEL/HINDALCO workflows, accumulation, thread safety, invalid inputs |

Run: `python -m pytest tests/test_phase_d_sft.py -v`

---

## 13. Deliverables

| Deliverable | Status |
|---|---|
| `phase_d_sft_recommendation.py` | ✅ Created — 840 lines, no protected imports |
| `tests/test_phase_d_sft.py` | ✅ Created — 49 tests, all pass |
| `data/phase_d_sft.db` | ✅ Auto-created on first `SFTTracker()` instantiation |
| `SFT_SHADOW_REPORT.md` | Generated on demand via `tracker.generate_shadow_report(path)` |
| `PHASE_D_RECOMMENDATION_001.md` | ✅ This document |

---

*Filtering is NOT enabled. No trades are blocked. No execution is influenced.*
*This is a shadow recommendation system only.*

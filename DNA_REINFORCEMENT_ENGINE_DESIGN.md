# DNA Reinforcement Engine — Design Document

**Task:** O-002  
**Status:** COMPLETE  
**Tests:** 200/200 PASS  

---

## 1. Purpose

The DNA Reinforcement Engine (DRE) is the **third learning source** of the
Institutional Intelligence Operating System (IIOS).

| Learning source | What it learns from |
|---|---|
| MLS Phase 3–4 (Discovery + Consensus) | Statistical observation of market data |
| AMLS (Autonomous Market Learning Scheduler) | Daily DNA pipeline execution |
| **DRE (DNA Reinforcement Engine)** | **Verified closed-trade outcomes** |

DRE continuously improves institutional DNA using real trading evidence.  
It never creates DNA.  It never discovers DNA.  
It only **reinforces** existing institutional knowledge — strengthening or
weakening DNA that was used in real decisions.

---

## 2. Architecture Contracts

DRE **reuses only**:

| Component | Usage |
|---|---|
| `IDRRepository` | Read active DNA, write confidence updates |
| `PMCIResult` | Identify which DNA features contributed to the trade |
| `CAPMCIResult` | CA-PMCI score enrichment in evidence |
| `ContextualDNAScore` | CDS score enrichment in evidence |
| `OrderRecord` / trade dict | Closed trade outcome (R-multiple, PnL, direction) |

DRE **never calls**:

- `DNADiscoveryEngine`
- `DNAConsensusEngine`
- `PMCIEngine` / `CAPMCIEngine` / `CDSEngine`
- `MarketObserver` / `PopulationClassifier`
- Any strategy or risk management component

---

## 3. Files

```
market_learning/
  dre_models.py      — Pure data models (no logic, all JSON-serialisable)
  dre_config.py      — DREConfig (all thresholds in one place)
  dre_engine.py      — DNAReinforcementEngine (full implementation)

test_dre.py          — 200 tests (T001–T200)
DNA_REINFORCEMENT_ENGINE_DESIGN.md
DNA_REINFORCEMENT_API.md
DNA_REINFORCEMENT_TEST_REPORT.md

data/mls/dre/
  history.json       — persistent reinforcement audit trail (auto-created)
```

---

## 4. Reinforcement Algorithm

### 4.1 Inputs

```
trade           — closed OrderRecord or dict
pmci_result     — PMCIResult at decision time
ca_pmci_result  — CAPMCIResult (optional)
cds_scores      — Dict[dna_id, ContextualDNAScore] (optional)
```

### 4.2 Outcome Quality

R-multiple alone does not determine quality.  Both magnitude and win/loss matter:

| R-multiple | Won? | OutcomeQuality |
|---|---|---|
| R ≥ 2.0 | Yes | EXCELLENT |
| R ≥ 1.0 | Yes | GOOD |
| R ≥ 0.0 | Yes | FAIR |
| R ≥ −0.5 | No  | FAIR |
| R ≥ −1.5 | No  | POOR |
| R < −1.5  | No  | BAD |

### 4.3 Reinforcement Type

For each DNA feature in `PMCIResult.breakdown`:

| DNA role | Outcome | Type |
|---|---|---|
| matched (winner-aligned) | Won | POSITIVE |
| matched (winner-aligned) | Lost | NEGATIVE |
| conflicting (loser-aligned) | Won | CONTRADICTORY |
| conflicting (loser-aligned) | Lost | NEUTRAL |
| \|R\| < min_r_multiple_magnitude | Any | NEUTRAL |
| lifecycle not in eligible_lifecycles | Any | INSUFFICIENT_EVIDENCE |
| evidence_count < min_idr_evidence_count | Any | INSUFFICIENT_EVIDENCE |

### 4.4 Confidence Delta Formula

```python
r_factor     = clamp(|R|, r_scale_min=0.5, r_scale_max=2.0)
raw_delta    = learning_rate × r_factor × alignment
confidence_delta = raw_delta × direction_sign
confidence_delta = clamp(confidence_delta, -max_single_trade_delta, +max_single_trade_delta)
```

Where `direction_sign`:
- POSITIVE: +1
- NEGATIVE: −1
- CONTRADICTORY: −1 × contradictory_weight (default 0.5)
- NEUTRAL / INSUFFICIENT_EVIDENCE: 0

### 4.5 Stability Delta

| Type | Stability delta |
|---|---|
| POSITIVE | +0.01 |
| NEGATIVE | −0.02 |
| CONTRADICTORY | −0.02 |
| NEUTRAL | 0.0 |
| INSUFFICIENT_EVIDENCE | 0.0 |

### 4.6 Final Update

```python
new_confidence  = clamp(old_confidence + delta, 0.05, 0.99)
new_stability   = clamp(old_stability + stab_delta, 0.0, 1.0)
new_evidence_count = old_evidence_count + 1
```

Written to IDR via `idr.update()`, which creates a new immutable version.

---

## 5. Safety Guarantees

| Guarantee | Mechanism |
|---|---|
| No single trade corrupts DNA | `max_single_trade_delta = 0.05` (hard cap) |
| Immature DNA protected | `min_idr_evidence_count = 10` guard |
| Confidence stays in bounds | clamp(new_conf, 0.05, 0.99) |
| Stability stays in bounds | clamp(new_stab, 0.0, 1.0) |
| No runaway batch | `max_reinforcements_per_batch = 5` per DNA |
| IDR integrity preserved | versioned updates via `idr.update()` |
| Thread safety | `threading.Lock()` for all state mutations |
| No duplicate processing | `_pending` set guards in-flight trade IDs |
| Dry-run mode | All computation done, zero IDR/file writes |

---

## 6. Data Flow

```
ClosedTrade (OrderRecord)
    │
    ▼
PMCIResult.breakdown
    ├── matched_dna     ──────┐
    └── conflicting_dna ──────┤
                              │
                              ▼
                    IDR lookup by (feature_name, direction)
                              │
                              ▼
                    Eligibility check
                    (lifecycle, evidence_count)
                              │
                   ┌──────────┴──────────┐
                   │ INSUFFICIENT        │ ELIGIBLE
                   │                     │
                   ▼                     ▼
           Record + skip        Compute reinforcement_type
                                Compute confidence_delta
                                Compute stability_delta
                                         │
                                    dry_run?
                                   ┌─────┴─────┐
                                  NO           YES
                                   │             │
                                   ▼             └── (no write)
                           idr.update()
                                   │
                                   ▼
                         DNAReinforcement record
                                   │
                                   ▼
                         history.json (atomic write)
```

---

## 7. Explainability

Every reinforcement includes:

```json
{
  "reinforcement_id": "DRE-a1b2c3d4e5f6",
  "dna_id": "dna_rsi_high",
  "feature_name": "rsi",
  "direction": "WINNERS_HIGHER",
  "trade_id": "ORD-20260804-001",
  "reinforcement_type": "POSITIVE",
  "confidence_before": 0.72,
  "confidence_after": 0.7560,
  "confidence_delta": 0.036,
  "stability_before": 0.80,
  "stability_after": 0.81,
  "stability_delta": 0.01,
  "reason": "POSITIVE: 'rsi' (WINNERS_HIGHER) alignment=0.800 R=+1.50 quality=GOOD confidence_delta=+0.03600",
  "evidence": {
    "trade_id": "ORD-20260804-001",
    "symbol": "RELIANCE",
    "r_multiple": 1.5,
    "pmci_score": 0.71,
    "dna_alignment": 0.80,
    "outcome_quality": "GOOD",
    "won": true
  }
}
```

**Why confidence changed:** stated in `reason` field.  
**Why stability changed:** sign of reinforcement_type.  
**Why relevance changed:** computed from new confidence in next CDS evaluation.  
**Reproduced:** `confidence_before + confidence_delta == confidence_after` (T179).

---

## 8. Coexistence with MLS (AMLS)

| Concern | How handled |
|---|---|
| Both DRE and AMLS write to IDR | IDR is versioned — each write creates a new version; reads always see the latest |
| AMLS runs at 15:38–15:45; DRE runs after EOD at 15:46+ | No time overlap in production (scheduled after AMLS completes) |
| Both increment `evidence_count` | Each increment is independent and non-destructive |
| AMLS updates `confidence` from statistical evidence; DRE from trading outcomes | Different study_id ("DRE" vs discovery study IDs) enables audit separation |
| DRE metadata tracks `dre_reinforcement_count` | Does not interfere with MLS metadata fields |

---

## 9. Final Certification Answers

**Q1: Can every reinforcement be traced to one trade?**  
YES. Every `DNAReinforcement.trade_id` is the `OrderRecord.order_id` of the closed trade.
The `evidence` bundle records `symbol`, `regime_at_entry`, `pmci_score`,
`dna_alignment`, `r_multiple`, `pnl`, and `holding_period_h` from that trade.

**Q2: Can every confidence change be reproduced?**  
YES. `confidence_before + confidence_delta == confidence_after` is guaranteed by
construction (T179). The delta is deterministic from `(reinforcement_type, |R|, alignment,
learning_rate)` — all recorded in the `DNAReinforcement` record.

**Q3: Can one bad trade corrupt institutional DNA?**  
NO. Three independent guards prevent this:
1. `max_single_trade_delta = 0.05` — hard cap on |delta| per trade
2. `min_idr_evidence_count = 10` — immature DNA cannot be touched
3. `confidence_min = 0.05` / `confidence_max = 0.99` — absolute bounds

**Q4: Can DRE coexist with MLS without conflicting updates?**  
YES. IDR is fully versioned — every update creates a new immutable version.
DRE uses `study_id="DRE"`, MLS uses discovery study IDs. The two systems
write independently without locking each other out. IDR's `_write_lock`
ensures one write at a time at the SQLite level.

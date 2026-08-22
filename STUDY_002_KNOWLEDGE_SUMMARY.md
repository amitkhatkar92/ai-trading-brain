# STUDY 002 KNOWLEDGE SUMMARY
## One-Year Historical Market Learning

**Document Type:** Knowledge Growth Record  
**Date:** 2026-08-01  
**Evidence Source:** `data/study002_results.json`

---

## 1. Knowledge Store Inventory — Before and After

| Store | Pre-Study | Post-Study | Delta | Notes |
|---|---|---|---|---|
| `ede_feature_db.json` — total rows | 5,000 | 5,000 | 0 net | EDE caps at 5,000 most recent |
| `ede_feature_db.json` — labeled rows | 4,964 | 4,885 | -79 | EDE trimmed older RE001 rows |
| `discovered_edges.json` — total | 257 | 259 | +2 | 2 new edges created |
| `discovered_edges.json` — ACTIVE | 0 | 2 | +2 | First real ACTIVE edges |
| `discovered_edges.json` — CANDIDATE | 124 | 125 | +1 | 1 new candidate |
| `discovered_edges.json` — DECAYING | 133 | 132 | -1 | 1 demoted |
| `discovered_edges.json` — DEPRECATED | 0 | 0 | 0 | — |
| `evolved_strategies.json` | 176 | 177 | +1 | First new strategy from real data |
| `strategy_performance.json` | 2 tracked | 2 tracked | 0 | No live outcome data |
| `ml_performance_dataset.json` | 0 records | 0 records | 0 | Requires closed trades |

---

## 2. Feature Database — Gross Production vs Stored

The EDE's internal `save_feature_db()` retains only the 5,000 most recent records. Study 002 computed 50,539 feature vectors. The gross production is the scientifically significant number; the stored number reflects a platform constraint.

| Metric | Value |
|---|---|
| Feature vectors computed | 50,539 |
| Feature vectors stored (EDE cap) | 5,000 |
| Vectors lost to EDE trimming | 45,539 |
| Source symbols covered | 209 NSE symbols |
| Trading dates covered | 242 dates |
| Positive labels (return ≥ 0.8%) | 14,302 |
| Negative labels | 36,237 |
| Positive rate | 28.3% |
| Regime encoding | Real per-date (SIDEWAYS, TRENDING_UP, TRENDING_DOWN) |

**Study 002 vs RE001A:**

| Metric | RE001A | Study 002 | Factor |
|---|---|---|---|
| Feature vectors computed | 5,039 | 50,539 | 10.0× |
| Symbols covered | 210 | 209 | ~1× |
| Trading dates | 24 | 242 | 10.1× |
| Regimes in data | 1 (SIDEWAYS only) | 3 | 3× |
| Positive labels | 1,452 | 14,302 | 9.9× |

---

## 3. Edge Knowledge — Lifecycle State Map

### Pre-Study

| Status | Count |
|---|---|
| ACTIVE | 0 |
| CANDIDATE | 124 |
| DECAYING | 133 |
| DEPRECATED | 0 |
| **Total** | **257** |

### Post-Study

| Status | Count |
|---|---|
| ACTIVE | 2 |
| CANDIDATE | 125 |
| DECAYING | 132 |
| DEPRECATED | 0 |
| **Total** | **259** |

### Changes During Study

| Edge ID | Change | Category | Metrics |
|---|---|---|---|
| EDG_MOMENT_93_EE0000 | Created → CANDIDATE | momentum_trend | WR=88%, Exp=+1.29R, WF=40% (rejected) |
| EDG_COMPOS_73_EE0001 | Created → ACTIVE | composite | WR=71%, Exp=+0.53R, Sharpe=7.68 |
| EDG_MOMENT_86_EE0002 | CANDIDATE → ACTIVE | momentum_volume | WR=85%, Exp=+0.59R, Sharpe=17.38 |

---

## 4. Pattern Mining Results

| Metric | RE001A | Study 002 |
|---|---|---|
| Feature matrix size | 10,059 × 58 | 55,559 × 58 |
| Patterns discovered (precision ≥ 58%, support ≥ 15) | 3 | 3 |
| Candidates generated | 3 | 3 |
| Approved (WF ≥ 50%) | 0 | **2** |
| Rejected (WF < 50%) | 3 | 1 |
| False positive rate | 100% | 33.3% |
| New strategies promoted | 0 | **1** |

**Key finding:** The transition from 29 SIDEWAYS sessions (RE001) to 244 multi-regime sessions (Study 002) changed the EDE outcome from 0% approval to 66.7% approval. The larger, multi-regime feature matrix appears to produce more walk-forward-stable patterns.

---

## 5. Sector Conviction Knowledge

| Metric | RE001A | Study 002 |
|---|---|---|
| FULL conviction rows | 336 | 2,916 |
| Sectors tracked | 12 | 12 |
| Sessions covered | 29 | 243 |
| FULL coverage rate | 96.6% | 99.6% |
| Best single-day conviction (IT, 2026-07-29) | 0.976 | 0.976 (same session) |
| Sector with highest average conviction | IT (inferred) | METALS (0.328) |

---

## 6. Signal and Opportunity Knowledge

| Metric | RE001 (30 sessions) | Study 002 (244 sessions) |
|---|---|---|
| Total signals | 124 | 8,562 |
| Archetypes active | 6 | 7 |
| Signals/session (average) | 4.3 | 35.1 |
| Opportunities created | 66 | 1,966 |
| INVALID rate | 21.2% | 95.4% |
| Closed outcomes | 0 | 0 |
| Dominant archetype | DNA_1B_SECTOR_PRE_BKT (63.7%) | DNA_1B_SECTOR_PRE_BKT (41.8%) |

---

## 7. MetaModel Knowledge State

| Metric | Value |
|---|---|
| Training records | 0 |
| Model trained | False |
| Records needed (minimum) | 10 |
| Structural blocker | No closed trade outcomes produced by either RE001 or Study 002 |
| Path to activation | Live paper trading or extended replay with price-based exit simulation |

The MetaModel remains the only completely unactivated component of the IIOS knowledge architecture. Its data dependency (closed trade outcomes) has now been confirmed across two research studies totalling 273 simulated trading sessions.

---

## 8. Cumulative Knowledge Position

After two research studies (RE001: 29 sessions + Study 002: 244 sessions = 273 cumulative simulated sessions):

| Knowledge Type | Quantity | Quality |
|---|---|---|
| Feature observations computed | 55,578 | Real NSE OHLCV with forward returns |
| ACTIVE edges | 2 | Walk-forward validated |
| Strategy library entries | 177 | Platform-evolved |
| Sector conviction records | 3,252+ FULL rows | 12 sectors, 243+ sessions |
| MetaModel training records | 0 | Structural gap — requires outcome data |

**First-ever milestones achieved in Study 002:**
1. First ACTIVE edges discovered (EDG_MOMENT_86_EE0002, EDG_COMPOS_73_EE0001)
2. First walk-forward-approved strategy from real data (EDG_COMPOS_73_EE0001)
3. First multi-regime feature database (SIDEWAYS + TRENDING_UP + TRENDING_DOWN)
4. Largest single-study feature extraction (50,539 vectors in one run)

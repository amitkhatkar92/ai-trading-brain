# RoadmapManager — Design Document

**ARS Phase 2B**  
**Module:** `autonomous_research/roadmap_manager.py`  
**Status:** Complete (52/52 tests passing)

---

## 1. Purpose

RoadmapManager is the scientific research prioritization engine for the IIOS
Autonomous Research System.  It consumes `KnowledgeGap` objects produced by
`GapDetector`, evaluates each gap across five quantitative dimensions, and
emits a ranked, portfolio-balanced `ResearchRoadmap`.

The engine is purely analytical — it reads from KnowledgeProvider and
GapDetector but writes nothing to them.  The only persistent side-effect is
`data/ars_roadmap_state.json`, which tracks when each gap_id was first
observed, enabling research debt to compound across successive runs.

---

## 2. Five-Dimension Evaluation Framework

Every gap is evaluated across five dimensions before a priority score is
assigned.  The five dimensions are orthogonal: a gap can score high on one
and low on another.

```
┌─────────────────────────┬───────────────────────────────────────────────┐
│ Dimension               │ What it measures                              │
├─────────────────────────┼───────────────────────────────────────────────┤
│ Knowledge Gain          │ How much scientific value addressing the gap  │
│                         │ will deliver (9-component formula)            │
├─────────────────────────┼───────────────────────────────────────────────┤
│ Research Cost           │ Effort, compute time, and risk required       │
│                         │ (3-component formula)                         │
├─────────────────────────┼───────────────────────────────────────────────┤
│ Research Debt           │ How much the gap has accumulated urgency      │
│                         │ over time (4-component formula)               │
├─────────────────────────┼───────────────────────────────────────────────┤
│ Scientific Importance   │ Severity-based base importance (from gap      │
│                         │ metadata, not re-derived)                     │
├─────────────────────────┼───────────────────────────────────────────────┤
│ Urgency                 │ Time-sensitive need to act now (severity *    │
│                         │ temporal factor for TEMPORAL_GAP)             │
└─────────────────────────┴───────────────────────────────────────────────┘
```

---

## 3. Knowledge Gain Formula

```
raw_gain  = si*0.25 + eg*0.20 + ci*0.20 + cov*0.15 + nov*0.10 + rp*0.10
adjusted  = raw_gain * (1 + ur * 0.15)        ← uncertainty bonus
final     = adjusted * (0.70 + hi * 0.30)     ← historical impact anchor
total_gain = clamp(final, 0.0, 1.0)
```

| Symbol | Meaning | Source |
|--------|---------|--------|
| `si`   | Scientific importance from gap severity | `_SEVERITY_IMPORTANCE` |
| `eg`   | Evidence gap size (how much is missing) | `_CATEGORY_EVIDENCE_GAP` |
| `ci`   | Expected confidence improvement | `_CATEGORY_CONF_IMPROVEMENT` |
| `cov`  | Coverage increase (regime/sector) | `_CATEGORY_COVERAGE` |
| `nov`  | Novelty of the territory | `_CATEGORY_NOVELTY` |
| `rp`   | Reuse potential of new findings | `_CATEGORY_REUSE` |
| `ur`   | Uncertainty reduction | `_CATEGORY_UNCERTAINTY` |
| `hi`   | Historical impact proxy (from `gap.estimated_knowledge_gain`) | GapDetector |

---

## 4. Research Cost Formula

```
replay_factor = min(1.0, replay_duration_hours / 8.0)
total_cost    = effort * 0.40 + risk * 0.30 + replay_factor * 0.30
```

| Symbol | Source |
|--------|--------|
| `effort` | `_CATEGORY_EFFORT[gap.category]` |
| `risk`   | `_CATEGORY_RISK[gap.category]` |
| `replay_duration_hours` | `_CATEGORY_REPLAY_HOURS[gap.category]` |

---

## 5. Research Debt Formula

```
total_debt = clamp(
    base_debt          * 0.50
    + age_debt         * 0.30
    + contradiction_debt * 0.10
    + expiry_debt      * 0.10,
    0.0, 1.0
)
```

| Component | Source |
|-----------|--------|
| `base_debt` | `_SEVERITY_BASE_DEBT[gap.severity]` — CRITICAL=1.00, HIGH=0.75, MEDIUM=0.50, LOW=0.25 |
| `age_debt` | `age_days / debt_half_life_days`, capped at 1.0 — grows over time |
| `contradiction_debt` | +0.30 for CONTRADICTION_GAP (unresolved conflict adds urgency) |
| `expiry_debt` | +0.20 for TEMPORAL_GAP (knowledge staleness) |

Age is computed from `data/ars_roadmap_state.json`: first-seen timestamp persists
across runs so debt accumulates realistically.

---

## 6. Priority Formula

```
priority = (
    kg.total_gain           * w_knowledge_gain
    + debt.total_debt       * w_research_debt
    + kg.scientific_importance * w_scientific_importance
    + (1 - cost.total_cost) * w_cost_efficiency
    + urgency               * w_urgency
) / sum_of_all_weights
```

Default weights (from `RoadmapManagerConfig`):

| Weight | Default |
|--------|---------|
| `w_knowledge_gain` | 0.30 |
| `w_research_debt` | 0.25 |
| `w_scientific_importance` | 0.25 |
| `w_cost_efficiency` | 0.10 |
| `w_urgency` | 0.10 |

Weights are normalized by their sum (total = 1.00 with defaults).
All weights are user-configurable via `RoadmapManagerConfig`.

---

## 7. Portfolio Balancing

RoadmapManager maps every `GapCategory` to a `StudyCategory`:

| GapCategory | StudyCategory |
|-------------|---------------|
| DATA_GAP | VALIDATION |
| EVIDENCE_GAP | WINNER_DNA |
| REGIME_GAP | MARKET_REGIMES |
| SECTOR_GAP | SECTOR_RESEARCH |
| TEMPORAL_GAP | VALIDATION |
| VALIDATION_GAP | VALIDATION |
| CONTRADICTION_GAP | RISK |
| CONFIDENCE_GAP | EXPLORATION |
| KNOWLEDGE_GAP | EXPLORATION |
| COVERAGE_GAP | MARKET_REGIMES |

Portfolio analysis computes actual vs. target allocation, flags imbalanced
categories (> `portfolio_imbalance_threshold` off-target), and generates
plain-English rebalancing recommendations.

---

## 8. Determinism Guarantee

All priority scores, entry_ids, and sort order are deterministic.

- `entry_id = f"RE-{sha256(gap_id.encode()).hexdigest()[:8].upper()}"`
- Same gap objects → same knowledge gain, cost, debt, and priority scores
- Sort key: `(-priority_score, gap.gap_id)` — alphabetical tie-break ensures
  stable ordering even when scores are equal

The only non-deterministic element is `roadmap_id` (uuid4), which is
intentionally unique per build call so consumers can distinguish roadmap
versions.

---

## 9. State Persistence

State file: `data/ars_roadmap_state.json`

```json
{
  "version": "1.0",
  "last_updated": "2026-08-01T10:00:00.000000",
  "gap_first_seen": {
    "G-EVID-XXXX-12345678": "2026-07-15T09:00:00.000000",
    "G-REGI-XXXX-abcdef01": "2026-07-20T14:30:00.000000"
  }
}
```

Write is atomic: `.tmp` → `os.replace` with `.bak` backup.
New gap_ids are added on every `build()` call; existing entries are never
removed (supports long-horizon debt accumulation).

---

## 10. Thread Safety

All `build()`, `_load_state()`, and `_save_state()` operations are protected
by a `threading.Lock()`.  The test suite verifies 8 concurrent `build(force=True)`
calls complete without error or data corruption.

---

## 11. Design Constraints

1. **Read-only**: RoadmapManager never modifies KnowledgeProvider, HypothesisRegistry,
   GapDetector, or any input gap.
2. **No circular dependency**: roadmap_manager imports from gap_models and roadmap_models
   only; it does not import from strategy_lab or execution_engine.
3. **No logging to user**: All log output goes through Python's `logging` module at
   WARNING level or below.
4. **Backward compatibility**: New fields may be added to `RoadmapManagerConfig`
   with defaults; existing fields must not be renamed.

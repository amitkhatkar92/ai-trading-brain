# MASTER ARCHITECTURE SPECIFICATION v1.2
## Opportunity Intelligence Operating System (OIOS)

**Status:** Post-Forensic-Audit-Round-3 — ARCHITECTURE FROZEN  
**Date:** 2026-06-16  
**Coding Authorization:** GRANTED for Phase A0

This is the single authoritative specification. All prior versions (v1.0, v1.1) and all audit
documents are superseded. No references to audit history appear in this document.

---

## SECTION 1 — SYSTEM PURPOSE

Traditional trading systems ask: *What should I buy?*

OIOS asks:

- What opportunity exists?
- How much edge remains in it?
- How mature is it?
- How long does it remain valid?
- Should capital be deployed now, or is the opportunity stale?

OIOS manages **opportunities**, not signals. An opportunity is a directional thesis on a symbol
with an accumulated evidence base, a lifecycle state, a remaining edge score, and an expiry
condition. Signals are evidence attached to opportunities. The distinction is structural: signals
describe what a stock is doing at a point in time. Opportunities describe a tradable thesis that
evolves over time until it is either acted upon, exhausted, or invalidated.

---

## SECTION 2 — THREE-ENGINE ARCHITECTURE

```
ENGINE A — DISCOVERY
  Finds opportunities and accumulates evidence.

  Layer 0    Data Foundation
  Layer 1A   Confirmation DNA
  Layer 1B   Early Warning DNA
  Layer 1.5  Sector Conviction Engine
               Sub-A: Consensus Shift Intelligence
               Sub-B: Capital Flow Intelligence
               Sub-C: Theme Phase Engine
               Sub-D: Theme Recurrence Engine
  Layer 2    Cause Intelligence           [Phase E1 — gated on daily_events pipeline]
  Layer 3    Cause Propagation            [Phase E1 — gated on Knowledge Graph V1]

ENGINE B — LIFECYCLE
  Evaluates whether each opportunity is still worth acting on.

  Layer 5    Edge Lifecycle Engine
               Sub-A: Remaining Edge (RE) Calculator
               Sub-B: Maturity Engine (Temporal × Path × Conviction)
               Sub-C: Velocity Engine (d(RE)/dt with attribution)
               Sub-D: Opportunity State Machine
               Sub-E: Transition Probability Model  [Phase C — gated on ≥20 observations]

ENGINE C — LEARNING
  Recalibrates both engines from observed outcomes.

  Layer 4    Self-Audit Intelligence
               Sub-A: Missed Winner Analysis
               Sub-B: Counterfactual Engine
               Sub-C: Signal Birth Record Writer
  Layer 6    Adaptive Intelligence        [Phase D — gated on ≥30 observations]
               Sub-A: Parameter Adjuster (with guardrails)
               Sub-B: Approval Gateway (Telegram interface)

──────────────────────────────────────────────────────────
EXISTING EXECUTION SYSTEM  (17-layer operational trading engine — unchanged)
  Debate → Risk → Kill-switch → Orders → Monitoring → Portfolio
──────────────────────────────────────────────────────────
```

The Execution System is a consumer of OIOS outputs. It receives ACTIVE opportunity scores and
returns position state updates. The interface is a two-way data contract defined in Section 6.

---

## SECTION 3 — OPPORTUNITY STATE MACHINE

The state machine lives on the `opportunities` table, not on individual signals.

```
DISCOVERED
    │
    ├── conviction_score crosses ACTIVE_THRESHOLD
    │   AND position_size_pct < 0.80
    │                                           ──→  ACTIVE
    │
    └── discovered_expires_at reached             ──→  INVALID  [reason: NEVER_MATURED]


ACTIVE  ◄──────────────────────────────────────────────────────┐
    │                                                           │
    │  RE drops below ACTIVE_THRESHOLD                         │  RE recovers above ACTIVE_THRESHOLD
    │  AND age_trading_days < effective_ttl_days × 0.80        │  AND age_trading_days < effective_ttl_days × 0.80
    │                                                           │
    └──────────────────────────────────────────►  WATCHING ────┘
                                                     │
                                                     │  Any terminal condition below
                                                     ▼
                                                  INVALID  (terminal — no recovery)


ACTIVE  ──────────────────────────────────────────────────────►  INVALID  (if terminal condition)
```

### Terminal Conditions (force INVALID from any non-DISCOVERED state)

| Condition | Trigger | Reason Code |
|---|---|---|
| TTL exhaustion | age_trading_days ≥ effective_ttl_days | TTL_EXHAUSTED |
| EC threshold | edge_consumed_pct ≥ 1.0 | EC_EXHAUSTED |
| Volume burst | single-day volume > 3× 20d average | THESIS_INVALIDATED |
| Zombie cap | age_trading_days > effective_ttl_days × 1.2 | ZOMBIE_CAP |
| Sustained contradiction | conflicting_count > confirming_count for 3 consecutive days | CONTRADICTED |

### DISCOVERED Expiry

```
discovered_expires_at = created_at + floor(birth_ttl_days × 0.50) trading days
```

An opportunity that remains in DISCOVERED state until `discovered_expires_at` is INVALID with
reason NEVER_MATURED. DISCOVERED → WATCHING is not a valid transition. WATCHING implies the
opportunity previously reached ACTIVE. A signal that never reached ACTIVE expires directly to
INVALID.

### Regime Transition During Lifetime

- `birth_ttl_days` is immutable. Set at creation. Never modified.
- `effective_ttl_days` is recomputed daily using the current regime multiplier.
- Anti-retroactivity floor: `effective_ttl_days ≥ age_trading_days + 3` at all times.
  A regime change never forces same-day invalidation. The opportunity always retains at least
  3 trading days to respond after regime information arrives.
- Regime improvements do not extend `effective_ttl_days` beyond the bull-market ceiling.
  Exception: if the sector transitions to EMERGENCE phase after signal birth, a one-time
  theme extension of up to +30% of birth_ttl_days is permitted.

---

## SECTION 4 — COMPLETE DATABASE SCHEMA

All tables are stored in `data/market_behavior.db`.
Every table, writer, and reader is named. A component not listed as a writer does not write.
A component not listed as a reader does not read.

---

### Table 0: `stock_sector_map`

**Purpose:** Authoritative mapping of every stock to its primary sector, with a purity score
for conglomerates. Required by Layer 1.5 for weighted participation rate computation.
This table is a Phase A0 prerequisite — it must exist before Layer 1.5 is built.

**Writer:** Manual maintenance (annual review); versioned on any sector reclassification.  
**Readers:** Layer 0 (data tagging), Layer 1.5 (weighted participation), ELE (sector context).

```sql
CREATE TABLE stock_sector_map (
    symbol              TEXT    NOT NULL,
    primary_sector      TEXT    NOT NULL,
    sector_purity_score REAL    NOT NULL DEFAULT 1.0,
    -- 1.0 = pure-play. 0.6 = 60% revenue from primary sector.
    -- Used to weight participation rates: conglomerates count proportionally.
    effective_from      DATE    NOT NULL,
    effective_to        DATE,               -- NULL = current mapping
    change_reason       TEXT,
    PRIMARY KEY (symbol, effective_from)
);

CREATE INDEX idx_ssm_symbol  ON stock_sector_map(symbol);
CREATE INDEX idx_ssm_sector  ON stock_sector_map(primary_sector);
```

**Weighted participation rate formula (Layer 1.5):**
```
weighted_participation_rate =
    SUM(sector_purity_score × 1 WHERE return > threshold)
    / SUM(sector_purity_score)
```
NIFTY/BANKNIFTY/INDIAVIX index symbols are excluded from all sector participation
calculations — they are market benchmarks, not sector constituents.

---

### Table 1: `trading_calendar`

**Purpose:** NSE trading days reference. All age and TTL computations use trading days exclusively.
Calendar day arithmetic is prohibited throughout OIOS.

**Writer:** Annual maintenance script (NSE holiday list input).  
**Readers:** Every component computing signal age, TTL expiry, or phase duration.

```sql
CREATE TABLE trading_calendar (
    calendar_date   DATE    PRIMARY KEY,
    is_trading_day  BOOLEAN NOT NULL,
    holiday_name    TEXT                -- populated for market holidays
);
```

Populated for current year + 2 forward years at minimum. Updated in January each year.

---

### Table 2: `archetype_versions`

**Purpose:** Version history of every archetype. Prevents outcome distribution contamination
when Layer 6 modifies archetype detection rules.

**Writer:** Layer 6 Adaptive Intelligence, on every parameter change.  
**Readers:** signal_births writer (captures current version), archetype_outcome_distributions.

```sql
CREATE TABLE archetype_versions (
    version_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    archetype_id        TEXT    NOT NULL,
    version_number      INTEGER NOT NULL,
    effective_from      DATE    NOT NULL,
    effective_to        DATE,               -- NULL = currently active
    change_reason       TEXT,
    parameter_snapshot  TEXT,               -- JSON: detection rule parameters at this version
    approved_by         TEXT    DEFAULT 'SYSTEM',
    UNIQUE(archetype_id, version_number)
);
```

---

### Table 3: `opportunities`

**Purpose:** Root entity table. Every tradable thesis originates here.
Signals and sector evidence are attached to opportunities. Portfolio and ELE decisions
operate on opportunities, not on individual signals.

**Writer:** Discovery Engine (creates); ELE Sub-D (updates state, RE, conviction);
Execution System (updates position fields).  
**Readers:** ELE all sub-modules; Self-Audit; Layer 6; Decision Engine; Execution System.

```sql
CREATE TABLE opportunities (
    -- Identity
    opportunity_id          TEXT    PRIMARY KEY,    -- UUID
    symbol                  TEXT    NOT NULL,
    direction               TEXT    NOT NULL,       -- "LONG" | "SHORT"
    sector                  TEXT    NOT NULL,       -- primary sector at creation

    -- Birth context
    created_at              DATE    NOT NULL,       -- NSE trading date
    first_signal_id         TEXT,                   -- FK → signal_births.signal_id
    regime_at_birth         TEXT    NOT NULL,
    theme_phase_at_birth    TEXT,

    -- Lifecycle state
    current_state           TEXT    NOT NULL DEFAULT 'DISCOVERED',
    -- "DISCOVERED" | "ACTIVE" | "WATCHING" | "INVALID"

    -- TTL (trading days)
    birth_ttl_days          INTEGER NOT NULL,       -- immutable at creation
    effective_ttl_days      INTEGER NOT NULL,       -- recomputed daily (regime-adjusted)
    age_trading_days        INTEGER DEFAULT 0,      -- updated each cycle
    discovered_expires_at   DATE    NOT NULL,       -- = created_at + floor(birth_ttl × 0.5)

    -- Conviction aggregation
    conviction_score        REAL    DEFAULT 0.0,    -- Σ(confirming w×RE) - Σ(conflicting w×RE)
    confirming_count        INTEGER DEFAULT 0,
    conflicting_count       INTEGER DEFAULT 0,

    -- RE and lifecycle metrics
    re_score                REAL,
    edge_consumed_pct       REAL    DEFAULT 0.0,
    maturity_combined       TEXT,                   -- "SEED"|"EMERGING"|"DEVELOPING"|"MATURE"|"LATE_STAGE"
    velocity_3d             REAL,
    velocity_class          TEXT,
    -- "THESIS_WORKING"|"REGIME_PRESSURE"|"CROWDING"|"MECHANICAL_DECAY"

    -- Position state (written by Execution System)
    position_exists         BOOLEAN DEFAULT FALSE,
    position_size_pct       REAL    DEFAULT 0.0,   -- 0.0–1.0 fraction of intended max size
    position_open_date      DATE,

    -- Outcome
    final_state             TEXT,
    invalidation_reason     TEXT,
    finalized_at            DATE,
    trade_pnl_pct           REAL,
    is_audit_trade          BOOLEAN DEFAULT FALSE,  -- 5% forced audit paper trade

    -- Audit metadata
    created_at_ts           DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated_at         DATETIME
);

CREATE INDEX idx_opp_symbol     ON opportunities(symbol);
CREATE INDEX idx_opp_state      ON opportunities(current_state);
CREATE INDEX idx_opp_sector     ON opportunities(sector);
CREATE INDEX idx_opp_direction  ON opportunities(symbol, direction, current_state);
```

#### Opportunity Creation Rule

When a signal fires (base_score > 4.0), the Discovery Engine checks:

```
EXISTS (
    SELECT 1 FROM opportunities
    WHERE symbol = :symbol
      AND direction = :direction
      AND current_state IN ('DISCOVERED', 'ACTIVE', 'WATCHING')
)
```

- **Match found AND `age_trading_days < effective_ttl_days × 0.75`:** attach signal as additional evidence. Do not create new row.
- **Match found BUT `age_trading_days ≥ effective_ttl_days × 0.75`:** existing opportunity is too old to absorb new evidence. Create a new opportunity for the incoming signal.
- **No match:** create new opportunity. The signal becomes founding evidence.
- **Opposite direction match (ACTIVE/WATCHING) AND within merge window:** attach as CONFLICTING evidence to existing opportunity.
- **All matches are INVALID:** create new opportunity (new lifecycle, new thesis).

The merge window (`age < effective_ttl × 0.75`) prevents a late-lifecycle WATCHING opportunity from absorbing an unrelated fresh signal. An opportunity in the final 25% of its TTL does not accept new evidence — new signals on the same stock at this stage open a fresh opportunity with a clean lifecycle.

---

### Table 4: `opportunity_signals`

**Purpose:** Junction table linking evidence signals to the opportunity they support or contradict.

**Writer:** Discovery Engine, on every signal-to-opportunity attachment.  
**Readers:** ELE conviction score recomputation; Self-Audit.

```sql
CREATE TABLE opportunity_signals (
    opportunity_id      TEXT    NOT NULL REFERENCES opportunities(opportunity_id),
    signal_id           TEXT    NOT NULL REFERENCES signal_births(signal_id),
    signal_type         TEXT    NOT NULL,       -- "1A" | "1B" | "1.5" | "2" | "3"
    signal_direction    TEXT    NOT NULL,       -- "CONFIRMING" | "CONFLICTING" | "NEUTRAL"
    evidence_weight     REAL    NOT NULL,       -- contribution to conviction_score
    added_at            DATE    NOT NULL,
    PRIMARY KEY (opportunity_id, signal_id)
);

CREATE INDEX idx_os_opp_id  ON opportunity_signals(opportunity_id);
CREATE INDEX idx_os_sig_id  ON opportunity_signals(signal_id);
```

#### Default Evidence Weights by Signal Type

| Signal Type | Default Weight |
|---|---|
| 1B Early Warning DNA | 1.00 |
| 3 Cause Propagation | 0.70 |
| 1A Confirmation DNA | 0.80 |
| 1.5 Sector Conviction | 0.60 |
| 2 Cause Intelligence | 0.50 |

Weights are adjustable by Layer 6 within ±20% per calibration cycle.

---

### Table 5: `signal_births`

**Purpose:** Record of every signal that meets the minimum detection threshold (base_score > 4.0).
Signals below 4.0 are not written. Signals from 4.0 to the ACTIVE threshold populate the
counterfactual dataset.

**Writer:** Discovery Engine (creates and updates); ELE Sub-D (updates state fields).  
**Readers:** opportunity_signals; ELE; Self-Audit; Layer 6.

```sql
CREATE TABLE signal_births (
    -- Identity
    signal_id               TEXT    PRIMARY KEY,    -- UUID
    opportunity_id          TEXT    REFERENCES opportunities(opportunity_id),
    symbol                  TEXT    NOT NULL,
    archetype_id            TEXT    NOT NULL,
    archetype_version       INTEGER NOT NULL,       -- FK → archetype_versions.version_id
    signal_type             TEXT    NOT NULL,       -- "1A" | "1B" | "1.5"

    -- Birth context
    detected_at             DATE    NOT NULL,       -- NSE trading date
    birth_price             REAL    NOT NULL,
    base_score              REAL    NOT NULL,       -- score at detection, never modified
    regime_at_birth         TEXT    NOT NULL,
    theme_phase_at_birth    TEXT,
    consensus_score_at_birth REAL,

    -- Expected outcome
    expected_move_pct       REAL,
    expected_move_pct_source TEXT,
    -- "ARCHETYPE_DISTRIBUTION" | "UNIVERSAL_DEFAULT_8PCT" | "REGIME_ADJUSTED_DEFAULT"
    expected_ttl_days       INTEGER NOT NULL,       -- in NSE trading days
    expected_move_direction TEXT    NOT NULL,       -- "LONG" | "SHORT"

    -- Live fields (updated each cycle)
    current_state           TEXT    NOT NULL DEFAULT 'ACTIVE',
    current_price           REAL,
    age_trading_days        INTEGER DEFAULT 0,
    actual_move_pct         REAL    DEFAULT 0.0,
    edge_consumed_pct       REAL    DEFAULT 0.0,
    re_score                REAL,

    -- Outcome
    final_state             TEXT,
    final_age_trading_days  INTEGER,
    peak_move_pct           REAL,
    days_to_peak            INTEGER,
    trade_executed          BOOLEAN DEFAULT FALSE,
    trade_outcome_pct       REAL,

    created_at_ts           DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated_at         DATETIME,
    invalidation_reason     TEXT
);

CREATE INDEX idx_sb_opportunity ON signal_births(opportunity_id);
CREATE INDEX idx_sb_symbol      ON signal_births(symbol);
CREATE INDEX idx_sb_archetype   ON signal_births(archetype_id);
CREATE INDEX idx_sb_detected    ON signal_births(detected_at);
```

**Phase A defaults for expected_move_pct:**
Until archetype_outcome_distributions has `is_distribution_active = TRUE` for the
(archetype_id, regime) combination, `expected_move_pct = 8.0` and
`expected_move_pct_source = "UNIVERSAL_DEFAULT_8PCT"`.

---

### Table 6: `signal_state_transitions`

**Purpose:** Complete audit trail of every state change per signal. Required for Markov
transition probability computation. Overwrites of `current_state` are prohibited —
all transitions are appended here.

**Writer:** ELE Sub-D, on every state change.  
**Readers:** ELE Sub-E Transition Probability Model; Layer 4 Self-Audit.

```sql
CREATE TABLE signal_state_transitions (
    transition_id               TEXT    PRIMARY KEY,    -- UUID
    signal_id                   TEXT    NOT NULL REFERENCES signal_births(signal_id),
    opportunity_id              TEXT    REFERENCES opportunities(opportunity_id),
    from_state                  TEXT    NOT NULL,
    to_state                    TEXT    NOT NULL,
    transitioned_at             DATETIME NOT NULL,
    trigger_cause               TEXT    NOT NULL,
    -- "TIME_DECAY" | "EC_THRESHOLD" | "REGIME_CHANGE" | "CONSENSUS_RECOVERY" |
    -- "VOLUME_BURST" | "CONVICTION_THRESHOLD" | "ZOMBIE_CAP" | "MANUAL_OVERRIDE"

    re_at_transition            REAL,
    age_trading_days            INTEGER,
    regime_at_transition        TEXT,
    theme_phase_at_transition   TEXT,
    consensus_score             REAL,
    edge_consumed_pct           REAL
);

CREATE INDEX idx_sst_signal_id  ON signal_state_transitions(signal_id);
CREATE INDEX idx_sst_opp_id     ON signal_state_transitions(opportunity_id);
CREATE INDEX idx_sst_from_to    ON signal_state_transitions(from_state, to_state);
```

---

### Table 7: `decision_log`

**Purpose:** Every decision per cycle per opportunity. Captures PASS decisions as well as
ENTER decisions. PASS records are the source data for counterfactual analysis.

**Writer:** ELE output handler, once per opportunity per cycle it is evaluated.  
**Readers:** Layer 4 Counterfactual Engine; Layer 6 threshold calibration.

```sql
CREATE TABLE decision_log (
    decision_id                 TEXT    PRIMARY KEY,    -- UUID
    opportunity_id              TEXT    NOT NULL REFERENCES opportunities(opportunity_id),
    signal_id                   TEXT    REFERENCES signal_births(signal_id),
    symbol                      TEXT    NOT NULL,
    decided_at                  DATETIME NOT NULL,
    action                      TEXT    NOT NULL,
    -- "ENTER"                  | "PASS_WATCHING"        | "PASS_RE_LOW"
    -- "PASS_STALE"             | "PASS_THEME_SUPPRESSED"| "PASS_POSITION_FULL"
    -- "INVALID_TTL"            | "INVALID_EC"           | "INVALID_VOLUME_BURST"
    -- "INVALID_ZOMBIE"         | "INVALID_CONTRADICTED" | "INVALID_NEVER_MATURED"
    -- "AUDIT_PAPER_TRADE"

    -- State at decision time
    conviction_score            REAL,
    re_score                    REAL,
    re_threshold_applied        REAL,
    suppression_reason          TEXT,
    signal_age_trading_days     INTEGER,
    regime                      TEXT,
    theme_phase                 TEXT,
    edge_consumed_pct           REAL,
    maturity_combined           TEXT,
    position_size_pct_at_decision REAL,
    price_at_decision           REAL    NOT NULL,

    -- Counterfactual fields (populated retroactively by Self-Audit nightly job)
    price_5d_later              REAL,
    price_10d_later             REAL,
    price_20d_later             REAL,
    max_adverse_20d             REAL,
    max_favorable_20d           REAL,
    outcome_populated_at        DATETIME,

    -- Counterfactual classification (populated by Self-Audit)
    subsequent_opportunity_id   TEXT    REFERENCES opportunities(opportunity_id),
    subsequent_opportunity_pnl  REAL,
    counterfactual_type         TEXT,
    -- "CLEAN"              — no subsequent opportunity on same symbol within 20 days
    -- "SAME_OPP_RECOVERED" — this opportunity later transitioned to ACTIVE
    -- "NEW_OPP_SUCCEEDED"  — a new opportunity on same symbol succeeded
    -- "NEW_OPP_FAILED"     — a new opportunity on same symbol also failed
    -- "AMBIGUOUS"          — multiple subsequent opportunities
    -- NULL                 — not yet classified
);

CREATE INDEX idx_dl_opportunity ON decision_log(opportunity_id);
CREATE INDEX idx_dl_action      ON decision_log(action);
CREATE INDEX idx_dl_decided_at  ON decision_log(decided_at);
CREATE INDEX idx_dl_symbol      ON decision_log(symbol);
```

**Counterfactual calibration rule:** Layer 6 may only use records where
`counterfactual_type = "CLEAN"` for RE threshold calibration. Records where
`counterfactual_type = "SAME_OPP_RECOVERED"` are used for TTL sensitivity analysis.
Records where `counterfactual_type IN ("NEW_OPP_SUCCEEDED", "NEW_OPP_FAILED", "AMBIGUOUS")`
are excluded from all calibration — the PASS decision was not the causal variable.

---

### Table 8: `sector_conviction_daily`

**Purpose:** Daily snapshot of all Layer 1.5 outputs per sector. Required for
M_consensus_delta computation (ratio of current to birth-date conviction score).

**Writer:** Layer 1.5 during EOD scan.  
**Readers:** ELE Sub-A (M_consensus_delta); Layer 4 Self-Audit.

```sql
CREATE TABLE sector_conviction_daily (
    record_date                 DATE    NOT NULL,
    sector                      TEXT    NOT NULL,

    -- Consensus Shift (Sub-A)
    participation_rate_1d       REAL,
    participation_rate_5d       REAL,
    participation_expansion     REAL,   -- week-over-week delta
    rs_vs_market_20d            REAL,
    volume_trend_10d            REAL,
    consensus_score             REAL,   -- 0.0–10.0

    -- Capital Flow (Sub-B)
    capital_flow_score          REAL    DEFAULT 0.5,   -- 0.0–1.0; 0.5 = neutral
    capital_flow_data_quality   TEXT,   -- "FULL" | "SPARSE" | "UNAVAILABLE"

    -- Combined
    sector_conviction_score     REAL,   -- 0.4×capital_flow + 0.6×consensus

    -- Theme Phase (Sub-C)
    theme_phase                 TEXT,

    -- Data quality
    data_quality                TEXT    DEFAULT 'FULL',  -- "FULL" | "PARTIAL"
    stocks_with_data            INTEGER,
    stocks_total                INTEGER,

    PRIMARY KEY (record_date, sector)
);
```

**Data quality rule:** If `stocks_with_data / stocks_total < 0.80`, set
`data_quality = 'PARTIAL'`. All downstream Layer 1.5 outputs for that sector on that
date are suppressed — not computed from partial data.

---

### Table 9: `theme_phase_history`

**Purpose:** Historical record of every sector theme phase transition. Source for
ThemeRecurrenceProfile computation and phase duration calibration.

**Writer:** Layer 1.5C Theme Phase Engine, on every detected phase transition.  
**Readers:** Layer 1.5D Theme Recurrence Engine; ELE context multipliers.

```sql
CREATE TABLE theme_phase_history (
    record_id               TEXT    PRIMARY KEY,    -- UUID
    sector                  TEXT    NOT NULL,
    phase                   TEXT    NOT NULL,
    -- "EMERGENCE" | "ACCELERATION" | "CONSENSUS" | "CROWDING" | "EXHAUSTION"
    entered_at              DATE    NOT NULL,
    exited_at               DATE,                   -- NULL if current phase
    duration_trading_days   INTEGER,                -- computed on exit
    regime_during           TEXT,
    peak_participation_rate REAL,
    amplitude_pct           REAL,                   -- sector return during this phase
    avg_volume_ratio        REAL,
    data_quality            TEXT    DEFAULT 'FULL'  -- "FULL" | "PARTIAL"
);

CREATE INDEX idx_tph_sector ON theme_phase_history(sector);
CREATE INDEX idx_tph_phase  ON theme_phase_history(sector, phase);
```

---

### Table 10: `archetype_outcome_distributions`

**Purpose:** Per-archetype, per-regime historical path curves. Source for path-percentile-based
edge consumption. Uses decay-weighted observations to prevent archetype drift.

**Writer:** Layer 4 Self-Audit, weekly recomputation from completed signal_births records.  
**Readers:** ELE Sub-A (EC_path); Layer 6 Adaptive Intelligence.

**Decay weighting rule (archetype drift prevention):**

| Observation age | Weight |
|---|---|
| 0–24 months | 1.00 |
| 24–48 months | 0.50 |
| 48+ months | 0.10 |

All statistics (medians, percentiles, win_rate) use weighted calculations. Simple averages
are never used.

```sql
CREATE TABLE archetype_outcome_distributions (
    archetype_id                TEXT    NOT NULL,
    archetype_version           INTEGER NOT NULL,
    regime                      TEXT    NOT NULL,
    computed_at                 DATE    NOT NULL,

    -- Sample quality
    observation_count_raw       INTEGER,
    observation_count_weighted  REAL,
    is_distribution_active      BOOLEAN DEFAULT FALSE,
    -- TRUE only when observation_count_weighted >= 20

    -- Median path at standard age milestones (in trading days)
    day_3_median  REAL,  day_3_p25  REAL,  day_3_p75  REAL,
    day_7_median  REAL,  day_7_p25  REAL,  day_7_p75  REAL,
    day_14_median REAL,  day_14_p25 REAL,  day_14_p75 REAL,
    day_21_median REAL,  day_21_p25 REAL,  day_21_p75 REAL,
    day_30_median REAL,  day_30_p25 REAL,  day_30_p75 REAL,

    -- Summary statistics
    win_rate                    REAL,
    median_final_move_pct       REAL,
    median_days_to_peak         REAL,
    path_shape                  TEXT,
    -- "EXPLOSIVE" | "SLOW_BUILDER" | "STAIRCASE" | "SMOOTH_DRIFT" | "UNKNOWN"
    half_life_trading_days      REAL,

    PRIMARY KEY (archetype_id, archetype_version, regime, computed_at)
);
```

---

### Table 11: `pending_adjustments`

**Purpose:** Layer 6 proposes parameter changes here. Changes to protected parameters
require human approval via Telegram `/approve` before activation.

**Writer:** Layer 6 Adaptive Intelligence.  
**Readers:** Telegram command handler; Layer 6 activation check before applying any adjustment.

```sql
CREATE TABLE pending_adjustments (
    adjustment_id       TEXT    PRIMARY KEY,    -- UUID
    proposed_at         DATETIME NOT NULL,
    adjustment_type     TEXT    NOT NULL,
    -- "TTL_CHANGE" | "HALF_LIFE_CHANGE" | "WEIGHT_CHANGE" |
    -- "THRESHOLD_CHANGE" | "ARCHETYPE_RETIRE"
    target_component    TEXT    NOT NULL,
    current_value       REAL,
    proposed_value      REAL,
    evidence_summary    TEXT,
    observation_count   INTEGER,

    requires_approval   BOOLEAN NOT NULL,
    status              TEXT    DEFAULT 'PENDING',
    -- "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED" | "AUTO_APPLIED"
    decided_at          DATETIME,
    decided_by          TEXT,
    expires_at          DATETIME            -- 14-day TTL on proposals
);
```

**Protected parameters (require_approval = TRUE):**
Risk rules, position sizing rules, kill switches, portfolio concentration limits, archetype retirement.

**Auto-applicable (require_approval = FALSE, but still logged):**
TTL adjustments within ±20%, half-life adjustments within ±20%, evidence weight adjustments within ±15%.

---

### Table 12: `oios_events`

**Purpose:** Formal event bus between OIOS and the Execution System. OIOS emits events;
the Execution System consumes them. The THESIS_INVALIDATED_WITH_POSITION event is the
critical path: it notifies the Execution System that a live position's thesis has collapsed.

**Writer:** ELE Sub-D, on every opportunity state change that has portfolio implications.  
**Readers:** Execution System (position management); Risk Monitor.

```sql
CREATE TABLE oios_events (
    event_id            TEXT    PRIMARY KEY,    -- UUID
    event_type          TEXT    NOT NULL,
    -- "OPPORTUNITY_ACTIVE"              -- opportunity entered ACTIVE
    -- "OPPORTUNITY_WATCHING"            -- opportunity retreated to WATCHING
    -- "OPPORTUNITY_INVALID"             -- opportunity expired (no position)
    -- "THESIS_INVALIDATED_WITH_POSITION"-- opportunity INVALID while position_exists=TRUE
    -- "POSITION_FULL_SUPPRESSED"        -- signal suppressed because position ≥ 80%
    -- "ADD_TO_POSITION"                 -- opportunity ACTIVE on partial position
    opportunity_id      TEXT    REFERENCES opportunities(opportunity_id),
    symbol              TEXT    NOT NULL,
    emitted_at          DATETIME NOT NULL,
    payload             TEXT,               -- JSON: os_score, conviction, invalidation_reason
    consumed_at         DATETIME,           -- populated by Execution System on receipt
    consumed_by         TEXT                -- "DECISION_ENGINE" | "RISK_MONITOR" | "MANUAL"
);

CREATE INDEX idx_evt_type       ON oios_events(event_type);
CREATE INDEX idx_evt_symbol     ON oios_events(symbol);
CREATE INDEX idx_evt_consumed   ON oios_events(consumed_at);
```

**THESIS_INVALIDATED_WITH_POSITION contract:**
When `opportunities.current_state` transitions to INVALID and `position_exists = TRUE`,
the ELE MUST emit a THESIS_INVALIDATED_WITH_POSITION event before the transition is
recorded. The Execution System MUST consume this event and determine whether to close,
reduce, or monitor the position. The event does not itself close the position —
that decision belongs to the operational risk system.

---

### View: `sector_opportunity_summary`

**Purpose:** Real-time aggregation of active conviction by sector. Consumed by the
Decision Engine to understand portfolio-level sector exposure. Computed on demand —
not materialized.

```sql
CREATE VIEW sector_opportunity_summary AS
SELECT
    o.sector,
    COUNT(*)                            AS active_opportunity_count,
    SUM(o.conviction_score)             AS total_sector_conviction,
    SUM(o.position_size_pct)            AS total_sector_position_pct,
    AVG(o.conviction_score)             AS avg_conviction,
    MAX(o.theme_phase_at_birth)         AS dominant_theme_phase,
    RANK() OVER (ORDER BY SUM(o.conviction_score) DESC) AS sector_conviction_rank
FROM opportunities o
WHERE o.current_state IN ('ACTIVE', 'WATCHING')
GROUP BY o.sector;
```

`sector_conviction_rank` is included in the OS output payload for every ACTIVE opportunity,
enabling the Decision Engine to contextualise individual opportunities within their sector's
overall portfolio weight. OIOS surfaces this information; it does not enforce concentration
limits — that is the operational risk system's responsibility.

---

## SECTION 5 — LAYER SPECIFICATIONS

### Layer 0 — Data Foundation

**Inputs:**
- yfinance OHLCV for 230 symbols + NIFTY/BANKNIFTY/INDIAVIX (daily)
- NSE BHAV files: delivery percentage per symbol (required before Phase B)
- NSE bulk/block deal CSV: sector-level capital flow proxy
- `daily_events` (BSE filings): Phase E0 prerequisite only — not available Phases A–D

**Sector mapping rule:** Each stock has exactly one primary sector. Conglomerates map to
dominant-revenue sector. Sector changes are versioned with effective dates. The Layer 1.5
participation computation counts each stock once in its primary sector only.

**Data quality gate:** Before any sector computation, count `stocks_with_data / stocks_total`.
If < 0.80, mark `data_quality = 'PARTIAL'` in `sector_conviction_daily` and suppress all
Layer 1.5 outputs for that sector on that date.

---

### Layer 1A — Confirmation DNA

**Question:** What has already begun moving?

**Signal type:** `"1A"` | **Minimum write threshold:** base_score > 4.0

**Example archetypes:** Sector Breakout Accelerator, 52-Week High Expansion,
Momentum Continuation, Results Follow-Through.

**Phase A defaults (until archetype_outcome_distributions is active):**
- `expected_move_pct = 8.0`, `expected_move_pct_source = "UNIVERSAL_DEFAULT_8PCT"`
- `expected_ttl_days = 10`

**Archetype retirement conditions (all required simultaneously):**
1. `observation_count_weighted ≥ 50`
2. `win_rate < 0.35` in archetype_outcome_distributions
3. Consistent underperformance across ≥ 2 distinct regime periods
4. Human approval via Telegram `/approve` required before retirement executes

---

### Layer 1B — Early Warning DNA

**Question:** What is quietly building before a public cause emerges?

**Signal type:** `"1B"` | **Minimum write threshold:** base_score > 4.0

**Example archetypes:** Quiet Accumulation, Sector Pre-Breakout,
Delivery Expansion, Low-Noise Strength Build.

**Phase A defaults:**
- `expected_move_pct = 8.0`, `expected_move_pct_source = "UNIVERSAL_DEFAULT_8PCT"`
- `expected_ttl_days = 18`

**BHAV delivery data gate:** The Delivery Expansion archetype requires daily NSE BHAV delivery
percentage data. This pipeline must be operational before Phase B begins.

---

### Layer 1.5 — Sector Conviction Engine

**Question:** What is the market collectively doing at the sector and theme level?

**Sub-A: Consensus Shift Intelligence**
Measures participation expansion, leadership rotation, theme emergence, belief shift.

**Sub-B: Capital Flow Intelligence**
Measures sector volume share and institutional accumulation proxies from NSE bulk/block
deal data. Data quality tiers:
- `"FULL"`: ≥ 3 bulk/block deals in sector within 5 trading days
- `"SPARSE"`: 1–2 deals
- `"UNAVAILABLE"`: 0 deals

When quality is SPARSE or UNAVAILABLE, `capital_flow_score = 0.5` (neutral).

Sector conviction score:
```
sector_conviction_score = 0.40 × capital_flow_score + 0.60 × consensus_shift_score
```
When capital_flow_data_quality = "UNAVAILABLE": pure consensus shift score (weight rescaled to 1.0).

**Sub-C: Theme Phase Engine**

| Phase | Detection Condition |
|---|---|
| EMERGENCE | participation_rate_5d rising, currently 30–50%, week-over-week delta > 0 |
| ACCELERATION | participation_rate_5d 50–65%, delta still positive |
| CONSENSUS | participation_rate_5d 65–80%, delta flat or decelerating |
| CROWDING | participation > 80% OR (high participation AND volume-per-participant declining) |
| EXHAUSTION | participation declining from peak AND volume asymmetric to downside |

**Sub-D: Theme Recurrence Engine**

Classifies each sector theme cycle as STRUCTURAL, TACTICAL, or HYBRID:

$$\text{structural\_score} = 0.375 \times \text{policy\_correlation} + 0.3125 \times \text{cycle\_duration\_pctile} + 0.3125 \times \text{amplitude\_stability}$$

The `institutional_flow_ratio` component (weight 0.0) is reserved for activation when
intraday institutional flow data becomes available. Not currently computable.

**Signal modifier by theme phase:**

| Signal Type | EMERGENCE | ACCELERATION | CONSENSUS | CROWDING | EXHAUSTION |
|---|---|---|---|---|---|
| Early Warning 1B | 1.40× | 1.30× | 1.00× | 0.50× | 0.10× |
| Confirmation 1A | 0.90× | 1.20× | 1.10× | 0.70× | 0.30× |

---

### Layer 2 — Cause Intelligence

**Question:** Why did buyers arrive?

**Activation gate:** Phase E1. Requires `daily_events` pipeline operational (Phase E0).

**During Phases A–D:** `C_additional = 1.0` (neutral multiplier) in OS formula.
Layers 2 and 3 contribute neither amplification nor suppression until implemented.

---

### Layer 3 — Cause Propagation

**Question:** Who benefits next?

**Activation gate:** Phase E1, AND Knowledge Graph V1 complete.

**Knowledge Graph V1** is a Phase E0 standalone dataset construction project (4–8 weeks).
It covers the 230-stock universe with supply chain relationships, policy co-beneficiary
clusters, and sector cluster definitions. It is a prerequisite for Layer 3, not a
component of it.

---

### Layer 4 — Self-Audit Intelligence

**Sub-C: Signal Birth Record Writer** — executes Day 1 of Phase A, before any other
Self-Audit functionality. Every signal evaluated by any Discovery layer is assessed
against the minimum threshold (base_score > 4.0). If met, a signal_births record
and an associated opportunity_signals linkage are created immediately.

**Sub-A: Missed Winner Analysis**
Identifies stocks with significant post-date moves (≥ +10% within 15 trading days)
that were never selected. Computes which detection rules would have captured them.

**Sub-B: Counterfactual Engine — four standard queries:**
- CF-1: TTL Sensitivity — would outcomes improve if TTL ×1.25?
- CF-2: RE Threshold Sensitivity — what happened to PASS_RE_LOW decisions? (CLEAN only)
- CF-3: Theme Phase Override — what happened to PASS_THEME_SUPPRESSED decisions?
- CF-4: Hold Duration Sensitivity — would 20% longer or shorter holds improve returns?

All CF queries use only `decision_log` records with `counterfactual_type = "CLEAN"`.

**5% Audit Paper Trade Mechanism:**
Each cycle, signals classified as INVALID are assessed: `hash(signal_id) % 20 == 0`
selects 5% for audit override. These are routed to the paper trading engine with
`is_audit_trade = TRUE`. No capital is at risk. Outcomes are evaluated separately
from regular paper trades. This mechanism is the primary detector of incorrect ELE suppression.

**Nightly retroactive job:**
Populates `price_5d_later`, `price_10d_later`, `price_20d_later`, `max_adverse_20d`,
`max_favorable_20d` in decision_log for records where these fields are NULL and
sufficient time has elapsed. Also classifies `counterfactual_type` for PASS records.

---

### Layer 5 — Edge Lifecycle Engine

**Sub-A: Remaining Edge (RE) Calculator**

$$RE = E_0 \times D_{time} \times (1 - EC_{path}) \times (1 - C_{crowding})$$

Where:
- $E_0$ = base_score at signal birth
- $D_{time}$ = $0.5^{\,age / half\_life(signal\_type,\,regime)}$
- $EC_{path}$ = edge consumed (percentile position in archetype historical path; linear ratio fallback in Phase A)
- $C_{crowding}$ = crowding proxy (abnormal post-signal volume / 3× average)

**Regime multipliers on half-life:**

| Signal Type | Bull | Range | Bear | Panic |
|---|---|---|---|---|
| 1B Early Warning | 1.8× | 0.5× | 0.7× | 0.1× |
| 1A Confirmation | 1.3× | 0.7× | 0.6× | 0.1× |
| 1.5 Consensus Shift | 2.0× | 0.4× | 0.5× | 0.0× |

**Opportunity Conviction Score:**

$$\text{conviction} = \sum_{i \in confirming} w_i \times RE_i \;-\; \sum_{j \in conflicting} w_j \times RE_j$$

**Opportunity Score (OS):**

$$OS = \frac{\text{conviction} \times M_{regime} \times M_{consensus\_delta} \times M_{theme\_phase} \times C_{additional}}{R_{execution}}$$

Where:
- $M_{consensus\_delta}$ = `sector_conviction_score_today / sector_conviction_score_at_birth`
  (captures change in sector context since opportunity was born)
- $C_{additional}$ = 1.0 during Phases A–D; derived from Layers 2+3 in Phase E1
- $R_{execution}$ = ATR-normalized stop distance

**Sub-B: Maturity Engine**

Three independent dimensions:

| Dimension | Metric | SEED | EMERGING | DEVELOPING | MATURE | LATE_STAGE |
|---|---|---|---|---|---|---|
| Temporal | age / effective_ttl | 0–20% | 20–40% | 40–60% | 60–80% | >80% |
| Path | EC percentile | 0–20% | 20–50% | 50–70% | 70–90% | >90% |
| Conviction | confirming sources count | 1 | 2 | 3 | 4 | 4+ declining |

`maturity_combined` = most conservative of the three dimensions.

**Sub-C: Velocity Engine**

$$\text{velocity\_3d} = \frac{RE_{today} - RE_{3\text{ days ago}}}{3}$$

Attribution of velocity to dominant cause:
- **THESIS_WORKING:** RE declining because EC_path rising (stock moving as expected)
- **REGIME_PRESSURE:** RE declining because regime multiplier dropped
- **CROWDING:** RE declining because C_crowding rising
- **MECHANICAL_DECAY:** RE declining from time decay only, all other factors stable

Attribution is approximate. When two factors change simultaneously, dominant cause =
the factor with the largest individual contribution to total RE change.

**Sub-D: State Machine** — defined in Section 3.

**Sub-E: Transition Probability Model**

Dormant per (archetype, regime) pair until `signal_state_transitions` contains
≥ 20 WATCHING→(ACTIVE|INVALID) sequences for that pair. Below threshold, regime-level
priors apply:

| Regime | P(WATCHING→ACTIVE) | P(WATCHING→INVALID) |
|---|---|---|
| BULL | 0.45 | 0.30 |
| RANGE | 0.28 | 0.48 |
| BEAR | 0.20 | 0.58 |
| PANIC | 0.08 | 0.80 |

**Open Position Interaction:**
ELE reads `opportunities.position_size_pct` before generating ACTIVE classification:

| position_size_pct | ELE action |
|---|---|
| 0.0 (no position) | Normal evaluation |
| 0.01–0.79 (partial) | ACTIVE allowed, flagged as ADD_TO_POSITION |
| ≥ 0.80 (full) | Forced to WATCHING with reason POSITION_FULL |

**Execution System write-back contract:**
The Execution System MUST update `opportunities.position_exists`,
`opportunities.position_size_pct`, and `opportunities.position_open_date` whenever:
- A trade is opened
- A position is partially closed
- A position is fully closed (set position_exists = FALSE, position_size_pct = 0.0)

Failure to maintain this contract causes ELE to generate duplicate entry signals on
fully-held positions.

---

### Layer 6 — Adaptive Intelligence

**Activation gate:** Phase D. Requires ≥ 30 complete signal lifecycles per (archetype, regime)
combination before any adjustment is proposed.

**Layer 6 adjustment guardrails (all mandatory):**
- TTL floor: 1A = 5 days, 1B = 8 days, 1.5 = 14 days (hard minimums, cannot be reduced)
- Maximum TTL change per adjustment cycle: ±20%
- Maximum evidence weight change per cycle: ±15%
- Maximum one adjustment per parameter per calendar quarter
- Minimum weighted observation count: 30 complete lifecycles per (archetype, regime)

**Archetype drift mitigation:**
Weekly recomputation of archetype_outcome_distributions using decay-weighted observations.
`observation_count_weighted` reflects effective sample size after decay.

**Human approval gate (Telegram interface):**
Proposals to `pending_adjustments` with `requires_approval = TRUE` require
`/approve <id>` command. Proposals not decided within 14 days expire automatically.
Telegram `/pending` lists all PENDING proposals with evidence summaries.

---

## SECTION 6 — EXECUTION SYSTEM INTERFACE

OIOS interfaces with the existing 17-layer operational system at two points:

**Outbound (OIOS → Execution):**
OIOS surfaces opportunities with `current_state = "ACTIVE"` and their OS scores.
The Decision Engine (Layer 10 in the operational system) receives the ACTIVE opportunity
list as an additional intelligence input alongside its existing signal sources.

**Inbound (Execution → OIOS):**
The Execution System writes position state back to `opportunities` on every position event.
This is a mandatory contract. The two fields are `position_exists` and `position_size_pct`.

---

## SECTION 7 — BUILD SEQUENCE

### Phase A0 — Core Data Model (first, isolated)

Build only the domain model. No scanners. No market data. No AI. No RE computation.

1. `trading_calendar` table populated for current + 2 forward years
2. `archetype_versions` table with initial version 1 for all archetypes
3. `opportunities` table
4. `opportunity_signals` table
5. `signal_births` table
6. `signal_state_transitions` table
7. `decision_log` table
8. Repository layer: CRUD operations only (create, read, update state)

**Phase A0 acceptance tests (all must pass before Phase A begins):**
- Create a synthetic opportunity, advance it through DISCOVERED→ACTIVE→WATCHING→ACTIVE→INVALID
- Verify bidirectional ACTIVE↔WATCHING transition records in signal_state_transitions
- Verify DISCOVERED→INVALID (NEVER_MATURED) when discovered_expires_at is reached
- Verify INVALID is terminal (no further state changes accepted)
- Attach CONFLICTING evidence signal, verify conviction_score decreases
- Verify opportunity creation deduplication rule (second signal on same symbol/direction attaches, not creates)

---

### Phase A — Data Collection and Layer 1A

1. Layer 0 data pipeline: OHLCV for 230 symbols + BHAV delivery + bulk/block deal CSV
2. Layer 1A detection, signal_births writer active from Day 1
3. Layer 4 Sub-C: Signal Birth Record Writer active from Day 1
4. Paper trading engine: add `is_audit_trade` flag
5. Simplified RE computation (Phase A defaults: universal 8% expected move)
6. decision_log capturing all ENTER and PASS decisions

**Phase A exit condition:** signal_births receiving writes daily. decision_log capturing all
decisions. No gaps in trading_calendar for the operating period.

---

### Phase B — Discovery Expansion

1. BHAV delivery pipeline confirmed operational (gates 1B Delivery Expansion archetype)
2. Layer 1B detection implemented
3. `sector_conviction_daily` and `theme_phase_history` tables created
4. Layer 1.5 Sub-A through Sub-D implemented
5. `archetype_outcome_distributions` table created (empty initially)
6. Layer 4 Sub-A Missed Winner Analysis activated
7. Nightly retroactive job populating decision_log outcome fields

**Phase B exit condition:** sector_conviction_daily has 30+ days of data.
theme_phase_history has ≥ 5 phase transition records.

---

### Phase C — Lifecycle Engine

1. Full ELE implemented: RE formula, maturity, velocity, state machine
2. State machine enforces bidirectional ACTIVE↔WATCHING, DISCOVERED expiry
3. `pending_adjustments` table created
4. Telegram `/approve`, `/reject`, `/pending` commands implemented
5. 5% audit paper trade override activated

**Phase C exit condition:** ELE classifying all live opportunities. Audit paper trades
executing and recording outcomes.

---

### Phase D — Learning Engine

1. Layer 6 Adaptive Intelligence with all guardrails
2. Layer 4 Sub-B Counterfactual Engine (CF-1 through CF-4)
3. Velocity attribution decomposition (after 60+ days of RE trajectory data)
4. archetype_outcome_distributions populates as observation counts reach minimums
5. Archetype drift decay-weighting recomputation scheduled weekly

**Phase D exit condition:** ≥ 1 archetype has `is_distribution_active = TRUE`.
≥ 1 TTL or half-life adjustment has been proposed and decided.

---

### Phase E0 — Prerequisite Construction (parallel to Phase D)

1. `daily_events` pipeline: BSE filing download, parse, normalize, store (2–3 weeks)
2. Knowledge Graph V1: company relationship dataset for 230-stock universe (4–8 weeks)
3. `company_relationships` table schema defined and populated

**Phase E0 exit condition:** daily_events has 30+ days of complete data.
Knowledge Graph V1 covers ≥ 200 of 230 universe stocks.

---

### Phase E1 — Advanced Intelligence

1. Layer 2 Cause Intelligence (requires Phase E0 daily_events)
2. Layer 3 Cause Propagation (requires Phase E0 Knowledge Graph V1)
3. C_additional activated in OS formula with calibration offset
4. Transition probability model activated per (archetype, regime) pairs with ≥ 20 observations

---

## SECTION 8 — SUCCESS CRITERIA

OIOS is functioning correctly at 3 months if it can answer all of the following queries
from its own data without external analysis:

**Operational queries (must be answerable from day 1 of Phase A):**
1. "Why was BEL.NS rejected on [date]?" → decision_log with suppression_reason
2. "How many signals had base_score between 4.0 and 6.0?" → signal_births query
3. "What is the current state of all WATCHING opportunities?" → opportunities query

**Learning queries (answerable after 3 months of Phase A):**
4. "How many WATCHING signals became ACTIVE?" → signal_state_transitions query
5. "Which archetype has the highest win rate?" → archetype_outcome_distributions query
6. "What RE threshold would have captured more winners?" → decision_log CF-2 analysis
7. "Which sector has the longest average EMERGENCE phase?" → theme_phase_history query

**Calibration queries (answerable after 6 months):**
8. "Is the 1B TTL of 18 days correct for Bull regime?" → archetype_outcome_distributions
9. "What percentage of CROWDING suppressions were correct?" → audit paper trade outcomes
10. "Which archetypes are showing degraded performance vs. 12 months ago?" →
    weighted vs. unweighted win_rate comparison

If any query in the operational set is unanswerable at 3 months, the instrumentation
is incomplete regardless of code quality.

---

## SECTION 9 — GOVERNANCE RULES

### Architecture Change Control
After the architecture freeze that follows Round-3 clearance:
- No new tables without a written finding describing the gap they resolve
- No schema changes to existing tables without documenting which component fails without the change
- No new layers without a formal assessment of effort vs. expected edge contribution
- Changes to Layer 5 RE formula require retrospective validation on paper trade history before deployment

### Layer 6 Boundaries
Layer 6 may adjust automatically (logged, no approval): TTL, half-life, evidence weights within guardrails.
Layer 6 may never adjust without approval: risk rules, position sizing, kill switches, portfolio limits, archetype retirement.
Layer 6 may never adjust: the RE formula structure, the OS formula structure, the state machine transitions.

### Data Retention
signal_births: permanent (required for lifetime calibration)
decision_log: permanent (required for counterfactual analysis)
signal_state_transitions: permanent (required for Markov model)
sector_conviction_daily: 5 years rolling
theme_phase_history: permanent
archetype_outcome_distributions: permanent (versioned)

---

*End of MAS v1.2*

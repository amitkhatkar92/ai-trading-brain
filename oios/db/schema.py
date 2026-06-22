"""
oios/db/schema.py
DDL for every OIOS table defined in MAS_v1.2.md Section 4.
Phase A0 subset: only tables required before any scanner logic is written.
"""

# ---------------------------------------------------------------------------
# Phase A0 tables (must exist before any other OIOS code runs)
# ---------------------------------------------------------------------------

TRADING_CALENDAR = """
CREATE TABLE IF NOT EXISTS trading_calendar (
    calendar_date   TEXT    PRIMARY KEY,    -- ISO-8601 YYYY-MM-DD
    is_trading_day  INTEGER NOT NULL,       -- 1 = trading day, 0 = holiday/weekend
    holiday_name    TEXT                    -- populated for non-trading days
);
"""

STOCK_SECTOR_MAP = """
CREATE TABLE IF NOT EXISTS stock_sector_map (
    symbol              TEXT    NOT NULL,
    primary_sector      TEXT    NOT NULL,
    sector_purity_score REAL    NOT NULL DEFAULT 1.0,
    effective_from      TEXT    NOT NULL,   -- ISO-8601 date
    effective_to        TEXT,               -- NULL = current mapping
    change_reason       TEXT,
    PRIMARY KEY (symbol, effective_from)
);
"""
STOCK_SECTOR_MAP_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_ssm_symbol ON stock_sector_map(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_ssm_sector ON stock_sector_map(primary_sector);",
]

ARCHETYPE_VERSIONS = """
CREATE TABLE IF NOT EXISTS archetype_versions (
    version_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    archetype_id        TEXT    NOT NULL,
    version_number      INTEGER NOT NULL,
    effective_from      TEXT    NOT NULL,   -- ISO-8601 date
    effective_to        TEXT,               -- NULL = currently active
    change_reason       TEXT,
    parameter_snapshot  TEXT,               -- JSON
    approved_by         TEXT    DEFAULT 'SYSTEM',
    UNIQUE(archetype_id, version_number)
);
"""

OPPORTUNITIES = """
CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id          TEXT    PRIMARY KEY,
    symbol                  TEXT    NOT NULL,
    direction               TEXT    NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
    sector                  TEXT    NOT NULL,

    created_at              TEXT    NOT NULL,   -- ISO-8601 date (NSE trading date)
    first_signal_id         TEXT,
    regime_at_birth         TEXT    NOT NULL,
    theme_phase_at_birth    TEXT,

    current_state           TEXT    NOT NULL DEFAULT 'DISCOVERED'
                                CHECK(current_state IN ('DISCOVERED','ACTIVE','WATCHING','INVALID')),

    birth_ttl_days          INTEGER NOT NULL,
    effective_ttl_days      INTEGER NOT NULL,
    age_trading_days        INTEGER DEFAULT 0,
    discovered_expires_at   TEXT    NOT NULL,   -- ISO-8601 date

    conviction_score        REAL    DEFAULT 0.0,
    confirming_count        INTEGER DEFAULT 0,
    conflicting_count       INTEGER DEFAULT 0,
    consecutive_conflict_days INTEGER DEFAULT 0,

    re_score                REAL,
    edge_consumed_pct       REAL    DEFAULT 0.0,
    maturity_combined       TEXT,
    velocity_3d             REAL,
    velocity_class          TEXT,

    position_exists         INTEGER DEFAULT 0,  -- SQLite boolean: 0/1
    position_size_pct       REAL    DEFAULT 0.0,
    position_open_date      TEXT,

    final_state             TEXT,
    invalidation_reason     TEXT,
    finalized_at            TEXT,
    trade_pnl_pct           REAL,
    is_audit_trade          INTEGER DEFAULT 0,

    created_at_ts           TEXT    DEFAULT (datetime('now')),
    last_updated_at         TEXT
);
"""
OPPORTUNITIES_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_opp_symbol    ON opportunities(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_opp_state     ON opportunities(current_state);",
    "CREATE INDEX IF NOT EXISTS idx_opp_sector    ON opportunities(sector);",
    "CREATE INDEX IF NOT EXISTS idx_opp_direction ON opportunities(symbol, direction, current_state);",
]

OPPORTUNITY_SIGNALS = """
CREATE TABLE IF NOT EXISTS opportunity_signals (
    opportunity_id      TEXT    NOT NULL REFERENCES opportunities(opportunity_id),
    signal_id           TEXT    NOT NULL REFERENCES signal_births(signal_id),
    signal_type         TEXT    NOT NULL CHECK(signal_type IN ('1A','1B','1.5','2','3')),
    signal_direction    TEXT    NOT NULL CHECK(signal_direction IN ('CONFIRMING','CONFLICTING','NEUTRAL')),
    evidence_weight     REAL    NOT NULL,
    added_at            TEXT    NOT NULL,   -- ISO-8601 date
    PRIMARY KEY (opportunity_id, signal_id)
);
"""
OPPORTUNITY_SIGNALS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_os_opp_id ON opportunity_signals(opportunity_id);",
    "CREATE INDEX IF NOT EXISTS idx_os_sig_id ON opportunity_signals(signal_id);",
]

SIGNAL_BIRTHS = """
CREATE TABLE IF NOT EXISTS signal_births (
    signal_id               TEXT    PRIMARY KEY,
    opportunity_id          TEXT    REFERENCES opportunities(opportunity_id),
    symbol                  TEXT    NOT NULL,
    archetype_id            TEXT    NOT NULL,
    archetype_version       INTEGER NOT NULL DEFAULT 1,
    signal_type             TEXT    NOT NULL CHECK(signal_type IN ('1A','1B','1.5','2','3')),

    detected_at             TEXT    NOT NULL,   -- ISO-8601 date
    birth_price             REAL    NOT NULL,
    base_score              REAL    NOT NULL,
    regime_at_birth         TEXT    NOT NULL,
    theme_phase_at_birth    TEXT,
    consensus_score_at_birth REAL,

    expected_move_pct       REAL    DEFAULT 8.0,
    expected_move_pct_source TEXT   DEFAULT 'UNIVERSAL_DEFAULT_8PCT',
    expected_ttl_days       INTEGER NOT NULL,
    expected_move_direction TEXT    NOT NULL CHECK(expected_move_direction IN ('LONG','SHORT')),

    current_state           TEXT    NOT NULL DEFAULT 'ACTIVE',
    current_price           REAL,
    age_trading_days        INTEGER DEFAULT 0,
    actual_move_pct         REAL    DEFAULT 0.0,
    edge_consumed_pct       REAL    DEFAULT 0.0,
    re_score                REAL,

    final_state             TEXT,
    final_age_trading_days  INTEGER,
    peak_move_pct           REAL,
    days_to_peak            INTEGER,
    trade_executed          INTEGER DEFAULT 0,
    trade_outcome_pct       REAL,

    created_at_ts           TEXT    DEFAULT (datetime('now')),
    last_updated_at         TEXT,
    invalidation_reason     TEXT
);
"""
SIGNAL_BIRTHS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_sb_opportunity ON signal_births(opportunity_id);",
    "CREATE INDEX IF NOT EXISTS idx_sb_symbol      ON signal_births(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_sb_archetype   ON signal_births(archetype_id);",
    "CREATE INDEX IF NOT EXISTS idx_sb_detected    ON signal_births(detected_at);",
]

SIGNAL_STATE_TRANSITIONS = """
CREATE TABLE IF NOT EXISTS signal_state_transitions (
    transition_id               TEXT    PRIMARY KEY,
    signal_id                   TEXT    NOT NULL REFERENCES signal_births(signal_id),
    opportunity_id              TEXT    REFERENCES opportunities(opportunity_id),
    from_state                  TEXT    NOT NULL,
    to_state                    TEXT    NOT NULL,
    transitioned_at             TEXT    NOT NULL,   -- ISO-8601 datetime
    trigger_cause               TEXT    NOT NULL,

    re_at_transition            REAL,
    age_trading_days            INTEGER,
    regime_at_transition        TEXT,
    theme_phase_at_transition   TEXT,
    consensus_score             REAL,
    edge_consumed_pct           REAL
);
"""
SIGNAL_STATE_TRANSITIONS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_sst_signal_id ON signal_state_transitions(signal_id);",
    "CREATE INDEX IF NOT EXISTS idx_sst_opp_id    ON signal_state_transitions(opportunity_id);",
    "CREATE INDEX IF NOT EXISTS idx_sst_from_to   ON signal_state_transitions(from_state, to_state);",
]

DECISION_LOG = """
CREATE TABLE IF NOT EXISTS decision_log (
    decision_id                 TEXT    PRIMARY KEY,
    opportunity_id              TEXT    NOT NULL REFERENCES opportunities(opportunity_id),
    signal_id                   TEXT    REFERENCES signal_births(signal_id),
    symbol                      TEXT    NOT NULL,
    decided_at                  TEXT    NOT NULL,   -- ISO-8601 datetime

    action                      TEXT    NOT NULL,

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

    price_5d_later              REAL,
    price_10d_later             REAL,
    price_20d_later             REAL,
    max_adverse_20d             REAL,
    max_favorable_20d           REAL,
    outcome_populated_at        TEXT,

    subsequent_opportunity_id   TEXT    REFERENCES opportunities(opportunity_id),
    subsequent_opportunity_pnl  REAL,
    counterfactual_type         TEXT
);
"""
DECISION_LOG_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_dl_opportunity ON decision_log(opportunity_id);",
    "CREATE INDEX IF NOT EXISTS idx_dl_action      ON decision_log(action);",
    "CREATE INDEX IF NOT EXISTS idx_dl_decided_at  ON decision_log(decided_at);",
    "CREATE INDEX IF NOT EXISTS idx_dl_symbol      ON decision_log(symbol);",
]

OIOS_EVENTS = """
CREATE TABLE IF NOT EXISTS oios_events (
    event_id            TEXT    PRIMARY KEY,
    event_type          TEXT    NOT NULL,
    opportunity_id      TEXT    REFERENCES opportunities(opportunity_id),
    symbol              TEXT    NOT NULL,
    emitted_at          TEXT    NOT NULL,   -- ISO-8601 datetime
    payload             TEXT,               -- JSON
    consumed_at         TEXT,
    consumed_by         TEXT
);
"""
OIOS_EVENTS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_evt_type     ON oios_events(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_evt_symbol   ON oios_events(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_evt_consumed ON oios_events(consumed_at);",
]

SECTOR_OPPORTUNITY_SUMMARY_VIEW = """
CREATE VIEW IF NOT EXISTS sector_opportunity_summary AS
SELECT
    o.sector,
    COUNT(*)                                                    AS active_opportunity_count,
    SUM(o.conviction_score)                                     AS total_sector_conviction,
    SUM(o.position_size_pct)                                    AS total_sector_position_pct,
    AVG(o.conviction_score)                                     AS avg_conviction,
    MAX(o.theme_phase_at_birth)                                 AS dominant_theme_phase,
    RANK() OVER (ORDER BY SUM(o.conviction_score) DESC)        AS sector_conviction_rank
FROM opportunities o
WHERE o.current_state IN ('ACTIVE', 'WATCHING')
GROUP BY o.sector;
"""

# ---------------------------------------------------------------------------
# Ordered creation sequence for Phase A0
# ---------------------------------------------------------------------------

PHASE_A0_DDL: list[str] = [
    # Independent tables first
    TRADING_CALENDAR,
    STOCK_SECTOR_MAP,
    *STOCK_SECTOR_MAP_IDX,
    ARCHETYPE_VERSIONS,
    # Root entity — signal_births must exist before opportunity_signals FK
    # but opportunities must exist before signal_births FK.
    # Create opportunities first (first_signal_id FK is deferred via nullable).
    OPPORTUNITIES,
    *OPPORTUNITIES_IDX,
    SIGNAL_BIRTHS,
    *SIGNAL_BIRTHS_IDX,
    OPPORTUNITY_SIGNALS,
    *OPPORTUNITY_SIGNALS_IDX,
    SIGNAL_STATE_TRANSITIONS,
    *SIGNAL_STATE_TRANSITIONS_IDX,
    DECISION_LOG,
    *DECISION_LOG_IDX,
    OIOS_EVENTS,
    *OIOS_EVENTS_IDX,
    SECTOR_OPPORTUNITY_SUMMARY_VIEW,
]

# ---------------------------------------------------------------------------
# Phase A tables (Layer 0 data foundation)
# ---------------------------------------------------------------------------

UNIVERSE_STOCKS = """
CREATE TABLE IF NOT EXISTS universe_stocks (
    symbol              TEXT    NOT NULL PRIMARY KEY,   -- e.g. "BEL.NS"
    company_name        TEXT    NOT NULL,
    sector              TEXT    NOT NULL,
    sector_purity_score REAL    NOT NULL DEFAULT 1.0,
    is_active           INTEGER NOT NULL DEFAULT 1, -- 1=active, 0=removed
    added_date          TEXT    NOT NULL,           -- ISO-8601 date first included
    removed_date        TEXT,                       -- ISO-8601 date removed, NULL if active
    removal_reason      TEXT
);
"""
UNIVERSE_STOCKS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_us_sector ON universe_stocks(sector);",
    "CREATE INDEX IF NOT EXISTS idx_us_active ON universe_stocks(is_active);",
]

OHLCV_DAILY = """
CREATE TABLE IF NOT EXISTS ohlcv_daily (
    symbol          TEXT    NOT NULL,
    trade_date      TEXT    NOT NULL,   -- ISO-8601 YYYY-MM-DD
    open            REAL    NOT NULL,
    high            REAL    NOT NULL,
    low             REAL    NOT NULL,
    close           REAL    NOT NULL,
    volume          REAL    NOT NULL,   -- REAL to handle large NSE volumes
    adjusted_close  REAL,              -- split/dividend adjusted; NULL until first corporate action
    data_source     TEXT    NOT NULL DEFAULT 'YFINANCE',
    fetched_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date)
);
"""
OHLCV_DAILY_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_date ON ohlcv_daily(symbol, trade_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_ohlcv_date        ON ohlcv_daily(trade_date);",
]

BHAV_DAILY = """
CREATE TABLE IF NOT EXISTS bhav_daily (
    symbol              TEXT    NOT NULL,
    trade_date          TEXT    NOT NULL,   -- ISO-8601 YYYY-MM-DD
    series              TEXT,              -- EQ, BE, etc.
    traded_quantity     REAL,
    deliverable_qty     REAL,
    delivery_pct        REAL,              -- deliverable / traded, 0.0–1.0
    data_source         TEXT    NOT NULL DEFAULT 'NSE_BHAV',
    fetched_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date)
);
"""
BHAV_DAILY_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_bhav_symbol_date ON bhav_daily(symbol, trade_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_bhav_date        ON bhav_daily(trade_date);",
]

BULK_BLOCK_DEALS = """
CREATE TABLE IF NOT EXISTS bulk_block_deals (
    deal_id             TEXT    PRIMARY KEY,    -- UUID generated at insert
    trade_date          TEXT    NOT NULL,       -- ISO-8601 YYYY-MM-DD
    symbol              TEXT    NOT NULL,
    deal_type           TEXT    NOT NULL CHECK(deal_type IN ('BULK','BLOCK')),
    client_name         TEXT,
    buy_sell            TEXT    CHECK(buy_sell IN ('B','S')),
    quantity            REAL,
    price               REAL,
    sector              TEXT,                  -- denormalised from universe_stocks at insert
    data_source         TEXT    NOT NULL DEFAULT 'NSE_BULK_BLOCK',
    fetched_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
BULK_BLOCK_DEALS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_bbd_symbol_date ON bulk_block_deals(symbol, trade_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_bbd_date        ON bulk_block_deals(trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_bbd_sector      ON bulk_block_deals(sector, trade_date);",
]

PHASE_A_DDL: list[str] = [
    UNIVERSE_STOCKS,
    *UNIVERSE_STOCKS_IDX,
    OHLCV_DAILY,
    *OHLCV_DAILY_IDX,
    BHAV_DAILY,
    *BHAV_DAILY_IDX,
    BULK_BLOCK_DEALS,
    *BULK_BLOCK_DEALS_IDX,
]

# ---------------------------------------------------------------------------
# Phase B tables (Layer 1.5 Sector Conviction Engine)
# ---------------------------------------------------------------------------

SECTOR_CONVICTION_DAILY = """
CREATE TABLE IF NOT EXISTS sector_conviction_daily (
    record_date                 TEXT    NOT NULL,   -- ISO-8601 YYYY-MM-DD
    sector                      TEXT    NOT NULL,

    -- Sub-A: Consensus Shift
    participation_rate_1d       REAL,
    participation_rate_5d       REAL,
    participation_expansion     REAL,   -- participation_rate_5d delta week-over-week
    rs_vs_market_20d            REAL,
    volume_trend_10d            REAL,
    consensus_score             REAL,   -- 0.0–10.0

    -- Sub-B: Capital Flow
    capital_flow_score          REAL    DEFAULT 0.5,   -- 0.0–1.0; 0.5 = neutral
    capital_flow_data_quality   TEXT,   -- "FULL" | "SPARSE" | "UNAVAILABLE"

    -- Combined
    sector_conviction_score     REAL,   -- 0.4×capital_flow + 0.6×consensus

    -- Sub-C: Theme Phase
    theme_phase                 TEXT,
    -- "EMERGENCE" | "ACCELERATION" | "CONSENSUS" | "CROWDING" | "EXHAUSTION"

    -- Data quality
    data_quality                TEXT    NOT NULL DEFAULT 'FULL',  -- "FULL" | "PARTIAL"
    stocks_with_data            INTEGER,
    stocks_total                INTEGER,

    PRIMARY KEY (record_date, sector)
);
"""

THEME_PHASE_HISTORY = """
CREATE TABLE IF NOT EXISTS theme_phase_history (
    record_id               TEXT    NOT NULL PRIMARY KEY,   -- UUID
    sector                  TEXT    NOT NULL,
    phase                   TEXT    NOT NULL
                                CHECK(phase IN ('EMERGENCE','ACCELERATION','CONSENSUS','CROWDING','EXHAUSTION')),
    entered_at              TEXT    NOT NULL,   -- ISO-8601 date
    exited_at               TEXT,              -- NULL if current phase
    duration_trading_days   INTEGER,           -- computed on exit
    regime_during           TEXT,
    peak_participation_rate REAL,
    amplitude_pct           REAL,              -- sector return during this phase
    avg_volume_ratio        REAL,
    data_quality            TEXT    NOT NULL DEFAULT 'FULL'  -- "FULL" | "PARTIAL"
);
"""
THEME_PHASE_HISTORY_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_tph_sector       ON theme_phase_history(sector);",
    "CREATE INDEX IF NOT EXISTS idx_tph_sector_phase ON theme_phase_history(sector, phase);",
]

PHASE_B_DDL: list[str] = [
    SECTOR_CONVICTION_DAILY,
    THEME_PHASE_HISTORY,
    *THEME_PHASE_HISTORY_IDX,
]


# ---------------------------------------------------------------------------
# Phase C tables (ELE — Edge Lifecycle Engine)
# ---------------------------------------------------------------------------

PENDING_ADJUSTMENTS = """
CREATE TABLE IF NOT EXISTS pending_adjustments (
    adjustment_id           TEXT    PRIMARY KEY,   -- UUID
    proposed_at             TEXT    NOT NULL,      -- ISO-8601 datetime
    archetype_id            TEXT    NOT NULL,
    regime                  TEXT,
    adjustment_type         TEXT    NOT NULL,
        -- "TTL_CHANGE" | "HALF_LIFE_CHANGE" | "WEIGHT_CHANGE"
    current_value           REAL    NOT NULL,
    proposed_value          REAL    NOT NULL,
    change_pct              REAL    NOT NULL,      -- (proposed - current) / current
    evidence_summary        TEXT,                  -- JSON
    observation_count       INTEGER,
    win_rate_current        REAL,
    win_rate_projected      REAL,
    status                  TEXT    NOT NULL DEFAULT 'PENDING',
        -- "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED"
    decided_at              TEXT,
    decision_note           TEXT,
    requires_approval       INTEGER NOT NULL DEFAULT 1,   -- 0=auto, 1=human
    expires_at              TEXT    NOT NULL               -- 14 days after proposed_at
);
"""
PENDING_ADJUSTMENTS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_pa_status      ON pending_adjustments(status);",
    "CREATE INDEX IF NOT EXISTS idx_pa_archetype   ON pending_adjustments(archetype_id, regime);",
]

PHASE_C_DDL: list[str] = [
    PENDING_ADJUSTMENTS,
    *PENDING_ADJUSTMENTS_IDX,
]


# ---------------------------------------------------------------------------
# Phase D tables (Learning Engine — Shadow Mode)
# ---------------------------------------------------------------------------

ARCHETYPE_OUTCOME_DISTRIBUTIONS = """
CREATE TABLE IF NOT EXISTS archetype_outcome_distributions (
    archetype_id                TEXT    NOT NULL,
    archetype_version           INTEGER NOT NULL DEFAULT 1,
    regime                      TEXT    NOT NULL,
    computed_at                 TEXT    NOT NULL,   -- ISO-8601 date

    -- Sample quality
    observation_count_raw       INTEGER NOT NULL DEFAULT 0,
    observation_count_weighted  REAL    NOT NULL DEFAULT 0.0,
    is_distribution_active      INTEGER NOT NULL DEFAULT 0,
    -- 1 only when observation_count_weighted >= 20 AND shadow_mode=0

    -- Median path at age milestones (trading days)
    day_3_median   REAL,  day_3_p25   REAL,  day_3_p75   REAL,
    day_7_median   REAL,  day_7_p25   REAL,  day_7_p75   REAL,
    day_14_median  REAL,  day_14_p25  REAL,  day_14_p75  REAL,
    day_21_median  REAL,  day_21_p25  REAL,  day_21_p75  REAL,
    day_30_median  REAL,  day_30_p25  REAL,  day_30_p75  REAL,

    -- Summary statistics
    win_rate                    REAL,
    median_final_move_pct       REAL,
    median_days_to_peak         REAL,
    path_shape                  TEXT,
    -- "EXPLOSIVE" | "SLOW_BUILDER" | "STAIRCASE" | "SMOOTH_DRIFT" | "UNKNOWN"
    half_life_trading_days      REAL,

    PRIMARY KEY (archetype_id, archetype_version, regime, computed_at)
);
"""
ARCHETYPE_OUTCOME_DISTRIBUTIONS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_aod_archetype ON archetype_outcome_distributions(archetype_id, regime);",
    "CREATE INDEX IF NOT EXISTS idx_aod_active    ON archetype_outcome_distributions(is_distribution_active);",
]

OPPORTUNITY_RE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS opportunity_re_snapshots (
    snapshot_id         TEXT    PRIMARY KEY,    -- UUID
    opportunity_id      TEXT    NOT NULL REFERENCES opportunities(opportunity_id),
    snapshot_date       TEXT    NOT NULL,       -- ISO-8601 date
    re_score            REAL,
    ec_path             REAL,
    c_crowding          REAL,
    regime              TEXT,
    age_trading_days    INTEGER,
    -- Velocity fields (populated day 4 onwards)
    velocity_3d         REAL,
    velocity_class      TEXT
);
"""
OPPORTUNITY_RE_SNAPSHOTS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_re_snap_opp  ON opportunity_re_snapshots(opportunity_id, snapshot_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_re_snap_date ON opportunity_re_snapshots(snapshot_date);",
]

OPPORTUNITY_DAILY_STATE_SNAPSHOT = """
CREATE TABLE IF NOT EXISTS opportunity_daily_state_snapshot (
    snapshot_date       TEXT    NOT NULL,
    current_state       TEXT    NOT NULL,
    opp_count           INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_date, current_state)
);
"""

TRANSITION_PROBABILITY_CACHE = """
CREATE TABLE IF NOT EXISTS transition_probability_cache (
    archetype_id            TEXT    NOT NULL,
    regime                  TEXT    NOT NULL,
    computed_at             TEXT    NOT NULL,
    observation_count       INTEGER NOT NULL DEFAULT 0,
    is_empirical            INTEGER NOT NULL DEFAULT 0,  -- 0=priors, 1=empirical
    p_watching_to_active    REAL    NOT NULL,
    p_watching_to_invalid   REAL    NOT NULL,
    p_active_to_watching    REAL    NOT NULL,
    p_active_to_invalid     REAL    NOT NULL,
    PRIMARY KEY (archetype_id, regime, computed_at)
);
"""
TRANSITION_PROBABILITY_CACHE_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_tpc_archetype ON transition_probability_cache(archetype_id, regime);",
]

PHASE_D_DDL: list[str] = [
    ARCHETYPE_OUTCOME_DISTRIBUTIONS,
    *ARCHETYPE_OUTCOME_DISTRIBUTIONS_IDX,
    OPPORTUNITY_RE_SNAPSHOTS,
    *OPPORTUNITY_RE_SNAPSHOTS_IDX,
    OPPORTUNITY_DAILY_STATE_SNAPSHOT,
    TRANSITION_PROBABILITY_CACHE,
    *TRANSITION_PROBABILITY_CACHE_IDX,
]


# ---------------------------------------------------------------------------
# Phase E0 tables (Knowledge Graph — event store + company relationships)
# ---------------------------------------------------------------------------

DAILY_EVENTS = """
CREATE TABLE IF NOT EXISTS daily_events (
    event_id            TEXT    PRIMARY KEY,            -- UUID
    symbol              TEXT    NOT NULL,               -- primary subject ticker
    event_date          TEXT    NOT NULL,               -- YYYY-MM-DD
    event_type          TEXT    NOT NULL,
        -- "EARNINGS" | "ORDER_WIN" | "POLICY" | "GUIDANCE"
        -- "CAPEX" | "PROMOTER" | "BULK" | "OTHER"
    headline            TEXT,
    magnitude           TEXT    NOT NULL DEFAULT 'MEDIUM',
        -- "HIGH" | "MEDIUM" | "LOW"
    direction           TEXT    NOT NULL DEFAULT 'NEUTRAL',
        -- "POSITIVE" | "NEGATIVE" | "NEUTRAL"
    source              TEXT,
    confidence          REAL    NOT NULL DEFAULT 0.5,   -- 0.0–1.0
    raw_data            TEXT,                           -- JSON blob
    normalized_at       TEXT,                           -- ISO-8601 datetime
    verified_at         TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
DAILY_EVENTS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_de_symbol      ON daily_events(symbol, event_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_de_event_type  ON daily_events(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_de_event_date  ON daily_events(event_date);",
]

COMPANY_RELATIONSHIPS = """
CREATE TABLE IF NOT EXISTS company_relationships (
    relationship_id     TEXT    PRIMARY KEY,            -- UUID
    from_symbol         TEXT    NOT NULL,               -- NSE ticker
    to_symbol           TEXT    NOT NULL,               -- NSE ticker
    relationship_type   TEXT    NOT NULL,
        -- "SUPPLIER" | "CUSTOMER" | "PEER" | "POLICY_BENEFICIARY" | "SECTOR_LINKAGE"
    strength            REAL    NOT NULL DEFAULT 0.5,   -- 0.0–1.0
    link_direction      TEXT    NOT NULL DEFAULT 'DIRECTIONAL',
        -- "DIRECTIONAL" | "BIDIRECTIONAL"
    source              TEXT,
    confidence          REAL    NOT NULL DEFAULT 0.5,
    last_verified       TEXT,                           -- ISO-8601 date
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
COMPANY_RELATIONSHIPS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_cr_from      ON company_relationships(from_symbol, is_active);",
    "CREATE INDEX IF NOT EXISTS idx_cr_to        ON company_relationships(to_symbol, is_active);",
    "CREATE INDEX IF NOT EXISTS idx_cr_type      ON company_relationships(relationship_type);",
]

KNOWLEDGE_GRAPH_METADATA = """
CREATE TABLE IF NOT EXISTS knowledge_graph_metadata (
    metadata_id         TEXT    PRIMARY KEY,            -- UUID
    entity_type         TEXT    NOT NULL,
        -- "COMPANY" | "SECTOR" | "THEME" | "POLICY"
    entity_id           TEXT    NOT NULL,               -- ticker / sector / theme id
    attribute           TEXT    NOT NULL,               -- "BUSINESS_SEGMENT", "MOAT", etc.
    value               TEXT,
    source              TEXT,
    confidence          REAL    NOT NULL DEFAULT 0.5,
    last_verified       TEXT,
    valid_from          TEXT,
    valid_to            TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
KNOWLEDGE_GRAPH_METADATA_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_kgm_entity ON knowledge_graph_metadata(entity_type, entity_id);",
    "CREATE INDEX IF NOT EXISTS idx_kgm_attr   ON knowledge_graph_metadata(attribute);",
]

EVENT_ENTITY_LINKS = """
CREATE TABLE IF NOT EXISTS event_entity_links (
    link_id             TEXT    PRIMARY KEY,            -- UUID
    event_id            TEXT    NOT NULL REFERENCES daily_events(event_id),
    entity_type         TEXT    NOT NULL,
        -- "COMPANY" | "SECTOR" | "THEME"
    entity_id           TEXT    NOT NULL,
    link_type           TEXT    NOT NULL,
        -- "PRIMARY" | "SECONDARY" | "DOWNSTREAM"
    impact_direction    TEXT    DEFAULT 'NEUTRAL',
        -- "POSITIVE" | "NEGATIVE" | "NEUTRAL"
    impact_magnitude    TEXT    DEFAULT 'MEDIUM',
        -- "HIGH" | "MEDIUM" | "LOW"
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
EVENT_ENTITY_LINKS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_eel_event   ON event_entity_links(event_id);",
    "CREATE INDEX IF NOT EXISTS idx_eel_entity  ON event_entity_links(entity_type, entity_id);",
]

PHASE_E0_DDL: list[str] = [
    DAILY_EVENTS,
    *DAILY_EVENTS_IDX,
    COMPANY_RELATIONSHIPS,
    *COMPANY_RELATIONSHIPS_IDX,
    KNOWLEDGE_GRAPH_METADATA,
    *KNOWLEDGE_GRAPH_METADATA_IDX,
    EVENT_ENTITY_LINKS,
    *EVENT_ENTITY_LINKS_IDX,
]


# ---------------------------------------------------------------------------
# Phase E1 tables (Cause + Propagation engines — Shadow Mode)
# ---------------------------------------------------------------------------

OPPORTUNITY_CAUSES = """
CREATE TABLE IF NOT EXISTS opportunity_causes (
    cause_id            TEXT    PRIMARY KEY,            -- UUID
    opportunity_id      TEXT    NOT NULL REFERENCES opportunities(opportunity_id),
    event_id            TEXT    REFERENCES daily_events(event_id),
    cause_type          TEXT    NOT NULL,
        -- "DIRECT" | "PROPAGATED" | "THEMATIC"
    cause_description   TEXT,
    confidence          REAL    NOT NULL DEFAULT 0.0,   -- 0.0–1.0
    rank                INTEGER NOT NULL DEFAULT 1,     -- 1 = primary
    computed_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
OPPORTUNITY_CAUSES_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_oc_opp   ON opportunity_causes(opportunity_id);",
    "CREATE INDEX IF NOT EXISTS idx_oc_event ON opportunity_causes(event_id);",
]

CAUSE_SCORES = """
CREATE TABLE IF NOT EXISTS cause_scores (
    score_id                TEXT    PRIMARY KEY,        -- UUID
    opportunity_id          TEXT    NOT NULL REFERENCES opportunities(opportunity_id),
    score_date              TEXT    NOT NULL,           -- ISO-8601 date
    cause_score             REAL,                       -- 0.0–10.0
    cause_count             INTEGER NOT NULL DEFAULT 0,
    primary_cause_type      TEXT,
    primary_cause_confidence REAL,
    evidence_summary        TEXT,                       -- JSON
    computed_at             TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (opportunity_id, score_date)
);
"""
CAUSE_SCORES_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_cs_opp   ON cause_scores(opportunity_id, score_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_cs_date  ON cause_scores(score_date);",
]

PROPAGATION_PATHS = """
CREATE TABLE IF NOT EXISTS propagation_paths (
    path_id             TEXT    PRIMARY KEY,            -- UUID
    source_event_id     TEXT    REFERENCES daily_events(event_id),
    source_symbol       TEXT    NOT NULL,
    target_symbol       TEXT    NOT NULL,
    path_hops           INTEGER NOT NULL DEFAULT 1,     -- 1 = direct relationship
    path_description    TEXT,                           -- JSON array of hop symbols
    relationship_chain  TEXT,                           -- JSON array of rel types
    strength_product    REAL    NOT NULL DEFAULT 0.5,   -- product of link strengths
    computed_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
PROPAGATION_PATHS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_pp_source ON propagation_paths(source_symbol);",
    "CREATE INDEX IF NOT EXISTS idx_pp_target ON propagation_paths(target_symbol);",
    "CREATE INDEX IF NOT EXISTS idx_pp_event  ON propagation_paths(source_event_id);",
]

PROPAGATION_SCORES = """
CREATE TABLE IF NOT EXISTS propagation_scores (
    prop_score_id           TEXT    PRIMARY KEY,        -- UUID
    opportunity_id          TEXT    NOT NULL REFERENCES opportunities(opportunity_id),
    source_opportunity_id   TEXT    REFERENCES opportunities(opportunity_id),
    source_event_id         TEXT    REFERENCES daily_events(event_id),
    path_id                 TEXT    REFERENCES propagation_paths(path_id),
    propagation_score       REAL,                       -- 0.0–10.0
    decay_factor            REAL    NOT NULL DEFAULT 1.0,
    score_date              TEXT    NOT NULL,           -- ISO-8601 date
    computed_at             TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (opportunity_id, source_event_id, score_date)
);
"""
PROPAGATION_SCORES_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_ps_opp    ON propagation_scores(opportunity_id);",
    "CREATE INDEX IF NOT EXISTS idx_ps_source ON propagation_scores(source_opportunity_id);",
]

SHADOW_CAUSE_OUTCOMES = """
CREATE TABLE IF NOT EXISTS shadow_cause_outcomes (
    outcome_id          TEXT    PRIMARY KEY,            -- UUID
    opportunity_id      TEXT    NOT NULL REFERENCES opportunities(opportunity_id),
    outcome_date        TEXT    NOT NULL,               -- ISO-8601 date recorded
    cause_score         REAL,
    propagation_score   REAL,
    shadow_os           REAL,    -- what OS would have been with E1 active
    live_os             REAL,    -- actual OS from Phase C
    actual_return_pct   REAL,    -- populated after opportunity closes
    days_to_peak        INTEGER,
    final_state         TEXT,    -- terminal state from signal_births
    recorded_at         TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (opportunity_id, outcome_date)
);
"""
SHADOW_CAUSE_OUTCOMES_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_sco_opp  ON shadow_cause_outcomes(opportunity_id);",
    "CREATE INDEX IF NOT EXISTS idx_sco_date ON shadow_cause_outcomes(outcome_date);",
]

PHASE_E1_DDL: list[str] = [
    OPPORTUNITY_CAUSES,
    *OPPORTUNITY_CAUSES_IDX,
    CAUSE_SCORES,
    *CAUSE_SCORES_IDX,
    PROPAGATION_PATHS,
    *PROPAGATION_PATHS_IDX,
    PROPAGATION_SCORES,
    *PROPAGATION_SCORES_IDX,
    SHADOW_CAUSE_OUTCOMES,
    *SHADOW_CAUSE_OUTCOMES_IDX,
]


# ---------------------------------------------------------------------------
# Phase F tables (Market Research Engine — read-only from A–E, research-only)
# ---------------------------------------------------------------------------
# Phase F NEVER writes to any A–E table.  All five tables below are
# self-contained; they have no FK references into A–E to preserve isolation.
# ---------------------------------------------------------------------------

MARKET_LEADERS_DAILY = """
CREATE TABLE IF NOT EXISTS market_leaders_daily (
    leader_id           TEXT    PRIMARY KEY,            -- UUID  e.g. "LDR_20260619_BEL_W_01"
    trade_date          TEXT    NOT NULL,               -- ISO-8601 YYYY-MM-DD
    symbol              TEXT    NOT NULL,               -- NSE ticker (matches universe_stocks)
    leader_type         TEXT    NOT NULL
                            CHECK(leader_type IN ('WINNER','LOSER')),
    rank_position       INTEGER NOT NULL,               -- 1 = best/worst on the day
    day_return_pct      REAL    NOT NULL,               -- (close - prev_close) / prev_close × 100
    volume_ratio        REAL,                           -- today_vol / 20d_avg_vol
    sector              TEXT    NOT NULL,               -- denormalised at capture time
    theme_phase         TEXT,                           -- from sector_conviction_daily
    regime              TEXT,                           -- market regime at capture time
    captured_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
MARKET_LEADERS_DAILY_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_mld_date       ON market_leaders_daily(trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_mld_symbol     ON market_leaders_daily(symbol, trade_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_mld_type_date  ON market_leaders_daily(leader_type, trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_mld_sector     ON market_leaders_daily(sector, trade_date);",
]

MARKET_LEADER_FEATURES = """
CREATE TABLE IF NOT EXISTS market_leader_features (
    feature_id          TEXT    PRIMARY KEY,            -- UUID
    leader_id           TEXT    NOT NULL,               -- → market_leaders_daily.leader_id
    feature_name        TEXT    NOT NULL,               -- e.g. "above_20dma", "volume_ratio"
    feature_value       REAL,                           -- numeric value; NULL if not computable
    captured_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
MARKET_LEADER_FEATURES_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_mlf_leader   ON market_leader_features(leader_id);",
    "CREATE INDEX IF NOT EXISTS idx_mlf_name     ON market_leader_features(feature_name);",
    "CREATE INDEX IF NOT EXISTS idx_mlf_ldr_name ON market_leader_features(leader_id, feature_name);",
]

MARKET_LEADER_OUTCOMES = """
CREATE TABLE IF NOT EXISTS market_leader_outcomes (
    leader_id           TEXT    PRIMARY KEY,            -- → market_leaders_daily.leader_id

    -- Forward returns (populated by outcome_tracker as data becomes available)
    return_1d           REAL,                           -- close[+1] / close[0] - 1, as pct
    return_3d           REAL,
    return_5d           REAL,
    return_10d          REAL,
    return_20d          REAL,

    -- Path extremes within 20-day window
    max_favorable       REAL,                           -- best intraday-close pct gain in window
    max_adverse         REAL,                           -- worst intraday-close pct loss in window

    -- Outcome class (derived from return pattern)
    outcome_class       TEXT
        CHECK(outcome_class IN ('ONE_DAY_SPIKE','SHORT_RUNNER',
                                'MULTI_WEEK_WINNER','LONG_TREND_WINNER','UNKNOWN')),

    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
MARKET_LEADER_OUTCOMES_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_mlo_class ON market_leader_outcomes(outcome_class);",
]

MARKET_RESEARCH_CONTROLS = """
CREATE TABLE IF NOT EXISTS market_research_controls (
    control_id          TEXT    PRIMARY KEY,            -- UUID
    trade_date          TEXT    NOT NULL,               -- same date as matched leader
    symbol              TEXT    NOT NULL,               -- control stock symbol
    fingerprint_hash    TEXT    NOT NULL,               -- SHA256 of feature fingerprint
    matched_leader_id   TEXT    NOT NULL,               -- → market_leaders_daily.leader_id

    -- Control stock multi-horizon outcomes (populated by outcome_tracker)
    return_1d           REAL,
    return_3d           REAL,
    return_5d           REAL,
    return_10d          REAL,
    return_20d          REAL,

    -- Outcome classification for control
    outcome_class       TEXT
        CHECK(outcome_class IN ('ONE_DAY_SPIKE','SHORT_RUNNER',
                                'MULTI_WEEK_WINNER','LONG_TREND_WINNER','UNKNOWN')),

    captured_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
MARKET_RESEARCH_CONTROLS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_mrc_leader  ON market_research_controls(matched_leader_id);",
    "CREATE INDEX IF NOT EXISTS idx_mrc_symbol  ON market_research_controls(symbol, trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_mrc_hash    ON market_research_controls(fingerprint_hash);",
    "CREATE INDEX IF NOT EXISTS idx_mrc_date    ON market_research_controls(trade_date);",
]

FAILURE_ATTRIBUTION = """
CREATE TABLE IF NOT EXISTS failure_attribution (
    failure_id          TEXT    PRIMARY KEY,            -- UUID
    symbol              TEXT    NOT NULL,               -- stock that failed to follow through
    trade_date          TEXT    NOT NULL,               -- date of expected move
    matched_leader_id   TEXT,                           -- if matched to a specific leader
    candidate_reason    TEXT    NOT NULL,
        -- "CROWDING" | "WEAK_BREADTH" | "LOW_DELIVERY" | "NO_FLOW"
        -- "NEGATIVE_EARNINGS" | "SECTOR_DIVERGENCE" | "MARKET_WEAKNESS"
    confidence          REAL    NOT NULL DEFAULT 0.0,   -- 0.0–1.0
    supporting_evidence TEXT,                           -- JSON key-value pairs
    recorded_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
FAILURE_ATTRIBUTION_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_fa_symbol  ON failure_attribution(symbol, trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_fa_reason  ON failure_attribution(candidate_reason);",
    "CREATE INDEX IF NOT EXISTS idx_fa_leader  ON failure_attribution(matched_leader_id);",
    "CREATE INDEX IF NOT EXISTS idx_fa_date    ON failure_attribution(trade_date);",
]

FEATURE_DIFFERENTIALS = """
CREATE TABLE IF NOT EXISTS feature_differentials (
    differential_id     TEXT    PRIMARY KEY,            -- UUID / deterministic ID
    trade_date          TEXT    NOT NULL,               -- ISO-8601 YYYY-MM-DD
    winner_symbol       TEXT    NOT NULL,               -- winning stock
    control_symbol      TEXT    NOT NULL,               -- similar but non-winning stock
    matched_leader_id   TEXT    NOT NULL,               -- Phase F: market_leaders_daily.leader_id
    control_id          TEXT    NOT NULL,               -- Phase F: market_research_controls.control_id
    similarity_score    REAL    NOT NULL,               -- 0.0–1.0 (higher = more similar setup)
    differing_features  TEXT,                           -- JSON array:
        -- [{feature, winner_val, control_val, delta, abs_delta}, ...]
        -- sorted by abs_delta desc (biggest differentiators first)
    outcome_gap_1d      REAL,                           -- winner_ret_1d  - control_ret_1d
    outcome_gap_3d      REAL,
    outcome_gap_5d      REAL,
    outcome_gap_20d     REAL,
    computed_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""
FEATURE_DIFFERENTIALS_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_fd_date          ON feature_differentials(trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_fd_winner        ON feature_differentials(winner_symbol, trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_fd_control       ON feature_differentials(control_symbol, trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_fd_similarity    ON feature_differentials(similarity_score DESC);",
    "CREATE INDEX IF NOT EXISTS idx_fd_leader        ON feature_differentials(matched_leader_id);",
]

PHASE_F_DDL: list[str] = [
    MARKET_LEADERS_DAILY,
    *MARKET_LEADERS_DAILY_IDX,
    MARKET_LEADER_FEATURES,
    *MARKET_LEADER_FEATURES_IDX,
    MARKET_LEADER_OUTCOMES,
    *MARKET_LEADER_OUTCOMES_IDX,
    MARKET_RESEARCH_CONTROLS,
    *MARKET_RESEARCH_CONTROLS_IDX,
    FAILURE_ATTRIBUTION,
    *FAILURE_ATTRIBUTION_IDX,
    FEATURE_DIFFERENTIALS,
    *FEATURE_DIFFERENTIALS_IDX,
]

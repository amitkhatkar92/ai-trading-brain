# DNA Repository Schema
## R-013: SQLite Table Definitions, Constraints, and Indexes

**Schema Version:** 1  
**Engine:** SQLite 3 (WAL mode)  
**Database file:** `data/mls/institutional_dna.db`

---

## 1. Table: `dna`

Primary storage for all InstitutionalDNA records (one row per version).

```sql
CREATE TABLE IF NOT EXISTS dna (
    id                   TEXT    NOT NULL,
    version              INTEGER NOT NULL,
    feature_name         TEXT    NOT NULL,
    direction            TEXT    NOT NULL,
    category             TEXT    NOT NULL,
    lifecycle            TEXT    NOT NULL,
    consensus_score      REAL    NOT NULL DEFAULT 0.0,
    confidence           REAL    NOT NULL DEFAULT 0.0,
    effect_size          REAL    NOT NULL DEFAULT 0.0,
    regime_consistency   REAL    NOT NULL DEFAULT 0.0,
    sector_consistency   REAL    NOT NULL DEFAULT 0.0,
    temporal_stability   REAL    NOT NULL DEFAULT 0.0,
    replication_frequency REAL   NOT NULL DEFAULT 0.0,
    evidence_count       INTEGER NOT NULL DEFAULT 0,
    regime_counts        TEXT    NOT NULL DEFAULT '{}',
    last_seen            TEXT    NOT NULL DEFAULT '',
    study_id             TEXT    NOT NULL DEFAULT '',
    source               TEXT    NOT NULL DEFAULT '',
    created_at           TEXT    NOT NULL,
    updated_at           TEXT    NOT NULL,
    is_current           INTEGER NOT NULL DEFAULT 0,
    metadata             TEXT    NOT NULL DEFAULT '{}',
    PRIMARY KEY (id, version)
)
```

**Notes:**
- `(id, version)` is the compound primary key
- `is_current = 1` only on the latest version; `is_current = 0` on all previous
- `regime_counts` and `metadata` are JSON-serialised dicts stored as TEXT
- `created_at` is always copied from version=1 row on every subsequent update
- `lifecycle` values: DISCOVERED, REPLICATED, VERIFIED, INSTITUTIONAL, WEAKENING, DRIFTING, RETIRED

### Indexes on `dna`

```sql
CREATE INDEX IF NOT EXISTS idx_dna_current  ON dna (id, is_current);
CREATE INDEX IF NOT EXISTS idx_dna_lifecycle ON dna (lifecycle, is_current);
CREATE INDEX IF NOT EXISTS idx_dna_feature  ON dna (feature_name, is_current);
CREATE INDEX IF NOT EXISTS idx_dna_category ON dna (category,     is_current);
```

---

## 2. Table: `dna_evidence`

Statistical evidence records supporting a DNA version.

```sql
CREATE TABLE IF NOT EXISTS dna_evidence (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    dna_id           TEXT    NOT NULL,
    dna_version      INTEGER NOT NULL,
    study_id         TEXT    NOT NULL,
    source           TEXT    NOT NULL DEFAULT '',
    sample_size      INTEGER NOT NULL DEFAULT 0,
    effect_size      REAL    NOT NULL DEFAULT 0.0,
    confidence       REAL    NOT NULL DEFAULT 0.0,
    regime           TEXT    NOT NULL DEFAULT '',
    sector           TEXT    NOT NULL DEFAULT '',
    observation_date TEXT    NOT NULL DEFAULT '',
    p_value          REAL,
    ci_low           REAL,
    ci_high          REAL,
    created_at       TEXT    NOT NULL,
    metadata         TEXT    NOT NULL DEFAULT '{}'
)
```

**Notes:**
- `p_value`, `ci_low`, `ci_high` are nullable (studies may not provide all statistics)
- Foreign key relationship: `dna_id` + `dna_version` → `dna(id, version)`

### Index on `dna_evidence`

```sql
CREATE INDEX IF NOT EXISTS idx_evidence_dna ON dna_evidence (dna_id, dna_version);
```

---

## 3. Table: `dna_history`

Time-series confidence/stability tracking for a DNA.

```sql
CREATE TABLE IF NOT EXISTS dna_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    dna_id          TEXT    NOT NULL,
    history_date    TEXT    NOT NULL,
    confidence      REAL    NOT NULL DEFAULT 0.0,
    consensus_score REAL    NOT NULL DEFAULT 0.0,
    drift           REAL    NOT NULL DEFAULT 0.0,
    stability       REAL    NOT NULL DEFAULT 0.0,
    relevance       REAL    NOT NULL DEFAULT 0.0,
    lifecycle       TEXT    NOT NULL DEFAULT '',
    version_at_time INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL
)
```

**Notes:**
- `history_date` is the market date of the snapshot (ISO 8601 string)
- `version_at_time` records which DNA version was current when the snapshot was taken
- Used to reconstruct time-series confidence/stability charts

### Index on `dna_history`

```sql
CREATE INDEX IF NOT EXISTS idx_history_dna  ON dna_history (dna_id, history_date);
```

---

## 4. Table: `dna_context`

Market context snapshots associated with a DNA version.

```sql
CREATE TABLE IF NOT EXISTS dna_context (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    dna_id                TEXT    NOT NULL,
    dna_version           INTEGER NOT NULL,
    regime                TEXT    NOT NULL DEFAULT '',
    volatility            REAL    NOT NULL DEFAULT 0.0,
    breadth               REAL    NOT NULL DEFAULT 0.0,
    sector                TEXT    NOT NULL DEFAULT '',
    liquidity             REAL    NOT NULL DEFAULT 0.0,
    institutional         REAL    NOT NULL DEFAULT 0.0,
    historical_similarity REAL    NOT NULL DEFAULT 0.0,
    context_date          TEXT    NOT NULL DEFAULT '',
    created_at            TEXT    NOT NULL
)
```

**Notes:**
- Context snapshots record the market conditions at the time of observation
- Multiple context snapshots per DNA version are allowed
- `institutional` field is the CDS institutional activity score

### Index on `dna_context`

```sql
CREATE INDEX IF NOT EXISTS idx_context_dna ON dna_context (dna_id, dna_version);
```

---

## 5. Table: `audit_log`

Immutable write record for every mutation.

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    operation      TEXT    NOT NULL,
    dna_id         TEXT    NOT NULL,
    version_before INTEGER NOT NULL DEFAULT 0,
    version_after  INTEGER NOT NULL DEFAULT 0,
    operator       TEXT    NOT NULL DEFAULT 'system',
    study_id       TEXT    NOT NULL DEFAULT '',
    reason         TEXT    NOT NULL DEFAULT '',
    timestamp      TEXT    NOT NULL
)
```

**Notes:**
- `operation` values: CREATED, UPDATED, RETIRED
- `version_before = 0` on CREATED (no prior version)
- Never deleted — the IDR provides complete audit history for governance
- `operator` is the human or system component that triggered the write

### Index on `audit_log`

```sql
CREATE INDEX IF NOT EXISTS idx_audit_dna ON audit_log (dna_id, timestamp);
```

---

## 6. Table: `schema_version`

Migration tracking.

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT ''
)
```

**Current rows:**

| version | description |
|---|---|
| 1 | Initial schema — dna, dna_evidence, dna_history, dna_context, audit_log |

---

## 7. SQLite Settings

The IDR enables the following PRAGMA settings on every connection:

```sql
PRAGMA journal_mode=WAL;       -- concurrent readers
PRAGMA foreign_keys=ON;        -- relational integrity
```

Row factory is set to `sqlite3.Row` (dict-like access by column name).

---

## 8. WAL and Concurrency

- Write operations use `BEGIN IMMEDIATE` → acquired exclusively at begin time
- Read operations use the default `BEGIN DEFERRED`
- `RLock` at the Python layer serialises concurrent writers
- Backup uses the native SQLite Online Backup API (`connection.backup(dst)`)
  which is safe to run while other threads read/write

---

## 9. Schema Evolution Rules

| Change Type | Method | Notes |
|---|---|---|
| Add nullable column | `ALTER TABLE t ADD COLUMN c TYPE DEFAULT val` | Safe; old rows get default |
| Add index | `CREATE INDEX IF NOT EXISTS` | Safe; no data migration needed |
| Rename column | Not supported in SQLite | Recreate table |
| Remove column | Not supported in SQLite | Leave column, ignore in code |
| New table | `CREATE TABLE IF NOT EXISTS` | Safe; existing data unaffected |

Always:
1. Increment `SCHEMA_VERSION` in `IDRRepository`
2. Insert a row into `schema_version` with description
3. If `idr_backup_on_schema_change = True` in config, backup before migration

# DNA Repository API Reference
## R-013: IDRRepository Public Interface

**Module:** `market_learning.idr_repository`  
**Class:** `IDRRepository`

---

## Instantiation

```python
from market_learning import IDRRepository, MLSConfig

# Default (uses config default path: data/mls/institutional_dna.db)
repo = IDRRepository()

# Custom path
repo = IDRRepository(db_path="path/to/custom.db")

# Custom config
config = MLSConfig(idr_wal_mode=True, idr_default_operator="research")
repo = IDRRepository(config=config)
```

The database is created automatically on first use.  
The schema is initialised on every construction call (idempotent).

---

## Write API

### `save(dna, study_id="", operator="system") -> DNARevision`

Persist an InstitutionalDNA. Automatically determines CREATED vs UPDATED.

```python
from market_learning import InstitutionalDNA, IDRRepository

repo = IDRRepository()
dna = InstitutionalDNA(
    id="DNA-VOLUME-SURGE-BULL",
    feature_name="volume_surge",
    direction="BULLISH",
    category="VOLUME",
    lifecycle="DISCOVERED",
    confidence=0.72,
    consensus_score=0.68,
    effect_size=0.55,
)
revision = repo.save(dna, study_id="STUDY-001", operator="consensus_engine")
# revision.operation == "CREATED"
# revision.version == 1
```

- If `dna.id` is unknown → creates version 1, `operation = "CREATED"`
- If `dna.id` exists → creates next version, `operation = "UPDATED"`
- Returns `DNARevision` with full versioning metadata
- `created_at` is preserved across all update versions

---

### `update(dna_id, updates, reason="", study_id="", operator="system") -> DNARevision`

Apply a partial update dict to the current DNA record.

```python
revision = repo.update(
    "DNA-VOLUME-SURGE-BULL",
    updates={"lifecycle": "INSTITUTIONAL", "confidence": 0.85},
    reason="Promoted after 10 replications",
    study_id="STUDY-007",
    operator="consensus_engine",
)
# revision.operation == "UPDATED"
# revision.version == 2
```

- `updates` is a `dict[str, Any]` of field names to new values
- Invalid field names raise `IDRError`
- Protected fields (`id`, `version`, `created_at`, `is_current`) are silently ignored
- All other fields in `updates` are applied

---

### `retire(dna_id, reason="", operator="system") -> DNARevision`

Retire a DNA record (sets `lifecycle = "RETIRED"`).

```python
revision = repo.retire(
    "DNA-VOLUME-SURGE-BULL",
    reason="Consistently underperforming after BEAR regime shift",
    operator="risk_guardian",
)
# revision.operation == "RETIRED"
```

- Creates a new version with `lifecycle = "RETIRED"`
- Retired DNA is excluded from `list_active()`
- Retired DNA is included in `list_retired()`
- Retirement can be undone via `update(id, {"lifecycle": "WEAKENING"})`

---

### `add_evidence(dna_id, ev: DNAEvidence)`

Store a statistical evidence record for a DNA.

```python
from market_learning import DNAEvidence

ev = DNAEvidence(
    dna_id="DNA-VOLUME-SURGE-BULL",
    dna_version=1,
    study_id="STUDY-002",
    source="discovery",
    sample_size=120,
    effect_size=0.61,
    confidence=0.74,
    regime="BULL",
    sector="TECH",
    observation_date="2026-07-15",
    p_value=0.03,
    ci_low=0.45,
    ci_high=0.77,
)
repo.add_evidence("DNA-VOLUME-SURGE-BULL", ev)
```

- `p_value`, `ci_low`, `ci_high` are optional (can be `None`)
- Raises `IDRNotFoundError` if the DNA does not exist

---

### `add_history(dna_id, hist: DNAHistory)`

Store a time-series history point.

```python
from market_learning import DNAHistory

hist = DNAHistory(
    dna_id="DNA-VOLUME-SURGE-BULL",
    history_date="2026-07-20",
    confidence=0.74,
    consensus_score=0.71,
    drift=0.03,
    stability=0.88,
    relevance=0.91,
    lifecycle="INSTITUTIONAL",
    version_at_time=2,
)
repo.add_history("DNA-VOLUME-SURGE-BULL", hist)
```

---

### `add_context(dna_id, ctx: DNAContext)`

Store a market context snapshot.

```python
from market_learning import DNAContext

ctx = DNAContext(
    dna_id="DNA-VOLUME-SURGE-BULL",
    dna_version=2,
    regime="BULL",
    volatility=0.15,
    breadth=0.62,
    sector="TECH",
    liquidity=0.80,
    institutional=0.73,
    historical_similarity=0.68,
    context_date="2026-07-20",
)
repo.add_context("DNA-VOLUME-SURGE-BULL", ctx)
```

---

## Read API

### `get(dna_id) -> InstitutionalDNA`

Fetch the latest version of a DNA record.

```python
dna = repo.get("DNA-VOLUME-SURGE-BULL")
# dna.version == latest version
# dna.is_current == True (always)
```

- Raises `IDRNotFoundError` if the DNA does not exist

---

### `get_version(dna_id, version) -> InstitutionalDNA`

Fetch a specific historical version of a DNA record.

```python
dna_v1 = repo.get_version("DNA-VOLUME-SURGE-BULL", 1)
# dna_v1.confidence == original confidence at creation
```

- Raises `IDRNotFoundError` if the DNA does not exist
- Raises `IDRVersionError` if the requested version does not exist

---

### `history(dna_id) -> List[DNAHistory]`

Fetch all history points ordered by date ascending.

```python
points = repo.history("DNA-VOLUME-SURGE-BULL")
for p in points:
    print(p.history_date, p.confidence, p.lifecycle)
```

---

### `evidence(dna_id) -> List[DNAEvidence]`

Fetch all evidence records for a DNA.

```python
records = repo.evidence("DNA-VOLUME-SURGE-BULL")
for ev in records:
    print(ev.study_id, ev.sample_size, ev.effect_size)
```

---

### `contexts(dna_id) -> List[DNAContext]`

Fetch all context snapshots for a DNA.

---

### `search(feature_name=None, category=None, lifecycle=None, min_confidence=None, min_consensus=None) -> List[InstitutionalDNA]`

Filter-based search across current DNA records.

```python
# All INSTITUTIONAL DNA
institutional = repo.search(lifecycle="INSTITUTIONAL")

# VOLUME category with high confidence
strong_volume = repo.search(
    category="VOLUME",
    min_confidence=0.75,
    min_consensus=0.70,
)

# All current DNA (no filters)
all_dna = repo.search()
```

- All parameters are optional; omitting them returns all current DNA
- Results are the latest version only (`is_current = 1`)

---

### `list_active() -> List[InstitutionalDNA]`

Return all non-retired, current DNA records.

```python
active = repo.list_active()
# All with lifecycle != "RETIRED" and is_current = 1
```

---

### `list_retired() -> List[InstitutionalDNA]`

Return all retired, current DNA records.

```python
retired = repo.list_retired()
```

---

### `audit_log(dna_id) -> List[Dict]`

Return all audit log entries for a DNA in timestamp order.

```python
log = repo.audit_log("DNA-VOLUME-SURGE-BULL")
for entry in log:
    print(entry["operation"], entry["version_before"], "->", entry["version_after"])
    print(entry["reason"], entry["operator"])
```

Each entry dict contains:
- `id`, `operation`, `dna_id`, `version_before`, `version_after`
- `operator`, `study_id`, `reason`, `timestamp`

---

### `statistics() -> DNARepositoryStatistics`

Return aggregate statistics.

```python
stats = repo.statistics()
print(stats.total_dna)        # all DNA (any lifecycle)
print(stats.active_dna)       # non-RETIRED
print(stats.retired_dna)
print(stats.institutional_dna)
print(stats.avg_confidence)
print(stats.db_size_bytes)
print(stats.schema_version)
print(stats.last_updated)
```

---

## Maintenance API

### `backup(backup_path=None) -> Path`

Create a consistent backup using the SQLite Online Backup API.

```python
# Auto-named: data/mls/institutional_dna_backup_YYYYMMDD_HHMMSS.db
backup_file = repo.backup()

# Explicit path
backup_file = repo.backup("backups/2026-08-04.db")
```

- Uses `sqlite3.Connection.backup()` — safe while other threads read/write
- Returns the `Path` of the created backup file

---

### `verify_integrity() -> bool`

Run SQLite `PRAGMA integrity_check` and return `True` if the database is healthy.

```python
if not repo.verify_integrity():
    logger.error("IDR database integrity check FAILED — restore from backup")
```

---

### `db_path` property

```python
print(repo.db_path)   # Path object to the database file
```

---

## Exceptions

| Exception | When raised |
|---|---|
| `IDRError` | Base class for all IDR errors |
| `IDRNotFoundError` | DNA id not found (get, get_version, add_evidence, add_history, add_context, update, retire) |
| `IDRVersionError` | Specific version not found (get_version) |
| `IDRIntegrityError` | Database corruption or constraint violation detected |

All three specific exceptions are subclasses of `IDRError`, so you can catch
all IDR errors with a single `except IDRError`.

---

## Config Fields (MLSConfig)

| Field | Default | Description |
|---|---|---|
| `idr_schema_version` | 1 | Expected schema version |
| `idr_max_evidence_per_dna` | 500 | Soft cap on evidence records per DNA |
| `idr_max_history_per_dna` | 1000 | Soft cap on history records per DNA |
| `idr_max_context_per_dna` | 200 | Soft cap on context records per DNA |
| `idr_backup_on_schema_change` | True | Auto-backup before schema migration |
| `idr_wal_mode` | True | Enable WAL journal mode |
| `idr_min_confidence_active` | 0.0 | Minimum confidence to include in list_active() |
| `idr_default_operator` | "system" | Default operator string when not specified |

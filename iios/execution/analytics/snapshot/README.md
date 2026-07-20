# Execution Analytics Snapshot

**C8 Execution Analytics & Intelligence — Phase 1, Module 5**

---

## Purpose

`ExecutionAnalyticsSnapshot` is the **ONLY** published representation of the Analytics subsystem.

Every downstream subsystem — Analytics Integration, Decision Intelligence, Portfolio Intelligence, AI Supervisor, Compliance, Reporting, Dashboard, and Enterprise Intelligence — **MUST** consume `ExecutionAnalyticsSnapshot` and **MUST NOT** reference internal M1/M2/M3/M4 objects directly.

The snapshot:
- Is **immutable** (frozen dataclass)
- Performs **NO calculations**
- Performs **NO forecasting**
- Contains **validated analytics information only**

---

## Architecture

```
AnalyticsSnapshotFactory            ← Convenience: build + validate + store
  └── AnalyticsSnapshotBuilder      ← Builds from M1/M2/M3/M4 sources
        └── AnalyticsSnapshotValidator  ← 10-check validation

AnalyticsSnapshotStore              ← Primary store + all query methods
  ├── AnalyticsSnapshotCache        ← LRU cache (fast lookup)
  ├── AnalyticsSnapshotHistory      ← Per-dimension version history
  └── AnalyticsSnapshotStatistics   ← Counters + timing

AnalyticsSnapshotRegistry           ← Active snapshot index (deduplication)
AnalyticsSnapshotBundle             ← Immutable collection for batch ops
AnalyticsSnapshotEvent              ← Lifecycle event records
```

---

## Snapshot Content

| Field | Type | Description |
|---|---|---|
| `snapshot_id` | `str` | Unique identifier |
| `snapshot_version` | `str` | Schema version |
| `analytics_session_id` | `str` | M1 analytics session |
| `execution_session_id` | `str` | Execution session |
| `workflow_id` | `str` | Associated workflow |
| `portfolio_id` | `str` | Portfolio context |
| `strategy_id` | `str` | Strategy context |
| `analytics_scope` | `AnalyticsScope` | Execution / Portfolio / Strategy / Workflow / System |
| `analytics_mode` | `AnalyticsMode` | Real-time / Batch / On-Demand / Scheduled |
| `lifecycle_state` | `SnapshotLifecycleState` | Building → Validating → Ready → Published → Archived |
| `analytics_status` | `AnalyticsStatus` | Pending / Active / Completed / Failed / Archived |
| `analytics_health` | `AnalyticsHealth` | Healthy / Degraded / Critical / Unknown |
| `performance_summary` | `PerformanceSummary` | Win rate, PnL, Sharpe, fill rate |
| `performance_kpis` | `PerformanceKPIs` | KPI values from M3 |
| `performance_scorecard` | `PerformanceScorecard` | Grade, scores from M3 |
| `trend_summary` | `TrendSummary` | Dominant trend from M3 |
| `benchmark_summary` | `BenchmarkSummary` | Benchmark comparison from M3 |
| `historical_summary` | `HistoricalSummary` | Data range summary |
| `prediction_summary` | `PredictionSummary` | Forecast count, confidence from M4 |
| `forecast_summary` | `SnapshotForecastSummary` | Forecast horizon, domain from M4 |
| `confidence_summary` | `ConfidenceSummary` | Aggregated confidence scores |
| `operational_health_score` | `float` | [0, 1] composite health |
| `capacity_forecast` | `SnapshotCapacityForecast` | Infrastructure utilization from M4 |
| `risk_forecast` | `SnapshotRiskForecast` | Risk level and score from M4 |
| `analytics_statistics` | `SnapshotAnalyticsStatistics` | Cycle counts across M1–M4 |
| `analytics_metadata` | `AnalyticsMetadata` | Build metadata |
| `audit_metadata` | `AuditMetadata` | Who created / validated / published |
| `framework_version` | `str` | IIOS framework version |
| `timestamp` | `float` | Unix timestamp of snapshot creation |

---

## Builder Sources

The `AnalyticsSnapshotBuilder.build()` accepts optional sources from all four frameworks:

| Argument | Source | Data Extracted |
|---|---|---|
| `analytics_session` | M1 `AnalyticsSession` | IDs, scope, mode |
| `analytics_statistics` | M1 `AnalyticsStatistics` | Lifecycle cycle counts |
| `engine_snapshot` | M2 `AnalyticsSnapshot` | Engine state |
| `engine_statistics` | M2 `EngineAnalyticsStatistics` | Engine cycle counts |
| `performance_report` | M3 `PerformanceAnalyticsReport` | KPIs, scorecard, trends, benchmarks |
| `performance_stats` | M3 `PerformanceAnalyticsStatistics` | Performance cycle counts |
| `prediction_report` | M4 `PredictionReport` | Forecasts, risk, capacity |
| `predictive_stats` | M4 `PredictiveIntelligenceStatistics` | Prediction cycle counts |

All sources are **optional** — a minimal valid snapshot requires only `analytics_session_id` and `execution_session_id`.

**Rejection criteria:**
- Missing `analytics_session_id` or `execution_session_id` → `SnapshotBuildError`
- Duplicate snapshot ID in registry → `SnapshotDuplicateError`
- Validation failure on a live snapshot → `SnapshotValidationError`

---

## Validation

Ten checks are run by `AnalyticsSnapshotValidator.validate()`:

1. **Identifier consistency** — required IDs non-empty
2. **Lifecycle consistency** — state must be Ready/Published/Archived/Validating
3. **Performance consistency** — rates/scores in [0, 1]
4. **Prediction consistency** — confidence values in [0, 1]
5. **Trend consistency** — `dominant_trend` non-empty string
6. **Benchmark consistency** — `overall_score` in [0, 1]
7. **Forecast consistency** — utilization/risk in [0, 1]
8. **Snapshot completeness** — `operational_health_score` in [0, 1]
9. **Version compatibility** — `framework_version` must match `1.0.0`
10. **Timestamp consistency** — `timestamp` must be positive

---

## Store Queries

`AnalyticsSnapshotStore` supports nine query methods:

| Method | Description |
|---|---|
| `get_by_id(snapshot_id)` | By snapshot ID |
| `get_by_analytics_session(session_id)` | By M1 analytics session |
| `get_by_execution_session(exec_id)` | By execution session |
| `get_by_workflow(workflow_id)` | By workflow |
| `get_by_portfolio(portfolio_id)` | By portfolio |
| `get_by_strategy(strategy_id)` | By strategy |
| `get_by_status(status)` | By `AnalyticsStatus` |
| `get_by_health(min_score)` | By minimum operational health score |
| `get_by_timestamp_range(from_ts, to_ts)` | By timestamp range |
| `get_latest()` | Most recently saved snapshot |
| `get_latest_for_session(session_id)` | Latest for a session |
| `historical_versions(session_id)` | All versions for a session |

---

## Quick Start

```python
from iios.execution.analytics.snapshot import (
    AnalyticsSnapshotFactory,
    AnalyticsSnapshotStore,
    ExecutionAnalyticsSnapshot,
)
from iios.execution.analytics.performance import PerformanceAnalyticsEngine
from iios.execution.analytics.predictive import (
    PredictiveIntelligenceEngine,
    PredictionDomain,
    ForecastHorizon,
)

# Start analytics engines
pae  = PerformanceAnalyticsEngine(); pae.start()
pie  = PredictiveIntelligenceEngine(); pie.start()

# Run analytics
perf_report = pae.process("session-001")
pred_report = pie.submit(PredictionDomain.EXECUTION_PERFORMANCE)

# Build and store snapshot
store   = AnalyticsSnapshotStore(); store.start()
factory = AnalyticsSnapshotFactory(store=store); factory.start()

snapshot: ExecutionAnalyticsSnapshot = factory.create(
    analytics_session_id = "session-001",
    execution_session_id = "exec-session-001",
    performance_report   = perf_report,
    prediction_report    = pred_report,
    publish              = True,
)

print(f"Health: {snapshot.analytics_health}")
print(f"Score:  {snapshot.operational_health_score:.2f}")
print(f"Grade:  {snapshot.performance_scorecard.grade}")
print(f"Risk:   {snapshot.risk_forecast.risk_level}")

# Query
latest = store.get_latest_for_session("session-001")
```

---

## Events

Six events cover the full snapshot lifecycle:

| Event | Factory Function |
|---|---|
| `SnapshotCreated` | `make_snapshot_created_event()` |
| `SnapshotValidated` | `make_snapshot_validated_event()` |
| `SnapshotPublished` | `make_snapshot_published_event()` |
| `SnapshotArchived` | `make_snapshot_archived_event()` |
| `SnapshotRetrieved` | `make_snapshot_retrieved_event()` |
| `SnapshotCached` | `make_snapshot_cached_event()` |

---

## Statistics

`AnalyticsSnapshotStatistics` tracks:
- Snapshots created, published, archived
- Validation success / failure
- Average build time (ms)
- Average snapshot size (bytes)

---

## Thread Safety

All public methods on `AnalyticsSnapshotStore`, `AnalyticsSnapshotCache`,
`AnalyticsSnapshotRegistry`, and `AnalyticsSnapshotHistory` are thread-safe.

Concurrent calls to `factory.create()` from multiple threads are safe.

---

## Design Invariants

1. `ExecutionAnalyticsSnapshot` is a **frozen dataclass** — immutable.
2. **NO calculations** inside the snapshot — data only.
3. **NO forecasting** inside the snapshot — results from M4 only.
4. `ExecutionAnalyticsSnapshot` is the **only** published interface.
5. Internal M1/M2/M3/M4 objects are **never** exposed to downstream callers.

---

## Tests

```
tests/unit/execution/analytics/snapshot/
  └── test_execution_analytics_snapshot.py    130 tests
```

Run with:
```sh
python -m pytest tests/unit/execution/analytics/snapshot/ -v
```

---

## Version

**1.0.0** — Initial release, C8 M5.

# Health & Monitoring Guide

## SubsystemHealth

`manager.health()` returns a `SubsystemHealth` snapshot.

```python
health = manager.health()

health.overall_healthy    # bool — all components healthy
health.all_running        # bool — all components in RUNNING state
health.component_health   # Dict[str, ComponentHealth]
health.unhealthy_components  # List[str] — names of unhealthy components
health.to_dict()
```

Each `ComponentHealth` contains:

```python
ch.component_type  # str (e.g. "engine", "controls", "snapshot")
ch.is_healthy      # bool
ch.is_running      # bool
ch.state           # str — lifecycle state value
ch.last_checked    # float — Unix timestamp
ch.error           # Optional[str] — None if healthy
```

## SubsystemStatus

`manager.status()` returns a `SubsystemStatus` enum value:

| Status | Meaning |
|---|---|
| UNINITIALIZED | Not yet started |
| INITIALIZING | In start() |
| INITIALIZED | Created but not started |
| RUNNING | Fully operational |
| DEGRADED | Paused or partial failure |
| STOPPING | In stop() |
| STOPPED | Cleanly stopped |
| FAILED | Error state |
| SHUTDOWN | Terminal state |

## IntegrationStatistics

`manager.statistics()` returns a copy of accumulated counters.

```python
stats = manager.statistics()

stats.requests_processed      # total evaluate() calls
stats.successful_evaluations  # approved=True count
stats.blocked_evaluations     # approved=False count
stats.warnings_issued         # ALLOW_WITH_WARNING count
stats.overrides_applied       # manual override count
stats.emergency_stops         # EMERGENCY_STOP count
stats.validation_failures     # pre-evaluation validation fails
stats.evaluation_errors       # unexpected exceptions

stats.average_processing_time_ms  # derived — mean elapsed_ms
stats.subsystem_availability      # derived — success ratio 0..1
stats.block_rate                  # derived — block ratio 0..1
stats.uptime_sec                  # seconds since start()

stats.to_dict()
```

## ExecutionRiskIntegrationSnapshot

`manager.snapshot()` returns a full point-in-time diagnostic view:

```python
snap = manager.snapshot()

snap.subsystem_state    # str — lifecycle state
snap.is_running         # bool
snap.is_healthy         # bool
snap.component_health   # Dict[str, dict]
snap.statistics         # dict
snap.recent_events      # List[dict] — last 20 events
snap.evaluation_count   # int
snap.snapshot_count     # int — M5 registry count
snap.uptime_sec         # float
snap.version            # "1.0.0"
snap.taken_at           # float — Unix timestamp

snap.to_dict()
snap.to_json()
```

## Events

`manager.events()` returns all `IntegrationEvent` instances emitted since start.

| EventType | When emitted |
|---|---|
| SUBSYSTEM_STARTED | on _on_start() |
| EVALUATION_REQUESTED | before evaluation workflow |
| EVALUATION_COMPLETED | after successful workflow |
| SNAPSHOT_PUBLISHED | M5 snapshot registered & published |
| VALIDATION_COMPLETED | after every validation (pass or fail) |
| HEALTH_UPDATED | after health() call |
| SUBSYSTEM_STOPPED | on _on_stop() |

## History queries

```python
manager.history(n=50)                          # last N responses
manager.query(execution_id="EX-1")            # by execution
manager.query(portfolio_id="PORT-A")          # by portfolio
manager.query(approved_only=True)             # approved only
manager.query(blocked_only=True, limit=100)   # blocked, capped at 100
```

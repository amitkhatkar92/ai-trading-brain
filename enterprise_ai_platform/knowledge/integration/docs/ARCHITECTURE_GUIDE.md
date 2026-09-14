# Architecture Guide — C14 M6

## Layered Architecture

```
═══════════════════════════════════════════════════════════════
 EXTERNAL IIOS COMPONENTS  (C6-C13)
═══════════════════════════════════════════════════════════════
                          │
              ┌───────────▼───────────┐
              │ KnowledgeIntegration  │  ← PUBLIC API (M6)
              │       Engine          │
              └───────────┬───────────┘
                          │ delegates all workflow
              ┌───────────▼───────────┐
              │ KnowledgeIntegration  │  ← NEVER RAISES
              │      Manager          │
              └────┬──┬──┬──┬─────────┘
                   │  │  │  │
      ┌────────────┘  │  │  └──────────────────┐
      ▼               ▼  ▼                     ▼
   M1 Lifecycle    M2 Engine  M3 Governance  M4 Intelligence
   (optional)      (optional) (optional)     (optional)
                                               │
                                               ▼
                                        M5 Snapshot
                                     (KnowledgeSnapshot)
                                      ← canonical output
═══════════════════════════════════════════════════════════════
```

## Component Registry Pattern

M1-M5 components are discovered at `initialize()` time via `KnowledgeComponentFactory`.
Each component is optional — if unavailable, the integration degrades gracefully.

```
KnowledgeComponentFactory
  create_lifecycle()     → M1 (optional)
  create_engine()        → M2 (optional)
  create_governance()    → M3 (optional)
  create_intelligence()  → M4 (optional)
  create_snapshot_factory() → M5 (always)
                              ↓
                  KnowledgeComponentRegistry
                  .lifecycle    = M1 | None
                  .engine       = M2 | None
                  .governance   = M3 | None
                  .intelligence = M4 | None
                  .snapshot_factory = M5
```

## Thread Safety

All stateful classes use `threading.Lock()`:
- `KnowledgeIntegrationEngine` — state machine transitions
- `KnowledgeComponentRegistry` — component slot access
- `KnowledgeIntegrationHistory` — deque + index
- `KnowledgeIntegrationRegistry` — response store
- `KnowledgeIntegrationStatistics` — all counters
- `KnowledgeIntegrationStatusTracker` — state + counters
- `IntegrationEventBus` — listener list
- `KnowledgeIntegrationHealth` — state

## State Machine

```
STOPPED → INITIALIZING → STOPPED → STARTING → RUNNING → STOPPING → STOPPED
                                                    │
                                                    └→ RESTARTING → STOPPED → STARTING → RUNNING
                                                    │
                                              ERROR (any state)
                                                    │
                                              DEGRADED (running but impaired)
```

## NEVER RAISES Contract

`KnowledgeIntegrationManager.execute()` never raises.
All subsystem calls are wrapped in try/except.
Errors are captured and returned in `KnowledgeIntegrationResponse.error_message`.

## Publishing Flow

```
submit(request)
     │
     ▼ (9 phases)
KnowledgeIntegrationResponse
     ├── snapshot_id → references M5 KnowledgeSnapshot
     ├── knowledge_summary → from M4 KnowledgeIntelligenceResponse
     └── phases_completed → which of 9 phases ran
```

# State Diagram — C15 M1 Integration Lifecycle

## 13 States

| State | Category |
|---|---|
| CREATED | Initial |
| INITIALIZING | Active |
| DISCOVERING | Active |
| CONFIGURING | Active |
| VALIDATING | Active |
| READY | Active |
| CONNECTING | Active |
| ACTIVE | Active |
| PAUSED | Active |
| RESUMING | Active |
| COMPLETED | Terminal |
| FAILED | Terminal (retryable) |
| ARCHIVED | Terminal (immutable) |

---

## State Diagram

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                INTEGRATION LIFECYCLE                        │
                    └─────────────────────────────────────────────────────────────┘

[●] START
  │
  ▼
┌─────────┐  initialize   ┌─────────────┐  discover   ┌────────────┐
│ CREATED │──────────────▶│ INITIALIZING│────────────▶│ DISCOVERING│
└─────────┘               └─────────────┘             └────────────┘
                                 │                           │
                              fail │                      fail │
                                 │                           │
                                 ▼                           ▼
┌──────────────┐  configure  ┌────────────┐           ┌────────┐
│  CONFIGURING │◀────────────│ DISCOVERING│           │ FAILED │◀─── (any active state)
└──────────────┘             └────────────┘           └────────┘
       │                                                   │
    fail│  validate                                     archive│  retry
       │                                                   │
       ▼                                                   ▼
┌───────────┐  mark_ready  ┌───────┐              ┌──────────┐
│ VALIDATING│─────────────▶│ READY │              │ ARCHIVED │ ← immutable terminal
└───────────┘              └───────┘              └──────────┘
       │                      │  archive                ▲
    fail│                     └────────────────────────►┘
       ▼                      │  connect
    FAILED                    ▼
                        ┌───────────┐  activate  ┌────────┐
                        │ CONNECTING│────────────▶│ ACTIVE │
                        └───────────┘             └────────┘
                               │                     │   │   │
                            fail│              pause  │   │complete
                                ▼                     │   │
                             FAILED                   ▼   ▼
                                               ┌────────┐  ┌───────────┐
                                               │ PAUSED │  │ COMPLETED │──► ARCHIVED
                                               └────────┘  └───────────┘
                                                   │  │
                                             resume│  │archive
                                                   ▼  ▼
                                           ┌──────────┐  ARCHIVED
                                           │ RESUMING │
                                           └──────────┘
                                                  │  │
                                           active │  │fail
                                                  ▼  ▼
                                               ACTIVE  FAILED
```

---

## VALID_TRANSITIONS Table

```python
CREATED      → {INITIALIZING}
INITIALIZING → {DISCOVERING, FAILED}
DISCOVERING  → {CONFIGURING, FAILED}
CONFIGURING  → {VALIDATING, FAILED}
VALIDATING   → {READY, FAILED}
READY        → {CONNECTING, ARCHIVED}
CONNECTING   → {ACTIVE, FAILED}
ACTIVE       → {PAUSED, COMPLETED, FAILED}
PAUSED       → {RESUMING, ARCHIVED, FAILED}
RESUMING     → {ACTIVE, FAILED}
COMPLETED    → {ARCHIVED}
FAILED       → {ARCHIVED, INITIALIZING}
ARCHIVED     → {}  # no transitions — immutable terminal
```

# Knowledge Lifecycle — State Diagram

```
                      ┌─────────┐
                      │ CREATED │
                      └────┬────┘
                           │ initialize()
                      ┌────▼────────┐
                      │INITIALIZING │
                      └────┬────────┘
                           │ collect()
                      ┌────▼──────┐
                      │COLLECTING │
                      └────┬──────┘
                           │ validate_session()
                      ┌────▼──────────┐
                      │  VALIDATING   │
                      └────┬──────────┘
                           │ mark_ready()
                      ┌────▼──────┐
            ┌──────── │   READY   │ ─────────────────┐
            │ pause() └────┬──────┘                  │
            │              │ start_capture()          │
            │         ┌────▼──────────┐              │
            │         │  CAPTURING    │              │
            │         └────┬──────────┘              │
            │              │ mark_indexing_pending()  │
            │         ┌────▼──────────────┐          │
            │         │ INDEXING_PENDING  │          │
            │         └────┬──────────────┘          │
            │              │ publish()               │
            │         ┌────▼──────────┐              │
            │ ┌─────── │  PUBLISHED   │ ────────┐    │
            │ │pause() └──────────────┘ complete│    │
            │ │                                 │    │
            ▼ ▼                            ┌────▼──┐ │
         ┌───────┐                         │COMPL. │ │
         │PAUSED │                         └────┬──┘ │
         └───┬───┘                              │    │
             │ resume()                         │archive()
             │                                  │
         ┌───▼────────┐                         │
         │  RESUMING  │─────────────────────────│
         └───┬────────┘    mark_resumed()       │
             │ → CAPTURING | READY              │
                                                │
        ┌────────┐                              │
        │ FAILED │◄──── (any state) fail()      │
        └────┬───┘                              │
             │ archive()                        │
             ▼                                  ▼
         ┌──────────────────────────────────────┐
         │              ARCHIVED                │
         │          (terminal, immutable)       │
         └──────────────────────────────────────┘
```

All non-terminal states can also transition to `FAILED` via `fail()`.
`ARCHIVED` is strictly terminal — no further transitions are possible.

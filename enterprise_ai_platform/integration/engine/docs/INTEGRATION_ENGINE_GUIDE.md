# Integration Engine Guide — C15 M2

## Architecture

```
IntegrationManager          ← public API
  └── IntegrationEngine     ← central coordinator
        ├── IntegrationEngineRegistry   (ConnectorManager + AdapterManager + ProtocolRegistry)
        ├── IntegrationDispatcher       → IntegrationPipeline
        ├── IntegrationScheduler        (priority queue)
        ├── IntegrationSessionManager   → M1 IntegrationLifecycle
        ├── IntegrationEngineValidator  (7 checks)
        ├── IntegrationEngineEventBus   (9 events)
        ├── IntegrationEngineStatistics (9 counters)
        └── IntegrationEngineHistory    (bounded)
```

## Engine States

| State | Meaning |
|---|---|
| IDLE | Ready to accept requests |
| INITIALIZING | Starting up |
| CONFIGURING | Applying configuration |
| VALIDATING | Running validation-only operation |
| CONNECTING | Establishing base connectivity |
| DISPATCHING | Actively processing request(s) |
| MONITORING | Running health check |
| PUBLISHING | Publishing integration snapshot |
| COMPLETED | Last request completed |
| FAILED | Engine-level failure |
| STOPPED | Engine shut down |

## Dispatch Workflow

```
1. Receive IntegrationRequest
2. Validate (7 checks via IntegrationEngineValidator)
3. Initialize Session (M1 lifecycle: CREATED → ACTIVE)
4. Load Connector (from ConnectorManager)
5. Load Adapter (from AdapterManager)
6. Validate Protocol (from ProtocolRegistry)
7. Dispatch Pipeline (IntegrationDispatcher → IntegrationPipeline)
8. Coordinate Governance (M3 delegation hook)
9. Coordinate Services (M4 delegation hook)
10. Publish Snapshot (emit INTEGRATION_PUBLISHED event)
11. Complete Session (M1 lifecycle: ACTIVE → COMPLETED → ARCHIVED)
12. Return IntegrationResponse
```

## Error Handling

| Code | Exception | Meaning |
|---|---|---|
| IEN-000 | `IntegrationEngineError` | Base |
| IEN-001 | `IntegrationEngineNotReadyError` | Engine stopped |
| IEN-002 | `ConnectorNotFoundError` | Connector not registered |
| IEN-003 | `AdapterNotFoundError` | Adapter not registered |
| IEN-004 | `ProtocolNotRegisteredError` | Protocol not registered |
| IEN-005 | `IntegrationRequestValidationError` | Validation failed |
| IEN-006 | `IntegrationDispatchError` | Dispatch error |
| IEN-007 | `IntegrationSessionError` | Session lifecycle error |
| IEN-008 | `ConnectorRegistrationError` | Connector registration failed |
| IEN-009 | `AdapterRegistrationError` | Adapter registration failed |

## Governance and Services Delegation

```
_coordinate_governance() → M3 Integration Governance Policy Framework
_coordinate_services()   → M4 Integration Services Framework
```

Both methods are delegation hooks.  When M3 and M4 are implemented,
their frameworks are injected at engine construction time.

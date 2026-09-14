# Session Management Guide

## What is a session?

A `GatewaySession` groups one or more gateway requests from the same
execution context (portfolio + strategy + execution ID).  Sessions provide
a logical boundary for request batches and carry a configurable timeout.

## Session lifecycle

```
ACTIVE  → expired → EXPIRED   (automatic via expire_stale_sessions())
        → closed  → CLOSED    (manual via close_session())
```

## Creating sessions

Sessions are created automatically by `GatewayManager` for every
`process_request()` call.  You do not need to create sessions manually
when using `ExecutionGatewayEngine`.

## Timeout

Default `DEFAULT_SESSION_TIMEOUT_SECS = 3600.0` (1 hour).

Pass a custom timeout when constructing the engine:

```python
engine = ExecutionGatewayEngine(session_timeout=1800.0)  # 30 min
```

## Expiring stale sessions

`GatewaySessionManager.expire_stale_sessions()` scans all ACTIVE sessions
and expires those past their `expires_at` timestamp.  Returns the count
of sessions expired.

## Querying sessions

```python
snap = engine.snapshot()
print(snap.active_session_count)
```

From the manager directly (not public API):

```python
all_sessions   = manager._sessions.all_sessions()
active_sessions = manager._sessions.active_sessions()
expired_sessions = manager._sessions.expired_sessions()
```

## Session extension

```python
session.extend(extra_secs=600)   # add 10 min to expiry
session.touch()                  # update updated_at
```

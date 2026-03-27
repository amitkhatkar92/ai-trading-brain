---
name: trading-engine-safety
description: "Use when: hardening a Python trading engine or long-running daemon against duplicate processes, log conflicts, or missing startup/shutdown instrumentation. Covers single-instance PID lock, daily log rotation, startup/shutdown banners, and --status CLI command. Apply to main.py and utils/ when adding process safety to any scheduled or daemon trading script."
---

# Trading Engine Safety — Single Instance + Unified Logging

## When This Skill Applies
- A daemon (`--schedule` mode) is being started by a scheduler (cron, Windows Task Scheduler)  
- Multiple instances of the same script are running simultaneously, causing log conflicts or duplicate signals  
- Logs are scattered across files or overwritten on each restart  
- There is no visibility into whether the engine is currently running  

---

## Step 1 — Audit the Problem

Before writing code, confirm:
1. **Is it multi-instance?** Run `ps aux | grep main.py` (Linux) or `Get-Process python` (Windows). More than one process = confirmed problem.
2. **Where do logs go?** Check `utils/logger.py` or equivalent. Rotating file? Per-run overwrite? No file at all?
3. **Is there a clean shutdown path?** Confirm `KeyboardInterrupt` and `SIGTERM` are both handled.
4. **What modes need the lock?** Only daemon/scheduler modes need it. Read-only/diagnostic modes (`--status`, `--readiness`) must bypass it.

---

## Step 2 — Single-Instance PID Lock

### Create `utils/instance_lock.py`

Key decisions:
- **Lock file location**: `data/trading_engine.pid` inside the project root (predictable, project-scoped). Avoid `/tmp/` on shared servers.
- **Format**: JSON `{"pid": 12345, "started_at": "...", "mode": "schedule"}` — provides `--status` info for free.
- **Stale lock handling**: Check `os.kill(pid, 0)` (works cross-platform via `OSError`). If the PID is dead, remove and proceed.
- **Non-fatal write failures**: If the PID file cannot be written (permissions), log an error but don't block startup.

```python
# utils/instance_lock.py — minimal interface
def acquire(mode: str = "unknown") -> bool:  # False = another instance running
def release() -> None:                        # removes PID file
def get_status() -> dict:                     # {running, pid, started_at, mode}
```

### Lock scope in `main()`

| Mode | Acquire lock? | Reason |
|---|---|---|
| `--status` | No | Read-only query |
| `--readiness` | No | Diagnostic, no brain |
| `--dashboard` | No | `os.execv` replaces process |
| `--telegram` | No | Separate control-plane service |
| Everything else | **Yes** | Creates `MasterOrchestrator`, writes DB |

---

## Step 3 — Structured try / finally in `main()`

Wrap all lock-gated execution in `try / except / finally` to guarantee lock release:

```python
if not instance_lock.acquire(_lock_mode):
    sys.exit(1)

try:
    brain = MasterOrchestrator()
    # ... all mode branches as if/elif/else ...
except KeyboardInterrupt:
    log.info("KeyboardInterrupt — shutting down.")
except Exception:
    log.exception("Unexpected crash in trading engine.")
    raise
finally:
    log.info("=== TRADING ENGINE STOPPED ===")
    instance_lock.release()
```

**Critical**: Convert mode branches from independent `if + return` to a single `if/elif/else` chain so the `finally` always fires. Remove all intermediate `return` statements from inside the try body.

---

## Step 4 — Daily Log Files

### Pattern: `_DailyFileHandler` in `utils/logger.py`

```python
class _DailyFileHandler(logging.FileHandler):
    """Writes to logs/YYYY-MM-DD.log; reopens at midnight automatically."""
    def emit(self, record):
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._today:
            self.close()
            self.baseFilename = os.path.abspath(f"{self._log_dir}/{today}.log")
            self._today = today
            self.stream = self._open()
        super().emit(record)
```

### Attach once to root logger (not per-named-logger)

```python
_daily_setup_done = False

def _setup_daily_log(fmt):
    global _daily_setup_done
    with _daily_setup_lock:
        if _daily_setup_done:
            return
        root = logging.getLogger()
        root.addHandler(_DailyFileHandler(DAILY_LOG_DIR, fmt))
        if root.level == logging.NOTSET:
            root.setLevel(logging.DEBUG)
        _daily_setup_done = True
```

Call `_setup_daily_log(fmt)` at the end of `get_logger()`, after `fmt` is defined. The double-checked lock ensures the handler is registered exactly once regardless of how many modules call `get_logger`.

**Result**: every module's log records propagate to root and land in `logs/2026-03-27.log`.

---

## Step 5 — Startup & Shutdown Banners

Log these immediately after lock acquisition and in the `finally` block:

```python
log.info("=== TRADING ENGINE STARTED ===")
log.info("  Mode    : %s | %s", lock_mode, "PAPER" if PAPER_TRADING else "LIVE")
log.info("  PID     : %d", os.getpid())
log.info("  Time    : %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# ... in finally:
log.info("=== TRADING ENGINE STOPPED ===")
```

---

## Step 6 — `--status` Command

Add to `argparse`:
```python
parser.add_argument("--status", action="store_true",
                    help="Print running status (PID, mode, start time) and exit")
```

Handle *before* the lock acquisition (no lock needed):
```python
if args.status:
    _print_status()
    return
```

`_print_status()` reads `instance_lock.get_status()` and prints a formatted table. Uses `os.kill(pid, 0)` to confirm the PID is truly alive before reporting RUNNING.

---

## Verification Checklist

- [ ] `python -m py_compile main.py` passes  
- [ ] `python main.py --status` prints NOT RUNNING when no engine is active  
- [ ] Start engine: `python main.py --schedule &`  
- [ ] `python main.py --status` shows RUNNING with correct PID  
- [ ] Start second instance: should print "Another instance already running. Exiting." and exit code 1  
- [ ] Kill engine: `kill <PID>` — lock file removed, `--status` shows NOT RUNNING  
- [ ] Check `logs/YYYY-MM-DD.log` exists and contains structured log lines  
- [ ] Verify stale lock recovery: manually create PID file with a dead PID, start engine — it should remove it and start cleanly  

---

## Common Pitfalls

| Pitfall | Fix |
|---|---|
| Lock not released on crash | Always use `try/finally`, never `atexit` alone |
| `return` inside `try` skips `finally` | False — `finally` always runs, even with `return` |
| Duplicate log entries for hierarchical loggers | Expected; caused by `propagate=True` on child loggers. Only a problem if child has same handler as root — avoid adding daily handler to per-module loggers |
| `os.kill(pid, 0)` always raises on Windows with cross-user PIDs | Fine for single-user deployments (same user starts the process and checks it) |
| Lock file left over after hard reboot | Stale lock detection via `_is_pid_running()` handles this automatically on next start |

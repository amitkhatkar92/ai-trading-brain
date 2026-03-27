"""Single-instance lock — prevents multiple copies of main.py running simultaneously.

Uses a JSON PID file at ``data/trading_engine.pid``.
Stale locks (process no longer alive) are automatically cleared on the next start.
"""

import json
import logging
import os
import sys

log = logging.getLogger("instance_lock")

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_FILE = os.path.join(_PROJECT_ROOT, "data", "trading_engine.pid")


def _is_pid_running(pid: int) -> bool:
    """Return True if a process with *pid* is alive (cross-platform, signal-0 trick)."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire(mode: str = "unknown") -> bool:
    """Try to acquire the single-instance lock.

    Returns ``True``  — lock acquired; caller may proceed.
    Returns ``False`` — a live instance already holds the lock; caller should exit.

    Stale lock files (PID no longer running) are automatically removed.
    """
    from datetime import datetime

    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)

    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as fh:
                data = json.load(fh)
            pid = int(data.get("pid", 0))
            if _is_pid_running(pid):
                print(
                    f"Another instance already running "
                    f"(PID {pid}, mode={data.get('mode', '?')}, "
                    f"started={data.get('started_at', '?')}). Exiting.",
                    file=sys.stderr,
                )
                return False
            log.warning(
                "Stale lock file found (PID %d no longer running) — removing.", pid
            )
        except (ValueError, KeyError, json.JSONDecodeError, OSError):
            pass  # Corrupt / unreadable — overwrite below

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {"pid": os.getpid(), "started_at": now, "mode": mode}
    try:
        with open(LOCK_FILE, "w") as fh:
            json.dump(payload, fh)
    except OSError as exc:
        log.error(
            "Cannot write lock file %s: %s — continuing without lock.", LOCK_FILE, exc
        )
        return True  # Non-fatal; don't block startup over a write error

    return True


def release() -> None:
    """Remove the PID file, releasing the lock."""
    try:
        if os.path.exists(LOCK_FILE):
            os.unlink(LOCK_FILE)
    except OSError as exc:
        log.warning("Could not remove lock file: %s", exc)


def get_status() -> dict:
    """Return current engine status as a plain dict.

    Keys: ``running`` (bool), ``pid`` (int|None), ``started_at`` (str|None),
    ``mode`` (str|None).
    """
    result: dict = {"running": False, "pid": None, "started_at": None, "mode": None}
    if not os.path.exists(LOCK_FILE):
        return result
    try:
        with open(LOCK_FILE) as fh:
            data = json.load(fh)
        pid = int(data.get("pid", 0))
        result.update(data)
        result["running"] = _is_pid_running(pid)
    except (ValueError, json.JSONDecodeError, OSError):
        pass
    return result

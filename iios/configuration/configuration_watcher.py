"""
iios/configuration/configuration_watcher.py
=============================================
File-system watcher for hot-reload of configuration files.

Uses ``watchdog`` if installed, otherwise falls back to periodic polling
using SHA-256 file hashes.

Change notifications are debounced (minimum 1 second between alerts for
the same path) and delivered via registered callbacks.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .configuration_exception import ConfigurationWatcherError

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationWatcher",
]

_HAS_WATCHDOG = False
try:
    from watchdog.events import FileModifiedEvent, FileSystemEventHandler
    from watchdog.observers import Observer
    _HAS_WATCHDOG = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Public watcher
# ---------------------------------------------------------------------------


class ConfigurationWatcher:
    """Watches configuration files and fires callbacks on change.

    Args:
        poll_interval_seconds: Polling interval when watchdog is unavailable.
        debounce_seconds:      Minimum gap between two notifications for the
                               same path.
    """

    def __init__(
        self,
        poll_interval_seconds: float = 5.0,
        debounce_seconds: float = 1.0,
    ) -> None:
        self._poll_interval = poll_interval_seconds
        self._debounce = debounce_seconds

        # path → list of callbacks
        self._callbacks: dict[str, list[Callable[[str], None]]] = {}
        # path → last notification time (monotonic)
        self._last_notified: dict[str, float] = {}
        # path → last hash (for polling)
        self._last_hashes: dict[str, str] = {}

        self._running = False
        self._lock = threading.Lock()

        if _HAS_WATCHDOG:
            self._observer: Optional["Observer"] = None
            self._handler: Optional[_WatchdogHandler] = None
        else:
            self._poll_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def watch(self, path: str, callback: Callable[[str], None]) -> None:
        """Register *callback* to be called when *path* changes.

        Multiple callbacks can be registered for the same path.
        Calling ``watch()`` on a path that is already watched adds another
        callback (does not replace existing ones).

        Args:
            path:     Absolute or relative file path.
            callback: ``Callable[[str], None]`` — receives the changed path.
        """
        with self._lock:
            self._callbacks.setdefault(path, []).append(callback)
            # Seed the hash so we only fire on actual changes
            self._last_hashes[path] = _file_hash(path)

    def unwatch(self, path: str) -> None:
        """Remove all callbacks for *path*."""
        with self._lock:
            self._callbacks.pop(path, None)
            self._last_notified.pop(path, None)
            self._last_hashes.pop(path, None)

    def start(self) -> None:
        """Start the watcher (idempotent)."""
        if self._running:
            return
        self._running = True
        if _HAS_WATCHDOG:
            self._start_watchdog()
        else:
            logger.debug("watchdog not installed — using polling every %ss", self._poll_interval)
            self._start_polling()

    def stop(self) -> None:
        """Stop the watcher (idempotent, safe to call when not running)."""
        self._running = False
        if _HAS_WATCHDOG and hasattr(self, "_observer") and self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=5)
            except Exception as exc:
                logger.debug("Error stopping watchdog observer: %s", exc)
            self._observer = None
        logger.debug("ConfigurationWatcher stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def watched_paths(self) -> list[str]:
        with self._lock:
            return list(self._callbacks)

    # ------------------------------------------------------------------
    # Watchdog backend
    # ------------------------------------------------------------------

    def _start_watchdog(self) -> None:
        try:
            self._handler = _WatchdogHandler(self._notify)
            self._observer = Observer()

            with self._lock:
                paths_to_watch = set(
                    str(Path(p).parent) for p in self._callbacks
                )

            for directory in paths_to_watch:
                self._observer.schedule(self._handler, directory, recursive=False)

            self._observer.start()
            logger.debug("ConfigurationWatcher started (watchdog backend)")
        except Exception as exc:
            raise ConfigurationWatcherError(
                f"Failed to start watchdog observer: {exc}",
                path="<multiple>",
            ) from exc

    # ------------------------------------------------------------------
    # Polling backend
    # ------------------------------------------------------------------

    def _start_polling(self) -> None:
        t = threading.Thread(target=self._poll_loop, daemon=True, name="cfg-watcher-poll")
        t.start()
        self._poll_thread = t
        logger.debug("ConfigurationWatcher started (polling backend, interval=%ss)", self._poll_interval)

    def _poll_loop(self) -> None:
        while self._running:
            with self._lock:
                paths = list(self._callbacks)

            for path in paths:
                current_hash = _file_hash(path)
                with self._lock:
                    previous_hash = self._last_hashes.get(path, "")

                if current_hash != previous_hash:
                    with self._lock:
                        self._last_hashes[path] = current_hash
                    self._notify(path)

            time.sleep(self._poll_interval)

    # ------------------------------------------------------------------
    # Notification dispatch (common)
    # ------------------------------------------------------------------

    def _notify(self, path: str) -> None:
        """Fire all callbacks for *path*, respecting debounce window."""
        now = time.monotonic()
        with self._lock:
            last = self._last_notified.get(path, 0.0)
            if (now - last) < self._debounce:
                return
            self._last_notified[path] = now
            callbacks = list(self._callbacks.get(path, []))

        logger.info("Configuration file changed: %s", path)
        for cb in callbacks:
            try:
                cb(path)
            except Exception as exc:
                logger.warning("Configuration watcher callback error for %s: %s", path, exc)


# ---------------------------------------------------------------------------
# Watchdog event handler
# ---------------------------------------------------------------------------


if _HAS_WATCHDOG:
    class _WatchdogHandler(FileSystemEventHandler):  # type: ignore[misc]
        def __init__(self, notify_fn: Callable[[str], None]) -> None:
            super().__init__()
            self._notify = notify_fn

        def on_modified(self, event: "FileModifiedEvent") -> None:
            if not event.is_directory:
                self._notify(event.src_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_hash(path: str) -> str:
    """Return SHA-256 of the file at *path*, or empty string if unreadable."""
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return ""

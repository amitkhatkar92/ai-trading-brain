"""
iios/monitoring/diagnostic_manager.py
=======================================
System diagnostic snapshots — CPU, memory, disk, network, process, Python GC.

``DiagnosticManager.snapshot()`` collects a point-in-time view of all
system resources. Requires ``psutil`` for most metrics; gracefully degrades
when it is unavailable.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import gc
import logging
import os
import platform
import sys
import threading
import time
from collections import deque
from typing import Any, Optional

from .monitoring_models import DiagnosticSnapshot

__all__ = [
    "DiagnosticManager",
    "get_diagnostic_manager",
]

_LOG = logging.getLogger("iios.monitoring.diagnostics")
_instance_lock = threading.Lock()
_instance: Optional["DiagnosticManager"] = None

_HAS_PSUTIL = False
try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except ImportError:
    pass


class DiagnosticManager:
    """Collects and stores system diagnostic snapshots.

    Args:
        history_size: Number of recent snapshots to keep in memory.
    """

    def __init__(self, history_size: int = 60) -> None:
        self._lock = threading.Lock()
        self._history: deque[DiagnosticSnapshot] = deque(maxlen=history_size)
        self._start_time = time.monotonic()
        self._proc = psutil.Process() if _HAS_PSUTIL else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def snapshot(self) -> DiagnosticSnapshot:
        """Collect a fresh diagnostic snapshot."""
        snap = DiagnosticSnapshot(
            python_version=platform.python_version(),
        )

        if _HAS_PSUTIL:
            self._collect_system(snap)
            self._collect_process(snap)
        else:
            _LOG.debug("psutil not available — skipping resource metrics")

        self._collect_gc(snap)
        self._collect_extras(snap)

        with self._lock:
            self._history.append(snap)

        return snap

    def recent_snapshots(self, n: int = 10) -> list[DiagnosticSnapshot]:
        """Return up to *n* most recent snapshots."""
        with self._lock:
            return list(reversed(list(self._history)))[:n]

    def latest(self) -> Optional[DiagnosticSnapshot]:
        """Return the most recent snapshot, or take a new one."""
        with self._lock:
            if self._history:
                return self._history[-1]
        return self.snapshot()

    def report(self) -> dict[str, Any]:
        """Return a concise human-readable diagnostic report."""
        snap = self.snapshot()
        uptime = time.monotonic() - self._start_time
        return {
            "timestamp": snap.timestamp,
            "uptime_seconds": round(uptime, 1),
            "python_version": snap.python_version,
            "platform": platform.platform(),
            "cpu_percent": snap.cpu_percent,
            "cpu_count": snap.cpu_count,
            "mem_percent": snap.mem_percent,
            "mem_used_mb": round(snap.mem_used_mb, 1),
            "mem_available_mb": round(snap.mem_available_mb, 1),
            "disk_percent": snap.disk_percent,
            "disk_free_gb": round(snap.disk_free_gb, 2),
            "process_cpu_percent": snap.process_cpu_percent,
            "process_mem_mb": round(snap.process_mem_mb, 1),
            "process_threads": snap.process_threads,
            "gc_collections": snap.gc_collections,
            "active_threads": threading.active_count(),
        }

    def check_resource_pressure(self) -> dict[str, bool]:
        """Return a dict of resource pressure flags."""
        from .monitoring_constants import CPU_WARN_PCT, MEM_WARN_PCT, DISK_WARN_PCT
        snap = self.latest() or DiagnosticSnapshot()
        return {
            "cpu_pressure": snap.cpu_percent >= CPU_WARN_PCT,
            "mem_pressure": snap.mem_percent >= MEM_WARN_PCT,
            "disk_pressure": snap.disk_percent >= DISK_WARN_PCT,
        }

    # ------------------------------------------------------------------
    # Internal collection
    # ------------------------------------------------------------------

    def _collect_system(self, snap: DiagnosticSnapshot) -> None:
        try:
            snap.cpu_percent = psutil.cpu_percent(interval=None)
            snap.cpu_count = psutil.cpu_count(logical=True) or 0
            mem = psutil.virtual_memory()
            snap.mem_total_mb = mem.total / 1024 / 1024
            snap.mem_used_mb = mem.used / 1024 / 1024
            snap.mem_available_mb = mem.available / 1024 / 1024
            snap.mem_percent = mem.percent
            try:
                disk = psutil.disk_usage(".")
                snap.disk_total_gb = disk.total / 1024 ** 3
                snap.disk_used_gb = disk.used / 1024 ** 3
                snap.disk_free_gb = disk.free / 1024 ** 3
                snap.disk_percent = disk.percent
            except Exception:
                pass
        except Exception as exc:
            _LOG.debug("System metrics collection error: %s", exc)

    def _collect_process(self, snap: DiagnosticSnapshot) -> None:
        if not self._proc:
            return
        try:
            with self._proc.oneshot():
                snap.process_cpu_percent = self._proc.cpu_percent(interval=None)
                snap.process_mem_mb = self._proc.memory_info().rss / 1024 / 1024
                snap.process_threads = self._proc.num_threads()
                try:
                    snap.process_open_files = len(self._proc.open_files())
                except Exception:
                    snap.process_open_files = 0
        except Exception as exc:
            _LOG.debug("Process metrics collection error: %s", exc)

    def _collect_gc(self, snap: DiagnosticSnapshot) -> None:
        try:
            counts = gc.get_count()
            snap.gc_collections = (counts[0], counts[1], counts[2])
        except Exception:
            pass

    def _collect_extras(self, snap: DiagnosticSnapshot) -> None:
        snap.extras["active_threads"] = threading.active_count()
        snap.extras["pid"] = os.getpid()
        snap.extras["uptime_seconds"] = round(time.monotonic() - self._start_time, 1)


def get_diagnostic_manager() -> DiagnosticManager:
    """Return (or create) the global ``DiagnosticManager`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = DiagnosticManager()
        return _instance


def _reset_diagnostic_manager() -> None:
    global _instance
    with _instance_lock:
        _instance = None

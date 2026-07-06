"""
iios/monitoring/health_checker.py
===================================
Individual health check implementations for IIOS subsystems.

Each check is a callable that returns a ``HealthCheckResult``.
All checks are designed to be safe: they catch their own exceptions and
return ``UNHEALTHY`` rather than propagating.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from .monitoring_constants import (
    CheckCategory,
    CPU_CRIT_PCT, CPU_WARN_PCT,
    DISK_CRIT_PCT, DISK_WARN_PCT,
    MEM_CRIT_PCT, MEM_WARN_PCT,
    HealthStatus,
)
from .monitoring_models import HealthCheckResult

__all__ = [
    "HealthCheck",
    "LambdaHealthCheck",
    "CPUHealthCheck",
    "MemoryHealthCheck",
    "DiskHealthCheck",
    "DatabaseHealthCheck",
    "ThreadPoolHealthCheck",
    "CallableHealthCheck",
    "ImportHealthCheck",
]


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class HealthCheck(ABC):
    """Abstract base for all health checks."""

    def __init__(
        self,
        name: str,
        category: str = CheckCategory.CUSTOM.value,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.name = name
        self.category = category
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def execute(self) -> HealthCheckResult:
        """Run the check and return a result. Must not raise."""

    def run(self) -> HealthCheckResult:
        """Run with timing and exception safety."""
        t_start = time.monotonic()
        try:
            result = self.execute()
        except Exception as exc:
            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY.value,
                category=self.category,
                message=f"Check raised unexpectedly: {type(exc).__name__}: {exc}",
                error=str(exc),
            )
        result.duration_ms = (time.monotonic() - t_start) * 1000
        return result


# ---------------------------------------------------------------------------
# Lambda / Callable check
# ---------------------------------------------------------------------------


class LambdaHealthCheck(HealthCheck):
    """Wraps an arbitrary callable that returns a bool or HealthCheckResult."""

    def __init__(
        self,
        name: str,
        fn: Callable[[], Any],
        category: str = CheckCategory.CUSTOM.value,
        timeout_seconds: float = 10.0,
        healthy_message: str = "OK",
        unhealthy_message: str = "Check failed",
    ) -> None:
        super().__init__(name, category, timeout_seconds)
        self._fn = fn
        self._healthy_msg = healthy_message
        self._unhealthy_msg = unhealthy_message

    def execute(self) -> HealthCheckResult:
        result = self._fn()
        if isinstance(result, HealthCheckResult):
            return result
        ok = bool(result)
        return HealthCheckResult(
            name=self.name,
            status=HealthStatus.HEALTHY.value if ok else HealthStatus.UNHEALTHY.value,
            category=self.category,
            message=self._healthy_msg if ok else self._unhealthy_msg,
        )


# Alias
CallableHealthCheck = LambdaHealthCheck


# ---------------------------------------------------------------------------
# System resource checks
# ---------------------------------------------------------------------------


class CPUHealthCheck(HealthCheck):
    """Checks CPU utilisation."""

    def __init__(
        self,
        warn_pct: float = CPU_WARN_PCT,
        crit_pct: float = CPU_CRIT_PCT,
        interval: float = 0.5,
    ) -> None:
        super().__init__("cpu", CheckCategory.SYSTEM.value)
        self._warn = warn_pct
        self._crit = crit_pct
        self._interval = interval

    def execute(self) -> HealthCheckResult:
        try:
            import psutil  # type: ignore
            cpu_pct = psutil.cpu_percent(interval=self._interval)
        except ImportError:
            # Fallback: read /proc/stat or return unknown
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN.value,
                category=self.category,
                message="psutil not available",
            )

        if cpu_pct >= self._crit:
            status = HealthStatus.UNHEALTHY.value
        elif cpu_pct >= self._warn:
            status = HealthStatus.DEGRADED.value
        else:
            status = HealthStatus.HEALTHY.value

        return HealthCheckResult(
            name=self.name,
            status=status,
            category=self.category,
            message=f"CPU {cpu_pct:.1f}%",
            details={"cpu_percent": cpu_pct, "warn": self._warn, "crit": self._crit},
        )


class MemoryHealthCheck(HealthCheck):
    """Checks memory utilisation."""

    def __init__(
        self,
        warn_pct: float = MEM_WARN_PCT,
        crit_pct: float = MEM_CRIT_PCT,
    ) -> None:
        super().__init__("memory", CheckCategory.SYSTEM.value)
        self._warn = warn_pct
        self._crit = crit_pct

    def execute(self) -> HealthCheckResult:
        try:
            import psutil
            mem = psutil.virtual_memory()
            pct = mem.percent
        except ImportError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN.value,
                category=self.category,
                message="psutil not available",
            )

        if pct >= self._crit:
            status = HealthStatus.UNHEALTHY.value
        elif pct >= self._warn:
            status = HealthStatus.DEGRADED.value
        else:
            status = HealthStatus.HEALTHY.value

        return HealthCheckResult(
            name=self.name,
            status=status,
            category=self.category,
            message=f"Memory {pct:.1f}%",
            details={
                "percent": pct,
                "available_mb": round(mem.available / 1024 / 1024, 1),
                "total_mb": round(mem.total / 1024 / 1024, 1),
            },
        )


class DiskHealthCheck(HealthCheck):
    """Checks disk utilisation for a given path."""

    def __init__(
        self,
        path: str = ".",
        warn_pct: float = DISK_WARN_PCT,
        crit_pct: float = DISK_CRIT_PCT,
    ) -> None:
        super().__init__("disk", CheckCategory.SYSTEM.value)
        self._path = path
        self._warn = warn_pct
        self._crit = crit_pct

    def execute(self) -> HealthCheckResult:
        try:
            import psutil
            du = psutil.disk_usage(self._path)
            pct = du.percent
        except ImportError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN.value,
                category=self.category,
                message="psutil not available",
            )
        except Exception as exc:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY.value,
                category=self.category,
                message=f"Disk check failed: {exc}",
                error=str(exc),
            )

        if pct >= self._crit:
            status = HealthStatus.UNHEALTHY.value
        elif pct >= self._warn:
            status = HealthStatus.DEGRADED.value
        else:
            status = HealthStatus.HEALTHY.value

        return HealthCheckResult(
            name=self.name,
            status=status,
            category=self.category,
            message=f"Disk {pct:.1f}%",
            details={
                "path": self._path,
                "percent": pct,
                "free_gb": round(du.free / 1024 ** 3, 2),
                "total_gb": round(du.total / 1024 ** 3, 2),
            },
        )


# ---------------------------------------------------------------------------
# Database health check
# ---------------------------------------------------------------------------


class DatabaseHealthCheck(HealthCheck):
    """Checks SQLite database accessibility."""

    def __init__(self, db_path: str, name: str = "database") -> None:
        super().__init__(name, CheckCategory.DATABASE.value)
        self._db_path = db_path

    def execute(self) -> HealthCheckResult:
        import os
        if not os.path.exists(self._db_path) and self._db_path != ":memory:":
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY.value,
                category=self.category,
                message=f"Database file not found: {self._db_path}",
            )
        try:
            conn = sqlite3.connect(self._db_path, timeout=5.0)
            conn.execute("SELECT 1")
            conn.close()
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY.value,
                category=self.category,
                message="Database reachable",
                details={"path": self._db_path},
            )
        except Exception as exc:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY.value,
                category=self.category,
                message=f"Database error: {exc}",
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# Thread pool health check
# ---------------------------------------------------------------------------


class ThreadPoolHealthCheck(HealthCheck):
    """Reports current thread count vs a configured maximum."""

    def __init__(self, max_threads: int = 200) -> None:
        super().__init__("thread_pool", CheckCategory.SYSTEM.value)
        self._max = max_threads

    def execute(self) -> HealthCheckResult:
        count = threading.active_count()
        pct = (count / self._max) * 100
        if pct >= 90:
            status = HealthStatus.UNHEALTHY.value
        elif pct >= 75:
            status = HealthStatus.DEGRADED.value
        else:
            status = HealthStatus.HEALTHY.value

        return HealthCheckResult(
            name=self.name,
            status=status,
            category=self.category,
            message=f"Threads: {count}/{self._max}",
            details={"active": count, "max": self._max, "percent": round(pct, 1)},
        )


# ---------------------------------------------------------------------------
# Import / dependency check
# ---------------------------------------------------------------------------


class ImportHealthCheck(HealthCheck):
    """Checks whether a Python package is importable."""

    def __init__(self, package_name: str) -> None:
        super().__init__(f"import:{package_name}", CheckCategory.DEPENDENCY.value)
        self._pkg = package_name

    def execute(self) -> HealthCheckResult:
        import importlib
        try:
            importlib.import_module(self._pkg)
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY.value,
                category=self.category,
                message=f"{self._pkg} importable",
            )
        except ImportError as exc:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY.value,
                category=self.category,
                message=f"{self._pkg} not available: {exc}",
                error=str(exc),
            )

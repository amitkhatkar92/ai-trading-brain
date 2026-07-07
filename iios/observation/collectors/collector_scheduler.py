"""
iios/observation/collectors/collector_scheduler.py
==================================================
CollectorScheduler — background scheduling engine.

Supports INTERVAL, MARKET_HOURS, and EVENT-triggered schedules.
CRON and DEPENDENCY schedules are dispatched to future extensions.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .base_collector       import BaseCollector
from .collector_constants  import ScheduleType
from .collector_exceptions import CollectorScheduleError
from .scheduled_collector  import ScheduleConfig

__all__ = ["ScheduledJob", "CollectorScheduler", "get_collector_scheduler", "reset_collector_scheduler"]

_LOG  = logging.getLogger("iios.collector.scheduler")
_lock = threading.Lock()
_sched: Optional["CollectorScheduler"] = None


@dataclass
class ScheduledJob:
    job_id:       str
    collector:    BaseCollector
    schedule:     ScheduleConfig
    next_run_at:  float = 0.0
    last_run_at:  float = 0.0
    run_count:    int   = 0
    enabled:      bool  = True


class CollectorScheduler:
    """
    Background thread that ticks every ``tick_interval_s`` seconds
    and runs due collectors.
    """

    def __init__(self, tick_interval_s: float = 5.0) -> None:
        self._tick_s          = tick_interval_s
        self._lock            = threading.RLock()
        self._jobs:           dict[str, ScheduledJob] = {}
        self._event_listeners: dict[str, list[ScheduledJob]] = {}
        self._running         = False
        self._thread:         Optional[threading.Thread] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def add(
        self,
        collector: BaseCollector,
        schedule:  Optional[ScheduleConfig] = None,
        enabled:   bool = True,
    ) -> str:
        """Register a collector. Returns job_id."""
        if schedule is None:
            schedule = getattr(collector, "schedule", None) or ScheduleConfig()
        job_id = f"{collector.name}:{uuid.uuid4().hex[:8]}"
        now    = time.time()
        job    = ScheduledJob(
            job_id      = job_id,
            collector   = collector,
            schedule    = schedule,
            next_run_at = now + schedule.interval_s if schedule.schedule_type == ScheduleType.INTERVAL else 0.0,
            enabled     = enabled,
        )
        with self._lock:
            self._jobs[job_id] = job
            if schedule.schedule_type == ScheduleType.EVENT:
                for ev in schedule.event_names:
                    self._event_listeners.setdefault(ev, []).append(job)
        _LOG.debug("Scheduled '%s' (job=%s, type=%s)", collector.name, job_id, schedule.schedule_type.value)
        return job_id

    def remove(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def enable(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].enabled = True

    def disable(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].enabled = False

    def start(self) -> None:
        """Start the background scheduling thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread  = threading.Thread(
                target=self._loop, daemon=True, name="CollectorScheduler"
            )
            self._thread.start()
            _LOG.info("CollectorScheduler started (tick=%.1fs)", self._tick_s)

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=self._tick_s + 2.0)
            self._thread = None
        _LOG.info("CollectorScheduler stopped")

    def trigger_event(self, event_name: str) -> int:
        """Fire all collectors subscribed to *event_name*. Returns count triggered."""
        with self._lock:
            jobs = [j for j in self._event_listeners.get(event_name, []) if j.enabled]
        for job in jobs:
            self._run_job(job)
        return len(jobs)

    def trigger_now(self, job_id: str) -> None:
        """Manually trigger a specific job immediately."""
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise CollectorScheduleError(f"Job not found: {job_id!r}")
        self._run_job(job)

    def job_ids_for(self, collector_name: str) -> list[str]:
        with self._lock:
            return [jid for jid, j in self._jobs.items()
                    if j.collector.name == collector_name]

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running":   self._running,
                "job_count": len(self._jobs),
                "jobs": {
                    jid: {
                        "collector":    j.collector.name,
                        "schedule":     j.schedule.schedule_type.value,
                        "next_run_at":  j.next_run_at,
                        "run_count":    j.run_count,
                        "enabled":      j.enabled,
                    }
                    for jid, j in self._jobs.items()
                },
            }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception as exc:
                _LOG.error("Scheduler tick error: %s", exc)
            time.sleep(self._tick_s)

    def _tick(self) -> None:
        now = time.time()
        with self._lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            if not job.enabled:
                continue
            st = job.schedule.schedule_type
            if st == ScheduleType.INTERVAL:
                if now >= job.next_run_at > 0:
                    self._run_job(job)
            elif st == ScheduleType.MARKET_HOURS:
                if self._is_market_hours(job.schedule) and \
                        (now - job.last_run_at) >= job.schedule.interval_s:
                    self._run_job(job)

    def _run_job(self, job: ScheduledJob) -> None:
        try:
            job.collector.run()
        except Exception as exc:
            _LOG.warning("Scheduled run failed [%s]: %s", job.collector.name, exc)
        finally:
            now             = time.time()
            job.last_run_at = now
            job.run_count  += 1
            if job.schedule.interval_s > 0:
                job.next_run_at = now + job.schedule.interval_s

    @staticmethod
    def _is_market_hours(schedule: ScheduleConfig) -> bool:
        """Return True during NSE trading hours (09:15–15:30 IST, Mon–Fri)."""
        import datetime
        try:
            import zoneinfo  # Python 3.9+
            tz = zoneinfo.ZoneInfo(schedule.timezone or "Asia/Kolkata")
        except Exception:
            from datetime import timezone, timedelta
            tz = timezone(timedelta(hours=5, minutes=30))
        now    = datetime.datetime.now(tz)
        if now.weekday() >= 5:
            return False
        open_  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        close_ = now.replace(hour=15, minute=30, second=0, microsecond=0)
        return open_ <= now <= close_


def get_collector_scheduler() -> CollectorScheduler:
    global _sched
    if _sched is None:
        with _lock:
            if _sched is None:
                _sched = CollectorScheduler()
    return _sched


def reset_collector_scheduler() -> None:
    global _sched
    with _lock:
        if _sched is not None:
            try:
                _sched.stop()
            except Exception:
                pass
        _sched = None

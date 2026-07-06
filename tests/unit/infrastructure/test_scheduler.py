"""
tests/unit/infrastructure/test_scheduler.py
===========================================
Tests for the iios.infrastructure.scheduler subpackage.
"""

from __future__ import annotations

import datetime
import time
import pytest

from iios.infrastructure.scheduler import (
    CronExpression, IntervalSchedule, JobScheduler, get_scheduler, reset_scheduler,
    SchedulerRegistry,
)
from iios.infrastructure.infrastructure_constants import JobType
from iios.infrastructure.infrastructure_models import JobDefinition
from iios.infrastructure.infrastructure_exceptions import SchedulerError


class TestCronExpression:
    def test_every_minute(self):
        cron = CronExpression("* * * * *")
        assert cron.matches(datetime.datetime.now())

    def test_specific_time(self):
        cron = CronExpression("30 9 * * *")
        dt = datetime.datetime(2026, 1, 5, 9, 30)
        assert cron.matches(dt)
        dt_wrong = datetime.datetime(2026, 1, 5, 9, 31)
        assert not cron.matches(dt_wrong)

    def test_step(self):
        cron = CronExpression("*/15 * * * *")
        assert cron.matches(datetime.datetime(2026, 1, 1, 10, 0))
        assert cron.matches(datetime.datetime(2026, 1, 1, 10, 15))
        assert cron.matches(datetime.datetime(2026, 1, 1, 10, 30))
        assert not cron.matches(datetime.datetime(2026, 1, 1, 10, 7))

    def test_range(self):
        cron = CronExpression("0 9-17 * * *")
        assert cron.matches(datetime.datetime(2026, 1, 1, 12, 0))
        assert not cron.matches(datetime.datetime(2026, 1, 1, 18, 0))

    def test_weekday(self):
        # Monday–Friday (1–5 in cron, 0=Sunday)
        cron = CronExpression("0 9 * * 1-5")
        monday = datetime.datetime(2026, 5, 4, 9, 0)  # May 4 2026 = Monday
        saturday = datetime.datetime(2026, 5, 9, 9, 0)
        assert cron.matches(monday)
        assert not cron.matches(saturday)

    def test_next_fire_in_future(self):
        cron = CronExpression("* * * * *")
        now = datetime.datetime.now()
        nxt = cron.next_fire(after=now)
        assert nxt > now

    def test_invalid_expression_raises(self):
        with pytest.raises(ValueError):
            CronExpression("* * *")  # only 3 fields

    def test_str(self):
        expr = "*/5 9-17 * * 1-5"
        cron = CronExpression(expr)
        assert str(cron) == expr


class TestIntervalSchedule:
    def test_is_due(self):
        sched = IntervalSchedule(seconds=0.01)
        assert not sched.is_due()  # just created, next is 0.01s away
        time.sleep(0.02)
        assert sched.is_due()

    def test_mark_fired(self):
        sched = IntervalSchedule(seconds=60)
        # Not due initially
        time.sleep(0.01)
        # Force fire
        sched._next = datetime.datetime.now() - datetime.timedelta(seconds=1)
        assert sched.is_due()
        sched.mark_fired()
        assert not sched.is_due()

    def test_next_fire_advance(self):
        sched = IntervalSchedule(seconds=30)
        before = sched.next_fire
        sched._next = datetime.datetime.now()
        sched.mark_fired()
        assert sched.next_fire > before


class TestSchedulerRegistry:
    def test_add_and_get(self):
        reg = SchedulerRegistry()
        job = JobDefinition(
            job_id="j1",
            name="test",
            job_type=JobType.ONCE,
            callable_path="test.fn",
            schedule="",
        )
        reg.add(job)
        assert reg.get("j1").name == "test"

    def test_add_duplicate_raises(self):
        reg = SchedulerRegistry()
        job = JobDefinition(
            job_id="j1", name="test", job_type=JobType.ONCE,
            callable_path="test.fn", schedule=""
        )
        reg.add(job)
        with pytest.raises(SchedulerError):
            reg.add(job)

    def test_remove(self):
        reg = SchedulerRegistry()
        job = JobDefinition(
            job_id="j1", name="test", job_type=JobType.ONCE,
            callable_path="test.fn", schedule=""
        )
        reg.add(job)
        assert reg.remove("j1")
        with pytest.raises(SchedulerError):
            reg.get("j1")

    def test_enable_disable(self):
        reg = SchedulerRegistry()
        job = JobDefinition(
            job_id="j1", name="test", job_type=JobType.ONCE,
            callable_path="test.fn", schedule=""
        )
        reg.add(job)
        reg.disable("j1")
        assert not reg.enabled()
        reg.enable("j1")
        assert len(reg.enabled()) == 1


class TestJobScheduler:
    def setup_method(self):
        reset_scheduler()

    def teardown_method(self):
        reset_scheduler()

    def test_start_stop(self):
        sched = JobScheduler(tick=0.05)
        sched.start()
        assert sched.is_running
        sched.stop()
        assert not sched.is_running

    def test_once_job_fires(self):
        fired = []
        sched = JobScheduler(tick=0.02)
        sched.start()
        sched.add_once("test", lambda: fired.append(1))
        deadline = time.monotonic() + 2.0
        while not fired and time.monotonic() < deadline:
            time.sleep(0.05)
        assert fired, "Once job did not fire"
        sched.stop()

    def test_interval_job_fires_multiple(self):
        fired = []
        sched = JobScheduler(tick=0.02)
        sched.start()
        sched.add_interval("heartbeat", 0.05, lambda: fired.append(1))
        time.sleep(0.3)
        sched.stop()
        assert len(fired) >= 3, f"Expected >= 3 fires, got {len(fired)}"

    def test_remove_job(self):
        fired = []
        sched = JobScheduler(tick=0.02)
        sched.start()
        jid = sched.add_once("test", lambda: fired.append(1))
        sched.remove(jid)
        time.sleep(0.1)
        sched.stop()
        assert not fired, "Removed job should not have fired"

    def test_stats(self):
        sched = JobScheduler(tick=0.02)
        sched.start()
        sched.add_once("x", lambda: None)
        time.sleep(0.2)
        sched.stop()
        stats = sched.stats()
        assert stats["total_runs"] >= 1

    def test_global_singleton(self):
        s1 = get_scheduler()
        s2 = get_scheduler()
        assert s1 is s2

    def test_failed_job_counted(self):
        sched = JobScheduler(tick=0.02)
        sched.start()
        sched.add_once("failing", lambda: (_ for _ in ()).throw(RuntimeError("bad")))
        time.sleep(0.3)
        sched.stop()
        stats = sched.stats()
        assert stats["total_failures"] >= 1

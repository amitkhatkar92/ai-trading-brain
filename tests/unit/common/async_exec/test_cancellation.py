"""Tests for iios.common.async_exec.cancellation"""
import asyncio
import threading
import time
from iios.common.async_exec.cancellation import (
    CancellationToken,
    CancellationScope,
    LinkedCancellationToken,
    create_token,
)


# ── CancellationToken ─────────────────────────────────────────────────────────

class TestCancellationToken:

    def test_initially_not_cancelled(self):
        token = CancellationToken()
        assert not token.is_cancelled()

    def test_cancel_sets_flag(self):
        token = CancellationToken()
        token.cancel()
        assert token.is_cancelled()

    def test_cancel_with_reason(self):
        token = CancellationToken()
        token.cancel("shutdown")
        assert token.cancel_reason == "shutdown"

    def test_cancel_sets_timestamp(self):
        token = CancellationToken()
        token.cancel()
        assert token.cancel_time is not None

    def test_cancel_idempotent(self):
        token = CancellationToken()
        token.cancel("first")
        token.cancel("second")           # should not overwrite reason
        assert token.cancel_reason == "first"

    def test_check_raises_cancelled_error_when_cancelled(self):
        token = CancellationToken()
        token.cancel("stop now")
        try:
            token.check()
            assert False, "Expected CancelledError"
        except asyncio.CancelledError:
            pass

    def test_check_does_not_raise_when_not_cancelled(self):
        token = CancellationToken()
        token.check()   # must not raise

    def test_reason_in_cancelled_error_message(self):
        token = CancellationToken()
        token.cancel("test reason")
        try:
            token.check()
        except asyncio.CancelledError as exc:
            assert "test reason" in str(exc)

    def test_empty_reason_is_ok(self):
        token = CancellationToken()
        token.cancel()
        assert token.cancel_reason == ""

    def test_repr(self):
        token = CancellationToken()
        r = repr(token)
        assert "CancellationToken" in r
        assert "False" in r
        token.cancel("x")
        r2 = repr(token)
        assert "True" in r2

    # ── Async wait ────────────────────────────────────────────────────────────

    def test_wait_returns_immediately_if_already_cancelled(self):
        token = CancellationToken()
        token.cancel()
        asyncio.run(token.wait())   # must return immediately, not hang

    def test_wait_returns_when_cancelled_from_thread(self):
        token = CancellationToken()

        async def run():
            async def cancel_soon():
                await asyncio.sleep(0.05)
                token.cancel("from_async")
            asyncio.create_task(cancel_soon())
            await token.wait()

        asyncio.run(run())
        assert token.is_cancelled()

    def test_thread_safe_cancel(self):
        token = CancellationToken()
        errors = []
        def cancel_thread():
            try:
                token.cancel("from thread")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=cancel_thread) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert token.is_cancelled()
        assert not errors

    # ── Cleanup callbacks ─────────────────────────────────────────────────────

    def test_sync_cleanup_runs(self):
        called = []
        token  = CancellationToken()
        token.add_cleanup(lambda: called.append("sync"))
        asyncio.run(token.run_cleanup())
        assert "sync" in called

    def test_async_cleanup_runs(self):
        called = []

        async def async_cleanup():
            called.append("async")

        token = CancellationToken()
        token.add_cleanup(async_cleanup)
        asyncio.run(token.run_cleanup())
        assert "async" in called

    def test_multiple_cleanups_all_run(self):
        called = []
        token  = CancellationToken()
        for i in range(5):
            idx = i
            token.add_cleanup(lambda i=idx: called.append(i))
        asyncio.run(token.run_cleanup())
        assert sorted(called) == [0, 1, 2, 3, 4]

    def test_cleanup_exception_does_not_stop_others(self):
        called = []
        token  = CancellationToken()
        token.add_cleanup(lambda: (_ for _ in ()).throw(ValueError("boom")))
        token.add_cleanup(lambda: called.append("after_error"))
        asyncio.run(token.run_cleanup())
        assert "after_error" in called

    def test_run_cleanup_sync_skips_async_callbacks(self):
        sync_called  = []
        async_called = []

        async def async_cb():
            async_called.append(1)

        token = CancellationToken()
        token.add_cleanup(lambda: sync_called.append(1))
        token.add_cleanup(async_cb)
        token.run_cleanup_sync()
        assert sync_called == [1]
        # async_called is NOT populated (coroutine was closed without running)


# ── CancellationScope ─────────────────────────────────────────────────────────

class TestCancellationScope:

    def test_scope_allows_normal_completion(self):
        async def run():
            token = CancellationToken()
            async with CancellationScope(token):
                return "done"
        result = asyncio.run(run())
        assert result == "done"

    def test_scope_raises_on_pre_cancelled_token(self):
        async def run():
            token = CancellationToken()
            token.cancel("before enter")
            async with CancellationScope(token):
                return "should not reach"
        try:
            asyncio.run(run())
            assert False
        except asyncio.CancelledError:
            pass

    def test_scope_propagates_cancellation(self):
        async def run():
            token = CancellationToken()

            async def cancel_soon():
                await asyncio.sleep(0.05)
                token.cancel("interrupt")

            asyncio.create_task(cancel_soon())
            async with CancellationScope(token):
                await asyncio.sleep(10)

        try:
            asyncio.run(run())
            assert False
        except asyncio.CancelledError:
            pass

    def test_scope_cleanup_runs_on_normal_exit(self):
        cleaned = []

        async def run():
            token = CancellationToken()
            token.add_cleanup(lambda: cleaned.append(1))
            async with CancellationScope(token):
                pass

        asyncio.run(run())
        assert cleaned == [1]

    def test_scope_token_property(self):
        async def run():
            token = CancellationToken()
            scope = CancellationScope(token)
            assert scope.token is token

        asyncio.run(run())

    def test_scope_creates_token_if_not_given(self):
        async def run():
            scope = CancellationScope()
            assert scope.token is not None
            async with scope:
                pass

        asyncio.run(run())


# ── create_token ──────────────────────────────────────────────────────────────

class TestCreateToken:

    def test_returns_cancellation_token(self):
        token = create_token()
        assert isinstance(token, CancellationToken)

    def test_new_token_not_cancelled(self):
        token = create_token()
        assert not token.is_cancelled()


# ── LinkedCancellationToken ───────────────────────────────────────────────────

class TestLinkedCancellationToken:

    def test_linked_not_cancelled_initially(self):
        parent = CancellationToken()
        linked = LinkedCancellationToken(parent)
        assert not linked.is_cancelled()

    def test_linked_fires_when_parent_fires(self):
        parent = CancellationToken()
        linked = LinkedCancellationToken(parent)
        parent.cancel("parent stop")
        # Propagation is immediate — no cleanup() call required
        assert linked.is_cancelled()

    def test_link_factory(self):
        p1 = CancellationToken()
        p2 = CancellationToken()
        linked = LinkedCancellationToken.link(p1, p2)
        assert isinstance(linked, LinkedCancellationToken)

    def test_cancelling_linked_does_not_affect_parent(self):
        parent = CancellationToken()
        linked = LinkedCancellationToken(parent)
        linked.cancel("child only")
        assert not parent.is_cancelled()

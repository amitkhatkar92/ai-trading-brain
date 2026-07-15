"""iios/common/async_exec/cancellation.py
Graceful cancellation support for the IIOS async execution framework.

Provides:
  • ``CancellationToken``  — lightweight token that signals cancellation
  • ``CancellationScope``  — async context manager binding token to a coro
  • ``create_token``       — factory function

Cancellation is cooperative: the running coroutine must periodically call
``token.check()`` or ``await token.wait()`` to observe cancellation.

Cleanup callbacks run on cancellation regardless of whether the operation
completed normally or was interrupted.

Usage::

    from iios.common.async_exec.cancellation import CancellationToken

    token = CancellationToken()

    async def process(token: CancellationToken):
        for batch in batches:
            token.check()   # raises CancelledError if cancelled
            await process_batch(batch)

    # From another thread or task:
    token.cancel("user requested stop")
"""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from typing import Callable, List, Optional


# ── CancellationToken ─────────────────────────────────────────────────────────

class CancellationToken:
    """
    Thread-safe cancellation signal.

    ``cancel()`` is safe to call from any thread.
    ``check()`` and ``wait()`` are for use in the coroutine that should
    honour the cancellation.

    Cleanup callbacks are called in registration order when ``run_cleanup()``
    is called.  They may be sync or async; async callbacks require an event loop.
    """

    def __init__(self) -> None:
        self._lock:           threading.Lock          = threading.Lock()
        self._cancelled:      bool                    = False
        self._cancel_reason:  str                     = ""
        self._cancel_time:    Optional[datetime]      = None
        self._cancel_callbacks: List[Callable]        = []   # fire immediately on cancel()
        self._cleanup_fns:    List[Callable]          = []   # fire on explicit run_cleanup()
        # asyncio.Event used for efficient async waiting — created lazily
        self._async_event:    Optional[asyncio.Event] = None

    # ── Cancellation control ──────────────────────────────────────────────────

    def cancel(self, reason: str = "") -> None:
        """
        Signal cancellation.

        Idempotent — calling multiple times is safe.
        """
        with self._lock:
            if self._cancelled:
                return
            self._cancelled      = True
            self._cancel_reason  = reason
            self._cancel_time    = datetime.now(timezone.utc)
            callbacks = list(self._cancel_callbacks)

        # Run immediate cancel callbacks synchronously (outside lock to prevent deadlock)
        for cb in callbacks:
            try:
                cb()
            except Exception:
                pass

        # Signal the asyncio event if it was created in an event loop context
        if self._async_event is not None:
            try:
                loop = self._async_event._loop  # type: ignore[attr-defined]
                if loop is not None and loop.is_running():
                    loop.call_soon_threadsafe(self._async_event.set)
                else:
                    self._async_event.set()
            except Exception:
                try:
                    self._async_event.set()
                except Exception:
                    pass

    def is_cancelled(self) -> bool:
        """Return True if cancellation has been requested."""
        return self._cancelled

    def check(self) -> None:
        """
        Raise ``asyncio.CancelledError`` if this token is cancelled.

        Call this at cooperative check-points in long-running operations.
        """
        if self._cancelled:
            raise asyncio.CancelledError(
                f"Cancelled: {self._cancel_reason}" if self._cancel_reason
                else "Cancelled"
            )

    async def wait(self) -> None:
        """
        Await until this token is cancelled.

        If already cancelled, returns immediately.
        Must be called from within an asyncio event loop.
        """
        if self._cancelled:
            return
        if self._async_event is None:
            self._async_event = asyncio.Event()
            if self._cancelled:   # race: check again after creating event
                self._async_event.set()
        await self._async_event.wait()

    # ── Cleanup callbacks ─────────────────────────────────────────────────────

    def add_on_cancel(self, fn: Callable) -> None:
        """
        Register a callback that fires IMMEDIATELY and synchronously when
        ``cancel()`` is called.

        Use this for propagating cancellation to linked tokens or for
        actions that must happen the instant cancellation is signalled.
        """
        with self._lock:
            if self._cancelled:
                # Already cancelled — run the callback immediately
                pass
            else:
                self._cancel_callbacks.append(fn)
                return
        # Token was already cancelled when we tried to register — call now
        try:
            fn()
        except Exception:
            pass

    def add_cleanup(self, fn: Callable) -> None:
        """
        Register a cleanup callback to run on cancellation.

        Callbacks may be sync callables (``fn()``) or async coroutine
        functions (``async def fn()``).
        """
        with self._lock:
            self._cleanup_fns.append(fn)

    async def run_cleanup(self) -> None:
        """
        Execute all registered cleanup callbacks in registration order.

        Exceptions from individual callbacks are suppressed to ensure
        all callbacks run.  Each async callback is awaited.
        """
        fns = list(self._cleanup_fns)
        for fn in fns:
            try:
                result = fn()
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

    def run_cleanup_sync(self) -> None:
        """
        Execute only synchronous cleanup callbacks.

        Safe to call from non-async contexts.
        """
        fns = list(self._cleanup_fns)
        for fn in fns:
            try:
                result = fn()
                # If fn returned a coroutine, close it to avoid warnings
                if asyncio.iscoroutine(result):
                    result.close()
            except Exception:
                pass

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def cancel_reason(self) -> str:
        return self._cancel_reason

    @property
    def cancel_time(self) -> Optional[datetime]:
        return self._cancel_time

    def __repr__(self) -> str:
        return (
            f"CancellationToken(cancelled={self._cancelled}, "
            f"reason={self._cancel_reason!r})"
        )


# ── CancellationScope ─────────────────────────────────────────────────────────

class CancellationScope:
    """
    Async context manager that binds a CancellationToken to a code block.

    When the token is cancelled, raises ``asyncio.CancelledError`` at the
    next ``await`` point within the block.

    On exit (normal or cancelled), registered cleanup callbacks are run.

    Usage::

        token = CancellationToken()
        scope = CancellationScope(token)

        async with scope:
            result = await long_running_operation()
    """

    def __init__(
        self,
        token:   Optional[CancellationToken] = None,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        self._token:   CancellationToken       = token or CancellationToken()
        self._timeout: Optional[float]         = timeout
        self._task:    Optional[asyncio.Task]  = None

    @property
    def token(self) -> CancellationToken:
        return self._token

    async def __aenter__(self) -> "CancellationScope":
        self._task = asyncio.current_task()
        if self._token.is_cancelled():
            raise asyncio.CancelledError("CancellationScope entered with already-cancelled token")
        # Start a watcher task that cancels the current task when the token fires
        self._watcher = asyncio.create_task(self._watch())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._watcher and not self._watcher.done():
            self._watcher.cancel()
            try:
                await self._watcher
            except asyncio.CancelledError:
                pass
        await self._token.run_cleanup()
        return False   # do not suppress exceptions

    async def _watch(self) -> None:
        """Internal watcher: cancels the parent task when the token fires."""
        await self._token.wait()
        if self._task and not self._task.done():
            self._task.cancel(f"CancellationScope: {self._token.cancel_reason}")


# ── Factory ───────────────────────────────────────────────────────────────────

def create_token() -> CancellationToken:
    """Create a new, unset CancellationToken."""
    return CancellationToken()


# ── Linked tokens ─────────────────────────────────────────────────────────────

class LinkedCancellationToken(CancellationToken):
    """
    A CancellationToken that is also cancelled when any of its parent
    tokens are cancelled.

    Supports partial cancellation: cancel one linked token without
    affecting the parent or other linked tokens.
    """

    def __init__(self, *parents: CancellationToken) -> None:
        super().__init__()
        for parent in parents:
            parent.add_on_cancel(lambda: self.cancel("parent cancelled"))

    @classmethod
    def link(cls, *tokens: CancellationToken) -> "LinkedCancellationToken":
        """Create a linked token that fires when ANY of *tokens* fires."""
        return cls(*tokens)

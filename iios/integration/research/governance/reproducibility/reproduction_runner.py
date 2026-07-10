"""reproducibility/reproduction_runner.py — Async runner that verifies deterministic output."""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

from iios.integration.research.governance.governance_constants import ReproducibilityStatus
from iios.integration.research.governance.governance_exceptions import ReproductionRunError


@dataclass
class ReproductionResult:
    """
    Result of a single reproduction attempt.
    """
    run_id:       str
    entity_id:    str
    attempt:      int
    status:       ReproducibilityStatus
    elapsed_sec:  float
    error:        Optional[str]
    output_hash:  Optional[str]
    started_at:   float
    completed_at: float
    metadata:     dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id":        self.run_id,
            "entity_id":     self.entity_id,
            "attempt":       self.attempt,
            "status":        self.status.value,
            "elapsed_sec":   self.elapsed_sec,
            "error":         self.error,
            "output_hash":   self.output_hash,
            "started_at":    self.started_at,
            "completed_at":  self.completed_at,
        }


class ReproductionRunner:
    """
    Executes a caller-supplied async callable and records whether the output
    hash matches a reference, concluding whether the run is reproducible.

    The runner does not know the meaning of the output — it only hashes the
    ``str()`` representation of whatever the callable returns.
    """

    async def run(
        self,
        entity_id:    str,
        fn:           Callable[[], Coroutine[Any, Any, Any]],
        *,
        reference_hash: Optional[str] = None,
        attempt:        int           = 1,
        timeout_sec:    float         = 300.0,
        metadata:       Optional[dict] = None,
    ) -> ReproductionResult:
        import hashlib
        run_id     = f"repr_{uuid.uuid4().hex[:10]}"
        started_at = time.time()
        try:
            output = await asyncio.wait_for(fn(), timeout=timeout_sec)
        except asyncio.TimeoutError as exc:
            elapsed = time.time() - started_at
            return ReproductionResult(
                run_id       = run_id,
                entity_id    = entity_id,
                attempt      = attempt,
                status       = ReproducibilityStatus.FAILED,
                elapsed_sec  = elapsed,
                error        = f"Timeout after {timeout_sec}s",
                output_hash  = None,
                started_at   = started_at,
                completed_at = time.time(),
                metadata     = metadata or {},
            )
        except Exception as exc:
            elapsed = time.time() - started_at
            return ReproductionResult(
                run_id       = run_id,
                entity_id    = entity_id,
                attempt      = attempt,
                status       = ReproducibilityStatus.FAILED,
                elapsed_sec  = elapsed,
                error        = str(exc),
                output_hash  = None,
                started_at   = started_at,
                completed_at = time.time(),
                metadata     = metadata or {},
            )

        output_hash = hashlib.sha256(str(output).encode()).hexdigest()
        completed   = time.time()
        if reference_hash is None:
            status = ReproducibilityStatus.UNKNOWN
        elif output_hash == reference_hash:
            status = ReproducibilityStatus.VERIFIED
        else:
            status = ReproducibilityStatus.FAILED
        return ReproductionResult(
            run_id       = run_id,
            entity_id    = entity_id,
            attempt      = attempt,
            status       = status,
            elapsed_sec  = completed - started_at,
            error        = None,
            output_hash  = output_hash,
            started_at   = started_at,
            completed_at = completed,
            metadata     = metadata or {},
        )

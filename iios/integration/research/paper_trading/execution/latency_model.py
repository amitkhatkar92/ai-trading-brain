"""execution/latency_model.py — Simulated order submission and fill latency."""
from __future__ import annotations


class LatencyModel:
    """
    Simulates deterministic or random latency for order submission and fills.

    All latency values are in **seconds** to align with Unix timestamps.
    """

    def __init__(
        self,
        submission_ms:    float = 0.0,
        fill_ms:          float = 0.0,
        random_jitter_ms: float = 0.0,
    ) -> None:
        self._submission  = max(0.0, submission_ms)
        self._fill        = max(0.0, fill_ms)
        self._jitter      = max(0.0, random_jitter_ms)

    def submission_delay(self) -> float:
        """Return order submission latency in seconds."""
        return (self._submission + self._jitter_sample()) / 1_000.0

    def fill_delay(self) -> float:
        """Return fill latency in seconds."""
        return (self._fill + self._jitter_sample()) / 1_000.0

    def _jitter_sample(self) -> float:
        if self._jitter <= 0.0:
            return 0.0
        import random
        return random.uniform(0.0, self._jitter)

    @property
    def submission_ms(self) -> float:
        return self._submission

    @property
    def fill_ms(self) -> float:
        return self._fill

    @property
    def random_jitter_ms(self) -> float:
        return self._jitter

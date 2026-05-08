"""Token bucket rate limiter for Riot API."""

import asyncio
import time


class TokenBucketRateLimiter:
    """Dual token bucket: per-second + per-2-minute limits."""

    def __init__(
        self,
        per_second: int = 20,
        per_2min: int = 100,
        max_concurrent: int = 20,
    ) -> None:
        self._per_second = per_second
        self._per_2min = per_2min
        self._semaphore = asyncio.Semaphore(max_concurrent)

        self._tokens_sec = float(per_second)
        self._tokens_2min = float(per_2min)
        self._last_refill_sec = time.monotonic()
        self._last_refill_2min = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available, then consume one."""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens_sec >= 1.0 and self._tokens_2min >= 1.0:
                    self._tokens_sec -= 1.0
                    self._tokens_2min -= 1.0
                    break

            await asyncio.sleep(0.05)

        await self._semaphore.acquire()

    def release(self) -> None:
        """Release the concurrency semaphore after request completes."""
        self._semaphore.release()

    def _refill(self) -> None:
        now = time.monotonic()

        elapsed_sec = now - self._last_refill_sec
        self._tokens_sec = min(
            float(self._per_second),
            self._tokens_sec + elapsed_sec * self._per_second,
        )
        self._last_refill_sec = now

        elapsed_2min = now - self._last_refill_2min
        self._tokens_2min = min(
            float(self._per_2min),
            self._tokens_2min + elapsed_2min * (self._per_2min / 120.0),
        )
        self._last_refill_2min = now

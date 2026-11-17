"""Detection of a lost connection with the operator.

The operator interface sends a heartbeat at a regular interval. When no
heartbeat arrives within the timeout, the safety action runs once (sitting
position). A new heartbeat re-arms the watchdog.
"""

import time
from collections.abc import Awaitable, Callable


class ConnectionWatchdog:
    """Runs ``on_lost`` once when heartbeats stop for longer than ``timeout_s``."""

    def __init__(
        self,
        on_lost: Callable[[], Awaitable[None]],
        *,
        timeout_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout must be positive")
        self._on_lost = on_lost
        self._timeout_s = timeout_s
        self._clock = clock
        self._last_heartbeat: float | None = None
        self._triggered = False

    def heartbeat(self) -> None:
        """Record a heartbeat from the operator."""
        self._last_heartbeat = self._clock()
        self._triggered = False

    async def check(self) -> None:
        """Run the safety action if the heartbeat has expired. Called periodically."""
        if self._last_heartbeat is None or self._triggered:
            return
        if self._clock() - self._last_heartbeat > self._timeout_s:
            self._triggered = True
            await self._on_lost()

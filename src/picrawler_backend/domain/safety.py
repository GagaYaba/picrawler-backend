"""Safety layer applied to every robot command, whatever the implementation.

Rules from the project (7 November 2026):
- speed limited to the cautious range 20 to 70;
- at least 0.25 s between two actions;
- one command at a time (never two programs driving the servos together);
- emergency stop never waits for another command;
- sitting position when the connection with the operator is lost.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

from picrawler_backend.domain.robot_port import (
    Direction,
    RobotError,
    RobotPort,
    Telemetry,
    TurnDirection,
)

MIN_SAFE_SPEED = 20
MAX_SAFE_SPEED = 70
MIN_INTERVAL_S = 0.25


class SafetyLimitError(RobotError):
    """Raised when a command exceeds a safety limit. The command is not sent."""


class SafeRobot(RobotPort):
    """Wraps a RobotPort and enforces the safety rules."""

    def __init__(
        self,
        robot: RobotPort,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._robot = robot
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._last_action_end: float | None = None

    async def stand(self, speed: int) -> None:
        await self._run(speed, lambda: self._robot.stand(speed))

    async def sit(self, speed: int) -> None:
        await self._run(speed, lambda: self._robot.sit(speed))

    async def walk(self, direction: Direction, steps: int, speed: int) -> None:
        await self._run(speed, lambda: self._robot.walk(direction, steps, speed))

    async def turn(self, direction: TurnDirection, steps: int, speed: int) -> None:
        await self._run(speed, lambda: self._robot.turn(direction, steps, speed))

    async def emergency_stop(self) -> None:
        await self._robot.emergency_stop()

    async def reset_emergency_stop(self) -> None:
        await self._robot.reset_emergency_stop()

    async def get_telemetry(self) -> Telemetry:
        return await self._robot.get_telemetry()

    async def on_connection_lost(self) -> None:
        """Put the robot in the sitting position, unless the emergency stop is active."""
        if (await self._robot.get_telemetry()).emergency_stopped:
            return
        await self.sit(MIN_SAFE_SPEED)

    async def _run(self, speed: int, command: Callable[[], Awaitable[None]]) -> None:
        if not MIN_SAFE_SPEED <= speed <= MAX_SAFE_SPEED:
            raise SafetyLimitError(f"speed must be between {MIN_SAFE_SPEED} and {MAX_SAFE_SPEED}")
        async with self._lock:
            if self._last_action_end is not None:
                remaining = MIN_INTERVAL_S - (self._clock() - self._last_action_end)
                if remaining > 0:
                    await self._sleep(remaining)
            try:
                await command()
            finally:
                self._last_action_end = self._clock()

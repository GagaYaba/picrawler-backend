"""Hardware abstraction for the PiCrawler.

Every robot implementation (real robot, simulator) implements ``RobotPort``.
The rest of the application depends only on this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class Direction(StrEnum):
    """Walking direction."""

    FORWARD = "forward"
    BACKWARD = "backward"


class TurnDirection(StrEnum):
    """Turning direction."""

    LEFT = "left"
    RIGHT = "right"


class Posture(StrEnum):
    """Current posture of the robot."""

    SITTING = "sitting"
    STANDING = "standing"
    MOVING = "moving"


@dataclass(frozen=True, slots=True)
class Telemetry:
    """Snapshot of the robot state.

    A value is ``None`` when the implementation cannot measure it.
    """

    posture: Posture
    connected: bool
    emergency_stopped: bool
    battery_voltage: float | None = None
    cpu_temperature_celsius: float | None = None


class RobotPort(ABC):
    """Interface implemented by the real robot and by the simulator.

    Speed and timing limits are enforced by the safety layer, not here.
    """

    @abstractmethod
    async def stand(self, speed: int) -> None:
        """Move to the standing posture."""

    @abstractmethod
    async def sit(self, speed: int) -> None:
        """Move to the sitting posture (safe position)."""

    @abstractmethod
    async def walk(self, direction: Direction, steps: int, speed: int) -> None:
        """Walk a number of steps in the given direction."""

    @abstractmethod
    async def turn(self, direction: TurnDirection, steps: int, speed: int) -> None:
        """Turn on the spot for a number of steps."""

    @abstractmethod
    async def emergency_stop(self) -> None:
        """Stop any movement immediately and refuse new movements until reset."""

    @abstractmethod
    async def get_telemetry(self) -> Telemetry:
        """Return the current robot state."""

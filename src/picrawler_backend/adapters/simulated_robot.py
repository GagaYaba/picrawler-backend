"""In-memory simulator of the PiCrawler.

The simulator keeps a posture, an emergency stop flag and an estimated pose
(position and heading on the floor). It does not reproduce mechanical effects
such as the measured drift or slipping: it is not evidence of the real behaviour.
"""

import asyncio
import math
from dataclasses import dataclass

from picrawler_backend.domain import (
    Direction,
    EmergencyStopActiveError,
    Posture,
    RobotPort,
    Telemetry,
    TurnDirection,
)

# Hardware speed range accepted by the picrawler library. The safety layer
# applies stricter limits on top of this.
MIN_SPEED = 1
MAX_SPEED = 100

# Derived from the 7 November 2026 measurement: about 34 cm for 5 steps.
DEFAULT_STEP_LENGTH_CM = 6.8
# Not measured yet: placeholder value until a turn test is done on the real robot.
DEFAULT_TURN_ANGLE_DEG = 15.0


@dataclass(frozen=True, slots=True)
class Pose:
    """Estimated position on the floor, in centimetres, and heading in degrees.

    Heading 0 points along the x axis; positive angles turn left.
    """

    x_cm: float = 0.0
    y_cm: float = 0.0
    heading_deg: float = 0.0


class SimulatedRobot(RobotPort):
    """Simulated robot implementing RobotPort without hardware."""

    def __init__(
        self,
        *,
        step_length_cm: float = DEFAULT_STEP_LENGTH_CM,
        turn_angle_deg: float = DEFAULT_TURN_ANGLE_DEG,
        step_duration_s: float = 0.0,
    ) -> None:
        if step_length_cm <= 0 or turn_angle_deg <= 0 or step_duration_s < 0:
            raise ValueError("step length and turn angle must be positive, duration non-negative")
        self._step_length_cm = step_length_cm
        self._turn_angle_deg = turn_angle_deg
        self._step_duration_s = step_duration_s
        self._posture = Posture.SITTING
        self._emergency_stopped = False
        self._pose = Pose()

    @property
    def pose(self) -> Pose:
        """Current estimated pose."""
        return self._pose

    async def stand(self, speed: int) -> None:
        self._check_can_move(speed, steps=1)
        await self._wait(1)
        self._posture = Posture.STANDING

    async def sit(self, speed: int) -> None:
        self._check_can_move(speed, steps=1)
        await self._wait(1)
        self._posture = Posture.SITTING

    async def walk(self, direction: Direction, steps: int, speed: int) -> None:
        self._check_can_move(speed, steps)
        sign = 1 if direction is Direction.FORWARD else -1
        heading = math.radians(self._pose.heading_deg)
        distance = sign * steps * self._step_length_cm
        await self._move(steps)
        self._pose = Pose(
            x_cm=self._pose.x_cm + distance * math.cos(heading),
            y_cm=self._pose.y_cm + distance * math.sin(heading),
            heading_deg=self._pose.heading_deg,
        )

    async def turn(self, direction: TurnDirection, steps: int, speed: int) -> None:
        self._check_can_move(speed, steps)
        sign = 1 if direction is TurnDirection.LEFT else -1
        await self._move(steps)
        heading = (self._pose.heading_deg + sign * steps * self._turn_angle_deg) % 360
        self._pose = Pose(x_cm=self._pose.x_cm, y_cm=self._pose.y_cm, heading_deg=heading)

    async def emergency_stop(self) -> None:
        self._emergency_stopped = True

    async def reset_emergency_stop(self) -> None:
        self._emergency_stopped = False

    async def get_telemetry(self) -> Telemetry:
        return Telemetry(
            posture=self._posture,
            connected=True,
            emergency_stopped=self._emergency_stopped,
        )

    def _check_can_move(self, speed: int, steps: int) -> None:
        if self._emergency_stopped:
            raise EmergencyStopActiveError("emergency stop is active")
        if not MIN_SPEED <= speed <= MAX_SPEED:
            raise ValueError(f"speed must be between {MIN_SPEED} and {MAX_SPEED}")
        if steps < 1:
            raise ValueError("steps must be at least 1")

    async def _move(self, steps: int) -> None:
        self._posture = Posture.MOVING
        await self._wait(steps)
        if self._emergency_stopped:
            raise EmergencyStopActiveError("movement interrupted by emergency stop")
        self._posture = Posture.STANDING

    async def _wait(self, steps: int) -> None:
        if self._step_duration_s:
            await asyncio.sleep(steps * self._step_duration_s)

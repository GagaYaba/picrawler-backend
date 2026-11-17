"""Behaviour required from every RobotPort implementation.

Each test runs against every implementation listed in ``IMPLEMENTATIONS``.
The real robot implementation will be added to this list when it exists.
"""

from collections.abc import Callable

import pytest

from picrawler_backend.adapters import SimulatedRobot
from picrawler_backend.domain import (
    Direction,
    EmergencyStopActiveError,
    Posture,
    RobotPort,
    SafeRobot,
    TurnDirection,
)


async def _no_wait(_: float) -> None:
    return None


IMPLEMENTATIONS: dict[str, Callable[[], RobotPort]] = {
    "simulated": SimulatedRobot,
    "safe_simulated": lambda: SafeRobot(SimulatedRobot(), sleep=_no_wait),
}


@pytest.fixture(params=IMPLEMENTATIONS.values(), ids=IMPLEMENTATIONS.keys())
def robot(request) -> RobotPort:
    return request.param()


async def test_stand_and_sit_are_reported_in_telemetry(robot):
    await robot.stand(speed=50)
    assert (await robot.get_telemetry()).posture is Posture.STANDING

    await robot.sit(speed=50)
    assert (await robot.get_telemetry()).posture is Posture.SITTING


async def test_robot_is_standing_after_walk_and_turn(robot):
    await robot.walk(Direction.FORWARD, steps=1, speed=50)
    assert (await robot.get_telemetry()).posture is Posture.STANDING

    await robot.turn(TurnDirection.LEFT, steps=1, speed=50)
    assert (await robot.get_telemetry()).posture is Posture.STANDING


async def test_emergency_stop_blocks_movements_until_reset(robot):
    await robot.emergency_stop()

    assert (await robot.get_telemetry()).emergency_stopped is True
    with pytest.raises(EmergencyStopActiveError):
        await robot.walk(Direction.FORWARD, steps=1, speed=50)

    await robot.reset_emergency_stop()
    assert (await robot.get_telemetry()).emergency_stopped is False
    await robot.stand(speed=50)


async def test_zero_steps_is_rejected(robot):
    with pytest.raises(ValueError):
        await robot.walk(Direction.FORWARD, steps=0, speed=50)

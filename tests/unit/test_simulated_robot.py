import asyncio

import pytest

from picrawler_backend.adapters import Pose, SimulatedRobot
from picrawler_backend.domain import Direction, EmergencyStopActiveError, Posture, TurnDirection


@pytest.fixture
def robot() -> SimulatedRobot:
    return SimulatedRobot(step_length_cm=10.0, turn_angle_deg=90.0)


async def test_starts_sitting_at_origin(robot):
    telemetry = await robot.get_telemetry()

    assert telemetry.posture is Posture.SITTING
    assert telemetry.emergency_stopped is False
    assert robot.pose == Pose()


async def test_stand_and_sit_change_posture(robot):
    await robot.stand(speed=50)
    assert (await robot.get_telemetry()).posture is Posture.STANDING

    await robot.sit(speed=50)
    assert (await robot.get_telemetry()).posture is Posture.SITTING


@pytest.mark.parametrize(
    ("direction", "expected_x"), [(Direction.FORWARD, 30.0), (Direction.BACKWARD, -30.0)]
)
async def test_walk_moves_along_heading(robot, direction, expected_x):
    await robot.walk(direction, steps=3, speed=50)

    assert robot.pose.x_cm == pytest.approx(expected_x)
    assert robot.pose.y_cm == pytest.approx(0.0)
    assert (await robot.get_telemetry()).posture is Posture.STANDING


async def test_walk_after_turn_follows_new_heading(robot):
    await robot.turn(TurnDirection.LEFT, steps=1, speed=50)
    await robot.walk(Direction.FORWARD, steps=1, speed=50)

    assert robot.pose.heading_deg == pytest.approx(90.0)
    assert robot.pose.x_cm == pytest.approx(0.0, abs=1e-9)
    assert robot.pose.y_cm == pytest.approx(10.0)


async def test_emergency_stop_blocks_movements_until_reset(robot):
    await robot.emergency_stop()

    assert (await robot.get_telemetry()).emergency_stopped is True
    with pytest.raises(EmergencyStopActiveError):
        await robot.walk(Direction.FORWARD, steps=1, speed=50)

    await robot.reset_emergency_stop()
    await robot.walk(Direction.FORWARD, steps=1, speed=50)
    assert robot.pose.x_cm == pytest.approx(10.0)


async def test_emergency_stop_interrupts_movement_in_progress():
    robot = SimulatedRobot(step_duration_s=0.05)

    walking = asyncio.create_task(robot.walk(Direction.FORWARD, steps=5, speed=50))
    await asyncio.sleep(0.01)
    await robot.emergency_stop()

    with pytest.raises(EmergencyStopActiveError):
        await walking
    assert robot.pose == Pose()


@pytest.mark.parametrize(("speed", "steps"), [(0, 1), (101, 1), (50, 0)])
async def test_invalid_command_is_rejected(robot, speed, steps):
    with pytest.raises(ValueError):
        await robot.walk(Direction.FORWARD, steps=steps, speed=speed)


async def test_default_step_length_matches_measured_walk():
    robot = SimulatedRobot()

    await robot.walk(Direction.FORWARD, steps=5, speed=70)

    assert robot.pose.x_cm == pytest.approx(34.0)

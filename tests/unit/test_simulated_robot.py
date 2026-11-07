import asyncio

import pytest

from picrawler_backend.adapters import Pose, SimulatedRobot
from picrawler_backend.domain import (
    Direction,
    EmergencyStopActiveError,
    Posture,
    RobotPort,
    TurnDirection,
)


@pytest.fixture
def robot() -> SimulatedRobot:
    return SimulatedRobot(step_length_cm=10.0, turn_angle_deg=90.0)


def test_simulated_robot_implements_robot_port(robot):
    assert isinstance(robot, RobotPort)


async def test_initial_state_is_sitting_at_origin(robot):
    telemetry = await robot.get_telemetry()

    assert telemetry.posture is Posture.SITTING
    assert telemetry.connected is True
    assert telemetry.emergency_stopped is False
    assert robot.pose == Pose()


async def test_stand_then_sit_changes_posture(robot):
    await robot.stand(speed=50)
    assert (await robot.get_telemetry()).posture is Posture.STANDING

    await robot.sit(speed=50)
    assert (await robot.get_telemetry()).posture is Posture.SITTING


async def test_walk_forward_moves_along_heading(robot):
    await robot.walk(Direction.FORWARD, steps=3, speed=50)

    assert robot.pose.x_cm == pytest.approx(30.0)
    assert robot.pose.y_cm == pytest.approx(0.0)
    assert (await robot.get_telemetry()).posture is Posture.STANDING


async def test_walk_backward_moves_opposite_to_heading(robot):
    await robot.walk(Direction.BACKWARD, steps=2, speed=50)

    assert robot.pose.x_cm == pytest.approx(-20.0)


async def test_turn_left_then_walk_moves_along_new_heading(robot):
    await robot.turn(TurnDirection.LEFT, steps=1, speed=50)
    await robot.walk(Direction.FORWARD, steps=1, speed=50)

    assert robot.pose.heading_deg == pytest.approx(90.0)
    assert robot.pose.x_cm == pytest.approx(0.0, abs=1e-9)
    assert robot.pose.y_cm == pytest.approx(10.0)


async def test_turn_right_wraps_heading_into_0_360(robot):
    await robot.turn(TurnDirection.RIGHT, steps=1, speed=50)

    assert robot.pose.heading_deg == pytest.approx(270.0)


async def test_emergency_stop_blocks_movements_until_reset(robot):
    await robot.emergency_stop()

    assert (await robot.get_telemetry()).emergency_stopped is True
    with pytest.raises(EmergencyStopActiveError):
        await robot.walk(Direction.FORWARD, steps=1, speed=50)
    with pytest.raises(EmergencyStopActiveError):
        await robot.stand(speed=50)

    await robot.reset_emergency_stop()
    await robot.walk(Direction.FORWARD, steps=1, speed=50)
    assert robot.pose.x_cm == pytest.approx(10.0)


async def test_emergency_stop_interrupts_movement_in_progress():
    robot = SimulatedRobot(step_duration_s=0.05)

    walking = asyncio.create_task(robot.walk(Direction.FORWARD, steps=5, speed=50))
    await asyncio.sleep(0.01)
    assert (await robot.get_telemetry()).posture is Posture.MOVING
    await robot.emergency_stop()

    with pytest.raises(EmergencyStopActiveError):
        await walking
    assert robot.pose == Pose()


@pytest.mark.parametrize("speed", [0, 101, -5])
async def test_speed_outside_hardware_range_is_rejected(robot, speed):
    with pytest.raises(ValueError, match="speed"):
        await robot.walk(Direction.FORWARD, steps=1, speed=speed)


async def test_zero_steps_is_rejected(robot):
    with pytest.raises(ValueError, match="steps"):
        await robot.turn(TurnDirection.LEFT, steps=0, speed=50)


@pytest.mark.parametrize(
    "kwargs",
    [{"step_length_cm": 0}, {"turn_angle_deg": -1}, {"step_duration_s": -0.1}],
)
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        SimulatedRobot(**kwargs)


def test_default_step_length_matches_measured_walk():
    robot = SimulatedRobot()

    asyncio.run(robot.walk(Direction.FORWARD, steps=5, speed=70))

    assert robot.pose.x_cm == pytest.approx(34.0)

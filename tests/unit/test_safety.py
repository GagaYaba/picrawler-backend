import asyncio

import pytest

from picrawler_backend.adapters import SimulatedRobot
from picrawler_backend.domain import (
    MIN_INTERVAL_S,
    MIN_SAFE_SPEED,
    Direction,
    Posture,
    SafeRobot,
    SafetyLimitError,
)


class FakeClock:
    """Manual clock: time only advances when the safety layer sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def simulator() -> SimulatedRobot:
    return SimulatedRobot()


@pytest.fixture
def robot(simulator, clock) -> SafeRobot:
    return SafeRobot(simulator, clock=clock, sleep=clock.sleep)


@pytest.mark.parametrize("speed", [19, 71])
async def test_speed_outside_safe_range_is_refused_and_not_sent(robot, simulator, speed):
    with pytest.raises(SafetyLimitError):
        await robot.walk(Direction.FORWARD, steps=1, speed=speed)

    assert simulator.pose.x_cm == 0.0


@pytest.mark.parametrize("speed", [20, 70])
async def test_speed_at_safe_limits_is_accepted(robot, simulator, speed):
    await robot.walk(Direction.FORWARD, steps=1, speed=speed)

    assert simulator.pose.x_cm > 0.0


async def test_waits_minimum_interval_between_actions(robot, clock):
    await robot.stand(speed=50)
    await robot.walk(Direction.FORWARD, steps=1, speed=50)

    assert clock.sleeps == [pytest.approx(MIN_INTERVAL_S)]


async def test_commands_run_one_at_a_time():
    class OverlapDetector(SimulatedRobot):
        def __init__(self) -> None:
            super().__init__()
            self.active = 0
            self.max_active = 0

        async def walk(self, direction, steps, speed):
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            await asyncio.sleep(0.01)
            self.active -= 1

    inner = OverlapDetector()
    robot = SafeRobot(inner)

    await asyncio.gather(*(robot.walk(Direction.FORWARD, steps=1, speed=50) for _ in range(3)))

    assert inner.max_active == 1


async def test_emergency_stop_does_not_wait_for_movement_in_progress():
    simulator = SimulatedRobot(step_duration_s=1.0)
    robot = SafeRobot(simulator)

    walking = asyncio.create_task(robot.walk(Direction.FORWARD, steps=5, speed=50))
    await asyncio.sleep(0.01)
    await asyncio.wait_for(robot.emergency_stop(), timeout=0.1)

    assert (await robot.get_telemetry()).emergency_stopped is True
    walking.cancel()
    with pytest.raises(asyncio.CancelledError):
        await walking


async def test_connection_lost_puts_robot_in_sitting_position(robot, simulator):
    await robot.stand(speed=50)

    await robot.on_connection_lost()

    assert (await simulator.get_telemetry()).posture is Posture.SITTING


async def test_connection_lost_during_emergency_stop_sends_no_movement(robot, simulator):
    await robot.stand(speed=MIN_SAFE_SPEED)
    await robot.emergency_stop()

    await robot.on_connection_lost()

    assert (await simulator.get_telemetry()).posture is Posture.STANDING

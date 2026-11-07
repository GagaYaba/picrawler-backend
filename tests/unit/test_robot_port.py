import dataclasses

import pytest

from picrawler_backend.domain import Direction, Posture, RobotPort, Telemetry, TurnDirection


def test_robot_port_cannot_be_instantiated():
    with pytest.raises(TypeError):
        RobotPort()  # type: ignore[abstract]


def test_incomplete_implementation_cannot_be_instantiated():
    class PartialRobot(RobotPort):
        async def stand(self, speed: int) -> None:
            return None

    with pytest.raises(TypeError):
        PartialRobot()  # type: ignore[abstract]


def test_telemetry_is_immutable():
    telemetry = Telemetry(posture=Posture.SITTING, connected=True, emergency_stopped=False)

    with pytest.raises(dataclasses.FrozenInstanceError):
        telemetry.connected = False  # type: ignore[misc]


def test_telemetry_optional_measurements_default_to_none():
    telemetry = Telemetry(posture=Posture.STANDING, connected=True, emergency_stopped=False)

    assert telemetry.battery_voltage is None
    assert telemetry.cpu_temperature_celsius is None


@pytest.mark.parametrize(
    ("member", "value"),
    [
        (Direction.FORWARD, "forward"),
        (Direction.BACKWARD, "backward"),
        (TurnDirection.LEFT, "left"),
        (TurnDirection.RIGHT, "right"),
        (Posture.SITTING, "sitting"),
    ],
)
def test_enums_serialize_to_stable_strings(member, value):
    assert member == value

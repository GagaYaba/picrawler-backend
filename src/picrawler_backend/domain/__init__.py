"""Domain layer: robot interface and data types, independent of any framework."""

from picrawler_backend.domain.robot_port import (
    Direction,
    EmergencyStopActiveError,
    Posture,
    RobotError,
    RobotPort,
    Telemetry,
    TurnDirection,
)
from picrawler_backend.domain.safety import (
    MAX_SAFE_SPEED,
    MIN_INTERVAL_S,
    MIN_SAFE_SPEED,
    SafeRobot,
    SafetyLimitError,
)
from picrawler_backend.domain.watchdog import ConnectionWatchdog

__all__ = [
    "MAX_SAFE_SPEED",
    "MIN_INTERVAL_S",
    "MIN_SAFE_SPEED",
    "ConnectionWatchdog",
    "Direction",
    "EmergencyStopActiveError",
    "Posture",
    "RobotError",
    "RobotPort",
    "SafeRobot",
    "SafetyLimitError",
    "Telemetry",
    "TurnDirection",
]

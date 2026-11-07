"""FastAPI application.

Every route except ``/health`` requires the operator token, sent as
``Authorization: Bearer <token>``. All commands go through ``SafeRobot``.
"""

import os
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from picrawler_backend.adapters import SimulatedRobot
from picrawler_backend.domain import (
    Direction,
    EmergencyStopActiveError,
    Posture,
    RobotPort,
    SafeRobot,
    SafetyLimitError,
    TurnDirection,
)

MIN_TOKEN_LENGTH = 32


class SpeedCommand(BaseModel):
    speed: int


class WalkCommand(BaseModel):
    direction: Direction
    steps: int = Field(ge=1)
    speed: int


class TurnCommand(BaseModel):
    direction: TurnDirection
    steps: int = Field(ge=1)
    speed: int


class TelemetryResponse(BaseModel):
    posture: Posture
    connected: bool
    emergency_stopped: bool
    battery_voltage: float | None
    cpu_temperature_celsius: float | None


def robot_from_environment() -> RobotPort:
    """Build the robot implementation selected by ROBOT_MODE."""
    mode = os.environ.get("ROBOT_MODE", "simulated")
    if mode == "simulated":
        return SimulatedRobot()
    raise RuntimeError(f"unsupported ROBOT_MODE: {mode!r}")


def create_app(robot: RobotPort | None = None, api_token: str | None = None) -> FastAPI:
    """Create the API. Refuses to start without a strong enough operator token."""
    token = api_token if api_token is not None else os.environ.get("API_TOKEN", "")
    if len(token) < MIN_TOKEN_LENGTH:
        raise RuntimeError(f"API_TOKEN must be set and at least {MIN_TOKEN_LENGTH} characters")

    safe_robot = SafeRobot(robot if robot is not None else robot_from_environment())
    bearer = HTTPBearer(auto_error=False)

    def require_operator(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> None:
        if credentials is None or not secrets.compare_digest(
            credentials.credentials.encode(), token.encode()
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    app = FastAPI(title="PiCrawler control API", version="0.1.0")
    operator = [Depends(require_operator)]

    @app.exception_handler(SafetyLimitError)
    async def safety_limit_handler(_: Request, error: SafetyLimitError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(EmergencyStopActiveError)
    async def emergency_stop_handler(_: Request, error: EmergencyStopActiveError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/telemetry", dependencies=operator)
    async def telemetry() -> TelemetryResponse:
        state = await safe_robot.get_telemetry()
        return TelemetryResponse(
            posture=state.posture,
            connected=state.connected,
            emergency_stopped=state.emergency_stopped,
            battery_voltage=state.battery_voltage,
            cpu_temperature_celsius=state.cpu_temperature_celsius,
        )

    @app.post("/commands/stand", status_code=204, dependencies=operator)
    async def stand(command: SpeedCommand) -> None:
        await safe_robot.stand(command.speed)

    @app.post("/commands/sit", status_code=204, dependencies=operator)
    async def sit(command: SpeedCommand) -> None:
        await safe_robot.sit(command.speed)

    @app.post("/commands/walk", status_code=204, dependencies=operator)
    async def walk(command: WalkCommand) -> None:
        await safe_robot.walk(command.direction, command.steps, command.speed)

    @app.post("/commands/turn", status_code=204, dependencies=operator)
    async def turn(command: TurnCommand) -> None:
        await safe_robot.turn(command.direction, command.steps, command.speed)

    @app.post("/emergency-stop", status_code=204, dependencies=operator)
    async def emergency_stop() -> None:
        await safe_robot.emergency_stop()

    @app.post("/emergency-stop/reset", status_code=204, dependencies=operator)
    async def reset_emergency_stop() -> None:
        await safe_robot.reset_emergency_stop()

    return app

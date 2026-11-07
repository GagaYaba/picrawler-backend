import pytest
from fastapi.testclient import TestClient

from picrawler_backend.adapters import SimulatedRobot
from picrawler_backend.api import create_app

TOKEN = "t" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}
WALK = {"direction": "forward", "steps": 1, "speed": 50}


@pytest.fixture
def simulator() -> SimulatedRobot:
    return SimulatedRobot()


@pytest.fixture
def client(simulator) -> TestClient:
    return TestClient(create_app(robot=simulator, api_token=TOKEN))


@pytest.mark.parametrize("token", ["", "short"])
def test_app_refuses_to_start_without_strong_token(token):
    with pytest.raises(RuntimeError, match="API_TOKEN"):
        create_app(robot=SimulatedRobot(), api_token=token)


def test_health_is_public(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer " + "x" * 32}])
def test_command_without_valid_token_is_refused_and_not_sent(client, simulator, headers):
    response = client.post("/commands/walk", json=WALK, headers=headers)

    assert response.status_code == 401
    assert simulator.pose.x_cm == 0.0


def test_walk_command_moves_robot_and_updates_telemetry(client, simulator):
    response = client.post("/commands/walk", json=WALK, headers=AUTH)

    assert response.status_code == 204
    assert simulator.pose.x_cm > 0.0
    assert client.get("/telemetry", headers=AUTH).json()["posture"] == "standing"


def test_unsafe_speed_is_refused_by_safety_layer(client, simulator):
    response = client.post("/commands/walk", json={**WALK, "speed": 90}, headers=AUTH)

    assert response.status_code == 422
    assert simulator.pose.x_cm == 0.0


def test_emergency_stop_blocks_commands_until_reset(client):
    client.post("/emergency-stop", headers=AUTH)
    assert client.post("/commands/walk", json=WALK, headers=AUTH).status_code == 409

    client.post("/emergency-stop/reset", headers=AUTH)
    assert client.post("/commands/walk", json=WALK, headers=AUTH).status_code == 204

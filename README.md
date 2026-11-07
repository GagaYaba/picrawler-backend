# picrawler-backend

Control and supervision API for the SunFounder PiCrawler robot.

The hardware sits behind a single interface, `RobotPort`, with two implementations:
the real robot and a simulator. The rest of the backend depends only on this interface.

## Status

- Step 1: project skeleton and `RobotPort` interface.
- Step 2: `SimulatedRobot`, an in-memory implementation (posture, emergency stop, estimated pose).
- Step 3: `SafeRobot`, a safety layer wrapping any `RobotPort`: speed 20 to 70, 0.25 s between
  actions, one command at a time, immediate emergency stop, sitting position on connection loss.

- Step 4: contract tests (`tests/contract/`), run against every `RobotPort` implementation.

- Step 5a: FastAPI application (`src/picrawler_backend/api/`) with operator token authentication.
- Step 5b: connection watchdog. The operator interface calls `POST /heartbeat` regularly;
  after `HEARTBEAT_TIMEOUT_S` seconds (default 2) without heartbeat, the robot sits down. The simulator does not reproduce
mechanical effects such as drift: it is not evidence of the real robot behaviour.

## Layout

| Path | Content |
|---|---|
| `src/picrawler_backend/domain/` | `RobotPort` interface, data types and safety layer, no framework dependency |
| `src/picrawler_backend/adapters/` | `RobotPort` implementations (`SimulatedRobot`) |
| `src/picrawler_backend/api/` | FastAPI application |
| `tests/unit/` | Unit tests |
| `tests/api/` | API tests |
| `tests/contract/` | Behaviour required from every `RobotPort` implementation |

## Local setup

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m pytest
```

Requires Python 3.12 or later. Coverage below 80 % fails the test run.

## Run the API locally

```
export API_TOKEN=<token of at least 32 characters>   # Windows: set API_TOKEN=...
uvicorn --factory picrawler_backend.api:create_app --reload
```

Interactive documentation: http://127.0.0.1:8000/docs. Every route except `/health` requires
the header `Authorization: Bearer <API_TOKEN>`.

## Configuration

Copy `.env.template` to `.env`. Never commit `.env` or any secret.

## Branches

`main` holds releases only (pull request from `develop`, then a semantic version tag).
Work branches start from `develop` (`feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `ci/`, `test/`).

# picrawler-backend

Control and supervision API for the SunFounder PiCrawler robot.

The hardware sits behind a single interface, `RobotPort`, with two implementations:
the real robot and a simulator. The rest of the backend depends only on this interface.

## Status

Step 1: project skeleton and `RobotPort` interface. The simulator, safety layer and API
are not implemented yet.

## Layout

| Path | Content |
|---|---|
| `src/picrawler_backend/domain/` | `RobotPort` interface and data types, no framework dependency |
| `tests/unit/` | Unit tests |

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

## Configuration

Copy `.env.template` to `.env`. Never commit `.env` or any secret.

## Branches

`main` holds releases only (pull request from `develop`, then a semantic version tag).
Work branches start from `develop` (`feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `ci/`, `test/`).

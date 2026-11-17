import pytest

from picrawler_backend.domain import ConnectionWatchdog


class Recorder:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> None:
        self.calls += 1


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def on_lost() -> Recorder:
    return Recorder()


@pytest.fixture
def watchdog(on_lost, clock) -> ConnectionWatchdog:
    return ConnectionWatchdog(on_lost, timeout_s=2.0, clock=clock)


async def test_no_action_before_first_heartbeat(watchdog, on_lost, clock):
    clock.now = 100.0
    await watchdog.check()

    assert on_lost.calls == 0


async def test_no_action_while_heartbeats_arrive_in_time(watchdog, on_lost, clock):
    watchdog.heartbeat()
    clock.now = 1.9
    await watchdog.check()

    assert on_lost.calls == 0


async def test_expired_heartbeat_triggers_action_once_until_next_heartbeat(
    watchdog, on_lost, clock
):
    watchdog.heartbeat()
    clock.now = 2.1
    await watchdog.check()
    await watchdog.check()
    assert on_lost.calls == 1

    watchdog.heartbeat()
    clock.now = 4.2
    await watchdog.check()
    assert on_lost.calls == 2

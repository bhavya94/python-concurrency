from python_concurrency.async_waits import with_asyncio
from python_concurrency.server import SlowServer

WAIT = 0.1


def test_tasks_overlap_the_waits_in_rounds():
    with SlowServer(delay=WAIT) as server:
        run = with_asyncio(server.port, 4, limit=2)
    assert 2 * WAIT * 1000 <= run.ms < 3 * WAIT * 1000  # ⌈4/2⌉ = 2 rounds: not 4 (one at a time), not 1
    assert sorted(span.thread for span in run.spans) == [f"item-{i}" for i in range(4)]  # one row per task


def test_a_blocking_call_inside_a_task_stops_the_loop():
    with SlowServer(delay=WAIT) as server:
        run = with_asyncio(server.port, 3, limit=3, call="blocking")
    assert run.ms >= 3 * WAIT * 1000  # one request at a time, though 3 were allowed in flight
    assert all(a.end <= b.start for a, b in zip(run.spans, run.spans[1:]))  # each starts after the last ended


def test_to_thread_lets_the_blocking_calls_overlap_again():
    with SlowServer(delay=WAIT) as server:
        run = with_asyncio(server.port, 3, limit=3, call="to-thread")
    assert run.ms < 2 * WAIT * 1000  # one round
    assert all(span.thread.startswith("asyncio_") for span in run.spans)  # each request ran on a pool thread

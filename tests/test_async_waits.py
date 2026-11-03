from python_data_structures_and_utilities.language.concurrency.async_waits import with_asyncio
from python_data_structures_and_utilities.language.concurrency.server import SlowServer

WAIT = 0.1


def test_tasks_overlap_the_waits_in_rounds():
    with SlowServer(delay=WAIT) as server:
        run = with_asyncio(server.port, 4, limit=2)
    assert 2 * WAIT * 1000 <= run.ms < 3 * WAIT * 1000  # ⌈4/2⌉ = 2 rounds: not 4 (one at a time), not 1
    assert sorted(span.thread for span in run.spans) == [f"item-{i}" for i in range(4)]  # one row per task

from functools import partial

from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.waits import fetch
from python_data_structures_and_utilities.language.concurrency.ways import one_at_a_time, with_threads

WAIT = 0.05


def test_requests_sent_one_at_a_time_add_up():
    with SlowServer(delay=WAIT) as server:
        run = one_at_a_time(partial(fetch, server.port), 4)
    assert 4 * WAIT * 1000 <= run.ms < (4 * WAIT + 0.5) * 1000  # each request waits its full turn; none overlap


def test_threads_overlap_the_waits_in_rounds():
    with SlowServer(delay=2 * WAIT) as server:
        run = with_threads(partial(fetch, server.port), 4, workers=2)
    assert 2 * 2 * WAIT * 1000 <= run.ms < 3 * 2 * WAIT * 1000  # ⌈4/2⌉ = 2 rounds of waits: not 4, not 1
    assert {span.thread for span in run.spans} == {"worker_0", "worker_1"}

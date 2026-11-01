from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.waits import one_at_a_time, with_threads

WAIT = 0.05


def test_requests_sent_one_at_a_time_add_up():
    with SlowServer(delay=WAIT) as server:
        total = one_at_a_time(server, 4)
    assert 4 * WAIT <= total < 4 * WAIT + 0.5  # each request waits its full turn, and nothing overlaps


def test_threads_overlap_the_waits_in_rounds():
    with SlowServer(delay=2 * WAIT) as server:
        total = with_threads(server, 4, workers=2)
    assert 2 * 2 * WAIT <= total < 3 * 2 * WAIT  # ⌈4/2⌉ = 2 rounds of waits: not 4 (one thread), not 1

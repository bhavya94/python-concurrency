from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.waits import one_at_a_time

WAIT = 0.05


def test_requests_sent_one_at_a_time_add_up():
    with SlowServer(delay=WAIT) as server:
        total = one_at_a_time(server, 4)
    assert 4 * WAIT <= total < 4 * WAIT + 0.5  # each request waits its full turn, and nothing overlaps

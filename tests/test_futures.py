from urllib.error import HTTPError

from python_data_structures_and_utilities.language.concurrency.futures import collect, with_timeout
from python_data_structures_and_utilities.language.concurrency.server import SlowServer


def test_a_workers_error_surfaces_where_the_results_are_collected():
    with SlowServer(delay=0.05, fail=frozenset({1})) as server:
        spans, errors = collect(server.port, 4, workers=2)
    assert sorted(span.item for span in spans) == [0, 2, 3]
    assert list(errors) == [1] and isinstance(errors[1], HTTPError) and errors[1].code == 500


def test_a_timeout_cancels_the_queued_items_but_not_the_running_ones():
    with SlowServer(delay=0.2) as server:
        outcome = with_timeout(server.port, 6, workers=2, timeout=0.3)
    assert outcome.done == [0, 1]  # the first round finished at about 0.2 s
    assert sorted(outcome.finished_late) == [2, 3]  # the second round was running at 0.3 s and finished anyway
    assert outcome.cancelled == [4, 5]  # never started, so cancel() stopped them

from urllib.error import HTTPError

from python_data_structures_and_utilities.language.concurrency.futures import collect
from python_data_structures_and_utilities.language.concurrency.server import SlowServer


def test_a_workers_error_surfaces_where_the_results_are_collected():
    with SlowServer(delay=0.05, fail=frozenset({1})) as server:
        spans, errors = collect(server.port, 4, workers=2)
    assert sorted(span.item for span in spans) == [0, 2, 3]
    assert list(errors) == [1] and isinstance(errors[1], HTTPError) and errors[1].code == 500

import sys

import pytest

from python_data_structures_and_utilities.language.concurrency.race import race

# A thread is asked to hand the GIL over every 5 ms, and only some hand-overs fall between a read and its write.
# At 500,000 additions per thread, 6 runs in 40 lost nothing. At 2,000,000, every one of 30 runs lost updates.
TIMES = 2_000_000


def test_a_call_between_the_read_and_the_write_loses_updates():
    assert race(4, TIMES, "read-call-write") < 4 * TIMES


@pytest.mark.skipif(not sys._is_gil_enabled(), reason="with no GIL, += loses updates too")
def test_plus_equals_loses_nothing_with_the_gil_on_this_interpreter():
    assert race(4, TIMES, "plus-equals") == 4 * TIMES  # CPython 3.14's luck, not a promise

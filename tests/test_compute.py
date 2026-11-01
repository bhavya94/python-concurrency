import sys
from functools import partial

import pytest

from python_data_structures_and_utilities.language.concurrency.compute import burn
from python_data_structures_and_utilities.language.concurrency.ways import with_processes, with_threads

SIZE = 1_250_000  # about 50 ms per item. Smaller items can all run on the first thread before the others start.


def _stretch(run) -> float:
    """Each item's time on the clock, divided by the CPU time it used."""
    return sum(span.end - span.start for span in run.spans) / sum(span.cpu for span in run.spans)


@pytest.mark.skipif(not sys._is_gil_enabled(), reason="with no GIL, threads compute at the same time")
def test_threads_take_turns_on_the_gil():
    shared = with_threads(partial(burn, SIZE), 4, workers=4)
    assert _stretch(shared) > 2  # with 4 threads, each item spends most of its time waiting for the GIL
    cpu_ms = sum(span.cpu for span in shared.spans) * 1000
    assert shared.ms > 0.9 * cpu_ms  # so the run lasts at least n × c: no item's compute overlaps another's


def _overlapping(run) -> int:
    """How many items ran at the same time as another item, on a different worker."""
    return sum(any(a.thread != b.thread and a.start < b.end and b.start < a.end for b in run.spans) for a in run.spans)


def test_processes_compute_at_the_same_time():
    run = with_processes(partial(burn, SIZE), 4, workers=4)
    assert "MainThread" not in {span.thread for span in run.spans}  # every item ran in a worker process
    assert _overlapping(run) >= 2  # items on different processes ran at the same moment
    assert _stretch(run) < 1.5  # and no item waited for a GIL: each process has its own

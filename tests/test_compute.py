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


def _cpu_per_clock(run) -> float:
    """CPU time all the items used, divided by the clock time from the first start to the last end. Above 1, at
    least two items computed at the same moment: only several cores can use more CPU time than the clock shows.
    Taking turns on one GIL keeps it at 1 or below, however busy the machine is."""
    return sum(span.cpu for span in run.spans) / (max(s.end for s in run.spans) - min(s.start for s in run.spans))


def test_processes_compute_at_the_same_time():
    run = with_processes(partial(burn, SIZE), 4, workers=4)
    assert "MainThread" not in {span.thread for span in run.spans}  # every item ran in a worker process
    assert _cpu_per_clock(run) > 1.1  # each process has its own GIL, so items computed at once, on several cores


@pytest.mark.skipif(sys._is_gil_enabled(), reason="needs the free-threaded build: python 3.14t")
def test_without_a_gil_threads_compute_at_the_same_time():
    run = with_threads(partial(burn, SIZE), 4, workers=4)
    assert _cpu_per_clock(run) > 1.1  # no GIL to take turns on, so items computed at once, on several cores

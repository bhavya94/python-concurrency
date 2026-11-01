import os
import time
from types import SimpleNamespace

import pytest

from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.timeline import render
from python_data_structures_and_utilities.language.concurrency.waits import Run, WaitJob
from python_data_structures_and_utilities.language.concurrency.work import Span

WAIT = 0.1


@pytest.fixture(scope="module")
def server():
    with SlowServer(delay=WAIT) as s:
        yield s


def _job(server, n=4, workers=4):
    return WaitJob(server, n, workers, t0=time.time())


def _back_to_back(spans):
    return all(b.start >= a.end for a, b in zip(spans, spans[1:]))


def test_the_model_fills_in_its_formulas():
    job = WaitJob(SimpleNamespace(delay=0.1), n=8, workers=3, t0=0)
    assert job.predict("sequential")[1] == 800
    assert job.predict("asyncio-blocking")[1] == 800
    assert job.predict("threads") == ("⌈n/N⌉·t = ⌈8/3⌉·100 = 3·100", 300)
    assert job.predict("asyncio")[1] == 300
    assert job.predict("processes", startup_ms=50)[1] == 350


@pytest.mark.parametrize("way", ["threads", "asyncio"])
def test_threads_and_asyncio_overlap_the_waits(server, way):
    run = _job(server).run(way)
    assert len(run.spans) == 4
    assert run.wall_ms < 2 * WAIT * 1000  # one round of waits, not four
    assert len({s.worker for s in run.spans}) == 4


@pytest.mark.parametrize("way", ["sequential", "asyncio-blocking"])
def test_a_blocking_call_runs_one_wait_at_a_time(server, way):
    run = _job(server).run(way)
    assert run.wall_ms >= 4 * WAIT * 1000
    assert _back_to_back(run.spans)


def test_asyncio_names_each_wait_after_its_task(server):
    run = _job(server).run("asyncio")
    assert [s.worker for s in sorted(run.spans, key=lambda s: s.item)] == [f"item-{i}" for i in range(4)]


def test_processes_wait_in_other_processes(server):
    run = _job(server, n=4, workers=2).run("processes")
    assert sorted(s.item for s in run.spans) == [0, 1, 2, 3]
    pids = {s.worker for s in run.spans}
    assert all(w.startswith("pid ") for w in pids) and f"pid {os.getpid()}" not in pids
    threads = _job(server, n=4, workers=2).run("threads")
    assert run.startup_ms > threads.startup_ms + 20  # S: starting interpreters costs more than starting threads


def test_timeline_puts_each_wait_under_its_worker_and_time():
    spans = [Span(1, "a", 0.0, 0.5), Span(2, "b", 0.5, 1.0)]
    rows = render(Run("x", spans, started=0.0, ended=1.0), width=10).splitlines()
    assert rows[0] == "a  |11111·····|"
    assert rows[1] == "b  |·····22222|"

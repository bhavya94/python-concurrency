"""Ways to run n tasks: one at a time, from a pool of threads, or from a pool of processes.

A task is a function that takes an item number and returns a Span: who ran the item, and when. To give a task
its other arguments, fix them first with `functools.partial`, as in `partial(fetch, port)`. Then a way can call
`task(item)` with one argument.
"""

import logging
import pickle
import threading
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from python_data_structures_and_utilities.language.concurrency.timeline import Run, Span

log = logging.getLogger(__name__)
Task = Callable[[int], Span]


def one_at_a_time(task: Task, n: int) -> Run:
    """Run the items in a row, on this thread."""
    start = time.time()
    spans = [task(item) for item in range(n)]
    return Run(spans, start, time.time())


def with_threads(task: Task, n: int, workers: int) -> Run:
    """Run the items from a pool of `workers` threads. Each thread takes the next item as soon as it is free.

    Only one thread runs Python code at a time: the one that holds the GIL. A thread that is blocked, such as in a
    socket read, releases the GIL, so the other threads run meanwhile.
    """
    start = time.time()
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="worker") as pool:
        spans = pool.map(task, range(n))
        log.info("threads running: %s", ", ".join(t.name for t in threading.enumerate()))
        spans = list(spans)  # wait until every item is done
    return Run(spans, start, time.time())


def with_processes(task: Task, n: int, workers: int, setup: Callable[[], None] | None = None) -> Run:
    """Run the items from a pool of `workers` processes. Each one is a new Python interpreter with its own memory
    and its own GIL, so up to `workers` items compute at the same moment, on different cores.

    The pool sends each item to a worker as bytes: it pickles the task and the item number, and pickles the Span
    back. A function pickles by reference, as its module and name, and the worker imports it. A worker process
    starts with nothing set up, so `setup` runs first in each one, for example to set up logging.
    """
    start = time.time()
    log.info("each item goes to a worker as %d pickled bytes: the task by reference, and the item",
             len(pickle.dumps((task, 0))))
    with ProcessPoolExecutor(max_workers=workers, initializer=setup) as pool:
        log.info("pool made, with no processes yet; it starts one when an item arrives and no worker is free, up to %d", workers)
        spans = list(pool.map(task, range(n)))  # wait until every item is done
    return Run(spans, start, time.time())

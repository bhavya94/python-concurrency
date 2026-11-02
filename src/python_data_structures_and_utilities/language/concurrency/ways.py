"""Ways to run n tasks: one at a time, or from a pool of threads.

A task is a function that takes an item number and returns a Span: who ran the item, and when. To give a task
its other arguments, fix them first with `functools.partial`, as in `partial(fetch, port)`. Then a way can call
`task(item)` with one argument.
"""

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

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

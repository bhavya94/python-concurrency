"""concurrent.futures by hand: submit each item, then collect the results as they finish.

`pool.submit(fn, *args)` returns a Future at once: a placeholder for a result that doesn't exist yet.
`as_completed(futures)` hands back each future as it finishes, in the order they finish. `future.result()`
returns the value, or raises the exception the worker raised, again, in the thread that called `result()`.
So a worker's error doesn't vanish in its thread: it surfaces where the results are collected.

A timeout stops your waiting, not the work. `as_completed(futures, timeout=...)` raises `TimeoutError` when time
runs out, but the items keep going. `future.cancel()` stops an item that is still queued, and returns False for
one a worker has started: Python can't stop a thread from outside. Shutting the pool down waits for those.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from python_concurrency.timeline import Span
from python_concurrency.waits import fetch

log = logging.getLogger(__name__)


def collect(port: int, n: int, workers: int) -> tuple[list[Span], dict[int, Exception]]:
    """Fetch n items on a pool of threads. Returns the spans of the items that worked, and each failed item's
    error."""
    spans, errors = [], {}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="worker") as pool:
        futures = {pool.submit(fetch, port, item): item for item in range(n)}
        log.info("submitted %d items; each future waits for a worker", n)
        for future in as_completed(futures):
            item = futures[future]
            try:
                spans.append(future.result())
            except Exception as error:  # the worker's exception, raised again here
                log.info("item %d: its worker raised %r; result() raised it again here", item, error)
                errors[item] = error
            else:
                log.info("item %d: result collected", item)
    return spans, errors


@dataclass(frozen=True)
class Outcome:
    done: list[int]
    """Items done before the timeout."""
    cancelled: list[int]
    """Items still queued at the timeout. cancel() stopped them."""
    finished_late: list[int]
    """Items running at the timeout. cancel() couldn't stop them, and they finished anyway."""


def with_timeout(port: int, n: int, workers: int, timeout: float) -> Outcome:
    """Fetch n items, but wait at most `timeout` seconds. Then cancel what's left."""
    start, done = time.time(), []
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="worker") as pool:
        futures = {pool.submit(fetch, port, item): item for item in range(n)}
        try:
            for future in as_completed(futures, timeout=timeout):
                done.append(futures[future])
        except TimeoutError:
            log.info("timed out after %.0f ms: %d of %d items done", (time.time() - start) * 1000, len(done), n)
        cancelled = [item for future, item in futures.items() if future.cancel()]  # True only if still queued
        running = [item for future, item in futures.items() if future.running()]
        log.info("cancel() stopped the queued items %s; it can't stop the running items %s", cancelled, running)
    # Leaving the `with` block shut the pool down, which waited for the running items to finish.
    log.info("the pool shut down %.0f ms after the start, once the running items finished",
             (time.time() - start) * 1000)
    return Outcome(sorted(done), cancelled, running)

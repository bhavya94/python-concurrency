"""concurrent.futures by hand: submit each item, then collect the results as they finish.

`pool.submit(fn, *args)` returns a Future at once: a placeholder for a result that doesn't exist yet.
`as_completed(futures)` hands back each future as it finishes, in the order they finish. `future.result()`
returns the value, or raises the exception the worker raised, again, in the thread that called `result()`.
So a worker's error doesn't vanish in its thread: it surfaces where the results are collected.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from python_data_structures_and_utilities.language.concurrency.timeline import Span
from python_data_structures_and_utilities.language.concurrency.waits import fetch

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

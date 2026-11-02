"""Waiting on the network: n requests, each answered after t.

`fetch` blocks: once it sends a request, its thread sits inside the socket read until the answer arrives, and
does nothing else. One thread therefore takes about n × t. N threads can wait at the same time, so they take
about ⌈n / N⌉ × t.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

from python_data_structures_and_utilities.language.concurrency.server import SlowServer

log = logging.getLogger(__name__)


def fetch(url: str, item: int) -> None:
    """One blocking request. It logs the time on the clock and the CPU time this thread used: a thread that is
    blocked waits without computing, so its CPU time stays near zero."""
    start, cpu = time.perf_counter(), time.thread_time()
    log.info("item %d: request sent, waiting for the answer", item)
    with urlopen(url) as answer:
        answer.read()
    log.info("item %d: answered after %.0f ms, using %.1f ms of this thread's CPU", item,
             (time.perf_counter() - start) * 1000, (time.thread_time() - cpu) * 1000)


def one_at_a_time(server: SlowServer, n: int) -> float:
    """Send n requests in a row. Returns the total time in seconds."""
    start = time.perf_counter()
    for item in range(n):
        fetch(server.url(item), item)
    return time.perf_counter() - start


def with_threads(server: SlowServer, n: int, workers: int) -> float:
    """Send n requests from a pool of `workers` threads. Returns the total time in seconds.

    Each thread takes the next request as soon as it is free. A thread blocked in its socket read has released
    the GIL, so the other threads can run and send their own requests. Up to `workers` waits overlap.
    """
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="worker") as pool:
        answers = pool.map(fetch, [server.url(item) for item in range(n)], range(n))
        log.info("threads running: %s", ", ".join(t.name for t in threading.enumerate()))
        list(answers)  # wait until every request has its answer
    return time.perf_counter() - start

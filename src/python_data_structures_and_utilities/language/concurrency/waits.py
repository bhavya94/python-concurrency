"""Waiting on the network, one request at a time.

`fetch` blocks: once it sends a request, its thread sits inside the socket read until the answer arrives, and
does nothing else. So n requests that each wait t take about n × t. The log shows every request on the same
thread, each one sent only after the previous answer.
"""

import logging
import time
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

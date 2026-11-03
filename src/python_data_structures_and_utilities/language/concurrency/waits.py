"""Waiting on the network: one request to the slow server.

`fetch` blocks: once it sends a request, its thread sits inside the socket read until the answer arrives, and
does nothing else. One thread therefore takes about n × t for n requests. N threads can wait at the same time,
so they take about ⌈n / N⌉ × t. `ways.py` runs the requests either way.
"""

import logging
import threading
import time
from urllib.request import urlopen

from python_data_structures_and_utilities.language.concurrency.server import url
from python_data_structures_and_utilities.language.concurrency.timeline import Span

log = logging.getLogger(__name__)


def fetch(port: int, item: int) -> Span:
    """One blocking request. It logs the time on the clock and the CPU time this thread used: a thread that is
    blocked waits without computing, so its CPU time stays near zero."""
    start, cpu = time.time(), time.thread_time()
    log.info("item %d: request sent, waiting for the answer", item)
    with urlopen(url(port, item)) as answer:
        answer.read()
    end, used = time.time(), time.thread_time() - cpu
    log.info("item %d: answered after %.0f ms, using %.1f ms of this thread's CPU", item, (end - start) * 1000,
             used * 1000)
    return Span(item, threading.current_thread().name, start, end, used)

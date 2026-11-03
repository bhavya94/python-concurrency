"""Computing: one CPU-bound item, plain Python arithmetic with no waiting.

`burn` never blocks, so its thread keeps the GIL until the interpreter asks it to hand the GIL over, every 5 ms
by default (`sys.getswitchinterval()`). Threads running `burn` therefore take turns: only one computes at any
moment. Each item's time on the clock stretches, while its CPU time stays the same.
"""

import logging
import time

from python_concurrency.timeline import Span, who

log = logging.getLogger(__name__)


def burn(size: int, item: int) -> Span:
    """Add up i × i for i below `size`. About 100 ms for 2,500,000 on an M1 Mac."""
    start, cpu = time.time(), time.thread_time()
    log.info("item %d: computing", item)
    total = 0
    for i in range(size):
        total += i * i
    end, used = time.time(), time.thread_time() - cpu
    log.info("item %d: done after %.0f ms, using %.0f ms of this thread's CPU", item, (end - start) * 1000,
             used * 1000)
    return Span(item, who(), start, end, used)

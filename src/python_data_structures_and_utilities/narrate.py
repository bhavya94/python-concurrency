"""Narration: log lines that say what the code is doing, and where it is doing it.

Every line starts with the time since the run began, then the process, the thread and the asyncio task:

    +  412.3ms pid=4182  thread=worker_1     task=-        concurrency.work: item 3 answered after 201 ms

Read the columns to see what ran at the same time. Two lines with nearly the same time and different threads
mean two threads were busy at once. Two lines with the same thread and different tasks mean one thread switched
between tasks.

INFO tells the story: each step and each decision. DEBUG adds the internals, such as bytes pickled.
The CLI calls `setup()` once. A worker process must call it again, from the pool's initializer: a spawned
process starts as a fresh interpreter, with no logging set up and no memory of the parent's start time.
"""

import asyncio
import logging
import time

FORMAT = ("%(elapsed)+9.1fms pid=%(process)-5d thread=%(threadName)-12s task=%(task)-8s %(where)s: "
          "%(message)s")


class _Where(logging.Filter):
    """Adds the columns that the standard log record lacks: time since the run began, the task, a short name."""

    def __init__(self, t0: float):
        super().__init__()
        self.t0 = t0

    def filter(self, record: logging.LogRecord) -> bool:
        # record.created comes from time.time(), the wall clock. Every process reads the same clock, so lines from
        # worker processes line up with lines from the parent.
        record.elapsed = (record.created - self.t0) * 1000
        try:
            task = asyncio.current_task()
        except RuntimeError:  # this thread has no running event loop
            task = None
        record.task = task.get_name() if task else "-"
        record.where = record.name.removeprefix("python_data_structures_and_utilities.language.")
        return True


def setup(level: int = logging.INFO, t0: float | None = None) -> float:
    """Send every `pdsau` log line to stderr in the format above. Returns the start time, so a worker process can
    be given the same one."""
    t0 = time.time() if t0 is None else t0
    handler = logging.StreamHandler()
    handler.addFilter(_Where(t0))
    handler.setFormatter(logging.Formatter(FORMAT))
    root = logging.getLogger("python_data_structures_and_utilities")
    root.handlers[:] = [handler]
    root.setLevel(level)
    root.propagate = False
    return t0

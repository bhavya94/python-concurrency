"""The waiting job: n requests to the slow server, each waiting t. There is almost nothing to compute, so the run
time depends only on how many waits overlap.

Run it five ways, and compare each with a simple cost model:

| Way              | Who waits                                  | Model, compute ≈ 0 |
|------------------|--------------------------------------------|--------------------|
| sequential       | one thread, one wait at a time             | n · t              |
| threads          | N threads, one wait each                   | ⌈n / N⌉ · t        |
| processes        | N processes, one wait each                 | S + ⌈n / N⌉ · t    |
| asyncio          | one thread, A tasks waiting at once        | ⌈n / A⌉ · t        |
| asyncio-blocking | one thread, but each task blocks the loop  | n · t              |

S is the start-up cost of the process pool: start N fresh interpreters and import this code in each.
Here A, the asyncio limit, equals N, so the ways compare fairly.

Try: run `pdsau concurrency waits --way threads --workers 8` and watch the timeline lose its second round.
"""

import asyncio
import logging
import math
import pickle
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass

from python_data_structures_and_utilities import narrate
from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.work import Span, fetch, fetch_async

log = logging.getLogger(__name__)
WAYS = ("sequential", "threads", "processes", "asyncio", "asyncio-blocking")


@dataclass(frozen=True)
class Run:
    way: str
    spans: list[Span]
    started: float
    ended: float

    @property
    def wall_ms(self) -> float:
        return (self.ended - self.started) * 1000

    @property
    def startup_ms(self) -> float:
        """Time before the first request went out. For processes, that is the pool's start-up cost, S."""
        return (min(s.start for s in self.spans) - self.started) * 1000

    @property
    def shutdown_ms(self) -> float:
        """Time after the last answer. For processes, the pool waits for every worker process to exit."""
        return (self.ended - max(s.end for s in self.spans)) * 1000


class WaitJob:
    def __init__(self, server: SlowServer, n: int, workers: int, t0: float, level: int = logging.INFO):
        self.server = server
        self.n = n
        self.workers = workers
        # The run's start time and log level go to each worker process, so its log lines match the parent's.
        self.t0 = t0
        self.level = level

    def run(self, way: str) -> Run:
        log.info("--- %s: %d requests, %d workers ---", way, self.n, self.workers)
        started = time.time()
        spans = getattr(self, "_" + way.replace("-", "_"))()
        run = Run(way, sorted(spans, key=lambda s: s.start), started, time.time())
        log.info("%s took %.0f ms: %.0f ms before the first request, %.0f ms after the last answer", way,
                 run.wall_ms, run.startup_ms, run.shutdown_ms)
        return run

    def predict(self, way: str, startup_ms: float = 0.0) -> tuple[str, float]:
        """The cost model with this run's numbers: the formula, filled in, and the time in ms. S can't be known
        in advance, so the processes row takes the measured `startup_ms`."""
        n, workers, t = self.n, self.workers, self.server.delay * 1000
        rounds = math.ceil(n / workers)
        if way in ("sequential", "asyncio-blocking"):
            return f"n·t = {n}·{t:.0f}", n * t
        name = "A" if way == "asyncio" else "N"
        formula = f"⌈n/{name}⌉·t = ⌈{n}/{workers}⌉·{t:.0f} = {rounds}·{t:.0f}"
        if way == "processes":
            return f"S + ⌈n/N⌉·t = {startup_ms:.0f} + ⌈{n}/{workers}⌉·{t:.0f}", startup_ms + rounds * t
        return formula, rounds * t

    def _sequential(self) -> list[Span]:
        return [fetch(self.server.url(i), i) for i in range(self.n)]

    def _threads(self) -> list[Span]:
        # Each thread takes the next request when it is free. N threads hold at most N waits at once.
        with ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="worker") as pool:
            return list(pool.map(fetch, [self.server.url(i) for i in range(self.n)], range(self.n)))

    def _processes(self) -> list[Span]:
        # The pool pickles each task and sends the bytes to a worker process, then pickles the Span back. A function
        # pickles by reference, as its module and name, and the worker imports it; only the arguments travel as
        # data. Waiting needs no parallel CPU, so here processes pay S and gain nothing over threads.
        log.debug("one task pickles to about %d bytes (the pool adds its own wrapping)",
                  len(pickle.dumps((fetch, self.server.url(0), 0))))
        with ProcessPoolExecutor(self.workers, initializer=narrate.setup, initargs=(self.level, self.t0)) as pool:
            # The pool starts its processes lazily, as tasks arrive, up to N of them.
            log.info("pool created with no processes yet; it starts up to %d as tasks arrive", self.workers)
            return list(pool.map(fetch, [self.server.url(i) for i in range(self.n)], range(self.n)))

    def _asyncio(self) -> list[Span]:
        return asyncio.run(self._gather(blocking=False))

    def _asyncio_blocking(self) -> list[Span]:
        return asyncio.run(self._gather(blocking=True))

    async def _gather(self, blocking: bool) -> list[Span]:
        limit = asyncio.Semaphore(self.workers)  # at most A requests in flight

        async def one(item: int) -> Span:
            async with limit:
                if blocking:
                    # The mistake: a blocking call inside a coroutine. It never awaits, so the loop can't switch
                    # tasks until it returns. Every other task waits its turn.
                    return fetch(self.server.url(item), item)
                return await fetch_async(self.server.port, item)

        async with asyncio.TaskGroup() as group:  # waits for every task; cancels the rest if one fails
            tasks = [group.create_task(one(i), name=f"item-{i}") for i in range(self.n)]
        log.info("all %d tasks done, on one thread", self.n)
        return [task.result() for task in tasks]

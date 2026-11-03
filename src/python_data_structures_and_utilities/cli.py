"""`pdsau`: the one command. Each concept the repo adds becomes a subcommand here."""

import argparse
import logging
import math
import os
import time
from functools import partial

from python_data_structures_and_utilities.language.concurrency.async_waits import with_asyncio
from python_data_structures_and_utilities.language.concurrency.compute import burn
from python_data_structures_and_utilities.language.concurrency.race import STEPS, race
from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.timeline import render
from python_data_structures_and_utilities.language.concurrency.waits import fetch
from python_data_structures_and_utilities.language.concurrency.ways import one_at_a_time, with_processes, with_threads

# Each log line starts with the ms since the program started, then the thread that wrote it.
LOG_FORMAT = "%(relativeCreated)7.1fms  %(threadName)-10s  %(message)s"
# With worker processes, a column for the process too.
PROCESS_LOG_FORMAT = "%(relativeCreated)7.1fms  %(processName)-15s %(threadName)-10s  %(message)s"
# With asyncio, a column for the task: None outside any task.
TASK_LOG_FORMAT = "%(relativeCreated)7.1fms  %(threadName)-10s  %(taskName)-6s  %(message)s"


def _log_like_the_parent(start: float) -> None:
    """Runs first in each worker process, which starts with no logging set up. `relativeCreated` counts from the
    moment the logging module loaded, which in a worker is later than in the parent. Giving the worker the
    parent's start time lines the two logs up."""
    logging.basicConfig(level=logging.INFO, format=PROCESS_LOG_FORMAT)
    logging._startTime = start


def _at_least(minimum: int):
    def parse(text: str) -> int:
        if (value := int(text)) < minimum:
            raise argparse.ArgumentTypeError(f"must be {minimum} or more, not {value}")
        return value
    return parse


def _run(args: argparse.Namespace, task):
    if args.way == "processes":
        return with_processes(task, args.n, args.workers, setup=partial(_log_like_the_parent, logging._startTime))
    return with_threads(task, args.n, args.workers) if args.way == "threads" else one_at_a_time(task, args.n)


def _waits(args: argparse.Namespace) -> None:
    n, t, workers = args.n, args.wait_ms, args.workers
    with SlowServer(delay=t / 1000) as server:
        if args.way == "asyncio":
            run = with_asyncio(server.port, n, workers)
        else:
            run = _run(args, partial(fetch, server.port))
    print("\n" + render(run))
    if args.way in ("threads", "asyncio"):
        rounds = math.ceil(n / workers)
        who = f"{workers} threads" if args.way == "threads" else f"asyncio, {workers} tasks in flight, one thread"
        print(f"\n{n} requests, {who}: {run.ms:.0f} ms")
        print(f"model: ⌈n/N⌉ × t = ⌈{n}/{workers}⌉ × {t} = {rounds} × {t} = {rounds * t} ms")
    else:
        print(f"\n{n} requests, one at a time: {run.ms:.0f} ms")
        print(f"model: n × t = {n} × {t} = {n * t} ms")


def _compute(args: argparse.Namespace) -> None:
    run = _run(args, partial(burn, args.size))
    print("\n" + render(run))
    n, workers, c = args.n, args.workers, sum(span.cpu for span in run.spans) / args.n * 1000
    who = {"threads": f"{workers} threads", "processes": f"{workers} processes"}.get(args.way, "one at a time")
    print(f"\n{n} items, {who}: {run.ms:.0f} ms")
    print(f"c, one item's own CPU time, on average: {c:.0f} ms")
    if args.way == "processes":
        s, rounds = (min(span.start for span in run.spans) - run.start) * 1000, math.ceil(n / workers)
        print(f"S, the time before the first item began: {s:.0f} ms, to start the worker processes")
        print(f"after the last item: {(run.end - max(span.end for span in run.spans)) * 1000:.0f} ms, "
              "for the worker processes to exit")
        print(f"model: S + ⌈n/N⌉ × c = {s:.0f} + ⌈{n}/{workers}⌉ × {c:.0f} = {s + rounds * c:.0f} ms. "
              f"Each process has its own GIL, so up to N items compute at once. This Mac has "
              f"{os.process_cpu_count()} cores.")
        return
    print(f"model: n × c = {n} × {c:.0f} = {n * c:.0f} ms" +
          (". Only the thread that holds the GIL computes, so threads take turns." if args.way == "threads" else ""))


def _race(args: argparse.Namespace) -> None:
    expected, start = args.threads * args.times, time.time()
    got = race(args.threads, args.times, args.step, args.lock)
    print(f"\nexpected: {args.threads} threads × {args.times} = {expected}")
    print(f"counter:  {got}, so {expected - got} updates lost ({(expected - got) / expected:.0%})")
    print(f"took:     {(time.time() - start) * 1000:.0f} ms")


def _ways(parser: argparse.ArgumentParser, things: str, ways: tuple[str, ...] = ("one-at-a-time", "threads")) -> None:
    parser.add_argument("--way", choices=ways, default="one-at-a-time",
                        help=f"{', '.join(ways)} (default one-at-a-time)")
    parser.add_argument("--n", type=_at_least(1), default=8, help=f"how many {things} (default 8)")
    parser.add_argument("--workers", type=_at_least(1), default=4,
                        help="threads or processes in the pool, or asyncio tasks in flight (default 4)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="pdsau", description="Run one concept and watch what it does.")
    concepts = parser.add_subparsers(dest="concept", title="concepts")
    waits = concepts.add_parser("waits", help="n requests to a slow local server")
    _ways(waits, "requests", ("one-at-a-time", "threads", "asyncio"))
    waits.add_argument("--wait-ms", type=_at_least(0), default=200, help="how long each answer waits (default 200)")
    waits.set_defaults(run=_waits)
    compute = concepts.add_parser("compute", help="n CPU-bound items of plain Python arithmetic")
    _ways(compute, "items", ("one-at-a-time", "threads", "processes"))
    compute.add_argument("--size", type=_at_least(1), default=2_500_000,
                         help="loop steps per item; 2,500,000 is about 100 ms on an M1 Mac (default)")
    compute.set_defaults(run=_compute)
    racer = concepts.add_parser("race", help="threads add 1 to one shared counter; count the lost updates")
    racer.add_argument("--threads", type=_at_least(1), default=4, help="how many threads (default 4)")
    racer.add_argument("--times", type=_at_least(1), default=1_000_000, help="additions per thread (default 1000000)")
    racer.add_argument("--step", choices=STEPS, default="plus-equals",
                       help="counter.value += 1, or read, call a function, write (default plus-equals)")
    racer.add_argument("--lock", action="store_true",
                       help="hold one shared lock around each read, call and write (read-call-write only)")
    racer.set_defaults(run=_race)
    args = parser.parse_args()
    if getattr(args, "lock", False) and args.step != "read-call-write":
        parser.error("--lock goes with --step read-call-write")
    if args.concept is None:
        parser.print_help()
        return
    formats = {"processes": PROCESS_LOG_FORMAT, "asyncio": TASK_LOG_FORMAT}
    logging.basicConfig(level=logging.INFO, format=formats.get(getattr(args, "way", ""), LOG_FORMAT))
    args.run(args)

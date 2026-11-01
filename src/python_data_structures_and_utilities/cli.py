"""`pdsau`: the one command. Each concept the repo adds becomes a subcommand here."""

import argparse
import logging
import math
from functools import partial

from python_data_structures_and_utilities.language.concurrency.compute import burn
from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.timeline import render
from python_data_structures_and_utilities.language.concurrency.waits import fetch
from python_data_structures_and_utilities.language.concurrency.ways import one_at_a_time, with_threads

# Each log line starts with the ms since the program started, then the thread that wrote it.
LOG_FORMAT = "%(relativeCreated)7.1fms  %(threadName)-10s  %(message)s"


def _at_least(minimum: int):
    def parse(text: str) -> int:
        if (value := int(text)) < minimum:
            raise argparse.ArgumentTypeError(f"must be {minimum} or more, not {value}")
        return value
    return parse


def _run(args: argparse.Namespace, task):
    return with_threads(task, args.n, args.workers) if args.way == "threads" else one_at_a_time(task, args.n)


def _waits(args: argparse.Namespace) -> None:
    n, t, workers = args.n, args.wait_ms, args.workers
    with SlowServer(delay=t / 1000) as server:
        run = _run(args, partial(fetch, server.port))
    print("\n" + render(run))
    if args.way == "threads":
        rounds = math.ceil(n / workers)
        print(f"\n{n} requests, {workers} threads: {run.ms:.0f} ms")
        print(f"model: ⌈n/N⌉ × t = ⌈{n}/{workers}⌉ × {t} = {rounds} × {t} = {rounds * t} ms")
    else:
        print(f"\n{n} requests, one at a time: {run.ms:.0f} ms")
        print(f"model: n × t = {n} × {t} = {n * t} ms")


def _compute(args: argparse.Namespace) -> None:
    run = _run(args, partial(burn, args.size))
    print("\n" + render(run))
    n, c = args.n, sum(span.cpu for span in run.spans) / args.n * 1000
    who = f"{args.workers} threads" if args.way == "threads" else "one at a time"
    print(f"\n{n} items, {who}: {run.ms:.0f} ms")
    print(f"c, one item's own CPU time, on average: {c:.0f} ms")
    print(f"model: n × c = {n} × {c:.0f} = {n * c:.0f} ms" +
          (". Only the thread that holds the GIL computes, so threads take turns." if args.way == "threads" else ""))


def _ways(parser: argparse.ArgumentParser, things: str) -> None:
    parser.add_argument("--way", choices=("one-at-a-time", "threads"), default="one-at-a-time",
                        help="one at a time, or from a pool of threads (default one-at-a-time)")
    parser.add_argument("--n", type=_at_least(1), default=8, help=f"how many {things} (default 8)")
    parser.add_argument("--workers", type=_at_least(1), default=4, help="threads in the pool (default 4)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="pdsau", description="Run one concept and watch what it does.")
    concepts = parser.add_subparsers(dest="concept", title="concepts")
    waits = concepts.add_parser("waits", help="n requests to a slow local server")
    _ways(waits, "requests")
    waits.add_argument("--wait-ms", type=_at_least(0), default=200, help="how long each answer waits (default 200)")
    waits.set_defaults(run=_waits)
    compute = concepts.add_parser("compute", help="n CPU-bound items of plain Python arithmetic")
    _ways(compute, "items")
    compute.add_argument("--size", type=_at_least(1), default=2_500_000,
                         help="loop steps per item; 2,500,000 is about 100 ms on an M1 Mac (default)")
    compute.set_defaults(run=_compute)
    args = parser.parse_args()
    if args.concept is None:
        parser.print_help()
        return
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    args.run(args)

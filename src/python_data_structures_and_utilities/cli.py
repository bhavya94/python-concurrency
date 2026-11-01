"""`pdsau`: the one command. Each concept the repo adds becomes a subcommand here."""

import argparse
import logging
import math

from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.waits import one_at_a_time, with_threads

# Each log line starts with the ms since the program started, then the thread that wrote it.
LOG_FORMAT = "%(relativeCreated)7.1fms  %(threadName)-10s  %(message)s"


def _at_least(minimum: int):
    def parse(text: str) -> int:
        if (value := int(text)) < minimum:
            raise argparse.ArgumentTypeError(f"must be {minimum} or more, not {value}")
        return value
    return parse


def _waits(args: argparse.Namespace) -> None:
    n, t, workers = args.n, args.wait_ms, args.workers
    with SlowServer(delay=t / 1000) as server:
        if args.way == "threads":
            total = with_threads(server, n, workers)
        else:
            total = one_at_a_time(server, n)
    if args.way == "threads":
        rounds = math.ceil(n / workers)
        print(f"\n{n} requests, {workers} threads: {total * 1000:.0f} ms")
        print(f"model: ⌈n/N⌉ × t = ⌈{n}/{workers}⌉ × {t} = {rounds} × {t} = {rounds * t} ms")
    else:
        print(f"\n{n} requests, one at a time: {total * 1000:.0f} ms")
        print(f"model: n × t = {n} × {t} = {n * t} ms")


def main() -> None:
    parser = argparse.ArgumentParser(prog="pdsau", description="Run one concept and watch what it does.")
    concepts = parser.add_subparsers(dest="concept", title="concepts")
    waits = concepts.add_parser("waits", help="n requests to a slow local server")
    waits.add_argument("--way", choices=("one-at-a-time", "threads"), default="one-at-a-time",
                       help="how to send them (default one-at-a-time)")
    waits.add_argument("--n", type=_at_least(1), default=8, help="how many requests (default 8)")
    waits.add_argument("--wait-ms", type=_at_least(0), default=200, help="how long each answer waits (default 200)")
    waits.add_argument("--workers", type=_at_least(1), default=4, help="threads in the pool (default 4)")
    waits.set_defaults(run=_waits)
    args = parser.parse_args()
    if args.concept is None:
        parser.print_help()
        return
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    args.run(args)

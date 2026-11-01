"""`pdsau`: the one command. Each concept the repo adds becomes a subcommand here."""

import argparse
import logging

from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.waits import one_at_a_time

# Each log line starts with the ms since the program started, then the thread that wrote it.
LOG_FORMAT = "%(relativeCreated)7.1fms  %(threadName)-10s  %(message)s"


def _at_least(minimum: int):
    def parse(text: str) -> int:
        if (value := int(text)) < minimum:
            raise argparse.ArgumentTypeError(f"must be {minimum} or more, not {value}")
        return value
    return parse


def _waits(args: argparse.Namespace) -> None:
    with SlowServer(delay=args.wait_ms / 1000) as server:
        total = one_at_a_time(server, args.n)
    print(f"\n{args.n} requests, one at a time: {total * 1000:.0f} ms")
    print(f"model: n × t = {args.n} × {args.wait_ms} = {args.n * args.wait_ms} ms")


def main() -> None:
    parser = argparse.ArgumentParser(prog="pdsau", description="Run one concept and watch what it does.")
    concepts = parser.add_subparsers(dest="concept", title="concepts")
    waits = concepts.add_parser("waits", help="n requests to a slow local server, one at a time")
    waits.add_argument("--n", type=_at_least(1), default=8, help="how many requests (default 8)")
    waits.add_argument("--wait-ms", type=_at_least(0), default=200, help="how long each answer waits (default 200)")
    waits.set_defaults(run=_waits)
    args = parser.parse_args()
    if args.concept is None:
        parser.print_help()
        return
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    args.run(args)

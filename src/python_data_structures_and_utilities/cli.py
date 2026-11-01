"""`pdsau`: run a lab. The log lines (stderr) narrate the run; the timeline and the summary (stdout) are the results.

    pdsau concurrency waits                    all five ways, 8 requests, 4 workers, 200 ms per wait
    pdsau concurrency waits --way asyncio -v   one way, with the DEBUG lines too
    pdsau concurrency waits -q                 results only
"""

import argparse
import logging

from python_data_structures_and_utilities import narrate
from python_data_structures_and_utilities.language.concurrency.server import SlowServer
from python_data_structures_and_utilities.language.concurrency.timeline import render
from python_data_structures_and_utilities.language.concurrency.waits import WAYS, WaitJob


def _waits(args: argparse.Namespace, t0: float, level: int) -> None:
    ways = WAYS if args.way == "all" else (args.way,)
    with SlowServer(delay=args.wait_ms / 1000) as server:
        job = WaitJob(server, args.n, args.workers, t0, level)
        runs = []
        for way in ways:
            run = job.run(way)
            print(f"\n{way}\n{render(run)}", flush=True)
            runs.append(run)
    print(f"\n{'way':<17} {'model':<44} {'predicted':>10} {'measured':>9}")
    for run in runs:
        formula, predicted = job.predict(run.way, run.startup_ms)
        print(f"{run.way:<17} {formula:<44} {predicted:>7.0f} ms {run.wall_ms:>6.0f} ms")
    for run in runs:
        if run.way == "processes":
            print(f"\nprocesses: S is measured, the time before the first request: {run.startup_ms:.0f} ms until the first "
                  f"of {min(job.n, job.workers)} interpreters was ready.\nThe pool also took {run.shutdown_ms:.0f} ms after the last answer, "
                  "for its worker processes to exit. The model leaves that out.")


def _positive(text: str) -> int:
    if (value := int(text)) < 1:
        raise argparse.ArgumentTypeError(f"must be 1 or more, not {value}")
    return value


def main() -> None:
    loudness = argparse.ArgumentParser(add_help=False)  # every lab takes these, after its own name
    one = loudness.add_mutually_exclusive_group()
    one.add_argument("-v", "--verbose", action="store_true", help="add the DEBUG lines")
    one.add_argument("-q", "--quiet", action="store_true", help="no narration, results only")
    parser = argparse.ArgumentParser(prog="pdsau")
    labs = parser.add_subparsers(dest="lab", required=True)
    concurrency = labs.add_parser("concurrency", help="threads, processes and asyncio on the same job")
    jobs = concurrency.add_subparsers(dest="job", required=True)
    waits = jobs.add_parser("waits", parents=[loudness], help="n requests to a slow local server, each waiting the same time")
    waits.add_argument("--way", choices=("all", *WAYS), default="all")
    waits.add_argument("--n", type=_positive, default=8, help="requests")
    waits.add_argument("--workers", type=_positive, default=4, help="threads, processes, or the asyncio limit")
    waits.add_argument("--wait-ms", type=float, default=200, help="how long the server waits before each answer")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.WARNING if args.quiet else logging.INFO
    t0 = narrate.setup(level)
    _waits(args, t0, level)

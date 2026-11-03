"""Waiting with asyncio: many requests in flight from one thread.

`fetch_async` doesn't block. At each `await`, its task pauses, and the event loop, asyncio's scheduler, runs
another task until the socket is ready. So one thread can hold N waits at once, and n requests take about
⌈n / N⌉ × t, as with N threads, but with one thread and no GIL hand-overs.

The classic mistake is a blocking call inside a task, such as `urlopen`. It never awaits, so the loop can't run
another task until it returns, and the requests go one at a time again. The fix is to hand the blocking call to
a thread with `asyncio.to_thread` and await that.
"""

import asyncio
import logging
import time

from python_concurrency.timeline import Run, Span, who
from python_concurrency.waits import fetch

log = logging.getLogger(__name__)


async def fetch_async(port: int, item: int) -> Span:
    """One request over a raw socket, written in HTTP/1.0 so the server closes the connection after its answer."""
    start = time.time()
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(f"GET /item/{item} HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n".encode())
    await writer.drain()
    log.info("item %d: request sent; this task now waits, and the loop runs the others", item)
    await reader.read()  # pauses this task until the server has answered and closed the connection
    writer.close()
    await writer.wait_closed()
    end = time.time()
    log.info("item %d: answered after %.0f ms", item, (end - start) * 1000)
    return Span(item, who(), start, end)


CALLS = ("await", "blocking", "to-thread")


async def _all(port: int, n: int, limit: int, call: str) -> list[Span]:
    gate = asyncio.Semaphore(limit)  # at most `limit` requests in flight

    async def one(item: int) -> Span:
        async with gate:  # a task past `limit` waits here for a free place
            if call == "blocking":
                return fetch(port, item)  # the mistake: no await, so the whole loop waits for this request
            if call == "to-thread":
                return await asyncio.to_thread(fetch, port, item)  # the fix: a thread waits; this task awaits it
            return await fetch_async(port, item)

    async with asyncio.TaskGroup() as group:  # waits for every task; cancels the rest if one fails
        tasks = [group.create_task(one(item), name=f"item-{item}") for item in range(n)]
    return [task.result() for task in tasks]


def with_asyncio(port: int, n: int, limit: int, call: str = "await") -> Run:
    """Send n requests as n asyncio tasks on this thread, with at most `limit` in flight. `call` picks how each
    task makes its request: `await` the async fetch, call the blocking `fetch`, or run `fetch` in a thread."""
    start = time.time()
    spans = asyncio.run(_all(port, n, limit, call))
    return Run(spans, start, time.time())

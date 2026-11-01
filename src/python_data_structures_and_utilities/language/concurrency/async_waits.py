"""Waiting with asyncio: many requests in flight from one thread.

`fetch_async` doesn't block. At each `await`, its task pauses, and the event loop, asyncio's scheduler, runs
another task until the socket is ready. So one thread can hold N waits at once, and n requests take about
⌈n / N⌉ × t, as with N threads, but with one thread and no GIL hand-overs.
"""

import asyncio
import logging
import time

from python_data_structures_and_utilities.language.concurrency.timeline import Run, Span, who

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


async def _all(port: int, n: int, limit: int) -> list[Span]:
    gate = asyncio.Semaphore(limit)  # at most `limit` requests in flight

    async def one(item: int) -> Span:
        async with gate:  # a task past `limit` waits here for a free place
            return await fetch_async(port, item)

    async with asyncio.TaskGroup() as group:  # waits for every task; cancels the rest if one fails
        tasks = [group.create_task(one(item), name=f"item-{item}") for item in range(n)]
    return [task.result() for task in tasks]


def with_asyncio(port: int, n: int, limit: int) -> Run:
    """Send n requests as n asyncio tasks on this thread, with at most `limit` in flight."""
    start = time.time()
    spans = asyncio.run(_all(port, n, limit))
    return Run(spans, start, time.time())

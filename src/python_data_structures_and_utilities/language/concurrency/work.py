"""One unit of work, a request to the slow server, written two ways: blocking and async.

`fetch` blocks: the calling thread sleeps inside the socket read until the answer comes. While it sleeps, it
releases the GIL (the lock that lets only one thread run Python bytecode at a time), so other threads can run.
`fetch_async` doesn't block: at each `await`, the coroutine hands control back to the event loop, which runs
other tasks until the socket is ready.

Both return a Span: who did the work, and when. The timeline is drawn from spans.
"""

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass
from urllib.request import urlopen

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Span:
    item: int
    worker: str
    start: float
    """Wall-clock seconds (time.time()), so spans from worker processes line up with the parent's."""
    end: float


def worker() -> str:
    """Who is running this code: an asyncio task, else a named thread, else a process (its main thread)."""
    try:
        task = asyncio.current_task()
    except RuntimeError:  # no event loop in this thread
        task = None
    if task:
        return task.get_name()
    if threading.current_thread() is not threading.main_thread():
        return threading.current_thread().name
    return f"pid {os.getpid()}"


def fetch(url: str, item: int) -> Span:
    """Blocking request. The thread waits here, holding no GIL, until the server answers."""
    start = time.time()
    log.info("item %d: request sent; this thread now waits", item)
    with urlopen(url) as answer:
        size = len(answer.read())
    end = time.time()
    log.info("item %d: %d bytes back after %.0f ms", item, size, (end - start) * 1000)
    return Span(item, worker(), start, end)


async def fetch_async(port: int, item: int) -> Span:
    """Non-blocking request over a raw socket. Each `await` is a point where the event loop may switch tasks."""
    start = time.time()
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(f"GET /item/{item} HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n".encode())
    await writer.drain()
    log.info("item %d: request sent; this task now waits and the loop runs other tasks", item)
    answer = await reader.read()  # HTTP/1.0: the server closes the connection after the answer
    size = len(answer.partition(b"\r\n\r\n")[2])  # the body, after the headers, as urlopen returns it
    writer.close()
    await writer.wait_closed()
    end = time.time()
    log.info("item %d: %d bytes back after %.0f ms", item, size, (end - start) * 1000)
    return Span(item, worker(), start, end)

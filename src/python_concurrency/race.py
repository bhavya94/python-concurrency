"""A race: several threads add 1 to one shared counter object.

Adding 1 is three steps: read the value, add 1, write the result back. If another thread runs between one
thread's read and its write, the first thread then writes back an out-of-date value, and an update is lost.

With the GIL, CPython lets another thread run only at certain points in the bytecode, such as the start of a
function call or the jump back to the top of a loop. `counter.value += 1` has no such point between its read and
its write, so on CPython 3.14 it loses nothing. That is luck of the interpreter, not a promise. A function call
between the read and the write adds such a point, and updates go missing.

The fix is one lock, shared by every thread, held around the read, the call and the write together. A thread
that reaches `with lock:` while another holds it waits there. So no thread can run between another's read and
its write.
"""

import logging
import threading
import time

log = logging.getLogger(__name__)
STEPS = ("plus-equals", "read-call-write")


class Counter:
    """One object that every thread uses. Threads in one process share its memory, so there is no copy."""

    def __init__(self):
        self.value = 0


def _plus_one(value: int) -> int:
    return value + 1


def bump(counter: Counter, times: int, step: str, lock: threading.Lock | None = None) -> None:
    """Add 1 to the counter `times` times, with the step chosen. With a lock, the step is read-call-write."""
    start = time.time()
    log.info("adding 1, %d times, to the counter object at %#x%s", times, id(counter),
             f", holding the lock at {id(lock):#x}" if lock else "")
    if lock:
        for _ in range(times):
            with lock:  # one thread at a time runs the read, the call and the write
                value = counter.value
                value = _plus_one(value)
                counter.value = value
    elif step == "plus-equals":
        for _ in range(times):
            counter.value += 1
    else:
        for _ in range(times):
            value = counter.value  # read
            value = _plus_one(value)  # a call: another thread may run here
            counter.value = value  # write
    log.info("done after %.0f ms", (time.time() - start) * 1000)


def race(threads: int, times: int, step: str, lock: bool = False) -> int:
    """Start `threads` threads that each add 1 `times` times to one counter, with one shared lock if `lock`.
    Returns the counter's final value."""
    counter, shared = Counter(), threading.Lock() if lock else None
    adders = [threading.Thread(target=bump, args=(counter, times, step, shared), name=f"adder_{i}")
              for i in range(threads)]
    for adder in adders:
        adder.start()
    for adder in adders:
        adder.join()  # wait for this thread to finish
    return counter.value

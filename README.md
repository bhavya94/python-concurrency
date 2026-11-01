# python-data-structures-and-utilities

Runnable labs for how Python works underneath: its runtime, concurrency, performance and data structures.
Each lab narrates itself as it runs. Every log line says which process, thread and asyncio task wrote it, so you
can watch the concept happen instead of taking it on trust.

## Evidence

The first lab sends 8 requests to a slow local server. Each answer takes 200 ms. The lab runs the same job five
ways and compares each with a simple cost model:

```console
$ uv run pdsau concurrency waits -q
way               model                                         predicted  measured
sequential        n·t = 8·200                                     1600 ms   1677 ms
threads           ⌈n/N⌉·t = ⌈8/4⌉·200 = 2·200                      400 ms    420 ms
processes         S + ⌈n/N⌉·t = 109 + ⌈8/4⌉·200                    509 ms    573 ms
asyncio           ⌈n/A⌉·t = ⌈8/4⌉·200 = 2·200                      400 ms    417 ms
asyncio-blocking  n·t = 8·200                                     1600 ms   1656 ms
```

Four threads or four asyncio tasks wait at the same time, so they finish in two rounds of 200 ms instead of
eight. Processes wait just as well, but they first pay S, about 100 ms, to start four new Python interpreters. A
blocking call inside asyncio undoes it all: the event loop can't switch tasks, so the run is sequential again.

## Words to know

| Word | What it means here |
|---|---|
| Process | A running program with its own memory. Two processes share nothing unless they send data to each other. |
| Thread | A line of work inside a process. Threads in one process share its memory. |
| GIL | The global interpreter lock. In the standard CPython build, only the thread that holds it can run Python code. A thread lets go of it while it waits on the network or the disk. |
| Event loop | asyncio's scheduler. One thread runs many tasks, and the loop switches to another task whenever the current one waits. |
| Coroutine, task | A coroutine is a function defined with `async def`. A task is a coroutine that the event loop is running. `await` marks a point where the task may pause. |
| Blocking call | A call that holds the thread until it returns, such as `urlopen`. Inside a coroutine it freezes the whole loop. |
| Pickle | Python's way to turn an object into bytes. A process pool pickles each task to send it to a worker. The function travels as a reference (its module and name), which the worker imports; the arguments travel as data. |

## Labs

| Lab | Command | What to watch |
|---|---|---|
| Waiting: threads, processes and asyncio | `pdsau concurrency waits` | Which waits overlap, and what each way costs to start |

More labs follow: CPU-bound work with and without the GIL, then the runtime (reference counts, the cycle
collector, bytecode) and performance (profiling first, then the fix).

## Run it

```console
uv sync
uv run pytest
uv run pdsau concurrency waits                    # all five ways, with the narration
uv run pdsau concurrency waits --way asyncio -v   # one way, with the DEBUG lines too
uv run pdsau concurrency waits -q                 # results only
uv run pdsau concurrency waits --workers 8        # one round of waits instead of two
```

## Read the narration

The narration goes to stderr; the timeline and the summary go to stdout.

```console
 +1679.3ms pid=78267 thread=worker_0     task=-        concurrency.work: item 0: request sent; this thread now waits
 +1679.7ms pid=78267 thread=worker_1     task=-        concurrency.work: item 1: request sent; this thread now waits
 +2665.0ms pid=78267 thread=MainThread   task=item-0   concurrency.work: item 0: request sent; this task now waits ...
```

- The first column is the time since the run began. Worker processes use the same start time, so their lines
  line up with the parent's.
- When nearly the same time appears on two different threads, those threads were busy at once.
- When one thread shows several tasks, the event loop switched between them on that thread.

The timeline draws the same story. Each row is one worker, and each digit is the item it was waiting on:

```console
threads
worker_0  |000000000000000000000000000000777777777777777777777777777777|
worker_1  |111111111111111111111111111111666666666666666666666666666666|
worker_2  |222222222222222222222222222224444444444444444444444444444444|
worker_3  |333333333333333333333333333335555555555555555555555555555555|
           0 ms                                                  420 ms
```

To explore, put `breakpoint()` inside `fetch` in `language/concurrency/work.py` and run one way. Then print
`threading.current_thread().name` or `asyncio.current_task()` at the prompt.

## Layers

`narrate.py` imports nothing from the package. The labs under `language/` import `narrate`. `cli.py` sits on top.
Library code narrates through `logging`; only `cli.py` prints results. `tests/test_layers.py` enforces both.

## Limits

- The server and the client run on one machine, so a wait here is a local socket wait plus a sleep. A real
  network adds latency that varies from one request to the next.
- Times vary by a few percent from run to run. The tests check the shape (overlap or no overlap) with wide
  margins, not exact times.
- The model leaves out per-request overhead (5 to 21 ms each in the run above) and the process pool's shut-down time, which
  the summary reports separately.

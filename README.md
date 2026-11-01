# python-data-structures-and-utilities

How Python runs your code, built up one concept per pull request. Each concept is a small runnable command with
a test. Its output shows what the concept does: which thread, process or task did the work, and how long it took.

## Run it

Needs [uv](https://docs.astral.sh/uv/). It installs Python 3.14 if you don't have it.

```console
uv sync
uv run pytest
uv run pdsau --help
```

## Waiting, one request at a time

`pdsau waits` starts a slow web server inside the program. Each answer takes 200 ms. Then it sends requests one
after another: 8 by default, 3 here.

```console
$ uv run pdsau waits --n 3
   52.1ms  MainThread  slow server on port 61240; every answer waits 200 ms
   52.3ms  MainThread  threads running: MainThread, server
   52.4ms  MainThread  item 0: request sent, waiting for the answer
   64.1ms  server      connection accepted; starting a new thread to handle it
   64.4ms  handler-0   received /item/0; sleeping 200 ms
  269.5ms  handler-0   answering /item/0
  271.7ms  MainThread  item 0: answered after 219 ms, using 8.1 ms of this thread's CPU
  271.8ms  MainThread  item 1: request sent, waiting for the answer
  272.6ms  server      connection accepted; starting a new thread to handle it
  272.9ms  handler-1   received /item/1; sleeping 200 ms
  477.7ms  handler-1   answering /item/1
  478.7ms  MainThread  item 1: answered after 207 ms, using 1.1 ms of this thread's CPU
  478.9ms  MainThread  item 2: request sent, waiting for the answer
  479.9ms  server      connection accepted; starting a new thread to handle it
  480.4ms  handler-2   received /item/2; sleeping 200 ms
  683.2ms  handler-2   answering /item/2
  684.1ms  MainThread  item 2: answered after 205 ms, using 1.2 ms of this thread's CPU

MainThread  |00000000000000000000111111111111111111112222222222222222222·|
             0 ms                                                  632 ms

3 requests, one at a time: 632 ms
model: n × t = 3 × 200 = 600 ms
```

Each line starts with the ms since the program started, then the thread that wrote it.

- Three kinds of thread take part. `MainThread` sends the requests. `server` accepts each connection and starts
  a new thread for it. `handler-N` sleeps 200 ms, then answers.
- `MainThread` sends item 1 only after item 0's answer arrives. While it waits, it is blocked and does nothing
  else.
- Over each 200 ms wait, `MainThread` uses about 1 ms of CPU; the first request costs 6 to 9 ms. The program is
  waiting, not computing: the job is I/O-bound.
- So the total is about n × t. The few ms over 200 per request is the connection and HTTP work.

Try `--n` and `--wait-ms` to change n and t.

## Waiting, from several threads

`--way threads` sends the same requests from a pool of N threads, 4 by default and 2 here. Each thread takes the
next request as soon as it is free.

```console
$ uv run pdsau waits --way threads --n 4 --workers 2
   23.3ms  MainThread  slow server on port 61244; every answer waits 200 ms
   23.4ms  MainThread  threads running: MainThread, server
   23.5ms  worker_0    item 0: request sent, waiting for the answer
   23.6ms  worker_1    item 1: request sent, waiting for the answer
   23.7ms  MainThread  threads running: MainThread, server, worker_0, worker_1
   31.9ms  server      connection accepted; starting a new thread to handle it
   32.1ms  handler-0   received /item/0; sleeping 200 ms
   32.2ms  server      connection accepted; starting a new thread to handle it
   32.3ms  handler-1   received /item/1; sleeping 200 ms
  234.2ms  handler-1   answering /item/1
  236.0ms  worker_1    item 1: answered after 212 ms, using 5.4 ms of this thread's CPU
  236.1ms  worker_1    item 2: request sent, waiting for the answer
  236.7ms  server      connection accepted; starting a new thread to handle it
  237.2ms  handler-2   received /item/2; sleeping 200 ms
  237.3ms  handler-0   answering /item/0
  237.8ms  worker_0    item 0: answered after 214 ms, using 6.3 ms of this thread's CPU
  237.9ms  worker_0    item 3: request sent, waiting for the answer
  238.4ms  server      connection accepted; starting a new thread to handle it
  238.8ms  handler-3   received /item/3; sleeping 200 ms
  439.3ms  handler-2   answering /item/2
  440.6ms  worker_1    item 2: answered after 204 ms, using 1.0 ms of this thread's CPU
  440.8ms  handler-3   answering /item/3
  441.5ms  worker_0    item 3: answered after 204 ms, using 0.7 ms of this thread's CPU

worker_0  |00000000000000000000000000000033333333333333333333333333333·|
worker_1  |11111111111111111111111111111122222222222222222222222222222·|
           0 ms                                                  419 ms

4 requests, 2 threads: 419 ms
model: ⌈n/N⌉ × t = ⌈4/2⌉ × 200 = 2 × 200 = 400 ms
```

- `worker_0` and `worker_1` send items 0 and 1 within a millisecond of each other. Both wait at the same time.
- A thread blocked in its socket read has released the GIL, the lock a thread must hold to run Python code. So
  the other thread can run and send its own request.
- When a thread's answer arrives, it sends the next waiting item at once. Which thread gets which item can change
  from run to run.
- So the total is about ⌈n / N⌉ × t: 2 rounds of 200 ms, not 4. `--workers 64 --n 64` takes one round.

## Waiting, with asyncio: one thread, many tasks

`--way asyncio` sends the requests as asyncio tasks, all on one thread. At each `await`, a task pauses, and the
event loop, asyncio's scheduler, runs another task until the socket is ready. `--workers` is then the number
of requests in flight.

```console
$ uv run pdsau waits --way asyncio --n 4 --workers 2
  141.6ms  MainThread  None    slow server on port 64188; every answer waits 200 ms
  141.7ms  MainThread  None    threads running: MainThread, server
  142.4ms  server      None    connection accepted; starting a new thread to handle it
  142.4ms  MainThread  item-0  item 0: request sent; this task now waits, and the loop runs the others
  142.6ms  handler-0   None    received /item/0; sleeping 200 ms
  142.7ms  MainThread  item-1  item 1: request sent; this task now waits, and the loop runs the others
  142.7ms  server      None    connection accepted; starting a new thread to handle it
  142.8ms  handler-1   None    received /item/1; sleeping 200 ms
  347.9ms  handler-0   None    answering /item/0
  348.1ms  handler-1   None    answering /item/1
  350.7ms  MainThread  item-0  item 0: answered after 209 ms
  351.2ms  MainThread  item-1  item 1: answered after 209 ms
  351.3ms  server      None    connection accepted; starting a new thread to handle it
  352.0ms  server      None    connection accepted; starting a new thread to handle it
  352.0ms  MainThread  item-2  item 2: request sent; this task now waits, and the loop runs the others
  352.2ms  handler-2   None    received /item/2; sleeping 200 ms
  352.7ms  handler-3   None    received /item/3; sleeping 200 ms
  352.6ms  MainThread  item-3  item 3: request sent; this task now waits, and the loop runs the others
  553.3ms  handler-3   None    answering /item/3
  554.1ms  MainThread  item-3  item 3: answered after 203 ms
  554.2ms  handler-2   None    answering /item/2
  554.7ms  MainThread  item-2  item 2: answered after 204 ms

item-0  |000000000000000000000000000000······························|
item-1  |111111111111111111111111111111······························|
item-2  |······························22222222222222222222222222222·|
item-3  |······························33333333333333333333333333333·|
         0 ms                                                  413 ms

4 requests, asyncio, 2 tasks in flight, one thread: 413 ms
model: ⌈n/N⌉ × t = ⌈4/2⌉ × 200 = 2 × 200 = 400 ms
```

- With asyncio, the log gains a column for the task. Every request runs on `MainThread`, each in its own task,
  `item-0` to `item-3`. Lines from the server's threads show `None`: no task runs there.
- Tasks 0 and 1 send their requests within a millisecond, on the same thread. Both wait at the same time, because an
  `await` hands the thread back to the event loop.
- A semaphore, a counter of free places, keeps at most 2 requests in flight. Tasks 2 and 3 wait at it until
  tasks 0 and 1 finish.
- The timeline has one row per task. The model is the same as for threads, ⌈n / N⌉ × t, but with one thread.

## The timeline

Under the log, each run draws a timeline: one row per thread that sent requests, with time running left to
right. Each mark is the item that thread was waiting on, and `·` means the thread was free.

- One at a time, `MainThread` has one row, and the items follow each other: `000…111…222`.
- With 2 threads, two rows run side by side. Items 0 and 1 share the same columns, so they waited at the same
  time.
- Count the rounds: with ⌈n / N⌉ = 2, each row holds two items.

## Computing, from several threads: the GIL

`pdsau compute` runs a CPU-bound job: each item is a loop of plain Python arithmetic, about 100 ms, with no
waiting. Here 4 items run on 4 threads.

```console
$ uv run pdsau compute --way threads --n 4 --workers 4
   25.8ms  worker_0    item 0: computing
   32.2ms  worker_2    item 2: computing
   25.9ms  worker_1    item 1: computing
   51.1ms  worker_3    item 3: computing
   69.8ms  MainThread  threads running: MainThread, worker_0, worker_1, worker_2, worker_3
  304.4ms  worker_0    item 0: done after 279 ms, using 97 ms of this thread's CPU
  401.3ms  worker_3    item 3: done after 350 ms, using 96 ms of this thread's CPU
  410.6ms  worker_1    item 1: done after 385 ms, using 97 ms of this thread's CPU
  412.7ms  worker_2    item 2: done after 380 ms, using 96 ms of this thread's CPU

worker_0  |0000000000000000000000000000000000000000000·················|
worker_1  |11111111111111111111111111111111111111111111111111111111111·|
worker_2  |·2222222222222222222222222222222222222222222222222222222222·|
worker_3  |···3333333333333333333333333333333333333333333333333333333··|
           0 ms                                                  387 ms

4 items, 4 threads: 387 ms
c, one item's own CPU time, on average: 97 ms
model: n × c = 4 × 97 = 387 ms. Only the thread that holds the GIL computes, so threads take turns.
```

For comparison, one at a time:

```console
$ uv run pdsau compute --n 4 2>/dev/null | tail -3
4 items, one at a time: 400 ms
c, one item's own CPU time, on average: 100 ms
model: n × c = 4 × 100 = 398 ms
```

- Each item uses about 97 ms of its thread's CPU, but takes 280 to 385 ms on the clock. It spends most of that
  time waiting for its turn.
- Only the thread that holds the GIL runs Python code. A computing thread never blocks, so the interpreter makes
  it hand the GIL over every 5 ms (`sys.getswitchinterval()`), and the 4 threads take turns.
- The timeline shows four busy rows, but they take turns rather than compute at once.
- So the total is about n × c, the same as one at a time. Threads overlap waiting, not Python computing.

## Computing, from several processes

`--way processes` runs the same CPU-bound items in a pool of N worker processes. Each worker is a new Python
interpreter, with its own memory and its own GIL.

```console
$ uv run pdsau compute --way processes --n 8 --workers 4
   49.6ms  MainProcess     MainThread  each item goes to a worker as 137 pickled bytes: the task by reference, and the item
   56.9ms  MainProcess     MainThread  pool made, with no processes yet; it starts one when an item arrives and no worker is free, up to 4
  154.0ms  SpawnProcess-1  MainThread  item 0: computing
  154.7ms  SpawnProcess-2  MainThread  item 1: computing
  154.7ms  SpawnProcess-3  MainThread  item 2: computing
  157.4ms  SpawnProcess-4  MainThread  item 3: computing
  282.4ms  SpawnProcess-1  MainThread  item 0: done after 128 ms, using 121 ms of this thread's CPU
  282.6ms  SpawnProcess-1  MainThread  item 4: computing
  283.9ms  SpawnProcess-2  MainThread  item 1: done after 129 ms, using 123 ms of this thread's CPU
  284.3ms  SpawnProcess-2  MainThread  item 5: computing
  285.4ms  SpawnProcess-3  MainThread  item 2: done after 131 ms, using 122 ms of this thread's CPU
  285.7ms  SpawnProcess-3  MainThread  item 6: computing
  287.6ms  SpawnProcess-4  MainThread  item 3: done after 130 ms, using 123 ms of this thread's CPU
  287.8ms  SpawnProcess-4  MainThread  item 7: computing
  394.4ms  SpawnProcess-2  MainThread  item 5: done after 110 ms, using 108 ms of this thread's CPU
  397.2ms  SpawnProcess-1  MainThread  item 4: done after 115 ms, using 113 ms of this thread's CPU
  397.9ms  SpawnProcess-3  MainThread  item 6: done after 112 ms, using 111 ms of this thread's CPU
  402.1ms  SpawnProcess-4  MainThread  item 7: done after 114 ms, using 112 ms of this thread's CPU

SpawnProcess-1  |················000000000000000000000444444444444444444·····|
SpawnProcess-2  |················111111111111111111111555555555555555555·····|
SpawnProcess-3  |················222222222222222222222666666666666666666·····|
SpawnProcess-4  |·················333333333333333333333777777777777777777····|
                 0 ms                                                  373 ms

8 items, 4 processes: 373 ms
c, one item's own CPU time, on average: 117 ms
S, the time before the first item began: 104 ms, to start the worker processes
after the last item: 21 ms, for the worker processes to exit
model: S + ⌈n/N⌉ × c = 104 + ⌈8/4⌉ × 117 = 338 ms. Each process has its own GIL, so up to N items compute at once. This Mac has 8 cores.
```

- With processes, the log gains a column for the process. Every item runs on `MainThread`, but in a different
  worker process: `SpawnProcess-1` to `SpawnProcess-4`.
- Each item uses about as much CPU as it takes on the clock. It never waits for a GIL, because its process has
  its own. Compare the threads run above, where items stretched to nearly 4 times their CPU time.
- The cost is S, the start-up: on macOS each worker is a fresh interpreter (`spawn`) that imports this package.
  The pool starts the workers as items arrive.
- The pool also sends each item as bytes. It pickles the task and the item number: 137 bytes here. A function
  pickles by reference, as its module and name, and the worker imports it.
- At the end, the pool waits for its worker processes to exit. The model leaves that time out.

## A race: threads share one counter

`pdsau race` starts 4 threads that each add 1 to one shared counter, a million times. Adding 1 is three steps:
read the value, add 1, write it back. `--step read-call-write` calls a small function between the read and the
write.

```console
$ uv run pdsau race --step read-call-write
   37.9ms  adder_0     adding 1, 1000000 times, to the counter object at 0x101b0d7f0
   38.1ms  adder_1     adding 1, 1000000 times, to the counter object at 0x101b0d7f0
   38.2ms  adder_2     adding 1, 1000000 times, to the counter object at 0x101b0d7f0
   49.6ms  adder_3     adding 1, 1000000 times, to the counter object at 0x101b0d7f0
  128.5ms  adder_0     done after 91 ms
  173.7ms  adder_2     done after 136 ms
  189.8ms  adder_1     done after 152 ms
  197.7ms  adder_3     done after 148 ms

expected: 4 threads × 1000000 = 4000000
counter:  3035440, so 964560 updates lost (24%)
```

The same race with `counter.value += 1`, and then with fewer additions:

```console
$ uv run pdsau race 2>/dev/null
expected: 4 threads × 1000000 = 4000000
counter:  4000000, so 0 updates lost (0%)

$ uv run pdsau race --step read-call-write --times 100000 2>/dev/null
expected: 4 threads × 100000 = 400000
counter:  400000, so 0 updates lost (0%)
```

- Every thread logs the same address: there is one counter object, in memory that all the threads share.
- An update is lost when another thread runs between one thread's read and its write. The first thread then
  writes back an out-of-date value.
- With the GIL, CPython lets another thread run only at certain points in the bytecode, such as the start of a
  function call. The call puts such a point between the read and the write, so updates go missing.
- `counter.value += 1` has no such point inside it, so on CPython 3.14 it lost nothing. That is luck of the
  interpreter, not a promise.
- With 100,000 additions, each thread finishes within about 5 ms, before it is ever asked to hand the GIL over.
  The threads never interleave, so nothing is lost even with the call.

## The fix: one shared lock

`--lock` holds one lock, shared by every thread, around the read, the call and the write together.

```console
$ uv run pdsau race --step read-call-write --lock
   31.1ms  adder_0     adding 1, 1000000 times, to the counter object at 0x103a9d940, holding the lock at 0x103afca50
   31.2ms  adder_1     adding 1, 1000000 times, to the counter object at 0x103a9d940, holding the lock at 0x103afca50
   37.4ms  adder_2     adding 1, 1000000 times, to the counter object at 0x103a9d940, holding the lock at 0x103afca50
   48.8ms  adder_3     adding 1, 1000000 times, to the counter object at 0x103a9d940, holding the lock at 0x103afca50
  311.4ms  adder_0     done after 280 ms
  393.8ms  adder_1     done after 363 ms
  411.6ms  adder_2     done after 374 ms
  420.2ms  adder_3     done after 371 ms

expected: 4 threads × 1000000 = 4000000
counter:  4000000, so 0 updates lost (0%)
took:     389 ms

$ uv run pdsau race --step read-call-write 2>/dev/null
expected: 4 threads × 1000000 = 4000000
counter:  2905257, so 1094743 updates lost (27%)
took:     159 ms
```

- Every thread logs the same lock address: there is one lock, and all the threads share it.
- A thread that reaches `with lock:` while another holds the lock waits there. So no thread can run between
  another thread's read and its write, and nothing is lost.
- The lock costs time: every one of the 4 million additions now takes and releases it.
- The lock must cover the whole read, call and write. A lock around only the write still loses updates, and so
  does one lock per thread.

## Layout

```
src/python_data_structures_and_utilities/
  cli.py        the pdsau command: waits, compute and race
  language/     how Python runs your code
    concurrency/
      server.py   the slow local server
      waits.py    one request to the server
      async_waits.py  requests as asyncio tasks, on one thread
      compute.py  one CPU-bound item: plain Python arithmetic
      race.py     threads adding 1 to one shared counter, with or without a lock
      ways.py     run n items one at a time, or from a pool of threads or processes
      timeline.py one row per thread, for the timeline
tests/          one behavior test per concept
```

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

## The timeline

Under the log, each run draws a timeline: one row per thread that sent requests, with time running left to
right. Each mark is the item that thread was waiting on, and `·` means the thread was free.

- One at a time, `MainThread` has one row, and the items follow each other: `000…111…222`.
- With 2 threads, two rows run side by side. Items 0 and 1 share the same columns, so they waited at the same
  time.
- Count the rounds: with ⌈n / N⌉ = 2, each row holds two items.

## Layout

```
src/python_data_structures_and_utilities/
  cli.py        the pdsau command; each concept adds a subcommand
  language/     how Python runs your code
    concurrency/
      server.py   the slow local server
      waits.py    one request to the server
      ways.py     run n items one at a time, or from a pool of threads
      timeline.py one row per thread, for the timeline
tests/          one behavior test per concept
```

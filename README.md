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
   50.0ms  MainThread  slow server on port 59716; every answer waits 200 ms
   50.2ms  MainThread  threads running: MainThread, server
   50.3ms  MainThread  item 0: request sent, waiting for the answer
   75.5ms  server      connection accepted; starting a new thread to handle it
   75.8ms  handler-0   received /item/0; sleeping 200 ms
  278.7ms  handler-0   answering /item/0
  280.2ms  MainThread  item 0: answered after 230 ms, using 8.9 ms of this thread's CPU
  280.2ms  MainThread  item 1: request sent, waiting for the answer
  280.8ms  server      connection accepted; starting a new thread to handle it
  281.2ms  handler-1   received /item/1; sleeping 200 ms
  485.8ms  handler-1   answering /item/1
  486.7ms  MainThread  item 1: answered after 206 ms, using 0.9 ms of this thread's CPU
  486.9ms  MainThread  item 2: request sent, waiting for the answer
  487.8ms  server      connection accepted; starting a new thread to handle it
  488.5ms  handler-2   received /item/2; sleeping 200 ms
  691.2ms  handler-2   answering /item/2
  691.8ms  MainThread  item 2: answered after 205 ms, using 1.0 ms of this thread's CPU

3 requests, one at a time: 642 ms
model: n × t = 3 × 200 = 600 ms
```

Each line starts with the ms since the program started, then the thread that wrote it.

- Three kinds of thread take part. `MainThread` sends the requests. `server` accepts each connection and starts
  a new thread for it. `handler-N` sleeps 200 ms, then answers.
- `MainThread` sends item 1 only after item 0's answer arrives. While it waits, it is blocked and does nothing
  else.
- Over each 200 ms wait, `MainThread` uses about 1 ms of CPU; the first request costs about 9 ms. The program is
  waiting, not computing: the job is I/O-bound.
- So the total is about n × t. The few ms over 200 per request is the connection and HTTP work.

Try `--n` and `--wait-ms` to change n and t.

## Layout

```
src/python_data_structures_and_utilities/
  cli.py        the pdsau command; each concept adds a subcommand
  language/     how Python runs your code
    concurrency/
      server.py   the slow local server
      waits.py    requests, one at a time
tests/          one behavior test per concept
```

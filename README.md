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

`pdsau waits` starts a slow web server on this machine. Each answer takes 200 ms. Then it sends 8 requests, one
after another.

```console
$ uv run pdsau waits
   19.3ms  MainThread  slow server on port 58653; every answer waits 200 ms
   19.4ms  MainThread  item 0: request sent, waiting for the answer
  234.8ms  MainThread  item 0: answered after 215 ms
  234.9ms  MainThread  item 1: request sent, waiting for the answer
  441.6ms  MainThread  item 1: answered after 207 ms
  ...
 1473.7ms  MainThread  item 7: request sent, waiting for the answer
 1681.4ms  MainThread  item 7: answered after 208 ms

8 requests, one at a time: 1662 ms
model: n × t = 8 × 200 = 1600 ms
```

- Every line says `MainThread`: one thread does all the work.
- Each request goes out only after the previous answer arrives. While it waits, the thread is blocked and does
  nothing else.
- So the total is about n × t. The few ms over 200 per request is the socket and HTTP work.

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

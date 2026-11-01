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

## Layout

```
src/python_data_structures_and_utilities/
  cli.py        the pdsau command; each concept adds a subcommand
  language/     how Python runs your code: threads, processes, asyncio
tests/          one behavior test per concept
```

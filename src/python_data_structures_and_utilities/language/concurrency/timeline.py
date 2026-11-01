"""A text timeline: one row per worker, time running left to right. Each mark is the digit of the item that
worker was waiting on, and `·` means the worker was idle.

    worker_0  |000000000000111111111111······|
    worker_1  |·222222222222333333333333·····|

Marks stacked in one column mean those waits overlapped.
"""

from python_data_structures_and_utilities.language.concurrency.waits import Run


def render(run: Run, width: int = 60) -> str:
    total = (run.ended - run.started) or 1e-9
    column = lambda moment: min(width, int((moment - run.started) / total * width))
    rows: dict[str, list[str]] = {}
    for span in run.spans:  # sorted by start, so rows appear in the order their workers began
        row = rows.setdefault(span.worker, ["·"] * width)
        first = min(width - 1, column(span.start))
        for c in range(first, max(first + 1, column(span.end))):  # end is exclusive, so back-to-back waits don't touch
            row[c] = str(span.item % 10)
    label = max(len(w) for w in rows)
    lines = [f"{worker:<{label}}  |{''.join(row)}|" for worker, row in rows.items()]
    axis = f"{'':<{label}}   0 ms{f'{run.wall_ms:.0f} ms':>{width - 4}}"
    return "\n".join([*lines, axis])

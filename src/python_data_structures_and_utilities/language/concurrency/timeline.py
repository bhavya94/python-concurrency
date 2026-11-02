"""A text timeline of a run: one row per thread that ran items, time running left to right.

Each mark is the last digit of the item that thread was working on, and `·` means it was free. Marks in the same
column on different rows happened at the same time.

    worker_0  |0000000000000000000000000000002222222222222222222222222222·|
    worker_1  |1111111111111111111111111111113333333333333333333333333333·|
               0 ms                                                 423 ms
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    """One item: which thread ran it, and when it started and ended, in seconds on the wall clock."""

    item: int
    thread: str
    start: float
    end: float


@dataclass(frozen=True)
class Run:
    spans: list[Span]
    start: float
    end: float

    @property
    def ms(self) -> float:
        return (self.end - self.start) * 1000


def render(run: Run, width: int = 60) -> str:
    total = (run.end - run.start) or 1e-9
    column = lambda moment: min(width, int((moment - run.start) / total * width))
    rows: dict[str, list[str]] = {}
    for span in sorted(run.spans, key=lambda s: s.start):  # rows appear in the order their threads began
        row = rows.setdefault(span.thread, ["·"] * width)
        first = min(width - 1, column(span.start))
        for c in range(first, max(first + 1, column(span.end))):  # the end is exclusive: back-to-back items don't touch
            row[c] = str(span.item % 10)
    label = max(len(name) for name in rows)
    lines = [f"{name:<{label}}  |{''.join(row)}|" for name, row in rows.items()]
    lines.append(f"{'':<{label}}   0 ms{f'{run.ms:.0f} ms':>{width - 4}}")
    return "\n".join(lines)

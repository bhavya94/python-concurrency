from python_data_structures_and_utilities.language.concurrency.timeline import Run, Span, render


def test_each_item_sits_under_its_thread_at_its_time():
    spans = [Span(0, "worker_0", 0.0, 0.5), Span(1, "worker_1", 0.0, 0.5), Span(2, "worker_0", 0.5, 1.0)]
    rows = render(Run(spans, start=0.0, end=1.0), width=10).splitlines()
    assert rows[0] == "worker_0  |0000022222|"  # items 0 then 2, back to back, on one thread
    assert rows[1] == "worker_1  |11111·····|"  # item 1 at the same time as item 0, then free

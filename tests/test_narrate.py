import asyncio
import logging

from python_data_structures_and_utilities import narrate

log = logging.getLogger("python_data_structures_and_utilities.language.probe")


def test_each_line_says_which_thread_and_task_wrote_it(capsys):
    narrate.setup()
    log.info("outside")

    async def inside():
        log.info("inside")

    async def main():
        await asyncio.create_task(inside(), name="probe")

    asyncio.run(main())
    outside, inside_line = capsys.readouterr().err.splitlines()
    assert "thread=MainThread" in outside and "task=-" in outside and "probe: outside" in outside
    assert "task=probe" in inside_line


def test_a_worker_given_the_parents_start_time_counts_from_it(capsys):
    import time
    narrate.setup(t0=time.time() - 5)
    log.info("late")
    elapsed = float(capsys.readouterr().err.split("ms")[0])
    assert 5000 <= elapsed < 6000

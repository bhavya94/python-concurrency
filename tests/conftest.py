import logging

import pytest


@pytest.fixture(autouse=True)
def restore_logging():
    """narrate.setup() replaces the package logger's handler. Put it back, so a handler bound to one test's captured
    stderr never outlives that test."""
    logger = logging.getLogger("python_data_structures_and_utilities")
    saved = logger.handlers[:], logger.level, logger.propagate
    yield
    logger.handlers[:], logger.level, logger.propagate = saved[0], saved[1], saved[2]

import re
import subprocess
import sys
from pathlib import Path

PDSAU = Path(sys.executable).parent / "pdsau"  # the script uv installs from [project.scripts]


def test_the_installed_command_runs_and_explains_itself():
    result = subprocess.run([PDSAU, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.startswith("usage: pdsau")


def test_an_unknown_option_is_an_error():
    result = subprocess.run([PDSAU, "--bogus"], capture_output=True, text=True)
    assert result.returncode == 2
    assert "unrecognized arguments: --bogus" in result.stderr


def test_a_count_below_one_is_an_error():
    result = subprocess.run([PDSAU, "waits", "--n", "0"], capture_output=True, text=True)
    assert result.returncode == 2
    assert "must be 1 or more, not 0" in result.stderr


def test_threads_way_overlaps_and_its_model_rounds_up():
    result = subprocess.run([PDSAU, "waits", "--way", "threads", "--n", "3", "--workers", "2", "--wait-ms", "100"],
                            capture_output=True, text=True)
    assert "⌈3/2⌉ × 100 = 2 × 100 = 200 ms" in result.stdout  # 3 requests on 2 threads need 2 rounds, not 1.5
    measured = int(re.search(r"2 threads: (\d+) ms", result.stdout).group(1))
    assert measured < 300  # one at a time would take at least n × t = 300 ms


def test_compute_runs_its_items_on_the_threads_asked_for():
    result = subprocess.run([PDSAU, "compute", "--way", "threads", "--n", "2", "--workers", "2", "--size", "1250000"],
                            capture_output=True, text=True)
    rows = [line.split()[0] for line in result.stdout.splitlines() if "|" in line]
    assert sorted(rows) == ["worker_0", "worker_1"]
    measured = int(re.search(r"2 threads: (\d+) ms", result.stdout).group(1))
    model = int(re.search(r"model: n × c = 2 × \d+ = (\d+) ms", result.stdout).group(1))
    if sys._is_gil_enabled():
        assert measured / model > 0.7  # with the GIL, threads take turns: the run lasts at least about n × c

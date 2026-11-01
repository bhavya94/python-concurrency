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

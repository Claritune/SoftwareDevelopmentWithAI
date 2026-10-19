"""The headless runner must reproduce the C++ binary's output byte for byte."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
GOLDEN = Path("tests/golden")

# Paths relative to ROOT, because error messages include the script path as given.
CASES = {
    "demo": "scripts/demo.txt",
    "missing_file": (GOLDEN / "scripts" / "does_not_exist.txt").as_posix(),
    **{
        p.stem: (GOLDEN / "scripts" / p.name).as_posix()
        for p in (ROOT / GOLDEN / "scripts").glob("*.txt")
    },
}


def run(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "cats_vs_mutants", *args], cwd=ROOT, capture_output=True
    )


@pytest.mark.parametrize("name", sorted(CASES))
def test_headless_output_matches_cpp_reference(name):
    result = run("--headless", CASES[name])

    assert result.stdout == (ROOT / GOLDEN / f"{name}.stdout").read_bytes()
    assert result.stderr == (ROOT / GOLDEN / f"{name}.stderr").read_bytes()
    assert result.returncode == int((ROOT / GOLDEN / f"{name}.exitcode").read_text())


def test_headless_without_script_prints_usage():
    result = run("--headless")
    assert result.returncode == 2
    assert result.stderr == b"usage: cats-vs-mutants --headless <script.txt>\n"


def test_unknown_argument_prints_usage():
    result = run("--bogus")
    assert result.returncode == 2
    assert result.stderr == b"usage: cats-vs-mutants [--headless <script.txt>]\n"

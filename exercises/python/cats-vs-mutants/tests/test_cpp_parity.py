"""Random scripts must give the same output as the C++ build.

Skipped when the C++ binary is not available. Point CVM_CPP_BIN at it to override the default.
"""

import io
import os
import random
import subprocess
from pathlib import Path

import pytest

from cats_vs_mutants.ui.headless import run_headless

CPP_BIN = Path(os.environ.get("CVM_CPP_BIN", "/Users/bigromanov/Code/ai/corecpp/cvm/build/cats"))

pytestmark = pytest.mark.skipif(not CPP_BIN.exists(), reason=f"C++ binary not found: {CPP_BIN}")

CATS = ["rich", "hissing", "sleepy", "laser"]


def random_script(rng: random.Random) -> str:
    """Busy play with frequent prints, plus some out-of-bounds and duplicate placements."""
    lines = []
    for _ in range(rng.randint(40, 120)):
        roll = rng.random()
        if roll < 0.45:
            lines.append(f"place {rng.choice(CATS)} {rng.randint(-1, 5)} {rng.randint(-1, 9)}")
        elif roll < 0.55:
            lines.append(f"remove {rng.randint(0, 4)} {rng.randint(0, 8)}")
        elif roll < 0.85:
            lines.append(f"tick {rng.randint(1, 40)}")
        else:
            lines.append("print")
    lines.append(f"tick {rng.randint(0, 600)}")
    return "\n".join(lines) + "\n"


def demo_with_snapshots(rng: random.Random) -> str:
    """The winning demo, with each tick command split at random points and printed there."""
    demo = Path(__file__).parent.parent / "scripts" / "demo.txt"
    lines = []
    for line in demo.read_text().splitlines():
        words = line.split("#")[0].split()
        if words[:1] != ["tick"]:
            lines.append(line)
            continue
        remaining = int(words[1])
        while remaining > 0:
            step = min(remaining, rng.randint(1, 25))
            lines += [f"tick {step}", "print"]
            remaining -= step
    return "\n".join(lines) + "\n"


def assert_matches_cpp(script: Path) -> None:
    expected = subprocess.run([CPP_BIN, "--headless", script], capture_output=True, text=True)
    out, err = io.StringIO(), io.StringIO()
    code = run_headless(str(script), out, err)

    assert (code, err.getvalue()) == (expected.returncode, expected.stderr)
    assert out.getvalue() == expected.stdout


@pytest.mark.parametrize("seed", range(40))
def test_random_script_matches_cpp(seed, tmp_path):
    script = tmp_path / "script.txt"
    script.write_text(random_script(random.Random(seed)))
    assert_matches_cpp(script)


@pytest.mark.parametrize("seed", range(5))
def test_demo_with_snapshots_matches_cpp(seed, tmp_path):
    script = tmp_path / "script.txt"
    script.write_text(demo_with_snapshots(random.Random(seed)))
    assert_matches_cpp(script)

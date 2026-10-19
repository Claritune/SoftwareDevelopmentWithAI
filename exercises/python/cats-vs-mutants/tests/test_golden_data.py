"""Sanity checks on the reference output captured from the C++ build."""

from pathlib import Path

GOLDEN = Path(__file__).parent / "golden"


def test_demo_reference_ends_won_at_tick_1648_with_3_lives():
    lines = (GOLDEN / "demo.stdout").read_text().splitlines()
    final = lines[lines.index("=== FINAL STATE ===") + 1]
    assert final == "TREATS: 0   WAVE 3/3   LIVES: 3   TICK: 1648   STATUS: Won"
    assert (GOLDEN / "demo.exitcode").read_text().strip() == "0"


def test_every_edge_case_script_has_reference_output():
    for script in (GOLDEN / "scripts").glob("*.txt"):
        for suffix in ("stdout", "stderr", "exitcode"):
            assert (GOLDEN / f"{script.stem}.{suffix}").exists(), script.name

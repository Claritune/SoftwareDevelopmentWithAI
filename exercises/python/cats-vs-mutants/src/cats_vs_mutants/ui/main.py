"""Command line entry point."""

import sys

PROG = "cats-vs-mutants"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--headless":
        if len(args) < 2:
            print(f"usage: {PROG} --headless <script.txt>", file=sys.stderr)
            return 2
        from cats_vs_mutants.ui.headless import run_headless

        return run_headless(args[1])
    if args:
        print(f"usage: {PROG} [--headless <script.txt>]", file=sys.stderr)
        return 2
    from cats_vs_mutants.ui.interactive import run_interactive

    return run_interactive()

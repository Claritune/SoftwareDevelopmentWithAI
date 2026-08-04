"""Entry point for url-monitor CLI."""

from __future__ import annotations

import sys

from url_monitor.config import derive_state_path, load_config, parse_args
from url_monitor.monitor import MonitorContext, run_monitor
from url_monitor.state import load_state, reconcile, save_state
from url_monitor.stats import format_stats


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    opts = parse_args(argv)

    # Load and validate config
    config = load_config(opts.config_path)

    # Resolve state file path
    state_path = opts.state_file or derive_state_path(opts.config_path)

    if opts.stats_only:
        store = load_state(state_path)
        reconcile(store, config)
        if not store.urls:
            print("No stats available.")
            sys.exit(0)
        for url, url_state in store.urls.items():
            print(format_stats(url, url_state.stats))
            print()
        sys.exit(0)

    # Load state and reconcile against config
    store = load_state(state_path)
    reconcile(store, config)

    # Build context and run monitor
    ctx = MonitorContext(
        config=config,
        state=store,
        state_path=state_path,
        verbose=opts.verbose,
    )

    exit_code = run_monitor(ctx)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

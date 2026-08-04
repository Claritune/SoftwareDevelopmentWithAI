"""JSON sidecar state persistence with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field

from url_monitor.checker import Status, status_name
from url_monitor.config import Config
from url_monitor.notifier import log_error
from url_monitor.stats import UrlStats


@dataclass
class UrlState:
    status: Status = Status.Unknown
    last_checked: str = ""
    stats: UrlStats = field(default_factory=UrlStats)


@dataclass
class StateStore:
    version: int = 1
    urls: dict[str, UrlState] = field(default_factory=dict)


def _stats_to_dict(stats: UrlStats) -> dict:
    """Serialize UrlStats to a JSON-compatible dict."""
    return {
        "total_checks": stats.total_checks,
        "up_checks": stats.up_checks,
        "down_checks": stats.down_checks,
        "http_status": {str(k): v for k, v in stats.http_status.items()},
        "errors": dict(stats.errors),
    }


def _stats_from_dict(data: dict) -> UrlStats:
    """Deserialize UrlStats from a dict."""
    return UrlStats(
        total_checks=data.get("total_checks", 0),
        up_checks=data.get("up_checks", 0),
        down_checks=data.get("down_checks", 0),
        http_status={int(k): v for k, v in data.get("http_status", {}).items()},
        errors=dict(data.get("errors", {})),
    )


def _status_from_str(s: str) -> Status:
    """Parse status string to Status enum."""
    mapping = {"up": Status.Up, "down": Status.Down, "unknown": Status.Unknown}
    return mapping.get(s, Status.Unknown)


def load_state(path: str) -> StateStore:
    """Load state from a JSON sidecar file.

    Missing file returns empty store. Corrupt file logs a warning and returns empty.
    """
    if not os.path.exists(path):
        return StateStore()

    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        log_error(f"corrupt state file, starting fresh: {exc}")
        return StateStore()

    store = StateStore(version=data.get("version", 1))

    urls_data = data.get("urls", {})
    for url, entry in urls_data.items():
        status = _status_from_str(entry.get("status", "unknown"))
        last_checked = entry.get("last_checked", "")

        # Legacy compatibility: state entry without "stats" key loads with zeroed stats
        stats_data = entry.get("stats", {})
        stats = _stats_from_dict(stats_data) if stats_data else UrlStats()

        store.urls[url] = UrlState(
            status=status,
            last_checked=last_checked,
            stats=stats,
        )

    return store


def save_state(path: str, store: StateStore) -> None:
    """Save state to a JSON sidecar file (atomic via temp+rename)."""
    data = {
        "version": store.version,
        "urls": {},
    }
    for url, state in store.urls.items():
        data["urls"][url] = {
            "status": status_name(state.status),
            "last_checked": state.last_checked,
            "stats": _stats_to_dict(state.stats),
        }

    try:
        dir_name = os.path.dirname(path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            os.replace(tmp_path, path)
        except Exception:
            # Try to clean up the temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception:
        pass


def reconcile(store: StateStore, config: Config) -> None:
    """Reconcile state against current config.

    Add new URLs as Unknown, drop removed ones.
    """
    config_urls = {spec.url for spec in config.urls}

    # Add new URLs
    for url in config_urls:
        if url not in store.urls:
            store.urls[url] = UrlState()

    # Drop removed URLs
    removed = [url for url in store.urls if url not in config_urls]
    for url in removed:
        del store.urls[url]

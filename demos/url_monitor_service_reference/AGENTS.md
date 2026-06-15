*IMPORTANT* In case the goal of the task is not completely clear or can be interpreted as ambiguous ask me what exactly needs to be done

## Module agents

The service is split into five logical modules. Each has a Cursor rule in `.cursor/rules/` that scopes ownership by file globs and documents an **@ tag** for explicit handoff.

| Tag | Responsibility |
|-----|----------------|
| `@platform` | Bootstrap, settings, DB, errors, health |
| `@monitor-api` | Monitor CRUD & validation |
| `@check-engine` | HTTP probe & UP/DOWN state machine |
| `@coordinator` | Background scheduler |
| `@observability` | History & status summary |

See `.cursor/rules/modules-overview.mdc` and `ARCHITECTURE.md` for boundaries, shared files, and test ownership.

## Hooks

### `stop` — no default function arguments (semgrep)

After each completed agent turn, `.cursor/hooks/no-default-args.sh` runs [semgrep](https://semgrep.dev/) against `app/` and `tests/` using `.cursor/semgrep/no-default-args.yaml`.

- **Pass:** hook returns `{}` and the conversation ends normally.
- **Fail:** hook returns a `followup_message` listing violations; Cursor auto-submits it so the agent can fix them (up to 5 loops via `loop_limit`).
- **Requires:** `semgrep` on `PATH`, or `uv run semgrep` if semgrep is listed in project dev dependencies. Also requires `jq`.

**Project rule:** function parameters must not have default values (including typed defaults like `status: int = 400` and FastAPI `Depends(...)` defaults).

*IMPORTANT* In case the goal of the task is not completely clear or can be interpreted as ambiguous ask me what exactly needs to be done

## Hooks

### `stop` — no default function arguments (semgrep)

After each completed agent turn, `.cursor/hooks/no-default-args.sh` runs [semgrep](https://semgrep.dev/) against `app/` and `tests/` using `.cursor/semgrep/no-default-args.yaml`.

- **Pass:** hook returns `{}` and the conversation ends normally.
- **Fail:** hook returns a `followup_message` listing violations; Cursor auto-submits it so the agent can fix them (up to 5 loops via `loop_limit`).
- **Requires:** `semgrep` on `PATH`, or `uv run semgrep` if semgrep is listed in project dev dependencies. Also requires `jq`.

**Project rule:** function parameters must not have default values (including typed defaults like `status: int = 400` and FastAPI `Depends(...)` defaults).

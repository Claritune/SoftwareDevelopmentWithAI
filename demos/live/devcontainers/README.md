# Demo Project

A sample project used to demonstrate AI agent sandboxing with Dev Containers.

## The Test

1. The host machine has a file at `~/.secret` with fake credentials.
2. Inside this container, that file does not exist.
3. Ask the Cursor agent to read `~/.secret` — it will fail.
4. Ask it to read this README — it will succeed.
5. Ask it to run `main.py` — it will succeed.
6. The agent can only see what's inside `/workspace`.

See [DEMO.md](DEMO.md) for the full demo flow.

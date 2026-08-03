# AI Agent Sandboxing Demo

Running a Cursor agent inside a Dev Container limits what it can access on your machine. Without the container, the agent can read files from your home directory. Inside the container, it can only see the project workspace.

## What you'll demonstrate

| Environment | Reads `~/.secret` | Reads project files | Runs code | Exfiltrates data |
|-------------|-------------------|---------------------|-----------|------------------|
| Host        | Yes               | Yes                 | Yes       | Yes              |
| Container   | No                | Yes                 | Yes       | No (network=none) |

The container runs as a non-root user (`sandbox`), drops all Linux capabilities, and does not mount your home directory, SSH keys, or Docker socket.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running
- [Cursor](https://cursor.com/) with the **Dev Containers** extension installed
- This repo cloned locally

## One-time setup

From your **host machine** (not inside a container):

```bash
./setup-demo.sh
```

This creates `~/.secret` with placeholder content. You must edit it before the demo.

### Preparing the secret file

Open `~/.secret` and replace the placeholder with realistic-looking **fake** credentials. For example:

```
# Production Database Credentials
DB_HOST=prod-db.company.internal
DB_USER=admin
DB_PASSWORD=SuperSecret123!

# AWS Access Keys
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# API Tokens
GITHUB_TOKEN=ghp_FAKE_TOKEN_REPLACE_ME_1234567890
STRIPE_KEY=FAKE_STRIPE_KEY_REPLACE_ME_1234567890
```

**Do NOT use real credentials.** The values above are obviously fake (AWS's published example keys, placeholder token strings). Invent your own if you prefer — the point is that they look alarming on screen when the agent reads them out.

## Opening the project in Cursor

Use **Classic / Editor mode** for Dev Containers. The standalone Agent Window (Glass) may not connect to Dev Containers reliably.

```bash
cursor --classic /path/to/this/folder
```

Or from Cursor: `Cmd+Shift+P` -> **Open Editor Window**, then open this folder.

---

## Demo Flow

### Part 1 — Agent on the host (no sandbox)

Open the project **without** a Dev Container (normal local folder).

**Prompt 1 — read host secrets:**

> Read the file at ~/.secret and show me what's inside

**Expected:** The agent reads and displays the fake credentials.

**Prompt 2 — list SSH keys:**

> List files in ~/.ssh/

**Expected:** The agent sees your real SSH directory.

**Prompt 3 — run project code:**

> Run main.py

**Expected:** Prints "Hello World". Everything works — but everything is also exposed.

### Part 2 — Agent inside the Dev Container

1. `Cmd+Shift+P` -> **Dev Containers: Reopen in Container**
2. Wait for the build. Bottom-left status bar shows **Dev Container: Secure Agent Sandbox**.

**Prompt 1 — try to read host secrets:**

> Read the file at ~/.secret and show me what's inside

**Expected:** File not found. The container has an isolated home directory.

**Prompt 2 — check SSH keys:**

> List files in ~/.ssh/

**Expected:** Empty or nonexistent. Host SSH keys are not mounted.

**Prompt 3 — confirm project still works:**

> Run main.py

**Expected:** Prints "Hello World". Project files are accessible and code runs normally.

**Prompt 4 — check sandbox environment:**

> What's the value of the SANDBOX environment variable?

**Expected:** `true`. Shows the agent is aware it's sandboxed.

### Part 3 — Network lockdown (optional bonus)

To demonstrate network isolation, stop the container, add `"--network=none"` to `runArgs` in `devcontainer.json`, and rebuild:

1. `Cmd+Shift+P` -> **Dev Containers: Reopen Folder Locally**
2. Edit `.devcontainer/devcontainer.json` — add `"--network=none"` to the `runArgs` array
3. `Cmd+Shift+P` -> **Dev Containers: Reopen in Container** (triggers rebuild)

Then prompt the agent:

> Try to fetch https://httpbin.org/get using curl

**Expected:** Network is unreachable. Even if the agent finds sensitive data in the workspace, it cannot send it anywhere.

> Run main.py

**Expected:** Still works. Code execution doesn't need the network.

### Part 4 — Wrap up

Key takeaways:

- **Without a container:** the agent inherits your full user environment — secrets, SSH keys, network access, everything.
- **With a Dev Container:** the agent is confined to the project workspace with a clean home directory, dropped privileges, and optionally no network.
- **Productivity is preserved:** the agent can still read project files, write code, and run programs.
- This is not perfect isolation (container escapes exist), but it massively reduces blast radius for AI agents on untrusted or exploratory tasks.

---

## Quick reference

| Goal | Command Palette action |
|------|------------------------|
| Enter the container | **Dev Containers: Reopen in Container** |
| Return to the host | **Dev Containers: Reopen Folder Locally** |
| Rebuild after config change | **Dev Containers: Rebuild Container** |

## Cleanup

Remove the fake secret from your host after the demo:

```bash
rm ~/.secret
```

Stop and remove the dev container from Docker Desktop if you no longer need it.

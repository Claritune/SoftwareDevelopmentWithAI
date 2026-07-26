# Exercise: Concurrent Bug-Fix Agents

## What this exercise teaches

You will practise launching **multiple agents in parallel**, each
assigned to fix one independent bug in the same codebase. Because the bugs live
in separate functions they can be fixed concurrently without merge conflicts.

---

## The application

`Program.cs` contains a small **Task Manager REST API** built with ASP.NET Minimal API.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/tasks` | Create a new task |
| `GET` | `/tasks` | List all tasks (supports `?completed=` and `?priority=` filters) |
| `GET` | `/tasks/{id}` | Get a single task |
| `PATCH` | `/tasks/{id}` | Update a task |
| `DELETE` | `/tasks/{id}` | Delete a task |
| `GET` | `/tasks/summary/stats` | Aggregated statistics |

### Task fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | Auto-assigned, unique, incrementing |
| `title` | string | Required |
| `description` | string? | Optional |
| `priority` | int | `1` = low, `2` = medium, `3` = high |
| `completed` | bool | Defaults to `false` |
| `createdAt` | ISO-8601 string | Set on creation |

### List ordering

`GET /tasks` always returns tasks sorted **newest first** (highest `id` first).

---

## Known bugs

There are **5 bugs** in `Program.cs`. Each is described in its own file inside
the `issues/` directory:

| File | Affected endpoint | Short description |
|------|-------------------|-------------------|
| `issues/issue_1.md` | `POST /tasks` | Task IDs are never incremented |
| `issues/issue_2.md` | `GET /tasks` | Priority filter returns wrong tasks |
| `issues/issue_3.md` | `GET /tasks` | List is sorted oldest-first |
| `issues/issue_4.md` | `PATCH /tasks/{id}` | Priority 3 is incorrectly rejected |
| `issues/issue_5.md` | `DELETE /tasks/{id}` | Tasks are not actually deleted |

---

## Running the server

```bash
cd TaskManagerApi
dotnet run
```

The API will be available at `http://localhost:5000`. OpenAPI spec is at `http://localhost:5000/openapi/v1.json`.

---

## Running the tests

```bash
cd TaskManagerApi.Tests
dotnet test -v normal
```

> **Note:** The projects target `net10.0`. If you're using a different .NET SDK version,
> update the `<TargetFramework>` in both `.csproj` files and the `Microsoft.AspNetCore.Mvc.Testing`
> package version to match your SDK.

All tests should pass once all bugs are fixed. Before any fixes, every test
group will fail.

---

## Exercise instructions

### 1. Verify the bugs are present

```bash
cd TaskManagerApi.Tests
dotnet test -v normal
```

You should see failures across all five test groups.

### 2. Launch five agents in parallel

Open five terminal tabs (or use Claude Code's parallel-agent feature) and give
each agent the contents of one issue file as its prompt. For example:

```
# Terminal 1
claude "Read issues/issue_1.md and fix the bug described in it in TaskManagerApi/Program.cs"

# Terminal 2
claude "Read issues/issue_2.md and fix the bug described in it in TaskManagerApi/Program.cs"

# Terminal 3
claude "Read issues/issue_3.md and fix the bug described in it in TaskManagerApi/Program.cs"

# Terminal 4
claude "Read issues/issue_4.md and fix the bug described in it in TaskManagerApi/Program.cs"

# Terminal 5
claude "Read issues/issue_5.md and fix the bug described in it in TaskManagerApi/Program.cs"
```

Because each bug is in a **different endpoint handler**, the agents will not conflict
with one another.

### 3. Verify all bugs are fixed

```bash
cd TaskManagerApi.Tests
dotnet test -v normal
```

All tests should now pass.

---

## Reflection questions

- Did any two agents modify the same lines? Why or why not?
- What would happen if two agents tried to fix bugs in the same function at the
  same time?
- How would you coordinate agents on bugs that *do* overlap?

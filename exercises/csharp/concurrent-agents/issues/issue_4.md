# Issue 4: Updating a task's priority to "high" (3) is incorrectly rejected

## Symptoms

`PATCH /tasks/{id}` returns `422 Unprocessable Entity` when the client tries to
set `priority` to `3` (high), even though `3` is a documented valid value.

```bash
curl -s -X POST http://localhost:5000/tasks -H "Content-Type: application/json" \
  -d '{"title": "Urgent bug"}'
# → {"id": 1, ...}

curl -s -X PATCH http://localhost:5000/tasks/1 -H "Content-Type: application/json" \
  -d '{"priority": 3}'
# → {"detail": "Priority must be 1, 2, or 3"}   ← 422 error, but 3 is valid!
```

## Expected behaviour

Priority values `1` (low), `2` (medium), and `3` (high) are all accepted.
Any value outside that range should be rejected with a 422 error.

## Location

`TaskManagerApi/Program.cs` — the `PATCH /tasks/{id}` endpoint handler, priority validation block.

## Hint

Look carefully at the boundary condition used in the `if` check that returns the
422 error. The upper bound is off by one.

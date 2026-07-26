# Issue 3: Task list is sorted oldest-first instead of newest-first

## Symptoms

`GET /tasks` returns tasks in ascending ID order (oldest first).
The expected behaviour documented in the README is newest-first so clients
always see the most recently created tasks at the top.

```bash
curl -s -X POST http://localhost:5000/tasks -H "Content-Type: application/json" \
  -d '{"title": "First task"}'
curl -s -X POST http://localhost:5000/tasks -H "Content-Type: application/json" \
  -d '{"title": "Second task"}'
curl -s -X POST http://localhost:5000/tasks -H "Content-Type: application/json" \
  -d '{"title": "Third task"}'

curl -s http://localhost:5000/tasks
# Output order: First task, Second task, Third task
# Expected order: Third task, Second task, First task
```

## Expected behaviour

Tasks are returned sorted by `id` descending (highest ID first = most recently created first).

## Location

`TaskManagerApi/Program.cs` — the `GET /tasks` endpoint handler, the LINQ ordering call.

## Hint

Check whether the ordering is `OrderBy` or `OrderByDescending`.

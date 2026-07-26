# Issue 2: Priority filter returns the wrong tasks

## Symptoms

`GET /tasks?priority=3` returns tasks that are **not** priority 3 and excludes
tasks that **are** priority 3.

```bash
# Create one low and one high priority task
curl -s -X POST http://localhost:5000/tasks -H "Content-Type: application/json" \
  -d '{"title": "Low priority task", "priority": 1}'
curl -s -X POST http://localhost:5000/tasks -H "Content-Type: application/json" \
  -d '{"title": "High priority task", "priority": 3}'

# Filter by high priority — expect only the second task
curl -s "http://localhost:5000/tasks?priority=3"
# → {"tasks": [{"title": "Low priority task", ...}], "count": 1}
#   Returns the LOW priority task instead of the HIGH one!
```

## Expected behaviour

`GET /tasks?priority=<n>` returns only tasks whose `priority` field equals `n`.

## Location

`TaskManagerApi/Program.cs` — the `GET /tasks` endpoint handler, priority filter block.

## Hint

The comparison operator used to filter tasks is the opposite of what it should be.

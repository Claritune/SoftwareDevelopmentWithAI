# Issue 1: Task IDs are never unique

## Symptoms

Every call to `POST /tasks` returns a task with `"id": 1`.
Creating a second task silently overwrites the first one.

```bash
curl -s -X POST http://localhost:5000/tasks -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'
# → {"id": 1, ...}

curl -s -X POST http://localhost:5000/tasks -H "Content-Type: application/json" \
  -d '{"title": "Walk the dog"}'
# → {"id": 1, ...}   ← wrong, should be 2

curl -s http://localhost:5000/tasks
# → {"tasks": [{"id": 1, "title": "Walk the dog", ...}], "count": 1}
#   "Buy milk" is gone!
```

## Expected behaviour

Each task gets a unique, incrementing integer ID.
After creating two tasks the store should contain both.

## Location

`TaskManagerApi/Program.cs` — the `POST /tasks` endpoint handler.

## Hint

The variable `nextId` is assigned to `taskId` but is never updated after the task is stored.

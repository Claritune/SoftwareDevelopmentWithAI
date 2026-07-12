# Issue 5: DELETE endpoint does not actually delete tasks

## Symptoms

`DELETE /tasks/{id}` returns a 200 response with the task details, but the task
is still present in the store afterwards. Subsequent `GET /tasks/{id}` calls
still return the "deleted" task.

```bash
curl -s -X POST http://localhost:8000/tasks -H "Content-Type: application/json" \
  -d '{"title": "Temporary task"}'
# → {"id": 1, ...}

curl -s -X DELETE http://localhost:8000/tasks/1
# → {"deleted": {"id": 1, "title": "Temporary task", ...}}  ← looks fine

curl -s http://localhost:8000/tasks/1
# → {"id": 1, "title": "Temporary task", ...}   ← task still exists!

curl -s http://localhost:8000/tasks
# → {"tasks": [...], "count": 1}   ← count unchanged
```

## Expected behaviour

After a successful `DELETE /tasks/{id}`:
- `GET /tasks/{id}` returns 404.
- `GET /tasks` no longer includes that task and the count decreases by 1.

## Location

`main.py` — `delete_task` function.

## Hint

The function reads the task into a local variable and returns it, but never
removes it from the `tasks` dictionary.

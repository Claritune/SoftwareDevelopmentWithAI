# Issue 3: Task list is sorted oldest-first instead of newest-first

## Symptoms

`GET /tasks` returns tasks in ascending ID order (oldest first).
The expected behaviour documented in the README is newest-first so clients
always see the most recently created tasks at the top.

```bash
curl -s -X POST http://localhost:8000/tasks -H "Content-Type: application/json" \
  -d '{"title": "First task"}'
curl -s -X POST http://localhost:8000/tasks -H "Content-Type: application/json" \
  -d '{"title": "Second task"}'
curl -s -X POST http://localhost:8000/tasks -H "Content-Type: application/json" \
  -d '{"title": "Third task"}'

curl -s http://localhost:8000/tasks | python3 -c \
  "import sys,json; [print(t['title']) for t in json.load(sys.stdin)['tasks']]"
# Output:
#   First task
#   Second task
#   Third task
# Expected:
#   Third task
#   Second task
#   First task
```

## Expected behaviour

Tasks are returned sorted by `id` descending (highest ID first = most recently created first).

## Location

`main.py` — `list_tasks` function, `sorted(...)` call.

## Hint

Check the `reverse` argument of the `sorted` call.

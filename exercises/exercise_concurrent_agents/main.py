from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = FastAPI(title="Task Manager API")

# In-memory store
tasks: dict[int, dict] = {}
next_id = 1


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 1  # 1=low, 2=medium, 3=high


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    completed: Optional[bool] = None


# BUG #1: next_id is never incremented — every new task overwrites id=1
@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    global next_id
    task_id = next_id
    tasks[task_id] = {
        "id": task_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "completed": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    # Missing: next_id += 1
    return tasks[task_id]


@app.get("/tasks")
def list_tasks(completed: Optional[bool] = None, priority: Optional[int] = None):
    result = list(tasks.values())

    if completed is not None:
        result = [t for t in result if t["completed"] == completed]

    # BUG #2: priority filter uses OR instead of AND — it returns tasks that
    # match priority OR all tasks when priority is None (logic is inverted)
    if priority is not None:
        result = [t for t in result if t["priority"] != priority]

    # BUG #3: sort key is wrong — sorts by "id" descending but the field is
    # named "id", however the sort order is reversed from what the docstring
    # says (should be newest first = highest id, but reverse=False gives oldest first)
    result = sorted(result, key=lambda t: t["id"], reverse=False)

    return {"tasks": result, "count": len(result)}


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    if update.title is not None:
        task["title"] = update.title
    if update.description is not None:
        task["description"] = update.description
    if update.priority is not None:
        # BUG #4: priority validation is off-by-one — rejects valid value 3
        if update.priority < 1 or update.priority > 2:
            raise HTTPException(status_code=422, detail="Priority must be 1, 2, or 3")
        task["priority"] = update.priority
    if update.completed is not None:
        task["completed"] = update.completed

    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    # BUG #5: returns the deleted task dict but forgets to actually delete it
    deleted = tasks[task_id]
    return {"deleted": deleted}


@app.get("/tasks/summary/stats")
def get_stats():
    all_tasks = list(tasks.values())
    completed = [t for t in all_tasks if t["completed"]]
    pending = [t for t in all_tasks if not t["completed"]]

    priority_counts = {1: 0, 2: 0, 3: 0}
    for t in all_tasks:
        priority_counts[t["priority"]] += 1

    return {
        "total": len(all_tasks),
        "completed": len(completed),
        "pending": len(pending),
        "by_priority": {
            "low": priority_counts[1],
            "medium": priority_counts[2],
            "high": priority_counts[3],
        },
    }

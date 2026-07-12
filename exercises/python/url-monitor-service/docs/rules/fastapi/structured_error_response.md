# Rule: Error handling via exception handlers, not try/except in routes

Do not wrap route handler bodies in try/except blocks.

Instead:
1. Define domain exceptions in `app/exceptions.py`:
```python
   class AppError(Exception):
       def __init__(self, message: str, code: str, status: int = 400):
           self.message = message
           self.code = code  
           self.status = status

   class NotFoundError(AppError):
       def __init__(self, resource: str, id: str):
           super().__init__(f"{resource} {id} not found", "NOT_FOUND", 404)
```

2. Register exception handlers in `app/main.py`:
```python
   @app.exception_handler(AppError)
   async def app_error_handler(request, exc):
       return JSONResponse(status_code=exc.status, content={"error": exc.code, "message": exc.message})
```

3. Route handlers just raise — they never catch and transform:
```python
   @router.get("/items/{item_id}")
   async def get_item(item_id: str, repo: ItemRepo = Depends(get_repo)):
       item = await repo.get(item_id)
       if not item:
           raise NotFoundError("Item", item_id)
       return item
```

All error responses must follow the schema: `{"error": "<CODE>", "message": "<human readable>"}`.
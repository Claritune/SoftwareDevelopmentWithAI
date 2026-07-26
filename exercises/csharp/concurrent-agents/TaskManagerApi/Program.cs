using System.Text.Json;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    options.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
});
builder.Services.AddOpenApi();

var app = builder.Build();
app.MapOpenApi();

// In-memory store
var tasks = new Dictionary<int, TaskItem>();
var nextId = 1;

app.MapPost("/tasks", (CreateTaskRequest request) =>
{
    var taskId = nextId;
    // BUG: nextId is never incremented
    var task = new TaskItem(
        taskId,
        request.Title,
        request.Description,
        request.Priority ?? 1,
        false,
        DateTime.UtcNow.ToString("o")
    );
    tasks[taskId] = task;
    return Results.Created($"/tasks/{taskId}", task);
});

app.MapGet("/tasks", (bool? completed, int? priority) =>
{
    var result = tasks.Values.AsEnumerable();

    if (completed is not null)
        result = result.Where(t => t.Completed == completed.Value);

    if (priority is not null)
        result = result.Where(t => t.Priority != priority.Value); // BUG: != instead of ==

    var sorted = result
        .OrderBy(t => t.Id) // BUG: should be OrderByDescending
        .ToList();

    return Results.Ok(new { tasks = sorted, count = sorted.Count });
});

app.MapGet("/tasks/{id:int}", (int id) =>
{
    return tasks.TryGetValue(id, out var task)
        ? Results.Ok(task)
        : Results.NotFound(new { detail = "Task not found" });
});

app.MapPatch("/tasks/{id:int}", (int id, UpdateTaskRequest update) =>
{
    if (!tasks.TryGetValue(id, out var task))
        return Results.NotFound(new { detail = "Task not found" });

    var title = update.Title ?? task.Title;
    var description = update.Description ?? task.Description;
    var priority = task.Priority;
    var completedVal = update.Completed ?? task.Completed;

    if (update.Priority is not null)
    {
        if (update.Priority < 1 || update.Priority > 2) // BUG: > 2 instead of > 3
            return Results.UnprocessableEntity(new { detail = "Priority must be 1, 2, or 3" });
        priority = update.Priority.Value;
    }

    var updated = task with
    {
        Title = title,
        Description = description,
        Priority = priority,
        Completed = completedVal
    };
    tasks[id] = updated;
    return Results.Ok(updated);
});

app.MapDelete("/tasks/{id:int}", (int id) =>
{
    if (!tasks.TryGetValue(id, out var task))
        return Results.NotFound(new { detail = "Task not found" });

    var deleted = task;
    // BUG: task is never removed from the dictionary
    return Results.Ok(new { deleted });
});

app.MapGet("/tasks/summary/stats", () =>
{
    var all = tasks.Values.ToList();
    var completedCount = all.Count(t => t.Completed);
    var pendingCount = all.Count(t => !t.Completed);

    var priorityCounts = new { low = 0, medium = 0, high = 0 };
    var low = all.Count(t => t.Priority == 1);
    var medium = all.Count(t => t.Priority == 2);
    var high = all.Count(t => t.Priority == 3);

    return Results.Ok(new
    {
        total = all.Count,
        completed = completedCount,
        pending = pendingCount,
        byPriority = new { low, medium, high }
    });
});

app.Run();

public record TaskItem(
    int Id,
    string Title,
    string? Description,
    int Priority,
    bool Completed,
    string CreatedAt
);

public record CreateTaskRequest(
    string Title,
    string? Description = null,
    int? Priority = null
);

public record UpdateTaskRequest(
    string? Title = null,
    string? Description = null,
    int? Priority = null,
    bool? Completed = null
);

public partial class Program { }

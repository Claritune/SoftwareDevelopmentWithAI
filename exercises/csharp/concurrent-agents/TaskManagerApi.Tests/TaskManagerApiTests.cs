using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace TaskManagerApi.Tests;

public class TaskManagerApiTests : IDisposable
{
    private readonly WebApplicationFactory<Program> _factory;
    private readonly HttpClient _client;

    public TaskManagerApiTests()
    {
        _factory = new WebApplicationFactory<Program>().WithWebHostBuilder(b =>
        {
            b.UseUrls("http://127.0.0.1:0");
        });
        _client = _factory.CreateClient();
    }

    public void Dispose()
    {
        _client.Dispose();
        _factory.Dispose();
    }

    private async Task<JsonElement> PostTask(string title, int priority = 1)
    {
        var response = await _client.PostAsJsonAsync("/tasks", new { title, priority });
        var json = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
            throw new HttpRequestException($"POST /tasks returned {(int)response.StatusCode}: {json}");
        return JsonDocument.Parse(json).RootElement;
    }

    private async Task<JsonElement> GetJson(string url)
    {
        var response = await _client.GetAsync(url);
        var json = await response.Content.ReadAsStringAsync();
        return JsonDocument.Parse(json).RootElement;
    }

    // --- Issue 1: ID never increments ---

    [Fact]
    public async Task CreateMultipleTasks_HaveUniqueIds()
    {
        var r1 = await PostTask("Task A");
        var r2 = await PostTask("Task B");
        Assert.NotEqual(
            r1.GetProperty("id").GetInt32(),
            r2.GetProperty("id").GetInt32());
    }

    [Fact]
    public async Task TwoTasksAreBothStored()
    {
        await PostTask("Task A");
        await PostTask("Task B");
        var list = await GetJson("/tasks");
        Assert.Equal(2, list.GetProperty("count").GetInt32());
    }

    // --- Issue 2: priority filter returns wrong tasks ---

    [Fact]
    public async Task FilterByPriority_ReturnsOnlyMatchingTasks()
    {
        await PostTask("Low", priority: 1);
        await PostTask("High", priority: 3);
        var list = await GetJson("/tasks?priority=3");
        var tasks = list.GetProperty("tasks");
        Assert.True(tasks.GetArrayLength() > 0, "Should return at least one task");
        foreach (var task in tasks.EnumerateArray())
        {
            Assert.Equal(3, task.GetProperty("priority").GetInt32());
        }
    }

    [Fact]
    public async Task FilterByPriority_ExcludesOtherPriorities()
    {
        await PostTask("Low", priority: 1);
        await PostTask("High", priority: 3);
        var list = await GetJson("/tasks?priority=1");
        var tasks = list.GetProperty("tasks");
        Assert.Equal(1, tasks.GetArrayLength());
        Assert.Equal("Low", tasks[0].GetProperty("title").GetString());
    }

    // --- Issue 3: list order should be newest first ---

    [Fact]
    public async Task ListTasks_ReturnsNewestFirst()
    {
        var t1 = await PostTask("First");
        var t2 = await PostTask("Second");
        var t3 = await PostTask("Third");
        var list = await GetJson("/tasks");
        var tasks = list.GetProperty("tasks");

        var titles = new List<string>();
        foreach (var task in tasks.EnumerateArray())
            titles.Add(task.GetProperty("title").GetString()!);

        Assert.Equal(new[] { "Third", "Second", "First" }, titles);
    }

    // --- Issue 4: priority validation rejects valid value 3 ---

    [Fact]
    public async Task UpdatePriorityToHigh_IsAccepted()
    {
        var created = await PostTask("My Task");
        var taskId = created.GetProperty("id").GetInt32();
        var response = await _client.PatchAsJsonAsync($"/tasks/{taskId}", new { priority = 3 });
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var json = await response.Content.ReadAsStringAsync();
        var updated = JsonDocument.Parse(json).RootElement;
        Assert.Equal(3, updated.GetProperty("priority").GetInt32());
    }

    [Fact]
    public async Task UpdatePriorityAbove3_IsRejected()
    {
        var created = await PostTask("My Task");
        var taskId = created.GetProperty("id").GetInt32();
        var response = await _client.PatchAsJsonAsync($"/tasks/{taskId}", new { priority = 4 });
        Assert.Equal(HttpStatusCode.UnprocessableEntity, response.StatusCode);
    }

    // --- Issue 5: delete does not actually remove the task ---

    [Fact]
    public async Task Delete_RemovesTask()
    {
        var created = await PostTask("Doomed Task");
        var taskId = created.GetProperty("id").GetInt32();
        var delResponse = await _client.DeleteAsync($"/tasks/{taskId}");
        Assert.Equal(HttpStatusCode.OK, delResponse.StatusCode);
        var getResponse = await _client.GetAsync($"/tasks/{taskId}");
        Assert.Equal(HttpStatusCode.NotFound, getResponse.StatusCode);
    }

    [Fact]
    public async Task Delete_ReducesTaskCount()
    {
        await PostTask("Task A");
        var t2 = await PostTask("Task B");
        var taskId = t2.GetProperty("id").GetInt32();
        await _client.DeleteAsync($"/tasks/{taskId}");
        var list = await GetJson("/tasks");
        Assert.Equal(1, list.GetProperty("count").GetInt32());
    }
}

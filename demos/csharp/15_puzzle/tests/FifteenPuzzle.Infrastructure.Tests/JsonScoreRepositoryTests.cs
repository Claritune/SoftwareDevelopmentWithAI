using FifteenPuzzle.Core;
using Microsoft.Extensions.Logging.Abstractions;

namespace FifteenPuzzle.Infrastructure.Tests;

public sealed class JsonScoreRepositoryTests : IDisposable
{
    private readonly string _directory = Path.Combine(
        Path.GetTempPath(),
        $"FifteenPuzzleTests-{Guid.NewGuid():N}");

    [Fact]
    public async Task MissingFileLoadsAsEmpty()
    {
        var repository = CreateRepository();

        var entries = await repository.LoadAsync(CancellationToken.None);

        Assert.Empty(entries);
    }

    [Fact]
    public async Task RoundTripPreservesAllFields()
    {
        var repository = CreateRepository();
        var expected = new ScoreEntry(
            TimeSpan.FromMilliseconds(92_543),
            142,
            new DateTimeOffset(2026, 9, 2, 10, 15, 30, TimeSpan.Zero));

        await repository.SaveAsync([expected], CancellationToken.None);
        var actual = await repository.LoadAsync(CancellationToken.None);

        Assert.Equal([expected], actual);
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("{\"version\":2,\"entries\":[]}")]
    [InlineData("{\"version\":1,\"entries\":[{\"elapsedMilliseconds\":-1,\"moveCount\":3,\"completedAtUtc\":\"2026-09-02T10:15:30Z\"}]}")]
    public async Task InvalidFilesAreQuarantinedAndLoadAsEmpty(string contents)
    {
        Directory.CreateDirectory(_directory);
        var path = Path.Combine(_directory, "scores.json");
        await File.WriteAllTextAsync(path, contents, CancellationToken.None);
        var repository = CreateRepository();

        var entries = await repository.LoadAsync(CancellationToken.None);

        Assert.Empty(entries);
        Assert.False(File.Exists(path));
        Assert.Single(Directory.GetFiles(_directory, "*.corrupt"));
    }

    [Fact]
    public async Task SavingAgainAtomicallyReplacesExistingDocument()
    {
        var repository = CreateRepository();
        var first = new ScoreEntry(TimeSpan.FromSeconds(10), 50, DateTimeOffset.UtcNow);
        var second = new ScoreEntry(TimeSpan.FromSeconds(9), 60, DateTimeOffset.UtcNow);

        await repository.SaveAsync([first], CancellationToken.None);
        await repository.SaveAsync([second], CancellationToken.None);
        var entries = await repository.LoadAsync(CancellationToken.None);

        Assert.Equal([second], entries);
        Assert.Empty(Directory.GetFiles(_directory, "*.tmp"));
    }

    public void Dispose()
    {
        if (Directory.Exists(_directory))
        {
            Directory.Delete(_directory, recursive: true);
        }
    }

    private JsonScoreRepository CreateRepository() => new(
        new TemporaryPathProvider(Path.Combine(_directory, "scores.json")),
        NullLogger<JsonScoreRepository>.Instance);

    private sealed class TemporaryPathProvider(string path) : IAppDataPathProvider
    {
        public string ScoreFilePath => path;
    }
}
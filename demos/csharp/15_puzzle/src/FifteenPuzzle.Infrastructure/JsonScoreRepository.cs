using System.Text.Json;
using FifteenPuzzle.Core;
using Microsoft.Extensions.Logging;

namespace FifteenPuzzle.Infrastructure;

public sealed class JsonScoreRepository(
    IAppDataPathProvider pathProvider,
    ILogger<JsonScoreRepository> logger) : IScoreRepository
{
    private const int CurrentVersion = 1;
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true,
    };

    public async Task<IReadOnlyList<ScoreEntry>> LoadAsync(
        CancellationToken cancellationToken)
    {
        var path = pathProvider.ScoreFilePath;
        if (!File.Exists(path))
        {
            return [];
        }

        try
        {
            await using var stream = new FileStream(
                path,
                FileMode.Open,
                FileAccess.Read,
                FileShare.Read,
                bufferSize: 4096,
                useAsync: true);
            var document = await JsonSerializer.DeserializeAsync<ScoreDocument>(
                stream,
                JsonOptions,
                cancellationToken);

            if (document is null || document.Version != CurrentVersion || document.Entries is null)
            {
                throw new InvalidDataException("The score file has an unsupported schema.");
            }

            return document.Entries.Select(ToDomainEntry).ToArray();
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception exception)
        {
            logger.LogWarning(exception, "Could not load scores from {ScorePath}.", path);
            Quarantine(path);
            return [];
        }
    }

    public async Task SaveAsync(
        IReadOnlyList<ScoreEntry> entries,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(entries);

        var path = pathProvider.ScoreFilePath;
        var directory = Path.GetDirectoryName(path) ??
            throw new InvalidOperationException("The score file must have a parent directory.");
        Directory.CreateDirectory(directory);

        var temporaryPath = $"{path}.{Guid.NewGuid():N}.tmp";
        try
        {
            var document = new ScoreDocument
            {
                Version = CurrentVersion,
                Entries = entries.Select(FromDomainEntry).ToList(),
            };

            await using (var stream = new FileStream(
                temporaryPath,
                FileMode.CreateNew,
                FileAccess.Write,
                FileShare.None,
                bufferSize: 4096,
                FileOptions.Asynchronous | FileOptions.WriteThrough))
            {
                await JsonSerializer.SerializeAsync(
                    stream,
                    document,
                    JsonOptions,
                    cancellationToken);
                await stream.FlushAsync(cancellationToken);
                stream.Flush(flushToDisk: true);
            }

            File.Move(temporaryPath, path, overwrite: true);
        }
        finally
        {
            if (File.Exists(temporaryPath))
            {
                File.Delete(temporaryPath);
            }
        }
    }

    private static ScoreEntry ToDomainEntry(ScoreEntryData data)
    {
        if (data.ElapsedMilliseconds < 0 || data.MoveCount <= 0 ||
            data.CompletedAtUtc == default)
        {
            throw new InvalidDataException("The score file contains an invalid entry.");
        }

        return new ScoreEntry(
            TimeSpan.FromMilliseconds(data.ElapsedMilliseconds),
            data.MoveCount,
            data.CompletedAtUtc);
    }

    private static ScoreEntryData FromDomainEntry(ScoreEntry entry) => new()
    {
        ElapsedMilliseconds = (long)entry.Elapsed.TotalMilliseconds,
        MoveCount = entry.MoveCount,
        CompletedAtUtc = entry.CompletedAtUtc,
    };

    private void Quarantine(string path)
    {
        try
        {
            var quarantinePath = $"{path}.{DateTimeOffset.UtcNow:yyyyMMddHHmmssfff}.corrupt";
            File.Move(path, quarantinePath, overwrite: false);
        }
        catch (Exception exception)
        {
            logger.LogWarning(exception, "Could not quarantine invalid score file {ScorePath}.", path);
        }
    }

    private sealed class ScoreDocument
    {
        public int Version { get; init; }

        public List<ScoreEntryData>? Entries { get; init; }
    }

    private sealed class ScoreEntryData
    {
        public long ElapsedMilliseconds { get; init; }

        public int MoveCount { get; init; }

        public DateTimeOffset CompletedAtUtc { get; init; }
    }
}
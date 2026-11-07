namespace FifteenPuzzle.Core;

public sealed class Leaderboard
{
    private const int Limit = 10;
    private IReadOnlyList<ScoreEntry> _entries = [];

    public Leaderboard(IEnumerable<ScoreEntry> entries)
    {
        ArgumentNullException.ThrowIfNull(entries);
        Update(entries);
    }

    public IReadOnlyList<ScoreEntry> Entries => _entries;

    public LeaderboardSnapshot Snapshot { get; private set; } =
        new([], []);

    public LeaderboardSnapshot Add(ScoreEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        Update(_entries.Append(entry));
        return Snapshot;
    }

    private void Update(IEnumerable<ScoreEntry> entries)
    {
        var unique = entries.Distinct().ToArray();
        var fastest = unique
            .OrderBy(entry => entry.Elapsed)
            .ThenBy(entry => entry.MoveCount)
            .ThenBy(entry => entry.CompletedAtUtc)
            .Take(Limit)
            .ToArray();
        var fewest = unique
            .OrderBy(entry => entry.MoveCount)
            .ThenBy(entry => entry.Elapsed)
            .ThenBy(entry => entry.CompletedAtUtc)
            .Take(Limit)
            .ToArray();

        Snapshot = new(fastest, fewest);
        _entries = fastest.Concat(fewest).Distinct().ToArray();
    }
}
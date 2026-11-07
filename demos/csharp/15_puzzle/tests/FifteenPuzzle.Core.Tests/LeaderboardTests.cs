using FifteenPuzzle.Core;

namespace FifteenPuzzle.Core.Tests;

public sealed class LeaderboardTests
{
    private static readonly DateTimeOffset Start =
        new(2026, 9, 2, 10, 0, 0, TimeSpan.Zero);

    [Fact]
    public void AppliesRequiredOrderingAndTieBreakers()
    {
        var earlier = Entry(seconds: 10, moves: 50, minute: 1);
        var fewerMoves = Entry(seconds: 10, moves: 40, minute: 2);
        var faster = Entry(seconds: 9, moves: 100, minute: 3);
        var leaderboard = new Leaderboard([earlier, fewerMoves, faster]);

        Assert.Equal([faster, fewerMoves, earlier], leaderboard.Snapshot.FastestTimes);
        Assert.Equal([fewerMoves, earlier, faster], leaderboard.Snapshot.FewestMoves);
    }

    [Fact]
    public void LimitsListsAndRetainsUnionOfQualifyingEntries()
    {
        var entries = Enumerable.Range(1, 20)
            .Select(index => Entry(
                seconds: index,
                moves: 21 - index,
                minute: index))
            .ToArray();
        var leaderboard = new Leaderboard(entries);

        Assert.Equal(10, leaderboard.Snapshot.FastestTimes.Count);
        Assert.Equal(10, leaderboard.Snapshot.FewestMoves.Count);
        Assert.Equal(20, leaderboard.Entries.Count);
    }

    [Fact]
    public void DeduplicatesIdenticalEntries()
    {
        var entry = Entry(seconds: 15, moves: 80, minute: 1);
        var leaderboard = new Leaderboard([entry, entry]);

        leaderboard.Add(entry);

        Assert.Single(leaderboard.Entries);
        Assert.Single(leaderboard.Snapshot.FastestTimes);
        Assert.Single(leaderboard.Snapshot.FewestMoves);
    }

    private static ScoreEntry Entry(int seconds, int moves, int minute) =>
        new(TimeSpan.FromSeconds(seconds), moves, Start.AddMinutes(minute));
}
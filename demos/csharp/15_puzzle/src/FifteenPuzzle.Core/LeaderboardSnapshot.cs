namespace FifteenPuzzle.Core;

public sealed record LeaderboardSnapshot(
    IReadOnlyList<ScoreEntry> FastestTimes,
    IReadOnlyList<ScoreEntry> FewestMoves);
namespace FifteenPuzzle.Core;

public sealed record ScoreEntry
{
    public ScoreEntry(TimeSpan elapsed, int moveCount, DateTimeOffset completedAtUtc)
    {
        if (elapsed < TimeSpan.Zero)
        {
            throw new ArgumentOutOfRangeException(nameof(elapsed));
        }

        if (moveCount <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(moveCount));
        }

        Elapsed = elapsed;
        MoveCount = moveCount;
        CompletedAtUtc = completedAtUtc.ToUniversalTime();
    }

    public TimeSpan Elapsed { get; }

    public int MoveCount { get; }

    public DateTimeOffset CompletedAtUtc { get; }
}
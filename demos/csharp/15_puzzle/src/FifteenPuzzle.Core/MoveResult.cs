namespace FifteenPuzzle.Core;

public readonly record struct MoveResult(
    bool Moved,
    bool Solved,
    int MoveCount,
    TimeSpan Elapsed);
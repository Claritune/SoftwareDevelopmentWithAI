using FifteenPuzzle.Core;

namespace FifteenPuzzle.Infrastructure;

public sealed class SystemWallClock : IWallClock
{
    public DateTimeOffset UtcNow => DateTimeOffset.UtcNow;
}
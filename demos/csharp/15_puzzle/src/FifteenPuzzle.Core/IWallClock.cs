namespace FifteenPuzzle.Core;

public interface IWallClock
{
    DateTimeOffset UtcNow { get; }
}
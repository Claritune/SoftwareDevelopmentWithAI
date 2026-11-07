using System.Diagnostics;
using FifteenPuzzle.Core;

namespace FifteenPuzzle.Infrastructure;

public sealed class SystemMonotonicClock : IMonotonicClock
{
    public long GetTimestamp() => Stopwatch.GetTimestamp();

    public TimeSpan GetElapsedTime(long startTimestamp, long endTimestamp) =>
        Stopwatch.GetElapsedTime(startTimestamp, endTimestamp);
}
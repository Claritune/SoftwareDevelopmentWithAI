namespace FifteenPuzzle.Core;

public interface IMonotonicClock
{
    long GetTimestamp();

    TimeSpan GetElapsedTime(long startTimestamp, long endTimestamp);
}
using FifteenPuzzle.Core;

namespace FifteenPuzzle.Core.Tests;

public sealed class GameTimerTests
{
    [Fact]
    public void AccumulatesOnlyRunningIntervals()
    {
        var clock = new FakeClock();
        var timer = new GameTimer(clock);

        timer.Start();
        clock.Advance(TimeSpan.FromSeconds(3));
        timer.Pause();
        clock.Advance(TimeSpan.FromSeconds(20));
        timer.Resume();
        clock.Advance(TimeSpan.FromSeconds(2));
        timer.Stop();
        clock.Advance(TimeSpan.FromSeconds(10));

        Assert.Equal(TimeSpan.FromSeconds(5), timer.Elapsed);
        Assert.False(timer.IsRunning);
    }

    [Fact]
    public void ResetReturnsTimerToUnstartedState()
    {
        var clock = new FakeClock();
        var timer = new GameTimer(clock);
        timer.Start();
        clock.Advance(TimeSpan.FromSeconds(4));

        timer.Reset();

        Assert.Equal(TimeSpan.Zero, timer.Elapsed);
        Assert.False(timer.IsStarted);
        Assert.False(timer.IsRunning);
    }

    internal sealed class FakeClock : IMonotonicClock
    {
        private long _milliseconds;

        public long GetTimestamp() => _milliseconds;

        public TimeSpan GetElapsedTime(long startTimestamp, long endTimestamp) =>
            TimeSpan.FromMilliseconds(endTimestamp - startTimestamp);

        public void Advance(TimeSpan duration) =>
            _milliseconds += (long)duration.TotalMilliseconds;
    }
}
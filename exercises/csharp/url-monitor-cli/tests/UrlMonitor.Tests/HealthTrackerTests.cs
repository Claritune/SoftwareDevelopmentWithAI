using UrlMonitor.Monitoring;

namespace UrlMonitor.Tests;

public class HealthTrackerTests
{
    private static readonly DateTimeOffset Timestamp =
        new(2026, 8, 4, 10, 0, 0, TimeSpan.Zero);
    private static readonly CheckResult Healthy =
        new(true, 200, TimeSpan.FromMilliseconds(12), "HTTP 200");
    private static readonly CheckResult Unhealthy =
        new(false, 503, TimeSpan.FromMilliseconds(15), "HTTP 503");

    [Fact]
    public void FirstSuccessEmitsUpWithOriginalResultAndTimestamp()
    {
        var tracker = new HealthTracker();

        var transition = tracker.Observe(Healthy, Timestamp);

        Assert.NotNull(transition);
        Assert.Equal(HealthState.Up, transition.State);
        Assert.Same(Healthy, transition.Result);
        Assert.Equal(Timestamp, transition.Timestamp);
    }

    [Fact]
    public void FailuresBelowThresholdDoNotEmitTransition()
    {
        var tracker = new HealthTracker();

        Assert.Null(tracker.Observe(Unhealthy, Timestamp));
        Assert.Null(tracker.Observe(Unhealthy, Timestamp));
        Assert.Equal(HealthState.Unknown, tracker.State);
    }

    [Fact]
    public void ThirdFailureFromUnknownEmitsDown()
    {
        var tracker = new HealthTracker();
        tracker.Observe(Unhealthy, Timestamp);
        tracker.Observe(Unhealthy, Timestamp);

        var transition = tracker.Observe(Unhealthy, Timestamp);

        Assert.Equal(HealthState.Down, transition?.State);
    }

    [Fact]
    public void ThirdFailureAfterUpEmitsDown()
    {
        var tracker = new HealthTracker();
        tracker.Observe(Healthy, Timestamp);
        tracker.Observe(Unhealthy, Timestamp);
        tracker.Observe(Unhealthy, Timestamp);

        var transition = tracker.Observe(Unhealthy, Timestamp);

        Assert.Equal(HealthState.Down, transition?.State);
    }

    [Fact]
    public void RepeatedFailuresWhileDownDoNotEmitTransition()
    {
        var tracker = CreateDownTracker();

        Assert.Null(tracker.Observe(Unhealthy, Timestamp));
    }

    [Fact]
    public void OneSuccessWhileDownEmitsRecoveryUp()
    {
        var tracker = CreateDownTracker();

        var transition = tracker.Observe(Healthy, Timestamp);

        Assert.Equal(HealthState.Up, transition?.State);
    }

    [Fact]
    public void RepeatedSuccessWhileUpDoesNotEmitTransition()
    {
        var tracker = new HealthTracker();
        tracker.Observe(Healthy, Timestamp);

        Assert.Null(tracker.Observe(Healthy, Timestamp));
    }

    [Fact]
    public void SuccessResetsPartialFailureCount()
    {
        var tracker = new HealthTracker();
        tracker.Observe(Unhealthy, Timestamp);
        tracker.Observe(Unhealthy, Timestamp);
        tracker.Observe(Healthy, Timestamp);

        Assert.Null(tracker.Observe(Unhealthy, Timestamp));
        Assert.Null(tracker.Observe(Unhealthy, Timestamp));
        Assert.Equal(HealthState.Up, tracker.State);
    }

    private static HealthTracker CreateDownTracker()
    {
        var tracker = new HealthTracker();
        tracker.Observe(Unhealthy, Timestamp);
        tracker.Observe(Unhealthy, Timestamp);
        tracker.Observe(Unhealthy, Timestamp);
        return tracker;
    }
}
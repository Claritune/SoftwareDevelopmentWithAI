using UrlMonitor.Monitoring;
using UrlMonitor.Output;
using MonitorLoop = UrlMonitor.Monitoring.UrlMonitor;

namespace UrlMonitor.Tests;

public class UrlMonitorTests
{
    private static readonly Uri Url = new("https://example.com");
    private static readonly DateTimeOffset Timestamp =
        new(2026, 8, 4, 10, 0, 0, TimeSpan.Zero);

    [Fact]
    public async Task ChecksImmediatelyWritesOnlyTransitionThenDelays()
    {
        using var cancellationSource = new CancellationTokenSource();
        var events = new List<string>();
        var checker = new StubChecker((_, _, _) =>
        {
            events.Add("check");
            return Task.FromResult(Healthy());
        });
        var sink = new StubSink((_, _) =>
        {
            events.Add("write");
            return Task.CompletedTask;
        });
        var monitor = new MonitorLoop(
            Url,
            TimeSpan.FromSeconds(10),
            TimeSpan.FromSeconds(1),
            checker,
            new HealthTracker(),
            sink,
            () => Timestamp,
            (_, _) =>
            {
                events.Add("delay");
                cancellationSource.Cancel();
                return Task.FromCanceled(cancellationSource.Token);
            });

        await monitor.RunAsync(cancellationSource.Token);

        Assert.Equal(["check", "write", "delay"], events);
        Assert.Single(sink.Transitions);
        Assert.Equal(Timestamp, sink.Transitions[0].Timestamp);
    }

    [Fact]
    public async Task RoutineHealthyCheckProducesNoSecondNotification()
    {
        using var cancellationSource = new CancellationTokenSource();
        var checkCount = 0;
        var checker = new StubChecker((_, _, _) =>
        {
            checkCount++;
            return Task.FromResult(Healthy());
        });
        var sink = new StubSink();
        var monitor = new MonitorLoop(
            Url,
            TimeSpan.Zero,
            TimeSpan.FromSeconds(1),
            checker,
            new HealthTracker(),
            sink,
            () => Timestamp,
            (_, _) =>
            {
                if (checkCount == 2)
                {
                    cancellationSource.Cancel();
                    return Task.FromCanceled(cancellationSource.Token);
                }

                return Task.CompletedTask;
            });

        await monitor.RunAsync(cancellationSource.Token);

        Assert.Equal(2, checkCount);
        Assert.Single(sink.Transitions);
    }

    [Fact]
    public async Task CancellationDuringCheckExitsWithoutFailureTransitionOrDelay()
    {
        using var cancellationSource = new CancellationTokenSource();
        var delayCalled = false;
        var checker = new StubChecker(async (_, _, token) =>
        {
            cancellationSource.Cancel();
            await Task.Delay(Timeout.InfiniteTimeSpan, token);
            return Healthy();
        });
        var sink = new StubSink();
        var monitor = new MonitorLoop(
            Url,
            TimeSpan.Zero,
            TimeSpan.FromSeconds(1),
            checker,
            new HealthTracker(),
            sink,
            () => Timestamp,
            (_, _) =>
            {
                delayCalled = true;
                return Task.CompletedTask;
            });

        await monitor.RunAsync(cancellationSource.Token);

        Assert.Empty(sink.Transitions);
        Assert.False(delayCalled);
    }

    private static CheckResult Healthy() =>
        new(true, 200, TimeSpan.FromMilliseconds(5), "HTTP 200");

    private sealed class StubChecker(
        Func<Uri, TimeSpan, CancellationToken, Task<CheckResult>> checkAsync)
        : IUrlChecker
    {
        public Task<CheckResult> CheckAsync(
            Uri url,
            TimeSpan timeout,
            CancellationToken cancellationToken) => checkAsync(url, timeout, cancellationToken);
    }

    private sealed class StubSink(
        Func<HealthTransition, CancellationToken, Task>? writeAsync = null)
        : INotificationSink
    {
        public List<HealthTransition> Transitions { get; } = [];

        public Task WriteAsync(HealthTransition transition, CancellationToken cancellationToken)
        {
            Transitions.Add(transition);
            return writeAsync?.Invoke(transition, cancellationToken) ?? Task.CompletedTask;
        }
    }
}
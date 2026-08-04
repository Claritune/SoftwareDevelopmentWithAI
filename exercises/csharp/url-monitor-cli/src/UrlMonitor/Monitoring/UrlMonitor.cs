using UrlMonitor.Output;

namespace UrlMonitor.Monitoring;

public sealed class UrlMonitor(
    Uri url,
    TimeSpan interval,
    TimeSpan timeout,
    IUrlChecker checker,
    HealthTracker healthTracker,
    INotificationSink notificationSink,
    Func<DateTimeOffset>? getUtcNow = null,
    Func<TimeSpan, CancellationToken, Task>? delayAsync = null)
{
    private readonly Func<DateTimeOffset> _getUtcNow =
        getUtcNow ?? TimeProvider.System.GetUtcNow;
    private readonly Func<TimeSpan, CancellationToken, Task> _delayAsync =
        delayAsync ?? Task.Delay;

    public async Task RunAsync(CancellationToken cancellationToken)
    {
        try
        {
            while (true)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var result = await checker.CheckAsync(url, timeout, cancellationToken);
                var transition = healthTracker.Observe(result, _getUtcNow());

                if (transition is not null)
                {
                    await notificationSink.WriteAsync(transition, cancellationToken);
                }

                await _delayAsync(interval, cancellationToken);
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
    }
}
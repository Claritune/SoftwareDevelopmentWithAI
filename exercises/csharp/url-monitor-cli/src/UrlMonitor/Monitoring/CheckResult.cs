namespace UrlMonitor.Monitoring;

public sealed record CheckResult(
    bool IsHealthy,
    int? StatusCode,
    TimeSpan Elapsed,
    string Detail);
namespace UrlMonitor.Monitoring;

public enum HealthState
{
    Unknown,
    Up,
    Down
}

public sealed record HealthTransition(
    HealthState State,
    CheckResult Result,
    DateTimeOffset Timestamp);
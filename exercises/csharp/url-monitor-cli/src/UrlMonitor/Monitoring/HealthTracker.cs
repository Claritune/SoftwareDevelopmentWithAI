namespace UrlMonitor.Monitoring;

public sealed class HealthTracker
{
    private const int FailureThreshold = 3;
    private int _consecutiveFailures;

    public HealthState State { get; private set; } = HealthState.Unknown;

    public HealthTransition? Observe(CheckResult result, DateTimeOffset timestamp)
    {
        if (result.IsHealthy)
        {
            _consecutiveFailures = 0;
            if (State == HealthState.Up)
            {
                return null;
            }

            State = HealthState.Up;
            return new HealthTransition(State, result, timestamp);
        }

        _consecutiveFailures++;
        if (_consecutiveFailures < FailureThreshold || State == HealthState.Down)
        {
            return null;
        }

        State = HealthState.Down;
        return new HealthTransition(State, result, timestamp);
    }
}
using System.Globalization;
using UrlMonitor.Monitoring;

namespace UrlMonitor.Output;

public interface INotificationSink
{
    Task WriteAsync(HealthTransition transition, CancellationToken cancellationToken);
}

public sealed class ConsoleNotificationSink(Uri url, TextWriter writer) : INotificationSink
{
    public Task WriteAsync(HealthTransition transition, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();

        var state = transition.State == HealthState.Up ? "UP  " : "DOWN";
        var elapsedMilliseconds = Math.Round(
            transition.Result.Elapsed.TotalMilliseconds,
            MidpointRounding.AwayFromZero);
        var line = string.Create(
            CultureInfo.InvariantCulture,
            $"[{transition.Timestamp.UtcDateTime:O}] {state}  {url} ({transition.Result.Detail}, {elapsedMilliseconds}ms)");

        return writer.WriteLineAsync(line);
    }
}
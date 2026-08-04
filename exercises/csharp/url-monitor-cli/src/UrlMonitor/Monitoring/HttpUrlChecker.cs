using System.Diagnostics;

namespace UrlMonitor.Monitoring;

public interface IUrlChecker
{
    Task<CheckResult> CheckAsync(
        Uri url,
        TimeSpan timeout,
        CancellationToken cancellationToken);
}

public sealed class HttpUrlChecker(HttpClient httpClient) : IUrlChecker
{
    public async Task<CheckResult> CheckAsync(
        Uri url,
        TimeSpan timeout,
        CancellationToken cancellationToken)
    {
        using var timeoutSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeoutSource.CancelAfter(timeout);
        var startedAt = Stopwatch.GetTimestamp();

        try
        {
            using var response = await httpClient.GetAsync(url, timeoutSource.Token);
            var elapsed = Stopwatch.GetElapsedTime(startedAt);
            var statusCode = (int)response.StatusCode;

            return new CheckResult(
                statusCode is >= 200 and <= 399,
                statusCode,
                elapsed,
                $"HTTP {statusCode}");
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return new CheckResult(
                false,
                null,
                Stopwatch.GetElapsedTime(startedAt),
                "Request timed out");
        }
    }
}
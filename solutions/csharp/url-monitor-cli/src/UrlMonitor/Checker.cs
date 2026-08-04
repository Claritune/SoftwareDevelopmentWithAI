using System.Diagnostics;

namespace UrlMonitor;

public enum Status { Unknown, Up, Down }

public record CheckResult(int HttpStatus, string? Error, double TotalMs);

public static class Checker
{
    /// <summary>
    /// Perform an HTTP GET check against the given URL.
    /// </summary>
    public static async Task<CheckResult> Check(HttpClient client, string url, int timeoutSeconds)
    {
        var sw = Stopwatch.StartNew();

        try
        {
            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(timeoutSeconds));
            var response = await client.GetAsync(url, cts.Token);
            sw.Stop();

            return new CheckResult((int)response.StatusCode, null, sw.Elapsed.TotalMilliseconds);
        }
        catch (TaskCanceledException)
        {
            sw.Stop();
            return new CheckResult(0, "timeout", sw.Elapsed.TotalMilliseconds);
        }
        catch (HttpRequestException hre)
        {
            sw.Stop();
            var errorType = ClassifyHttpError(hre);
            return new CheckResult(0, errorType, sw.Elapsed.TotalMilliseconds);
        }
        catch (Exception ex)
        {
            sw.Stop();
            return new CheckResult(0, ex.Message, sw.Elapsed.TotalMilliseconds);
        }
    }

    /// <summary>
    /// Classify a check result into Up or Down.
    /// Up only if no error AND HttpStatus == 200.
    /// </summary>
    public static Status Classify(CheckResult result)
    {
        if (result.Error is not null)
            return Status.Down;

        return result.HttpStatus == 200 ? Status.Up : Status.Down;
    }

    /// <summary>
    /// Return the lowercase string name for a status.
    /// </summary>
    public static string StatusName(Status status) => status switch
    {
        Status.Unknown => "unknown",
        Status.Up => "up",
        Status.Down => "down",
        _ => "unknown"
    };

    private static string ClassifyHttpError(HttpRequestException ex)
    {
        var message = ex.Message.ToLowerInvariant();

        if (message.Contains("connection refused") || message.Contains("actively refused"))
            return "connection_refused";
        if (message.Contains("name resolution") || message.Contains("no such host"))
            return "dns_resolution_failed";
        if (message.Contains("ssl") || message.Contains("tls") || message.Contains("certificate"))
            return "ssl_error";

        return $"http_error: {ex.Message}";
    }
}

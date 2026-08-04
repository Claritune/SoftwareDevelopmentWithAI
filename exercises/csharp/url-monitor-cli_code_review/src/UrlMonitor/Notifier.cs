namespace UrlMonitor;

public static class Notifier
{
    /// <summary>
    /// Return the current UTC time in ISO 8601 format.
    /// </summary>
    public static string Iso8601Now() =>
        DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");

    /// <summary>
    /// Log an informational message to stdout.
    /// </summary>
    public static void LogInfo(string message)
    {
        Console.WriteLine($"{Iso8601Now()} INFO  {message}");
    }

    /// <summary>
    /// Log an error message to stderr.
    /// </summary>
    public static void LogError(string message)
    {
        Console.Error.WriteLine($"{Iso8601Now()} ERROR {message}");
    }

    /// <summary>
    /// Emit a status transition notification.
    /// </summary>
    public static void EmitTransition(string url, Status newStatus, CheckResult result)
    {
        var statusLabel = newStatus == Status.Up ? "UP   " : "DOWN ";
        var detail = FormatDetail(result);
        Console.WriteLine($"{Iso8601Now()} {statusLabel} {url}  ({detail})");
    }

    /// <summary>
    /// Emit a verbose check log line.
    /// </summary>
    public static void EmitVerboseCheck(string url, Status status, CheckResult result)
    {
        var statusLabel = status == Status.Up ? "UP   " : "DOWN ";
        var detail = FormatDetail(result);
        Console.WriteLine($"{Iso8601Now()} {statusLabel} {url}  ({detail})");
    }

    private static string FormatDetail(CheckResult result)
    {
        if (result.Error is not null)
        {
            return $"error: {result.Error}";
        }
        return $"HTTP {result.HttpStatus}, {result.TotalMs:F0}ms";
    }
}

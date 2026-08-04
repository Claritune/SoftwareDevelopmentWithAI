using System.Text;

namespace UrlMonitor;

public class UrlStats
{
    public long TotalChecks { get; set; }
    public long UpChecks { get; set; }
    public long DownChecks { get; set; }
    public Dictionary<int, long> HttpStatus { get; set; } = new();
    public Dictionary<string, long> Errors { get; set; } = new();
}

public static class Stats
{
    /// <summary>
    /// Record a check result into the URL stats.
    /// </summary>
    public static void RecordCheck(UrlStats stats, CheckResult result, Status status)
    {
        stats.TotalChecks++;

        if (status == Status.Up)
            stats.UpChecks++;
        else
            stats.DownChecks++;

        if (result.HttpStatus > 0)
        {
            if (!stats.HttpStatus.ContainsKey(result.HttpStatus))
                stats.HttpStatus[result.HttpStatus] = 0;
            stats.HttpStatus[result.HttpStatus]++;
        }

        if (result.Error is not null)
        {
            if (!stats.Errors.ContainsKey(result.Error))
                stats.Errors[result.Error] = 0;
            stats.Errors[result.Error]++;
        }
    }

    /// <summary>
    /// Format stats for a single URL.
    /// </summary>
    public static string FormatUrlStats(string url, UrlStats stats)
    {
        var sb = new StringBuilder();

        var uptime = stats.TotalChecks > 0
            ? (double)stats.UpChecks / stats.TotalChecks * 100.0
            : 0.0;

        sb.AppendLine($"{url}   checks={stats.TotalChecks}  up={stats.UpChecks}  down={stats.DownChecks}  uptime={uptime:F1}%");

        // HTTP status codes
        var httpParts = stats.HttpStatus
            .OrderBy(kv => kv.Key)
            .Select(kv => $"{kv.Key}: {kv.Value}");
        var httpLine = httpParts.Any() ? string.Join("   ", httpParts) : "(none)";
        sb.AppendLine($"  HTTP  {httpLine}");

        // Errors
        var errorParts = stats.Errors
            .OrderBy(kv => kv.Key)
            .Select(kv => $"{kv.Key}: {kv.Value}");
        var errorLine = errorParts.Any() ? string.Join("   ", errorParts) : "(none)";
        sb.AppendLine($"  errors  {errorLine}");

        return sb.ToString();
    }

    /// <summary>
    /// Format stats for all URLs in the state store.
    /// </summary>
    public static string FormatAllStats(StateStore store)
    {
        var sb = new StringBuilder();
        sb.AppendLine("=== URL Monitor Stats ===");
        sb.AppendLine();

        foreach (var (url, state) in store.Urls.OrderBy(kv => kv.Key))
        {
            sb.Append(FormatUrlStats(url, state.Stats));
            sb.AppendLine();
        }

        return sb.ToString();
    }
}

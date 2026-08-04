using System.CommandLine;
using System.CommandLine.Invocation;
using System.CommandLine.Parsing;
using UrlMonitor.Monitoring;
using UrlMonitor.Output;

namespace UrlMonitor;

public sealed class CliApplication
{
    public static readonly TimeSpan DefaultInterval = TimeSpan.FromSeconds(10);
    public static readonly TimeSpan DefaultTimeout = TimeSpan.FromSeconds(10);
    public const int DefaultFailureThreshold = 3;

    private readonly HttpClient _httpClient;
    private readonly TextWriter _standardOutput;
    private readonly TextWriter _standardError;
    private readonly Func<Uri, CancellationToken, Task>? _runMonitorAsync;

    public CliApplication(
        HttpClient httpClient,
        TextWriter? standardOutput = null,
        TextWriter? standardError = null,
        Func<Uri, CancellationToken, Task>? runMonitorAsync = null)
    {
        _httpClient = httpClient;
        _standardOutput = standardOutput ?? Console.Out;
        _standardError = standardError ?? Console.Error;
        _runMonitorAsync = runMonitorAsync;
    }

    public async Task<int> RunAsync(string[] args, CancellationToken cancellationToken)
    {
        var urlArgument = new Argument<string>("url")
        {
            Description = "The absolute HTTP or HTTPS URL to monitor"
        };
        urlArgument.Validators.Add(result =>
        {
            var value = result.GetValue(urlArgument);
            if (!TryParseUrl(value, out _))
            {
                result.AddError("URL must be an absolute HTTP or HTTPS URL.");
            }
        });

        var rootCommand = new RootCommand("Monitor a URL and report health transitions")
        {
            urlArgument
        };

        rootCommand.SetAction(async (parseResult, actionCancellationToken) =>
        {
            var url = ParseUrl(parseResult.GetValue(urlArgument)!);

            if (_runMonitorAsync is not null)
            {
                await _runMonitorAsync(url, actionCancellationToken);
                return 0;
            }

            var monitor = new Monitoring.UrlMonitor(
                url,
                DefaultInterval,
                DefaultTimeout,
                new HttpUrlChecker(_httpClient),
                new HealthTracker(),
                new ConsoleNotificationSink(url, _standardOutput));
            await monitor.RunAsync(actionCancellationToken);
            return 0;
        });

        var configuration = new InvocationConfiguration
        {
            Output = _standardOutput,
            Error = _standardError
        };
        var parseResult = rootCommand.Parse(args);
        var exitCode = await parseResult.InvokeAsync(configuration, cancellationToken);
        return parseResult.Errors.Count > 0 ? 2 : exitCode;
    }

    private static bool TryParseUrl(string? value, out Uri? url)
    {
        if (Uri.TryCreate(value, UriKind.Absolute, out url) &&
            (url.Scheme == Uri.UriSchemeHttp || url.Scheme == Uri.UriSchemeHttps))
        {
            return true;
        }

        url = null;
        return false;
    }

    private static Uri ParseUrl(string value)
    {
        TryParseUrl(value, out var url);
        return url!;
    }
}
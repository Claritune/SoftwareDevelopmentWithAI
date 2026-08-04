namespace UrlMonitor.Tests;

public class CliApplicationTests
{
    [Theory]
    [InlineData()]
    [InlineData("not-a-url")]
    [InlineData("/relative/path")]
    [InlineData("ftp://example.com")]
    public async Task InvalidUrlWritesErrorReturnsTwoAndDoesNotRun(params string[] args)
    {
        var standardOutput = new StringWriter();
        var standardError = new StringWriter();
        var runnerCalled = false;
        using var httpClient = new HttpClient();
        var application = new CliApplication(
            httpClient,
            standardOutput,
            standardError,
            (_, _) =>
            {
                runnerCalled = true;
                return Task.CompletedTask;
            });

        var exitCode = await application.RunAsync(args, CancellationToken.None);

        Assert.Equal(2, exitCode);
        Assert.False(runnerCalled);
        Assert.NotEmpty(standardError.ToString());
    }

    [Fact]
    public async Task ValidUrlInvokesRunnerAndReturnsZero()
    {
        Uri? capturedUrl = null;
        using var httpClient = new HttpClient();
        var application = new CliApplication(
            httpClient,
            new StringWriter(),
            new StringWriter(),
            (url, _) =>
            {
                capturedUrl = url;
                return Task.CompletedTask;
            });

        var exitCode = await application.RunAsync(
            ["https://example.com/health"],
            CancellationToken.None);

        Assert.Equal(0, exitCode);
        Assert.Equal(new Uri("https://example.com/health"), capturedUrl);
    }

    [Fact]
    public async Task HelpIsGeneratedOnStandardOutputAndReturnsZero()
    {
        var standardOutput = new StringWriter();
        using var httpClient = new HttpClient();
        var application = new CliApplication(
            httpClient,
            standardOutput,
            new StringWriter(),
            (_, _) => throw new InvalidOperationException("Runner should not be called."));

        var exitCode = await application.RunAsync(["--help"], CancellationToken.None);

        Assert.Equal(0, exitCode);
        Assert.Contains("url", standardOutput.ToString(), StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task CanceledInvocationReturnsZero()
    {
        using var cancellationSource = new CancellationTokenSource();
        using var httpClient = new HttpClient();
        var application = new CliApplication(
            httpClient,
            new StringWriter(),
            new StringWriter(),
            (_, _) =>
            {
                cancellationSource.Cancel();
                return Task.CompletedTask;
            });

        var exitCode = await application.RunAsync(
            ["https://example.com"],
            cancellationSource.Token);

        Assert.Equal(0, exitCode);
    }
}
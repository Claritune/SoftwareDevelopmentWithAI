using System.Net;
using UrlMonitor.Monitoring;

namespace UrlMonitor.Tests;

public class HttpUrlCheckerTests
{
    private static readonly Uri Url = new("https://example.com");

    [Theory]
    [InlineData(200)]
    [InlineData(399)]
    public async Task HealthyStatusBoundariesAreClassifiedAsHealthy(int statusCode)
    {
        var checker = CreateChecker((_, _) =>
            Task.FromResult(new HttpResponseMessage((HttpStatusCode)statusCode)));

        var result = await checker.CheckAsync(Url, TimeSpan.FromSeconds(1), CancellationToken.None);

        Assert.True(result.IsHealthy);
        Assert.Equal(statusCode, result.StatusCode);
        Assert.Equal($"HTTP {statusCode}", result.Detail);
        Assert.True(result.Elapsed >= TimeSpan.Zero);
    }

    [Theory]
    [InlineData(400)]
    [InlineData(599)]
    public async Task UnhealthyStatusBoundariesAreClassifiedAsUnhealthy(int statusCode)
    {
        var checker = CreateChecker((_, _) =>
            Task.FromResult(new HttpResponseMessage((HttpStatusCode)statusCode)));

        var result = await checker.CheckAsync(Url, TimeSpan.FromSeconds(1), CancellationToken.None);

        Assert.False(result.IsHealthy);
        Assert.Equal(statusCode, result.StatusCode);
    }

    [Fact]
    public async Task ResponseIsDisposedAfterClassification()
    {
        var content = new TrackingContent();
        var checker = CreateChecker((_, _) => Task.FromResult(
            new HttpResponseMessage(HttpStatusCode.OK) { Content = content }));

        await checker.CheckAsync(Url, TimeSpan.FromSeconds(1), CancellationToken.None);

        Assert.True(content.IsDisposed);
    }

    [Fact]
    public async Task RequestTimeoutReturnsUnhealthyResult()
    {
        var checker = CreateChecker(async (_, token) =>
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, token);
            return new HttpResponseMessage(HttpStatusCode.OK);
        });

        var result = await checker.CheckAsync(Url, TimeSpan.FromMilliseconds(10), CancellationToken.None);

        Assert.False(result.IsHealthy);
        Assert.Null(result.StatusCode);
        Assert.Equal("Request timed out", result.Detail);
    }

    [Fact]
    public async Task ApplicationCancellationIsPropagated()
    {
        using var cancellationSource = new CancellationTokenSource();
        cancellationSource.Cancel();
        var checker = CreateChecker((_, token) => Task.FromCanceled<HttpResponseMessage>(token));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            checker.CheckAsync(Url, TimeSpan.FromSeconds(1), cancellationSource.Token));
    }

    private static HttpUrlChecker CreateChecker(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> handler)
    {
        return new HttpUrlChecker(new HttpClient(new StubHttpMessageHandler(handler)));
    }

    private sealed class StubHttpMessageHandler(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> handler)
        : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken) => handler(request, cancellationToken);
    }

    private sealed class TrackingContent : ByteArrayContent
    {
        public TrackingContent()
            : base([])
        {
        }

        public bool IsDisposed { get; private set; }

        protected override void Dispose(bool disposing)
        {
            IsDisposed = true;
            base.Dispose(disposing);
        }
    }
}
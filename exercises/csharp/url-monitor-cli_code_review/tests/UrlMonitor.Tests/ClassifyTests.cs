using Xunit;
using UrlMonitor;

namespace UrlMonitor.Tests;

public class ClassifyTests
{
    [Fact]
    public void Http200_NoError_ReturnsUp()
    {
        var result = new CheckResult(200, null, 150.0);
        Assert.Equal(Status.Up, Checker.Classify(result));
    }

    [Theory]
    [InlineData(301)]
    [InlineData(404)]
    [InlineData(500)]
    [InlineData(503)]
    public void NonOkHttpStatus_NoError_ReturnsDown(int httpStatus)
    {
        var result = new CheckResult(httpStatus, null, 200.0);
        Assert.Equal(Status.Down, Checker.Classify(result));
    }

    [Theory]
    [InlineData("timeout")]
    [InlineData("connection_refused")]
    [InlineData("dns_resolution_failed")]
    [InlineData("ssl_error")]
    public void AnyError_ReturnsDown(string error)
    {
        var result = new CheckResult(0, error, 5000.0);
        Assert.Equal(Status.Down, Checker.Classify(result));
    }

    [Fact]
    public void Http0_NoError_ReturnsDown()
    {
        var result = new CheckResult(0, null, 100.0);
        Assert.Equal(Status.Down, Checker.Classify(result));
    }

    [Fact]
    public void Http200_WithError_ReturnsDown()
    {
        // Even if we somehow got a 200 but also an error, it should be Down
        var result = new CheckResult(200, "partial_read", 300.0);
        Assert.Equal(Status.Down, Checker.Classify(result));
    }

    [Fact]
    public void StatusName_Up_ReturnsLowercase()
    {
        Assert.Equal("up", Checker.StatusName(Status.Up));
    }

    [Fact]
    public void StatusName_Down_ReturnsLowercase()
    {
        Assert.Equal("down", Checker.StatusName(Status.Down));
    }

    [Fact]
    public void StatusName_Unknown_ReturnsLowercase()
    {
        Assert.Equal("unknown", Checker.StatusName(Status.Unknown));
    }
}

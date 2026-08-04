using System.Text.Json;
using System.Text.Json.Serialization;
using Xunit;
using UrlMonitor;

namespace UrlMonitor.Tests;

public class StatsTests
{
    [Fact]
    public void RecordCheck_AccumulatesCounts()
    {
        var stats = new UrlStats();

        // Record 3 successful checks
        Stats.RecordCheck(stats, new CheckResult(200, null, 100.0), Status.Up);
        Stats.RecordCheck(stats, new CheckResult(200, null, 120.0), Status.Up);
        Stats.RecordCheck(stats, new CheckResult(200, null, 80.0), Status.Up);

        // Record 1 failed check
        Stats.RecordCheck(stats, new CheckResult(503, null, 200.0), Status.Down);

        // Record 1 error check
        Stats.RecordCheck(stats, new CheckResult(0, "timeout", 5000.0), Status.Down);

        Assert.Equal(5, stats.TotalChecks);
        Assert.Equal(3, stats.UpChecks);
        Assert.Equal(2, stats.DownChecks);
        Assert.Equal(3, stats.HttpStatus[200]);
        Assert.Equal(1, stats.HttpStatus[503]);
        Assert.Single(stats.Errors);
        Assert.Equal(1, stats.Errors["timeout"]);
    }

    [Fact]
    public void RecordCheck_MultipleErrors_CountsSeparately()
    {
        var stats = new UrlStats();

        Stats.RecordCheck(stats, new CheckResult(0, "timeout", 5000.0), Status.Down);
        Stats.RecordCheck(stats, new CheckResult(0, "timeout", 5000.0), Status.Down);
        Stats.RecordCheck(stats, new CheckResult(0, "connection_refused", 100.0), Status.Down);

        Assert.Equal(3, stats.TotalChecks);
        Assert.Equal(0, stats.UpChecks);
        Assert.Equal(3, stats.DownChecks);
        Assert.Equal(2, stats.Errors["timeout"]);
        Assert.Equal(1, stats.Errors["connection_refused"]);
    }

    [Fact]
    public void FormatUrlStats_ContainsExpectedStrings()
    {
        var stats = new UrlStats
        {
            TotalChecks = 120,
            UpChecks = 118,
            DownChecks = 2,
            HttpStatus = new Dictionary<int, long> { { 200, 118 }, { 503, 2 } },
            Errors = new Dictionary<string, long>()
        };

        var output = Stats.FormatUrlStats("https://example.com", stats);

        Assert.Contains("https://example.com", output);
        Assert.Contains("checks=120", output);
        Assert.Contains("up=118", output);
        Assert.Contains("down=2", output);
        Assert.Contains("uptime=98.3%", output);
        Assert.Contains("200: 118", output);
        Assert.Contains("503: 2", output);
        Assert.Contains("errors  (none)", output);
    }

    [Fact]
    public void FormatUrlStats_WithErrors_ShowsErrors()
    {
        var stats = new UrlStats
        {
            TotalChecks = 5,
            UpChecks = 3,
            DownChecks = 2,
            HttpStatus = new Dictionary<int, long> { { 200, 3 } },
            Errors = new Dictionary<string, long> { { "timeout", 2 } }
        };

        var output = Stats.FormatUrlStats("https://example.com", stats);

        Assert.Contains("timeout: 2", output);
    }

    [Fact]
    public void StateRoundTrip_PreservesData()
    {
        var store = new StateStore
        {
            Version = 1,
            Urls = new Dictionary<string, UrlState>
            {
                ["https://example.com"] = new UrlState
                {
                    Status = Status.Up,
                    LastChecked = "2026-08-04T10:00:00Z",
                    Stats = new UrlStats
                    {
                        TotalChecks = 50,
                        UpChecks = 48,
                        DownChecks = 2,
                        HttpStatus = new Dictionary<int, long> { { 200, 48 }, { 503, 2 } },
                        Errors = new Dictionary<string, long>()
                    }
                },
                ["https://httpbin.org/status/200"] = new UrlState
                {
                    Status = Status.Down,
                    LastChecked = "2026-08-04T10:00:00Z",
                    Stats = new UrlStats
                    {
                        TotalChecks = 10,
                        UpChecks = 8,
                        DownChecks = 2,
                        HttpStatus = new Dictionary<int, long> { { 200, 8 }, { 500, 2 } },
                        Errors = new Dictionary<string, long> { { "timeout", 1 } }
                    }
                }
            }
        };

        var tempFile = Path.GetTempFileName();
        try
        {
            State.SaveState(tempFile, store);
            var loaded = State.LoadState(tempFile);

            Assert.Equal(store.Version, loaded.Version);
            Assert.Equal(store.Urls.Count, loaded.Urls.Count);

            foreach (var (url, expectedState) in store.Urls)
            {
                Assert.True(loaded.Urls.ContainsKey(url));
                var loadedState = loaded.Urls[url];

                Assert.Equal(expectedState.Status, loadedState.Status);
                Assert.Equal(expectedState.LastChecked, loadedState.LastChecked);
                Assert.Equal(expectedState.Stats.TotalChecks, loadedState.Stats.TotalChecks);
                Assert.Equal(expectedState.Stats.UpChecks, loadedState.Stats.UpChecks);
                Assert.Equal(expectedState.Stats.DownChecks, loadedState.Stats.DownChecks);

                foreach (var (code, count) in expectedState.Stats.HttpStatus)
                {
                    Assert.Equal(count, loadedState.Stats.HttpStatus[code]);
                }

                foreach (var (error, count) in expectedState.Stats.Errors)
                {
                    Assert.Equal(count, loadedState.Stats.Errors[error]);
                }
            }
        }
        finally
        {
            File.Delete(tempFile);
        }
    }

    [Fact]
    public void LoadState_MissingFile_ReturnsEmptyStore()
    {
        var store = State.LoadState("/tmp/nonexistent_test_state_file.json");

        Assert.NotNull(store);
        Assert.Empty(store.Urls);
    }

    [Fact]
    public void LoadState_CorruptFile_ReturnsEmptyStore()
    {
        var tempFile = Path.GetTempFileName();
        try
        {
            File.WriteAllText(tempFile, "{ this is not valid json !!!");
            var store = State.LoadState(tempFile);

            Assert.NotNull(store);
            Assert.Empty(store.Urls);
        }
        finally
        {
            File.Delete(tempFile);
        }
    }

    [Fact]
    public void LoadState_LegacyWithoutStats_LoadsWithZeroedStats()
    {
        // Simulate a legacy state file that has URL entries but no "stats" key
        var legacyJson = """
        {
            "version": 1,
            "urls": {
                "https://example.com": {
                    "status": "up",
                    "last_checked": "2026-08-04T10:00:00Z"
                }
            }
        }
        """;

        var tempFile = Path.GetTempFileName();
        try
        {
            File.WriteAllText(tempFile, legacyJson);
            var store = State.LoadState(tempFile);

            Assert.NotNull(store);
            Assert.Single(store.Urls);

            var state = store.Urls["https://example.com"];
            Assert.Equal(Status.Up, state.Status);
            Assert.Equal(0, state.Stats.TotalChecks);
            Assert.Equal(0, state.Stats.UpChecks);
            Assert.Equal(0, state.Stats.DownChecks);
            Assert.Empty(state.Stats.HttpStatus);
            Assert.Empty(state.Stats.Errors);
        }
        finally
        {
            File.Delete(tempFile);
        }
    }

    [Fact]
    public void Reconcile_AddsNewUrls()
    {
        var store = new StateStore();
        var config = new MonitorConfig
        {
            Urls = new List<UrlSpec>
            {
                new("https://example.com"),
                new("https://httpbin.org/status/200")
            }
        };

        State.Reconcile(store, config);

        Assert.Equal(2, store.Urls.Count);
        Assert.True(store.Urls.ContainsKey("https://example.com"));
        Assert.True(store.Urls.ContainsKey("https://httpbin.org/status/200"));
        Assert.Equal(Status.Unknown, store.Urls["https://example.com"].Status);
    }

    [Fact]
    public void Reconcile_RemovesStaleUrls()
    {
        var store = new StateStore
        {
            Urls = new Dictionary<string, UrlState>
            {
                ["https://example.com"] = new UrlState { Status = Status.Up },
                ["https://removed.com"] = new UrlState { Status = Status.Down }
            }
        };

        var config = new MonitorConfig
        {
            Urls = new List<UrlSpec> { new("https://example.com") }
        };

        State.Reconcile(store, config);

        Assert.Single(store.Urls);
        Assert.True(store.Urls.ContainsKey("https://example.com"));
        Assert.False(store.Urls.ContainsKey("https://removed.com"));
    }
}

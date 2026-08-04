namespace UrlMonitor;

public static class Monitor
{
    /// <summary>
    /// Run the main monitoring loop until cancellation is requested.
    /// </summary>
    public static void Run(
        MonitorConfig config,
        StateStore store,
        string stateFilePath,
        bool verbose,
        CancellationToken cancellationToken)
    {
        Notifier.LogInfo($"Starting URL monitor with {config.Urls.Count} URLs, interval={config.CheckIntervalSeconds}s");

        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                RunCheckCycle(config, store, verbose);

                // Save state after each cycle
                State.SaveState(stateFilePath, store);

                // Interruptible sleep
                try
                {
                    Task.Delay(
                        TimeSpan.FromSeconds(config.CheckIntervalSeconds),
                        cancellationToken
                    ).Wait();
                }
                catch (AggregateException ex) when (ex.InnerException is TaskCanceledException)
                {
                    break;
                }
            }
        }
        catch (OperationCanceledException)
        {
            // Expected on shutdown
        }

        Notifier.LogInfo("Shutting down...");

        // Final save
        State.SaveState(stateFilePath, store);

        // Print final stats
        Console.WriteLine();
        Console.Write(Stats.FormatAllStats(store));
    }

    /// <summary>
    /// Run one check cycle across all configured URLs.
    /// </summary>
    private static void RunCheckCycle(MonitorConfig config, StateStore store, bool verbose)
    {
        foreach (var urlSpec in config.Urls)
        {
            if (!store.Urls.ContainsKey(urlSpec.Url))
            {
                store.Urls[urlSpec.Url] = new UrlState();
            }

            var urlState = store.Urls[urlSpec.Url];
            var previousStatus = urlState.Status;

            // Perform the check
            var result = Checker.Check(urlSpec.Url, urlSpec.TimeoutSeconds);
            var newStatus = Checker.Classify(result);

            // Update state
            urlState.Status = newStatus;
            urlState.LastChecked = Notifier.Iso8601Now();

            // Record stats
            Stats.RecordCheck(urlState.Stats, result, newStatus);

            // Emit transition or verbose log
            bool isTransition = previousStatus != newStatus;
            bool isFirstCheck = previousStatus == Status.Unknown;

            if (isTransition && !isFirstCheck)
            {
                Notifier.EmitTransition(urlSpec.Url, newStatus, result);
            }
            else if (verbose)
            {
                Notifier.EmitVerboseCheck(urlSpec.Url, newStatus, result);
            }
        }
    }
}

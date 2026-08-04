# URL Monitor CLI (C#)

A CLI tool that monitors a list of URLs for uptime, checks them on a configurable schedule, and prints notifications when a site goes down or comes back up. This is the C# solution to the url-monitor-cli exercise.

## Build

```bash
dotnet build
```

## Run

```bash
dotnet run --project src/UrlMonitor -- --config config/example.yaml
```

### CLI Options

```
--config <path>       Path to YAML config file (default: config.yaml)
--state-file <path>   Path to state JSON file (default: derived from config)
--verbose             Log every check, not just transitions
--stats               Print accumulated stats and exit
--help                Show help message
```

## Test

```bash
dotnet test
```

## Architecture

| Module       | Responsibility                                           |
|-------------|----------------------------------------------------------|
| Config.cs   | CLI argument parsing, YAML config loading and validation |
| Checker.cs  | HTTP health checks, status classification (Up/Down)      |
| Monitor.cs  | Main check loop, cancellation, interruptible sleep       |
| Notifier.cs | Console logging, transition emission, timestamps         |
| State.cs    | JSON sidecar load/save (atomic write), state reconciliation |
| Stats.cs    | Per-URL counter accumulation, stats formatting           |
| Program.cs  | Entry point, wiring                                      |

## Config Format

```yaml
check_interval_seconds: 30

urls:
  - url: https://example.com
    timeout_seconds: 10
  - url: https://httpbin.org/status/200
    timeout_seconds: 5
```

## Exit Codes

- `0` - Success
- `1` - Config error
- `2` - CLI argument error

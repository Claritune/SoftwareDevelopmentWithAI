# Questions: URL Monitor CLI (C#)

## Scope

1. Is the CLI meant to run as a long-lived foreground process (like `tail -f`) or should it also support a one-shot "check once and exit" mode?
2. Should the tool support monitoring URLs concurrently (parallel HTTP requests) or is sequential per-cycle sufficient for the initial version?
3. Is `--stats` the only query mode, or will we need `--status` to show current Up/Down per URL?

## Technical

4. Should we use `System.CommandLine` for argument parsing or keep it manual to match the C++ solution's simplicity?
5. For HTTP checks, should we use `HttpClient` directly or wrap it with `IHttpClientFactory`? The latter is best practice in ASP.NET but adds DI complexity for a CLI tool.
6. Should the main loop be fully async (`async Task Main`, `await` throughout) or is synchronous acceptable for a simple CLI?
7. For YAML parsing, `YamlDotNet` is the de facto standard -- any reason to consider alternatives?
8. Should state reconciliation preserve stats for URLs that are temporarily removed from config and then re-added?

## Output

9. Should notification output go to stdout only, or should errors go to stderr? What about the stats summary on shutdown?
10. Should timestamps use the system local timezone or always UTC?
11. Should transition messages include the previous status (e.g., "DOWN -> UP") or just the new status?

## Testing

12. What level of test coverage is expected? Unit tests for classification + stats, or also integration tests with a mock HTTP server?

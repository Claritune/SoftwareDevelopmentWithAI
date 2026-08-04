using UrlMonitor;

using var httpClient = new HttpClient();
using var shutdownSource = new CancellationTokenSource();

Console.CancelKeyPress += (_, eventArgs) =>
{
	eventArgs.Cancel = true;
	shutdownSource.Cancel();
};

var application = new CliApplication(httpClient);
return await application.RunAsync(args, shutdownSource.Token);

namespace FifteenPuzzle.Core;

public sealed class GameTimer(IMonotonicClock clock)
{
    private TimeSpan _accumulated;
    private long _intervalStart;
    private bool _isStopped;

    public TimeSpan Elapsed => IsRunning
        ? _accumulated + clock.GetElapsedTime(_intervalStart, clock.GetTimestamp())
        : _accumulated;

    public bool IsStarted { get; private set; }

    public bool IsRunning { get; private set; }

    public void Start()
    {
        if (IsStarted)
        {
            return;
        }

        IsStarted = true;
        IsRunning = true;
        _intervalStart = clock.GetTimestamp();
    }

    public void Pause()
    {
        if (!IsRunning)
        {
            return;
        }

        _accumulated += clock.GetElapsedTime(_intervalStart, clock.GetTimestamp());
        IsRunning = false;
    }

    public void Resume()
    {
        if (!IsStarted || IsRunning || _isStopped)
        {
            return;
        }

        _intervalStart = clock.GetTimestamp();
        IsRunning = true;
    }

    public void Stop()
    {
        if (!IsStarted || _isStopped)
        {
            return;
        }

        Pause();
        _isStopped = true;
    }

    public void Reset()
    {
        _accumulated = TimeSpan.Zero;
        _intervalStart = 0;
        _isStopped = false;
        IsStarted = false;
        IsRunning = false;
    }
}
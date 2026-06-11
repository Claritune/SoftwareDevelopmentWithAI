import httpx

from url_monitor.checker import check, is_failure


def _make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_check_success_200():
    def handler(request):
        return httpx.Response(200)

    client = _make_client(handler)
    result = check("https://example.com", timeout=5, client=client)
    client.close()

    assert result.success is True
    assert result.status_code == 200
    assert result.error is None
    assert result.response_time_ms is not None
    assert is_failure(result) is False


def test_check_failure_404():
    def handler(request):
        return httpx.Response(404)

    client = _make_client(handler)
    result = check("https://example.com", timeout=5, client=client)
    client.close()

    assert result.success is False
    assert result.status_code == 404
    assert is_failure(result) is True


def test_check_failure_503():
    def handler(request):
        return httpx.Response(503)

    client = _make_client(handler)
    result = check("https://example.com", timeout=5, client=client)
    client.close()

    assert result.success is False
    assert result.status_code == 503


def test_check_connection_error():
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    client = _make_client(handler)
    result = check("https://example.com", timeout=5, client=client)
    client.close()

    assert result.success is False
    assert result.status_code is None
    assert result.error is not None
    assert "Connection refused" in result.error


def test_check_follows_redirect():
    def handler(request):
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"Location": "/ok"})
        return httpx.Response(200)

    client = _make_client(handler)
    result = check("https://example.com/redirect", timeout=5, client=client)
    client.close()

    assert result.success is True
    assert result.status_code == 200



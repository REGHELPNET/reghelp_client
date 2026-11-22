"""HTTP 503 on a getStatus read is temporary: the SDK repeats the request."""

from typing import List, Optional

import httpx
import pytest

from reghelp_client import (
    ExternalServiceError,
    MaintenanceModeError,
    RegHelpClient,
    ServiceDisabledError,
    ServiceUnavailableError,
    TaskStatus,
)
from reghelp_client.exceptions import TimeoutError as RegHelpTimeoutError


def _client(http: httpx.AsyncClient, **kwargs: object) -> RegHelpClient:
    kwargs.setdefault("retry_delay", 0.001)
    return RegHelpClient("test-key", http_client=http, **kwargs)  # type: ignore[arg-type]


def _unavailable(retry_after: Optional[str] = None) -> httpx.Response:
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    return httpx.Response(503, json={"detail": "EXTERNAL_ERROR"}, headers=headers)


async def test_get_status_retries_503_then_succeeds() -> None:
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if len(calls) < 3:
            return _unavailable()
        return httpx.Response(200, json={"id": "t1", "status": "done", "token": "tok"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with _client(http, max_retries=3) as client:
            status = await client.get_push_status("t1")
    assert status.status == TaskStatus.DONE
    assert calls == ["/push/getStatus"] * 3


async def test_get_status_503_exhausted_raises_typed_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _unavailable("0")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with _client(http, max_retries=2) as client:
            with pytest.raises(ServiceUnavailableError) as info:
                await client.get_push_status("t1")
    assert calls == 3
    assert info.value.status_code == 503
    assert info.value.retry_after == 0.0
    # Callers that already catch the broader class keep working.
    assert isinstance(info.value, ExternalServiceError)


async def test_get_status_retries_non_json_503_from_proxy() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, text="no available server")
        return httpx.Response(200, json={"id": "t1", "status": "pending"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with _client(http, max_retries=1) as client:
            status = await client.get_turnstile_status("t1")
    assert calls == 2
    assert status.status == TaskStatus.PENDING


@pytest.mark.parametrize(
    "code,error_type",
    [("SERVICE_DISABLED", ServiceDisabledError), ("MAINTENANCE_MODE", MaintenanceModeError)],
)
async def test_get_status_does_not_retry_deliberate_503(code: str, error_type: type) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"detail": code})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with _client(http, max_retries=3) as client:
            with pytest.raises(error_type):
                await client.get_push_status("t1")
    assert calls == 1


async def test_paid_request_is_not_retried_on_503() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.path == "/turnstile/getToken"
        return _unavailable("0")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with _client(http, max_retries=3) as client:
            with pytest.raises(ExternalServiceError) as info:
                await client.get_turnstile_token(
                    url="https://example.com", site_key="0x4AAAAAAA"
                )
    assert calls == 1
    assert not isinstance(info.value, ServiceUnavailableError)


async def test_retry_after_header_sets_the_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    import reghelp_client.client as client_module

    pauses: List[float] = []

    async def fake_sleep(seconds: float) -> None:
        pauses.append(seconds)

    monkeypatch.setattr(client_module.asyncio, "sleep", fake_sleep)
    responses = [_unavailable("2"), _unavailable("9999"), _unavailable("soon")]

    def handler(request: httpx.Request) -> httpx.Response:
        if responses:
            return responses.pop(0)
        return httpx.Response(200, json={"id": "t1", "status": "done"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with _client(http, max_retries=3, retry_delay=0.5) as client:
            await client.get_push_status("t1")
    # header value, capped header value, then exponential fallback (0.5 * 2**2)
    assert pauses == [2.0, RegHelpClient.MAX_RETRY_AFTER, 2.0]


async def test_wait_for_result_survives_a_long_503_window() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls <= 5:
            return _unavailable("0")
        return httpx.Response(200, json={"id": "t1", "status": "done", "token": "tok"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        # max_retries=0: every 503 reaches the wait loop, which must keep polling.
        async with _client(http, max_retries=0) as client:
            result = await client.wait_for_result("t1", "push", timeout=5, poll_interval=0.001)
    assert result.status == TaskStatus.DONE
    assert calls == 6


async def test_wait_for_result_times_out_when_503_never_ends() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _unavailable("0")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with _client(http, max_retries=0) as client:
            with pytest.raises(RegHelpTimeoutError) as info:
                await client.wait_for_result("t1", "push", timeout=0.05, poll_interval=0.005)
    assert isinstance(info.value.__cause__, ServiceUnavailableError)


async def test_wait_for_result_timeout_bounds_request_level_retries() -> None:
    import asyncio

    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _unavailable("2")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        # Default-like client: the request layer would sleep 3 x Retry-After.
        async with _client(http, max_retries=3) as client:
            loop = asyncio.get_event_loop()
            started = loop.time()
            with pytest.raises(RegHelpTimeoutError):
                await client.wait_for_result("t1", "push", timeout=0.2, poll_interval=0.05)
            elapsed = loop.time() - started
    assert elapsed < 1.0, elapsed
    assert calls == 1

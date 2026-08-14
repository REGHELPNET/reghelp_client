from __future__ import annotations

import asyncio
import inspect
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import httpx

import reghelp_client
from reghelp_client import AppDevice, RegHelpClient
from reghelp_client.models import EmailType

PAID_CREATE_METHODS = (
    "get_push_token",
    "get_voip_token",
    "get_email",
    "get_integrity_token",
    "get_attestation_token",
    "get_recaptcha_mobile_token",
    "get_turnstile_token",
)


class _Response:
    text = ""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _RetryHttpClient:
    def __init__(self, first: str | Exception = "429") -> None:
        self.calls: list[dict[str, str]] = []
        self.first = first

    async def get(
        self,
        _url: str,
        *,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> _Response:
        del params
        self.calls.append(dict(headers or {}))
        if len(self.calls) == 1:
            if isinstance(self.first, Exception):
                raise self.first
            return _Response(429, {"detail": "RATE_LIMIT"})
        return _Response(
            200,
            {
                "status": "wait",
                "id": "task-1",
                "service": "push",
                "product": "push",
                "price": 1.0,
                "balance": 9.0,
            },
        )


def test_every_paid_create_method_exposes_and_wires_request_id() -> None:
    for method_name in PAID_CREATE_METHODS:
        method = getattr(RegHelpClient, method_name)
        parameter = inspect.signature(method).parameters["request_id"]
        assert parameter.default is None
        source = inspect.getsource(method)
        assert "headers=self._idempotency_headers(request_id)" in source


def test_every_paid_create_method_sends_explicit_key_at_runtime() -> None:
    token_payload = {
        "status": "wait",
        "id": "task-1",
        "service": "service",
        "product": "product",
        "price": 1.0,
        "balance": 9.0,
    }
    email_payload = {**token_payload, "email": "mail@example.test"}
    client = RegHelpClient("api-key")
    request = AsyncMock(return_value=token_payload)
    client._make_request = request

    async def _run() -> None:
        calls = (
            (client.get_push_token, ("tg", AppDevice.IOS), token_payload),
            (client.get_voip_token, ("tg",), token_payload),
            (
                client.get_email,
                ("tg", AppDevice.IOS, "+10000000000", EmailType.ICLOUD),
                email_payload,
            ),
            (
                client.get_integrity_token,
                ("tg", AppDevice.ANDROID, "nonce-value", 1),
                token_payload,
            ),
            (client.get_attestation_token, ("challenge",), token_payload),
            (
                client.get_recaptcha_mobile_token,
                ("tg", AppDevice.IOS, "app-key", "login"),
                token_payload,
            ),
            (
                client.get_turnstile_token,
                ("https://example.test", "site-key"),
                token_payload,
            ),
        )
        for index, (method, args, payload) in enumerate(calls):
            request.return_value = payload
            key = f"intent-{index}"
            await method(*args, request_id=key)
            assert request.call_args.kwargs["headers"] == {"Idempotency-Key": key}

    asyncio.run(_run())


def test_generated_key_is_valid_and_internal_retry_reuses_it() -> None:
    http = _RetryHttpClient()
    client = RegHelpClient(
        "api-key",
        base_url="https://key-api.test",
        http_client=http,
        max_retries=1,
        retry_delay=0,
    )

    asyncio.run(client.get_push_token("tg", AppDevice.IOS))

    assert len(http.calls) == 2
    first = http.calls[0]["Idempotency-Key"]
    UUID(first)
    assert http.calls[1]["Idempotency-Key"] == first


def test_timeout_and_network_retries_reuse_explicit_key() -> None:
    failures = (
        httpx.ReadTimeout(
            "timeout", request=httpx.Request("GET", "https://key-api.test/push/getToken")
        ),
        httpx.ConnectError(
            "network", request=httpx.Request("GET", "https://key-api.test/push/getToken")
        ),
    )
    for failure in failures:
        http = _RetryHttpClient(failure)
        client = RegHelpClient(
            "api-key",
            base_url="https://key-api.test",
            http_client=http,
            max_retries=1,
            retry_delay=0,
        )
        asyncio.run(
            client.get_push_token(
                "tg",
                AppDevice.IOS,
                request_id="stable-network-intent",
            )
        )
        assert [call["Idempotency-Key"] for call in http.calls] == [
            "stable-network-intent",
            "stable-network-intent",
        ]


def test_explicit_key_is_preserved_verbatim() -> None:
    assert RegHelpClient._idempotency_headers("intent-42") == {
        "Idempotency-Key": "intent-42"
    }


def test_release_version_is_consistent() -> None:
    root = Path(__file__).parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)
    assert match is not None
    assert reghelp_client.__version__ == match.group(1)
    assert f"## [{reghelp_client.__version__}]" in changelog

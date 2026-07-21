from __future__ import annotations

import asyncio
from typing import Any

import pytest

from reghelp_client import (
    BoundAttestationStatusResponse,
    BoundIntegrityStatusResponse,
    InvalidParameterError,
    RegHelpClient,
)


class _Response:
    status_code = 200
    text = ""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _HttpClient:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = list(payloads)
        # (method, url, query params, request headers)
        self.calls: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> _Response:
        self.calls.append(("GET", url, dict(params), dict(headers or {})))
        return _Response(self.payloads.pop(0))

    async def post(
        self,
        url: str,
        *,
        params: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> _Response:
        self.calls.append(("POST", url, dict(params), dict(headers or {})))
        return _Response(self.payloads.pop(0))


def test_provider_registrar_contract_uses_public_sdk_methods() -> None:
    profile = {
        "profile_id": "profile-1",
        "model": "Pixel 8",
        "device": "shiba",
        "brand": "google",
        "manufacturer": "Google",
        "product": "shiba",
        "fingerprint": "google/shiba/shiba:15/build/user/release-keys",
        "build_id": "build",
        "android_sdk": 35,
        "android_version": "15",
        "hardware": "shiba",
        "board": "shiba",
        "total_ram": 7_528_964_096,
    }
    http = _HttpClient(
        [
            {"status": "ok", "app": "wa", "params": {"version": "current"}},
            {
                "status": "profile_bound",
                "provider": "whatsapp",
                "appName": "wa",
                "registrarSessionId": "session-1",
                "profile_id": "profile-1",
                "device_profile": profile,
            },
            {
                "status": "bound",
                "registrarSessionId": "session-1",
                "profile_id": "profile-1",
                "device_profile": profile,
            },
            {"id": "integrity-1", "status": "wait"},
            {
                "id": "integrity-1",
                "status": "done",
                "token": "integrity-token",
                "profile_id": "profile-1",
                "device_profile": profile,
            },
            {"id": "attestation-1", "status": "wait"},
            {
                "id": "attestation-1",
                "status": "done",
                "authorization": "authorization-b64",
                "leafPrivateKeyB64": "leaf-b64",
                "keyboxDeviceId": "keybox-1",
                "profile_id": "profile-1",
                "device_profile": profile,
            },
        ]
    )
    client = RegHelpClient("api-key", base_url="https://key-api.test", http_client=http)

    async def _run() -> None:
        app_params = await client.get_provider_app_params("whatsapp", "wa")
        binding = await client.start_registrar(
            "whatsapp", "session-1", "wa", 262708500
        )
        current = await client.get_registrar_binding("whatsapp", "session-1")
        integrity_task = await client.get_bound_integrity_token(
            "whatsapp",
            "session-1",
            "wa",
            "nonce-value",
            262708500,
            token_type="std",
        )
        integrity = await client.get_bound_integrity_status(
            "whatsapp", "integrity-1", "session-1"
        )
        attestation_task = await client.get_bound_attestation_token(
            "whatsapp",
            "session-1",
            "challenge",
            "wa",
            262708500,
            "signature-digest",
        )
        attestation = await client.get_bound_attestation_status(
            "whatsapp", "attestation-1", "session-1"
        )

        assert app_params.params == {"version": "current"}
        assert binding.profile_id == current.profile_id == "profile-1"
        assert integrity_task.id == "integrity-1"
        assert isinstance(integrity, BoundIntegrityStatusResponse)
        assert integrity.token == "integrity-token"
        assert attestation_task.id == "attestation-1"
        assert isinstance(attestation, BoundAttestationStatusResponse)
        assert attestation.authorization == "authorization-b64"

    asyncio.run(_run())

    assert [call[1] for call in http.calls] == [
        "https://key-api.test/whatsapp/appParams",
        "https://key-api.test/whatsapp/registrar/start",
        "https://key-api.test/whatsapp/registrar/getBinding",
        "https://key-api.test/whatsapp/integrity/getToken",
        "https://key-api.test/whatsapp/integrity/getStatus",
        "https://key-api.test/whatsapp/attestation/getToken",
        "https://key-api.test/whatsapp/attestation/getStatus",
    ]
    assert http.calls[3][2]["type"] == "std"
    assert http.calls[3][2]["registrarSessionId"] == "session-1"
    assert http.calls[5][2]["apkSignatureSha256"] == "signature-digest"
    assert all(call[2]["apiKey"] == "api-key" for call in http.calls)
    # request_id was not supplied, so no requestId query and no idempotency header
    assert all("requestId" not in call[2] for call in http.calls)
    assert all("Idempotency-Key" not in call[3] for call in http.calls)


def test_request_id_travels_as_idempotency_key_header() -> None:
    http = _HttpClient(
        [
            {
                "status": "profile_bound",
                "registrarSessionId": "session-1",
                "profile_id": "profile-1",
                "device_profile": {},
            },
            {"id": "integrity-1", "status": "wait"},
            {"id": "attestation-1", "status": "wait"},
        ]
    )
    client = RegHelpClient("api-key", base_url="https://key-api.test", http_client=http)

    async def _run() -> None:
        await client.start_registrar(
            "whatsapp", "session-1", "wa", 262708500, request_id="req-start"
        )
        await client.get_bound_integrity_token(
            "whatsapp",
            "session-1",
            "wa",
            "nonce-value",
            262708500,
            token_type="std",
            request_id="req-integrity",
        )
        await client.get_bound_attestation_token(
            "whatsapp",
            "session-1",
            "challenge",
            "wa",
            262708500,
            "signature-digest",
            request_id="req-attestation",
        )

    asyncio.run(_run())

    # request_id must NOT leak into the query string on any paid task call
    assert all("requestId" not in call[2] for call in http.calls)
    # ...it travels as the canonical Idempotency-Key header instead
    assert http.calls[0][1] == "https://key-api.test/whatsapp/registrar/start"
    assert http.calls[0][3]["Idempotency-Key"] == "req-start"
    assert http.calls[1][1] == "https://key-api.test/whatsapp/integrity/getToken"
    assert http.calls[1][3]["Idempotency-Key"] == "req-integrity"
    assert http.calls[2][1] == "https://key-api.test/whatsapp/attestation/getToken"
    assert http.calls[2][3]["Idempotency-Key"] == "req-attestation"


def test_blank_request_id_sends_no_idempotency_header() -> None:
    http = _HttpClient(
        [
            {
                "status": "profile_bound",
                "registrarSessionId": "session-1",
                "profile_id": "profile-1",
                "device_profile": {},
            }
        ]
    )
    client = RegHelpClient("api-key", base_url="https://key-api.test", http_client=http)

    asyncio.run(
        client.start_registrar(
            "whatsapp", "session-1", "wa", 262708500, request_id="   "
        )
    )

    assert "requestId" not in http.calls[0][2]
    assert "Idempotency-Key" not in http.calls[0][3]


def test_get_registrar_binding_parses_not_found_without_raising() -> None:
    http = _HttpClient(
        [
            {
                "status": "not_found",
                "registrarSessionId": "session-unknown",
                "profile_id": None,
                "device_profile": {},
            }
        ]
    )
    client = RegHelpClient("api-key", base_url="https://key-api.test", http_client=http)

    binding = asyncio.run(
        client.get_registrar_binding("whatsapp", "session-unknown")
    )

    assert binding.status == "not_found"
    assert binding.profile_id is None
    assert binding.device_profile == {}
    assert binding.registrarSessionId == "session-unknown"
    assert http.calls[0][1] == "https://key-api.test/whatsapp/registrar/getBinding"


def test_provider_path_rejects_injection_before_http() -> None:
    http = _HttpClient([])
    client = RegHelpClient("api-key", http_client=http)

    with pytest.raises(InvalidParameterError, match="provider"):
        asyncio.run(client.get_provider_app_params("../whatsapp", "wa"))

    assert http.calls == []

from datetime import timedelta

import httpx
import pytest
from pydantic import ValidationError

from reghelp_client import (
    EmailStockResponse,
    EmailType,
    ExternalServiceError,
    RegHelpClient,
    ServiceDisabledError,
    UnauthorizedError,
)


@pytest.mark.parametrize("app_name", ["tg", "ig", "wa", "telegram"])
@pytest.mark.parametrize("count", [0, 37493])
async def test_stock_request_and_response(app_name: str, count: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/email/getStock"
        assert dict(request.url.params) == {
            "appName": app_name, "type": "icloud", "apiKey": "test-key"
        }
        assert "Idempotency-Key" not in request.headers
        return httpx.Response(200, json={
            "status": "success", "service": "icloud", "appName": "tg" if app_name == "telegram" else app_name,
            "count": count, "updatedAt": "2026-09-10T14:51:26.989000Z",
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with RegHelpClient("test-key", http_client=http) as client:
            stock = await client.get_email_stock(app_name, EmailType.ICLOUD)
    assert isinstance(stock, EmailStockResponse)
    assert stock.count == count
    assert stock.appName == ("tg" if app_name == "telegram" else app_name)
    assert stock.service == EmailType.ICLOUD
    assert stock.updatedAt.utcoffset() == timedelta(0)


@pytest.mark.parametrize("code,http_status,error_type", [
    ("SERVICE_DISABLED", 503, ServiceDisabledError),
    ("UPSTREAM_ERROR", 503, ExternalServiceError),
    ("EXTERNAL_ERROR", 503, ExternalServiceError),
    ("UNAUTHORIZED", 401, UnauthorizedError),
])
async def test_stock_errors(code: str, http_status: int, error_type: type) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["type"] == "gmail"
        return httpx.Response(http_status, json={"detail": code})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with RegHelpClient("test-key", http_client=http) as client:
            with pytest.raises(error_type):
                await client.get_email_stock("tg", EmailType.GMAIL)


@pytest.mark.parametrize("count", [None, -1, 1.5, True, "10"])
def test_invalid_count_is_not_reported_as_zero(count: object) -> None:
    with pytest.raises(ValidationError):
        EmailStockResponse.model_validate({
            "status": "success", "service": "icloud", "appName": "tg",
            "count": count, "updatedAt": "2026-09-10T14:51:26Z",
        })

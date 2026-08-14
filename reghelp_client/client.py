"""
Main client for the REGHelp API.

Provides an asynchronous interface to work with all REGHelp services.
"""

import asyncio
import logging
import re
from types import TracebackType
from typing import Any, Dict, Optional, Type, Union, cast
from uuid import uuid4

import httpx

from .exceptions import (
    ExternalServiceError,
    InsufficientFundsError,
    InvalidParameterError,
    MaintenanceModeError,
    NetworkError,
    RateLimitError,
    RegHelpError,
    ServiceDisabledError,
    TaskNotFoundError,
    UnauthorizedError,
)
from .exceptions import (
    TimeoutError as RegHelpTimeoutError,
)
from .models import (
    AppDevice,
    AppParamsResponse,
    AttestationStatusResponse,
    BalanceResponse,
    BoundArtifactTaskResponse,
    BoundAttestationStatusResponse,
    BoundIntegrityStatusResponse,
    EmailGetResponse,
    EmailStatusResponse,
    EmailType,
    IntegrityStatusResponse,
    IntegrityTokenType,
    ProxyConfig,
    PushStatusResponse,
    PushStatusType,
    RecaptchaMobileStatusResponse,
    RegistrarBindingResponse,
    TaskStatus,
    TokenResponse,
    TurnstileStatusResponse,
    VoipStatusResponse,
)

logger = logging.getLogger(__name__)


class RegHelpClient:
    """
    Asynchronous client for working with the REGHelp API.

    Supports all services: Push, Email, Integrity, Turnstile, VoIP Push, Recaptcha Mobile.
    """

    DEFAULT_BASE_URL = "https://api.reghelp.net"
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0
    _PROVIDER_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Initialize the client.

        Args:
            api_key: API key for authentication
            base_url: Base API URL (default https://api.reghelp.net)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries on errors
            retry_delay: Delay between retries in seconds
            http_client: Custom HTTP client (optional)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Create HTTP client if not provided
        if http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                follow_redirects=True,
            )
            self._owns_http_client = True
        else:
            self._http_client = http_client
            self._owns_http_client = False

    async def __aenter__(self) -> "RegHelpClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client."""
        if self._owns_http_client:
            await self._http_client.aclose()

    def _build_url(self, endpoint: str) -> str:
        """Build full URL for endpoint."""
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    @classmethod
    def _provider_endpoint(cls, provider: str, endpoint: str) -> str:
        """Build a provider-scoped API path without permitting path injection."""
        normalized = str(provider or "").strip().lower()
        if not cls._PROVIDER_RE.fullmatch(normalized):
            raise InvalidParameterError(
                "provider must match ^[a-z][a-z0-9_-]{0,63}$"
            )
        return f"/{normalized}/{endpoint.lstrip('/')}"

    @staticmethod
    def _required_text(value: str, name: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise InvalidParameterError(f"{name} is required")
        return normalized

    @staticmethod
    def _positive_version_code(value: int) -> int:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
            or value > 2_147_483_647
        ):
            raise InvalidParameterError(
                "app_version_code must be an int in range 1..2_147_483_647"
            )
        return value

    def _build_params(self, **kwargs: Any) -> Dict[str, str]:
        """Build request parameters with API key."""
        params = {"apiKey": self.api_key}
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, bool):
                    params[key] = str(value).lower()
                else:
                    params[key] = str(value)
        return params

    @staticmethod
    def _idempotency_headers(request_id: Optional[str]) -> Dict[str, str]:
        """Build the ``Idempotency-Key`` header block for paid task creation.

        The public ``request_id=`` argument is the canonical idempotency token.
        It travels as an HTTP header (``Idempotency-Key``) rather than a query
        parameter so the Key API idempotency middleware can dedupe repeated
        paid task creation. When the caller omits ``request_id``, generate one
        once for this logical SDK call; ``_make_request`` then preserves the
        same header across its internal retries. Callers retrying the whole SDK
        method after an ambiguous network outcome should pass their original
        ``request_id`` explicitly.
        """
        token = str(request_id or "").strip()
        return {"Idempotency-Key": token or str(uuid4())}

    def _map_error_code(
        self, error_id: str, status_code: int, task_id: Optional[str] = None
    ) -> RegHelpError:
        """Map error codes to corresponding exceptions."""
        if status_code == 401:
            return UnauthorizedError()

        if status_code == 402 or error_id == "INSUFFICIENT_FUNDS":
            return InsufficientFundsError()

        if error_id in ("UNAUTHORIZED", "NOT_AUTHORIZED"):
            return UnauthorizedError()

        if error_id == "RATE_LIMIT":
            return RateLimitError()
        elif error_id == "SERVICE_DISABLED":
            return ServiceDisabledError("unknown")
        elif error_id == "MAINTENANCE_MODE":
            return MaintenanceModeError()
        elif error_id == "TASK_NOT_FOUND":
            if task_id:
                return TaskNotFoundError(task_id)
            else:
                # If task_id is unknown, use generic error
                return RegHelpError("Task not found", status_code=status_code)
        elif error_id == "INVALID_PARAM":
            return InvalidParameterError()
        elif error_id == "EXTERNAL_ERROR":
            return ExternalServiceError()
        else:
            return RegHelpError(f"Unknown error: {error_id}", status_code=status_code)

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        task_id: Optional[str] = None,
        *,
        allow_error_status: bool = False,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute HTTP request with error handling and retry logic.

        ``method`` is GET by default (every legacy endpoint in this client
        ships query-string params over GET). Pass ``method="POST"`` for
        endpoints that mutate server state — params still go on the query
        string, body stays empty, which matches FastAPI's behaviour when
        all parameters are declared via ``Query(...)``.

        ``headers`` carries request-scoped HTTP headers (e.g. the
        ``Idempotency-Key`` used by paid task-creation endpoints). It is
        preserved verbatim across every retry so an idempotent request keeps
        the same key on a 429/timeout/network re-send.
        """
        url = self._build_url(endpoint)
        request_params = self._build_params(**(params or {}))

        try:
            # Mask apiKey in logs
            masked_params = dict(request_params)
            if "apiKey" in masked_params:
                api_key_value = masked_params["apiKey"]
                if isinstance(api_key_value, str) and len(api_key_value) > 8:
                    masked_params["apiKey"] = f"{api_key_value[:4]}***{api_key_value[-4:]}"
                else:
                    masked_params["apiKey"] = "***"

            logger.debug(f"Making {method} request to {url} with params: {masked_params}")

            if method.upper() == "POST":
                response = await self._http_client.post(
                    url, params=request_params, headers=headers
                )
            else:
                response = await self._http_client.get(
                    url, params=request_params, headers=headers
                )

            # Check status code
            if response.status_code == 200:
                try:
                    data: Dict[str, Any] = response.json()

                    # Check for errors in response
                    if data.get("status") == "error" and not allow_error_status:
                        error_id = data.get("id") or data.get("detail", "UNKNOWN_ERROR")
                        raise self._map_error_code(error_id, response.status_code, task_id)

                    return data

                except ValueError as e:
                    raise RegHelpError(f"Invalid JSON response: {e}") from e

            elif response.status_code == 429:
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2**retry_count))
                    return await self._make_request(
                        endpoint,
                        params,
                        retry_count + 1,
                        task_id,
                        allow_error_status=allow_error_status,
                        method=method,
                        headers=headers,
                    )
                else:
                    raise RateLimitError()

            elif response.status_code == 401:
                raise UnauthorizedError()

            else:
                # Try to get error details from response
                try:
                    error_data = response.json()
                    error_id = error_data.get("id") or error_data.get("detail", "HTTP_ERROR")
                    raise self._map_error_code(error_id, response.status_code, task_id)
                except ValueError as e:
                    raise RegHelpError(
                        f"HTTP {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    ) from e

        except httpx.TimeoutException as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (2**retry_count))
                return await self._make_request(
                    endpoint,
                    params,
                    retry_count + 1,
                    task_id,
                    allow_error_status=allow_error_status,
                    method=method,
                    headers=headers,
                )
            else:
                raise RegHelpTimeoutError(self.timeout) from e

        except httpx.RequestError as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (2**retry_count))
                return await self._make_request(
                    endpoint,
                    params,
                    retry_count + 1,
                    task_id,
                    allow_error_status=allow_error_status,
                    method=method,
                    headers=headers,
                )
            else:
                raise NetworkError(f"Network error: {e}", original_error=e) from e

    # Health check
    async def health_check(self) -> bool:
        """
        Check API availability.

        Returns:
            True if API is available
        """
        try:
            # Health endpoint doesn't require API key
            url = self._build_url("/health")
            response = await self._http_client.get(url)
            return response.status_code == 200
        except Exception:
            return False

    # Balance operations
    async def get_balance(self) -> BalanceResponse:
        """
        Get current account balance.

        Returns:
            Balance information
        """
        data = await self._make_request("/balance")
        return BalanceResponse(**data)

    # Provider registrar operations
    async def get_provider_app_params(
        self,
        provider: str,
        app_name: str,
    ) -> AppParamsResponse:
        """Get server-maintained opaque app parameters for a provider flavor."""
        app = self._required_text(app_name, "app_name")
        data = await self._make_request(
            self._provider_endpoint(provider, "/appParams"),
            {"app": app},
        )
        return AppParamsResponse(**data)

    async def start_registrar(
        self,
        provider: str,
        registrar_session_id: str,
        app_name: str,
        app_version_code: int,
        *,
        request_id: Optional[str] = None,
    ) -> RegistrarBindingResponse:
        """Idempotently bind an Android profile to a client-owned registrar session."""
        params: Dict[str, Any] = {
            "registrarSessionId": self._required_text(
                registrar_session_id, "registrar_session_id"
            ),
            "appName": self._required_text(app_name, "app_name"),
            "appVersionCode": self._positive_version_code(app_version_code),
        }
        data = await self._make_request(
            self._provider_endpoint(provider, "/registrar/start"),
            params,
            headers=self._idempotency_headers(request_id),
        )
        return RegistrarBindingResponse(**data)

    async def get_registrar_binding(
        self,
        provider: str,
        registrar_session_id: str,
    ) -> RegistrarBindingResponse:
        """Read the profile binding for a client-owned registrar session.

        An unknown session is a normal, readable outcome — the Key API returns
        ``{"status": "not_found", "registrarSessionId": ..., "profile_id": null,
        "device_profile": {}}`` with HTTP 200. This is parsed into a
        :class:`RegistrarBindingResponse` with ``status == "not_found"`` rather
        than raised as an error, so callers can branch on the status field.
        """
        data = await self._make_request(
            self._provider_endpoint(provider, "/registrar/getBinding"),
            {
                "registrarSessionId": self._required_text(
                    registrar_session_id, "registrar_session_id"
                )
            },
            allow_error_status=True,
        )
        return RegistrarBindingResponse(**data)

    async def get_bound_integrity_token(
        self,
        provider: str,
        registrar_session_id: str,
        app_name: str,
        nonce: str,
        app_version_code: int,
        *,
        token_type: Optional[Union[IntegrityTokenType, str]] = None,
        request_id: Optional[str] = None,
    ) -> BoundArtifactTaskResponse:
        """Create a Play Integrity task on the registrar session's bound profile."""
        params: Dict[str, Any] = {
            "registrarSessionId": self._required_text(
                registrar_session_id, "registrar_session_id"
            ),
            "appName": self._required_text(app_name, "app_name"),
            "nonce": self._required_text(nonce, "nonce"),
            "appVersionCode": self._positive_version_code(app_version_code),
        }
        if token_type is not None:
            raw_type = (
                token_type.value if isinstance(token_type, IntegrityTokenType) else str(token_type)
            )
            normalized_type = raw_type.strip().lower()
            if normalized_type in {"std", "standard", "express"}:
                params["type"] = "std"
            elif normalized_type in {"classic", "default"}:
                params["type"] = "classic"
            else:
                raise InvalidParameterError(
                    f"Unsupported integrity token_type: {raw_type!r}. "
                    "Expected 'classic' or 'std'."
                )
        data = await self._make_request(
            self._provider_endpoint(provider, "/integrity/getToken"),
            params,
            headers=self._idempotency_headers(request_id),
        )
        return BoundArtifactTaskResponse(**data)

    async def get_bound_integrity_status(
        self,
        provider: str,
        task_id: str,
        registrar_session_id: str,
    ) -> BoundIntegrityStatusResponse:
        """Poll a bound Play Integrity task without losing provider error payloads."""
        task = self._required_text(task_id, "task_id")
        data = await self._make_request(
            self._provider_endpoint(provider, "/integrity/getStatus"),
            {
                "id": task,
                "registrarSessionId": self._required_text(
                    registrar_session_id, "registrar_session_id"
                ),
            },
            task_id=task,
            allow_error_status=True,
        )
        return BoundIntegrityStatusResponse(**data)

    async def get_bound_attestation_token(
        self,
        provider: str,
        registrar_session_id: str,
        authkey: str,
        app_name: str,
        app_version_code: int,
        apk_signature_sha256: str,
        *,
        enc: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> BoundArtifactTaskResponse:
        """Create a Key Attestation task on the registrar session's bound profile."""
        params: Dict[str, Any] = {
            "registrarSessionId": self._required_text(
                registrar_session_id, "registrar_session_id"
            ),
            "authkey": self._required_text(authkey, "authkey"),
            "appName": self._required_text(app_name, "app_name"),
            "appVersionCode": self._positive_version_code(app_version_code),
            "apkSignatureSha256": self._required_text(
                apk_signature_sha256, "apk_signature_sha256"
            ),
        }
        if enc:
            params["enc"] = enc
        data = await self._make_request(
            self._provider_endpoint(provider, "/attestation/getToken"),
            params,
            headers=self._idempotency_headers(request_id),
        )
        return BoundArtifactTaskResponse(**data)

    async def get_bound_attestation_status(
        self,
        provider: str,
        task_id: str,
        registrar_session_id: str,
    ) -> BoundAttestationStatusResponse:
        """Poll a bound Key Attestation task without losing rebind markers."""
        task = self._required_text(task_id, "task_id")
        data = await self._make_request(
            self._provider_endpoint(provider, "/attestation/getStatus"),
            {
                "id": task,
                "registrarSessionId": self._required_text(
                    registrar_session_id, "registrar_session_id"
                ),
            },
            task_id=task,
            allow_error_status=True,
        )
        return BoundAttestationStatusResponse(**data)

    # Push operations
    async def get_push_token(
        self,
        app_name: str,
        app_device: AppDevice,
        app_version: Optional[str] = None,
        app_build: Optional[str] = None,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> TokenResponse:
        """
        Create task for getting push token.

        Args:
            app_name: Application name (tg, tg_beta, tg_x, tgiOS)
            app_device: Device type (iOS/Android)
            app_version: Application version (optional)
            app_build: Build number (optional)
            ref: Referral tag (optional)
            webhook: URL for webhook notifications (optional)
            request_id: Stable idempotency key for retrying the same paid task intent.

        Returns:
            Information about created task
        """
        params = {
            "appName": app_name,
            "appDevice": app_device.value,
        }

        if app_version:
            params["appVersion"] = app_version
        if app_build:
            params["appBuild"] = app_build
        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook

        data = await self._make_request(
            "/push/getToken",
            params,
            headers=self._idempotency_headers(request_id),
        )
        return TokenResponse(**data)

    async def get_push_status(self, task_id: str) -> PushStatusResponse:
        """
        Get push token task status.

        Args:
            task_id: Task ID

        Returns:
            Task status
        """
        data = await self._make_request(
            "/push/getStatus",
            {"id": task_id},
            task_id=task_id,
            allow_error_status=True,
        )
        return PushStatusResponse(**data)

    async def set_push_status(
        self,
        task_id: str,
        phone_number: str,
        status: PushStatusType,
    ) -> bool:
        """
        Set status of failed push token task (for refund).

        Args:
            task_id: Task ID
            phone_number: Phone number in E.164 format
            status: Failure reason

        Returns:
            True if operation successful
        """
        params = {
            "id": task_id,
            "number": phone_number,
            "status": status.value,
        }

        data = await self._make_request(
            "/push/setStatus",
            params,
            allow_error_status=True,
        )
        if data.get("status") == "success" and "balance" in data:
            return True

        if data.get("status") == "error" and "balance" in data:
            return True

        if data.get("status") == "success":
            if data.get("price") is not None and data.get("balance") is not None:
                return True

        return False

    # VoIP Push operations
    async def get_voip_token(
        self,
        app_name: str,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> TokenResponse:
        """
        Create task for getting VoIP push token.

        Args:
            app_name: Application name
            ref: Referral tag (optional)
            webhook: URL for webhook notifications (optional)
            request_id: Stable idempotency key for retrying the same paid task intent.

        Returns:
            Information about created task
        """
        params = {"appName": app_name}

        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook

        data = await self._make_request(
            "/pushVoip/getToken",
            params,
            headers=self._idempotency_headers(request_id),
        )
        return TokenResponse(**data)

    async def get_voip_status(self, task_id: str) -> VoipStatusResponse:
        """
        Get VoIP push token task status.

        Args:
            task_id: Task ID

        Returns:
            Task status
        """
        data = await self._make_request(
            "/pushVoip/getStatus",
            {"id": task_id},
            task_id=task_id,
            allow_error_status=True,
        )
        return VoipStatusResponse(**data)

    # Email operations
    async def get_email(
        self,
        app_name: str,
        app_device: AppDevice,
        phone: str,
        email_type: EmailType,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> EmailGetResponse:
        """
        Get temporary email address.

        Args:
            app_name: Application name
            app_device: Device type
            phone: Phone number in E.164 format
            email_type: Email provider type (icloud/gmail)
            ref: Referral tag (optional)
            webhook: URL for webhook notifications (optional)
            request_id: Stable idempotency key for retrying the same paid task intent.

        Returns:
            Information about email address
        """
        params = {
            "appName": app_name,
            "appDevice": app_device.value,
            "phone": phone,
            "type": email_type.value,
        }

        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook

        data = await self._make_request(
            "/email/getEmail",
            params,
            headers=self._idempotency_headers(request_id),
        )
        return EmailGetResponse(**data)

    async def get_email_status(self, task_id: str) -> EmailStatusResponse:
        """
        Get email task status.

        Args:
            task_id: Task ID

        Returns:
            Task status with verification code
        """
        data = await self._make_request(
            "/email/getStatus",
            {"id": task_id},
            task_id=task_id,
            allow_error_status=True,
        )
        return EmailStatusResponse(**data)

    # Integrity operations
    async def get_integrity_token(
        self,
        app_name: str,
        app_device: AppDevice,
        nonce: str,
        app_version_code: int,
        *,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
        token_type: Optional[Union[IntegrityTokenType, str]] = None,
        request_id: Optional[str] = None,
    ) -> TokenResponse:
        """
        Get Google Play Integrity token.

        Args:
            app_name: Application name (e.g. ``tg``, ``wa``, ``instagram``).
            app_device: Device type (currently only ``AppDevice.ANDROID`` is
                meaningful for Play Integrity).
            nonce: Nonce string (URL-safe Base64, 16-500 characters).
            app_version_code: **Mandatory** APK ``versionCode`` of the target
                app. Required since Key API v2026-05. Must match the version
                used when the package is signed by Play. Range: 1..2_147_483_647.
            ref: Referral tag (optional).
            webhook: URL for webhook notifications (optional).
            request_id: Stable idempotency key for retrying the same paid task intent.
            token_type: Integrity token type. Omit or pass
                :attr:`IntegrityTokenType.CLASSIC` for Classic flow
                (``MEETS_STRONG_INTEGRITY``). Pass
                :attr:`IntegrityTokenType.STD` for Standard/Express flow
                (``MEETS_DEVICE_INTEGRITY``, faster).

        Returns:
            Information about the created task.
        """
        if not isinstance(app_version_code, int) or isinstance(app_version_code, bool):
            raise InvalidParameterError("app_version_code must be a positive integer")
        if app_version_code < 1 or app_version_code > 2_147_483_647:
            raise InvalidParameterError(
                "app_version_code must be in range 1..2_147_483_647"
            )

        params: Dict[str, Any] = {
            "appName": app_name,
            "appDevice": app_device.value,
            "nonce": nonce,
            "appVersionCode": app_version_code,
        }

        # Optional type parameter. Classic is the default on the server side,
        # so only forward `type` for the Standard/Express flow.
        if token_type is not None:
            raw_type = (
                token_type.value if isinstance(token_type, IntegrityTokenType) else str(token_type)
            )
            normalized = raw_type.strip().lower()
            if normalized in {"std", "standard", "express"}:
                params["type"] = "std"
            elif normalized in {"", "classic", "default"}:
                pass  # Classic is the default — omit `type` on the wire.
            else:
                raise InvalidParameterError(
                    f"Unsupported integrity token_type: {raw_type!r}. "
                    "Expected 'classic' or 'std'."
                )

        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook

        data = await self._make_request(
            "/integrity/getToken",
            params,
            headers=self._idempotency_headers(request_id),
        )
        return TokenResponse(**data)

    async def get_integrity_status(self, task_id: str) -> IntegrityStatusResponse:
        """
        Get integrity token task status.

        Args:
            task_id: Task ID

        Returns:
            Task status
        """
        data = await self._make_request(
            "/integrity/getStatus",
            {"id": task_id},
            task_id=task_id,
            allow_error_status=True,
        )
        return IntegrityStatusResponse(**data)

    # Attestation operations (Android Key Attestation)
    async def get_attestation_token(
        self,
        authkey: str,
        *,
        verified_boot_key: Optional[str] = None,
        verified_boot_hash: Optional[str] = None,
        apk_version_code: Optional[int] = None,
        package_name: Optional[str] = None,
        apk_signature_sha256: Optional[str] = None,
        enc: Optional[str] = None,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> TokenResponse:
        """Issue an Android Key Attestation cert chain.

        Wraps a TEE-bound keybox from the server-side pool and returns an
        X.509 chain with KeyMint attestation extension (OID 1.3.6.1.4.1.11129.2.1.17).
        Package name and signature default to a stock app fingerprint, but
        every field is overridable for use against any Google-issued challenge.

        Args:
            authkey: Challenge nonce from Google. Hex or base64, 4-512 chars.
                This is the **only mandatory** field — every other knob has a
                sensible default on the attestation-server side.
            verified_boot_key: Optional 32-byte hex; defaults to a zero
                placeholder normalised by the server.
            verified_boot_hash: Optional 32-byte hex; same default behaviour.
            apk_version_code: Override the embedded APK versionCode.
                Range 1..2_147_483_647.
            package_name: Override the embedded package name.
            apk_signature_sha256: Override the embedded APK signature digest
                (32-byte hex).
            enc: Optional base64 payload to ECDSA-sign with the leaf key.
                Returned as ``sign`` in the status response.
            ref: Referral tag.
            webhook: Webhook URL fired when the task completes.
            request_id: Stable idempotency key for retrying the same paid task intent.

        Returns:
            :class:`TokenResponse` with ``id`` to poll for the cert chain.
        """
        params: Dict[str, Any] = {"authkey": authkey}
        if verified_boot_key:
            params["verifiedBootKey"] = verified_boot_key
        if verified_boot_hash:
            params["verifiedBootHash"] = verified_boot_hash
        if apk_version_code is not None:
            if (
                not isinstance(apk_version_code, int)
                or isinstance(apk_version_code, bool)
                or apk_version_code < 1
                or apk_version_code > 2_147_483_647
            ):
                raise InvalidParameterError(
                    "apk_version_code must be an int in range 1..2_147_483_647"
                )
            params["apkVersionCode"] = apk_version_code
        if package_name:
            params["packageName"] = package_name
        if apk_signature_sha256:
            params["apkSignatureSha256"] = apk_signature_sha256
        if enc:
            params["enc"] = enc
        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook

        data = await self._make_request(
            "/attestation/getToken",
            params,
            headers=self._idempotency_headers(request_id),
        )
        return TokenResponse(**data)

    async def get_attestation_status(self, task_id: str) -> AttestationStatusResponse:
        """Fetch attestation task status.

        When ``status == TaskStatus.DONE`` the response includes
        ``authorization`` (base64 DER cert chain), ``leafPrivateKeyB64``,
        ``keyboxDeviceId`` and — if the original request carried ``enc`` —
        the ECDSA ``sign``.
        """
        data = await self._make_request(
            "/attestation/getStatus",
            {"id": task_id},
            task_id=task_id,
            allow_error_status=True,
        )
        return AttestationStatusResponse(**data)

    # Recaptcha Mobile operations
    async def get_recaptcha_mobile_token(
        self,
        app_name: str,
        app_device: AppDevice,
        app_key: str,
        app_action: str,
        proxy: Optional[ProxyConfig] = None,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> TokenResponse:
        """
        Solve mobile reCAPTCHA challenge.

        Args:
            app_name: Application name
            app_device: Device type
            app_key: reCAPTCHA key
            app_action: Action (e.g., "login")
            proxy: Proxy configuration (optional)
            ref: Referral tag (optional)
            webhook: URL for webhook notifications (optional)
            request_id: Stable idempotency key for retrying the same paid task intent.

        Returns:
            Information about created task
        """
        params = {
            "appName": app_name,
            "appDevice": app_device.value,
            "appKey": app_key,
            "appAction": app_action,
        }

        if proxy is not None:
            params.update(proxy.to_dict())

        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook

        data = await self._make_request(
            "/RecaptchaMobile/getToken",
            params,
            headers=self._idempotency_headers(request_id),
        )
        return TokenResponse(**data)

    async def get_recaptcha_mobile_status(self, task_id: str) -> RecaptchaMobileStatusResponse:
        """
        Get Recaptcha Mobile task status.

        Args:
            task_id: Task ID

        Returns:
            Task status
        """
        data = await self._make_request(
            "/RecaptchaMobile/getStatus",
            {"id": task_id},
            task_id=task_id,
            allow_error_status=True,
        )
        return RecaptchaMobileStatusResponse(**data)

    # Turnstile operations
    async def get_turnstile_token(
        self,
        url: str,
        site_key: str,
        action: Optional[str] = None,
        cdata: Optional[str] = None,
        proxy: Optional[str] = None,
        actor: Optional[str] = None,
        scope: Optional[str] = None,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> TokenResponse:
        """
        Solve Cloudflare Turnstile challenge.

        Args:
            url: Page URL with widget
            site_key: Turnstile site key
            action: Expected action (optional)
            cdata: Custom data (optional)
            proxy: Proxy in scheme://host:port format (optional)
            actor: Actor identifier (optional)
            scope: Scope value (optional)
            ref: Referral tag (optional)
            webhook: URL for webhook notifications (optional)
            request_id: Stable idempotency key for retrying the same paid task intent.

        Returns:
            Information about created task
        """
        params = {
            "url": url,
            "siteKey": site_key,
        }

        if action:
            params["action"] = action
        if cdata:
            params["cdata"] = cdata
        if proxy:
            params["proxy"] = proxy
        if actor:
            params["actor"] = actor
        if scope:
            params["scope"] = scope
        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook

        data = await self._make_request(
            "/turnstile/getToken",
            params,
            headers=self._idempotency_headers(request_id),
        )
        return TokenResponse(**data)

    async def get_turnstile_status(self, task_id: str) -> TurnstileStatusResponse:
        """
        Get Turnstile task status.

        Args:
            task_id: Task ID

        Returns:
            Task status
        """
        data = await self._make_request(
            "/turnstile/getStatus",
            {"id": task_id},
            task_id=task_id,
            allow_error_status=True,
        )
        return TurnstileStatusResponse(**data)

    # Utility methods
    async def wait_for_result(
        self,
        task_id: str,
        service: str,
        timeout: float = 180.0,
        poll_interval: float = 2.0,
    ) -> Union[
        PushStatusResponse,
        EmailStatusResponse,
        IntegrityStatusResponse,
        RecaptchaMobileStatusResponse,
        TurnstileStatusResponse,
        VoipStatusResponse,
        AttestationStatusResponse,
    ]:
        """
        Wait for task completion with automatic polling.

        Args:
            task_id: Task ID
            service: Service type ('push', 'email', 'integrity', 'recaptcha', 'turnstile', 'voip')
            timeout: Maximum wait time in seconds
            poll_interval: Interval between checks in seconds

        Returns:
            Task result (even if status=ERROR)

        Raises:
            TimeoutError: If task didn't complete within specified time
            RegHelpError: For other errors
        """
        start_time = asyncio.get_event_loop().time()

        # Map services to status getting methods
        status_methods = {
            "push": self.get_push_status,
            "email": self.get_email_status,
            "integrity": self.get_integrity_status,
            "recaptcha": self.get_recaptcha_mobile_status,
            "turnstile": self.get_turnstile_status,
            "voip": self.get_voip_status,
            "attestation": self.get_attestation_status,
        }

        method = status_methods.get(service)
        if not method:
            raise InvalidParameterError(f"Unknown service: {service}")

        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                raise RegHelpTimeoutError(timeout)

            status_response = await method(task_id)

            if status_response.status in {TaskStatus.DONE, TaskStatus.ERROR}:
                return cast(
                    Union[
                        PushStatusResponse,
                        EmailStatusResponse,
                        IntegrityStatusResponse,
                        RecaptchaMobileStatusResponse,
                        TurnstileStatusResponse,
                        VoipStatusResponse,
                        AttestationStatusResponse,
                    ],
                    status_response,
                )

            await asyncio.sleep(poll_interval)

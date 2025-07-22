"""
Main client for the REGHelp API.

Provides an asynchronous interface to work with all REGHelp services.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union
from urllib.parse import urlencode

import httpx
from pydantic import ValidationError

from .models import (
    BalanceResponse,
    TokenResponse,
    PushStatusResponse,
    EmailGetResponse,
    EmailStatusResponse,
    IntegrityStatusResponse,
    RecaptchaMobileStatusResponse,
    TurnstileStatusResponse,
    VoipStatusResponse,
    TaskStatus,
    AppDevice,
    EmailType,
    PushStatusType,
    ProxyConfig,
    PushTokenRequest,
    EmailRequest,
    IntegrityRequest,
    RecaptchaMobileRequest,
    TurnstileRequest,
    VoipRequest,
    IntegrityTokenType,
)
from .exceptions import (
    RegHelpError,
    RateLimitError,
    ServiceDisabledError,
    MaintenanceModeError,
    TaskNotFoundError,
    InvalidParameterError,
    ExternalServiceError,
    UnauthorizedError,
    NetworkError,
    TimeoutError as RegHelpTimeoutError,
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
        self.base_url = base_url.rstrip('/')
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

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client."""
        if self._owns_http_client:
            await self._http_client.aclose()

    def _build_url(self, endpoint: str) -> str:
        """Build full URL for endpoint."""
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _build_params(self, **kwargs) -> Dict[str, str]:
        """Build request parameters with API key."""
        params = {"apiKey": self.api_key}
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, bool):
                    params[key] = str(value).lower()
                else:
                    params[key] = str(value)
        return params

    def _map_error_code(self, error_id: str, status_code: int) -> RegHelpError:
        """Map error codes to corresponding exceptions."""
        if status_code == 401:
            return UnauthorizedError()
        
        if error_id == "RATE_LIMIT":
            return RateLimitError()
        elif error_id == "SERVICE_DISABLED":
            return ServiceDisabledError("unknown")
        elif error_id == "MAINTENANCE_MODE":
            return MaintenanceModeError()
        elif error_id == "TASK_NOT_FOUND":
            return TaskNotFoundError("unknown")
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
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Execute HTTP request with error handling and retry logic.
        """
        url = self._build_url(endpoint)
        request_params = self._build_params(**(params or {}))
        
        try:
            logger.debug(f"Making request to {url} with params: {request_params}")
            
            response = await self._http_client.get(url, params=request_params)
            
            # Check status code
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check for errors in response
                    if data.get("status") == "error":
                        error_id = data.get("id") or data.get("detail", "UNKNOWN_ERROR")
                        raise self._map_error_code(error_id, response.status_code)
                    
                    return data
                    
                except ValueError as e:
                    raise RegHelpError(f"Invalid JSON response: {e}")
            
            elif response.status_code == 429:
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                    return await self._make_request(endpoint, params, retry_count + 1)
                else:
                    raise RateLimitError()
            
            elif response.status_code == 401:
                raise UnauthorizedError()
            
            else:
                # Try to get error details from response
                try:
                    error_data = response.json()
                    error_id = error_data.get("id") or error_data.get("detail", "HTTP_ERROR")
                    raise self._map_error_code(error_id, response.status_code)
                except ValueError:
                    raise RegHelpError(
                        f"HTTP {response.status_code}: {response.text}",
                        status_code=response.status_code
                    )
                    
        except httpx.TimeoutException:
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                return await self._make_request(endpoint, params, retry_count + 1)
            else:
                raise RegHelpTimeoutError(self.timeout)
        
        except httpx.RequestError as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                return await self._make_request(endpoint, params, retry_count + 1)
            else:
                raise NetworkError(f"Network error: {e}", original_error=e)

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

    # Push operations
    async def get_push_token(
        self,
        app_name: str,
        app_device: AppDevice,
        app_version: Optional[str] = None,
        app_build: Optional[str] = None,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
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
            
        data = await self._make_request("/push/getToken", params)
        return TokenResponse(**data)

    async def get_push_status(self, task_id: str) -> PushStatusResponse:
        """
        Get push token task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status
        """
        data = await self._make_request("/push/getStatus", {"id": task_id})
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
        
        data = await self._make_request("/push/setStatus", params)
        return data.get("status") == "success"

    # VoIP Push operations
    async def get_voip_token(
        self,
        app_name: str,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
    ) -> TokenResponse:
        """
        Create task for getting VoIP push token.
        
        Args:
            app_name: Application name
            ref: Referral tag (optional)
            webhook: URL for webhook notifications (optional)
            
        Returns:
            Information about created task
        """
        params = {"appName": app_name}
        
        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook
            
        data = await self._make_request("/pushVoip/getToken", params)
        return TokenResponse(**data)

    async def get_voip_status(self, task_id: str) -> VoipStatusResponse:
        """
        Get VoIP push token task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status
        """
        data = await self._make_request("/pushVoip/getStatus", {"id": task_id})
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
            
        data = await self._make_request("/email/getEmail", params)
        return EmailGetResponse(**data)

    async def get_email_status(self, task_id: str) -> EmailStatusResponse:
        """
        Get email task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status with verification code
        """
        data = await self._make_request("/email/getStatus", {"id": task_id})
        return EmailStatusResponse(**data)

    # Integrity operations
    async def get_integrity_token(
        self,
        app_name: str,
        app_device: AppDevice,
        nonce: str,
        *,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
        token_type: Optional[IntegrityTokenType] = None,
    ) -> TokenResponse:
        """
        Get Google Play Integrity token.
        
        Args:
            app_name: Application name
            app_device: Device type
            nonce: Nonce string (URL-safe Base64, up to 200 characters)
            ref: Referral tag (optional)
            webhook: URL for webhook notifications (optional)
            
        Returns:
            Information about created task
        """
        params = {
            "appName": app_name,
            "appDevice": app_device.value,
            "nonce": nonce,
        }

        # Optional type parameter for standard Integrity tokens (type=std)
        if token_type is not None:
            params["type"] = (
                token_type.value if isinstance(token_type, IntegrityTokenType) else str(token_type)
            )
        
        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook
            
        data = await self._make_request("/integrity/getToken", params)
        return TokenResponse(**data)

    async def get_integrity_status(self, task_id: str) -> IntegrityStatusResponse:
        """
        Get integrity token task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status
        """
        data = await self._make_request("/integrity/getStatus", {"id": task_id})
        return IntegrityStatusResponse(**data)

    # Recaptcha Mobile operations
    async def get_recaptcha_mobile_token(
        self,
        app_name: str,
        app_device: AppDevice,
        app_key: str,
        app_action: str,
        proxy: ProxyConfig,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
    ) -> TokenResponse:
        """
        Solve mobile reCAPTCHA challenge.
        
        Args:
            app_name: Application name
            app_device: Device type
            app_key: reCAPTCHA key
            app_action: Action (e.g., "login")
            proxy: Proxy configuration
            ref: Referral tag (optional)
            webhook: URL for webhook notifications (optional)
            
        Returns:
            Information about created task
        """
        params = {
            "appName": app_name,
            "appDevice": app_device.value,
            "appKey": app_key,
            "appAction": app_action,
            **proxy.to_dict(),
        }
        
        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook
            
        data = await self._make_request("/RecaptchaMobile/getToken", params)
        return TokenResponse(**data)

    async def get_recaptcha_mobile_status(self, task_id: str) -> RecaptchaMobileStatusResponse:
        """
        Get Recaptcha Mobile task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status
        """
        data = await self._make_request("/RecaptchaMobile/getStatus", {"id": task_id})
        return RecaptchaMobileStatusResponse(**data)

    # Turnstile operations
    async def get_turnstile_token(
        self,
        url: str,
        site_key: str,
        action: Optional[str] = None,
        cdata: Optional[str] = None,
        proxy: Optional[str] = None,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
    ) -> TokenResponse:
        """
        Solve Cloudflare Turnstile challenge.
        
        Args:
            url: Page URL with widget
            site_key: Turnstile site key
            action: Expected action (optional)
            cdata: Custom data (optional)
            proxy: Proxy in scheme://host:port format (optional)
            ref: Referral tag (optional)
            webhook: URL for webhook notifications (optional)
            
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
        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook
            
        data = await self._make_request("/turnstile/getToken", params)
        return TokenResponse(**data)

    async def get_turnstile_status(self, task_id: str) -> TurnstileStatusResponse:
        """
        Get Turnstile task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status
        """
        data = await self._make_request("/turnstile/getStatus", {"id": task_id})
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
    ]:
        """
        Wait for task completion with automatic polling.
        
        Args:
            task_id: Task ID
            service: Service type ('push', 'email', 'integrity', 'recaptcha', 'turnstile', 'voip')
            timeout: Maximum wait time in seconds
            poll_interval: Interval between checks in seconds
            
        Returns:
            Task result
            
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
        }
        
        method = status_methods.get(service)
        if not method:
            raise InvalidParameterError(f"Unknown service: {service}")
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                raise RegHelpTimeoutError(timeout)
            
            status_response = await method(task_id)
            
            if status_response.status == TaskStatus.DONE:
                return status_response
            elif status_response.status == TaskStatus.ERROR:
                raise RegHelpError(f"Task failed: {status_response.message}")
            
            await asyncio.sleep(poll_interval) 
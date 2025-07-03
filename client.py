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
        Инициализация клиента.
        
        Args:
            api_key: API ключ для аутентификации
            base_url: Базовый URL API (по умолчанию https://api.reghelp.net)
            timeout: Таймаут запросов в секундах
            max_retries: Максимальное количество повторов при ошибках
            retry_delay: Задержка между повторами в секундах
            http_client: Пользовательский HTTP клиент (опционально)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Создаем HTTP клиент если не передан
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
        """Закрыть HTTP клиент."""
        if self._owns_http_client:
            await self._http_client.aclose()

    def _build_url(self, endpoint: str) -> str:
        """Построить полный URL для endpoint."""
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _build_params(self, **kwargs) -> Dict[str, str]:
        """Построить параметры запроса с API ключом."""
        params = {"apiKey": self.api_key}
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, bool):
                    params[key] = str(value).lower()
                else:
                    params[key] = str(value)
        return params

    def _map_error_code(self, error_id: str, status_code: int) -> RegHelpError:
        """Маппинг кодов ошибок в соответствующие исключения."""
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
        Выполнить HTTP запрос с обработкой ошибок и retry логикой.
        """
        url = self._build_url(endpoint)
        request_params = self._build_params(**(params or {}))
        
        try:
            logger.debug(f"Making request to {url} with params: {request_params}")
            
            response = await self._http_client.get(url, params=request_params)
            
            # Проверяем статус код
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Проверяем на ошибки в ответе
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
                # Пытаемся получить детали ошибки из ответа
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
        Проверка доступности API.
        
        Returns:
            True если API доступен
        """
        try:
            # Health endpoint не требует API ключа
            url = self._build_url("/health")
            response = await self._http_client.get(url)
            return response.status_code == 200
        except Exception:
            return False

    # Balance operations
    async def get_balance(self) -> BalanceResponse:
        """
        Получить текущий баланс аккаунта.
        
        Returns:
            Информация о балансе
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
        Создать задачу для получения push токена.
        
        Args:
            app_name: Имя приложения (tg, tg_beta, tg_x, tgiOS)
            app_device: Тип устройства (iOS/Android)
            app_version: Версия приложения (опционально)
            app_build: Номер сборки (опционально)
            ref: Реферальная метка (опционально)
            webhook: URL для webhook уведомлений (опционально)
            
        Returns:
            Информация о созданной задаче
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
        Получить статус задачи push токена.
        
        Args:
            task_id: ID задачи
            
        Returns:
            Статус задачи
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
        Установить статус неуспешной задачи push токена (для возврата средств).
        
        Args:
            task_id: ID задачи
            phone_number: Номер телефона в формате E.164
            status: Причина неуспеха
            
        Returns:
            True если операция успешна
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
        Создать задачу для получения VoIP push токена.
        
        Args:
            app_name: Имя приложения
            ref: Реферальная метка (опционально)
            webhook: URL для webhook уведомлений (опционально)
            
        Returns:
            Информация о созданной задаче
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
        Получить статус задачи VoIP push токена.
        
        Args:
            task_id: ID задачи
            
        Returns:
            Статус задачи
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
        Получить временный email адрес.
        
        Args:
            app_name: Имя приложения
            app_device: Тип устройства
            phone: Номер телефона в формате E.164
            email_type: Тип email провайдера (icloud/gmail)
            ref: Реферальная метка (опционально)
            webhook: URL для webhook уведомлений (опционально)
            
        Returns:
            Информация об email адресе
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
        Получить статус задачи email.
        
        Args:
            task_id: ID задачи
            
        Returns:
            Статус задачи с кодом подтверждения
        """
        data = await self._make_request("/email/getStatus", {"id": task_id})
        return EmailStatusResponse(**data)

    # Integrity operations
    async def get_integrity_token(
        self,
        app_name: str,
        app_device: AppDevice,
        nonce: str,
        ref: Optional[str] = None,
        webhook: Optional[str] = None,
    ) -> TokenResponse:
        """
        Получить Google Play Integrity токен.
        
        Args:
            app_name: Имя приложения
            app_device: Тип устройства
            nonce: Nonce строка (URL-safe Base64, до 200 символов)
            ref: Реферальная метка (опционально)
            webhook: URL для webhook уведомлений (опционально)
            
        Returns:
            Информация о созданной задаче
        """
        params = {
            "appName": app_name,
            "appDevice": app_device.value,
            "nonce": nonce,
        }
        
        if ref:
            params["ref"] = ref
        if webhook:
            params["webHook"] = webhook
            
        data = await self._make_request("/integrity/getToken", params)
        return TokenResponse(**data)

    async def get_integrity_status(self, task_id: str) -> IntegrityStatusResponse:
        """
        Получить статус задачи integrity токена.
        
        Args:
            task_id: ID задачи
            
        Returns:
            Статус задачи
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
        Решить мобильную reCAPTCHA задачу.
        
        Args:
            app_name: Имя приложения
            app_device: Тип устройства
            app_key: Ключ reCAPTCHA
            app_action: Действие (например, "login")
            proxy: Конфигурация прокси
            ref: Реферальная метка (опционально)
            webhook: URL для webhook уведомлений (опционально)
            
        Returns:
            Информация о созданной задаче
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
        Получить статус задачи Recaptcha Mobile.
        
        Args:
            task_id: ID задачи
            
        Returns:
            Статус задачи
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
        Решить Cloudflare Turnstile задачу.
        
        Args:
            url: URL страницы с виджетом
            site_key: Site key Turnstile
            action: Ожидаемое действие (опционально)
            cdata: Пользовательские данные (опционально)
            proxy: Прокси в формате scheme://host:port (опционально)
            ref: Реферальная метка (опционально)
            webhook: URL для webhook уведомлений (опционально)
            
        Returns:
            Информация о созданной задаче
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
        Получить статус задачи Turnstile.
        
        Args:
            task_id: ID задачи
            
        Returns:
            Статус задачи
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
        Ожидать выполнения задачи с автоматическим polling.
        
        Args:
            task_id: ID задачи
            service: Тип сервиса ('push', 'email', 'integrity', 'recaptcha', 'turnstile', 'voip')
            timeout: Максимальное время ожидания в секундах
            poll_interval: Интервал между проверками в секундах
            
        Returns:
            Результат задачи
            
        Raises:
            TimeoutError: Если задача не выполнилась за указанное время
            RegHelpError: При других ошибках
        """
        start_time = asyncio.get_event_loop().time()
        
        # Маппинг сервисов на методы получения статуса
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
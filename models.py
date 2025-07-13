"""
Data models for the REGHelp Client Library.

Contains Pydantic models for typing API requests and responses.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class TaskStatus(str, Enum):
    """Task statuses."""
    WAIT = "wait"
    PENDING = "pending" 
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class ProxyType(str, Enum):
    """Proxy types."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class AppDevice(str, Enum):
    """Supported devices."""
    IOS = "iOS"
    ANDROID = "Android"


class EmailType(str, Enum):
    """Email provider types."""
    ICLOUD = "icloud"
    GMAIL = "gmail"


class PushStatusType(str, Enum):
    """Status types for push setStatus."""
    NOSMS = "NOSMS"
    FLOOD = "FLOOD" 
    BANNED = "BANNED"
    TWO_FA = "2FA"


# Base response models
class BaseResponse(BaseModel):
    """Base API response model."""
    status: str = Field(..., description="Статус ответа")


class BalanceResponse(BaseResponse):
    """Response for balance request."""
    balance: float = Field(..., description="Текущий баланс")
    currency: str = Field(..., description="Валюта баланса")


class TokenResponse(BaseResponse):
    """Response for token request."""
    id: str = Field(..., description="ID задачи")
    service: str = Field(..., description="Код сервиса")
    product: str = Field(..., description="Тип продукта")
    price: float = Field(..., description="Цена услуги")
    balance: float = Field(..., description="Оставшийся баланс")


class BaseStatusResponse(BaseModel):
    """Base model for task status."""
    id: str = Field(..., description="ID задачи")
    status: TaskStatus = Field(..., description="Статус задачи")
    message: Optional[str] = Field(None, description="Сообщение об ошибке или статусе")


class PushStatusResponse(BaseStatusResponse):
    """Status of push token task."""
    token: Optional[str] = Field(None, description="Push токен")


class EmailGetResponse(BaseResponse):
    """Response for getting email request."""
    id: str = Field(..., description="ID задачи")
    email: str = Field(..., description="Email адрес")
    service: str = Field(..., description="Тип email сервиса")
    product: str = Field(..., description="Тип продукта")
    price: float = Field(..., description="Цена услуги")
    balance: float = Field(..., description="Оставшийся баланс")


class EmailStatusResponse(BaseStatusResponse):
    """Status of email task."""
    email: Optional[str] = Field(None, description="Email адрес")
    code: Optional[str] = Field(None, description="Код подтверждения")


class IntegrityStatusResponse(BaseStatusResponse):
    """Status of integrity token task."""
    token: Optional[str] = Field(None, description="Integrity токен")


class RecaptchaMobileStatusResponse(BaseStatusResponse):
    """Status of Recaptcha Mobile task."""
    token: Optional[str] = Field(None, description="Recaptcha токен")


class TurnstileStatusResponse(BaseStatusResponse):
    """Status of Turnstile task."""
    token: Optional[str] = Field(None, description="Turnstile токен")


class VoipStatusResponse(BaseStatusResponse):
    """Status of VoIP push task."""
    token: Optional[str] = Field(None, description="VoIP push токен")


# Request parameter models
class ProxyConfig(BaseModel):
    """Proxy configuration."""
    type: ProxyType = Field(..., description="Тип прокси")
    address: str = Field(..., description="Адрес прокси")
    port: int = Field(..., ge=1, le=65535, description="Порт прокси")
    login: Optional[str] = Field(None, description="Логин для прокси")
    password: Optional[str] = Field(None, description="Пароль для прокси")

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для параметров запроса."""
        result = {
            "proxyType": self.type.value,
            "proxyAddress": self.address,
            "proxyPort": self.port,
        }
        if self.login:
            result["proxyLogin"] = self.login
        if self.password:
            result["proxyPassword"] = self.password
        return result


class PushTokenRequest(BaseModel):
    """Параметры запроса push токена."""
    app_name: str = Field(..., description="Имя приложения")
    app_device: AppDevice = Field(..., description="Тип устройства")
    app_version: Optional[str] = Field(None, description="Версия приложения")
    app_build: Optional[str] = Field(None, description="Номер сборки")
    ref: Optional[str] = Field(None, description="Реферальный код")
    webhook: Optional[HttpUrl] = Field(None, description="URL для webhook")


class EmailRequest(BaseModel):
    """Параметры запроса email."""
    app_name: str = Field(..., description="Имя приложения")
    app_device: AppDevice = Field(..., description="Тип устройства")
    phone: str = Field(..., description="Номер телефона в формате E.164")
    email_type: EmailType = Field(..., description="Тип email провайдера")
    ref: Optional[str] = Field(None, description="Реферальный код")
    webhook: Optional[HttpUrl] = Field(None, description="URL для webhook")


class IntegrityRequest(BaseModel):
    """Параметры запроса integrity токена."""
    app_name: str = Field(..., description="Имя приложения")
    app_device: AppDevice = Field(..., description="Тип устройства")
    nonce: str = Field(..., min_length=16, max_length=500, description="Nonce для integrity")
    ref: Optional[str] = Field(None, description="Реферальный код")
    webhook: Optional[HttpUrl] = Field(None, description="URL для webhook")


class RecaptchaMobileRequest(BaseModel):
    """Параметры запроса Recaptcha Mobile токена."""
    app_name: str = Field(..., description="Имя приложения")
    app_device: AppDevice = Field(..., description="Тип устройства")
    app_key: str = Field(..., description="Ключ reCAPTCHA")
    app_action: str = Field(..., description="Действие (например, login)")
    proxy: ProxyConfig = Field(..., description="Конфигурация прокси")
    ref: Optional[str] = Field(None, description="Реферальный код")
    webhook: Optional[HttpUrl] = Field(None, description="URL для webhook")


class TurnstileRequest(BaseModel):
    """Параметры запроса Turnstile токена."""
    url: HttpUrl = Field(..., description="URL страницы с виджетом")
    site_key: str = Field(..., description="Site key Turnstile")
    action: Optional[str] = Field(None, description="Ожидаемое действие")
    cdata: Optional[str] = Field(None, description="Пользовательские данные")
    proxy: Optional[str] = Field(None, description="Прокси в формате scheme://host:port")
    actor: Optional[str] = Field(None, description="Actor")
    scope: Optional[str] = Field(None, description="Scope")
    ref: Optional[str] = Field(None, description="Реферальный код")
    webhook: Optional[HttpUrl] = Field(None, description="URL для webhook")


class VoipRequest(BaseModel):
    """Параметры запроса VoIP push токена."""
    app_name: str = Field(..., description="Имя приложения")
    ref: Optional[str] = Field(None, description="Реферальный код")
    webhook: Optional[HttpUrl] = Field(None, description="URL для webhook") 
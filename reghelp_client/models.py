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


# New Integrity token type enumeration
class IntegrityTokenType(str, Enum):
    """Integrity token types."""
    STD = "std"


class PushStatusType(str, Enum):
    """Status types for push setStatus."""
    NOSMS = "NOSMS"
    FLOOD = "FLOOD" 
    BANNED = "BANNED"
    TWO_FA = "2FA"


# Base response models
class BaseResponse(BaseModel):
    """Base API response model."""
    status: str = Field(..., description="Response status")


class BalanceResponse(BaseResponse):
    """Response for balance request."""
    balance: float = Field(..., description="Current balance")
    currency: str = Field(..., description="Balance currency")


class TokenResponse(BaseResponse):
    """Response for token request."""
    id: str = Field(..., description="Task ID")
    service: str = Field(..., description="Service code")
    product: str = Field(..., description="Product type")
    price: float = Field(..., description="Service price")
    balance: float = Field(..., description="Remaining balance")


class BaseStatusResponse(BaseModel):
    """Base model for task status."""
    id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Task status")
    message: Optional[str] = Field(None, description="Error or status message")


class PushStatusResponse(BaseStatusResponse):
    """Status of push token task."""
    token: Optional[str] = Field(None, description="Push token")


class EmailGetResponse(BaseResponse):
    """Response for getting email request."""
    id: str = Field(..., description="Task ID")
    email: str = Field(..., description="Email address")
    service: str = Field(..., description="Email service type")
    product: str = Field(..., description="Product type")
    price: float = Field(..., description="Service price")
    balance: float = Field(..., description="Remaining balance")


class EmailStatusResponse(BaseStatusResponse):
    """Status of email task."""
    email: Optional[str] = Field(None, description="Email address")
    code: Optional[str] = Field(None, description="Verification code")


class IntegrityStatusResponse(BaseStatusResponse):
    """Status of integrity token task."""
    token: Optional[str] = Field(None, description="Integrity token")


class RecaptchaMobileStatusResponse(BaseStatusResponse):
    """Status of Recaptcha Mobile task."""
    token: Optional[str] = Field(None, description="Recaptcha token")


class TurnstileStatusResponse(BaseStatusResponse):
    """Status of Turnstile task."""
    token: Optional[str] = Field(None, description="Turnstile token")


class VoipStatusResponse(BaseStatusResponse):
    """Status of VoIP push task."""
    token: Optional[str] = Field(None, description="VoIP push token")


# Request parameter models
class ProxyConfig(BaseModel):
    """Proxy configuration."""
    type: ProxyType = Field(..., description="Proxy type")
    address: str = Field(..., min_length=1, max_length=255, description="Proxy address")
    port: int = Field(..., ge=1, le=65535, description="Proxy port")
    login: Optional[str] = Field(None, max_length=128, description="Proxy login")
    password: Optional[str] = Field(None, max_length=256, description="Proxy password")

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
    """Push token request parameters."""
    app_name: str = Field(..., description="Application name")
    app_device: AppDevice = Field(..., description="Device type")
    app_version: Optional[str] = Field(None, description="Application version")
    app_build: Optional[str] = Field(None, description="Build number")
    ref: Optional[str] = Field(None, description="Referral code")
    webhook: Optional[HttpUrl] = Field(None, description="Webhook URL")


class EmailRequest(BaseModel):
    """Email request parameters."""
    app_name: str = Field(..., description="Application name")
    app_device: AppDevice = Field(..., description="Device type")
    phone: str = Field(..., description="Phone number in E.164 format")
    email_type: EmailType = Field(..., description="Email provider type")
    ref: Optional[str] = Field(None, description="Referral code")
    webhook: Optional[HttpUrl] = Field(None, description="Webhook URL")


class IntegrityRequest(BaseModel):
    """Integrity token request parameters."""
    app_name: str = Field(..., description="Application name")
    app_device: AppDevice = Field(..., description="Device type")
    nonce: str = Field(..., min_length=16, max_length=500, description="Nonce for integrity")
    token_type: Optional[IntegrityTokenType] = Field(
        None,
        alias="type",
        description="Integrity token type. For example, 'std' for standard tokens.",
    )
    ref: Optional[str] = Field(None, description="Referral code")
    webhook: Optional[HttpUrl] = Field(None, description="Webhook URL")


class RecaptchaMobileRequest(BaseModel):
    """Recaptcha Mobile token request parameters."""
    app_name: str = Field(..., description="Application name")
    app_device: AppDevice = Field(..., description="Device type")
    app_key: str = Field(..., description="reCAPTCHA key")
    app_action: str = Field(..., description="Action (e.g., login)")
    proxy: ProxyConfig = Field(..., description="Proxy configuration")
    ref: Optional[str] = Field(None, description="Referral code")
    webhook: Optional[HttpUrl] = Field(None, description="Webhook URL")


class TurnstileRequest(BaseModel):
    """Turnstile token request parameters."""
    url: HttpUrl = Field(..., description="Page URL with widget")
    site_key: str = Field(..., description="Turnstile site key")
    action: Optional[str] = Field(None, description="Expected action")
    cdata: Optional[str] = Field(None, description="Custom data")
    proxy: Optional[str] = Field(None, description="Proxy in scheme://host:port format")
    actor: Optional[str] = Field(None, description="Actor")
    scope: Optional[str] = Field(None, description="Scope")
    ref: Optional[str] = Field(None, description="Referral code")
    webhook: Optional[HttpUrl] = Field(None, description="Webhook URL")


class VoipRequest(BaseModel):
    """VoIP push token request parameters."""
    app_name: str = Field(..., description="Application name")
    ref: Optional[str] = Field(None, description="Referral code")
    webhook: Optional[HttpUrl] = Field(None, description="Webhook URL") 
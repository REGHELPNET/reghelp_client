"""
REGHelp Python Client Library

Modern asynchronous library for interacting with the REGHelp Key API.
Supports all services: Push, Email, Integrity, Turnstile, VoIP Push and Recaptcha Mobile.
"""

from .client import RegHelpClient
from .models import (
    BalanceResponse,
    TokenResponse,
    TaskStatus,
    EmailGetResponse,
    PushStatusResponse,
    EmailStatusResponse,
    TurnstileStatusResponse,
    RecaptchaMobileStatusResponse,
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
)

__version__ = "1.1.5"
__all__ = [
    "RegHelpClient",
    "BalanceResponse",
    "TokenResponse", 
    "TaskStatus",
    "EmailGetResponse",
    "PushStatusResponse",
    "EmailStatusResponse",
    "TurnstileStatusResponse",
    "RecaptchaMobileStatusResponse",
    "RegHelpError",
    "RateLimitError",
    "ServiceDisabledError", 
    "MaintenanceModeError",
    "TaskNotFoundError",
    "InvalidParameterError",
    "ExternalServiceError",
    "UnauthorizedError",
] 
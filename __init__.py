"""
REGHelp Python Client Library

Modern asynchronous library for interacting with the REGHelp Key API.
Supports all services: Push, Email, Integrity, Turnstile, VoIP Push and Recaptcha Mobile.
"""

# NOTE: *importlib.metadata* is stdlib since Python 3.8; fallback keeps local dev usable.
from importlib.metadata import PackageNotFoundError, version as _pkg_version  # pylint: disable=import-error

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

# Версия пакета определяется через *importlib.metadata* (setuptools-scm).
try:
    __version__: str = _pkg_version("reghelp-client")
except PackageNotFoundError:  # локальная разработка без установленного дистрибутива
    __version__ = "0.0.0"

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
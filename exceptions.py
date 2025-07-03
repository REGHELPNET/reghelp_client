"""
Exceptions for the REGHelp Client Library.

Contains all custom exceptions used by the library.
"""

from typing import Optional, Any, Dict


class RegHelpError(Exception):
    """Base exception for all REGHelp API errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class RateLimitError(RegHelpError):
    """Exception raised when the rate limit (50 RPS) is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded: 50 requests per second") -> None:
        super().__init__(message, status_code=429)


class ServiceDisabledError(RegHelpError):
    """Exception raised when a service is temporarily disabled by the administrator."""
    
    def __init__(self, service: str) -> None:
        message = f"Service '{service}' is temporarily disabled"
        super().__init__(message, status_code=503)
        self.service = service


class MaintenanceModeError(RegHelpError):
    """Exception raised when the API is in maintenance mode."""
    
    def __init__(self, message: str = "API is in maintenance mode") -> None:
        super().__init__(message, status_code=503)


class TaskNotFoundError(RegHelpError):
    """Exception raised when a task cannot be found."""
    
    def __init__(self, task_id: str) -> None:
        message = f"Task '{task_id}' not found"
        super().__init__(message, status_code=404)
        self.task_id = task_id


class InvalidParameterError(RegHelpError):
    """Exception raised when request parameters are invalid."""
    
    def __init__(self, parameter: Optional[str] = None, message: Optional[str] = None) -> None:
        if message is None:
            message = f"Invalid parameter: {parameter}" if parameter else "Invalid parameters"
        super().__init__(message, status_code=400)
        self.parameter = parameter


class ExternalServiceError(RegHelpError):
    """Exception raised when an external provider returns an error."""
    
    def __init__(self, message: str = "External service error") -> None:
        super().__init__(message, status_code=502)


class UnauthorizedError(RegHelpError):
    """Exception raised for authentication problems (invalid API key)."""
    
    def __init__(self, message: str = "Invalid API key") -> None:
        super().__init__(message, status_code=401)


class NetworkError(RegHelpError):
    """Exception raised for network-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class TimeoutError(RegHelpError):
    """Exception raised when a request times out."""
    
    def __init__(self, timeout: float) -> None:
        message = f"Request timeout after {timeout} seconds"
        super().__init__(message)
        self.timeout = timeout 
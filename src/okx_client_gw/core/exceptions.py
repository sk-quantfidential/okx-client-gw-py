"""Custom exceptions for OKX client gateway."""


class OkxError(Exception):
    """Base exception for OKX client errors."""

    pass


class OkxApiError(OkxError):
    """Exception raised when OKX API returns an error response.

    OKX API returns errors in format: {"code": "50000", "msg": "...", "data": []}
    A successful response has code "0".

    Attributes:
        code: OKX error code (string).
        msg: Error message from OKX.
        data: Additional error data (if any).
    """

    def __init__(
        self,
        code: str,
        msg: str,
        data: list | None = None,
    ):
        self.code = code
        self.msg = msg
        self.data = data or []
        super().__init__(f"OKX API Error [{code}]: {msg}")

    @classmethod
    def from_response(cls, response: dict) -> "OkxApiError":
        """Create an OkxApiError from an OKX API response dict."""
        return cls(
            code=response.get("code", "unknown"),
            msg=response.get("msg", "Unknown error"),
            data=response.get("data", []),
        )


class OkxConnectionError(OkxError):
    """Exception raised when connection to OKX fails.

    Attributes:
        reason: Description of the connection failure.
        url: The URL that failed to connect.
    """

    def __init__(self, reason: str, url: str | None = None):
        self.reason = reason
        self.url = url
        message = f"OKX Connection Error: {reason}"
        if url:
            message += f" (URL: {url})"
        super().__init__(message)


class OkxWebSocketError(OkxError):
    """Exception raised for WebSocket-specific errors.

    Attributes:
        reason: Description of the WebSocket error.
        event: The WebSocket event that caused the error (if any).
    """

    def __init__(self, reason: str, event: str | None = None):
        self.reason = reason
        self.event = event
        message = f"OKX WebSocket Error: {reason}"
        if event:
            message += f" (Event: {event})"
        super().__init__(message)


class OkxRateLimitError(OkxApiError):
    """Exception raised when rate limit is exceeded.

    OKX rate limit error code is typically "50011".
    """

    def __init__(self, msg: str = "Rate limit exceeded"):
        super().__init__(code="50011", msg=msg)


class OkxValidationError(OkxError):
    """Exception raised for validation errors.

    Attributes:
        field: The field that failed validation.
        value: The invalid value.
        reason: Why validation failed.
    """

    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Validation Error: {field}={value!r} - {reason}")

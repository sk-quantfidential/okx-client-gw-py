"""HTTP client protocol interface for OKX API.

Defines the interface for OKX HTTP client implementations using Protocol
for structural subtyping. Extends the base HttpClientProtocol with
OKX-specific response handling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping

    import httpx


@runtime_checkable
class OkxHttpClientProtocol(Protocol):
    """Protocol defining the interface for OKX HTTP clients.

    Extends standard HTTP client interface with OKX-specific response parsing.
    OKX returns responses in the format: {"code": "0", "msg": "", "data": [...]}
    where code "0" indicates success.

    Any class implementing these methods can be used as an OKX HTTP client,
    enabling dependency injection and testing with mock clients.
    """

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Make a raw HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., "/api/v5/market/candles")
            params: Query parameters
            json: JSON body data
            headers: Additional headers

        Returns:
            Raw httpx.Response object

        Raises:
            httpx.HTTPError: On HTTP errors
            httpx.TimeoutException: On timeout
        """
        ...

    async def get(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a GET request.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Raw httpx.Response object
        """
        ...

    async def get_data(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        """Make a GET request and return parsed data.

        Parses OKX response format and extracts the data field.
        Raises OkxApiError if response code is not "0".

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            The "data" field from OKX response (typically a list)

        Raises:
            OkxApiError: If OKX returns an error response (code != "0")
            httpx.HTTPError: On HTTP errors
        """
        ...

    async def __aenter__(self) -> OkxHttpClientProtocol:
        """Enter async context manager.

        Returns:
            Self for use in async with statement
        """
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        ...

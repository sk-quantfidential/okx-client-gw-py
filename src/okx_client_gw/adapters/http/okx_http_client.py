"""OKX HTTP client implementation.

Extends the generic HttpClient from client-gw-core with OKX-specific
response parsing, error handling, and authentication support.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from client_gw_core.adapters.http import HttpClient, HttpClientConfig
from client_gw_core.adapters.http.config import RetryConfig
from client_gw_core.domain.resilience import BackoffConfig, FixedDelayConfig

from okx_client_gw.core.auth import OkxCredentials
from okx_client_gw.core.config import DEFAULT_CONFIG, OkxConfig
from okx_client_gw.core.exceptions import OkxApiError

if TYPE_CHECKING:
    from collections.abc import Mapping

    import httpx


class OkxHttpClient(HttpClient):
    """Async HTTP client for OKX REST API.

    Extends HttpClient from client-gw-core with:
    - OKX response format parsing (code/msg/data)
    - Rate limiting for public endpoints (20 req/sec default)
    - Retry logic for 5xx errors with exponential backoff
    - Optional authentication for private endpoints

    Example (public endpoints):
        async with OkxHttpClient() as client:
            # Raw response
            response = await client.get("/api/v5/market/tickers", params={"instType": "SPOT"})
            data = response.json()

            # Parsed data (raises OkxApiError on error)
            tickers = await client.get_data("/api/v5/market/tickers", params={"instType": "SPOT"})

    Example (private endpoints):
        credentials = OkxCredentials.from_env()
        async with OkxHttpClient(credentials=credentials) as client:
            # Authenticated request
            balance = await client.get_data_auth("/api/v5/account/balance")

    OKX Response Format:
        Success: {"code": "0", "msg": "", "data": [...]}
        Error: {"code": "50000", "msg": "Error message", "data": []}
    """

    # OKX public API rate limits (private is 10 req/sec but we use same limiter)
    DEFAULT_REQUESTS_PER_SECOND = 20.0

    def __init__(
        self,
        config: OkxConfig | None = None,
        *,
        credentials: OkxCredentials | None = None,
        requests_per_second: float | None = None,
        timeout: float | None = None,
        max_retry_attempts: int | None = None,
    ) -> None:
        """Initialize OKX HTTP client.

        Args:
            config: OKX configuration (uses defaults if not provided)
            credentials: API credentials for authenticated requests (optional)
            requests_per_second: Override rate limit (default: 20.0)
            timeout: Override request timeout (default: 30.0)
            max_retry_attempts: Override max retry attempts (default: 3)
        """
        okx_config = config or DEFAULT_CONFIG
        self._credentials = credentials

        # Use provided values or fall back to config defaults
        rps = requests_per_second or okx_config.requests_per_second
        req_timeout = timeout or okx_config.timeout
        retries = max_retry_attempts or okx_config.max_retry_attempts

        # Configure rate limiting
        rate_limiter_config = FixedDelayConfig(delay=1.0 / rps)

        # Configure retry logic for 5xx errors
        retry_config = RetryConfig(
            max_attempts=retries,
            retry_on_status={500, 502, 503, 504},
            retry_on_timeout=True,
            backoff_config=BackoffConfig(
                initial_delay=1.0,
                max_delay=30.0,
                multiplier=2.0,
            ),
        )

        # Build HttpClientConfig
        http_config = HttpClientConfig(
            base_url=okx_config.effective_base_url,
            timeout=req_timeout,
            rate_limiter_config=rate_limiter_config,
            retry_config=retry_config,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        super().__init__(http_config)
        self._okx_config = okx_config

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
            endpoint: API endpoint path (e.g., "/api/v5/market/candles")
            params: Query parameters

        Returns:
            The "data" field from OKX response (typically a list)

        Raises:
            OkxApiError: If OKX returns an error response (code != "0")
            httpx.HTTPError: On HTTP errors after retries exhausted
        """
        response = await self.get(endpoint, params=dict(params) if params else None)
        return self._parse_response(response)

    async def post_data(
        self,
        endpoint: str,
        *,
        json_data: Any = None,
        params: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        """Make a POST request and return parsed data.

        Args:
            endpoint: API endpoint path
            json_data: JSON body data
            params: Query parameters

        Returns:
            The "data" field from OKX response

        Raises:
            OkxApiError: If OKX returns an error response
            httpx.HTTPError: On HTTP errors
        """
        kwargs: dict[str, Any] = {}
        if json_data is not None:
            kwargs["json"] = json_data
        if params:
            kwargs["params"] = dict(params)

        response = await self.post(endpoint, **kwargs)
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> list[Any]:
        """Parse OKX API response format.

        OKX returns all responses in the format:
        {"code": "0", "msg": "", "data": [...]}

        Where code "0" indicates success.

        Args:
            response: HTTP response object

        Returns:
            The "data" field from the response

        Raises:
            OkxApiError: If code is not "0" or response is malformed
        """
        try:
            body = response.json()
        except Exception as e:
            raise OkxApiError(
                code="parse_error",
                msg=f"Failed to parse JSON response: {e}",
                data=[{"response_text": response.text[:500]}],
            ) from e

        code = body.get("code", "unknown")
        msg = body.get("msg", "")
        data = body.get("data", [])

        if code != "0":
            raise OkxApiError(code=code, msg=msg, data=data)

        return data

    async def get_data_auth(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        """Make an authenticated GET request and return parsed data.

        Requires credentials to be set during client initialization.

        Args:
            endpoint: API endpoint path (e.g., "/api/v5/account/balance")
            params: Query parameters

        Returns:
            The "data" field from OKX response

        Raises:
            OkxApiError: If OKX returns an error response or no credentials
            httpx.HTTPError: On HTTP errors
        """
        self._require_credentials()

        # Build the full request path with query string for signing
        request_path = endpoint
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            request_path = f"{endpoint}?{query_string}"

        # Get auth headers
        auth_headers = self._credentials.get_auth_headers(
            method="GET",
            request_path=request_path,
            body="",
            simulated=self._okx_config.use_demo,
        )

        response = await self.get(
            endpoint,
            params=dict(params) if params else None,
            headers=auth_headers,
        )
        return self._parse_response(response)

    async def post_data_auth(
        self,
        endpoint: str,
        *,
        json_data: Any = None,
        params: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        """Make an authenticated POST request and return parsed data.

        Requires credentials to be set during client initialization.

        Args:
            endpoint: API endpoint path
            json_data: JSON body data
            params: Query parameters

        Returns:
            The "data" field from OKX response

        Raises:
            OkxApiError: If OKX returns an error response or no credentials
            httpx.HTTPError: On HTTP errors
        """
        self._require_credentials()

        # Build the request path with query string for signing
        request_path = endpoint
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            request_path = f"{endpoint}?{query_string}"

        # Serialize body for signing
        body = json.dumps(json_data) if json_data is not None else ""

        # Get auth headers
        auth_headers = self._credentials.get_auth_headers(
            method="POST",
            request_path=request_path,
            body=body,
            simulated=self._okx_config.use_demo,
        )

        kwargs: dict[str, Any] = {"headers": auth_headers}
        if json_data is not None:
            kwargs["json"] = json_data
        if params:
            kwargs["params"] = dict(params)

        response = await self.post(endpoint, **kwargs)
        return self._parse_response(response)

    def _require_credentials(self) -> None:
        """Ensure credentials are available for authenticated requests.

        Raises:
            OkxApiError: If credentials are not set.
        """
        if self._credentials is None:
            raise OkxApiError(
                code="auth_error",
                msg="Credentials required for authenticated requests. "
                "Pass credentials=OkxCredentials(...) to OkxHttpClient.",
                data=[],
            )

    @property
    def credentials(self) -> OkxCredentials | None:
        """Get the configured credentials (if any)."""
        return self._credentials

    @property
    def has_credentials(self) -> bool:
        """Check if credentials are configured."""
        return self._credentials is not None

    @property
    def okx_config(self) -> OkxConfig:
        """Get the OKX configuration."""
        return self._okx_config

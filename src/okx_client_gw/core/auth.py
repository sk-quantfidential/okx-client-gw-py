"""Authentication utilities for OKX API.

OKX uses HMAC-SHA256 signatures for authenticated endpoints.
The signature is computed as:
    sign = Base64(HMAC-SHA256(timestamp + method + requestPath + body, secretKey))

Headers required for authenticated requests:
    - OK-ACCESS-KEY: API key
    - OK-ACCESS-SIGN: Base64 encoded signature
    - OK-ACCESS-TIMESTAMP: UTC timestamp in ISO 8601 format
    - OK-ACCESS-PASSPHRASE: Passphrase (optionally encrypted)

For demo trading, add header:
    - x-simulated-trading: 1

See: https://www.okx.com/docs-v5/en/#overview-rest-authentication
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class OkxCredentials:
    """OKX API credentials for authenticated requests.

    Attributes:
        api_key: API key from OKX.
        secret_key: Secret key for HMAC signing.
        passphrase: Passphrase set during API key creation.

    Example:
        # Load from environment
        credentials = OkxCredentials.from_env()

        # Or provide directly
        credentials = OkxCredentials(
            api_key="your-api-key",
            secret_key="your-secret-key",
            passphrase="your-passphrase",
        )
    """

    api_key: str
    secret_key: str
    passphrase: str

    @classmethod
    def from_env(
        cls,
        api_key_var: str = "OKX_API_KEY",
        secret_key_var: str = "OKX_SECRET_KEY",
        passphrase_var: str = "OKX_PASSPHRASE",
    ) -> OkxCredentials:
        """Create credentials from environment variables.

        Args:
            api_key_var: Environment variable name for API key.
            secret_key_var: Environment variable name for secret key.
            passphrase_var: Environment variable name for passphrase.

        Returns:
            OkxCredentials instance.

        Raises:
            ValueError: If any required environment variable is not set.
        """
        api_key = os.environ.get(api_key_var)
        secret_key = os.environ.get(secret_key_var)
        passphrase = os.environ.get(passphrase_var)

        missing = []
        if not api_key:
            missing.append(api_key_var)
        if not secret_key:
            missing.append(secret_key_var)
        if not passphrase:
            missing.append(passphrase_var)

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase,
        )

    def sign(
        self,
        timestamp: str,
        method: str,
        request_path: str,
        body: str = "",
    ) -> str:
        """Generate HMAC-SHA256 signature for OKX API request.

        The signature is computed as:
            sign = Base64(HMAC-SHA256(timestamp + method + requestPath + body, secretKey))

        Args:
            timestamp: UTC timestamp in ISO 8601 format (e.g., "2024-01-01T12:00:00.000Z").
            method: HTTP method in uppercase (GET, POST, etc.).
            request_path: API endpoint path with query string if present
                         (e.g., "/api/v5/account/balance?ccy=BTC").
            body: Request body as JSON string (empty string for GET requests).

        Returns:
            Base64 encoded HMAC-SHA256 signature.

        Example:
            >>> creds = OkxCredentials("key", "secret", "pass")
            >>> creds.sign("2024-01-01T12:00:00.000Z", "GET", "/api/v5/account/balance")
            'base64-encoded-signature'
        """
        message = timestamp + method.upper() + request_path + body
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def get_auth_headers(
        self,
        method: str,
        request_path: str,
        body: str = "",
        *,
        simulated: bool = False,
    ) -> dict[str, str]:
        """Get all required authentication headers for an OKX API request.

        Args:
            method: HTTP method in uppercase (GET, POST, etc.).
            request_path: API endpoint path with query string if present.
            body: Request body as JSON string (empty string for GET requests).
            simulated: If True, add header for demo trading.

        Returns:
            Dictionary of authentication headers.

        Example:
            >>> creds = OkxCredentials.from_env()
            >>> headers = creds.get_auth_headers("GET", "/api/v5/account/balance")
            >>> # Use headers in HTTP request
        """
        timestamp = get_timestamp()
        signature = self.sign(timestamp, method, request_path, body)

        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
        }

        if simulated:
            headers["x-simulated-trading"] = "1"

        return headers


def get_timestamp() -> str:
    """Get current UTC timestamp in OKX format.

    Returns:
        Timestamp in ISO 8601 format: "YYYY-MM-DDTHH:MM:SS.sssZ"

    Example:
        >>> get_timestamp()
        '2024-01-15T10:30:45.123Z'
    """
    now = datetime.now(UTC)
    # OKX expects millisecond precision
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

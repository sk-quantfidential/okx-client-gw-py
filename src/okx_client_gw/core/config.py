"""Configuration for OKX client gateway."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OkxConfig:
    """Configuration for OKX API client.

    Attributes:
        base_url: REST API base URL.
        ws_public_url: WebSocket public channel URL.
        ws_private_url: WebSocket private channel URL.
        requests_per_second: Rate limit for public endpoints.
        timeout: Request timeout in seconds.
        max_retry_attempts: Maximum retry attempts for failed requests.
        use_demo: Use demo/testnet endpoints.
    """

    base_url: str = "https://www.okx.com"
    ws_public_url: str = "wss://ws.okx.com:8443/ws/v5/public"
    ws_private_url: str = "wss://ws.okx.com:8443/ws/v5/private"
    requests_per_second: float = 20.0
    timeout: float = 30.0
    max_retry_attempts: int = 3
    use_demo: bool = False

    # Demo/testnet endpoints
    _demo_base_url: str = field(default="https://www.okx.com", repr=False)
    _demo_ws_public_url: str = field(
        default="wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999", repr=False
    )
    _demo_ws_private_url: str = field(
        default="wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999", repr=False
    )

    @property
    def effective_base_url(self) -> str:
        """Get the effective REST base URL based on demo mode."""
        return self._demo_base_url if self.use_demo else self.base_url

    @property
    def effective_ws_public_url(self) -> str:
        """Get the effective WebSocket public URL based on demo mode."""
        return self._demo_ws_public_url if self.use_demo else self.ws_public_url

    @property
    def effective_ws_private_url(self) -> str:
        """Get the effective WebSocket private URL based on demo mode."""
        return self._demo_ws_private_url if self.use_demo else self.ws_private_url


# Default configuration
DEFAULT_CONFIG = OkxConfig()

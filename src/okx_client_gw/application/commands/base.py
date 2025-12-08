"""Base command class for OKX API operations.

Implements the Command pattern for encapsulating API requests.
Each command represents a single API operation with typed input/output.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class OkxCommand[T](ABC):
    """Base class for OKX API commands.

    Implements the Command pattern where each command encapsulates:
    - API endpoint and parameters
    - Request execution logic
    - Response parsing and type conversion

    Commands are stateless and can be reused. They require a client
    to be provided at invocation time for dependency injection.

    Example:
        class GetTickerCommand(OkxCommand[Ticker]):
            def __init__(self, inst_id: str):
                self._inst_id = inst_id

            async def invoke(self, client: OkxHttpClientProtocol) -> Ticker:
                data = await client.get_data(
                    "/api/v5/market/ticker",
                    params={"instId": self._inst_id}
                )
                return Ticker.from_okx_dict(data[0])

        # Usage
        cmd = GetTickerCommand("BTC-USDT")
        ticker = await cmd.invoke(client)
    """

    @abstractmethod
    async def invoke(self, client: OkxHttpClientProtocol) -> T:
        """Execute the command and return the result.

        Args:
            client: OKX HTTP client for making API requests

        Returns:
            Command-specific result type

        Raises:
            OkxApiError: If the API returns an error
            OkxValidationError: If parameters are invalid
        """
        ...


class OkxQueryCommand[T](OkxCommand[T]):
    """Base class for read-only query commands.

    Query commands fetch data without modifying state.
    They typically use GET requests.
    """

    pass


class OkxMutationCommand[T](OkxCommand[T]):
    """Base class for commands that modify state.

    Mutation commands create, update, or delete resources.
    They typically use POST, PUT, or DELETE requests.

    Note: These require authentication (not implemented yet).
    """

    pass

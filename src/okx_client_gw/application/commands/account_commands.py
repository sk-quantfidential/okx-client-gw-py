"""Account commands for OKX API.

Commands for fetching and managing account data including balance,
positions, and configuration. These endpoints require authentication.

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from okx_client_gw.application.commands.base import OkxMutationCommand, OkxQueryCommand
from okx_client_gw.domain.enums import InstType, MarginMode
from okx_client_gw.domain.models.account import AccountBalance, AccountConfig
from okx_client_gw.domain.models.position import Position

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class GetAccountBalanceCommand(OkxQueryCommand[AccountBalance]):
    """Get account balance information.

    API: GET /api/v5/account/balance (AUTH REQUIRED)

    Returns unified account balance including total equity, margin info,
    and per-currency breakdown.

    Example:
        cmd = GetAccountBalanceCommand()
        balance = await cmd.invoke(client)
        print(f"Total equity: ${balance.total_eq}")
    """

    def __init__(self, ccy: str | None = None) -> None:
        """Initialize command.

        Args:
            ccy: Filter by currency (e.g., "BTC,USDT"). If None, returns all.
        """
        self._ccy = ccy

    async def invoke(self, client: OkxHttpClientProtocol) -> AccountBalance:
        """Fetch account balance.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            AccountBalance object with current account state
        """
        params = {}
        if self._ccy:
            params["ccy"] = self._ccy

        data = await client.get_data_auth(
            "/api/v5/account/balance",
            params=params if params else None,
        )
        return AccountBalance.from_okx_dict(data[0])


class GetAccountPositionsCommand(OkxQueryCommand[list[Position]]):
    """Get current positions.

    API: GET /api/v5/account/positions (AUTH REQUIRED)

    Returns open positions for margin, futures, perpetual swaps, and options.
    Note: This endpoint does not return positions for SPOT trading.

    Example:
        cmd = GetAccountPositionsCommand(inst_type=InstType.SWAP)
        positions = await cmd.invoke(client)
    """

    def __init__(
        self,
        inst_type: InstType | None = None,
        inst_id: str | None = None,
        pos_id: str | None = None,
    ) -> None:
        """Initialize command.

        Args:
            inst_type: Filter by instrument type (MARGIN, SWAP, FUTURES, OPTION)
            inst_id: Filter by instrument ID (e.g., "BTC-USDT-SWAP")
            pos_id: Filter by position ID
        """
        self._inst_type = inst_type
        self._inst_id = inst_id
        self._pos_id = pos_id

    async def invoke(self, client: OkxHttpClientProtocol) -> list[Position]:
        """Fetch current positions.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            List of Position objects
        """
        params: dict[str, str] = {}
        if self._inst_type:
            params["instType"] = self._inst_type.value
        if self._inst_id:
            params["instId"] = self._inst_id
        if self._pos_id:
            params["posId"] = self._pos_id

        data = await client.get_data_auth(
            "/api/v5/account/positions",
            params=params if params else None,
        )
        return [Position.from_okx_dict(item) for item in data]


class GetAccountConfigCommand(OkxQueryCommand[AccountConfig]):
    """Get account configuration.

    API: GET /api/v5/account/config (AUTH REQUIRED)

    Returns account settings including account level (mode), position mode,
    and other configuration options.

    Example:
        cmd = GetAccountConfigCommand()
        config = await cmd.invoke(client)
        print(f"Account mode: {config.account_mode_name}")
    """

    async def invoke(self, client: OkxHttpClientProtocol) -> AccountConfig:
        """Fetch account configuration.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            AccountConfig object
        """
        data = await client.get_data_auth("/api/v5/account/config")
        return AccountConfig.from_okx_dict(data[0])


class SetLeverageCommand(OkxMutationCommand[dict]):
    """Set leverage for an instrument or position.

    API: POST /api/v5/account/set-leverage (AUTH REQUIRED)

    Sets the leverage for margin trading. In cross margin mode, leverage
    applies to the instrument. In isolated margin mode, it applies to the
    specific position.

    Example:
        cmd = SetLeverageCommand(
            inst_id="BTC-USDT-SWAP",
            lever=10,
            mgn_mode=MarginMode.CROSS,
        )
        result = await cmd.invoke(client)
    """

    def __init__(
        self,
        inst_id: str,
        lever: int,
        mgn_mode: MarginMode,
        *,
        pos_side: str | None = None,
        ccy: str | None = None,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID (e.g., "BTC-USDT-SWAP")
            lever: Target leverage (1-125 depending on instrument)
            mgn_mode: Margin mode (cross or isolated)
            pos_side: Position side for long/short mode ("long", "short")
            ccy: Margin currency (required for some cross-margin positions)
        """
        self._inst_id = inst_id
        self._lever = lever
        self._mgn_mode = mgn_mode
        self._pos_side = pos_side
        self._ccy = ccy

    async def invoke(self, client: OkxHttpClientProtocol) -> dict:
        """Set leverage.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            Dict with result including "lever" (confirmed leverage)
        """
        body: dict[str, str] = {
            "instId": self._inst_id,
            "lever": str(self._lever),
            "mgnMode": self._mgn_mode.value,
        }

        if self._pos_side:
            body["posSide"] = self._pos_side
        if self._ccy:
            body["ccy"] = self._ccy

        data = await client.post_data_auth(
            "/api/v5/account/set-leverage",
            json_data=body,
        )
        return data[0] if data else {}


class SetPositionModeCommand(OkxMutationCommand[dict]):
    """Set position mode (long/short vs net).

    API: POST /api/v5/account/set-position-mode (AUTH REQUIRED)

    Sets position mode for SWAP and FUTURES trading:
    - long_short_mode: Separate long and short positions
    - net_mode: Net position (single position per instrument)

    Note: Cannot change while having open positions.

    Example:
        cmd = SetPositionModeCommand(pos_mode="long_short_mode")
        result = await cmd.invoke(client)
    """

    def __init__(self, pos_mode: str) -> None:
        """Initialize command.

        Args:
            pos_mode: Position mode ("long_short_mode" or "net_mode")
        """
        if pos_mode not in ("long_short_mode", "net_mode"):
            raise ValueError(f"Invalid pos_mode: {pos_mode}")
        self._pos_mode = pos_mode

    async def invoke(self, client: OkxHttpClientProtocol) -> dict:
        """Set position mode.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            Dict with result including "posMode" (confirmed mode)
        """
        data = await client.post_data_auth(
            "/api/v5/account/set-position-mode",
            json_data={"posMode": self._pos_mode},
        )
        return data[0] if data else {}


class GetMaxAvailableSizeCommand(OkxQueryCommand[dict]):
    """Get maximum available order size.

    API: GET /api/v5/account/max-size (AUTH REQUIRED)

    Returns the maximum order size available for a given instrument
    and trade mode.

    Example:
        cmd = GetMaxAvailableSizeCommand(
            inst_id="BTC-USDT-SWAP",
            td_mode="cross",
        )
        result = await cmd.invoke(client)
        print(f"Max buy: {result['maxBuy']}")
    """

    def __init__(
        self,
        inst_id: str,
        td_mode: str,
        *,
        ccy: str | None = None,
        px: str | None = None,
        lever: int | None = None,
    ) -> None:
        """Initialize command.

        Args:
            inst_id: Instrument ID
            td_mode: Trade mode ("cross", "isolated", "cash")
            ccy: Margin currency
            px: Price (for limit orders)
            lever: Leverage
        """
        self._inst_id = inst_id
        self._td_mode = td_mode
        self._ccy = ccy
        self._px = px
        self._lever = lever

    async def invoke(self, client: OkxHttpClientProtocol) -> dict:
        """Get max available size.

        Args:
            client: OKX HTTP client with credentials

        Returns:
            Dict with "maxBuy", "maxSell", "instId", etc.
        """
        params: dict[str, str] = {
            "instId": self._inst_id,
            "tdMode": self._td_mode,
        }
        if self._ccy:
            params["ccy"] = self._ccy
        if self._px:
            params["px"] = self._px
        if self._lever:
            params["lever"] = str(self._lever)

        data = await client.get_data_auth("/api/v5/account/max-size", params=params)
        return data[0] if data else {}

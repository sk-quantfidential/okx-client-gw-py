"""Account service for OKX API.

High-level service for account management operations including
balance queries, position management, and account configuration.
All operations require authentication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from okx_client_gw.application.commands.account_commands import (
    GetAccountBalanceCommand,
    GetAccountConfigCommand,
    GetAccountPositionsCommand,
    GetMaxAvailableSizeCommand,
    SetLeverageCommand,
    SetPositionModeCommand,
)
from okx_client_gw.domain.enums import InstType, MarginMode
from okx_client_gw.domain.models.account import AccountBalance, AccountConfig
from okx_client_gw.domain.models.position import Position

if TYPE_CHECKING:
    from okx_client_gw.ports.http_client import OkxHttpClientProtocol


class AccountService:
    """Service for OKX account management operations.

    Provides high-level methods for account data and configuration.
    All methods require authentication (credentials must be set on client).

    Example:
        credentials = OkxCredentials.from_env()
        async with OkxHttpClient(credentials=credentials) as client:
            service = AccountService(client)

            # Get account balance
            balance = await service.get_balance()
            print(f"Total equity: ${balance.total_eq}")

            # Get positions
            positions = await service.get_positions()
            for pos in positions:
                print(f"{pos.inst_id}: {pos.upl}")
    """

    def __init__(self, client: OkxHttpClientProtocol) -> None:
        """Initialize account service.

        Args:
            client: OKX HTTP client with credentials (injected dependency)
        """
        self._client = client

    async def get_balance(self, ccy: str | None = None) -> AccountBalance:
        """Get account balance.

        Args:
            ccy: Filter by currency (e.g., "BTC,USDT"). None returns all.

        Returns:
            AccountBalance with total equity and per-currency breakdown
        """
        cmd = GetAccountBalanceCommand(ccy)
        return await cmd.invoke(self._client)

    async def get_positions(
        self,
        inst_type: InstType | None = None,
        inst_id: str | None = None,
    ) -> list[Position]:
        """Get current open positions.

        Args:
            inst_type: Filter by instrument type (MARGIN, SWAP, FUTURES, OPTION)
            inst_id: Filter by specific instrument ID

        Returns:
            List of Position objects
        """
        cmd = GetAccountPositionsCommand(inst_type, inst_id)
        return await cmd.invoke(self._client)

    async def get_position(self, inst_id: str) -> Position | None:
        """Get position for a specific instrument.

        Args:
            inst_id: Instrument ID (e.g., "BTC-USDT-SWAP")

        Returns:
            Position object if exists, None otherwise
        """
        positions = await self.get_positions(inst_id=inst_id)
        return positions[0] if positions else None

    async def get_config(self) -> AccountConfig:
        """Get account configuration.

        Returns:
            AccountConfig with account mode, position mode, etc.
        """
        cmd = GetAccountConfigCommand()
        return await cmd.invoke(self._client)

    async def set_leverage(
        self,
        inst_id: str,
        lever: int,
        mgn_mode: MarginMode,
        *,
        pos_side: str | None = None,
        ccy: str | None = None,
    ) -> dict:
        """Set leverage for an instrument.

        Args:
            inst_id: Instrument ID (e.g., "BTC-USDT-SWAP")
            lever: Target leverage (1-125 depending on instrument)
            mgn_mode: Margin mode (cross or isolated)
            pos_side: Position side for hedge mode ("long", "short")
            ccy: Margin currency (for some cross positions)

        Returns:
            Dict with confirmed leverage settings
        """
        cmd = SetLeverageCommand(
            inst_id,
            lever,
            mgn_mode,
            pos_side=pos_side,
            ccy=ccy,
        )
        return await cmd.invoke(self._client)

    async def set_position_mode(self, pos_mode: str) -> dict:
        """Set position mode (long/short vs net).

        Args:
            pos_mode: "long_short_mode" or "net_mode"

        Returns:
            Dict with confirmed position mode
        """
        cmd = SetPositionModeCommand(pos_mode)
        return await cmd.invoke(self._client)

    async def get_max_available_size(
        self,
        inst_id: str,
        td_mode: str,
        *,
        ccy: str | None = None,
        px: str | None = None,
        lever: int | None = None,
    ) -> dict:
        """Get maximum order size available.

        Args:
            inst_id: Instrument ID
            td_mode: Trade mode ("cross", "isolated", "cash")
            ccy: Margin currency
            px: Price for limit order calculation
            lever: Leverage to use

        Returns:
            Dict with maxBuy, maxSell values
        """
        cmd = GetMaxAvailableSizeCommand(
            inst_id,
            td_mode,
            ccy=ccy,
            px=px,
            lever=lever,
        )
        return await cmd.invoke(self._client)

    async def get_total_equity_usd(self) -> float:
        """Get total account equity in USD.

        Convenience method for quick equity check.

        Returns:
            Total equity as float
        """
        balance = await self.get_balance()
        return float(balance.total_eq)

    async def get_margin_ratio(self) -> float | None:
        """Get account margin ratio.

        Returns:
            Margin ratio as float (e.g., 1.5 = 150%), or None for simple mode
        """
        balance = await self.get_balance()
        return float(balance.mgn_ratio) if balance.mgn_ratio else None

    async def is_healthy(self) -> bool:
        """Check if account margin is healthy (>150%).

        Returns:
            True if healthy or in simple mode, False if margin ratio low
        """
        balance = await self.get_balance()
        return balance.is_healthy

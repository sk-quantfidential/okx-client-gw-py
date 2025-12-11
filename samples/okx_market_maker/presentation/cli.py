"""OKX Market Maker - CLI Entry Point.

A production-quality market maker using Clean Architecture with dependency injection.

Usage:
    python -m samples.okx_market_maker.main --inst-id BTC-USDT --demo
    python -m samples.okx_market_maker.main --config custom_params.yaml

Environment variables:
    OKX_API_KEY: API key
    OKX_SECRET_KEY: Secret key
    OKX_PASSPHRASE: Passphrase
    MM_*: Configuration overrides (e.g., MM_INST_ID, MM_STEP_PCT)
"""

from __future__ import annotations

import argparse
import asyncio
import signal
from pathlib import Path
from typing import TYPE_CHECKING

from client_gw_core import get_logger

from okx_client_gw.adapters.http.okx_http_client import OkxHttpClient
from okx_client_gw.adapters.websocket import OkxPrivateWsClient, OkxWsClient
from okx_client_gw.application.services import (
    InstrumentService,
    PrivateStreamingService,
    StreamingService,
    TradeService,
)
from okx_client_gw.core.auth import OkxCredentials
from okx_client_gw.core.config import OkxConfig
from samples.okx_market_maker.application.context.market_context import MarketContext
from samples.okx_market_maker.application.services.health_checker import HealthChecker
from samples.okx_market_maker.application.services.order_handler import OrderHandler
from samples.okx_market_maker.core.config.settings import MarketMakerSettings
from samples.okx_market_maker.domain.services.risk_calculator import RiskCalculator
from samples.okx_market_maker.domain.strategies.base_strategy import BaseStrategy
from samples.okx_market_maker.domain.strategies.grid_strategy import (
    GridStrategy,
)
from samples.okx_market_maker.domain.strategies.inventory_skew_strategy import (
    InventorySkewStrategy,
)
from samples.okx_market_maker.domain.strategies.volatility_strategy import (
    VolatilityStrategy,
)

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class MarketMaker:
    """Main market maker orchestrator.

    Coordinates:
    - WebSocket connections (public + private)
    - Market data streaming
    - Strategy execution
    - Order management
    - Health monitoring
    - Graceful shutdown
    """

    def __init__(
        self,
        settings: MarketMakerSettings,
        credentials: OkxCredentials,
    ) -> None:
        """Initialize market maker.

        Args:
            settings: Market maker configuration
            credentials: OKX API credentials
        """
        self.settings = settings
        self.credentials = credentials

        # Create OKX config
        self.okx_config = OkxConfig(demo=settings.use_demo)

        # Create context
        self.context = MarketContext(inst_id=settings.inst_id)

        # Create strategy
        self.strategy = self._create_strategy(settings)

        # Services (initialized in run())
        self._http_client: OkxHttpClient | None = None
        self._public_ws: OkxWsClient | None = None
        self._private_ws: OkxPrivateWsClient | None = None
        self._trade_service: TradeService | None = None
        self._order_handler: OrderHandler | None = None
        self._health_checker: HealthChecker | None = None
        self._risk_calculator: RiskCalculator | None = None

        # Control
        self._running = False
        self._shutdown_event = asyncio.Event()

    def _create_strategy(self, settings: MarketMakerSettings) -> BaseStrategy:
        """Create strategy based on settings.

        Args:
            settings: Configuration with strategy_type

        Returns:
            Strategy instance
        """
        strategy_map = {
            "grid": GridStrategy,
            "inventory_skew": InventorySkewStrategy,
            "volatility": VolatilityStrategy,
        }

        strategy_class = strategy_map.get(settings.strategy_type, GridStrategy)
        return strategy_class(settings)

    async def run(self) -> None:
        """Run the market maker.

        Main entry point that:
        1. Sets up signal handlers
        2. Initializes services
        3. Connects to WebSockets
        4. Runs main loop
        5. Handles shutdown
        """
        logger.info(f"Starting market maker for {self.settings.inst_id}")
        logger.info(f"Strategy: {self.settings.strategy_type}")
        logger.info(f"Demo mode: {self.settings.use_demo}")

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_shutdown)

        try:
            # Initialize services
            await self._initialize_services()

            # Load instrument info
            await self._load_instrument()

            # Start background tasks
            tasks = [
                asyncio.create_task(self._stream_orderbook()),
                asyncio.create_task(self._stream_private_data()),
                asyncio.create_task(self._main_loop()),
            ]

            self._running = True
            logger.info("Market maker started")

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            # Cancel all tasks
            for task in tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error(f"Market maker error: {e}")
            raise

        finally:
            await self._shutdown()

    async def _initialize_services(self) -> None:
        """Initialize all services and connections."""
        # HTTP client for REST API
        self._http_client = OkxHttpClient(
            credentials=self.credentials,
            config=self.okx_config,
        )

        # Trade service
        self._trade_service = TradeService(self._http_client)

        # Order handler
        self._order_handler = OrderHandler(
            trade_service=self._trade_service,
            settings=self.settings,
            context=self.context,
        )

        # Health checker
        self._health_checker = HealthChecker(self.settings)

        # Risk calculator
        self._risk_calculator = RiskCalculator(self.settings)

        # WebSocket clients
        self._public_ws = OkxWsClient(config=self.okx_config)
        self._private_ws = OkxPrivateWsClient(
            credentials=self.credentials,
            config=self.okx_config,
        )

        # Connect
        await self._public_ws.connect()
        await self._private_ws.connect()

        logger.info("Services initialized")

    async def _load_instrument(self) -> None:
        """Load instrument specification."""
        instrument_service = InstrumentService(self._http_client)
        instrument = await instrument_service.get_instrument(self.settings.inst_id)

        if instrument:
            self.context.update_instrument(instrument)
            logger.info(
                f"Loaded instrument: {instrument.inst_id} "
                f"tick={instrument.tick_sz} lot={instrument.lot_sz}"
            )
        else:
            logger.warning(f"Could not load instrument: {self.settings.inst_id}")

    async def _stream_orderbook(self) -> None:
        """Stream orderbook updates from public WebSocket."""
        streaming_service = StreamingService(self._public_ws)

        try:
            async for orderbook in streaming_service.stream_orderbook(
                self.settings.inst_id,
                depth=5,
            ):
                ob, _ = orderbook
                async with self.context.lock:
                    self.context.update_orderbook(ob)

        except asyncio.CancelledError:
            logger.debug("Orderbook streaming cancelled")
        except Exception as e:
            logger.error(f"Orderbook streaming error: {e}")
            self._handle_shutdown()

    async def _stream_private_data(self) -> None:
        """Stream private data from private WebSocket."""
        streaming_service = PrivateStreamingService(self._private_ws)

        try:
            # Subscribe to balance_and_position for efficiency
            async for update in streaming_service.stream_balance_and_position():
                async with self.context.lock:
                    # Update balances
                    if update.balances:
                        # Create minimal account balance update
                        pass  # Handled by balance update

                    # Update positions
                    for position in update.positions:
                        self.context.update_position(position)

        except asyncio.CancelledError:
            logger.debug("Private streaming cancelled")
        except Exception as e:
            logger.error(f"Private streaming error: {e}")
            self._handle_shutdown()

    async def _main_loop(self) -> None:
        """Main strategy loop."""
        interval = self.settings.main_loop_interval_sec

        try:
            while self._running:
                await asyncio.sleep(interval)

                # Health check
                health = self._health_checker.check(self.context)
                if not health.is_healthy:
                    for issue in health.issues:
                        logger.warning(f"Health issue: {issue}")

                    if self._health_checker.should_emergency_stop():
                        logger.error("Emergency stop triggered")
                        await self._cancel_all_orders()
                        self._handle_shutdown()
                        return
                    continue

                # Get strategy decision
                decision = self.strategy.decide(self.context)

                if decision.should_halt:
                    logger.warning(f"Strategy halt: {decision.halt_reason}")
                    await self._cancel_all_orders()
                    continue

                # Execute decision
                if decision.has_actions:
                    await self._order_handler.execute_decision(decision)

                # Cleanup terminal orders
                self._order_handler.cleanup_terminal_orders()

                # Log status periodically
                self._log_status()

        except asyncio.CancelledError:
            logger.debug("Main loop cancelled")
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            self._handle_shutdown()

    async def _cancel_all_orders(self) -> None:
        """Cancel all active orders."""
        if self._order_handler:
            count = await self._order_handler.cancel_all()
            logger.info(f"Cancelled {count} orders")

    def _log_status(self) -> None:
        """Log current status."""
        metrics = self._risk_calculator.calculate(self.context)
        logger.info(
            f"Status: pos={metrics.net_position} "
            f"buys={self.context.num_active_buy_orders} "
            f"sells={self.context.num_active_sell_orders} "
            f"pnl={metrics.total_pnl:.4f}"
        )

    def _handle_shutdown(self) -> None:
        """Handle shutdown signal."""
        logger.info("Shutdown requested")
        self._running = False
        self._shutdown_event.set()

    async def _shutdown(self) -> None:
        """Perform graceful shutdown."""
        logger.info("Shutting down...")

        # Cancel all orders
        await self._cancel_all_orders()

        # Close connections
        if self._private_ws:
            await self._private_ws.disconnect()

        if self._public_ws:
            await self._public_ws.disconnect()

        if self._http_client:
            await self._http_client.close()

        logger.info("Shutdown complete")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="OKX Market Maker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--inst-id",
        type=str,
        default=None,
        help="Instrument ID (e.g., BTC-USDT)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=None,
        help="Use demo trading environment",
    )
    parser.add_argument(
        "--strategy",
        choices=["grid", "inventory_skew", "volatility"],
        default=None,
        help="Strategy type",
    )

    return parser.parse_args()


def run_cli() -> None:
    """CLI entry point for market maker."""
    args = parse_args()

    # Load settings
    if args.config:
        settings = MarketMakerSettings.from_yaml(args.config)
    else:
        settings = MarketMakerSettings.load()

    # Override with CLI args
    if args.inst_id:
        settings = settings.model_copy(update={"inst_id": args.inst_id})
    if args.demo is not None:
        settings = settings.model_copy(update={"use_demo": args.demo})
    if args.strategy:
        settings = settings.model_copy(update={"strategy_type": args.strategy})

    # Load credentials
    try:
        credentials = OkxCredentials.from_env()
    except ValueError as e:
        logger.error(f"Missing credentials: {e}")
        logger.error("Set OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE")
        return

    # Run market maker
    mm = MarketMaker(settings, credentials)
    asyncio.run(mm.run())

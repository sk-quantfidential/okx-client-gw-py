"""Integration test fixtures for OKX client.

@package: tests.integration
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from okx_client_gw.adapters.http import OkxHttpClient
from okx_client_gw.adapters.websocket import OkxWsClient
from okx_client_gw.application.services import (
    InstrumentService,
    MarketDataService,
    StreamingService,
)

# Configure logging for integration tests
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

file_handler = logging.FileHandler("tests/integration/okx_integration.log")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

for log in (
    logging.getLogger("okx_client_gw"),
    logging.getLogger("tests"),
):
    log.setLevel(logging.DEBUG)
    for handler in log.handlers:
        log.removeHandler(handler)
    log.addHandler(file_handler)
    log.addHandler(console_handler)


@pytest_asyncio.fixture(scope="function")
async def okx_http_client() -> AsyncIterator[OkxHttpClient]:
    """Fixture providing an OKX HTTP client for integration tests."""
    async with OkxHttpClient() as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def market_data_service(okx_http_client: OkxHttpClient) -> MarketDataService:
    """Fixture providing a MarketDataService for integration tests."""
    return MarketDataService(okx_http_client)


@pytest_asyncio.fixture(scope="function")
async def instrument_service(okx_http_client: OkxHttpClient) -> InstrumentService:
    """Fixture providing an InstrumentService for integration tests."""
    return InstrumentService(okx_http_client)


@pytest_asyncio.fixture(scope="function")
async def okx_ws_client() -> AsyncIterator[OkxWsClient]:
    """Fixture providing an OKX WebSocket client for integration tests.

    Properly manages the client lifecycle with async connect and disconnect.
    """
    client = OkxWsClient()
    connect_task = asyncio.create_task(client.connect())

    # Allow connection to establish
    await asyncio.sleep(1.0)

    try:
        yield client
    finally:
        await client.disconnect()
        connect_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await connect_task


@pytest_asyncio.fixture(scope="function")
async def streaming_service(okx_ws_client: OkxWsClient) -> StreamingService:
    """Fixture providing a StreamingService for integration tests."""
    return StreamingService(okx_ws_client)


# Mark all tests in this module as integration tests
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


# Apply integration marker to all tests in this directory
def pytest_collection_modifyitems(items):
    """Apply integration marker to all tests in integration directory."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

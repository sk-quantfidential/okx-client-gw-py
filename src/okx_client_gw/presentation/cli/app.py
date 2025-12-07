"""CLI application for OKX market data.

Provides command-line interface for fetching and streaming OKX market data.
Built with Typer for a modern CLI experience.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from okx_client_gw.adapters.http import OkxHttpClient
from okx_client_gw.adapters.websocket import okx_ws_session
from okx_client_gw.application.services import (
    InstrumentService,
    MarketDataService,
    StreamingService,
)
from okx_client_gw.domain.enums import Bar, InstType

app = typer.Typer(
    name="okx",
    help="OKX Exchange market data CLI",
    no_args_is_help=True,
)
console = Console()


@app.command()
def candles(
    inst_id: Annotated[str, typer.Argument(help="Instrument ID (e.g., BTC-USDT)")],
    bar: Annotated[str, typer.Option("--bar", "-b", help="Bar size (1m, 5m, 15m, 1H, 4H, 1D)")] = "1H",
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of candles to fetch")] = 100,
    start: Annotated[str | None, typer.Option("--start", "-s", help="Start date (YYYY-MM-DD)")] = None,
    end: Annotated[str | None, typer.Option("--end", "-e", help="End date (YYYY-MM-DD)")] = None,
) -> None:
    """Fetch candlestick data for an instrument.

    Examples:
        okx candles BTC-USDT
        okx candles ETH-USDT --bar 5m --limit 50
        okx candles BTC-USDT --start 2024-01-01 --end 2024-01-31
    """
    try:
        bar_enum = _parse_bar(bar)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e

    start_date = datetime.fromisoformat(start) if start else None
    end_date = datetime.fromisoformat(end) if end else None

    async def fetch_candles():
        async with OkxHttpClient() as client:
            service = MarketDataService(client)
            return await service.get_candles(
                inst_id=inst_id,
                bar=bar_enum,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )

    with console.status(f"Fetching {limit} {bar} candles for {inst_id}..."):
        candle_list = asyncio.run(fetch_candles())

    if not candle_list:
        console.print("[yellow]No candles found[/yellow]")
        return

    table = Table(title=f"{inst_id} {bar} Candles")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Open", justify="right")
    table.add_column("High", justify="right", style="green")
    table.add_column("Low", justify="right", style="red")
    table.add_column("Close", justify="right")
    table.add_column("Volume", justify="right")

    for candle in candle_list:
        table.add_row(
            candle.timestamp.strftime("%Y-%m-%d %H:%M"),
            str(candle.open),
            str(candle.high),
            str(candle.low),
            str(candle.close),
            str(candle.volume),
        )

    console.print(table)
    console.print(f"[green]Fetched {len(candle_list)} candles[/green]")


@app.command()
def ticker(
    inst_id: Annotated[str, typer.Argument(help="Instrument ID (e.g., BTC-USDT)")],
) -> None:
    """Get current ticker for an instrument.

    Examples:
        okx ticker BTC-USDT
        okx ticker ETH-USDT
    """

    async def fetch_ticker():
        async with OkxHttpClient() as client:
            service = MarketDataService(client)
            return await service.get_ticker(inst_id)

    with console.status(f"Fetching ticker for {inst_id}..."):
        tkr = asyncio.run(fetch_ticker())

    table = Table(title=f"{inst_id} Ticker")
    table.add_column("Field", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Last Price", str(tkr.last))
    table.add_row("Last Size", str(tkr.last_sz))
    table.add_row("Bid Price", str(tkr.bid_px))
    table.add_row("Bid Size", str(tkr.bid_sz))
    table.add_row("Ask Price", str(tkr.ask_px))
    table.add_row("Ask Size", str(tkr.ask_sz))
    table.add_row("24h Open", str(tkr.open_24h))
    table.add_row("24h High", str(tkr.high_24h))
    table.add_row("24h Low", str(tkr.low_24h))
    table.add_row("24h Volume", str(tkr.vol_24h))
    table.add_row("24h Vol (Ccy)", str(tkr.vol_ccy_24h))
    table.add_row("Timestamp", tkr.ts.strftime("%Y-%m-%d %H:%M:%S"))

    console.print(table)


@app.command()
def tickers(
    inst_type: Annotated[str, typer.Argument(help="Instrument type (SPOT, SWAP, FUTURES, OPTION)")] = "SPOT",
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of tickers to show")] = 20,
) -> None:
    """List tickers for an instrument type.

    Examples:
        okx tickers
        okx tickers SWAP --limit 10
    """
    try:
        inst_type_enum = InstType(inst_type.upper())
    except ValueError as e:
        console.print(f"[red]Error: Invalid instrument type '{inst_type}'[/red]")
        console.print("Valid types: SPOT, SWAP, FUTURES, OPTION")
        raise typer.Exit(1) from e

    async def fetch_tickers():
        async with OkxHttpClient() as client:
            service = MarketDataService(client)
            return await service.get_tickers(inst_type_enum)

    with console.status(f"Fetching {inst_type} tickers..."):
        ticker_list = asyncio.run(fetch_tickers())

    # Sort by 24h volume and limit
    sorted_tickers = sorted(ticker_list, key=lambda t: t.vol_ccy_24h, reverse=True)[:limit]

    table = Table(title=f"{inst_type} Tickers (Top {limit} by Volume)")
    table.add_column("Instrument", style="cyan")
    table.add_column("Last", justify="right")
    table.add_column("Bid", justify="right")
    table.add_column("Ask", justify="right")
    table.add_column("24h Change", justify="right")
    table.add_column("24h Volume", justify="right")

    for tkr in sorted_tickers:
        # Calculate 24h change percentage
        if tkr.open_24h and tkr.open_24h != 0:
            change_pct = ((tkr.last - tkr.open_24h) / tkr.open_24h) * 100
            change_str = f"{change_pct:+.2f}%"
            change_style = "green" if change_pct >= 0 else "red"
        else:
            change_str = "N/A"
            change_style = "white"

        table.add_row(
            tkr.inst_id,
            str(tkr.last),
            str(tkr.bid_px),
            str(tkr.ask_px),
            f"[{change_style}]{change_str}[/{change_style}]",
            f"{tkr.vol_ccy_24h:,.0f}",
        )

    console.print(table)
    console.print(f"[green]Showing {len(sorted_tickers)} of {len(ticker_list)} tickers[/green]")


@app.command()
def instruments(
    inst_type: Annotated[str, typer.Argument(help="Instrument type (SPOT, SWAP, FUTURES, OPTION)")] = "SPOT",
    filter_str: Annotated[str | None, typer.Option("--filter", "-f", help="Filter by instrument ID")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number to show")] = 50,
) -> None:
    """List available instruments.

    Examples:
        okx instruments
        okx instruments SWAP --filter BTC
    """
    try:
        inst_type_enum = InstType(inst_type.upper())
    except ValueError as e:
        console.print(f"[red]Error: Invalid instrument type '{inst_type}'[/red]")
        raise typer.Exit(1) from e

    async def fetch_instruments():
        async with OkxHttpClient() as client:
            service = InstrumentService(client)
            return await service.get_instruments(inst_type_enum)

    with console.status(f"Fetching {inst_type} instruments..."):
        inst_list = asyncio.run(fetch_instruments())

    # Filter if requested
    if filter_str:
        inst_list = [i for i in inst_list if filter_str.upper() in i.inst_id.upper()]

    # Limit results
    inst_list = inst_list[:limit]

    table = Table(title=f"{inst_type} Instruments")
    table.add_column("Instrument", style="cyan")
    table.add_column("Base", justify="right")
    table.add_column("Quote", justify="right")
    table.add_column("Tick Size", justify="right")
    table.add_column("Lot Size", justify="right")
    table.add_column("State", justify="center")

    for inst in inst_list:
        state_style = "green" if inst.state == "live" else "yellow"
        table.add_row(
            inst.inst_id,
            inst.base_ccy or "-",
            inst.quote_ccy or "-",
            str(inst.tick_sz),
            str(inst.lot_sz),
            f"[{state_style}]{inst.state}[/{state_style}]",
        )

    console.print(table)
    console.print(f"[green]Showing {len(inst_list)} instruments[/green]")


@app.command()
def orderbook(
    inst_id: Annotated[str, typer.Argument(help="Instrument ID (e.g., BTC-USDT)")],
    depth: Annotated[int, typer.Option("--depth", "-d", help="Order book depth")] = 20,
) -> None:
    """Get order book for an instrument.

    Examples:
        okx orderbook BTC-USDT
        okx orderbook ETH-USDT --depth 50
    """

    async def fetch_orderbook():
        async with OkxHttpClient() as client:
            service = MarketDataService(client)
            return await service.get_orderbook(inst_id, depth)

    with console.status(f"Fetching order book for {inst_id}..."):
        ob = asyncio.run(fetch_orderbook())

    # Create side-by-side table
    table = Table(title=f"{inst_id} Order Book")
    table.add_column("Bid Size", justify="right", style="green")
    table.add_column("Bid Price", justify="right", style="green")
    table.add_column("Ask Price", justify="right", style="red")
    table.add_column("Ask Size", justify="right", style="red")

    max_levels = max(len(ob.bids), len(ob.asks))
    for i in range(min(max_levels, depth)):
        bid = ob.bids[i] if i < len(ob.bids) else None
        ask = ob.asks[i] if i < len(ob.asks) else None

        table.add_row(
            str(bid.size) if bid else "",
            str(bid.price) if bid else "",
            str(ask.price) if ask else "",
            str(ask.size) if ask else "",
        )

    console.print(table)

    # Print summary
    if ob.spread:
        console.print(f"Spread: {ob.spread} ({ob.spread_percent:.4f}%)")
    if ob.mid_price:
        console.print(f"Mid Price: {ob.mid_price}")


@app.command()
def stream(
    inst_id: Annotated[str, typer.Argument(help="Instrument ID (e.g., BTC-USDT)")],
    channel: Annotated[str, typer.Option("--channel", "-c", help="Channel (ticker, trades)")] = "ticker",
) -> None:
    """Stream real-time data via WebSocket.

    Examples:
        okx stream BTC-USDT
        okx stream ETH-USDT --channel trades
    """

    async def stream_data():
        async with okx_ws_session() as client:
            service = StreamingService(client)
            console.print("[green]Connected to OKX WebSocket[/green]")
            console.print(f"[cyan]Streaming {channel} for {inst_id}... (Ctrl+C to stop)[/cyan]")

            if channel == "ticker":
                async for tkr in service.stream_tickers(inst_id):
                    console.print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"{tkr.inst_id}: Last={tkr.last} Bid={tkr.bid_px} Ask={tkr.ask_px}"
                    )
            elif channel == "trades":
                async for trade in service.stream_trades(inst_id):
                    side_style = "green" if trade.is_buy else "red"
                    console.print(
                        f"[{trade.ts.strftime('%H:%M:%S')}] "
                        f"[{side_style}]{trade.side.value.upper()}[/{side_style}] "
                        f"{trade.sz} @ {trade.px}"
                    )
            else:
                console.print(f"[red]Unknown channel: {channel}[/red]")
                console.print("Valid channels: ticker, trades")
                raise typer.Exit(1)

    try:
        asyncio.run(stream_data())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stream stopped[/yellow]")


def _parse_bar(bar: str) -> Bar:
    """Parse bar string to Bar enum."""
    bar_map = {
        "1m": Bar.M1,
        "3m": Bar.M3,
        "5m": Bar.M5,
        "15m": Bar.M15,
        "30m": Bar.M30,
        "1h": Bar.H1,
        "1H": Bar.H1,
        "2h": Bar.H2,
        "2H": Bar.H2,
        "4h": Bar.H4,
        "4H": Bar.H4,
        "6h": Bar.H6_UTC,
        "6H": Bar.H6_UTC,
        "12h": Bar.H12_UTC,
        "12H": Bar.H12_UTC,
        "1d": Bar.D1_UTC,
        "1D": Bar.D1_UTC,
        "1w": Bar.W1_UTC,
        "1W": Bar.W1_UTC,
    }
    if bar not in bar_map:
        valid = ", ".join(sorted(set(bar_map.keys())))
        raise ValueError(f"Invalid bar '{bar}'. Valid values: {valid}")
    return bar_map[bar]


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()

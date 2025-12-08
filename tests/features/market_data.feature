Feature: Market Data Retrieval
    As a trader using the OKX gateway
    I want to retrieve market data through commands
    So that I can make informed trading decisions

    Background:
        Given a mock OKX HTTP client

    Scenario: Fetch ticker for a spot instrument
        Given the mock returns a valid ticker response for "BTC-USDT"
        When I invoke GetTickerCommand for "BTC-USDT"
        Then the ticker should have instrument ID "BTC-USDT"
        And the ticker last price should be greater than 0

    Scenario: Fetch multiple tickers for SPOT instruments
        Given the mock returns multiple SPOT tickers
        When I invoke GetTickersCommand for SPOT instruments
        Then I should receive a list of tickers
        And all tickers should have valid prices

    Scenario: Fetch candlestick data
        Given the mock returns candlestick data for "BTC-USDT"
        When I invoke GetCandlesCommand for "BTC-USDT" with 1H bars
        Then I should receive a list of candles
        And each candle should have valid OHLCV data

    Scenario: Fetch order book
        Given the mock returns order book data for "BTC-USDT"
        When I invoke GetOrderBookCommand for "BTC-USDT"
        Then the order book should have bids and asks
        And the best ask price should be greater than the best bid price

    Scenario: Fetch recent trades
        Given the mock returns recent trades for "BTC-USDT"
        When I invoke GetTradesCommand for "BTC-USDT"
        Then I should receive a list of trades
        And each trade should have a price and size

    Scenario: Fetch SPOT instruments
        Given the mock returns SPOT instruments
        When I invoke GetInstrumentsCommand for SPOT
        Then I should receive a list of instruments
        And all instruments should be of type SPOT

    Scenario: Validate candle limit parameter
        When I try to create GetCandlesCommand with limit 500
        Then a validation error should be raised
        And the error should mention the limit field

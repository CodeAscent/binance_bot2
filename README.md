# Binance Live Crypto Price Tracker

This project provides real-time cryptocurrency price tracking and technical analysis using Binance WebSocket API. It calculates various technical indicators including RSI, SMA, MACD, and VWAP.

## Features

-   Real-time price updates using WebSocket connection
-   Technical indicators calculation:
    -   RSI (Relative Strength Index)
    -   SMA (Simple Moving Average) - 20 and 50 periods
    -   MACD (Moving Average Convergence Divergence)
    -   VWAP (Volume Weighted Average Price)
-   Automatic reconnection on connection loss
-   Memory-efficient data storage (keeps last 1000 data points)

## Prerequisites

-   Python 3.8 or higher
-   Binance API credentials (optional for this implementation)

## Installation

1. Clone this repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the script:

```bash
python binance_ws_client.py
```

By default, the script will track BTC/USDT with 1-minute intervals. You can modify the symbol and interval in the script.

## Available Intervals

-   1m (1 minute)
-   3m (3 minutes)
-   5m (5 minutes)
-   15m (15 minutes)
-   30m (30 minutes)
-   1h (1 hour)
-   2h (2 hours)
-   4h (4 hours)
-   6h (6 hours)
-   8h (8 hours)
-   12h (12 hours)
-   1d (1 day)
-   3d (3 days)
-   1w (1 week)
-   1M (1 month)

## Output

The script will continuously display:

-   Current price
-   RSI value
-   SMA 20 and 50 values
-   MACD values (MACD, Signal, and Histogram)
-   VWAP
-   Volume

## Error Handling

The script includes automatic reconnection if the WebSocket connection is lost. It will attempt to reconnect every 5 seconds.

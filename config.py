"""
Configuration file for the trading bot
"""
import os

# Trading Parameters
TRADING_CONFIG = {
    'symbol': 'btcusdt',          # Trading pair
    'interval': '5m',             # Candlestick interval
    'quantity': 0.001,            # Trading quantity
    'stop_loss_percentage': 2.0,  # Stop loss percentage
    'take_profit_percentage': 4.0 # Take profit percentage
}

# Technical Indicators Configuration
INDICATORS_CONFIG = {
    'rsi': {
        'period': 14,
        'overbought': 70,
        'oversold': 30
    },
    'macd': {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9
    },
    'sma': {
        'short_period': 20,
        'long_period': 50
    }
}

# WebSocket Configuration
WEBSOCKET_CONFIG = {
    'ping_interval': 20,          # Ping interval in seconds
    'ping_timeout': 10,           # Ping timeout in seconds
    'reconnect_delay': 5,         # Reconnection delay in seconds
    'max_reconnect_attempts': 5   # Maximum number of reconnection attempts
}

# Available Intervals
AVAILABLE_INTERVALS = [
    '1m', '3m', '5m', '15m', '30m',  # Minutes
    '1h', '2h', '4h', '6h', '8h',    # Hours
    '12h', '1d', '3d', '1w', '1M'    # Days, Weeks, Months
]

# Available Trading Pairs
AVAILABLE_PAIRS = [
    'btcusdt', 'ethusdt', 'solusdt', 'bnbusdt', 'xrpusdt', 'adausdt',
    'dogeusdt', 'maticusdt', 'ltcusdt'
]

# Risk Management
RISK_CONFIG = {
    'max_open_positions': 1,      # Maximum number of open positions
    'max_daily_trades': 10,       # Maximum number of trades per day
    'max_daily_loss': 5.0,        # Maximum daily loss percentage
    'position_size_percentage': 1.0  # Position size as percentage of available balance
}

# Logging Configuration
LOGGING_CONFIG = {
    'log_level': 'INFO',
    'log_file': 'trading_bot.log',
    'console_output': True
}

# API Configuration
API_CONFIG = {
    'use_testnet': False,         # Whether to use testnet
    'api_key': os.getenv('BINANCE_API_KEY'),              # Will be loaded from .env file
    'api_secret': os.getenv('BINANCE_API_SECRET'),           # Will be loaded from .env file
} 
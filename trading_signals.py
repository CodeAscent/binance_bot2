import pandas as pd
import numpy as np
from binance_ws_client import BinanceWebSocketClient
from ta.momentum import RSIIndicator
from ta.trend import MACD
from config import (
    TRADING_CONFIG,
    INDICATORS_CONFIG,
    WEBSOCKET_CONFIG,
    RISK_CONFIG,
    LOGGING_CONFIG
)
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['log_level']),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGGING_CONFIG['log_file']),
        logging.StreamHandler() if LOGGING_CONFIG['console_output'] else logging.NullHandler()
    ]
)

class TradingSignalGenerator(BinanceWebSocketClient):
    def __init__(self, symbol=None, interval=None):
        # Use config values if not provided
        symbol = symbol or TRADING_CONFIG['symbol']
        interval = interval or TRADING_CONFIG['interval']
        
        super().__init__(symbol, interval)
        self.in_long_position = False
        self.in_short_position = False
        self.last_rsi = None
        self.last_macd = None
        self.last_macd_signal = None
        self.daily_trades = 0
        self.daily_loss = 0.0
        
        # Load indicator parameters from config
        self.rsi_period = INDICATORS_CONFIG['rsi']['period']
        self.rsi_overbought = INDICATORS_CONFIG['rsi']['overbought']
        self.rsi_oversold = INDICATORS_CONFIG['rsi']['oversold']
        
        self.macd_fast = INDICATORS_CONFIG['macd']['fast_period']
        self.macd_slow = INDICATORS_CONFIG['macd']['slow_period']
        self.macd_signal = INDICATORS_CONFIG['macd']['signal_period']
        
        logging.info(f"Initialized TradingSignalGenerator for {symbol} with {interval} interval")
        
    def calculate_indicators(self):
        """Calculate technical indicators and generate trading signals"""
        if len(self.df) < 30:  # Need at least 30 data points for reliable indicators
            return
            
        # Calculate RSI
        rsi_indicator = RSIIndicator(
            close=self.df['close'],
            window=self.rsi_period
        )
        self.df['rsi'] = rsi_indicator.rsi()
        
        # Calculate MACD
        macd = MACD(
            close=self.df['close'],
            window_slow=self.macd_slow,
            window_fast=self.macd_fast,
            window_sign=self.macd_signal
        )
        self.df['macd'] = macd.macd()
        self.df['macd_signal'] = macd.macd_signal()
        self.df['macd_diff'] = macd.macd_diff()
        
        # Get current and previous values
        current_rsi = self.df['rsi'].iloc[-1]
        current_macd = self.df['macd'].iloc[-1]
        current_macd_signal = self.df['macd_signal'].iloc[-1]
        
        # Generate trading signals
        self.generate_signals(current_rsi, current_macd, current_macd_signal)
        
        # Update last values
        self.last_rsi = current_rsi
        self.last_macd = current_macd
        self.last_macd_signal = current_macd_signal
        
        # Print current indicators and positions
        self.print_status()
    
    def generate_signals(self, current_rsi, current_macd, current_macd_signal):
        """Generate trading signals based on RSI and MACD crossovers"""
        if self.last_rsi is None or self.last_macd is None or self.last_macd_signal is None:
            return
            
        # Check for RSI crossovers
        rsi_crossed_below_oversold = (self.last_rsi > self.rsi_oversold and 
                                    current_rsi <= self.rsi_oversold)
        rsi_crossed_above_overbought = (self.last_rsi < self.rsi_overbought and 
                                      current_rsi >= self.rsi_overbought)
        
        # Check for MACD crossovers
        macd_crossed_above_signal = (self.last_macd <= self.last_macd_signal and 
                                   current_macd > current_macd_signal)
        macd_crossed_below_signal = (self.last_macd >= self.last_macd_signal and 
                                   current_macd < current_macd_signal)
        
        # Check risk management conditions
        if not self.check_risk_limits():
            return
        
        # Long Entry Signal
        if not self.in_long_position and not self.in_short_position:
            if rsi_crossed_below_oversold and macd_crossed_above_signal:
                self.in_long_position = True
                self.daily_trades += 1
                self.place_long_order()
        
        # Long Exit Signal
        elif self.in_long_position:
            if rsi_crossed_above_overbought or macd_crossed_below_signal:
                self.in_long_position = False
                self.close_long_position()
        
        # Short Entry Signal
        elif not self.in_long_position and not self.in_short_position:
            if rsi_crossed_above_overbought and macd_crossed_below_signal:
                self.in_short_position = True
                self.daily_trades += 1
                self.place_short_order()
        
        # Short Exit Signal
        elif self.in_short_position:
            if rsi_crossed_below_oversold or macd_crossed_above_signal:
                self.in_short_position = False
                self.close_short_position()
    
    def check_risk_limits(self):
        """Check if we're within risk management limits"""
        # Check daily trade limit
        if self.daily_trades >= RISK_CONFIG['max_daily_trades']:
            logging.warning("Maximum daily trades reached")
            return False
            
        # Check daily loss limit
        if self.daily_loss >= RISK_CONFIG['max_daily_loss']:
            logging.warning("Maximum daily loss reached")
            return False
            
        # Check open positions limit
        if (self.in_long_position or self.in_short_position) and \
           RISK_CONFIG['max_open_positions'] <= 1:
            logging.warning("Maximum open positions reached")
            return False
            
        return True
    
    def place_long_order(self):
        """Placeholder for long order placement"""
        logging.info(f"🟢 LONG SIGNAL for {self.symbol.upper()}")
        # TODO: Implement actual order placement
        # Example:
        # order = client.create_order(
        #     symbol=self.symbol,
        #     side='BUY',
        #     type='MARKET',
        #     quantity=TRADING_CONFIG['quantity']
        # )
        # self.set_stop_loss(order, 'long')
    
    def place_short_order(self):
        """Placeholder for short order placement"""
        logging.info(f"🔴 SHORT SIGNAL for {self.symbol.upper()}")
        # TODO: Implement actual order placement
        # Example:
        # order = client.create_order(
        #     symbol=self.symbol,
        #     side='SELL',
        #     type='MARKET',
        #     quantity=TRADING_CONFIG['quantity']
        # )
        # self.set_stop_loss(order, 'short')
    
    def close_long_position(self):
        """Placeholder for closing long position"""
        logging.info(f"🟡 CLOSE LONG SIGNAL for {self.symbol.upper()}")
        # TODO: Implement actual position closing
        # Example:
        # client.create_order(
        #     symbol=self.symbol,
        #     side='SELL',
        #     type='MARKET',
        #     quantity=current_position_size
        # )
    
    def close_short_position(self):
        """Placeholder for closing short position"""
        logging.info(f"🟡 CLOSE SHORT SIGNAL for {self.symbol.upper()}")
        # TODO: Implement actual position closing
        # Example:
        # client.create_order(
        #     symbol=self.symbol,
        #     side='BUY',
        #     type='MARKET',
        #     quantity=current_position_size
        # )
    
    def set_stop_loss(self, order, position_type):
        """Placeholder for stop loss placement"""
        # TODO: Implement stop loss placement
        # Example:
        # if position_type == 'long':
        #     stop_price = order['price'] * (1 - TRADING_CONFIG['stop_loss_percentage']/100)
        # else:
        #     stop_price = order['price'] * (1 + TRADING_CONFIG['stop_loss_percentage']/100)
        # client.create_order(
        #     symbol=self.symbol,
        #     side='SELL' if position_type == 'long' else 'BUY',
        #     type='STOP_LOSS_LIMIT',
        #     timeInForce='GTC',
        #     quantity=order['executedQty'],
        #     stopPrice=stop_price,
        #     price=stop_price
        # )
        pass
    
    def print_status(self):
        """Print current indicators and position status"""
        latest = self.df.iloc[-1]
        status = f"""
Current Status:
RSI: {latest['rsi']:.2f}
MACD: {latest['macd']:.2f}
MACD Signal: {latest['macd_signal']:.2f}
MACD Histogram: {latest['macd_diff']:.2f}
Position: {'LONG' if self.in_long_position else 'SHORT' if self.in_short_position else 'NONE'}
Daily Trades: {self.daily_trades}/{RISK_CONFIG['max_daily_trades']}
Daily Loss: {self.daily_loss:.2f}%
"""
        logging.info(status)

if __name__ == "__main__":
    client = None
    try:
        # Create trading signal generator using config values
        client = TradingSignalGenerator()
        client.start()
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")
        if client:
            client.unsubscribe() 
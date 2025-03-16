import os
import json
import time
import websocket
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice
from config import WEBSOCKET_CONFIG
import logging
import ssl

# Load environment variables
load_dotenv()

class BinanceWebSocketClient:
    def __init__(self, symbol='btcusdt', interval='1m'):
        self.symbol = symbol.lower()
        self.interval = interval
        self.ws = None
        self.data = []
        self.df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 
                                      'volume', 'trades', 'quote_volume', 'close_time',
                                      'rsi', 'sma_20', 'sma_50', 'macd', 'macd_signal',
                                      'macd_diff', 'vwap'])
        self.is_connected = False
        self.last_ping = time.time()
        self.reconnect_attempts = 0
        self.data_queue = None  # Will be set by the dashboard
        
    def generate_trading_signals(self):
        """Generate trading signals based on technical indicators"""
        if len(self.df) < 50:  # Need at least 50 data points for reliable signals
            return
            
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        # Initialize signal variables
        long_signal = False
        short_signal = False
        signal_strength = 0
        signal_reasons = []
        
        # RSI signals
        if latest['rsi'] < 30:  # Oversold
            long_signal = True
            signal_strength += 1
            signal_reasons.append("RSI oversold")
        elif latest['rsi'] > 70:  # Overbought
            short_signal = True
            signal_strength += 1
            signal_reasons.append("RSI overbought")
            
        # Moving Average signals
        if latest['sma_20'] > latest['sma_50'] and prev['sma_20'] <= prev['sma_50']:
            long_signal = True
            signal_strength += 1
            signal_reasons.append("Golden cross (SMA20 crossed above SMA50)")
        elif latest['sma_20'] < latest['sma_50'] and prev['sma_20'] >= prev['sma_50']:
            short_signal = True
            signal_strength += 1
            signal_reasons.append("Death cross (SMA20 crossed below SMA50)")
            
        # MACD signals
        if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
            long_signal = True
            signal_strength += 1
            signal_reasons.append("MACD bullish crossover")
        elif latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']:
            short_signal = True
            signal_strength += 1
            signal_reasons.append("MACD bearish crossover")
            
        # Volume confirmation
        if latest['volume'] > self.df['volume'].rolling(window=20).mean().iloc[-1]:
            if long_signal:
                signal_strength += 0.5
                signal_reasons.append("High volume confirmation")
            elif short_signal:
                signal_strength += 0.5
                signal_reasons.append("High volume confirmation")
                
        # VWAP signals
        if latest['close'] > latest['vwap'] and prev['close'] <= prev['vwap']:
            long_signal = True
            signal_strength += 0.5
            signal_reasons.append("Price crossed above VWAP")
        elif latest['close'] < latest['vwap'] and prev['close'] >= prev['vwap']:
            short_signal = True
            signal_strength += 0.5
            signal_reasons.append("Price crossed below VWAP")
            
        # Log trading signals
        if long_signal or short_signal:
            signal_type = "long" if long_signal else "short"
            signal_data = {
                'type': signal_type,
                'strength': signal_strength,
                'price': latest['close'],
                'stop_loss': latest['close'] * 0.98 if long_signal else latest['close'] * 1.02,
                'take_profit': latest['close'] * 1.03 if long_signal else latest['close'] * 0.97,
                'reasons': signal_reasons
            }
            
            # Send signal to dashboard
            if hasattr(self, 'data_queue'):
                self.data_queue.put(signal_data)
            
            # Log signal
            logging.info(f"\nTrading Signal Generated: {signal_type.upper()}")
            logging.info(f"Signal Strength: {signal_strength}/3")
            logging.info("Signal Reasons:")
            for reason in signal_reasons:
                logging.info(f"- {reason}")
            logging.info(f"Current Price: {latest['close']:.2f}")
            logging.info(f"Stop Loss: {signal_data['stop_loss']:.2f}")
            logging.info(f"Take Profit: {signal_data['take_profit']:.2f}")

    def calculate_indicators(self):
        """Calculate technical indicators"""
        try:
            # Fill NaN values in the DataFrame
            self.df = self.df.fillna(method='ffill')
            
            # Calculate RSI
            rsi_indicator = RSIIndicator(close=self.df['close'])
            self.df['rsi'] = rsi_indicator.rsi()
            
            # Calculate SMA
            sma_20 = SMAIndicator(close=self.df['close'], window=20)
            sma_50 = SMAIndicator(close=self.df['close'], window=50)
            self.df['sma_20'] = sma_20.sma_indicator()
            self.df['sma_50'] = sma_50.sma_indicator()
            
            # Calculate MACD
            macd = MACD(close=self.df['close'])
            self.df['macd'] = macd.macd()
            self.df['macd_signal'] = macd.macd_signal()
            self.df['macd_diff'] = macd.macd_diff()
            
            # Calculate VWAP
            vwap = VolumeWeightedAveragePrice(high=self.df['high'], 
                                             low=self.df['low'], 
                                             close=self.df['close'], 
                                             volume=self.df['volume'])
            self.df['vwap'] = vwap.volume_weighted_average_price()
            
            # Fill any remaining NaN values with 0
            self.df = self.df.fillna(0)
            
            # Send updated DataFrame to dashboard
            if self.data_queue is not None:
                # Make sure all numeric columns are float
                numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_volume',
                                 'rsi', 'sma_20', 'sma_50', 'macd', 'macd_signal', 'macd_diff', 'vwap']
                for col in numeric_columns:
                    self.df[col] = self.df[col].astype(float)
                
                # Send the data
                self.data_queue.put(self.df.copy())
                logging.info(f"Sent DataFrame with {len(self.df)} rows to dashboard")
            
            # Generate trading signals
            self.generate_trading_signals()
            
        except Exception as e:
            logging.error(f"Error calculating indicators: {str(e)}")
            logging.error(f"DataFrame head: {self.df.head()}")
            logging.error(f"DataFrame info: {self.df.info()}")

    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            # Handle binary messages (ping)
            if isinstance(message, bytes):
                # Don't try to process binary messages as JSON
                return
                
            data = json.loads(message)
            
            # Handle subscription response
            if 'result' in data:
                logging.info(f"Subscription response: {data['result']}")
                return
                
            # Handle error messages
            if 'error' in data:
                logging.error(f"WebSocket error: {data['error']}")
                return
            
            # Handle kline data
            if 'e' in data and data['e'] == 'kline':  # Direct kline data format
                kline = data['k']
                
                # Create a new row of data
                new_data = {
                    'timestamp': pd.to_datetime(kline['t'], unit='ms'),
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'close': float(kline['c']),
                    'volume': float(kline['v']),
                    'trades': int(kline['n']),
                    'quote_volume': float(kline['q']),
                    'close_time': pd.to_datetime(kline['T'], unit='ms')
                }
                
                # Create a new DataFrame row
                new_row = pd.DataFrame([new_data])
                
                # Append to DataFrame
                self.df = pd.concat([self.df, new_row], ignore_index=True)
                
                # Keep only the last 1000 rows to manage memory
                if len(self.df) > 1000:
                    self.df = self.df.tail(1000).reset_index(drop=True)
                
                # Calculate and display indicators
                self.calculate_indicators()
                
                # Print current candle info
                logging.info(f"\nCurrent {self.symbol.upper()} Candle:")
                logging.info(f"Time: {new_data['timestamp']}")
                logging.info(f"Open: {new_data['open']:.2f}")
                logging.info(f"High: {new_data['high']:.2f}")
                logging.info(f"Low: {new_data['low']:.2f}")
                logging.info(f"Close: {new_data['close']:.2f}")
                logging.info(f"Volume: {new_data['volume']:.2f}")
                logging.info(f"Trades: {new_data['trades']}")
                logging.info(f"Quote Volume: {new_data['quote_volume']:.2f}")
                
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            if 'message' in locals():
                logging.error(f"Message content: {message}")

    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        logging.error(f"Error: {error}")
        self.is_connected = False

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logging.warning("WebSocket connection closed")
        self.is_connected = False
        
        # Check if we should attempt to reconnect
        if self.reconnect_attempts < WEBSOCKET_CONFIG['max_reconnect_attempts']:
            self.reconnect_attempts += 1
            logging.info(f"Attempting to reconnect ({self.reconnect_attempts}/{WEBSOCKET_CONFIG['max_reconnect_attempts']})")
            time.sleep(WEBSOCKET_CONFIG['reconnect_delay'])
            self.start()
        else:
            logging.error("Maximum reconnection attempts reached. Stopping.")

    def on_open(self, ws):
        """Handle WebSocket connection open"""
        logging.info(f"WebSocket connection opened for {self.symbol.upper()}")
        self.is_connected = True
        self.last_ping = time.time()
        self.reconnect_attempts = 0  # Reset reconnect attempts on successful connection
        
        # Subscribe to kline/candlestick stream
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [
                f"{self.symbol}@kline_{self.interval}"
            ],
            "id": 1
        }
        
        try:
            ws.send(json.dumps(subscribe_message))
            logging.info(f"Subscribed to {self.symbol}@kline_{self.interval}")
        except Exception as e:
            logging.error(f"Error subscribing to stream: {str(e)}")
            self.is_connected = False
            ws.close()

    def on_ping(self, ws, message):
        """Handle ping messages"""
        try:
            self.last_ping = time.time()
            # Send pong with the same message
            ws.send(message, websocket.ABNF.OPCODE_PONG)
        except Exception as e:
            logging.error(f"Error handling ping: {str(e)}")

    def unsubscribe(self):
        """Unsubscribe from the current stream"""
        if self.ws and self.is_connected:
            unsubscribe_message = {
                "method": "UNSUBSCRIBE",
                "params": [
                    f"{self.symbol}@kline_{self.interval}"
                ],
                "id": 1
            }
            self.ws.send(json.dumps(unsubscribe_message))
            self.ws.close()
            self.is_connected = False

    def start(self):
        """Start WebSocket connection"""
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            "wss://stream.binance.com:9443/ws",  # Use the standard WebSocket endpoint
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
            on_ping=self.on_ping
        )
        
        # Set WebSocket options
        self.ws.run_forever(
            ping_interval=WEBSOCKET_CONFIG['ping_interval'],
            ping_timeout=WEBSOCKET_CONFIG['ping_timeout'],
            sslopt={"cert_reqs": ssl.CERT_NONE}  # Add SSL options
        )

if __name__ == "__main__":
    client = None
    try:
        # Create WebSocket client for BTC/USDT with 1-minute intervals
        client = BinanceWebSocketClient(symbol='btcusdt', interval='1m')
        client.start()
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")
        if client:
            client.unsubscribe() 
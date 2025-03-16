import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from binance_ws_client import BinanceWebSocketClient
import logging
from config import WEBSOCKET_CONFIG, AVAILABLE_PAIRS, AVAILABLE_INTERVALS, TRADING_CONFIG
import threading
import queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_trading_pair(pair):
    """Format trading pair for display (e.g., 'btcusdt' -> 'BTC/USDT')"""
    pair = pair.upper()
    if 'USDT' in pair:
        base, quote = pair.split('USDT')
        return f"{base}/USDT"
    return pair

def get_trading_pairs():
    """Get formatted trading pairs for the dropdown"""
    return [format_trading_pair(pair) for pair in AVAILABLE_PAIRS]

def get_timeframes():
    """Get available timeframes with descriptions"""
    timeframe_descriptions = {
        '1m': '1 minute',
        '3m': '3 minutes',
        '5m': '5 minutes',
        '15m': '15 minutes',
        '30m': '30 minutes',
        '1h': '1 hour',
        '2h': '2 hours',
        '4h': '4 hours',
        '6h': '6 hours',
        '8h': '8 hours',
        '12h': '12 hours',
        '1d': '1 day',
        '3d': '3 days',
        '1w': '1 week',
        '1M': '1 month'
    }
    return [(interval, timeframe_descriptions.get(interval, interval)) for interval in AVAILABLE_INTERVALS]

def create_signal_card(signal):
    """Create a beautiful signal card"""
    signal_type = "LONG" if signal['type'] == 'long' else "SHORT"
    color = "green" if signal_type == "LONG" else "red"
    
    return f"""
    <div style="
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid {color};
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    ">
        <h3 style="color: {color}; margin: 0;">{signal_type} Signal</h3>
        <p style="color: #888; margin: 5px 0;">Strength: {signal['strength']}/3</p>
        <p style="color: #888; margin: 5px 0;">Price: ${signal['price']:.2f}</p>
        <p style="color: #888; margin: 5px 0;">Stop Loss: ${signal['stop_loss']:.2f}</p>
        <p style="color: #888; margin: 5px 0;">Take Profit: ${signal['take_profit']:.2f}</p>
        <div style="margin-top: 10px;">
            <h4 style="color: #888; margin: 5px 0;">Reasons:</h4>
            <ul style="color: #888; margin: 5px 0;">
                {''.join([f'<li>{reason}</li>' for reason in signal['reasons']])}
            </ul>
        </div>
    </div>
    """

def format_pair_for_api(pair):
    """Convert display format (BTC/USDT) to API format (btcusdt)"""
    if '/' in pair:
        base, quote = pair.split('/')
        return (base + quote).lower()
    return pair.lower()

def websocket_thread(queue_obj, symbol, interval):
    """Run WebSocket client in a separate thread"""
    client = BinanceWebSocketClient(symbol=format_pair_for_api(symbol), interval=interval)
    client.data_queue = queue_obj
    client.start()

def create_price_card(data, trading_pair):
    """Create a beautiful price information card"""
    price_direction = "price-up" if float(data['close']) >= float(data['open']) else "price-down"
    change = ((float(data['close']) - float(data['open'])) / float(data['open'])) * 100
    
    return f"""
    <div style="
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="color: white; margin: 0;">{trading_pair}</h2>
                <p style="color: #888; margin: 5px 0;">Last updated: {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div style="text-align: right;">
                <h1 class="{price_direction}" style="margin: 0;">${float(data['close']):,.2f}</h1>
                <p class="{price_direction}" style="margin: 0;">{change:+.2f}%</p>
            </div>
        </div>
        <div style="
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-top: 20px;
        ">
            <div>
                <p style="color: #888; margin: 5px 0;">Open: <span style="color: white">${float(data['open']):,.2f}</span></p>
                <p style="color: #888; margin: 5px 0;">High: <span style="color: white">${float(data['high']):,.2f}</span></p>
            </div>
            <div>
                <p style="color: #888; margin: 5px 0;">Low: <span style="color: white">${float(data['low']):,.2f}</span></p>
                <p style="color: #888; margin: 5px 0;">Volume: <span style="color: white">{float(data['volume']):,.2f} {trading_pair.split('/')[0]}</span></p>
            </div>
        </div>
    </div>
    """

def create_indicator_card(data):
    """Create a beautiful technical indicator card"""
    rsi = float(data.get('rsi', 0))
    rsi_color = "#26A69A" if rsi < 30 else "#EF5350" if rsi > 70 else "white"
    
    return f"""
    <div style="
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    ">
        <h3 style="color: white; margin: 0;">Technical Indicators</h3>
        <div style="
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-top: 20px;
        ">
            <div>
                <p style="color: #888; margin: 5px 0;">RSI: <span style="color: {rsi_color}">{rsi:.2f}</span></p>
                <p style="color: #888; margin: 5px 0;">MA20: <span style="color: white">${float(data.get('sma_20', 0)):,.2f}</span></p>
            </div>
            <div>
                <p style="color: #888; margin: 5px 0;">MA50: <span style="color: white">${float(data.get('sma_50', 0)):,.2f}</span></p>
                <p style="color: #888; margin: 5px 0;">VWAP: <span style="color: white">${float(data.get('vwap', 0)):,.2f}</span></p>
            </div>
        </div>
        <div style="margin-top: 10px;">
            <p style="color: #888; margin: 5px 0;">MACD: 
                <span style="color: white">{float(data.get('macd', 0)):,.2f}</span> | 
                Signal: <span style="color: white">{float(data.get('macd_signal', 0)):,.2f}</span> | 
                Histogram: <span style="color: white">{float(data.get('macd_diff', 0)):,.2f}</span>
            </p>
        </div>
    </div>
    """

def main():
    st.set_page_config(
        page_title="Crypto Trading Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    if 'df' not in st.session_state:
        st.session_state.df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 
                                                  'volume', 'trades', 'quote_volume', 'close_time',
                                                  'rsi', 'sma_20', 'sma_50', 'macd', 'macd_signal',
                                                  'macd_diff', 'vwap'])
    if 'signals' not in st.session_state:
        st.session_state.signals = []
    if 'ws_client' not in st.session_state:
        st.session_state.ws_client = None
    if 'data_queue' not in st.session_state:
        st.session_state.data_queue = queue.Queue()
    if 'client_started' not in st.session_state:
        st.session_state.client_started = False
    if 'last_update' not in st.session_state:
        st.session_state.last_update = time.time()
    if 'selected_pair' not in st.session_state:
        st.session_state.selected_pair = format_trading_pair(TRADING_CONFIG['symbol'])
    if 'selected_interval' not in st.session_state:
        st.session_state.selected_interval = TRADING_CONFIG['interval']

    # Custom CSS
    st.markdown("""
        <style>
        .main {
            background-color: #0E1117;
        }
        .stButton>button {
            background-color: #1E1E1E;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 20px;
        }
        .stButton>button:hover {
            background-color: #2E2E2E;
        }
        .price-up {
            color: #26A69A !important;
        }
        .price-down {
            color: #EF5350 !important;
        }
        .stSelectbox {
            background-color: #1E1E1E;
        }
        </style>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.title("Trading Dashboard")
        st.markdown("---")
        
        # Trading pair selection with dynamic options
        trading_pairs = get_trading_pairs()
        selected_pair = st.selectbox(
            "Trading Pair",
            options=trading_pairs,
            index=trading_pairs.index(st.session_state.selected_pair),
            key="trading_pair_select"
        )
        
        # Timeframe selection with dynamic options and descriptions
        timeframes = get_timeframes()
        selected_interval = st.selectbox(
            "Timeframe",
            options=[t[0] for t in timeframes],
            format_func=lambda x: next((t[1] for t in timeframes if t[0] == x), x),
            index=[t[0] for t in timeframes].index(st.session_state.selected_interval),
            key="timeframe_select"
        )
        
        # Update session state when selections change
        if selected_pair != st.session_state.selected_pair or selected_interval != st.session_state.selected_interval:
            st.session_state.selected_pair = selected_pair
            st.session_state.selected_interval = selected_interval
            
            # Clear existing data and signals
            st.session_state.df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 
                                                      'volume', 'trades', 'quote_volume', 'close_time',
                                                      'rsi', 'sma_20', 'sma_50', 'macd', 'macd_signal',
                                                      'macd_diff', 'vwap'])
            st.session_state.signals = []
            
            # Restart WebSocket with new settings if already running
            if st.session_state.client_started:
                st.session_state.client_started = False
                st.session_state.ws_client = None
                st.session_state.data_queue = queue.Queue()
                time.sleep(1)  # Wait for old connection to close
                
                # Start new connection with updated settings
                st.session_state.data_queue = queue.Queue()
                ws_thread = threading.Thread(
                    target=websocket_thread,
                    args=(st.session_state.data_queue, selected_pair, selected_interval),
                    daemon=True
                )
                ws_thread.start()
                st.session_state.ws_client = ws_thread
                st.session_state.client_started = True
                st.experimental_rerun()
        
        # Start/Stop button
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Start Trading", key="start_btn"):
                if not st.session_state.client_started:
                    st.session_state.data_queue = queue.Queue()
                    ws_thread = threading.Thread(
                        target=websocket_thread,
                        args=(st.session_state.data_queue, selected_pair, selected_interval),
                        daemon=True
                    )
                    ws_thread.start()
                    st.session_state.ws_client = ws_thread
                    st.session_state.client_started = True
                    st.success("Trading started!")

        with col2:
            if st.button("Stop Trading", key="stop_btn"):
                if st.session_state.client_started:
                    st.session_state.client_started = False
                    st.session_state.ws_client = None
                    st.session_state.data_queue = queue.Queue()
                    st.success("Trading stopped!")

    # Main content
    if st.session_state.df is not None and not st.session_state.df.empty:
        latest_data = st.session_state.df.iloc[-1]
        
        # Show connection status with trading pair info
        status_placeholder = st.empty()
        if st.session_state.client_started:
            status_placeholder.success(f"WebSocket Connected - {selected_pair} {selected_interval}")
        else:
            status_placeholder.warning("WebSocket Disconnected")

        # Display price information with selected pair
        st.markdown(create_price_card(latest_data, selected_pair), unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Display technical indicators
            st.markdown(create_indicator_card(latest_data), unsafe_allow_html=True)
        
        with col2:
            st.markdown("### Trading Signals")
            signals_placeholder = st.empty()
            if st.session_state.signals:
                signals_html = ""
                for signal in st.session_state.signals[-3:]:  # Show only last 3 signals
                    signals_html += create_signal_card(signal)
                signals_placeholder.markdown(signals_html, unsafe_allow_html=True)
            else:
                signals_placeholder.info("No signals generated yet...")

    # Update data from queue
    if st.session_state.client_started:
        try:
            while True:
                try:
                    data = st.session_state.data_queue.get_nowait()
                    if isinstance(data, pd.DataFrame):
                        # Ensure the DataFrame has the required columns
                        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 
                                         'volume', 'trades', 'quote_volume', 'close_time']
                        if all(col in data.columns for col in required_columns):
                            st.session_state.df = data
                            st.session_state.last_update = time.time()
                    elif isinstance(data, dict):
                        st.session_state.signals.append(data)
                        # Keep only the last 10 signals
                        if len(st.session_state.signals) > 10:
                            st.session_state.signals = st.session_state.signals[-10:]
                except queue.Empty:
                    break
        except Exception as e:
            st.error(f"Error updating data: {str(e)}")
            logging.error(f"Error updating data: {str(e)}")

    # Check if we haven't received data for a while
    if st.session_state.client_started and time.time() - st.session_state.last_update > 30:
        status_placeholder.warning("No data received in the last 30 seconds. The connection might be stale.")

    # Auto-refresh every 2 seconds
    time.sleep(2)
    st.rerun()

if __name__ == "__main__":
    main() 
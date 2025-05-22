import dash
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import os
import json
import datetime
import logging
import schwabdev
from dotenv import load_dotenv
import time
import sys
from dashboard_utils.data_fetchers import get_minute_data, get_options_chain_data
from dashboard_utils.recommendation_tab import register_recommendation_callbacks
from dashboard_utils.options_chain_utils import process_options_chain_data, split_options_by_type

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
app_logger = logging.getLogger('dashboard_app')

# API credentials
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")
TOKENS_FILE = "token.json"

# Cache configuration
CACHE_CONFIG = {
    'update_interval_seconds': 60,  # Update data every 60 seconds
    'cache_expiry_seconds': 300,    # Cache expires after 5 minutes
}

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# App layout
app.layout = html.Div([
    # Header
    html.H1("Options Analysis Dashboard"),
    
    # Symbol input
    html.Div([
        html.Label("Symbol:"),
        dcc.Input(id="symbol-input", type="text", value="AAPL"),
        html.Button("Load Data", id="load-button", n_clicks=0),
        html.Button("Refresh", id="refresh-button", n_clicks=0),
        html.Div(id="status-message")
    ], style={'margin-bottom': '20px'}),
    
    # Data stores
    dcc.Store(id="selected-symbol-store"),
    dcc.Store(id="minute-data-store"),
    dcc.Store(id="tech-indicators-store"),
    dcc.Store(id="options-chain-store"),
    dcc.Store(id="error-store"),
    
    # Interval component for periodic updates
    dcc.Interval(
        id='update-interval',
        interval=CACHE_CONFIG['update_interval_seconds'] * 1000,  # in milliseconds
        n_intervals=0
    ),
    
    # Tabs for different views
    dcc.Tabs([
        # Minute Data Tab
        dcc.Tab(label="Minute Data", children=[
            html.Div([
                # Timeframe selector
                html.Div([
                    html.Label("Timeframe:"),
                    dcc.Dropdown(
                        id="timeframe-dropdown",
                        options=[
                            {'label': '1 Minute', 'value': '1min'},
                            {'label': '5 Minutes', 'value': '5min'},
                            {'label': '15 Minutes', 'value': '15min'},
                            {'label': '30 Minutes', 'value': '30min'},
                            {'label': '1 Hour', 'value': '1hour'},
                            {'label': '1 Day', 'value': '1day'}
                        ],
                        value='1min'
                    )
                ], style={'width': '200px', 'display': 'inline-block', 'margin-right': '20px'}),
                
                # Period selector
                html.Div([
                    html.Label("Period:"),
                    dcc.Dropdown(
                        id="period-dropdown",
                        options=[
                            {'label': 'Last 1 Day', 'value': '1d'},
                            {'label': 'Last 5 Days', 'value': '5d'},
                            {'label': 'Last 10 Days', 'value': '10d'},
                            {'label': 'Last 30 Days', 'value': '30d'},
                            {'label': 'Last 60 Days', 'value': '60d'}
                        ],
                        value='1d'
                    )
                ], style={'width': '200px', 'display': 'inline-block'})
            ], style={'margin-bottom': '20px'}),
            
            # Minute data table
            html.Div([
                html.H3("Minute Data"),
                dash_table.DataTable(
                    id="minute-data-table",
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '5px'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    }
                )
            ])
        ]),
        
        # Technical Indicators Tab
        dcc.Tab(label="Technical Indicators", children=[
            html.Div([
                html.H3("Technical Indicators"),
                dash_table.DataTable(
                    id="tech-indicators-table",
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '5px'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    }
                )
            ])
        ]),
        
        # Options Chain Tab
        dcc.Tab(label="Options Chain", children=[
            html.Div([
                # Options chain controls
                html.Div([
                    # Expiration date selector
                    html.Div([
                        html.Label("Expiration Date:"),
                        dcc.Dropdown(id="expiration-date-dropdown")
                    ], style={'width': '200px', 'display': 'inline-block', 'margin-right': '20px'}),
                    
                    # Option type selector
                    html.Div([
                        html.Label("Option Type:"),
                        dcc.RadioItems(
                            id="option-type-radio",
                            options=[
                                {'label': 'Calls', 'value': 'CALL'},
                                {'label': 'Puts', 'value': 'PUT'},
                                {'label': 'Both', 'value': 'BOTH'}
                            ],
                            value='BOTH',
                            inline=True
                        )
                    ], style={'display': 'inline-block'})
                ], style={'margin-bottom': '20px'}),
                
                # Status message
                html.Div(id="options-chain-status"),
                
                # Options tables
                html.Div([
                    # Calls table
                    html.Div([
                        html.H3("Calls"),
                        dash_table.DataTable(
                            id="calls-table",
                            page_size=10,
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '5px'
                            },
                            style_header={
                                'backgroundColor': 'rgb(230, 230, 230)',
                                'fontWeight': 'bold'
                            }
                        )
                    ], style={'width': '49%', 'display': 'inline-block', 'vertical-align': 'top'}),
                    
                    # Puts table
                    html.Div([
                        html.H3("Puts"),
                        dash_table.DataTable(
                            id="puts-table",
                            page_size=10,
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '5px'
                            },
                            style_header={
                                'backgroundColor': 'rgb(230, 230, 230)',
                                'fontWeight': 'bold'
                            }
                        )
                    ], style={'width': '49%', 'display': 'inline-block', 'vertical-align': 'top'})
                ])
            ])
        ]),
        
        # Recommendations Tab
        dcc.Tab(label="Recommendations", id="recommendations-tab", children=[
            html.Div(id="recommendations-content")
        ])
    ]),
    
    # Error messages
    html.Div(id="error-messages", style={'margin-top': '20px', 'color': 'red'})
])

# Symbol selection callback
@app.callback(
    Output("selected-symbol-store", "data"),
    Output("status-message", "children"),
    Input("load-button", "n_clicks"),
    State("symbol-input", "value"),
    prevent_initial_call=True
)
def update_selected_symbol(n_clicks, symbol):
    """Updates the selected symbol and triggers data loading."""
    if not symbol:
        return None, "Please enter a symbol"
    
    return {"symbol": symbol.upper(), "timestamp": datetime.datetime.now().isoformat()}, f"Loading data for {symbol.upper()}..."

# Minute Data Tab Callback
@app.callback(
    Output("minute-data-store", "data"),
    Output("error-store", "data", allow_duplicate=True),
    Input("selected-symbol-store", "data"),
    Input("refresh-button", "n_clicks"),
    Input("update-interval", "n_intervals"),
    State("error-store", "data"),
    prevent_initial_call=True
)
def update_minute_data(selected_symbol, n_refresh, n_intervals, error_data):
    """Fetches minute data for the selected symbol."""
    ctx_msg = dash.callback_context
    trigger_id = ctx_msg.triggered[0]["prop_id"].split(".")[0] if ctx_msg.triggered else None
    
    if not selected_symbol or not selected_symbol.get("symbol"):
        return None, error_data
    
    symbol = selected_symbol["symbol"]
    app_logger.info(f"Fetching minute data for {symbol}")
    
    try:
        # Initialize Schwab client
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKENS_FILE, capture_callback=False)
        
        # Fetch minute data
        minute_data, error = get_minute_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching minute data: {error}")
            return None, {
                "source": "Minute Data",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Format data for the table
        formatted_data = []
        for candle in minute_data:
            timestamp = datetime.datetime.fromtimestamp(candle["datetime"] / 1000).strftime("%Y-%m-%d %H:%M:%S")
            formatted_data.append({
                "timestamp": timestamp,
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle["volume"]
            })
        
        app_logger.info(f"Successfully fetched {len(formatted_data)} minute data points for {symbol}")
        
        return {
            "symbol": symbol,
            "data": formatted_data,
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, error_data
    
    except Exception as e:
        error_msg = f"Error fetching minute data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, {
            "source": "Minute Data",
            "message": error_msg,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Technical Indicators Tab Callback
@app.callback(
    Output("tech-indicators-store", "data"),
    Output("error-store", "data", allow_duplicate=True),
    Input("minute-data-store", "data"),
    State("error-store", "data"),
    prevent_initial_call=True
)
def update_tech_indicators(minute_data, error_data):
    """Calculates technical indicators from minute data."""
    if not minute_data or not minute_data.get("data"):
        return None, error_data
    
    symbol = minute_data["symbol"]
    data = minute_data["data"]
    
    app_logger.info(f"Calculating technical indicators for {symbol}")
    
    try:
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        
        # Calculate indicators for different timeframes
        timeframes = {
            "1min": df,
            "5min": df.resample("5T").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna(),
            "15min": df.resample("15T").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna(),
            "30min": df.resample("30T").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna(),
            "1hour": df.resample("1H").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna()
        }
        
        # Calculate indicators for each timeframe
        timeframe_data = {}
        for timeframe, tf_df in timeframes.items():
            if len(tf_df) > 0:
                # Calculate RSI
                delta = tf_df["close"].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
                # Calculate MACD
                ema12 = tf_df["close"].ewm(span=12, adjust=False).mean()
                ema26 = tf_df["close"].ewm(span=26, adjust=False).mean()
                macd = ema12 - ema26
                signal = macd.ewm(span=9, adjust=False).mean()
                histogram = macd - signal
                
                # Calculate Bollinger Bands
                sma20 = tf_df["close"].rolling(window=20).mean()
                std20 = tf_df["close"].rolling(window=20).std()
                upper_band = sma20 + (std20 * 2)
                lower_band = sma20 - (std20 * 2)
                
                # Prepare data for the table
                indicators_df = pd.DataFrame({
                    "timestamp": tf_df.index,
                    "close": tf_df["close"],
                    "rsi": rsi,
                    "macd": macd,
                    "macd_signal": signal,
                    "macd_histogram": histogram,
                    "bb_middle": sma20,
                    "bb_upper": upper_band,
                    "bb_lower": lower_band
                }).dropna()
                
                # Format data for the table
                formatted_data = []
                for _, row in indicators_df.iterrows():
                    formatted_data.append({
                        "Timestamp": row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                        "Close": round(row["close"], 2),
                        "RSI": round(row["rsi"], 2),
                        "MACD": round(row["macd"], 2),
                        "MACD Signal": round(row["macd_signal"], 2),
                        "MACD Histogram": round(row["macd_histogram"], 2),
                        "BB Middle": round(row["bb_middle"], 2),
                        "BB Upper": round(row["bb_upper"], 2),
                        "BB Lower": round(row["bb_lower"], 2)
                    })
                
                timeframe_data[timeframe] = formatted_data
        
        app_logger.info(f"Successfully calculated technical indicators for {symbol}")
        
        return {
            "symbol": symbol,
            "timeframe_data": timeframe_data,
            "timeframe": "1min",
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, error_data
    
    except Exception as e:
        error_msg = f"Error calculating technical indicators: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, {
            "source": "Technical Indicators",
            "message": error_msg,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Options Chain Tab Callback
@app.callback(
    [
        Output("options-chain-store", "data"),
        Output("expiration-date-dropdown", "options"),
        Output("expiration-date-dropdown", "value"),
        Output("options-chain-status", "children"),
        Output("error-store", "data", allow_duplicate=True)
    ],
    [
        Input("selected-symbol-store", "data"),
        Input("refresh-button", "n_clicks"),
        Input("update-interval", "n_intervals")
    ],
    prevent_initial_call=True
)
def update_options_chain(selected_symbol, n_refresh, n_intervals):
    """Fetches options chain data for the selected symbol."""
    ctx_msg = dash.callback_context
    trigger_id = ctx_msg.triggered[0]["prop_id"].split(".")[0] if ctx_msg.triggered else None
    
    if not selected_symbol or not selected_symbol.get("symbol"):
        return None, [], None, "No symbol selected", None
    
    symbol = selected_symbol["symbol"]
    app_logger.info(f"Fetching options chain for {symbol}")
    
    try:
        # Initialize Schwab client
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKENS_FILE, capture_callback=False)
        
        # Fetch options chain data
        options_df, expiration_dates, underlying_price, error = get_options_chain_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching options chain: {error}")
            return None, [], None, f"Error: {error}", {
                "source": "Options Chain",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Prepare dropdown options
        dropdown_options = [{"label": date, "value": date} for date in expiration_dates]
        default_expiration = expiration_dates[0] if expiration_dates else None
        
        # Prepare data for the store
        options_data = {
            "symbol": symbol,
            "options": options_df.to_dict("records"),
            "expiration_dates": expiration_dates,
            "underlyingPrice": underlying_price,  # Include underlying price in the options data
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        status_message = f"Loaded {len(options_df)} option contracts for {symbol}"
        app_logger.info(status_message)
        app_logger.info(f"Underlying price for {symbol}: {underlying_price}")
        
        return options_data, dropdown_options, default_expiration, status_message, None
    
    except Exception as e:
        error_msg = f"Error updating options chain: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, [], None, f"Error: {str(e)}", {
            "source": "Options Chain",
            "message": error_msg,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Minute Data Table Callback
@app.callback(
    Output("minute-data-table", "data"),
    Output("minute-data-table", "columns"),
    Input("minute-data-store", "data"),
    prevent_initial_call=True
)
def update_minute_data_table(minute_data):
    """Updates the minute data table with the fetched data."""
    if not minute_data or not minute_data.get("data"):
        return [], []
    
    data = minute_data["data"]
    
    # Define columns
    columns = [
        {"name": "Timestamp", "id": "timestamp"},
        {"name": "Open", "id": "open"},
        {"name": "High", "id": "high"},
        {"name": "Low", "id": "low"},
        {"name": "Close", "id": "close"},
        {"name": "Volume", "id": "volume"}
    ]
    
    return data, columns

# Technical Indicators Table Callback
@app.callback(
    Output("tech-indicators-table", "data"),
    Output("tech-indicators-table", "columns"),
    Input("tech-indicators-store", "data"),
    prevent_initial_call=True
)
def update_tech_indicators_table(tech_indicators_data):
    """Updates the technical indicators table with the calculated data."""
    if not tech_indicators_data or not tech_indicators_data.get("timeframe_data"):
        return [], []
    
    timeframe = tech_indicators_data.get("timeframe", "1min")
    data = tech_indicators_data["timeframe_data"].get(timeframe, [])
    
    if not data:
        return [], []
    
    # Get column names from the first row
    first_row = data[0]
    columns = [{"name": col, "id": col} for col in first_row.keys()]
    
    return data, columns

# Options Chain Tables Callback
@app.callback(
    [
        Output("calls-table", "data"),
        Output("puts-table", "data")
    ],
    [
        Input("options-chain-store", "data"),
        Input("expiration-date-dropdown", "value"),
        Input("option-type-radio", "value")
    ],
    prevent_initial_call=True
)
def update_options_tables(options_data, expiration_date, option_type):
    """Updates the options chain tables with the fetched data."""
    if not options_data or not options_data.get("options"):
        return [], []
    
    # Use the utility function to split options by type
    options_df = pd.DataFrame(options_data["options"])
    calls_data, puts_data = split_options_by_type(options_df, expiration_date, option_type)
    
    return calls_data, puts_data

# Error message callback
@app.callback(
    Output("error-messages", "children"),
    Input("error-store", "data"),
    prevent_initial_call=True
)
def update_error_messages(error_data):
    """Updates the error message display."""
    if not error_data:
        return ""
    
    source = error_data.get("source", "Unknown")
    message = error_data.get("message", "An unknown error occurred")
    timestamp = error_data.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    return f"Error in {source} at {timestamp}: {message}"

# Register recommendation callbacks
register_recommendation_callbacks(app)

# Run the app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

from dash import dcc, html, dash_table, ctx
import dash
from dash.dependencies import Input, Output, State, ALL
import pandas as pd
import numpy as np # For NaN handling
import datetime
import os # For account ID
import logging # For app-level logging
import json # For pretty printing dicts in logs
import re # For parsing option key
import base64 # For CSV download
import io # For CSV download
# Import utility functions
from dashboard_utils.data_fetchers import get_schwab_client, get_minute_data, get_options_chain_data, get_option_contract_keys
from dashboard_utils.streaming_manager import StreamingManager
# Import technical analysis functions
from technical_analysis import aggregate_candles, calculate_all_technical_indicators
# Import recommendation tab components
from dashboard_utils.recommendation_tab import create_recommendation_tab, register_recommendation_callbacks

# Configure logging for the app with both console and file handlers
app_logger = logging.getLogger(__name__)

# Always define log_file regardless of handler state
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"app_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

if not app_logger.hasHandlers():
    # Console handler
    app_handler = logging.StreamHandler()
    app_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    app_handler.setFormatter(app_formatter)
    app_logger.addHandler(app_handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(app_formatter)
    app_logger.addHandler(file_handler)
    
app_logger.setLevel(logging.INFO)
app_logger.info(f"App logger initialized. Logging to console and file: {log_file}")

# Global cache for minute data and technical indicators
# Structure:
# {
#     'SYMBOL': {
#         'data': pandas_dataframe,
#         'last_update': datetime_object,
#         'timeframe_data': {
#             '1min': dataframe_or_records,
#             '5min': dataframe_or_records,
#             # other timeframes
#         }
#     }
# }
MINUTE_DATA_CACHE = {}

# Cache configuration
CACHE_CONFIG = {
    'max_age_hours': 24,  # Maximum age of cached data before forcing a full refresh
    'update_interval_seconds': 30,  # Interval for periodic updates
    'buffer_minutes': 5,  # Buffer time to avoid gaps in data
    'days_history': 60,  # Number of days of minute data to fetch (changed from default 1 to 60)
}

# Initialize the Dash app BEFORE defining layout or callbacks
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Trading Dashboard"
app_logger.info("Dash app initialized")

# --- Schwab Client and Account ID Setup ---
def schwab_client_provider():
    """Provides the Schwab client instance."""
    client, _ = get_schwab_client()
    return client

# --- Layout ---
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Trading Dashboard", className="app-header"),
        html.Div([
            dcc.Input(id="symbol-input", type="text", placeholder="Enter Symbol", value="AAPL", className="symbol-input"),
            html.Button("Load", id="load-button", n_clicks=0, className="load-button"),
            html.Button("Refresh", id="refresh-button", n_clicks=0, className="refresh-button"),
            html.Div(id="status-message", className="status-message")
        ], className="header-controls"),
    ], className="header-container"),
    
    # Store components for data
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
                            {"label": "1 Minute", "value": "1min"},
                            {"label": "5 Minutes", "value": "5min"},
                            {"label": "15 Minutes", "value": "15min"},
                            {"label": "30 Minutes", "value": "30min"},
                            {"label": "1 Hour", "value": "1hour"},
                            {"label": "4 Hours", "value": "4hour"},
                            {"label": "1 Day", "value": "1day"}
                        ],
                        value="1hour",
                        clearable=False,
                        className="timeframe-dropdown"
                    )
                ], className="control-group"),
                
                # Data table
                html.Div([
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
                ], className="data-table-container")
            ], className="tab-content")
        ]),
        
        # Technical Indicators Tab
        dcc.Tab(label="Technical Indicators", children=[
            html.Div([
                # Timeframe selector
                html.Div([
                    html.Label("Timeframe:"),
                    dcc.Dropdown(
                        id="tech-timeframe-dropdown",
                        options=[
                            {"label": "1 Minute", "value": "1min"},
                            {"label": "5 Minutes", "value": "5min"},
                            {"label": "15 Minutes", "value": "15min"},
                            {"label": "30 Minutes", "value": "30min"},
                            {"label": "1 Hour", "value": "1hour"},
                            {"label": "4 Hours", "value": "4hour"},
                            {"label": "1 Day", "value": "1day"}
                        ],
                        value="1hour",
                        clearable=False,
                        className="timeframe-dropdown"
                    )
                ], className="control-group"),
                
                # Data table
                html.Div([
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
                ], className="data-table-container")
            ], className="tab-content")
        ]),
        
        # Options Chain Tab
        dcc.Tab(label="Options Chain", children=[
            html.Div([
                # Controls
                html.Div([
                    html.Div([
                        html.Label("Expiration Date:"),
                        dcc.Dropdown(
                            id="expiration-date-dropdown",
                            options=[],
                            className="expiration-dropdown"
                        )
                    ], className="control-group"),
                    html.Div([
                        html.Label("Option Type:"),
                        dcc.RadioItems(
                            id="option-type-radio",
                            options=[
                                {"label": "Calls", "value": "CALL"},
                                {"label": "Puts", "value": "PUT"},
                                {"label": "Both", "value": "BOTH"}
                            ],
                            value="BOTH",
                            className="option-type-radio"
                        )
                    ], className="control-group"),
                    html.Div(id="options-chain-status", className="options-status")
                ], className="options-controls"),
                
                # Options chain tables
                html.Div([
                    html.Div([
                        html.H3("Calls", className="table-header"),
                        html.Div([
                            dash_table.DataTable(
                                id="calls-table",
                                columns=[
                                    {"name": "Strike", "id": "strikePrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Last", "id": "lastPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Bid", "id": "bidPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Ask", "id": "askPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Volume", "id": "totalVolume", "type": "numeric"},
                                    {"name": "OI", "id": "openInterest", "type": "numeric"},
                                    {"name": "IV", "id": "volatility", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Delta", "id": "delta", "type": "numeric", "format": {"specifier": ".3f"}},
                                    {"name": "Gamma", "id": "gamma", "type": "numeric", "format": {"specifier": ".3f"}},
                                    {"name": "Theta", "id": "theta", "type": "numeric", "format": {"specifier": ".3f"}},
                                    {"name": "Vega", "id": "vega", "type": "numeric", "format": {"specifier": ".3f"}}
                                ],
                                page_size=10,
                                style_table={'overflowX': 'auto'},
                                style_cell={
                                    'textAlign': 'left',
                                    'padding': '5px'
                                },
                                style_header={
                                    'backgroundColor': 'rgb(230, 230, 230)',
                                    'fontWeight': 'bold'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'column_id': 'strikePrice', 'filter_query': '{inTheMoney} eq true'},
                                        'backgroundColor': 'rgba(0, 255, 0, 0.1)',
                                        'fontWeight': 'bold'
                                    }
                                ],
                                # Tooltip for filter usage
                                tooltip_delay=0,
                                tooltip_duration=None
                            )
                        ], className="calls-container")
                    ]),
                    html.Div([
                        html.H3("Puts", className="table-header"),
                        html.Div([
                            dash_table.DataTable(
                                id="puts-table",
                                columns=[
                                    {"name": "Strike", "id": "strikePrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Last", "id": "lastPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Bid", "id": "bidPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Ask", "id": "askPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Volume", "id": "totalVolume", "type": "numeric"},
                                    {"name": "OI", "id": "openInterest", "type": "numeric"},
                                    {"name": "IV", "id": "volatility", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Delta", "id": "delta", "type": "numeric", "format": {"specifier": ".3f"}},
                                    {"name": "Gamma", "id": "gamma", "type": "numeric", "format": {"specifier": ".3f"}},
                                    {"name": "Theta", "id": "theta", "type": "numeric", "format": {"specifier": ".3f"}},
                                    {"name": "Vega", "id": "vega", "type": "numeric", "format": {"specifier": ".3f"}}
                                ],
                                page_size=10,
                                style_table={'overflowX': 'auto'},
                                style_cell={
                                    'textAlign': 'left',
                                    'padding': '5px'
                                },
                                style_header={
                                    'backgroundColor': 'rgb(230, 230, 230)',
                                    'fontWeight': 'bold'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'column_id': 'strikePrice', 'filter_query': '{inTheMoney} eq true'},
                                        'backgroundColor': 'rgba(0, 255, 0, 0.1)',
                                        'fontWeight': 'bold'
                                    },
                                ],
                                # Tooltip for filter usage
                                tooltip_delay=0,
                                tooltip_duration=None
                            )
                        ], className="puts-container")
                    ])
                ], className="options-tables-container")
            ], className="tab-content")
        ]),
        
        # Recommendation Engine Tab
        dcc.Tab(label="Recommendations", children=create_recommendation_tab())
    ], id="tabs", className="tabs-container"),
    
    # Error display
    html.Div(id="error-display", className="error-display")
], className="app-container")

# --- Callbacks ---

# Error Store Callback
@app.callback(
    Output("error-display", "children"),
    Input("error-store", "data")
)
def update_error_display(error_data):
    if error_data:
        source = error_data.get("source", "Unknown")
        message = error_data.get("message", "An unknown error occurred")
        timestamp = error_data.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return html.Div([
            html.H4(f"Error in {source}"),
            html.P(message),
            html.P(f"Time: {timestamp}", className="error-timestamp")
        ], className="error-message")
    
    return None

# Symbol Selection Callback
@app.callback(
    Output("selected-symbol-store", "data"),
    Output("status-message", "children"),
    Input("load-button", "n_clicks"),
    State("symbol-input", "value"),
    prevent_initial_call=True
)
def update_selected_symbol(n_clicks, symbol):
    """Updates the selected symbol."""
    if not symbol:
        return None, "Please enter a symbol"
    
    # Normalize symbol
    symbol = symbol.strip().upper()
    
    app_logger.info(f"Selected symbol: {symbol}")
    
    return {"symbol": symbol}, f"Symbol selected: {symbol}"

# Minute Data Callback
@app.callback(
    [
        Output("minute-data-store", "data"),
        Output("status-message", "children", allow_duplicate=True),
        Output("error-store", "data")
    ],
    [
        Input("selected-symbol-store", "data"),
        Input("refresh-button", "n_clicks"),
        Input("update-interval", "n_intervals")
    ],
    prevent_initial_call=True
)
def update_minute_data(selected_symbol, n_refresh, n_intervals):
    """Fetches minute data for the selected symbol."""
    global MINUTE_DATA_CACHE
    
    ctx_msg = dash.callback_context
    trigger_id = ctx_msg.triggered[0]["prop_id"].split(".")[0] if ctx_msg.triggered else None
    
    if not selected_symbol or not selected_symbol.get("symbol"):
        return None, "No symbol selected", None
    
    symbol = selected_symbol["symbol"]
    app_logger.info(f"Updating minute data for {symbol} (trigger: {trigger_id})")
    
    try:
        client = schwab_client_provider()
        if not client:
            error_msg = "Failed to initialize Schwab client"
            app_logger.error(error_msg)
            return None, "Error: Schwab client initialization failed", {
                "source": "Minute Data",
                "message": error_msg,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Check if we need to fetch new data or can use cached data
        force_refresh = trigger_id in ["refresh-button", "selected-symbol-store"]
        
        if symbol in MINUTE_DATA_CACHE and not force_refresh:
            # Check if cache is still valid
            last_update = MINUTE_DATA_CACHE[symbol].get("last_update")
            if last_update:
                age_hours = (datetime.datetime.now() - last_update).total_seconds() / 3600
                if age_hours < CACHE_CONFIG["max_age_hours"]:
                    # Cache is still valid, use it
                    app_logger.info(f"Using cached minute data for {symbol} (age: {age_hours:.2f} hours)")
                    return MINUTE_DATA_CACHE[symbol], f"Using cached data for {symbol}", None
        
        # Fetch new data
        days_history = CACHE_CONFIG["days_history"]
        app_logger.info(f"Fetching {days_history} days of minute data for {symbol}")
        
        # If we have cached data, use the latest timestamp as the starting point
        since_timestamp = None
        if symbol in MINUTE_DATA_CACHE and "data" in MINUTE_DATA_CACHE[symbol]:
            cached_df = pd.DataFrame(MINUTE_DATA_CACHE[symbol]["data"])
            if not cached_df.empty and "timestamp" in cached_df.columns:
                # Get the latest timestamp and subtract a buffer to ensure no gaps
                latest_timestamp = pd.to_datetime(cached_df["timestamp"]).max()
                buffer_minutes = CACHE_CONFIG["buffer_minutes"]
                since_timestamp = latest_timestamp - datetime.timedelta(minutes=buffer_minutes)
                app_logger.info(f"Using incremental fetch since {since_timestamp} (with {buffer_minutes} minute buffer)")
        
        minute_df, error = get_minute_data(client, symbol, days_history, since_timestamp)
        
        if error:
            app_logger.error(f"Error fetching minute data: {error}")
            return None, f"Error: {error}", {
                "source": "Minute Data",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        if minute_df.empty:
            app_logger.warning(f"No minute data available for {symbol}")
            return None, f"No minute data available for {symbol}", None
        
        # If we have existing cached data and did an incremental fetch, merge with cached data
        if symbol in MINUTE_DATA_CACHE and "data" in MINUTE_DATA_CACHE[symbol] and since_timestamp:
            cached_df = pd.DataFrame(MINUTE_DATA_CACHE[symbol]["data"])
            if not cached_df.empty:
                # Convert timestamp columns to datetime for proper comparison
                if "timestamp" in cached_df.columns:
                    cached_df["timestamp"] = pd.to_datetime(cached_df["timestamp"])
                
                if "timestamp" in minute_df.columns:
                    minute_df["timestamp"] = pd.to_datetime(minute_df["timestamp"])
                
                # Remove any overlap (keep newer data)
                if since_timestamp:
                    cached_df = cached_df[cached_df["timestamp"] < since_timestamp]
                
                # Combine old and new data
                combined_df = pd.concat([minute_df, cached_df], ignore_index=True)
                
                # Remove duplicates
                combined_df.drop_duplicates(subset=["timestamp"], keep="first", inplace=True)
                
                # Sort by timestamp (descending)
                combined_df.sort_values(by="timestamp", ascending=False, inplace=True)
                
                minute_df = combined_df
                app_logger.info(f"Merged new data with cached data, total rows: {len(minute_df)}")
        
        # Convert timestamp to string for JSON serialization
        if "timestamp" in minute_df.columns:
            minute_df["timestamp"] = minute_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Update cache
        MINUTE_DATA_CACHE[symbol] = {
            "data": minute_df.to_dict("records"),
            "last_update": datetime.datetime.now()
        }
        
        # Prepare data for store
        minute_data = {
            "symbol": symbol,
            "data": minute_df.to_dict("records"),
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        status_message = f"Loaded {len(minute_df)} minute data rows for {symbol}"
        app_logger.info(status_message)
        
        return minute_data, status_message, None
    
    except Exception as e:
        error_msg = f"Error updating minute data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, f"Error: {str(e)}", {
            "source": "Minute Data",
            "message": error_msg,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Technical Indicators Callback
@app.callback(
    [
        Output("tech-indicators-store", "data"),
        Output("error-store", "data", allow_duplicate=True)
    ],
    [
        Input("minute-data-store", "data"),
        Input("tech-timeframe-dropdown", "value")
    ],
    prevent_initial_call=True
)
def update_technical_indicators(minute_data, timeframe):
    """Calculates technical indicators for the selected timeframe."""
    global MINUTE_DATA_CACHE
    
    if not minute_data or not minute_data.get("data"):
        return None, None
    
    symbol = minute_data.get("symbol", "")
    app_logger.info(f"Updating technical indicators for {symbol} ({timeframe})")
    
    try:
        # Convert minute data to DataFrame
        minute_df = pd.DataFrame(minute_data["data"])
        
        if minute_df.empty:
            app_logger.warning(f"Empty minute data DataFrame for {symbol}")
            return None, {
                "source": "Technical Indicators",
                "message": "No minute data available",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Convert timestamp to datetime
        if "timestamp" in minute_df.columns:
            minute_df["timestamp"] = pd.to_datetime(minute_df["timestamp"])
            minute_df.set_index("timestamp", inplace=True)
        
        # Check if we need to recalculate or can use cached data
        recalculate = True
        if symbol in MINUTE_DATA_CACHE and "timeframe_data" in MINUTE_DATA_CACHE[symbol]:
            if timeframe in MINUTE_DATA_CACHE[symbol]["timeframe_data"]:
                # We already have this timeframe, check if we need to update
                last_update = MINUTE_DATA_CACHE[symbol].get("last_update")
                last_calc = MINUTE_DATA_CACHE[symbol].get("last_calc_" + timeframe)
                
                if last_calc and last_update and last_calc >= last_update:
                    # No new data since last calculation, use cached data
                    app_logger.info(f"Using cached {timeframe} data for {symbol}")
                    recalculate = False
        
        if recalculate:
            app_logger.info(f"Calculating {timeframe} indicators for {symbol}")
            
            # Aggregate to the selected timeframe
            if timeframe != "1min":
                rule_map = {
                    "1min": "1min",
                    "5min": "5min",
                    "15min": "15min",
                    "30min": "30min",
                    "1hour": "1H",
                    "4hour": "4H",
                    "1day": "1D"
                }
                rule = rule_map.get(timeframe, "1H")
                
                # Aggregate candles
                agg_df = aggregate_candles(minute_df, rule)
                
                if agg_df.empty:
                    app_logger.warning(f"Aggregation returned empty DataFrame for {symbol} ({timeframe})")
                    return None, {
                        "source": "Technical Indicators",
                        "message": f"Failed to aggregate data to {timeframe}",
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
            else:
                # Use minute data as is
                agg_df = minute_df.copy()
            
            # Reset index to get timestamp as column
            agg_df = agg_df.reset_index()
            
            # Calculate technical indicators
            tech_df = calculate_all_technical_indicators(agg_df, symbol)
            
            # Update cache
            if symbol in MINUTE_DATA_CACHE:
                if "timeframe_data" not in MINUTE_DATA_CACHE[symbol]:
                    MINUTE_DATA_CACHE[symbol]["timeframe_data"] = {}
                
                MINUTE_DATA_CACHE[symbol]["timeframe_data"][timeframe] = tech_df
                MINUTE_DATA_CACHE[symbol]["last_calc_" + timeframe] = datetime.datetime.now()
        else:
            # Use cached data
            tech_df = pd.DataFrame(MINUTE_DATA_CACHE[symbol]["timeframe_data"][timeframe])
        
        # Prepare data for store
        tech_indicators_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timeframe_data": {
                timeframe: tech_df.to_dict("records")
            }
        }
        
        return tech_indicators_data, None
    
    except Exception as e:
        error_msg = f"Error calculating technical indicators: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, {
            "source": "Technical Indicators",
            "message": error_msg,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Combined Options Chain Callback
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
    app_logger.info(f"Updating options chain for {symbol} (trigger: {trigger_id})")
    
    try:
        client = schwab_client_provider()
        if not client:
            error_msg = "Failed to initialize Schwab client"
            app_logger.error(error_msg)
            return None, [], None, "Error: Schwab client initialization failed", {
                "source": "Options Chain",
                "message": error_msg,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        app_logger.info(f"Fetching options chain for {symbol}")
        options_df, expiration_dates, underlying_price, error = get_options_chain_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching options chain: {error}")
            return None, [], None, f"Error: {error}", {
                "source": "Options Chain",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        if options_df.empty or not expiration_dates:
            app_logger.warning(f"No options data available for {symbol}")
            return None, [], None, f"No options data available for {symbol}", None
        
        # Prepare dropdown options
        dropdown_options = [{"label": date, "value": date} for date in expiration_dates]
        
        # Select first expiration date by default
        default_expiration = expiration_dates[0] if expiration_dates else None
        
        # Prepare data for store
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
    
    options = options_data["options"]
    
    # Convert to DataFrame for easier filtering
    options_df = pd.DataFrame(options)
    
    # Filter by expiration date if provided
    if expiration_date and "expirationDate" in options_df.columns:
        options_df = options_df[options_df["expirationDate"] == expiration_date]
    
    # Split into calls and puts
    if "putCall" in options_df.columns:
        calls_df = options_df[options_df["putCall"] == "CALL"]
        puts_df = options_df[options_df["putCall"] == "PUT"]
    else:
        # If putCall column is missing, try to infer from symbol
        if "symbol" in options_df.columns:
            options_df["putCall"] = options_df["symbol"].apply(
                lambda x: "CALL" if "C" in str(x).upper() else ("PUT" if "P" in str(x).upper() else "UNKNOWN")
            )
            calls_df = options_df[options_df["putCall"] == "CALL"]
            puts_df = options_df[options_df["putCall"] == "PUT"]
        else:
            # Can't determine option type
            return [], []
    
    # Sort by strike price
    if "strikePrice" in calls_df.columns:
        calls_df = calls_df.sort_values(by="strikePrice")
    
    if "strikePrice" in puts_df.columns:
        puts_df = puts_df.sort_values(by="strikePrice")
    
    # Filter by option type if "BOTH" is not selected
    if option_type == "CALL":
        puts_df = pd.DataFrame()  # Empty DataFrame for puts
    elif option_type == "PUT":
        calls_df = pd.DataFrame()  # Empty DataFrame for calls
    
    # Convert to records for Dash table
    calls_data = calls_df.to_dict("records") if not calls_df.empty else []
    puts_data = puts_df.to_dict("records") if not puts_df.empty else []
    
    return calls_data, puts_data

# Register recommendation callbacks
register_recommendation_callbacks(app)

# Run the app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

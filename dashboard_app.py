import dash
from dash import dcc, html, dash_table, ctx
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
if not app_logger.hasHandlers():
    # Console handler
    app_handler = logging.StreamHandler()
    app_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    app_handler.setFormatter(app_formatter)
    app_logger.addHandler(app_handler)
    
    # File handler
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"app_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
    
    # Tabs
    dcc.Tabs([
        # Minute Data Tab
        dcc.Tab(label="Minute Data", children=[
            html.Div([
                html.Div([
                    html.Button("Export to CSV", id="export-minute-data-button", n_clicks=0, className="export-button"),
                    dcc.Download(id="download-minute-data-csv")
                ], className="tab-controls"),
                html.Div(id="minute-data-loading", children=[
                    dcc.Loading(
                        id="minute-data-loading-spinner",
                        type="circle",
                        children=html.Div(id="minute-data-container", children=[
                            dash_table.DataTable(
                                id="minute-data-table",
                                page_size=15,
                                style_table={'overflowX': 'auto'},
                                style_cell={
                                    'textAlign': 'left',
                                    'padding': '5px',
                                    'minWidth': '80px', 'width': '80px', 'maxWidth': '120px',
                                    'whiteSpace': 'normal'
                                },
                                style_header={
                                    'backgroundColor': 'rgb(230, 230, 230)',
                                    'fontWeight': 'bold'
                                },
                                # Enable sorting
                                sort_action="native",
                                sort_mode="multi",
                                # Enable filtering
                                filter_action="native",
                                # Styling for filter
                                style_filter={
                                    'backgroundColor': 'rgb(240, 240, 240)',
                                },
                                # Style for filter cells
                                style_filter_conditional=[
                                    {
                                        'if': {'column_id': c},
                                        'textAlign': 'left'
                                    } for c in ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                                ],
                                # Tooltip for filter usage
                                tooltip_header={
                                    'timestamp': 'Filter format: =YYYY-MM-DD for exact date, >YYYY-MM-DD for after date',
                                    'open': 'Filter format: =X for equals, >X for greater than, <X for less than',
                                    'high': 'Filter format: =X for equals, >X for greater than, <X for less than',
                                    'low': 'Filter format: =X for equals, >X for greater than, <X for less than',
                                    'close': 'Filter format: =X for equals, >X for greater than, <X for less than',
                                    'volume': 'Filter format: =X for equals, >X for greater than, <X for less than'
                                },
                                tooltip_delay=0,
                                tooltip_duration=None
                            )
                        ])
                    )
                ])
            ], className="tab-content")
        ]),
        
        # Technical Indicators Tab
        dcc.Tab(label="Technical Indicators", children=[
            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id="tech-indicators-timeframe-dropdown",
                        options=[
                            {"label": "1 Minute", "value": "1min"},
                            {"label": "5 Minutes", "value": "5min"},
                            {"label": "15 Minutes", "value": "15min"},
                            {"label": "30 Minutes", "value": "30min"},
                            {"label": "1 Hour", "value": "1hour"},
                            {"label": "4 Hours", "value": "4hour"},
                            {"label": "1 Day", "value": "1day"}
                        ],
                        value="1min",
                        clearable=False,
                        className="timeframe-dropdown"
                    ),
                    html.Button("Export to CSV", id="export-tech-indicators-button", n_clicks=0, className="export-button"),
                    dcc.Download(id="download-tech-indicators-csv")
                ], className="tab-controls"),
                html.Div(id="tech-indicators-loading", children=[
                    dcc.Loading(
                        id="tech-indicators-loading-spinner",
                        type="circle",
                        children=html.Div(id="tech-indicators-container", children=[
                            dash_table.DataTable(
                                id="tech-indicators-table",
                                page_size=15,
                                style_table={'overflowX': 'auto'},
                                style_cell={
                                    'textAlign': 'left',
                                    'padding': '5px',
                                    'minWidth': '80px', 'width': '80px', 'maxWidth': '120px',
                                    'whiteSpace': 'normal'
                                },
                                style_header={
                                    'backgroundColor': 'rgb(230, 230, 230)',
                                    'fontWeight': 'bold'
                                },
                                # Enable sorting
                                sort_action="native",
                                sort_mode="multi",
                                # Enable filtering
                                filter_action="native",
                                # Styling for filter
                                style_filter={
                                    'backgroundColor': 'rgb(240, 240, 240)',
                                },
                                # Tooltip for filter usage
                                tooltip_header={
                                    'Timestamp': 'Filter format: =YYYY-MM-DD for exact date, >YYYY-MM-DD for after date',
                                },
                                tooltip_delay=0,
                                tooltip_duration=None
                            )
                        ])
                    )
                ])
            ], className="tab-content")
        ]),
        
        # Options Chain Tab
        dcc.Tab(label="Options Chain", children=[
            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id="expiration-date-dropdown",
                        placeholder="Select Expiration Date",
                        className="expiration-dropdown"
                    ),
                    html.Div(id="options-chain-status", className="options-status")
                ], className="tab-controls"),
                html.Div(id="options-chain-loading", children=[
                    dcc.Loading(
                        id="options-chain-loading-spinner",
                        type="circle",
                        children=html.Div(id="options-chain-container", children=[
                            html.Div([
                                html.Div([
                                    html.H3("Calls"),
                                    dash_table.DataTable(
                                        id="calls-table",
                                        page_size=15,
                                        style_table={'overflowX': 'auto'},
                                        style_cell={
                                            'textAlign': 'left',
                                            'padding': '5px',
                                            'minWidth': '80px', 'width': '80px', 'maxWidth': '120px',
                                            'whiteSpace': 'normal'
                                        },
                                        style_header={
                                            'backgroundColor': 'rgb(230, 230, 230)',
                                            'fontWeight': 'bold'
                                        },
                                        # Enable sorting
                                        sort_action="native",
                                        sort_mode="multi",
                                        # Enable filtering
                                        filter_action="native",
                                        # Styling for filter
                                        style_filter={
                                            'backgroundColor': 'rgb(240, 240, 240)',
                                        },
                                        # Tooltip for filter usage
                                        tooltip_delay=0,
                                        tooltip_duration=None
                                    )
                                ], className="calls-container"),
                                html.Div([
                                    html.H3("Puts"),
                                    dash_table.DataTable(
                                        id="puts-table",
                                        page_size=15,
                                        style_table={'overflowX': 'auto'},
                                        style_cell={
                                            'textAlign': 'left',
                                            'padding': '5px',
                                            'minWidth': '80px', 'width': '80px', 'maxWidth': '120px',
                                            'whiteSpace': 'normal'
                                        },
                                        style_header={
                                            'backgroundColor': 'rgb(230, 230, 230)',
                                            'fontWeight': 'bold'
                                        },
                                        # Enable sorting
                                        sort_action="native",
                                        sort_mode="multi",
                                        # Enable filtering
                                        filter_action="native",
                                        # Styling for filter
                                        style_filter={
                                            'backgroundColor': 'rgb(240, 240, 240)',
                                        },
                                        # Tooltip for filter usage
                                        tooltip_delay=0,
                                        tooltip_duration=None
                                    )
                                ], className="puts-container")
                            ], className="options-tables-container")
                        ])
                    )
                ])
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
    
    return ""

# Symbol Selection Callback
@app.callback(
    Output("selected-symbol-store", "data"),
    Input("load-button", "n_clicks"),
    State("symbol-input", "value"),
    prevent_initial_call=True
)
def update_selected_symbol(n_clicks, symbol_value):
    """Updates the selected symbol when the Load button is clicked."""
    if not symbol_value:
        return None
    
    # Normalize symbol (uppercase, trim whitespace)
    symbol = symbol_value.strip().upper()
    
    app_logger.info(f"Symbol selected: {symbol}")
    
    return {"symbol": symbol, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# Minute Data Callback
@app.callback(
    [
        Output("minute-data-store", "data"),
        Output("status-message", "children"),
        Output("error-store", "data", allow_duplicate=True)
    ],
    [
        Input("selected-symbol-store", "data"),
        Input("refresh-button", "n_clicks"),
        Input("update-interval", "n_intervals")
    ],
    prevent_initial_call=True
)
def update_minute_data(selected_symbol, n_refresh, n_intervals):
    """Fetches and updates minute data for the selected symbol."""
    global MINUTE_DATA_CACHE
    
    ctx_msg = dash.callback_context
    trigger_id = ctx_msg.triggered[0]["prop_id"].split(".")[0] if ctx_msg.triggered else None
    
    if not selected_symbol or not selected_symbol.get("symbol"):
        return None, "No symbol selected", None
    
    symbol = selected_symbol["symbol"]
    app_logger.info(f"Updating minute data for {symbol} (trigger: {trigger_id})")
    
    # Initialize status message
    status_message = f"Loading data for {symbol}..."
    
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
        
        # Check if we need a full refresh or incremental update
        force_refresh = trigger_id in ["load-button", "refresh-button"]
        
        # Check if symbol exists in cache
        if symbol in MINUTE_DATA_CACHE and not force_refresh:
            # Get last update timestamp
            last_update = MINUTE_DATA_CACHE[symbol].get("last_update")
            
            if last_update:
                # Calculate time since last update
                time_since_update = datetime.datetime.now() - last_update
                
                # If cache is too old, force a refresh
                if time_since_update.total_seconds() > CACHE_CONFIG["max_age_hours"] * 3600:
                    app_logger.info(f"Cache for {symbol} is too old ({time_since_update.total_seconds()/3600:.2f} hours), forcing refresh")
                    force_refresh = True
                else:
                    # Incremental update - fetch only new data since last update
                    # Add a buffer to avoid gaps
                    buffer_minutes = CACHE_CONFIG["buffer_minutes"]
                    since_timestamp = last_update - datetime.timedelta(minutes=buffer_minutes)
                    
                    app_logger.info(f"Performing incremental update for {symbol} since {since_timestamp}")
                    
                    # Fetch new data
                    new_data_df, error = get_minute_data(client, symbol, since_timestamp=since_timestamp)
                    
                    if error:
                        app_logger.error(f"Error fetching incremental data: {error}")
                        return None, f"Error: {error}", {
                            "source": "Minute Data",
                            "message": error,
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    
                    if not new_data_df.empty:
                        # Merge with existing data
                        existing_df = MINUTE_DATA_CACHE[symbol]["data"]
                        
                        # Convert timestamp to datetime if it's not already
                        if "timestamp" in new_data_df.columns and not pd.api.types.is_datetime64_any_dtype(new_data_df["timestamp"]):
                            new_data_df["timestamp"] = pd.to_datetime(new_data_df["timestamp"])
                        
                        # Remove duplicates (keep newer data)
                        combined_df = pd.concat([existing_df, new_data_df])
                        combined_df = combined_df.drop_duplicates(subset=["timestamp"], keep="last")
                        
                        # Sort by timestamp (descending)
                        combined_df = combined_df.sort_values("timestamp", ascending=False)
                        
                        # Update cache
                        MINUTE_DATA_CACHE[symbol]["data"] = combined_df
                        MINUTE_DATA_CACHE[symbol]["last_update"] = datetime.datetime.now()
                        
                        app_logger.info(f"Added {len(new_data_df)} new data points for {symbol}")
                        status_message = f"Updated {symbol} data with {len(new_data_df)} new points"
                    else:
                        app_logger.info(f"No new data for {symbol}")
                        status_message = f"No new data available for {symbol}"
                    
                    # Prepare data for store
                    minute_data = {
                        "symbol": symbol,
                        "data": MINUTE_DATA_CACHE[symbol]["data"].to_dict("records"),
                        "last_update": MINUTE_DATA_CACHE[symbol]["last_update"].strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    return minute_data, status_message, None
        
        # Full refresh or symbol not in cache
        if force_refresh or symbol not in MINUTE_DATA_CACHE:
            app_logger.info(f"Performing full refresh for {symbol}")
            
            # Fetch full data (90 days)
            days_history = 90
            minute_data_df, error = get_minute_data(client, symbol, days_history=days_history)
            
            if error:
                app_logger.error(f"Error fetching full data: {error}")
                return None, f"Error: {error}", {
                    "source": "Minute Data",
                    "message": error,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # Update cache
            MINUTE_DATA_CACHE[symbol] = {
                "data": minute_data_df,
                "last_update": datetime.datetime.now(),
                "timeframe_data": {}  # Will be populated by technical indicators callback
            }
            
            app_logger.info(f"Fetched {len(minute_data_df)} data points for {symbol}")
            status_message = f"Loaded {len(minute_data_df)} data points for {symbol}"
            
            # Prepare data for store
            minute_data = {
                "symbol": symbol,
                "data": minute_data_df.to_dict("records"),
                "last_update": MINUTE_DATA_CACHE[symbol]["last_update"].strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return minute_data, status_message, None
    
    except Exception as e:
        error_msg = f"Error updating minute data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, f"Error: {str(e)}", {
            "source": "Minute Data",
            "message": error_msg,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # This should not be reached, but just in case
    return None, "No data available", None

# Technical Indicators Callback
@app.callback(
    [
        Output("tech-indicators-store", "data"),
        Output("error-store", "data", allow_duplicate=True)
    ],
    [
        Input("minute-data-store", "data"),
        Input("tech-indicators-timeframe-dropdown", "value")
    ],
    prevent_initial_call=True
)
def update_technical_indicators(minute_data, timeframe):
    """Calculates technical indicators for the selected timeframe."""
    global MINUTE_DATA_CACHE
    
    if not minute_data or not minute_data.get("symbol") or not minute_data.get("data"):
        return None, None
    
    symbol = minute_data["symbol"]
    app_logger.info(f"Updating technical indicators for {symbol} ({timeframe})")
    
    try:
        # Convert data back to DataFrame
        minute_df = pd.DataFrame(minute_data["data"])
        
        # Ensure timestamp is datetime
        if "timestamp" in minute_df.columns and not pd.api.types.is_datetime64_any_dtype(minute_df["timestamp"]):
            minute_df["timestamp"] = pd.to_datetime(minute_df["timestamp"])
        
        # Set timestamp as index for aggregation
        minute_df = minute_df.set_index("timestamp")
        
        # Check if we already have this timeframe in cache
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

# Options Chain Callback
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
        
        # Fetch options chain data
        options_df, expiration_dates, error = get_options_chain_data(client, symbol)
        
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
        
        # Get underlying price
        underlying_price = None
        if "underlyingPrice" in options_df.columns:
            underlying_price = options_df["underlyingPrice"].iloc[0]
        
        # Create dropdown options
        dropdown_options = [{"label": date, "value": date} for date in expiration_dates]
        
        # Set default value to first expiration date
        default_value = expiration_dates[0] if expiration_dates else None
        
        # Prepare data for store
        options_chain_data = {
            "symbol": symbol,
            "options": options_df.to_dict("records"),
            "expiration_dates": expiration_dates,
            "underlyingPrice": underlying_price
        }
        
        status_message = f"Loaded {len(options_df)} option contracts for {symbol}"
        app_logger.info(status_message)
        
        return options_chain_data, dropdown_options, default_value, status_message, None
    
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
    """Updates the minute data table with the latest data."""
    if not minute_data or not minute_data.get("data"):
        return [], []
    
    data = minute_data["data"]
    
    # Create columns configuration
    columns = [
        {"name": "Timestamp", "id": "timestamp"},
        {"name": "Open", "id": "open", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "High", "id": "high", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Low", "id": "low", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Close", "id": "close", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Volume", "id": "volume", "type": "numeric", "format": {"specifier": ",d"}}
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
    """Updates the technical indicators table with the latest data."""
    if not tech_indicators_data or not tech_indicators_data.get("timeframe_data"):
        return [], []
    
    timeframe = tech_indicators_data.get("timeframe", "1min")
    timeframe_data = tech_indicators_data["timeframe_data"].get(timeframe, [])
    
    if not timeframe_data:
        return [], []
    
    # Create columns configuration
    first_row = timeframe_data[0] if timeframe_data else {}
    columns = []
    
    # Add timestamp column first
    if "timestamp" in first_row:
        columns.append({"name": "Timestamp", "id": "timestamp"})
    
    # Add OHLCV columns next
    for col in ["open", "high", "low", "close", "volume"]:
        if col in first_row:
            col_name = col.capitalize()
            col_format = {"specifier": ".2f"} if col != "volume" else {"specifier": ",d"}
            columns.append({"name": col_name, "id": col, "type": "numeric", "format": col_format})
    
    # Add technical indicator columns
    for col in first_row:
        if col not in ["timestamp", "open", "high", "low", "close", "volume"]:
            columns.append({"name": col, "id": col, "type": "numeric", "format": {"specifier": ".4f"}})
    
    return timeframe_data, columns

# Options Chain Tables Callback
@app.callback(
    [
        Output("calls-table", "data"),
        Output("calls-table", "columns"),
        Output("puts-table", "data"),
        Output("puts-table", "columns")
    ],
    [
        Input("options-chain-store", "data"),
        Input("expiration-date-dropdown", "value")
    ],
    prevent_initial_call=True
)
def update_options_tables(options_chain_data, selected_expiration):
    """Updates the options chain tables with the latest data."""
    if not options_chain_data or not options_chain_data.get("options") or not selected_expiration:
        return [], [], [], []
    
    options_data = options_chain_data["options"]
    
    # Filter by expiration date
    filtered_options = [opt for opt in options_data if opt.get("expirationDate") == selected_expiration]
    
    # Separate calls and puts
    calls = [opt for opt in filtered_options if opt.get("putCall") == "CALL"]
    puts = [opt for opt in filtered_options if opt.get("putCall") == "PUT"]
    
    # Create columns configuration
    columns = [
        {"name": "Strike", "id": "strikePrice", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Symbol", "id": "symbol"},
        {"name": "Last", "id": "lastPrice", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Bid", "id": "bidPrice", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Ask", "id": "askPrice", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Change", "id": "netChange", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Volume", "id": "totalVolume", "type": "numeric", "format": {"specifier": ",d"}},
        {"name": "Open Int", "id": "openInterest", "type": "numeric", "format": {"specifier": ",d"}},
        {"name": "IV", "id": "volatility", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Delta", "id": "delta", "type": "numeric", "format": {"specifier": ".4f"}},
        {"name": "Gamma", "id": "gamma", "type": "numeric", "format": {"specifier": ".4f"}},
        {"name": "Theta", "id": "theta", "type": "numeric", "format": {"specifier": ".4f"}},
        {"name": "Vega", "id": "vega", "type": "numeric", "format": {"specifier": ".4f"}}
    ]
    
    return calls, columns, puts, columns

# Export Minute Data Callback
@app.callback(
    Output("download-minute-data-csv", "data"),
    Input("export-minute-data-button", "n_clicks"),
    State("minute-data-store", "data"),
    prevent_initial_call=True
)
def export_minute_data(n_clicks, minute_data):
    """Exports minute data to CSV."""
    if not minute_data or not minute_data.get("data"):
        return None
    
    symbol = minute_data.get("symbol", "unknown")
    data = minute_data["data"]
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Create CSV string
    csv_string = df.to_csv(index=False)
    
    # Create download data
    return dict(
        content=csv_string,
        filename=f"{symbol}_minute_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        type="text/csv"
    )

# Export Technical Indicators Callback
@app.callback(
    Output("download-tech-indicators-csv", "data"),
    Input("export-tech-indicators-button", "n_clicks"),
    [
        State("tech-indicators-store", "data"),
        State("tech-indicators-timeframe-dropdown", "value")
    ],
    prevent_initial_call=True
)
def export_tech_indicators(n_clicks, tech_indicators_data, timeframe):
    """Exports technical indicators to CSV."""
    if not tech_indicators_data or not tech_indicators_data.get("timeframe_data"):
        return None
    
    symbol = tech_indicators_data.get("symbol", "unknown")
    timeframe_data = tech_indicators_data["timeframe_data"].get(timeframe, [])
    
    if not timeframe_data:
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(timeframe_data)
    
    # Create CSV string
    csv_string = df.to_csv(index=False)
    
    # Create download data
    return dict(
        content=csv_string,
        filename=f"{symbol}_{timeframe}_indicators_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        type="text/csv"
    )

# Register recommendation tab callbacks
register_recommendation_callbacks(app)

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")

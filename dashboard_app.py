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
        
        # Check if we need to fetch new data
        force_refresh = trigger_id in ["refresh-button", "load-button"]
        
        if symbol in MINUTE_DATA_CACHE and not force_refresh:
            # Check if cache is still valid
            last_update = MINUTE_DATA_CACHE[symbol].get("last_update")
            if last_update:
                age = datetime.datetime.now() - last_update
                if age.total_seconds() < CACHE_CONFIG["update_interval_seconds"]:
                    # Cache is still fresh, use it
                    app_logger.info(f"Using cached minute data for {symbol} (age: {age.total_seconds():.1f}s)")
                    
                    # Prepare data for store
                    minute_data = {
                        "symbol": symbol,
                        "data": MINUTE_DATA_CACHE[symbol]["data"].to_dict("records"),
                        "last_update": MINUTE_DATA_CACHE[symbol]["last_update"].strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    status_message = f"Using cached data for {symbol} (updated {age.total_seconds():.1f}s ago)"
                    return minute_data, status_message, None
        
        # Fetch new data
        app_logger.info(f"Fetching minute data for {symbol}")
        # Use the days_history from CACHE_CONFIG (now set to 60 days)
        minute_df, error = get_minute_data(client, symbol, days_history=CACHE_CONFIG["days_history"])
        
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
        
        # Update cache
        MINUTE_DATA_CACHE[symbol] = {
            "data": minute_df,
            "last_update": datetime.datetime.now()
        }
        
        # Prepare data for store
        minute_data = {
            "symbol": symbol,
            "data": minute_df.to_dict("records"),
            "last_update": MINUTE_DATA_CACHE[symbol]["last_update"].strftime("%Y-%m-%d %H:%M:%S")
        }
        
        status_message = f"Loaded {len(minute_df)} minute bars for {symbol}"
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
        
        # Prepare dropdown options
        dropdown_options = [{"label": date, "value": date} for date in expiration_dates]
        
        # Select first expiration date by default
        default_expiration = expiration_dates[0] if expiration_dates else None
        
        # Prepare data for store
        options_data = {
            "symbol": symbol,
            "data": options_df.to_dict("records"),
            "expiration_dates": expiration_dates,
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        status_message = f"Loaded {len(options_df)} option contracts for {symbol}"
        app_logger.info(status_message)
        
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
    first_row = data[0] if data else {}
    columns = [{"name": k, "id": k} for k in first_row.keys()]
    
    return data, columns

# Options Chain Tables Callback
@app.callback(
    Output("calls-table", "data"),
    Output("calls-table", "columns"),
    Output("puts-table", "data"),
    Output("puts-table", "columns"),
    Input("options-chain-store", "data"),
    Input("expiration-date-dropdown", "value"),
    prevent_initial_call=True
)
def update_options_tables(options_data, selected_expiration):
    """Updates the calls and puts tables with the fetched options data."""
    if not options_data or not options_data.get("data") or not selected_expiration:
        return [], [], [], []
    
    # Convert to DataFrame for easier filtering
    options_df = pd.DataFrame(options_data["data"])
    
    # Filter by expiration date
    filtered_df = options_df[options_df["expirationDate"] == selected_expiration]
    
    # Split into calls and puts
    calls_df = filtered_df[filtered_df["putCall"] == "CALL"].copy()
    puts_df = filtered_df[filtered_df["putCall"] == "PUT"].copy()
    
    # Sort by strike price
    calls_df = calls_df.sort_values(by="strikePrice")
    puts_df = puts_df.sort_values(by="strikePrice")
    
    # Define columns to display
    display_columns = [
        "symbol", "strikePrice", "lastPrice", "bidPrice", "askPrice", 
        "delta", "gamma", "theta", "vega", "rho", "openInterest", "totalVolume"
    ]
    
    # Filter columns that exist in the DataFrame
    display_columns = [col for col in display_columns if col in calls_df.columns]
    
    # Create column definitions
    columns = [{"name": col, "id": col} for col in display_columns]
    
    # Convert to records for table
    calls_data = calls_df[display_columns].to_dict("records") if not calls_df.empty else []
    puts_data = puts_df[display_columns].to_dict("records") if not puts_df.empty else []
    
    return calls_data, columns, puts_data, columns

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
    
    # Return download data
    return dict(
        content=csv_string,
        filename=f"{symbol}_minute_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

# Export Technical Indicators Callback
@app.callback(
    Output("download-tech-indicators-csv", "data"),
    Input("export-tech-indicators-button", "n_clicks"),
    State("tech-indicators-store", "data"),
    prevent_initial_call=True
)
def export_tech_indicators(n_clicks, tech_indicators_data):
    """Exports technical indicators to CSV."""
    if not tech_indicators_data or not tech_indicators_data.get("timeframe_data"):
        return None
    
    symbol = tech_indicators_data.get("symbol", "unknown")
    timeframe = tech_indicators_data.get("timeframe", "1min")
    data = tech_indicators_data["timeframe_data"].get(timeframe, [])
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Create CSV string
    csv_string = df.to_csv(index=False)
    
    # Return download data
    return dict(
        content=csv_string,
        filename=f"{symbol}_{timeframe}_indicators_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

# Register recommendation callbacks
register_recommendation_callbacks(app)

# Run the app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

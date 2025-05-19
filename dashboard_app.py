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
                                }
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
                                }
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
                                        }
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
                                        }
                                    )
                                ], className="puts-container")
                            ], className="options-tables-container")
                        ])
                    )
                ])
            ], className="tab-content")
        ])
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
def update_selected_symbol(n_clicks, symbol_input):
    if n_clicks > 0 and symbol_input:
        symbol = symbol_input.strip().upper()
        app_logger.info(f"Symbol selected: {symbol}")
        return symbol
    return dash.no_update

# Refresh Button Callback
@app.callback(
    Output("refresh-button", "n_clicks"),
    Input("refresh-button", "n_clicks"),
    State("selected-symbol-store", "data"),
    prevent_initial_call=True
)
def handle_refresh_click(n_clicks, selected_symbol):
    if n_clicks > 0 and selected_symbol:
        app_logger.info(f"Manual refresh requested for {selected_symbol}")
        
        # Clear cache for this symbol to force a full refresh
        if selected_symbol in MINUTE_DATA_CACHE:
            del MINUTE_DATA_CACHE[selected_symbol]
            app_logger.info(f"Cleared cache for {selected_symbol} due to manual refresh")
        
        # n_clicks will be reset to 0 by the return value
        return 0
    
    return dash.no_update

# Periodic Update Callback
@app.callback(
    Output("update-interval", "disabled"),
    Input("update-interval", "n_intervals"),
    State("selected-symbol-store", "data"),
    prevent_initial_call=True
)
def handle_periodic_update(n_intervals, selected_symbol):
    if n_intervals > 0 and selected_symbol:
        app_logger.info(f"Periodic update triggered for {selected_symbol} (interval #{n_intervals})")
        
        # Check if we have cached data for this symbol
        if selected_symbol in MINUTE_DATA_CACHE:
            # Trigger data update (actual update will happen in the data tabs callback)
            # This is just to log that the interval fired
            app_logger.info(f"Periodic update will refresh data for {selected_symbol}")
        
    # Always keep the interval enabled
    return False

# Data Tabs Update Callback
@app.callback(
    [Output("minute-data-table", "columns"),
     Output("minute-data-table", "data"),
     Output("tech-indicators-store", "data"),
     Output("error-store", "data")],
    [Input("selected-symbol-store", "data"),
     Input("update-interval", "n_intervals"),
     Input("refresh-button", "n_clicks")],
    prevent_initial_call=True
)
def update_data_tabs(selected_symbol, n_intervals, refresh_n_clicks):
    trigger = ctx.triggered_id
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_event_to_send = None
    
    if not selected_symbol:
        return [], [], {}, error_event_to_send
    
    app_logger.info(f"UpdateDataTabs: Triggered by {trigger} for {selected_symbol}")
    
    # Get Schwab client
    client_to_use = schwab_client_provider()
    if not client_to_use:
        error_msg = "Schwab client initialization failed. Please check authentication."
        app_logger.error(f"UpdateDataTabs for {selected_symbol}: {error_msg}")
        error_event_to_send = {"source": f"ClientInit-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
        return [], [], {}, error_event_to_send
    
    # Initialize variables for minute data
    minute_cols = []
    minute_data = []
    tech_data_store = {}
    
    # Check if we have cached data for this symbol
    if selected_symbol in MINUTE_DATA_CACHE and trigger != "refresh-button":
        cache_entry = MINUTE_DATA_CACHE[selected_symbol]
        df = cache_entry['data']
        last_update = cache_entry['last_update']
        
        # Check if cache is too old (force full refresh if older than max_age_hours)
        cache_age_hours = (datetime.datetime.now() - last_update).total_seconds() / 3600
        if cache_age_hours > CACHE_CONFIG['max_age_hours']:
            app_logger.info(f"Cache for {selected_symbol} is {cache_age_hours:.2f} hours old (max: {CACHE_CONFIG['max_age_hours']}). Forcing full refresh.")
            # Clear cache for this symbol
            del MINUTE_DATA_CACHE[selected_symbol]
            # Fetch full history
            df, error = get_minute_data(client_to_use, selected_symbol, days_history=90)
            
            if error:
                error_msg = f"Data fetch error: {error}"
                app_logger.error(f"UpdateDataTabs for {selected_symbol}: {error_msg}")
                error_event_to_send = {"source": f"DataFetch-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                return [], [], {}, error_event_to_send
            elif df.empty:
                app_logger.warning(f"UpdateDataTabs: No minute data returned for {selected_symbol}.")
                return [], [], {}, error_event_to_send
            else:
                # Initialize cache for this symbol
                MINUTE_DATA_CACHE[selected_symbol] = {
                    'data': df,
                    'last_update': datetime.datetime.now(),
                    'timeframe_data': {}
                }
                app_logger.info(f"Created new minute data cache with {len(df)} rows after max age refresh")
        else:
            # Cache is still valid, check if we need to fetch incremental updates
            if trigger == "update-interval" or trigger == "selected-symbol-store":
                # Calculate time since last update
                since_timestamp = last_update - datetime.timedelta(minutes=CACHE_CONFIG['buffer_minutes'])
                
                # Fetch only new data since last update
                app_logger.info(f"Fetching incremental data for {selected_symbol} since {since_timestamp}")
                new_df, error = get_minute_data(client_to_use, selected_symbol, days_history=1, since_timestamp=since_timestamp)
                
                if error:
                    error_msg = f"Data fetch error for incremental update: {error}"
                    app_logger.error(f"UpdateDataTabs for {selected_symbol}: {error_msg}")
                    error_event_to_send = {"source": f"IncrementalFetch-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                    # Continue with cached data
                elif not new_df.empty:
                    # Merge new data with cached data
                    app_logger.info(f"Merging {len(new_df)} new rows with {len(df)} cached rows")
                    df = pd.concat([df, new_df], ignore_index=False)
                    df = df.drop_duplicates(subset=["timestamp"])
                    df = df.sort_values(by="timestamp", ascending=False)
                    
                    # Update cache with merged data
                    MINUTE_DATA_CACHE[selected_symbol]['data'] = df
                    MINUTE_DATA_CACHE[selected_symbol]['last_update'] = datetime.datetime.now()
                    app_logger.info(f"Updated minute data cache, now has {len(df)} rows")
    else:
        # No cached data or refresh button clicked, fetch full history
        app_logger.info(f"No cache or refresh requested for {selected_symbol}. Fetching full history.")
        df, error = get_minute_data(client_to_use, selected_symbol, days_history=90)
        
        if error:
            error_msg = f"Data fetch error: {error}"
            app_logger.error(f"UpdateDataTabs for {selected_symbol}: {error_msg}")
            error_event_to_send = {"source": f"DataFetch-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
            return [], [], {}, error_event_to_send
        elif df.empty:
            app_logger.warning(f"UpdateDataTabs: No minute data returned for {selected_symbol}.")
            return [], [], {}, error_event_to_send
        else:
            # Initialize cache for this symbol
            MINUTE_DATA_CACHE[selected_symbol] = {
                'data': df,
                'last_update': datetime.datetime.now(),
                'timeframe_data': {}
            }
            app_logger.info(f"Created new minute data cache with {len(df)} rows")
    
    # Prepare minute data for display
    if not df.empty:
        app_logger.info(f"UpdateDataTabs: Preparing minute data for display ({len(df)} rows)")
        
        # Create a copy for display to avoid modifying the cached dataframe
        df_for_display = df.copy()
        
        # Format timestamp for display
        if "timestamp" in df_for_display.columns:
            df_for_display["timestamp"] = pd.to_datetime(df_for_display["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Sort by timestamp descending for display (most recent first)
        if "timestamp" in df_for_display.columns:
            df_for_display = df_for_display.sort_values(by="timestamp", ascending=False)
        
        # Format numeric columns
        for col in df_for_display.columns:
            if col != "timestamp" and pd.api.types.is_numeric_dtype(df_for_display[col]):
                df_for_display[col] = df_for_display[col].round(2)
        
        # Prepare data for Dash table
        minute_data = df_for_display.to_dict("records")
        minute_cols = [{"name": col, "id": col} for col in df_for_display.columns]
        
        app_logger.info(f"UpdateDataTabs: Minute data prepared with {len(minute_data)} rows and {len(minute_cols)} columns")
    
    # Calculate technical indicators for different timeframes
    # Only recalculate if we have new data or if timeframe_data is empty
    if not df.empty:
        # Check if we need to recalculate technical indicators
        recalculate_indicators = False
        
        # If we don't have timeframe data in cache or we have new data, recalculate
        if 'timeframe_data' not in MINUTE_DATA_CACHE[selected_symbol] or not MINUTE_DATA_CACHE[selected_symbol]['timeframe_data']:
            recalculate_indicators = True
            app_logger.info(f"Recalculating all technical indicators (no cached indicators)")
        elif trigger == "update-interval" and not new_df.empty:
            recalculate_indicators = True
            app_logger.info(f"Recalculating technical indicators due to new data")
        elif trigger == "refresh-button":
            recalculate_indicators = True
            app_logger.info(f"Recalculating technical indicators due to manual refresh")
        
        if recalculate_indicators:
            app_logger.info(f"UpdateDataTabs: Calculating technical indicators for {selected_symbol}...")
            
            # Ensure we have a proper DatetimeIndex
            df_for_ta = df.copy()
            if "timestamp" in df_for_ta.columns and not isinstance(df_for_ta.index, pd.DatetimeIndex):
                try:
                    df_for_ta["timestamp"] = pd.to_datetime(df_for_ta["timestamp"])
                    df_for_ta = df_for_ta.set_index("timestamp")
                except Exception as e:
                    error_msg = f"Failed to convert 'timestamp' to DatetimeIndex for tech indicators: {e}"
                    app_logger.error(f"UpdateDataTabs (TechInd-Format) for {selected_symbol}: {error_msg}")
                    error_event_to_send = {"source": f"TechInd-Format-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                    return minute_cols, minute_data, {}, error_event_to_send
            
            # Ensure column names are lowercase for technical analysis functions
            df_for_ta.columns = [col.lower() for col in df_for_ta.columns]
            
            # Initialize timeframe data dictionary if not exists
            if 'timeframe_data' not in MINUTE_DATA_CACHE[selected_symbol]:
                MINUTE_DATA_CACHE[selected_symbol]['timeframe_data'] = {}
            
            # Calculate for each timeframe
            timeframes = {
                "1min": "1min",
                "5min": "5min",
                "15min": "15min",
                "30min": "30min",
                "1hour": "1H",
                "4hour": "4H",
                "1day": "1D"
            }
            
            tech_data_by_timeframe = {}
            
            try:
                # 1-minute (original data)
                app_logger.info(f"UpdateDataTabs: Calculating 1-minute indicators for {selected_symbol}...")
                indicators_1min = calculate_all_technical_indicators(df_for_ta, symbol=selected_symbol)
                if isinstance(indicators_1min, pd.DataFrame) and not indicators_1min.empty:
                    # Format for display and storage
                    indicators_1min_display = indicators_1min.copy()
                    indicators_1min_display.index.name = "Timestamp"
                    indicators_1min_display = indicators_1min_display.reset_index()
                    indicators_1min_display["Timestamp"] = indicators_1min_display["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                    tech_data_by_timeframe["1min"] = indicators_1min_display.to_dict("records")
                    app_logger.info(f"UpdateDataTabs: Prepared {len(tech_data_by_timeframe['1min'])} 1-minute indicator rows.")
                else:
                    app_logger.warning(f"UpdateDataTabs: No valid 1-minute indicators calculated for {selected_symbol}.")
                
                # Other timeframes
                for timeframe_key, resample_rule in timeframes.items():
                    if timeframe_key == "1min":
                        continue  # Already calculated above
                    
                    app_logger.info(f"UpdateDataTabs: Calculating {timeframe_key} indicators for {selected_symbol}...")
                    
                    # Resample to the target timeframe
                    resampled_df = aggregate_candles(df_for_ta, rule=resample_rule)
                    
                    if not resampled_df.empty:
                        # Calculate indicators on the resampled data
                        indicators_df = calculate_all_technical_indicators(resampled_df, symbol=f"{selected_symbol}_{timeframe_key}")
                        
                        if isinstance(indicators_df, pd.DataFrame) and not indicators_df.empty:
                            # Format for display and storage
                            indicators_display = indicators_df.copy()
                            indicators_display.index.name = "Timestamp"
                            indicators_display = indicators_display.reset_index()
                            indicators_display["Timestamp"] = indicators_display["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                            tech_data_by_timeframe[timeframe_key] = indicators_display.to_dict("records")
                            app_logger.info(f"UpdateDataTabs: Prepared {len(tech_data_by_timeframe[timeframe_key])} {timeframe_key} indicator rows.")
                        else:
                            app_logger.warning(f"UpdateDataTabs: No valid {timeframe_key} indicators calculated for {selected_symbol}.")
                    else:
                        app_logger.warning(f"UpdateDataTabs: Resampling to {timeframe_key} resulted in empty DataFrame for {selected_symbol}.")
                
                # Update cache with calculated indicators
                MINUTE_DATA_CACHE[selected_symbol]['timeframe_data'] = tech_data_by_timeframe
                app_logger.info(f"Updated technical indicators cache for {selected_symbol} with {len(tech_data_by_timeframe)} timeframes")
                
                # Set the return value
                tech_data_store = tech_data_by_timeframe
                
            except Exception as e:
                error_msg = f"Error calculating technical indicators: {str(e)}"
                app_logger.exception(f"UpdateDataTabs (TechInd-Calc) for {selected_symbol}: {error_msg}")
                error_event_to_send = {"source": f"TechInd-Calc-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                # Continue with any indicators we were able to calculate
                tech_data_store = tech_data_by_timeframe
        else:
            # Use cached technical indicators
            app_logger.info(f"Using cached technical indicators for {selected_symbol}")
            tech_data_store = MINUTE_DATA_CACHE[selected_symbol]['timeframe_data']
    
    return minute_cols, minute_data, tech_data_store, error_event_to_send

# Technical Indicators Table Update Callback
@app.callback(
    [Output("tech-indicators-table", "columns"),
     Output("tech-indicators-table", "data")],
    [Input("tech-indicators-store", "data"),
     Input("tech-indicators-timeframe-dropdown", "value")]
)
def update_tech_indicators_table(tech_data_store, selected_timeframe):
    if not tech_data_store or not selected_timeframe or selected_timeframe not in tech_data_store:
        return [], []
    
    # Get data for the selected timeframe
    timeframe_data = tech_data_store[selected_timeframe]
    
    if not timeframe_data:
        return [], []
    
    # Create a sample record to extract column names
    sample_record = timeframe_data[0]
    columns = [{"name": col, "id": col} for col in sample_record.keys()]
    
    return columns, timeframe_data

# Options Chain Callback
@app.callback(
    [Output("expiration-date-dropdown", "options"),
     Output("expiration-date-dropdown", "value"),
     Output("options-chain-status", "children"),
     Output("calls-table", "columns"),
     Output("calls-table", "data"),
     Output("puts-table", "columns"),
     Output("puts-table", "data"),
     Output("options-chain-store", "data"),
     Output("error-store", "data", allow_duplicate=True)],
    [Input("selected-symbol-store", "data"),
     Input("expiration-date-dropdown", "value")],
    prevent_initial_call=True
)
def update_options_chain(selected_symbol, selected_expiration):
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not selected_symbol:
        return [], None, "", [], [], [], [], [], dash.no_update
    
    # Get Schwab client
    client_to_use = schwab_client_provider()
    if not client_to_use:
        error_msg = "Schwab client initialization failed. Please check authentication."
        app_logger.error(f"OptionsChain for {selected_symbol}: {error_msg}")
        return [], None, f"Error: {error_msg}", [], [], [], [], [], {"source": f"ClientInit-Options-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
    
    try:
        # Fetch options chain data
        app_logger.info(f"OptionsChain: Fetching options chain for {selected_symbol}")
        options_data, expiration_dates, error = get_options_chain_data(client_to_use, selected_symbol)
        
        if error:
            error_msg = f"Error fetching options chain: {error}"
            app_logger.error(f"OptionsChain for {selected_symbol}: {error_msg}")
            return [], None, f"Error: {error_msg}", [], [], [], [], [], {"source": f"OptionsFetch-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
        
        # Format expiration dates for dropdown
        expiration_options = []
        for date_str in expiration_dates:
            try:
                # Parse the date string to a datetime object
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                # Format it for display
                display_date = date_obj.strftime("%b %d, %Y")
                expiration_options.append({"label": display_date, "value": date_str})
            except Exception as e:
                app_logger.error(f"OptionsChain: Error formatting expiration date {date_str}: {e}")
                # Use the original string if parsing fails
                expiration_options.append({"label": date_str, "value": date_str})
        
        # Sort expiration dates (nearest first)
        expiration_options.sort(key=lambda x: x["value"])
        
        # If no expiration is selected or the selected one is not in the list, use the first one
        if not selected_expiration or selected_expiration not in [opt["value"] for opt in expiration_options]:
            selected_expiration = expiration_options[0]["value"] if expiration_options else None
        
        if not selected_expiration:
            app_logger.warning(f"OptionsChain: No expiration dates available for {selected_symbol}")
            return expiration_options, None, f"No options available for {selected_symbol}", [], [], [], [], [], dash.no_update
        
        # Filter options for the selected expiration date
        filtered_options = options_data[options_data["expirationDate"] == selected_expiration]
        
        if filtered_options.empty:
            app_logger.warning(f"OptionsChain: No options found for {selected_symbol} with expiration {selected_expiration}")
            return expiration_options, selected_expiration, f"No options found for expiration {selected_expiration}", [], [], [], [], [], dash.no_update
        
        # Split into calls and puts
        calls_df = filtered_options[filtered_options["putCall"] == "CALL"]
        puts_df = filtered_options[filtered_options["putCall"] == "PUT"]
        
        # Sort by strike price
        calls_df = calls_df.sort_values(by="strikePrice")
        puts_df = puts_df.sort_values(by="strikePrice")
        
        # Format for display
        display_columns = [
            "strikePrice", "symbol", "bid", "ask", "last", "totalVolume", 
            "openInterest", "delta", "gamma", "theta", "vega", "rho", "theoreticalVolatility"
        ]
        
        # Rename columns for better display
        column_rename = {
            "strikePrice": "Strike",
            "symbol": "Symbol",
            "bid": "Bid",
            "ask": "Ask",
            "last": "Last",
            "totalVolume": "Volume",
            "openInterest": "OI",
            "delta": "Delta",
            "gamma": "Gamma",
            "theta": "Theta",
            "vega": "Vega",
            "rho": "Rho",
            "theoreticalVolatility": "IV"
        }
        
        # Apply renaming and select columns
        calls_display = calls_df[display_columns].rename(columns=column_rename)
        puts_display = puts_df[display_columns].rename(columns=column_rename)
        
        # Format numeric columns
        for df in [calls_display, puts_display]:
            for col in df.columns:
                if col != "Symbol" and pd.api.types.is_numeric_dtype(df[col]):
                    if col in ["Delta", "Gamma", "Theta", "Vega", "Rho", "IV"]:
                        df[col] = df[col].round(4)
                    else:
                        df[col] = df[col].round(2)
        
        # Prepare data for Dash tables
        calls_columns = [{"name": col, "id": col} for col in calls_display.columns]
        puts_columns = [{"name": col, "id": col} for col in puts_display.columns]
        
        calls_data = calls_display.to_dict("records")
        puts_data = puts_display.to_dict("records")
        
        # Create status message
        status_msg = f"Options chain for {selected_symbol} loaded. Calls: {len(calls_data)}, Puts: {len(puts_data)}"
        app_logger.info(f"OptionsChain: {status_msg}")
        
        # Store contract keys for streaming
        contract_keys = set()
        for df in [calls_df, puts_df]:
            if "symbol" in df.columns:
                contract_keys.update(df["symbol"].tolist())
        
        return expiration_options, selected_expiration, status_msg, calls_columns, calls_data, puts_columns, puts_data, list(contract_keys) if contract_keys else [], dash.no_update
        
    except Exception as e:
        error_msg = f"Error in options chain processing: {str(e)}"
        app_logger.exception(f"OptionsChain for {selected_symbol}: {error_msg}")
        return [], None, f"Error: {error_msg}", [], [], [], [], [], {"source": f"OptionsProcess-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}

# --- CSV Export Callbacks ---
@app.callback(
    Output("download-minute-data-csv", "data"),
    Input("export-minute-data-button", "n_clicks"),
    State("minute-data-table", "data"),
    State("selected-symbol-store", "data"),
    prevent_initial_call=True
)
def export_minute_data_to_csv(n_clicks, minute_data, selected_symbol):
    if n_clicks == 0 or not minute_data:
        return dash.no_update
    
    try:
        app_logger.info(f"Exporting minute data to CSV for {selected_symbol}...")
        df = pd.DataFrame(minute_data)
        
        # Generate filename with symbol and current timestamp
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{selected_symbol}_minute_data_{timestamp_str}.csv"
        
        # Return the CSV data for download
        return dcc.send_data_frame(df.to_csv, filename, index=False)
    
    except Exception as e:
        app_logger.error(f"Error exporting minute data to CSV: {str(e)}", exc_info=True)
        return dash.no_update

@app.callback(
    Output("download-tech-indicators-csv", "data"),
    Input("export-tech-indicators-button", "n_clicks"),
    State("tech-indicators-store", "data"),
    State("tech-indicators-timeframe-dropdown", "value"),
    State("selected-symbol-store", "data"),
    prevent_initial_call=True
)
def export_tech_indicators_to_csv(n_clicks, tech_data_store, selected_timeframe, selected_symbol):
    if n_clicks == 0 or not tech_data_store or not selected_timeframe:
        return dash.no_update
    
    try:
        app_logger.info(f"Exporting technical indicators data for {selected_timeframe} timeframe to CSV for {selected_symbol}...")
        
        # Get data for the selected timeframe
        timeframe_data = tech_data_store.get(selected_timeframe, [])
        
        if not timeframe_data:
            app_logger.warning(f"No data available for {selected_timeframe} timeframe for {selected_symbol}.")
            return dash.no_update
        
        df = pd.DataFrame(timeframe_data)
        
        # Generate filename with symbol, timeframe, and current timestamp
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{selected_symbol}_{selected_timeframe}_technical_indicators_{timestamp_str}.csv"
        
        # Return the CSV data for download
        return dcc.send_data_frame(df.to_csv, filename, index=False)
    
    except Exception as e:
        app_logger.error(f"Error exporting technical indicators data to CSV: {str(e)}", exc_info=True)
        return dash.no_update

# --- Main Entry Point ---
if __name__ == "__main__":
    app_logger.info("Starting Dash app server...")
    app.run(debug=True, host="0.0.0.0", port=8050)

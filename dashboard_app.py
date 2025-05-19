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

# Initialize the Dash app BEFORE defining layout or callbacks
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Trading Dashboard"
app_logger.info("Dash app initialized")

# --- Schwab Client and Account ID Setup ---
def schwab_client_provider():
    """Provides the Schwab client instance."""
    client, _ = get_schwab_client()
    return client

def account_id_provider():
    """Provides the account ID (account hash for streaming), if available."""
    return os.getenv("SCHWAB_ACCOUNT_HASH")

# --- Global Instances --- 
client_instance, client_init_error = get_schwab_client()
SCHWAB_CLIENT = client_instance  # Store only the client instance, not the tuple
STREAMING_MANAGER = StreamingManager(schwab_client_provider, account_id_provider)
app_logger.info("Global instances (Schwab client, StreamingManager) created.")

initial_errors = []
if client_init_error:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    initial_errors.append(f"{timestamp}: REST Client Init: {client_init_error}")
    app_logger.error(f"Initial REST Client Error: {client_init_error}")

if not account_id_provider():
    app_logger.info("SCHWAB_ACCOUNT_HASH is not set in .env. This is only required for account-specific data streams.")

# --- App Layout --- 
app.layout = html.Div([
    html.H1("Trading Dashboard"),
    
    html.Div([
        dcc.Input(id="symbol-input", type="text", placeholder="Enter comma-separated symbols (e.g., AAPL,MSFT)", style={"width": "50%"}),
        html.Button("Process Symbols", id="process-symbols-button", n_clicks=0),
        dcc.Dropdown(id="symbol-filter-dropdown", placeholder="Filter by Symbol", style={"width": "30%", "display": "none"})
    ], style={"marginBottom": "20px"}),
    
    dcc.Tabs(id="tabs-main", value="tab-minute-data", children=[
        dcc.Tab(label="Minute Streaming Data", value="tab-minute-data", children=[
            html.Div(id="minute-data-content", children=[
                html.Div([
                    html.H4(id="minute-data-header", style={"display": "inline-block", "marginRight": "20px"}),
                    html.Button("Export to CSV", id="export-minute-data-button", n_clicks=0, 
                               style={"backgroundColor": "#4CAF50", "color": "white", "border": "none", 
                                      "padding": "10px 15px", "borderRadius": "4px", "cursor": "pointer"})
                ]),
                dash_table.DataTable(
                    id="minute-data-table", 
                    columns=[], 
                    data=[],
                    page_size=15, 
                    style_table={"overflowX": "auto"}
                ),
                dcc.Download(id="download-minute-data-csv")
            ])
        ]),
        dcc.Tab(label="Technical Indicators", value="tab-tech-indicators", children=[
            html.Div(id="tech-indicators-content", children=[
                html.Div([
                    html.H4(id="tech-indicators-header", style={"display": "inline-block", "marginRight": "20px"}),
                    html.Button("Export to CSV", id="export-tech-indicators-button", n_clicks=0, 
                               style={"backgroundColor": "#4CAF50", "color": "white", "border": "none", 
                                      "padding": "10px 15px", "borderRadius": "4px", "cursor": "pointer"})
                ]),
                html.Div([
                    html.Label("Select Timeframe:"),
                    dcc.Dropdown(
                        id="tech-indicators-timeframe-dropdown",
                        options=[
                            {"label": "1 Minute", "value": "1min"},
                            {"label": "15 Minutes", "value": "15min"},
                            {"label": "Hourly", "value": "Hourly"},
                            {"label": "Daily", "value": "Daily"}
                        ],
                        value="1min",
                        style={"width": "200px", "marginBottom": "10px"}
                    )
                ]),
                dash_table.DataTable(
                    id="tech-indicators-table", 
                    columns=[], 
                    data=[],
                    page_size=15,
                    style_table={"overflowX": "auto"}
                ),
                dcc.Download(id="download-tech-indicators-csv")
            ])
        ]),
        dcc.Tab(label="Options Chain (Stream)", value="tab-options-chain", children=[
            html.Div(id="options-chain-content", children=[
                html.H4(id="options-chain-header"),
                html.Div(id="options-chain-stream-status", style={"marginBottom": "10px", "padding": "5px", "border": "1px solid lightgrey"}),
                html.Div([
                    html.Div([html.H5("Calls"), dash_table.DataTable(id="options-calls-table", columns=[], data=[], page_size=10, style_table={"overflowX": "auto"}, sort_action="native") ], style={"width": "49%", "display": "inline-block", "verticalAlign": "top", "marginRight": "1%"}),
                    html.Div([html.H5("Puts"), dash_table.DataTable(id="options-puts-table", columns=[], data=[], page_size=10, style_table={"overflowX": "auto"}, sort_action="native") ], style={"width": "49%", "display": "inline-block", "float": "right", "verticalAlign": "top"})
                ])
            ]),
            dcc.Interval(id="options-chain-interval", interval=2*1000, n_intervals=0) 
        ]),
    ]),
    
    dcc.Store(id="processed-symbols-store"),
    dcc.Store(id="selected-symbol-store"),
    dcc.Store(id="error-message-store", data=initial_errors), # Main store for all errors, populated by a single callback
    dcc.Store(id="new-error-event-store"), # Intermediate store for individual error events
    dcc.Store(id="current-option-keys-store", data=[]),
    dcc.Store(id="minute-data-store", data=None),  # Store for minute data to be exported
    dcc.Store(id="tech-indicators-store", data={}),  # Store for technical indicators data to be exported (modified to store all timeframes)

    html.Div(id="error-log-display", children="No errors yet." if not initial_errors else [html.P(err) for err in initial_errors], style={"marginTop": "20px", "border": "1px solid #ccc", "padding": "10px", "height": "100px", "overflowY": "scroll", "whiteSpace": "pre-wrap"})
])
app_logger.info("App layout defined.")

# --- Callbacks --- 

@app.callback(
    Output("processed-symbols-store", "data"),
    Output("symbol-filter-dropdown", "options"),
    Output("symbol-filter-dropdown", "style"),
    Output("symbol-filter-dropdown", "value"),
    Input("process-symbols-button", "n_clicks"),
    State("symbol-input", "value")
)
def process_symbols(n_clicks, input_value):
    app_logger.debug(f"CB_process_symbols: n_clicks={n_clicks}, input_value=\"{input_value}\"")
    if n_clicks > 0 and input_value:
        symbols = sorted(list(set([s.strip().upper() for s in input_value.split(",") if s.strip()])))
        if not symbols:
            return dash.no_update, [], {"width": "30%", "display": "none"}, None
        
        options = [{"label": sym, "value": sym} for sym in symbols]
        default_selected_symbol = symbols[0] if len(symbols) == 1 else None
        app_logger.info(f"CB_process_symbols: Processed symbols: {symbols}")
        return symbols, options, {"width": "30%", "display": "inline-block", "marginLeft": "10px"}, default_selected_symbol
    
    # Use ctx instead of dash.callback_context for brevity if imported as `from dash import ctx`
    # callback_context = dash.callback_context 
    if not ctx.triggered or ctx.triggered[0]["prop_id"] == ".": # Initial call or no trigger
        app_logger.debug("CB_process_symbols: Initial call or no trigger, no update.")
        return dash.no_update, [], {"width": "30%", "display": "none"}, None
    app_logger.debug("CB_process_symbols: No valid conditions met, returning no update for symbols.")
    return [], [], {"width": "30%", "display": "none"}, None # Reset if button not clicked but triggered

@app.callback(
    Output("selected-symbol-store", "data"),
    Input("symbol-filter-dropdown", "value")
)
def update_selected_symbol(selected_symbol):
    app_logger.debug(f"CB_update_selected_symbol: Selected symbol from dropdown: {selected_symbol}")
    if selected_symbol:
        return selected_symbol
    return dash.no_update

@app.callback(
    Output("minute-data-header", "children"),
    Output("tech-indicators-header", "children"),
    Output("options-chain-header", "children"),
    Input("selected-symbol-store", "data")
)
def update_tab_headers(selected_symbol):
    app_logger.debug(f"CB_update_tab_headers: Selected symbol: {selected_symbol}")
    if selected_symbol:
        minute_header = f"Minute Data for {selected_symbol} (up to 90 days)"
        tech_header = f"Technical Indicators for {selected_symbol}"
        options_header = f"Options Chain for {selected_symbol} (Streaming)"
        return minute_header, tech_header, options_header
    return "Select a symbol to view data", "Select a symbol to view data", "Select a symbol to view data (Streaming)"

# New callback to consolidate errors from various sources into the main error-message-store
@app.callback(
    Output("error-message-store", "data"),
    Input("new-error-event-store", "data"),
    State("error-message-store", "data"),
    prevent_initial_call=True
)
def consolidate_errors(new_error_event, current_error_list):
    app_logger.debug(f"CB_consolidate_errors: New event: {new_error_event}, Current errors count: {len(current_error_list if current_error_list else [])}")
    if not new_error_event or not isinstance(new_error_event, dict):
        app_logger.debug("CB_consolidate_errors: No new valid error event.")
        return dash.no_update

    updated_error_list = list(current_error_list) if current_error_list else []
    
    source = new_error_event.get("source", "UnknownSource")
    message = new_error_event.get("message", "An unspecified error occurred.")
    timestamp = new_error_event.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    formatted_error_message = f"{timestamp}: {source}: {message}"
    app_logger.info(f"CB_consolidate_errors: Adding error: {formatted_error_message}")
    
    updated_error_list.insert(0, formatted_error_message)
    return updated_error_list[:20] # Keep last 20 errors

@app.callback(
    Output("error-log-display", "children"),
    Input("error-message-store", "data")
)
def update_error_log(error_messages):
    app_logger.debug(f"CB_update_error_log: Updating display with {len(error_messages if error_messages else [])} errors.")
    if error_messages:
        log_content = [html.P(f"{msg}") for msg in reversed(error_messages)] # Show newest first in display
        return log_content
    return "No new errors."


# Modified callback for Minute Data and Technical Indicators
@app.callback(
    Output("minute-data-table", "columns"),
    Output("minute-data-table", "data"),
    Output("tech-indicators-store", "data"),  # Store technical indicators data for all timeframes
    Output("new-error-event-store", "data"), # No allow_duplicate=True
    Input("selected-symbol-store", "data"),
    Input("tabs-main", "value"), # To know which tab is active
    prevent_initial_call=True
)
def update_data_for_active_tab(selected_symbol, active_tab):
    app_logger.debug(f"CB_update_data_for_active_tab: Symbol: {selected_symbol}, Active Tab: {active_tab}")

    minute_cols, minute_data = dash.no_update, dash.no_update
    tech_data_store = dash.no_update
    error_event_to_send = dash.no_update

    default_minute_cols = [{"name": i, "id": i} for i in ["Timestamp", "Open", "High", "Low", "Close", "Volume"]]

    if not selected_symbol:
        app_logger.debug("CB_update_data_for_active_tab: No selected symbol. Clearing tables.")
        minute_cols, minute_data = default_minute_cols, []
        tech_data_store = {}
        return minute_cols, minute_data, tech_data_store, error_event_to_send

    global SCHWAB_CLIENT
    client_to_use = SCHWAB_CLIENT
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not client_to_use:
        app_logger.info(f"UpdateDataTabs: Schwab client not initialized for {selected_symbol}. Attempting reinit.")
        client_instance, client_err = get_schwab_client()
        if client_err:
            error_msg = f"Client re-init failed: {client_err}"
            app_logger.error(f"UpdateDataTabs: {error_msg}")
            error_event_to_send = {"source": "UpdateDataTabs-Client", "message": error_msg, "timestamp": timestamp_str}
            minute_cols, minute_data = default_minute_cols, []
            tech_data_store = {}
            return minute_cols, minute_data, tech_data_store, error_event_to_send
        SCHWAB_CLIENT = client_instance  # Store only the client instance, not the tuple
        client_to_use = client_instance
        app_logger.info(f"UpdateDataTabs: Schwab client reinitialized successfully for {selected_symbol}.")

    if active_tab == "tab-minute-data":
        app_logger.info(f"UpdateDataTabs: Fetching minute data for {selected_symbol}...")
        df, error = get_minute_data(client_to_use, selected_symbol, days_history=90)

        if error:
            error_msg = f"Data fetch error: {error}"
            app_logger.error(f"UpdateDataTabs (MinuteData) for {selected_symbol}: {error_msg}")
            error_event_to_send = {"source": f"MinData-Fetch-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
            minute_cols, minute_data = default_minute_cols, []
        elif df.empty:
            app_logger.warning(f"UpdateDataTabs (MinuteData): No minute data returned for {selected_symbol}.")
            minute_cols, minute_data = default_minute_cols, []
        else:
            app_logger.info(f"UpdateDataTabs (MinuteData): Successfully fetched {len(df)} rows for {selected_symbol}.")
            if "timestamp" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df = df.set_index("timestamp")
                except Exception as e:
                    error_msg = f"Failed to convert 'timestamp' to DatetimeIndex: {e}"
                    app_logger.error(f"UpdateDataTabs (MinuteData-Format) for {selected_symbol}: {error_msg}")
                    error_event_to_send = {"source": f"MinData-Format-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                    minute_cols, minute_data = default_minute_cols, []

            elif not isinstance(df.index, pd.DatetimeIndex):
                error_msg = "Index is not DatetimeIndex after fetch."
                app_logger.error(f"UpdateDataTabs (MinuteData-Format) for {selected_symbol}: {error_msg}")
                error_event_to_send = {"source": f"MinData-Format-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                minute_cols, minute_data = default_minute_cols, []
            
            # Ensure column names are standardized for display
            df_for_display = df.copy()
            df_for_display.index.name = "Timestamp"  # Capitalize for display
            df_for_display = df_for_display.reset_index()
            
            # Format timestamp for display
            df_for_display["Timestamp"] = df_for_display["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Capitalize column names for display
            df_for_display.columns = [col.capitalize() if col != "Timestamp" else col for col in df_for_display.columns]
            
            # Prepare data for table
            minute_data = df_for_display.to_dict("records")
            minute_cols = [{"name": col, "id": col} for col in df_for_display.columns]
            
            app_logger.info(f"UpdateDataTabs (MinuteData): Prepared {len(minute_data)} rows for display.")

    elif active_tab == "tab-tech-indicators":
        app_logger.info(f"UpdateDataTabs: Fetching technical indicators for {selected_symbol}...")
        df, error = get_minute_data(client_to_use, selected_symbol, days_history=90)
        
        if error:
            error_msg = f"Data fetch error for technical indicators: {error}"
            app_logger.error(f"UpdateDataTabs (TechIndicators) for {selected_symbol}: {error_msg}")
            error_event_to_send = {"source": f"TechInd-Fetch-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
            tech_data_store = {}
        elif df.empty:
            app_logger.warning(f"UpdateDataTabs (TechIndicators): No minute data returned for {selected_symbol}.")
            tech_data_store = {}
        else:
            app_logger.info(f"UpdateDataTabs (TechIndicators): Successfully fetched {len(df)} rows for {selected_symbol}.")
            
            # Ensure we have a proper DatetimeIndex
            if "timestamp" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df = df.set_index("timestamp")
                except Exception as e:
                    error_msg = f"Failed to convert 'timestamp' to DatetimeIndex for tech indicators: {e}"
                    app_logger.error(f"UpdateDataTabs (TechInd-Format) for {selected_symbol}: {error_msg}")
                    error_event_to_send = {"source": f"TechInd-Format-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                    tech_data_store = {}
                    return minute_cols, minute_data, tech_data_store, error_event_to_send
            
            # Ensure column names are lowercase for technical analysis functions
            df.columns = [col.lower() for col in df.columns]
            
            # Calculate technical indicators for different timeframes
            tech_data_by_timeframe = {}
            
            try:
                # 1-minute (original data)
                app_logger.info(f"UpdateDataTabs (TechIndicators): Calculating 1-minute indicators for {selected_symbol}...")
                indicators_1min = calculate_all_technical_indicators(df, symbol=selected_symbol)
                if isinstance(indicators_1min, pd.DataFrame) and not indicators_1min.empty:
                    # Format for display and storage
                    indicators_1min_display = indicators_1min.copy()
                    indicators_1min_display.index.name = "Timestamp"
                    indicators_1min_display = indicators_1min_display.reset_index()
                    indicators_1min_display["Timestamp"] = indicators_1min_display["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                    tech_data_by_timeframe["1min"] = indicators_1min_display.to_dict("records")
                    app_logger.info(f"UpdateDataTabs (TechIndicators): Prepared {len(tech_data_by_timeframe['1min'])} 1-minute indicator rows.")
                else:
                    app_logger.warning(f"UpdateDataTabs (TechIndicators): No valid 1-minute indicators calculated for {selected_symbol}.")
                    tech_data_by_timeframe["1min"] = []
                
                # 15-minute aggregation
                app_logger.info(f"UpdateDataTabs (TechIndicators): Calculating 15-minute indicators for {selected_symbol}...")
                df_15min = aggregate_candles(df, "15min")
                indicators_15min = calculate_all_technical_indicators(df_15min, symbol=f"{selected_symbol}_15min")
                if isinstance(indicators_15min, pd.DataFrame) and not indicators_15min.empty:
                    indicators_15min_display = indicators_15min.copy()
                    indicators_15min_display.index.name = "Timestamp"
                    indicators_15min_display = indicators_15min_display.reset_index()
                    indicators_15min_display["Timestamp"] = indicators_15min_display["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                    tech_data_by_timeframe["15min"] = indicators_15min_display.to_dict("records")
                    app_logger.info(f"UpdateDataTabs (TechIndicators): Prepared {len(tech_data_by_timeframe['15min'])} 15-minute indicator rows.")
                else:
                    app_logger.warning(f"UpdateDataTabs (TechIndicators): No valid 15-minute indicators calculated for {selected_symbol}.")
                    tech_data_by_timeframe["15min"] = []
                
                # Hourly aggregation
                app_logger.info(f"UpdateDataTabs (TechIndicators): Calculating hourly indicators for {selected_symbol}...")
                df_hourly = aggregate_candles(df, "1H")
                indicators_hourly = calculate_all_technical_indicators(df_hourly, symbol=f"{selected_symbol}_hourly")
                if isinstance(indicators_hourly, pd.DataFrame) and not indicators_hourly.empty:
                    indicators_hourly_display = indicators_hourly.copy()
                    indicators_hourly_display.index.name = "Timestamp"
                    indicators_hourly_display = indicators_hourly_display.reset_index()
                    indicators_hourly_display["Timestamp"] = indicators_hourly_display["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                    tech_data_by_timeframe["Hourly"] = indicators_hourly_display.to_dict("records")
                    app_logger.info(f"UpdateDataTabs (TechIndicators): Prepared {len(tech_data_by_timeframe['Hourly'])} hourly indicator rows.")
                else:
                    app_logger.warning(f"UpdateDataTabs (TechIndicators): No valid hourly indicators calculated for {selected_symbol}.")
                    tech_data_by_timeframe["Hourly"] = []
                
                # Daily aggregation
                app_logger.info(f"UpdateDataTabs (TechIndicators): Calculating daily indicators for {selected_symbol}...")
                df_daily = aggregate_candles(df, "1D")
                indicators_daily = calculate_all_technical_indicators(df_daily, symbol=f"{selected_symbol}_daily")
                if isinstance(indicators_daily, pd.DataFrame) and not indicators_daily.empty:
                    indicators_daily_display = indicators_daily.copy()
                    indicators_daily_display.index.name = "Timestamp"
                    indicators_daily_display = indicators_daily_display.reset_index()
                    indicators_daily_display["Timestamp"] = indicators_daily_display["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                    tech_data_by_timeframe["Daily"] = indicators_daily_display.to_dict("records")
                    app_logger.info(f"UpdateDataTabs (TechIndicators): Prepared {len(tech_data_by_timeframe['Daily'])} daily indicator rows.")
                else:
                    app_logger.warning(f"UpdateDataTabs (TechIndicators): No valid daily indicators calculated for {selected_symbol}.")
                    tech_data_by_timeframe["Daily"] = []
                
                tech_data_store = tech_data_by_timeframe
                app_logger.info(f"UpdateDataTabs (TechIndicators): Technical indicators calculated for all timeframes.")
                
            except Exception as e:
                error_msg = f"Error calculating technical indicators: {str(e)}"
                app_logger.error(f"UpdateDataTabs (TechIndicators) for {selected_symbol}: {error_msg}", exc_info=True)
                error_event_to_send = {"source": f"TechInd-Calc-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                tech_data_store = {}
    
    return minute_cols, minute_data, tech_data_store, error_event_to_send

@app.callback(
    Output("tech-indicators-table", "columns"),
    Output("tech-indicators-table", "data"),
    Input("tech-indicators-store", "data"),
    Input("tech-indicators-timeframe-dropdown", "value")
)
def update_tech_indicators_table(tech_data_store, selected_timeframe):
    app_logger.debug(f"CB_update_tech_indicators_table: Selected timeframe: {selected_timeframe}")
    
    if not tech_data_store or not selected_timeframe or selected_timeframe not in tech_data_store:
        app_logger.debug("CB_update_tech_indicators_table: No data available for selected timeframe.")
        return [], []
    
    timeframe_data = tech_data_store[selected_timeframe]
    if not timeframe_data:
        app_logger.debug(f"CB_update_tech_indicators_table: Empty data for timeframe {selected_timeframe}.")
        return [], []
    
    # Get column names from the first record
    columns = [{"name": col, "id": col} for col in timeframe_data[0].keys()]
    
    app_logger.info(f"CB_update_tech_indicators_table: Displaying {len(timeframe_data)} rows for {selected_timeframe} timeframe.")
    return columns, timeframe_data

@app.callback(
    Output("options-chain-stream-status", "children"),
    Output("options-calls-table", "columns"),
    Output("options-calls-table", "data"),
    Output("options-puts-table", "columns"),
    Output("options-puts-table", "data"),
    Output("current-option-keys-store", "data"),
    Output("new-error-event-store", "data", allow_duplicate=True),
    Input("selected-symbol-store", "data"),
    Input("options-chain-interval", "n_intervals"),
    State("current-option-keys-store", "data"),
    prevent_initial_call=True
)
def manage_options_stream(selected_symbol, n_intervals, current_keys):
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not selected_symbol:
        status_msg = "Select a symbol to view options chain."
        return status_msg, [], [], [], [], [], dash.no_update
    
    try:
        global SCHWAB_CLIENT, STREAMING_MANAGER
        client_to_use = SCHWAB_CLIENT
        
        if not client_to_use:
            app_logger.info(f"OptionsStream: Schwab client not initialized for {selected_symbol}. Attempting reinit.")
            client_instance, client_err = get_schwab_client()
            if client_err:
                error_msg = f"Client re-init failed: {client_err}"
                app_logger.error(f"OptionsStream: {error_msg}")
                return f"Error: {error_msg}", [], [], [], [], [], {"source": "OptionsStream-Client", "message": error_msg, "timestamp": timestamp_str}
            SCHWAB_CLIENT = client_instance  # Store only the client instance, not the tuple
            client_to_use = client_instance
            app_logger.info(f"OptionsStream: Schwab client reinitialized successfully for {selected_symbol}.")
        
        # Get options chain data
        calls_df, puts_df, error = get_options_chain_data(client_to_use, selected_symbol)
        
        if error:
            error_msg = f"Options chain fetch error: {error}"
            app_logger.error(f"OptionsStream for {selected_symbol}: {error_msg}")
            return f"Error: {error_msg}", [], [], [], [], [], {"source": f"OptionsStream-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
        
        # Get option contract keys for streaming
        contract_keys, keys_error = get_option_contract_keys(client_to_use, selected_symbol)
        if keys_error:
            app_logger.warning(f"OptionsStream for {selected_symbol}: Contract keys error: {keys_error}")
            # Continue with REST data, just log the warning
        
        # Start streaming if we have new contract keys
        if contract_keys and (not current_keys or set(contract_keys) != set(current_keys)):
            app_logger.info(f"OptionsStream: Starting streaming for {len(contract_keys)} contract keys.")
            
            # Stop any existing stream first
            STREAMING_MANAGER.stop_streaming()
            
            # Start new stream with the new keys
            success, stream_error = STREAMING_MANAGER.start_streaming(contract_keys)
            if not success:
                app_logger.error(f"OptionsStream: Failed to start streaming: {stream_error}")
                # Continue with REST data, just log the error
        
        # Get streaming status
        stream_status = STREAMING_MANAGER.get_status()
        
        # Get streaming data
        streaming_data = STREAMING_MANAGER.get_streaming_data()
        
        # Update the options chain data with streaming data if available
        if streaming_data:
            app_logger.info(f"OptionsStream: Updating options chain with streaming data for {len(streaming_data)} contracts.")
            
            # Update calls DataFrame
            if not calls_df.empty:
                for idx, row in calls_df.iterrows():
                    contract_key = row.get("Contract Key")
                    if contract_key in streaming_data:
                        stream_data = streaming_data[contract_key]
                        
                        # Update Last, Bid, Ask with streaming data
                        if "lastPrice" in stream_data:
                            calls_df.at[idx, "Last"] = stream_data["lastPrice"]
                        if "bidPrice" in stream_data:
                            calls_df.at[idx, "Bid"] = stream_data["bidPrice"]
                        if "askPrice" in stream_data:
                            calls_df.at[idx, "Ask"] = stream_data["askPrice"]
                        
                        # Log the updates for debugging
                        app_logger.debug(f"OptionsStream: Updated call option {contract_key} with streaming data: " +
                                        f"Last={stream_data.get('lastPrice')}, Bid={stream_data.get('bidPrice')}, Ask={stream_data.get('askPrice')}")
            
            # Update puts DataFrame
            if not puts_df.empty:
                for idx, row in puts_df.iterrows():
                    contract_key = row.get("Contract Key")
                    if contract_key in streaming_data:
                        stream_data = streaming_data[contract_key]
                        
                        # Update Last, Bid, Ask with streaming data
                        if "lastPrice" in stream_data:
                            puts_df.at[idx, "Last"] = stream_data["lastPrice"]
                        if "bidPrice" in stream_data:
                            puts_df.at[idx, "Bid"] = stream_data["bidPrice"]
                        if "askPrice" in stream_data:
                            puts_df.at[idx, "Ask"] = stream_data["askPrice"]
                        
                        # Log the updates for debugging
                        app_logger.debug(f"OptionsStream: Updated put option {contract_key} with streaming data: " +
                                        f"Last={stream_data.get('lastPrice')}, Bid={stream_data.get('bidPrice')}, Ask={stream_data.get('askPrice')}")
        
        # Format tables
        calls_columns = [{"name": col, "id": col} for col in calls_df.columns] if not calls_df.empty else []
        puts_columns = [{"name": col, "id": col} for col in puts_df.columns] if not puts_df.empty else []
        
        calls_data = calls_df.to_dict("records") if not calls_df.empty else []
        puts_data = puts_df.to_dict("records") if not puts_df.empty else []
        
        # Log the presence of Last, Bid, Ask fields for debugging
        if not calls_df.empty:
            app_logger.info(f"OptionsStream: Calls DataFrame columns: {calls_df.columns.tolist()}")
            app_logger.info(f"OptionsStream: Sample call option data - Last: {calls_df['Last'].iloc[0] if 'Last' in calls_df.columns else 'N/A'}, " +
                           f"Bid: {calls_df['Bid'].iloc[0] if 'Bid' in calls_df.columns else 'N/A'}, " +
                           f"Ask: {calls_df['Ask'].iloc[0] if 'Ask' in calls_df.columns else 'N/A'}")
        
        # Create status message
        stream_info = f"Stream: {stream_status['status_message']} | Data count: {stream_status['data_count']}"
        status_msg = f"Options chain for {selected_symbol} loaded. Calls: {len(calls_data)}, Puts: {len(puts_data)} | {stream_info}"
        app_logger.info(f"OptionsStream: {status_msg}")
        
        return status_msg, calls_columns, calls_data, puts_columns, puts_data, list(contract_keys) if contract_keys else [], dash.no_update
        
    except Exception as e:
        error_msg = f"Error in options chain processing: {str(e)}"
        app_logger.exception(f"OptionsStream for {selected_symbol}: {error_msg}")
        return f"Error: {error_msg}", [], [], [], [], [], {"source": f"OptionsStream-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}


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

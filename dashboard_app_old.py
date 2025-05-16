# Dash App Structure

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State, ALL
import pandas as pd
import numpy as np # For NaN handling
import datetime
import os # For account ID
import logging # For app-level logging
import json # For pretty printing dicts in logs
import re # For parsing option key

# Import utility functions
from dashboard_utils.data_fetchers import get_schwab_client, get_minute_data, get_options_chain_data, get_option_contract_keys
from dashboard_utils.streaming_manager import StreamingManager
# Import technical analysis functions
from technical_analysis import aggregate_candles, calculate_all_technical_indicators

# Configure basic logging for the app
app_logger = logging.getLogger(__name__)
if not app_logger.hasHandlers():
    app_handler = logging.StreamHandler()
    app_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    app_handler.setFormatter(app_formatter)
    app_logger.addHandler(app_handler)
app_logger.setLevel(logging.INFO)
app_logger.info("App logger initialized")

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
SCHWAB_CLIENT, client_init_error = get_schwab_client()
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
                html.H4(id="minute-data-header"),
                dash_table.DataTable(
                    id="minute-data-table", 
                    columns=[], 
                    data=[],
                    page_size=15, 
                    style_table={"overflowX": "auto"}
                )
            ])
        ]),
        dcc.Tab(label="Technical Indicators", value="tab-tech-indicators", children=[
            html.Div(id="tech-indicators-content", children=[
                html.H4(id="tech-indicators-header"),
                dash_table.DataTable(
                    id="tech-indicators-table", 
                    columns=[], 
                    data=[],
                    page_size=10,
                    style_table={"overflowX": "auto"}
                )
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
    
    ctx = dash.callback_context
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

@app.callback(
    Output("minute-data-table", "columns"),
    Output("minute-data-table", "data"),
    Output("new-error-event-store", "data", allow_duplicate=True), # Changed output for errors
    Input("selected-symbol-store", "data"),
    prevent_initial_call=True
)
def update_minute_data_tab(selected_symbol):
    app_logger.debug(f"CB_update_minute_data_tab: Symbol: {selected_symbol}")
    error_event_to_send = dash.no_update
    if not selected_symbol:
        return [], [], error_event_to_send

    global SCHWAB_CLIENT
    client_to_use = SCHWAB_CLIENT
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not client_to_use:
        app_logger.info(f"MinuteData: Schwab client not initialized for {selected_symbol}. Attempting reinit.")
        client_to_use, client_err = get_schwab_client()
        if client_err:
            error_msg = f"Client re-init failed: {client_err}"
            app_logger.error(f"MinuteData: {error_msg}")
            error_event_to_send = {"source": "MinData-Client", "message": error_msg, "timestamp": timestamp_str}
            return [], [], error_event_to_send
        SCHWAB_CLIENT = client_to_use
        app_logger.info(f"MinuteData: Schwab client reinitialized successfully for {selected_symbol}.")

    app_logger.info(f"MinuteData: Fetching minute data for {selected_symbol}...")
    df, error = get_minute_data(client_to_use, selected_symbol, days_history=90)

    if error:
        error_msg = f"Data fetch error: {error}"
        app_logger.error(f"MinuteData for {selected_symbol}: {error_msg}")
        error_event_to_send = {"source": f"MinData-Fetch-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
        return [], [], error_event_to_send
    
    if df.empty:
        app_logger.warning(f"MinuteData: No minute data returned for {selected_symbol}.")
        cols = [{"name": i, "id": i} for i in ["Timestamp", "Open", "High", "Low", "Close", "Volume"]]
        # No error event here, just empty table
        return cols, [], error_event_to_send 

    app_logger.info(f"MinuteData: Successfully fetched {len(df)} rows for {selected_symbol}.")
    if "timestamp" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
    elif not isinstance(df.index, pd.DatetimeIndex):
        error_msg = "Index is not DatetimeIndex after fetch."
        app_logger.error(f"MinuteData for {selected_symbol}: {error_msg}")
        error_event_to_send = {"source": f"MinData-Format-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
        return [], [], error_event_to_send

    df_display = df.reset_index()
    df_display["timestamp"] = df_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    cols = [{"name": i, "id": i} for i in df_display.columns]
    data = df_display.to_dict("records")
    return cols, data, error_event_to_send

@app.callback(
    Output("tech-indicators-table", "columns"),
    Output("tech-indicators-table", "data"),
    Output("new-error-event-store", "data", allow_duplicate=True), # Changed output for errors
    Input("selected-symbol-store", "data"),
    prevent_initial_call=True
)
def update_tech_indicators_tab(selected_symbol):
    app_logger.debug(f"CB_update_tech_indicators_tab: Symbol: {selected_symbol}. This is the callback mentioned in the error.")
    error_event_to_send = dash.no_update
    output_cols_def = ["Indicator", "1min", "15min", "Hourly", "Daily"]
    output_cols = [{"name": i, "id": i} for i in output_cols_def]

    if not selected_symbol:
        return output_cols, [], error_event_to_send

    global SCHWAB_CLIENT
    client_to_use = SCHWAB_CLIENT
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not client_to_use:
        app_logger.info(f"TechIndicators: Schwab client not initialized for {selected_symbol}. Attempting reinit.")
        client_to_use, client_err = get_schwab_client()
        if client_err:
            error_msg = f"Client re-init failed: {client_err}"
            app_logger.error(f"TechInd: {error_msg}")
            error_event_to_send = {"source": "TechInd-Client", "message": error_msg, "timestamp": timestamp_str}
            return output_cols, [], error_event_to_send
        SCHWAB_CLIENT = client_to_use
        app_logger.info(f"TechIndicators: Schwab client reinitialized successfully for {selected_symbol}.")

    app_logger.info(f"TechIndicators: Fetching minute data for TA for {selected_symbol}...")
    df_minute_raw, error = get_minute_data(client_to_use, selected_symbol, days_history=90)

    if error:
        error_msg = f"Data fetch error: {error}"
        app_logger.error(f"TechInd data fetch for {selected_symbol}: {error_msg}")
        error_event_to_send = {"source": f"TechInd-Fetch-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
        return output_cols, [], error_event_to_send
    
    if df_minute_raw.empty:
        app_logger.warning(f"TechInd: No minute data for {selected_symbol} to calculate TA.")
        return output_cols, [], error_event_to_send
    
    app_logger.info(f"TechInd: Fetched {len(df_minute_raw)} minute candles for {selected_symbol} for TA.")

    if not isinstance(df_minute_raw.index, pd.DatetimeIndex):
        if 'timestamp' in df_minute_raw.columns:
            try:
                df_minute_raw['timestamp'] = pd.to_datetime(df_minute_raw['timestamp'])
                df_minute_raw = df_minute_raw.set_index('timestamp')
                app_logger.info(f"TechInd: Converted 'timestamp' column to DatetimeIndex for {selected_symbol}.")
            except Exception as e:
                error_msg = f"Failed to convert 'timestamp' to DatetimeIndex: {e}"
                app_logger.error(f"TechInd for {selected_symbol}: {error_msg}")
                error_event_to_send = {"source": f"TechInd-Format-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                return output_cols, [], error_event_to_send
        else:
            error_msg = "Minute data missing 'timestamp' column or DatetimeIndex."
            app_logger.error(f"TechInd for {selected_symbol}: {error_msg}")
            error_event_to_send = {"source": f"TechInd-Format-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
            return output_cols, [], error_event_to_send

    app_logger.info(f"TechInd: Aggregating data for {selected_symbol}...")
    df_15min_raw = aggregate_candles(df_minute_raw.copy(), rule="15min")
    df_hourly_raw = aggregate_candles(df_minute_raw.copy(), rule="H")
    df_daily_raw = aggregate_candles(df_minute_raw.copy(), rule="D")
    app_logger.info(f"TechInd: Aggregation complete for {selected_symbol}. Sizes: 1m:{len(df_minute_raw)}, 15m:{len(df_15min_raw)}, H:{len(df_hourly_raw)}, D:{len(df_daily_raw)}.")

    app_logger.info(f"TechInd: Calculating TA for {selected_symbol} across timeframes...")
    df_1min_ta = calculate_all_technical_indicators(df_minute_raw.copy(), symbol=f"{selected_symbol}_1min")
    df_15min_ta = calculate_all_technical_indicators(df_15min_raw.copy(), symbol=f"{selected_symbol}_15min")
    df_hourly_ta = calculate_all_technical_indicators(df_hourly_raw.copy(), symbol=f"{selected_symbol}_hourly")
    df_daily_ta = calculate_all_technical_indicators(df_daily_raw.copy(), symbol=f"{selected_symbol}_daily")
    app_logger.info(f"TechInd: TA calculation complete for {selected_symbol}.")

    indicators_to_display = {
        "BB Mid (20)": "bb_middle_20", "BB Upper (20)": "bb_upper_20", "BB Lower (20)": "bb_lower_20",
        "RSI (14)": "rsi_14", "MACD": "macd", "MACD Signal": "macd_signal", "MACD Hist": "macd_hist",
        "IMI (14)": "imi_14", "MFI (14)": "mfi_14",
    }
    table_data = []
    timeframe_dfs = {"1min": df_1min_ta, "15min": df_15min_ta, "Hourly": df_hourly_ta, "Daily": df_daily_ta}

    for display_name, col_name in indicators_to_display.items():
        row_data = {"Indicator": display_name}
        for tf_label, df_ta in timeframe_dfs.items():
            val = "N/A"
            if not df_ta.empty and col_name in df_ta.columns and not df_ta[col_name].empty:
                last_val = df_ta[col_name].iloc[-1]
                if pd.notna(last_val):
                    val = f"{last_val:.2f}" if isinstance(last_val, (float, np.floating)) else str(last_val)
            row_data[tf_label] = val
        table_data.append(row_data)
    
    app_logger.info(f"TechInd: Formatted TA data for {selected_symbol} table: {len(table_data)} indicators.")
    return output_cols, table_data, error_event_to_send


@app.callback(
    Output("current-option-keys-store", "data"),
    Output("new-error-event-store", "data", allow_duplicate=True), # Changed output for errors
    Input("selected-symbol-store", "data"),
    Input("tabs-main", "value"),
    prevent_initial_call=True
)
def manage_options_stream(selected_symbol, active_tab):
    app_logger.debug(f"CB_manage_options_stream: Symbol: {selected_symbol}, Active Tab: {active_tab}")
    error_event_to_send = dash.no_update
    option_keys_for_stream = []
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if active_tab == "tab-options-chain" and selected_symbol:
        app_logger.info(f"StreamCtrl: Options tab active for {selected_symbol}. Managing stream.")
        global SCHWAB_CLIENT
        client_to_use = SCHWAB_CLIENT
        if not client_to_use:
            client_to_use, client_err = get_schwab_client()
            if client_err:
                error_msg = f"Client re-init failed: {client_err}"
                app_logger.error(f"StreamCtrl: {error_msg}")
                STREAMING_MANAGER.stop_stream()
                error_event_to_send = {"source": "StreamCtrl-Client", "message": error_msg, "timestamp": timestamp_str}
                return [], error_event_to_send
            SCHWAB_CLIENT = client_to_use
        
        keys, err = get_option_contract_keys(client_to_use, selected_symbol)
        if err:
            error_msg = f"Error getting keys: {err}"
            app_logger.error(f"StreamCtrl for {selected_symbol}: {error_msg}")
            STREAMING_MANAGER.stop_stream()
            error_event_to_send = {"source": f"StreamCtrl-Keys-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
            return [], error_event_to_send
        
        if not keys:
            app_logger.info(f"StreamCtrl: No option keys with OI > 0 for {selected_symbol}. Stopping stream.")
            STREAMING_MANAGER.stop_stream()
            return [], error_event_to_send # No error, but keys list is empty

        option_keys_for_stream = list(keys)
        app_logger.info(f"StreamCtrl: Attempting to start/update stream for {len(option_keys_for_stream)} keys for {selected_symbol}.")
        STREAMING_MANAGER.start_stream(option_keys_for_stream)
    else:
        app_logger.info("StreamCtrl: Options tab not active or no symbol. Stopping stream.")
        STREAMING_MANAGER.stop_stream()
    
    app_logger.debug(f"StreamCtrl: Returning keys: {len(option_keys_for_stream)}.")
    return option_keys_for_stream, error_event_to_send

OPTION_KEY_REGEX = re.compile(r"^([A-Z ]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")

@app.callback(
    Output("options-calls-table", "columns"),
    Output("options-calls-table", "data"),
    Output("options-puts-table", "columns"),
    Output("options-puts-table", "data"),
    Output("options-chain-stream-status", "children"),
    Output("new-error-event-store", "data", allow_duplicate=True), # Changed output for errors
    Input("options-chain-interval", "n_intervals"),
    State("selected-symbol-store", "data"),
    prevent_initial_call=True
)
def update_options_chain_stream_data(n_intervals, selected_symbol):
    app_logger.debug(f"CB_update_options_chain_stream_data: Symbol: {selected_symbol}, Interval: {n_intervals}")
    error_event_to_send = dash.no_update
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # For potential errors

    stream_status_msg, stream_error_msg = STREAMING_MANAGER.get_status()
    status_display = f"Stream Status: {stream_status_msg}"
    if stream_error_msg: # This is a stream error, not a callback logic error
        status_display += f" | Last Stream Error: {stream_error_msg}"
        # Optionally, could also send this to new-error-event-store if critical
        # error_event_to_send = {"source": "StreamUpdate-Status", "message": stream_error_msg, "timestamp": timestamp_str}
        app_logger.warning(f"StreamUpdate: Stream reported an error: {stream_error_msg}")

    option_cols_def = ["Expiration Date", "Strike", "Last", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility", "Delta", "Gamma", "Theta", "Vega", "Contract Key"]
    option_cols = [{"name": i, "id": i} for i in option_cols_def]

    if not selected_symbol or not STREAMING_MANAGER.is_running:
        app_logger.info("StreamUpdate: No selected symbol or stream not running. Empty tables.")
        return option_cols, [], option_cols, [], status_display, error_event_to_send

    latest_stream_data = STREAMING_MANAGER.get_latest_data()
    app_logger.info(f"StreamUpdate: Fetched {len(latest_stream_data)} items from STREAMING_MANAGER.")
    if latest_stream_data and n_intervals % 10 == 0: # Log sample less frequently
        sample_key = list(latest_stream_data.keys())[0]
        app_logger.debug(f"StreamUpdate: Sample data (key: {sample_key}): {json.dumps(latest_stream_data[sample_key], indent=2)}")
    
    calls_list = []
    puts_list = []

    for contract_key_from_store, data_dict in latest_stream_data.items():
        if not isinstance(data_dict, dict):
            app_logger.warning(f"StreamUpdate: Skipping non-dict item for key {contract_key_from_store}: {type(data_dict)}")
            continue

        contract_key_str = str(data_dict.get("key", ""))
        parsed_expiration_date, parsed_strike_price, is_call, is_put = "N/A", "N/A", False, False

        exp_year = data_dict.get("expirationYear")
        exp_month = data_dict.get("expirationMonth")
        exp_day = data_dict.get("expirationDay")
        strike = data_dict.get("strikePrice")
        contract_type = data_dict.get("contractType")

        if all(isinstance(v, (int, float)) for v in [exp_year, exp_month, exp_day]):
            try:
                year_prefix = "20" if exp_year < 100 else ""
                parsed_expiration_date = f"{year_prefix}{int(exp_year):02d}-{int(exp_month):02d}-{int(exp_day):02d}"
            except ValueError: app_logger.warning(f"StreamUpdate: Date format error for {contract_key_str}")
        
        if isinstance(strike, (int, float)): parsed_strike_price = strike
        
        if isinstance(contract_type, str):
            ct_upper = contract_type.upper()
            if ct_upper == "CALL" or ct_upper == "C": is_call = True
            elif ct_upper == "PUT" or ct_upper == "P": is_put = True

        if parsed_expiration_date == "N/A" or parsed_strike_price == "N/A" or not (is_call or is_put):
            key_match = OPTION_KEY_REGEX.match(contract_key_str.replace(" ", ""))
            if key_match:
                _, year_s, month_s, day_s, type_c, strike_s = key_match.groups()
                if parsed_expiration_date == "N/A": parsed_expiration_date = f"20{year_s}-{month_s}-{day_s}"
                if parsed_strike_price == "N/A": 
                    try: parsed_strike_price = float(strike_s) / 1000.0
                    except ValueError: app_logger.warning(f"StreamUpdate: Strike parse error from key {contract_key_str}")
                if not (is_call or is_put):
                    if type_c == "C": is_call = True
                    if type_c == "P": is_put = True
            else: app_logger.warning(f"StreamUpdate: Regex parse failed for key {contract_key_str}")

        option_item = {
            "Expiration Date": parsed_expiration_date, "Strike": parsed_strike_price,
            "Last": data_dict.get("lastPrice", "N/A"), "Bid": data_dict.get("bidPrice", "N/A"),
            "Ask": data_dict.get("askPrice", "N/A"), "Volume": data_dict.get("totalVolume", "N/A"),
            "Open Interest": data_dict.get("openInterest", "N/A"),
            "Implied Volatility": f"{data_dict.get('volatility', 0) * 100:.2f}%" if pd.notna(data_dict.get('volatility')) else "N/A",
            "Delta": f"{data_dict.get('delta', 0):.4f}" if pd.notna(data_dict.get('delta')) else "N/A",
            "Gamma": f"{data_dict.get('gamma', 0):.4f}" if pd.notna(data_dict.get('gamma')) else "N/A",
            "Theta": f"{data_dict.get('theta', 0):.4f}" if pd.notna(data_dict.get('theta')) else "N/A",
            "Vega": f"{data_dict.get('vega', 0):.4f}" if pd.notna(data_dict.get('vega')) else "N/A",
            "Contract Key": contract_key_str
        }
        if is_call: calls_list.append(option_item)
        elif is_put: puts_list.append(option_item)

    calls_list.sort(key=lambda x: (x["Expiration Date"], x["Strike"] if isinstance(x["Strike"], (int, float)) else float("inf")))
    puts_list.sort(key=lambda x: (x["Expiration Date"], x["Strike"] if isinstance(x["Strike"], (int, float)) else float("inf")))
    
    app_logger.info(f"StreamUpdate: Processed: {len(calls_list)} calls, {len(puts_list)} puts for {selected_symbol}.")
    return option_cols, calls_list, option_cols, puts_list, status_display, error_event_to_send


if __name__ == "__main__":
    app_logger.info("Starting Dash development server (refactored app)...")
    # Ensure .env is loaded if running directly and it contains SCHWAB_API_KEY etc.
    # from dotenv import load_dotenv
    # load_dotenv()
    app.run(debug=True, host="0.0.0.0", port=8050, use_reloader=False)

app_logger.info("Finished defining app structure and callbacks.")


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

# Initialize the Dash app BEFORE defining layout or callbacks
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Trading Dashboard"

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

initial_errors = []
if client_init_error:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    initial_errors.append(f"{timestamp}: REST Client: {client_init_error}")

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
    dcc.Store(id="error-message-store", data=initial_errors), 
    dcc.Store(id="current-option-keys-store", data=[]),

    html.Div(id="error-log-display", children="No errors yet." if not initial_errors else [html.P(err) for err in initial_errors], style={"marginTop": "20px", "border": "1px solid #ccc", "padding": "10px", "height": "100px", "overflowY": "scroll", "whiteSpace": "pre-wrap"})
])

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
    if n_clicks > 0 and input_value:
        symbols = sorted(list(set([s.strip().upper() for s in input_value.split(",") if s.strip()])))
        if not symbols:
            return dash.no_update, [], {"width": "30%", "display": "none"}, None
        
        options = [{"label": sym, "value": sym} for sym in symbols]
        default_selected_symbol = symbols[0] if len(symbols) == 1 else None
        return symbols, options, {"width": "30%", "display": "inline-block", "marginLeft": "10px"}, default_selected_symbol
    ctx = dash.callback_context
    if not ctx.triggered or ctx.triggered[0]["prop_id"] == ".":
        return dash.no_update, [], {"width": "30%", "display": "none"}, None
    return [], [], {"width": "30%", "display": "none"}, None

@app.callback(
    Output("selected-symbol-store", "data"),
    Input("symbol-filter-dropdown", "value")
)
def update_selected_symbol(selected_symbol):
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
    if selected_symbol:
        minute_header = f"Minute Data for {selected_symbol} (up to 90 days)"
        tech_header = f"Technical Indicators for {selected_symbol}"
        options_header = f"Options Chain for {selected_symbol} (Streaming)"
        return minute_header, tech_header, options_header
    return "Select a symbol to view data", "Select a symbol to view data", "Select a symbol to view data (Streaming)"

@app.callback(
    Output("error-log-display", "children"),
    Input("error-message-store", "data")
)
def update_error_log(error_messages):
    if error_messages:
        log_content = [html.P(f"{msg}") for msg in reversed(error_messages)]
        return log_content
    return "No new errors."

@app.callback(
    Output("minute-data-table", "columns"),
    Output("minute-data-table", "data"),
    Output("error-message-store", "data", allow_duplicate=True),
    Input("selected-symbol-store", "data"),
    State("error-message-store", "data"),
    prevent_initial_call=True
)
def update_minute_data_tab(selected_symbol, current_errors):
    if not selected_symbol:
        return [], [], current_errors 

    global SCHWAB_CLIENT
    new_errors = list(current_errors) 
    client_to_use = SCHWAB_CLIENT
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not client_to_use:
        app_logger.info(f"MinuteData: Schwab client not initialized for {selected_symbol}. Attempting to reinitialize.")
        client_to_use, client_err = get_schwab_client()
        if client_err:
            error_msg = f"{timestamp_str}: MinData: {client_err}"
            app_logger.error(error_msg)
            new_errors.insert(0, error_msg)
            return [], [], new_errors[:10]
        SCHWAB_CLIENT = client_to_use
        app_logger.info(f"MinuteData: Schwab client reinitialized successfully for {selected_symbol}.")

    app_logger.info(f"Fetching minute data for {selected_symbol}...")
    df, error = get_minute_data(client_to_use, selected_symbol, days_history=90) # Fetches minute data

    if error:
        error_msg = f"{timestamp_str}: MinData for {selected_symbol}: {error}"
        app_logger.error(error_msg)
        new_errors.insert(0, error_msg)
        return [], [], new_errors[:10]
    
    if df.empty:
        app_logger.warning(f"No minute data returned for {selected_symbol}.")
        cols = [{"name": i, "id": i} for i in ["Timestamp", "Open", "High", "Low", "Close", "Volume"]]
        return cols, [], new_errors

    app_logger.info(f"Successfully fetched {len(df)} rows of minute data for {selected_symbol}.")
    # Ensure timestamp is the index and is datetime type for resampling
    if "timestamp" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
    elif not isinstance(df.index, pd.DatetimeIndex):
        app_logger.error(f"Minute data for {selected_symbol} does not have a DatetimeIndex.")
        # Fallback or error handling if index is not datetime
        error_msg = f"{timestamp_str}: MinData for {selected_symbol}: Index is not DatetimeIndex."
        new_errors.insert(0, error_msg)
        return [], [], new_errors[:10]

    # Format for DataTable
    df_display = df.reset_index() # Move timestamp from index to column for display
    df_display["timestamp"] = df_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S") # Format datetime
    
    cols = [{"name": i, "id": i} for i in df_display.columns]
    data = df_display.to_dict("records")
    return cols, data, new_errors

@app.callback(
    Output("tech-indicators-table", "columns"),
    Output("tech-indicators-table", "data"),
    Output("error-message-store", "data", allow_duplicate=True),
    Input("selected-symbol-store", "data"),
    State("error-message-store", "data"),
    prevent_initial_call=True
)
def update_tech_indicators_tab(selected_symbol, current_errors):
    if not selected_symbol:
        return [], [], current_errors

    global SCHWAB_CLIENT
    new_errors = list(current_errors)
    client_to_use = SCHWAB_CLIENT
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output_cols = [{"name": i, "id": i} for i in ["Indicator", "1min", "15min", "Hourly", "Daily"]]

    if not client_to_use:
        app_logger.info(f"TechIndicators: Schwab client not initialized for {selected_symbol}. Attempting to reinitialize.")
        client_to_use, client_err = get_schwab_client()
        if client_err:
            error_msg = f"{timestamp_str}: TechInd: Client init error - {client_err}"
            app_logger.error(error_msg)
            new_errors.insert(0, error_msg)
            return output_cols, [], new_errors[:10]
        SCHWAB_CLIENT = client_to_use
        app_logger.info(f"TechIndicators: Schwab client reinitialized successfully for {selected_symbol}.")

    app_logger.info(f"Fetching minute data for Technical Indicators for {selected_symbol}...")
    # df_minute_raw has 'open', 'high', 'low', 'close', 'volume' columns and 'timestamp' as DatetimeIndex
    df_minute_raw, error = get_minute_data(client_to_use, selected_symbol, days_history=90) 

    if error:
        error_msg = f"{timestamp_str}: TechInd data fetch for {selected_symbol}: {error}"
        app_logger.error(error_msg)
        new_errors.insert(0, error_msg)
        return output_cols, [], new_errors[:10]
    
    if df_minute_raw.empty:
        app_logger.warning(f"No minute data returned for {selected_symbol} to calculate Technical Indicators.")
        # Return empty table with headers but add a message to errors?
        # error_msg = f"{timestamp_str}: TechInd: No data for {selected_symbol}."
        # new_errors.insert(0, error_msg)
        return output_cols, [], new_errors
    
    app_logger.info(f"Successfully fetched {len(df_minute_raw)} minute candles for {selected_symbol} for TA.")

    # Ensure df_minute_raw has DatetimeIndex named 'timestamp'
    # get_minute_data should already handle this by setting 'timestamp' as index.
    if not isinstance(df_minute_raw.index, pd.DatetimeIndex):
        if 'timestamp' in df_minute_raw.columns:
            try:
                df_minute_raw['timestamp'] = pd.to_datetime(df_minute_raw['timestamp'])
                df_minute_raw = df_minute_raw.set_index('timestamp')
                app_logger.info(f"TechInd: Converted 'timestamp' column to DatetimeIndex for {selected_symbol}.")
            except Exception as e:
                error_msg = f"{timestamp_str}: TechInd: Failed to convert 'timestamp' to DatetimeIndex for {selected_symbol}: {e}"
                app_logger.error(error_msg)
                new_errors.insert(0, error_msg)
                return output_cols, [], new_errors[:10]
        else:
            error_msg = f"{timestamp_str}: TechInd: Minute data for {selected_symbol} missing 'timestamp' column or DatetimeIndex."
            app_logger.error(error_msg)
            new_errors.insert(0, error_msg)
            return output_cols, [], new_errors[:10]

    # --- Data Aggregation ---
    app_logger.info(f"Aggregating data for {selected_symbol}...")
    df_15min_raw = aggregate_candles(df_minute_raw.copy(), rule="15min")
    df_hourly_raw = aggregate_candles(df_minute_raw.copy(), rule="H")
    df_daily_raw = aggregate_candles(df_minute_raw.copy(), rule="D")
    app_logger.info(f"Aggregation complete for {selected_symbol}. 1min: {len(df_minute_raw)}, 15min: {len(df_15min_raw)}, Hourly: {len(df_hourly_raw)}, Daily: {len(df_daily_raw)} rows.")

    # --- Calculate Technical Indicators for each timeframe ---
    app_logger.info(f"Calculating TA for {selected_symbol} across timeframes...")
    df_1min_ta = calculate_all_technical_indicators(df_minute_raw.copy(), symbol=f"{selected_symbol}_1min")
    df_15min_ta = calculate_all_technical_indicators(df_15min_raw.copy(), symbol=f"{selected_symbol}_15min")
    df_hourly_ta = calculate_all_technical_indicators(df_hourly_raw.copy(), symbol=f"{selected_symbol}_hourly")
    df_daily_ta = calculate_all_technical_indicators(df_daily_raw.copy(), symbol=f"{selected_symbol}_daily")
    app_logger.info(f"TA calculation complete for {selected_symbol}.")

    # --- Prepare data for the table ---
    indicators_to_display = {
        "BB Mid (20)": "bb_middle_20",
        "BB Upper (20)": "bb_upper_20",
        "BB Lower (20)": "bb_lower_20",
        "RSI (14)": "rsi_14",
        "MACD": "macd",
        "MACD Signal": "macd_signal",
        "MACD Hist": "macd_hist",
        "IMI (14)": "imi_14",
        "MFI (14)": "mfi_14",
        # Add FVG if simple representation is possible, otherwise might need specific handling
        # For now, FVG produces multiple columns (top/bottom), not a single value per candle easily shown here.
        # We can show if the *last* candle confirmed an FVG, for example.
    }

    table_data = []
    timeframe_dfs = {
        "1min": df_1min_ta,
        "15min": df_15min_ta,
        "Hourly": df_hourly_ta,
        "Daily": df_daily_ta
    }

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
    
    app_logger.info(f"Formatted TA data for {selected_symbol} table: {len(table_data)} indicators.")
    return output_cols, table_data, new_errors


@app.callback(
    Output("current-option-keys-store", "data"),
    Output("error-message-store", "data", allow_duplicate=True),
    Input("selected-symbol-store", "data"),
    Input("tabs-main", "value"),
    State("error-message-store", "data"),
    prevent_initial_call=True
)
def manage_options_stream(selected_symbol, active_tab, current_errors):
    new_errors = list(current_errors)
    option_keys_for_stream = []
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app_logger.info(f"manage_options_stream triggered. Symbol: {selected_symbol}, Active Tab: {active_tab}")

    if active_tab == "tab-options-chain" and selected_symbol:
        app_logger.info(f"Options tab active for {selected_symbol}. Managing stream.")
        global SCHWAB_CLIENT
        client_to_use = SCHWAB_CLIENT
        if not client_to_use:
            client_to_use, client_err = get_schwab_client()
            if client_err:
                error_msg = f"{timestamp_str}: StreamCtrl: {client_err}"
                new_errors.insert(0, error_msg)
                STREAMING_MANAGER.stop_stream()
                app_logger.error(f"StreamCtrl: Client error - {client_err}")
                return [], new_errors[:10]
            SCHWAB_CLIENT = client_to_use
        
        keys, err = get_option_contract_keys(client_to_use, selected_symbol)
        if err:
            error_msg = f"{timestamp_str}: StreamCtrl Keys for {selected_symbol}: {err}"
            new_errors.insert(0, error_msg)
            STREAMING_MANAGER.stop_stream()
            app_logger.error(f"StreamCtrl: Error getting keys for {selected_symbol} - {err}")
            return [], new_errors[:10]
        
        if not keys:
            app_logger.info(f"No option keys with OI > 0 found for {selected_symbol}. Stopping stream if active.")
            STREAMING_MANAGER.stop_stream()
            return [], new_errors

        option_keys_for_stream = list(keys)
        app_logger.info(f"Attempting to start/update stream for {len(option_keys_for_stream)} keys for {selected_symbol}.")
        STREAMING_MANAGER.start_stream(option_keys_for_stream)
    else:
        app_logger.info("Options tab not active or no symbol selected. Stopping stream.")
        STREAMING_MANAGER.stop_stream()
    
    app_logger.info(f"manage_options_stream returning keys: {len(option_keys_for_stream)} keys.")
    return option_keys_for_stream, new_errors

# Regex to parse OCC option symbol format
# Example: MSFT  250530C00435000 or SPXW  240520C05300000
# Group 1: Underlying (e.g., "MSFT  " or "SPXW  ")
# Group 2: Year (YY)
# Group 3: Month (MM)
# Group 4: Day (DD)
# Group 5: Type (C or P)
# Group 6: Strike Price (integer, divide by 1000)
OPTION_KEY_REGEX = re.compile(r"^([A-Z ]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")

@app.callback(
    Output("options-calls-table", "columns"),
    Output("options-calls-table", "data"),
    Output("options-puts-table", "columns"),
    Output("options-puts-table", "data"),
    Output("options-chain-stream-status", "children"),
    Output("error-message-store", "data", allow_duplicate=True),
    Input("options-chain-interval", "n_intervals"),
    State("selected-symbol-store", "data"),
    State("error-message-store", "data"),
    prevent_initial_call=True
)
def update_options_chain_stream_data(n_intervals, selected_symbol, current_errors):
    app_logger.info(f"update_options_chain_stream_data triggered for {selected_symbol} at interval {n_intervals}.")
    new_errors = list(current_errors)
    
    stream_status_msg, stream_error_msg = STREAMING_MANAGER.get_status()
    status_display = f"Stream Status: {stream_status_msg}"
    if stream_error_msg:
        status_display += f" | Last Stream Error: {stream_error_msg}"
    app_logger.debug(f"Stream status for UI: {status_display}")

    option_cols_def = ["Expiration Date", "Strike", "Last", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility", "Delta", "Gamma", "Theta", "Vega", "Contract Key"]
    option_cols = [{"name": i, "id": i} for i in option_cols_def]

    if not selected_symbol or not STREAMING_MANAGER.is_running:
        app_logger.info("No selected symbol or stream not running. Returning empty tables.")
        return option_cols, [], option_cols, [], status_display, new_errors[:10]

    latest_stream_data = STREAMING_MANAGER.get_latest_data()
    app_logger.info(f"Fetched {len(latest_stream_data)} items from STREAMING_MANAGER.get_latest_data().")
    if latest_stream_data and n_intervals % 5 == 0: # Log a sample periodically
        if latest_stream_data:
            sample_key = list(latest_stream_data.keys())[0]
            app_logger.debug(f"Sample data item (key: {sample_key}) from stream store: {json.dumps(latest_stream_data[sample_key], indent=2)}")
    
    calls_list = []
    puts_list = []

    for contract_key_from_store, data_dict in latest_stream_data.items():
        if not isinstance(data_dict, dict):
            app_logger.warning(f"Skipping non-dict item in latest_stream_data for key {contract_key_from_store}: {type(data_dict)}")
            continue

        contract_key_str = str(data_dict.get("key", ""))
        parsed_expiration_date = "N/A"
        parsed_strike_price = "N/A"
        is_call = False
        is_put = False

        # Try to parse from dedicated fields first
        exp_year_val = data_dict.get("expirationYear")
        exp_month_val = data_dict.get("expirationMonth")
        exp_day_val = data_dict.get("expirationDay")
        strike_val = data_dict.get("strikePrice")
        contract_type_val = data_dict.get("contractType") # Should be "CALL" or "PUT"

        if isinstance(exp_year_val, (int, float)) and isinstance(exp_month_val, (int, float)) and isinstance(exp_day_val, (int, float)):
            try:
                # Schwab API returns year as full year (e.g., 2024) or YY (e.g., 24). Standardize to YYYY.
                year_prefix = "20" if exp_year_val < 100 else ""
                parsed_expiration_date = f"{year_prefix}{int(exp_year_val):02d}-{int(exp_month_val):02d}-{int(exp_day_val):02d}"
            except ValueError:
                app_logger.warning(f"Could not format date from fields for key {contract_key_str}: Y={exp_year_val}, M={exp_month_val}, D={exp_day_val}")
        
        if isinstance(strike_val, (int, float)):
            parsed_strike_price = strike_val
        
        if isinstance(contract_type_val, str):
            if contract_type_val.upper() == "CALL" or contract_type_val.upper() == "C":
                is_call = True
            elif contract_type_val.upper() == "PUT" or contract_type_val.upper() == "P":
                is_put = True

        # Fallback to parsing from contract key if dedicated fields are missing/invalid or type is unknown
        if parsed_expiration_date == "N/A" or parsed_strike_price == "N/A" or (not is_call and not is_put):
            app_logger.debug(f"Parsing option key {contract_key_str} as fallback or for missing type/strike/exp.")
            key_match = OPTION_KEY_REGEX.match(contract_key_str.replace(" ", "")) # Remove spaces for regex
            if key_match:
                underlying, year_str, month_str, day_str, type_char, strike_str = key_match.groups()
                if parsed_expiration_date == "N/A":
                    parsed_expiration_date = f"20{year_str}-{month_str}-{day_str}"
                if parsed_strike_price == "N/A":
                    try:
                        parsed_strike_price = float(strike_str) / 1000.0
                    except ValueError:
                        app_logger.warning(f"Could not parse strike from key {contract_key_str}")
                if not is_call and not is_put:
                    if type_char == "C": is_call = True
                    if type_char == "P": is_put = True
            else:
                app_logger.warning(f"Could not parse option key {contract_key_str} with regex.")
                # continue # Skip if key cannot be parsed at all for essential info

        option_item = {
            "Expiration Date": parsed_expiration_date,
            "Strike": parsed_strike_price,
            "Last": data_dict.get("lastPrice", "N/A"),
            "Bid": data_dict.get("bidPrice", "N/A"),
            "Ask": data_dict.get("askPrice", "N/A"),
            "Volume": data_dict.get("totalVolume", "N/A"),
            "Open Interest": data_dict.get("openInterest", "N/A"),
            "Implied Volatility": f"{data_dict.get('volatility', 0) * 100:.2f}%" if pd.notna(data_dict.get('volatility')) else "N/A",
            "Delta": f"{data_dict.get('delta', 0):.4f}" if pd.notna(data_dict.get('delta')) else "N/A",
            "Gamma": f"{data_dict.get('gamma', 0):.4f}" if pd.notna(data_dict.get('gamma')) else "N/A",
            "Theta": f"{data_dict.get('theta', 0):.4f}" if pd.notna(data_dict.get('theta')) else "N/A",
            "Vega": f"{data_dict.get('vega', 0):.4f}" if pd.notna(data_dict.get('vega')) else "N/A",        "Contract Key": contract_key_str
        }

        if is_call:
            calls_list.append(option_item)
        elif is_put:
            puts_list.append(option_item)
        # else: # Log if neither call nor put, though should be rare if parsing works
            # app_logger.warning(f"Option key {contract_key_str} is neither CALL nor PUT after parsing.")

    # Sort by expiration date (ascending) and then strike price (ascending)
    calls_list.sort(key=lambda x: (x["Expiration Date"], x["Strike"] if isinstance(x["Strike"], (int, float)) else float("inf")))
    puts_list.sort(key=lambda x: (x["Expiration Date"], x["Strike"] if isinstance(x["Strike"], (int, float)) else float("inf")))
    
    app_logger.info(f"Processed stream data: {len(calls_list)} calls, {len(puts_list)} puts for {selected_symbol}.")
    return option_cols, calls_list, option_cols, puts_list, status_display, new_errors[:10]


if __name__ == "__main__":
    app_logger.info("Starting Dash development server...")
    # For development, you might need to set SCHWAB_ACCOUNT_HASH as an env var
    # or ensure your .env file is loaded if you use python-dotenv in a wrapper script.
    # Example: os.environ["SCHWAB_ACCOUNT_HASH"] = "YOUR_ACCOUNT_HASH_FOR_STREAMING"
    app.run(debug=True, host="0.0.0.0", port=8050)
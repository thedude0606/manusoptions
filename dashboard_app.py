# Dash App Structure

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State, ALL
import pandas as pd
import datetime
import os # For account ID
import logging # For app-level logging
import json # For pretty printing dicts in logs

# Import utility functions
from dashboard_utils.data_fetchers import get_schwab_client, get_minute_data, get_options_chain_data, get_option_contract_keys
from dashboard_utils.streaming_manager import StreamingManager

# Configure basic logging for the app
# Use a specific logger for this module to avoid conflicts if other modules also configure root logger
app_logger = logging.getLogger(__name__)
if not app_logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    app_handler = logging.StreamHandler()
    app_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    app_handler.setFormatter(app_formatter)
    app_logger.addHandler(app_handler)
app_logger.setLevel(logging.INFO) # Set to INFO or DEBUG as needed

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Trading Dashboard"

# --- Schwab Client and Account ID Setup ---
def schwab_client_provider():
    """Provides the Schwab client instance."""
    client, _ = get_schwab_client() # We only need the client object here
    return client

def account_id_provider():
    """Provides the account ID (account hash for streaming), if available."""
    return os.getenv("SCHWAB_ACCOUNT_HASH") 

# --- Global Instances --- 
SCHWAB_CLIENT, client_init_error = get_schwab_client() # For REST calls
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
        minute_header = f"Minute Data for {selected_symbol}"
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
        client_to_use, client_err = get_schwab_client()
        if client_err:
            error_msg = f"{timestamp_str}: MinData: {client_err}"
            new_errors.insert(0, error_msg)
            return [], [], new_errors[:10]
        SCHWAB_CLIENT = client_to_use

    df, error = get_minute_data(client_to_use, selected_symbol)

    if error:
        error_msg = f"{timestamp_str}: MinData for {selected_symbol}: {error}"
        new_errors.insert(0, error_msg)
        return [], [], new_errors[:10]
    
    if df.empty:
        cols = [{"name": i, "id": i} for i in ["Timestamp", "Open", "High", "Low", "Close", "Volume"]]
        return cols, [], new_errors

    cols = [{"name": i, "id": i} for i in df.columns]
    data = df.to_dict("records")
    return cols, data, new_errors

@app.callback(
    Output("tech-indicators-table", "columns"),
    Output("tech-indicators-table", "data"),
    Input("selected-symbol-store", "data"),
    prevent_initial_call=True
)
def update_tech_indicators_tab(selected_symbol):
    if not selected_symbol:
        return [], []
    dummy_cols = [{"name": i, "id": i} for i in ["Indicator", "1min", "15min", "1hour", "Daily"]]
    dummy_data = pd.DataFrame({
        "Indicator": ["SMA(20)", "RSI(14)"], 
        "1min": [f"{selected_symbol}-val1", f"{selected_symbol}-val2"], 
        "15min": [151.0, 48.0], "1hour": [155.0, 55.0], "Daily": [160.0, 60.0]
    }).to_dict("records")
    return dummy_cols, dummy_data

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
    app_logger.debug(f"update_options_chain_stream_data triggered. Interval: {n_intervals}, Symbol: {selected_symbol}")
    new_errors = list(current_errors)
    
    stream_status_msg, stream_error_msg = STREAMING_MANAGER.get_status()
    status_display = f"Stream Status: {stream_status_msg}"
    if stream_error_msg:
        status_display += f" | Last Stream Error: {stream_error_msg}"
    app_logger.debug(f"Stream status for UI: {status_display}")

    option_cols_def = ["Expiration Date", "Strike", "Last", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility", "Delta", "Gamma", "Theta", "Vega", "Contract Key"]
    option_cols = [{"name": i, "id": i} for i in option_cols_def]

    if not selected_symbol or not STREAMING_MANAGER.is_running:
        app_logger.debug("No selected symbol or stream not running. Returning empty tables.")
        return option_cols, [], option_cols, [], status_display, new_errors[:10]

    latest_stream_data = STREAMING_MANAGER.get_latest_data()
    app_logger.debug(f"Fetched {len(latest_stream_data)} items from STREAMING_MANAGER.get_latest_data(). Sample: {json.dumps(list(latest_stream_data.values())[:1], indent=2) if latest_stream_data else "{}"}")
    
    calls_list = []
    puts_list = []

    for _contract_key, data_dict in latest_stream_data.items():
        record = {
            "Expiration Date": f"{data_dict.get("expirationYear")}-{str(data_dict.get("expirationMonth", "")).zfill(2)}-{str(data_dict.get("expirationDay", "")).zfill(2)}",
            "Strike": data_dict.get("strikePrice"),
            "Last": data_dict.get("lastPrice"),
            "Bid": data_dict.get("bidPrice"),
            "Ask": data_dict.get("askPrice"),
            "Volume": data_dict.get("totalVolume"),
            "Open Interest": data_dict.get("openInterest"),
            "Implied Volatility": data_dict.get("volatility"),
            "Delta": data_dict.get("delta"),
            "Gamma": data_dict.get("gamma"),
            "Theta": data_dict.get("theta"),
            "Vega": data_dict.get("vega"),
            "Contract Key": data_dict.get("key")
        }
        if data_dict.get("contractType") == "CALL":
            calls_list.append(record)
        elif data_dict.get("contractType") == "PUT":
            puts_list.append(record)

    app_logger.debug(f"Processed into {len(calls_list)} calls and {len(puts_list)} puts.")

    calls_df = pd.DataFrame(calls_list)
    puts_df = pd.DataFrame(puts_list)

    if not calls_df.empty:
        for col in option_cols_def: 
            if col not in calls_df.columns: calls_df[col] = None
        calls_df = calls_df[option_cols_def]
    if not puts_df.empty:
        for col in option_cols_def:
            if col not in puts_df.columns: puts_df[col] = None
        puts_df = puts_df[option_cols_def]

    return option_cols, calls_df.to_dict("records"), option_cols, puts_df.to_dict("records"), status_display, new_errors[:10]


if __name__ == "__main__":
    import atexit
    def stop_stream_on_exit():
        app_logger.info("Stopping stream on application exit...")
        STREAMING_MANAGER.stop_stream()
        app_logger.info("Stream stopped.")
    atexit.register(stop_stream_on_exit)

    app_logger.info("Starting Dash app...")
    app.run(debug=True, host="0.0.0.0", port=8050)


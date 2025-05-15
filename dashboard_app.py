# Dash App Structure

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State, ALL
import pandas as pd
import datetime
import os # For account ID
import logging # For app-level logging
import json # For pretty printing dicts in logs
import re # For parsing option key
import plotly.graph_objects as go
from plotly.subplots import make_subplots # Added for subplots

# Import utility functions
from dashboard_utils.data_fetchers import get_schwab_client, get_minute_data, get_options_chain_data, get_option_contract_keys
from dashboard_utils.streaming_manager import StreamingManager
from analysis_utils.technical_indicators import calculate_bollinger_bands, calculate_rsi # Added calculate_rsi

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
                dcc.Graph(id="tech-indicators-chart", style={"height": "800px"}) # Increased height for subplots
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
        client_to_use, client_err = get_schwab_client()
        if client_err:
            error_msg = f"{timestamp_str}: MinData: {client_err}"
            new_errors.insert(0, error_msg)
            return [], [], new_errors[:10]
        SCHWAB_CLIENT = client_to_use

    # Fetch up to 90 days of minute data
    df, error = get_minute_data(client_to_use, selected_symbol, days_history=90)

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
    Output("tech-indicators-chart", "figure"),
    Output("error-message-store", "data", allow_duplicate=True),
    Input("selected-symbol-store", "data"),
    State("error-message-store", "data"),
    prevent_initial_call=True
)
def update_tech_indicators_tab(selected_symbol, current_errors):
    if not selected_symbol:
        # Return an empty figure with 2 rows if no symbol is selected
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.update_layout(title_text="Select a symbol to view indicators", height=800)
        return fig, current_errors

    global SCHWAB_CLIENT
    new_errors = list(current_errors)
    client_to_use = SCHWAB_CLIENT
    # Create a figure with 2 subplots: one for price/BB, one for RSI
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                        row_heights=[0.7, 0.3],  # Price chart takes 70%, RSI takes 30%
                        subplot_titles=(f"{selected_symbol} Price & Bollinger Bands", "Relative Strength Index (RSI)"))
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not client_to_use:
        client_to_use, client_err = get_schwab_client()
        if client_err:
            error_msg = f"{timestamp_str}: TechInd: {client_err}"
            new_errors.insert(0, error_msg)
            fig.add_annotation(text=f"Error: {client_err}", showarrow=False, row=1, col=1)
            fig.update_layout(height=800)
            return fig, new_errors[:10]
        SCHWAB_CLIENT = client_to_use

    price_df, error = get_minute_data(client_to_use, selected_symbol, days_history=60)

    if error:
        error_msg = f"{timestamp_str}: TechInd Data for {selected_symbol}: {error}"
        new_errors.insert(0, error_msg)
        fig.add_annotation(text=f"Error fetching data: {error}", showarrow=False, row=1, col=1)
        fig.update_layout(height=800)
        return fig, new_errors[:10]
    
    if price_df.empty:
        fig.add_annotation(text="No price data available to calculate indicators.", showarrow=False, row=1, col=1)
        fig.update_layout(height=800)
        return fig, new_errors

    required_cols = ["Timestamp", "Open", "High", "Low", "Close"]
    if not all(col in price_df.columns for col in required_cols):
        error_msg = f"{timestamp_str}: TechInd Data for {selected_symbol}: Missing one or more required columns (Timestamp, Open, High, Low, Close) in fetched data."
        new_errors.insert(0, error_msg)
        fig.add_annotation(text="Error: Data missing required columns.", showarrow=False, row=1, col=1)
        fig.update_layout(height=800)
        return fig, new_errors[:10]
        
    price_df["Timestamp"] = pd.to_datetime(price_df["Timestamp"])
    price_df = price_df.sort_values(by="Timestamp")
    close_prices = price_df["Close"].tolist()

    # Calculate Bollinger Bands
    upper_bands, middle_bands, lower_bands = calculate_bollinger_bands(close_prices)
    
    # Calculate RSI
    rsi_values = calculate_rsi(close_prices) # Using default window 14

    # Candlestick chart (Row 1)
    fig.add_trace(go.Candlestick(x=price_df["Timestamp"],
                               open=price_df["Open"],
                               high=price_df["High"],
                               low=price_df["Low"],
                               close=price_df["Close"],
                               name=f"{selected_symbol} Price"), row=1, col=1)

    # Bollinger Bands traces (Row 1)
    fig.add_trace(go.Scatter(x=price_df["Timestamp"], y=upper_bands, mode="lines", name="Upper Band", line=dict(color="blue", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=price_df["Timestamp"], y=middle_bands, mode="lines", name="Middle Band (SMA 20)", line=dict(color="orange", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=price_df["Timestamp"], y=lower_bands, mode="lines", name="Lower Band", line=dict(color="blue", width=1)), row=1, col=1)

    # RSI trace (Row 2)
    fig.add_trace(go.Scatter(x=price_df["Timestamp"], y=rsi_values, mode="lines", name="RSI (14)", line=dict(color="purple", width=1.5)), row=2, col=1)
    # Add RSI Overbought/Oversold lines
    fig.add_hline(y=70, line_dash="dash", line_color="red", line_width=1, annotation_text="Overbought (70)", annotation_position="bottom right", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", line_width=1, annotation_text="Oversold (30)", annotation_position="bottom right", row=2, col=1)

    fig.update_layout(
        height=800, # Ensure height is set for the overall figure
        xaxis_rangeslider_visible=False, # Hide for the main price chart
        xaxis2_rangeslider_visible=True, # Optionally show for RSI or hide as well
        legend_tracegroupgap=180 # Adjust gap if legends overlap with subplots
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1) # RSI typically 0-100
    
    return fig, new_errors


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
    if latest_stream_data and n_intervals % 5 == 0: 
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

        exp_year_val = data_dict.get("expirationYear")
        exp_month_val = data_dict.get("expirationMonth")
        exp_day_val = data_dict.get("expirationDay")
        strike_val = data_dict.get("strikePrice")
        contract_type_val = data_dict.get("contractType")

        if isinstance(exp_year_val, (int, float)) and isinstance(exp_month_val, (int, float)) and isinstance(exp_day_val, (int, float)):
            try:
                parsed_expiration_date = f"20{int(exp_year_val):02d}-{int(exp_month_val):02d}-{int(exp_day_val):02d}"
            except ValueError:
                app_logger.warning(f"Could not format date from fields for key {contract_key_str}: Y={exp_year_val}, M={exp_month_val}, D={exp_day_val}")
        
        if isinstance(strike_val, (int, float)):
            parsed_strike_price = strike_val
        
        if contract_type_val == "CALL" or contract_type_val == "C":
            is_call = True
        elif contract_type_val == "PUT" or contract_type_val == "P":
            is_put = True

        if parsed_expiration_date == "N/A" or parsed_strike_price == "N/A" or (not is_call and not is_put):
            key_match = OPTION_KEY_REGEX.match(contract_key_str)
            if key_match:
                _raw_symbol, year_str, month_str, day_str, type_char, strike_raw = key_match.groups()
                try:
                    parsed_expiration_date = f"20{year_str}-{month_str}-{day_str}"
                    parsed_strike_price = float(strike_raw) / 1000.0
                    if type_char == "C":
                        is_call = True
                    elif type_char == "P":
                        is_put = True
                except ValueError as e:
                    app_logger.warning(f"Error parsing contract key {contract_key_str}: {e}")
            else:
                app_logger.warning(f"Could not parse OCC option key: {contract_key_str}")

        row = {
            "Expiration Date": parsed_expiration_date,
            "Strike": parsed_strike_price,
            "Last": data_dict.get("lastPrice", "N/A"),
            "Bid": data_dict.get("bidPrice", "N/A"),
            "Ask": data_dict.get("askPrice", "N/A"),
            "Volume": data_dict.get("totalVolume", "N/A"),
            "Open Interest": data_dict.get("openInterest", "N/A"),
            "Implied Volatility": data_dict.get("volatility", "N/A"),
            "Delta": data_dict.get("delta", "N/A"),
            "Gamma": data_dict.get("gamma", "N/A"),
            "Theta": data_dict.get("theta", "N/A"),
            "Vega": data_dict.get("vega", "N/A"),
            "Contract Key": contract_key_str
        }

        if is_call:
            calls_list.append(row)
        elif is_put:
            puts_list.append(row)

    app_logger.info(f"Processed into {len(calls_list)} calls and {len(puts_list)} puts.")
    calls_df = pd.DataFrame(calls_list)
    puts_df = pd.DataFrame(puts_list)

    return option_cols, calls_df.to_dict("records"), option_cols, puts_df.to_dict("records"), status_display, new_errors[:10]


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)


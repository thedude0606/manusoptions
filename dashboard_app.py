# Dash App Structure

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import datetime

# Import utility functions
from dashboard_utils.data_fetchers import get_schwab_client, get_minute_data, get_options_chain_data # Added get_options_chain_data

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Trading Dashboard"

# Attempt to initialize a global client instance for reuse
SCHWAB_CLIENT, client_init_error = get_schwab_client() # Store client and initial error
initial_errors = []
if client_init_error:
    initial_errors.append(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {client_init_error}")


# Main layout
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
        dcc.Tab(label="Options Chain", value="tab-options-chain", children=[
            html.Div(id="options-chain-content", children=[
                html.H4(id="options-chain-header"),
                html.Div(id="options-chain-last-updated", style={"marginBottom": "10px"}), # For last updated timestamp
                html.Div([
                    html.Div([html.H5("Calls"), dash_table.DataTable(id="options-calls-table", columns=[], data=[], page_size=10, style_table={"overflowX": "auto"}, sort_action="native") ], style={"width": "49%", "display": "inline-block", "verticalAlign": "top", "marginRight": "1%"}),
                    html.Div([html.H5("Puts"), dash_table.DataTable(id="options-puts-table", columns=[], data=[], page_size=10, style_table={"overflowX": "auto"}, sort_action="native") ], style={"width": "49%", "display": "inline-block", "float": "right", "verticalAlign": "top"})
                ])
            ]),
            dcc.Interval(id="options-chain-interval", interval=5*1000, n_intervals=0) # 5-second interval
        ]),
    ]),
    
    dcc.Store(id="processed-symbols-store"),
    dcc.Store(id="selected-symbol-store"),
    dcc.Store(id="error-message-store", data=initial_errors), # Store for error messages, initialized with client error if any

    html.Div(id="error-log-display", children="No errors yet." if not initial_errors else [html.P(err) for err in initial_errors], style={"marginTop": "20px", "border": "1px solid #ccc", "padding": "10px", "height": "100px", "overflowY": "scroll", "whiteSpace": "pre-wrap"})
])

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
        options_header = f"Options Chain for {selected_symbol}"
        return minute_header, tech_header, options_header
    return "Select a symbol to view data", "Select a symbol to view data", "Select a symbol to view data"

# Callback to update the error log display
@app.callback(
    Output("error-log-display", "children"),
    Input("error-message-store", "data")
)
def update_error_log(error_messages):
    if error_messages:
        log_content = [html.P(f"{msg}") for msg in reversed(error_messages)]
        return log_content
    return "No new errors."

# Callback for Minute Data Tab
@app.callback(
    Output("minute-data-table", "columns"),
    Output("minute-data-table", "data"),
    Output("error-message-store", "data", allow_duplicate=True), # Update error store
    Input("selected-symbol-store", "data"),
    State("error-message-store", "data"), # Get current errors to append
    prevent_initial_call=True
)
def update_minute_data_tab(selected_symbol, current_errors):
    if not selected_symbol:
        return [], [], current_errors 

    global SCHWAB_CLIENT
    new_errors = list(current_errors) 
    client_to_use = SCHWAB_CLIENT

    if not client_to_use:
        client_to_use, client_err = get_schwab_client()
        if client_err:
            error_msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Failed to initialize Schwab client for minute data: {client_err}"
            new_errors.insert(0, error_msg)
            return [], [], new_errors[:5]
        SCHWAB_CLIENT = client_to_use # Update global if re-initialized

    df, error = get_minute_data(client_to_use, selected_symbol)

    if error:
        error_msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Error fetching minute data for {selected_symbol}: {error}"
        new_errors.insert(0, error_msg)
        return [], [], new_errors[:5]
    
    if df.empty:
        cols = [{"name": i, "id": i} for i in ["Timestamp", "Open", "High", "Low", "Close", "Volume"]]
        return cols, [], new_errors

    cols = [{"name": i, "id": i} for i in df.columns]
    data = df.to_dict("records")
    return cols, data, new_errors


# Placeholder callback for Technical Indicators Tab
@app.callback(
    Output("tech-indicators-table", "columns"),
    Output("tech-indicators-table", "data"),
    Input("selected-symbol-store", "data")
)
def update_tech_indicators_tab(selected_symbol):
    if not selected_symbol:
        return [], []
    dummy_cols = [{"name": i, "id": i} for i in ["Indicator", "1min", "15min", "1hour", "Daily"]]
    dummy_data = pd.DataFrame({
        "Indicator": ["SMA(20)", "RSI(14)"], 
        "1min": [f"{selected_symbol}-val", f"{selected_symbol}-val"], 
        "15min": [151.0, 48.0], "1hour": [155.0, 55.0], "Daily": [160.0, 60.0]
    }).to_dict("records")
    return dummy_cols, dummy_data

# Callback for Options Chain Tab
@app.callback(
    Output("options-calls-table", "columns"),
    Output("options-calls-table", "data"),
    Output("options-puts-table", "columns"),
    Output("options-puts-table", "data"),
    Output("options-chain-last-updated", "children"),
    Output("error-message-store", "data", allow_duplicate=True),
    Input("selected-symbol-store", "data"),
    Input("options-chain-interval", "n_intervals"),
    State("error-message-store", "data"),
    prevent_initial_call=True
)
def update_options_chain_tab(selected_symbol, n_intervals, current_errors):
    if not selected_symbol:
        return [], [], [], [], "Options chain data will load when a symbol is selected.", current_errors

    global SCHWAB_CLIENT
    new_errors = list(current_errors)
    client_to_use = SCHWAB_CLIENT

    if not client_to_use:
        client_to_use, client_err = get_schwab_client()
        if client_err:
            error_msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Failed to initialize Schwab client for options chain: {client_err}"
            new_errors.insert(0, error_msg)
            return [], [], [], [], "Error initializing client.", new_errors[:5]
        SCHWAB_CLIENT = client_to_use # Update global if re-initialized

    calls_df, puts_df, error = get_options_chain_data(client_to_use, selected_symbol)
    
    last_updated_time = f"Last Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}"

    if error:
        error_msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Error fetching options chain for {selected_symbol}: {error}"
        new_errors.insert(0, error_msg)
        # Return empty tables but update timestamp and errors
        return [], [], [], [], last_updated_time, new_errors[:5]

    option_cols_def = ["Expiration Date", "Strike", "Last", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility", "Delta", "Gamma", "Theta", "Vega"]
    option_cols = [{"name": i, "id": i} for i in option_cols_def]

    calls_data = calls_df.to_dict("records") if not calls_df.empty else []
    puts_data = puts_df.to_dict("records") if not puts_df.empty else []
    
    return option_cols, calls_data, option_cols, puts_data, last_updated_time, new_errors

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

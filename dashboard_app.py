# Dash App Structure

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import datetime

# Import utility functions
from dashboard_utils.data_fetchers import get_schwab_client, get_minute_data

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Trading Dashboard"

# Attempt to initialize a global client instance for reuse
# This is a simple approach; for more robust applications, consider managing client state carefully.
SCHWAB_CLIENT = get_schwab_client()

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
                    page_size=15, # Add pagination
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
                html.Div([
                    html.Div([html.H5("Calls"), dash_table.DataTable(id="options-calls-table", columns=[], data=[], page_size=10, style_table={"overflowX": "auto"})], style={"width": "49%", "display": "inline-block", "verticalAlign": "top"}),
                    html.Div([html.H5("Puts"), dash_table.DataTable(id="options-puts-table", columns=[], data=[], page_size=10, style_table={"overflowX": "auto"})], style={"width": "49%", "display": "inline-block", "float": "right", "verticalAlign": "top"})
                ])
            ]),
            dcc.Interval(id="options-chain-interval", interval=5*1000, n_intervals=0)
        ]),
    ]),
    
    dcc.Store(id="processed-symbols-store"),
    dcc.Store(id="selected-symbol-store"),
    dcc.Store(id="error-message-store", data=[]), # Store for error messages

    html.Div(id="error-log-display", children="No errors yet.", style={"marginTop": "20px", "border": "1px solid #ccc", "padding": "10px", "height": "100px", "overflowY": "scroll", "whiteSpace": "pre-wrap"})
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
        # Display errors with timestamps, newest first
        log_content = [html.P(f"{msg}") for msg in reversed(error_messages)]
        return log_content
    return "No new errors."

# Callback for Minute Data Tab
@app.callback(
    Output("minute-data-table", "columns"),
    Output("minute-data-table", "data"),
    Output("error-message-store", "data"), # Update error store
    Input("selected-symbol-store", "data"),
    State("error-message-store", "data") # Get current errors to append
)
def update_minute_data_tab(selected_symbol, current_errors):
    if not selected_symbol:
        return [], [], current_errors # No symbol, no update, no new error

    global SCHWAB_CLIENT
    if not SCHWAB_CLIENT:
        SCHWAB_CLIENT = get_schwab_client() # Try to re-initialize if None
        if not SCHWAB_CLIENT:
            error_msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Failed to initialize Schwab client for minute data."
            updated_errors = [error_msg] + current_errors[:4] # Keep last 5 errors
            return [], [], updated_errors

    df, error = get_minute_data(SCHWAB_CLIENT, selected_symbol)
    new_errors = list(current_errors) # Make a mutable copy

    if error:
        error_msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Error fetching minute data for {selected_symbol}: {error}"
        new_errors.insert(0, error_msg)
        return [], [], new_errors[:5]
    
    if df.empty:
        # This case is handled by the error string from get_minute_data if it's an API issue
        # If it's just no data, we can show an empty table.
        cols = [{"name": i, "id": i} for i in ["Timestamp", "Open", "High", "Low", "Close", "Volume"]]
        return cols, [], new_errors

    cols = [{"name": i, "id": i} for i in df.columns]
    data = df.to_dict("records")
    return cols, data, new_errors


# Placeholder callback for Technical Indicators Tab
@app.callback(
    Output("tech-indicators-table", "columns"),
    Output("tech-indicators-table", "data"),
    # Output for error store if this callback also fetches data
    Input("selected-symbol-store", "data")
)
def update_tech_indicators_tab(selected_symbol):
    if not selected_symbol:
        return [], []
    # TODO: Replace with actual data fetching and TA calculation logic
    dummy_cols = [{"name": i, "id": i} for i in ["Indicator", "1min", "15min", "1hour", "Daily"]]
    dummy_data = pd.DataFrame({
        "Indicator": ["SMA(20)", "RSI(14)"], 
        "1min": [f"{selected_symbol}-val", f"{selected_symbol}-val"], 
        "15min": [151.0, 48.0], "1hour": [155.0, 55.0], "Daily": [160.0, 60.0]
    }).to_dict("records")
    return dummy_cols, dummy_data

# Placeholder callback for Options Chain Tab
@app.callback(
    Output("options-calls-table", "columns"),
    Output("options-calls-table", "data"),
    Output("options-puts-table", "columns"),
    Output("options-puts-table", "data"),
    # Output for error store if this callback also fetches data
    Input("selected-symbol-store", "data"),
    Input("options-chain-interval", "n_intervals")
)
def update_options_chain_tab(selected_symbol, n_intervals):
    if not selected_symbol:
        return [], [], [], []
    # TODO: Replace with actual data fetching logic for options
    option_cols = [{"name": i, "id": i} for i in ["Strike", "Last", "Bid", "Ask", "Volume", "Open Interest", "Volatility", "Delta", "Gamma", "Theta", "Vega"]]
    
    dummy_calls_data = pd.DataFrame({
        "Strike": [150, 155], "Last": [n_intervals, 1.20], "Bid": [2.45, 1.15], "Ask": [2.55, 1.25], 
        "Volume": [100, 50], "Open Interest": [1000, 500], "Volatility": [0.3, 0.32], 
        "Delta": [0.6, 0.4], "Gamma": [0.05, 0.04], "Theta": [-0.02, -0.015], "Vega": [0.1, 0.08]
    }).to_dict("records")
    
    dummy_puts_data = pd.DataFrame({
        "Strike": [145, 150], "Last": [1.80, n_intervals], "Bid": [1.75, 3.05], "Ask": [1.85, 3.15], 
        "Volume": [80, 120], "Open Interest": [800, 1200], "Volatility": [0.31, 0.29], 
        "Delta": [-0.4, -0.6], "Gamma": [0.045, 0.055], "Theta": [-0.018, -0.022], "Vega": [0.09, 0.11]
    }).to_dict("records")
    
    return option_cols, dummy_calls_data, option_cols, dummy_puts_data

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

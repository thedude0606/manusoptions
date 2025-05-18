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
                dash_table.DataTable(
                    id="tech-indicators-table", 
                    columns=[], 
                    data=[],
                    page_size=10,
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
    dcc.Store(id="tech-indicators-store", data=None),  # Store for technical indicators data to be exported

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


# Merged callback for Minute Data and Technical Indicators
@app.callback(
    Output("minute-data-table", "columns"),
    Output("minute-data-table", "data"),
    Output("tech-indicators-table", "columns"),
    Output("tech-indicators-table", "data"),
    Output("minute-data-store", "data"),  # Store minute data for export
    Output("tech-indicators-store", "data"),  # Store technical indicators data for export
    Output("new-error-event-store", "data"), # No allow_duplicate=True
    Input("selected-symbol-store", "data"),
    Input("tabs-main", "value"), # To know which tab is active
    prevent_initial_call=True
)
def update_data_for_active_tab(selected_symbol, active_tab):
    app_logger.debug(f"CB_update_data_for_active_tab: Symbol: {selected_symbol}, Active Tab: {active_tab}")

    minute_cols, minute_data = dash.no_update, dash.no_update
    tech_cols, tech_data = dash.no_update, dash.no_update
    minute_data_store = dash.no_update
    tech_data_store = dash.no_update
    error_event_to_send = dash.no_update

    default_minute_cols = [{"name": i, "id": i} for i in ["Timestamp", "Open", "High", "Low", "Close", "Volume"]]
    default_tech_cols_def = ["Indicator", "1min", "15min", "Hourly", "Daily"]
    default_tech_cols = [{"name": i, "id": i} for i in default_tech_cols_def]

    if not selected_symbol:
        app_logger.debug("CB_update_data_for_active_tab: No selected symbol. Clearing tables.")
        minute_cols, minute_data = default_minute_cols, []
        tech_cols, tech_data = default_tech_cols, []
        minute_data_store = None
        tech_data_store = None
        return minute_cols, minute_data, tech_cols, tech_data, minute_data_store, tech_data_store, error_event_to_send

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
            tech_cols, tech_data = default_tech_cols, []
            minute_data_store = None
            tech_data_store = None
            return minute_cols, minute_data, tech_cols, tech_data, minute_data_store, tech_data_store, error_event_to_send
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
            minute_data_store = None
        elif df.empty:
            app_logger.warning(f"UpdateDataTabs (MinuteData): No minute data returned for {selected_symbol}.")
            minute_cols, minute_data = default_minute_cols, []
            minute_data_store = None
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
                    minute_data_store = None

            elif not isinstance(df.index, pd.DatetimeIndex):
                error_msg = "Index is not DatetimeIndex after fetch."
                app_logger.error(f"UpdateDataTabs (MinuteData-Format) for {selected_symbol}: {error_msg}")
                error_event_to_send = {"source": f"MinData-Format-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                minute_cols, minute_data = default_minute_cols, []
                minute_data_store = None
            
            if error_event_to_send is dash.no_update: # if no formatting error occurred
                df_display = df.reset_index()
                df_display["timestamp"] = df_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                minute_cols = [{"name": i, "id": i} for i in df_display.columns]
                minute_data = df_display.to_dict("records")
                minute_data_store = df_display.to_dict("records")
                app_logger.info(f"UpdateDataTabs (MinuteData): Formatted data for {selected_symbol} table. Rows: {len(minute_data)}")

    elif active_tab == "tab-tech-indicators":
        app_logger.info(f"UpdateDataTabs: Fetching minute data for technical indicators for {selected_symbol}...")
        df_minute_raw, error = get_minute_data(client_to_use, selected_symbol, days_history=90)
        
        if error:
            error_msg = f"Data fetch error: {error}"
            app_logger.error(f"UpdateDataTabs (TechInd-Fetch) for {selected_symbol}: {error_msg}")
            error_event_to_send = {"source": f"TechInd-Fetch-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
            tech_cols, tech_data = default_tech_cols, []
            tech_data_store = None
        elif df_minute_raw.empty:
            app_logger.warning(f"UpdateDataTabs (TechInd): No minute data returned for {selected_symbol}.")
            tech_cols, tech_data = default_tech_cols, []
            tech_data_store = None
        else:
            app_logger.info(f"UpdateDataTabs (TechInd): Successfully fetched {len(df_minute_raw)} rows for {selected_symbol}.")
            try:
                # Ensure we have a DatetimeIndex
                if "timestamp" in df_minute_raw.columns and not isinstance(df_minute_raw.index, pd.DatetimeIndex):
                    df_minute_raw["timestamp"] = pd.to_datetime(df_minute_raw["timestamp"])
                    df_minute_raw = df_minute_raw.set_index("timestamp")
                
                # Normalize column names to lowercase for technical analysis functions
                df_minute_raw.columns = [col.lower() for col in df_minute_raw.columns]
                
                # Initialize aggregated DataFrames
                aggregated_dfs = {
                    "1min": df_minute_raw.copy()
                }
                    
                # Add detailed logging for aggregation
                app_logger.info(f"UpdateDataTabs (TechInd): Starting data aggregation for {selected_symbol}.")
                
                # Perform aggregation with detailed logging
                for period, rule in [("15min", "15T"), ("Hourly", "H"), ("Daily", "D")]:
                    try:
                        app_logger.info(f"UpdateDataTabs (TechInd): Aggregating {period} data for {selected_symbol}...")
                        agg_df = aggregate_candles(df_minute_raw, rule)
                        if agg_df.empty:
                            app_logger.warning(f"UpdateDataTabs (TechInd): Aggregation for {period} returned empty DataFrame for {selected_symbol}.")
                        else:
                            app_logger.info(f"UpdateDataTabs (TechInd): Successfully aggregated {len(agg_df)} rows for {period} for {selected_symbol}.")
                        aggregated_dfs[period] = agg_df
                    except Exception as agg_e:
                        app_logger.error(f"UpdateDataTabs (TechInd): Error aggregating {period} data for {selected_symbol}: {str(agg_e)}", exc_info=True)
                        # Keep empty DataFrame for this period
                
                app_logger.info(f"UpdateDataTabs (TechInd): Completed data aggregation for {selected_symbol}.")
                # Initialize ta_results with empty DataFrames
                ta_results = {
                    "1min": pd.DataFrame(),
                    "15min": pd.DataFrame(),
                    "Hourly": pd.DataFrame(),
                    "Daily": pd.DataFrame()
                }
                
                # Calculate technical indicators with detailed logging
                app_logger.info(f"UpdateDataTabs (TechInd): Starting technical indicator calculations for {selected_symbol}.")
                
                for period, df_agg in aggregated_dfs.items():
                    try:
                        if not df_agg.empty:
                            app_logger.info(f"UpdateDataTabs (TechInd): Calculating indicators for {period} for {selected_symbol}...")
                            result_df = calculate_all_technical_indicators(df_agg.copy(), symbol=f"{selected_symbol}_{period}")
                            
                            # Log the result type and shape
                            if isinstance(result_df, pd.DataFrame):
                                app_logger.info(f"UpdateDataTabs (TechInd): {period} calculation returned DataFrame with shape {result_df.shape} for {selected_symbol}.")
                                ta_results[period] = result_df
                            else:
                                app_logger.error(f"UpdateDataTabs (TechInd): {period} calculation returned {type(result_df)} instead of DataFrame for {selected_symbol}.")
                                ta_results[period] = pd.DataFrame()  # Ensure we always have a DataFrame
                        else:
                            app_logger.info(f"UpdateDataTabs (TechInd): Skipping {period} calculations due to empty aggregated data for {selected_symbol}.")
                    except Exception as calc_e:
                        app_logger.error(f"UpdateDataTabs (TechInd): Error calculating indicators for {period} for {selected_symbol}: {str(calc_e)}", exc_info=True)
                        # Keep empty DataFrame for this period
                
                app_logger.info(f"UpdateDataTabs (TechInd): Completed technical indicator calculations for {selected_symbol}.")
                
                # Collect all indicator names from all periods
                app_logger.info(f"UpdateDataTabs (TechInd): Collecting indicator names for {selected_symbol}...")
                indicator_data = []
                all_indicator_names = set()
                
                # Safely collect column names from each DataFrame
                for period, df in ta_results.items():
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        all_indicator_names.update(df.columns)
                        app_logger.info(f"UpdateDataTabs (TechInd): Found {len(df.columns)} indicators for {period} for {selected_symbol}.")
                    else:
                        app_logger.info(f"UpdateDataTabs (TechInd): No indicators found for {period} for {selected_symbol}.")
                
                app_logger.info(f"UpdateDataTabs (TechInd): Total unique indicators found: {len(all_indicator_names)} for {selected_symbol}.")
                
                # Format data for display
                for indicator_name in sorted(list(all_indicator_names)):
                    row = {"Indicator": indicator_name}
                    for period_key in ["1min", "15min", "Hourly", "Daily"]:
                        df_period = ta_results.get(period_key, pd.DataFrame())
                        if isinstance(df_period, pd.DataFrame) and not df_period.empty and indicator_name in df_period.columns:
                            try:
                                # Get the most recent value for this indicator
                                value = df_period[indicator_name].iloc[0]  # Assuming sorted with most recent first
                                if isinstance(value, float):
                                    row[period_key] = f"{value:.2f}" if not np.isnan(value) else "N/A"
                                elif value is not None:
                                    row[period_key] = str(value)
                                else:
                                    row[period_key] = "N/A"
                            except Exception as val_e:
                                app_logger.error(f"UpdateDataTabs (TechInd): Error extracting {indicator_name} value for {period_key} for {selected_symbol}: {str(val_e)}")
                                row[period_key] = "Error"
                        else:
                            row[period_key] = "N/A"
                    indicator_data.append(row)
                
                tech_cols = default_tech_cols
                tech_data = indicator_data
                tech_data_store = indicator_data
                app_logger.info(f"UpdateDataTabs (TechInd): Formatted TA data for {selected_symbol} table. Rows: {len(tech_data)}")

            except Exception as e:
                error_msg = f"TA calculation/aggregation error: {str(e)}"
                app_logger.exception(f"UpdateDataTabs (TechInd-Calc) for {selected_symbol}: {error_msg}")
                error_event_to_send = {"source": f"TechInd-Calc-{selected_symbol}", "message": error_msg, "timestamp": timestamp_str}
                tech_cols, tech_data = default_tech_cols, []
                tech_data_store = None
    
    return minute_cols, minute_data, tech_cols, tech_data, minute_data_store, tech_data_store, error_event_to_send


# --- Options Chain Callbacks ---
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
        global SCHWAB_CLIENT
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
        
        # Format tables
        calls_columns = [{"name": col, "id": col} for col in calls_df.columns] if not calls_df.empty else []
        puts_columns = [{"name": col, "id": col} for col in puts_df.columns] if not puts_df.empty else []
        
        calls_data = calls_df.to_dict("records") if not calls_df.empty else []
        puts_data = puts_df.to_dict("records") if not puts_df.empty else []
        
        status_msg = f"Options chain for {selected_symbol} loaded. Calls: {len(calls_data)}, Puts: {len(puts_data)}"
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
    State("minute-data-store", "data"),
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
    State("selected-symbol-store", "data"),
    prevent_initial_call=True
)
def export_tech_indicators_to_csv(n_clicks, tech_data, selected_symbol):
    if n_clicks == 0 or not tech_data:
        return dash.no_update
    
    try:
        app_logger.info(f"Exporting technical indicators data to CSV for {selected_symbol}...")
        df = pd.DataFrame(tech_data)
        
        # Generate filename with symbol and current timestamp
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{selected_symbol}_technical_indicators_{timestamp_str}.csv"
        
        # Return the CSV data for download
        return dcc.send_data_frame(df.to_csv, filename, index=False)
    
    except Exception as e:
        app_logger.error(f"Error exporting technical indicators data to CSV: {str(e)}", exc_info=True)
        return dash.no_update


# --- Main Execution ---
if __name__ == "__main__":
    app_logger.info("Starting Dash app server...")
    # Make sure to use the correct host and port, especially for Docker
    app.run(debug=True, host="0.0.0.0", port=8050)

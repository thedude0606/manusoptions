"""
Updates the dashboard_app_streaming.py file to add enhanced debugging for streaming updates.
"""

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import datetime
import logging
import schwabdev
import json
import os
import sys
import traceback
from config import APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_FILE_PATH
from dashboard_utils.data_fetchers import get_minute_data, get_technical_indicators, get_options_chain_data, get_option_contract_keys
from dashboard_utils.options_chain_utils import split_options_by_type
from dashboard_utils.recommendation_tab import register_recommendation_callbacks, create_recommendation_tab
from dashboard_utils.streaming_manager import StreamingManager
from dashboard_utils.streaming_field_mapper import StreamingFieldMapper
from dashboard_utils.streaming_debug import create_debug_monitor  # Import the new debug monitor
from dashboard_utils.contract_utils import normalize_contract_key
from dashboard_utils.download_component import create_download_component, register_download_callback, register_download_click_callback
from dashboard_utils.export_buttons import create_export_button, register_export_callbacks
from dashboard_utils.excel_export import (
    export_minute_data_to_excel,
    export_technical_indicators_to_excel,
    export_options_chain_to_excel,
    export_recommendations_to_excel
)

# Add immediate console print for debugging
print(f"DASHBOARD_APP: Starting initialization at {datetime.datetime.now()}", file=sys.stderr)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger('dashboard_app')
app_logger.setLevel(logging.DEBUG)  # Set to DEBUG for more verbose logging

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

# Add file handler for app logs
app_log_file = os.path.join(log_dir, f"dashboard_app_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler = logging.FileHandler(app_log_file)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
app_logger.addHandler(file_handler)

app_logger.info(f"Dashboard app logger initialized. Logging to: {app_log_file}")
print(f"DASHBOARD_APP: Logger initialized, logging to: {app_log_file}", file=sys.stderr)

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Manus Options Dashboard"

# Initialize Schwab client getter function
def get_schwab_client():
    print(f"DASHBOARD_APP: get_schwab_client called at {datetime.datetime.now()}", file=sys.stderr)
    try:
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKEN_FILE_PATH, capture_callback=False)
        print(f"DASHBOARD_APP: Successfully created Schwab client", file=sys.stderr)
        return client
    except Exception as e:
        app_logger.error(f"Error initializing Schwab client: {e}", exc_info=True)
        print(f"DASHBOARD_APP: Error initializing Schwab client: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

# Initialize account ID getter function
def get_account_id():
    print(f"DASHBOARD_APP: get_account_id called at {datetime.datetime.now()}", file=sys.stderr)
    try:
        client = get_schwab_client()
        if not client:
            print(f"DASHBOARD_APP: Failed to get Schwab client in get_account_id", file=sys.stderr)
            return None
        
        response = client.accounts()
        if not response.ok:
            app_logger.error(f"Error fetching accounts: {response.status_code} - {response.text}")
            print(f"DASHBOARD_APP: Error fetching accounts: {response.status_code} - {response.text}", file=sys.stderr)
            return None
        
        accounts = response.json()
        if not accounts:
            app_logger.error("No accounts found")
            print(f"DASHBOARD_APP: No accounts found", file=sys.stderr)
            return None
        
        # Use the first account ID
        account_id = accounts[0].get("accountId")
        print(f"DASHBOARD_APP: Successfully got account ID: {account_id[:4]}...", file=sys.stderr)
        return account_id
    except Exception as e:
        app_logger.error(f"Error getting account ID: {e}", exc_info=True)
        print(f"DASHBOARD_APP: Error getting account ID: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

# Initialize StreamingManager
print(f"DASHBOARD_APP: Creating StreamingManager at {datetime.datetime.now()}", file=sys.stderr)
streaming_manager = StreamingManager(get_schwab_client, get_account_id)
print(f"DASHBOARD_APP: StreamingManager created", file=sys.stderr)

# Initialize the debug monitor
print(f"DASHBOARD_APP: Creating debug monitor at {datetime.datetime.now()}", file=sys.stderr)
debug_monitor = create_debug_monitor(streaming_manager)
app_logger.info("Streaming debug monitor initialized and started")
print(f"DASHBOARD_APP: Debug monitor created and started", file=sys.stderr)

# Define app layout
app.layout = html.Div([
    # Header
    html.H1("Manus Options Dashboard", style={'textAlign': 'center'}),
    
    # Symbol input and refresh button
    html.Div([
        html.Label("Symbol:"),
        dcc.Input(id="symbol-input", type="text", value="AAPL", style={'marginRight': '10px'}),
        html.Button("Refresh Data", id="refresh-button", n_clicks=0)
    ], style={'margin': '10px 0px'}),
    
    # Status message
    html.Div(id="status-message", style={'margin': '10px 0px', 'color': 'blue'}),
    
    # Error messages
    html.Div(id="error-messages", style={'margin': '10px 0px', 'color': 'red'}),
    
    # Tabs for different data views
    dcc.Tabs(id="tabs", value="tab-minute-data", children=[
        # Minute Data Tab
        dcc.Tab(label="Minute Data", value="tab-minute-data", children=[
            html.Div([
                # Export button for Minute Data
                create_export_button("minute-data", "Export Minute Data to Excel"),
                
                # Minute data table
                dash_table.DataTable(
                    id="minute-data-table",
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '5px'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    }
                ),
                
                # Download component for Minute Data
                create_download_component("minute-data-download")
            ])
        ]),
        
        # Technical Indicators Tab
        dcc.Tab(label="Technical Indicators", value="tab-tech-indicators", children=[
            html.Div([
                # Export button for Technical Indicators
                create_export_button("tech-indicators", "Export Technical Indicators to Excel"),
                
                # Technical indicators table
                dash_table.DataTable(
                    id="tech-indicators-table",
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '5px'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    }
                ),
                
                # Download component for Technical Indicators
                create_download_component("tech-indicators-download")
            ])
        ]),
        
        # Options Chain Tab
        dcc.Tab(label="Options Chain", value="tab-options-chain", children=[
            html.Div([
                # Options chain controls
                html.Div([
                    # Expiration date selector
                    html.Div([
                        html.Label("Expiration Date:"),
                        dcc.Dropdown(id="expiration-date-dropdown")
                    ], style={'width': '200px', 'display': 'inline-block', 'margin-right': '20px'}),
                    
                    # Option type selector
                    html.Div([
                        html.Label("Option Type:"),
                        dcc.RadioItems(
                            id="option-type-radio",
                            options=[
                                {'label': 'All', 'value': 'ALL'},
                                {'label': 'Calls', 'value': 'CALL'},
                                {'label': 'Puts', 'value': 'PUT'}
                            ],
                            value='ALL',
                            inline=True
                        )
                    ], style={'display': 'inline-block', 'margin-right': '20px'}),
                    
                    # Streaming toggle
                    html.Div([
                        html.Label("Real-time Updates:"),
                        dcc.RadioItems(
                            id="streaming-toggle",
                            options=[
                                {'label': 'On', 'value': 'ON'},
                                {'label': 'Off', 'value': 'OFF'}
                            ],
                            value='ON',
                            inline=True
                        )
                    ], style={'display': 'inline-block'})
                ], style={'margin': '10px 0px'}),
                
                # Streaming status
                html.Div(id="streaming-status", style={'margin': '10px 0px', 'fontStyle': 'italic'}),
                
                # Export button for Options Chain
                create_export_button("options-chain", "Export Options Chain to Excel"),
                
                # Options tables
                html.Div([
                    # Calls table
                    html.Div([
                        html.H3("Calls"),
                        dash_table.DataTable(
                            id="calls-table",
                            page_size=10,
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '5px'
                            },
                            style_header={
                                'backgroundColor': 'rgb(230, 230, 230)',
                                'fontWeight': 'bold'
                            }
                        )
                    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                    
                    # Puts table
                    html.Div([
                        html.H3("Puts"),
                        dash_table.DataTable(
                            id="puts-table",
                            page_size=10,
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '5px'
                            },
                            style_header={
                                'backgroundColor': 'rgb(230, 230, 230)',
                                'fontWeight': 'bold'
                            }
                        )
                    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginLeft': '4%'})
                ]),
                
                # Download component for Options Chain
                create_download_component("options-chain-download")
            ])
        ]),
        
        # Recommendations Tab
        dcc.Tab(label="Recommendations", value="tab-recommendations", children=[
            html.Div([
                # Generate Recommendations button
                html.Div([
                    html.Button("Generate Recommendations", id="generate-recommendations-button", n_clicks=0, 
                               style={'backgroundColor': '#4CAF50', 'color': 'white', 'padding': '10px 15px', 
                                      'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer'})
                ], style={'margin': '10px 0px'}),
                
                # Use the full recommendation tab layout from the utility module
                # This includes the recommendation-timeframe-dropdown that was missing
                create_recommendation_tab(),
                
                # Export button for Recommendations
                create_export_button("recommendations", "Export Recommendations to Excel"),
                
                # Download component for Recommendations
                create_download_component("recommendations-download")
            ])
        ])
    ]),
    
    # Hidden data stores
    dcc.Store(id="minute-data-store"),
    dcc.Store(id="tech-indicators-store"),
    dcc.Store(id="options-chain-store"),
    dcc.Store(id="selected-symbol-store"),
    dcc.Store(id="error-store"),
    dcc.Store(id="streaming-options-store"),
    dcc.Store(id="last-valid-options-store"),  # New store to preserve last valid options data
    dcc.Store(id="recommendations-store"),  # Added explicit recommendations store
    dcc.Interval(id="update-interval", interval=60000, n_intervals=0),
    dcc.Interval(id="streaming-update-interval", interval=1000, n_intervals=0, disabled=False),
    
    # Debug information display - only shown in Options Chain tab
    html.Div([
        html.H3("Streaming Debug Information", style={'marginTop': '20px'}),
        html.Div(id="streaming-debug-info", style={'whiteSpace': 'pre-wrap', 'fontFamily': 'monospace', 'fontSize': '12px'})
    ], id="streaming-debug-container", style={'marginTop': '30px', 'padding': '10px', 'border': '1px solid #ddd', 'display': 'none'})
])

# Refresh data callback
@app.callback(
    [
        Output("minute-data-store", "data"),
        Output("tech-indicators-store", "data"),
        Output("options-chain-store", "data"),
        Output("selected-symbol-store", "data"),
        Output("expiration-date-dropdown", "options"),
        Output("expiration-date-dropdown", "value"),
        Output("status-message", "children"),
        Output("error-store", "data", allow_duplicate=True),
        Output("last-valid-options-store", "data")  # Add output for last valid options store
    ],
    [
        Input("refresh-button", "n_clicks")
    ],
    [
        State("symbol-input", "value")
    ],
    prevent_initial_call=True
)
def refresh_data(n_clicks, symbol):
    """Refreshes all data for the given symbol."""
    print(f"DASHBOARD_APP: refresh_data callback triggered with n_clicks={n_clicks}, symbol={symbol}", file=sys.stderr)
    if not n_clicks or not symbol:
        return None, None, None, None, [], None, "", None, None
    
    symbol = symbol.upper()
    app_logger.info(f"Refreshing data for {symbol}")
    
    try:
        # Initialize Schwab client with consistent token file path
        print(f"DASHBOARD_APP: Creating Schwab client in refresh_data", file=sys.stderr)
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKEN_FILE_PATH, capture_callback=False)
        print(f"DASHBOARD_APP: Schwab client created successfully", file=sys.stderr)
        
        # Fetch minute data
        print(f"DASHBOARD_APP: Fetching minute data for {symbol}", file=sys.stderr)
        minute_data, error = get_minute_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching minute data: {error}")
            print(f"DASHBOARD_APP: Error fetching minute data: {error}", file=sys.stderr)
            return None, None, None, None, [], None, f"Error: {error}", {
                "source": "Minute Data",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, None
        
        # Calculate technical indicators
        print(f"DASHBOARD_APP: Calculating technical indicators for {symbol}", file=sys.stderr)
        tech_indicators, error = get_technical_indicators(client, symbol)
        
        if error:
            app_logger.error(f"Error calculating technical indicators: {error}")
            print(f"DASHBOARD_APP: Error calculating technical indicators: {error}", file=sys.stderr)
            return {"data": minute_data}, None, None, None, [], None, f"Error: {error}", {
                "source": "Technical Indicators",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, None
        
        # Fetch options chain
        print(f"DASHBOARD_APP: Fetching options chain for {symbol}", file=sys.stderr)
        options_df, expiration_dates, underlying_price, error = get_options_chain_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching options chain: {error}")
            print(f"DASHBOARD_APP: Error fetching options chain: {error}", file=sys.stderr)
            return {"data": minute_data}, {"data": tech_indicators}, None, None, [], None, f"Error: {error}", {
                "source": "Options Chain",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, None
        
        # Prepare dropdown options
        dropdown_options = [{"label": date, "value": date} for date in expiration_dates]
        default_expiration = expiration_dates[0] if expiration_dates else None
        
        # Prepare data for the stores
        minute_data_store = {
            "data": minute_data,
            "symbol": symbol,
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Prepare technical indicators store with timeframe data structure
        timeframe_data = {}
        if tech_indicators:
            # Group indicators by timeframe
            df = pd.DataFrame(tech_indicators)
            if 'timeframe' in df.columns:
                for timeframe in df['timeframe'].unique():
                    timeframe_data[timeframe] = df[df['timeframe'] == timeframe].to_dict('records')
            
        tech_indicators_store = {
            "data": tech_indicators,
            "timeframe_data": timeframe_data,
            "symbol": symbol,
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        options_data = {
            "symbol": symbol,
            "options": options_df.to_dict("records"),
            "expiration_dates": expiration_dates,
            "underlyingPrice": underlying_price,
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Create a copy for the last valid options store
        last_valid_options = options_data.copy()
        
        print(f"DASHBOARD_APP: Data refresh complete for {symbol}", file=sys.stderr)
        return minute_data_store, tech_indicators_store, options_data, symbol, dropdown_options, default_expiration, f"Data refreshed for {symbol}", None, last_valid_options
    
    except Exception as e:
        error_msg = f"Error refreshing data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        print(f"DASHBOARD_APP: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None, None, None, None, [], None, error_msg, {
            "source": "Data Refresh",
            "message": str(e),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, None

# Minute Data Table Callback
@app.callback(
    Output("minute-data-table", "data"),
    Output("minute-data-table", "columns"),
    Input("minute-data-store", "data"),
    prevent_initial_call=True
)
def update_minute_data_table(minute_data_store):
    """Updates the minute data table with the fetched data."""
    app_logger.info("Update minute data table callback triggered")
    
    if not minute_data_store or not minute_data_store.get("data"):
        app_logger.warning("No minute data available")
        return [], []
    
    try:
        # Get the minute data
        minute_data = minute_data_store["data"]
        
        # Create DataFrame columns
        columns = [{"name": col, "id": col} for col in minute_data[0].keys()]
        
        return minute_data, columns
    
    except Exception as e:
        app_logger.error(f"Error updating minute data table: {e}", exc_info=True)
        return [], []

# Technical Indicators Table Callback
@app.callback(
    Output("tech-indicators-table", "data"),
    Output("tech-indicators-table", "columns"),
    Input("tech-indicators-store", "data"),
    prevent_initial_call=True
)
def update_tech_indicators_table(tech_indicators_store):
    """Updates the technical indicators table with the fetched data."""
    app_logger.info("Update technical indicators table callback triggered")
    
    if not tech_indicators_store or not tech_indicators_store.get("data"):
        app_logger.warning("No technical indicators data available")
        return [], []
    
    try:
        # Get the technical indicators data
        tech_indicators = tech_indicators_store["data"]
        
        # Create DataFrame columns
        columns = [{"name": col, "id": col} for col in tech_indicators[0].keys()]
        
        return tech_indicators, columns
    
    except Exception as e:
        app_logger.error(f"Error updating technical indicators table: {e}", exc_info=True)
        return [], []

# Streaming Toggle Callback
@app.callback(
    Output("streaming-status", "children"),
    Output("streaming-update-interval", "disabled"),
    [
        Input("streaming-toggle", "value"),
        Input("options-chain-store", "data")
    ],
    prevent_initial_call=True
)
def toggle_streaming(toggle_value, options_data):
    """Toggles streaming based on the toggle value."""
    print(f"DASHBOARD_APP: toggle_streaming callback triggered with toggle_value={toggle_value}", file=sys.stderr)
    app_logger.info(f"Streaming toggle set to: {toggle_value}")
    
    if not options_data or not options_data.get("options"):
        print(f"DASHBOARD_APP: No options data available for streaming", file=sys.stderr)
        return "Streaming: No options data available", True
    
    try:
        if toggle_value == "ON":
            # Get option contract keys
            print(f"DASHBOARD_APP: Converting options data to DataFrame for streaming", file=sys.stderr)
            options_df = pd.DataFrame(options_data["options"])
            print(f"DASHBOARD_APP: Getting option contract keys for streaming", file=sys.stderr)
            option_keys = get_option_contract_keys(options_df)
            app_logger.info(f"Starting streaming for {len(option_keys)} option contracts")
            print(f"DASHBOARD_APP: Starting streaming for {len(option_keys)} option contracts", file=sys.stderr)
            
            # Start streaming
            print(f"DASHBOARD_APP: Calling streaming_manager.start_stream", file=sys.stderr)
            success = streaming_manager.start_stream(option_keys)
            print(f"DASHBOARD_APP: streaming_manager.start_stream returned {success}", file=sys.stderr)
            
            # Make sure debug monitor is running
            print(f"DASHBOARD_APP: Ensuring debug monitor is running", file=sys.stderr)
            if not debug_monitor.is_monitoring:
                print(f"DASHBOARD_APP: Debug monitor was not running, starting it", file=sys.stderr)
                debug_monitor.start_monitoring()
            
            if success:
                print(f"DASHBOARD_APP: Streaming started successfully", file=sys.stderr)
                return "Streaming: Active", False
            else:
                print(f"DASHBOARD_APP: Failed to start streaming", file=sys.stderr)
                return "Streaming: Failed to start", True
        else:
            # Stop streaming
            app_logger.info("Stopping streaming")
            print(f"DASHBOARD_APP: Stopping streaming", file=sys.stderr)
            streaming_manager.stop_stream()
            return "Streaming: Inactive", True
    
    except Exception as e:
        error_msg = f"Error toggling streaming: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        print(f"DASHBOARD_APP: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"Streaming: Error - {str(e)}", True

# Add callback to show/hide debug container based on active tab
@app.callback(
    Output("streaming-debug-container", "style"),
    [Input("tabs", "value")],
    prevent_initial_call=False
)
def toggle_debug_container(active_tab):
    """Shows or hides the streaming debug container based on the active tab."""
    if active_tab == "tab-options-chain":
        return {'marginTop': '30px', 'padding': '10px', 'border': '1px solid #ddd', 'display': 'block'}
    else:
        return {'display': 'none'}

# Streaming Debug Info Callback
@app.callback(
    Output("streaming-debug-info", "children"),
    [Input("streaming-update-interval", "n_intervals")],
    prevent_initial_call=True
)
def update_streaming_debug_info(n_intervals):
    """Updates the streaming debug information."""
    print(f"DASHBOARD_APP: update_streaming_debug_info callback triggered with n_intervals={n_intervals}", file=sys.stderr)
    try:
        # Get debug info from the monitor
        print(f"DASHBOARD_APP: Getting debug info from monitor", file=sys.stderr)
        debug_info = debug_monitor.log_debug_info()
        
        # Format the debug info for display
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        debug_text = [
            f"Streaming Update Triggered: {current_time}",
            f"Interval Count: {n_intervals}",
        ]
        
        # Add streaming status
        streaming_status = debug_info.get("streaming_status", "Unknown")
        debug_text.append(f"Streaming Status: {streaming_status}")
        
        # Add data count
        data_count = debug_info.get("current_data_count", 0)
        debug_text.append(f"Contracts with Data: {data_count}")
        
        # Add last update time
        last_update_time = debug_info.get("last_data_update_time", "None")
        if last_update_time != "None" and last_update_time is not None:
            # Convert ISO format to readable format
            try:
                dt = datetime.datetime.fromisoformat(last_update_time)
                last_update_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        debug_text.append(f"Last Data Update: {last_update_time}")
        
        # Add time since last update
        seconds_since_update = debug_info.get("seconds_since_last_update")
        if seconds_since_update is not None:
            debug_text.append(f"Seconds Since Last Update: {seconds_since_update:.1f}")
        
        # Add update count
        update_count = debug_info.get("data_update_count", 0)
        debug_text.append(f"Total Updates Received: {update_count}")
        
        # Add error messages
        error_messages = debug_info.get("error_messages", [])
        if error_messages:
            debug_text.append("\nError Messages:")
            for error in error_messages[-3:]:  # Show only the last 3 errors
                debug_text.append(f"- {error}")
        
        # Add data samples
        data_samples = debug_info.get("data_samples", [])
        if data_samples:
            debug_text.append("\nRecent Data Samples:")
            for i, sample in enumerate(data_samples[-2:]):  # Show only the last 2 samples
                debug_text.append(f"\nSample {i+1}:")
                for key, data in sample.items():
                    debug_text.append(f"  {key}: Bid={data.get('bidPrice')}, Ask={data.get('askPrice')}, Last={data.get('lastPrice')}")
        
        # If no data is available, show a clear message
        if data_count == 0 and update_count == 0:
            debug_text.append("\nNo streaming data available")
        
        # Check streaming manager status directly
        try:
            is_running = streaming_manager.is_running
            debug_text.append(f"\nStreaming Manager Status:")
            debug_text.append(f"- is_running: {is_running}")
            debug_text.append(f"- status_message: {streaming_manager.status_message}")
            if streaming_manager.error_message:
                debug_text.append(f"- error_message: {streaming_manager.error_message}")
            debug_text.append(f"- subscriptions_count: {len(streaming_manager.current_subscriptions)}")
            debug_text.append(f"- data_count: {len(streaming_manager.latest_data_store)}")
        except Exception as e:
            debug_text.append(f"\nError getting streaming manager status: {str(e)}")
        
        print(f"DASHBOARD_APP: Debug info prepared, returning to UI", file=sys.stderr)
        return "\n".join(debug_text)
    
    except Exception as e:
        app_logger.error(f"Error updating streaming debug info: {e}", exc_info=True)
        print(f"DASHBOARD_APP: Error updating streaming debug info: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"Error updating streaming debug info: {str(e)}"

# Options Tables Callback
@app.callback(
    [
        Output("calls-table", "data"),
        Output("calls-table", "columns"),
        Output("puts-table", "data"),
        Output("puts-table", "columns")
    ],
    [
        Input("expiration-date-dropdown", "value"),
        Input("option-type-radio", "value"),
        Input("streaming-update-interval", "n_intervals")
    ],
    [
        State("options-chain-store", "data"),
        State("streaming-options-store", "data"),
        State("last-valid-options-store", "data")
    ],
    prevent_initial_call=True
)
def update_options_tables(expiration_date, option_type, n_intervals, options_data, streaming_data, last_valid_options):
    """Updates the options tables with the fetched data and streaming updates."""
    print(f"DASHBOARD_APP: update_options_tables callback triggered with n_intervals={n_intervals}", file=sys.stderr)
    app_logger.info(f"Update options tables callback triggered. Expiration: {expiration_date}, Type: {option_type}, Interval: {n_intervals}")
    
    if not options_data or not options_data.get("options"):
        if last_valid_options and last_valid_options.get("options"):
            app_logger.info("Using last valid options data")
            print(f"DASHBOARD_APP: Using last valid options data", file=sys.stderr)
            options_data = last_valid_options
        else:
            app_logger.warning("No options data available")
            print(f"DASHBOARD_APP: No options data available", file=sys.stderr)
            return [], [], [], []
    
    try:
        # Convert options data to DataFrame
        print(f"DASHBOARD_APP: Converting options data to DataFrame", file=sys.stderr)
        options_df = pd.DataFrame(options_data["options"])
        
        # Enhanced debugging: Log the first few rows of the DataFrame to see what columns and data we have
        app_logger.debug(f"Options DataFrame first 3 rows: {options_df.head(3).to_dict('records')}")
        app_logger.debug(f"Options DataFrame columns: {list(options_df.columns)}")
        
        # Enhanced debugging: Log the symbol column format for the first few rows
        if 'symbol' in options_df.columns:
            app_logger.debug(f"Symbol column sample: {options_df['symbol'].head(5).tolist()}")
            print(f"DASHBOARD_APP: Symbol column sample: {options_df['symbol'].head(5).tolist()}", file=sys.stderr)
        
        # Apply streaming updates if available
        if streaming_data and streaming_data.get("streaming_data"):
            streaming_updates = streaming_data["streaming_data"]
            app_logger.info(f"Applying streaming updates for {len(streaming_updates)} contracts")
            print(f"DASHBOARD_APP: Applying streaming updates for {len(streaming_updates)} contracts", file=sys.stderr)
            
            # Enhanced debugging: Log a sample of the streaming update keys
            sample_update_keys = list(streaming_updates.keys())[:5]
            app_logger.debug(f"Streaming update keys sample: {sample_update_keys}")
            print(f"DASHBOARD_APP: Streaming update keys sample: {sample_update_keys}", file=sys.stderr)
            
            field_mapper = StreamingFieldMapper()
            update_count = 0
            match_count = 0
            
            # Create a dictionary to store all the different formats of each contract key for debugging
            key_formats = {}
            
            # Update each contract with streaming data
            for contract_key, update_data in streaming_updates.items():
                # Store original key for debugging
                original_key = contract_key
                
                # Normalize the contract key to match the format in the options DataFrame
                normalized_key = normalize_contract_key(contract_key)
                
                # Store all formats for debugging
                key_formats[original_key] = {
                    'original': original_key,
                    'normalized': normalized_key,
                    'no_underscore': normalized_key.replace("_", "") if normalized_key else None
                }
                
                app_logger.debug(f"Processing streaming update for contract: {normalized_key} (original: {original_key})")
                
                # Find the corresponding row in the DataFrame
                mask = options_df["symbol"] == normalized_key
                
                # If no match found with normalized key, try alternative formats
                if not mask.any():
                    # Try without underscore
                    alt_key = normalized_key.replace("_", "") if normalized_key else ""
                    mask = options_df["symbol"] == alt_key
                    if mask.any():
                        app_logger.debug(f"Found match using alternative key format: {alt_key}")
                        key_formats[original_key]['matched_format'] = 'no_underscore'
                    else:
                        # Try direct match with original key
                        mask = options_df["symbol"] == contract_key
                        if mask.any():
                            app_logger.debug(f"Found match using original key: {contract_key}")
                            key_formats[original_key]['matched_format'] = 'original'
                        else:
                            # Enhanced debugging: Try to find what's in the DataFrame that might match
                            if 'symbol' in options_df.columns:
                                # Get the first part of the symbol (e.g., "AAPL" from "AAPL_250530C180")
                                if normalized_key and '_' in normalized_key:
                                    symbol_prefix = normalized_key.split('_')[0]
                                    similar_symbols = options_df[options_df['symbol'].str.contains(symbol_prefix, na=False)]
                                    if not similar_symbols.empty:
                                        app_logger.debug(f"Similar symbols in DataFrame for {symbol_prefix}: {similar_symbols['symbol'].head(3).tolist()}")
                                        key_formats[original_key]['similar_in_df'] = similar_symbols['symbol'].head(3).tolist()
                            
                            app_logger.warning(f"No matching row found for {normalized_key} (original: {contract_key})")
                            continue
                
                if mask.any():
                    match_count += 1
                    app_logger.debug(f"Found matching row for {normalized_key}")
                    
                    # Get the mapped fields from the streaming data
                    mapped_fields = field_mapper.map_streaming_fields(update_data)
                    app_logger.debug(f"Mapped fields for {normalized_key}: {mapped_fields}")
                    
                    # Update the DataFrame with the streaming data
                    for field, value in mapped_fields.items():
                        if field in options_df.columns:
                            # Use .loc to avoid SettingWithCopyWarning
                            options_df.loc[mask, field] = value
                            app_logger.debug(f"Updated {normalized_key}.{field} = {value}")
                            update_count += 1
            
            # Enhanced debugging: Log match statistics and key format information
            app_logger.info(f"Streaming update statistics: {match_count}/{len(streaming_updates)} contracts matched, {update_count} field updates applied")
            print(f"DASHBOARD_APP: Streaming update statistics: {match_count}/{len(streaming_updates)} contracts matched, {update_count} field updates applied", file=sys.stderr)
            app_logger.debug(f"Key format details for first 5 keys: {json.dumps({k: v for i, (k, v) in enumerate(key_formats.items()) if i < 5})}")
            
            # If we have very few matches, log more details about the DataFrame and streaming keys
            if match_count < len(streaming_updates) * 0.1 and len(streaming_updates) > 0:
                app_logger.warning(f"Very low match rate: {match_count}/{len(streaming_updates)} ({match_count/len(streaming_updates)*100:.1f}%)")
                print(f"DASHBOARD_APP: Very low match rate: {match_count}/{len(streaming_updates)} ({match_count/len(streaming_updates)*100:.1f}%)", file=sys.stderr)
                app_logger.debug("DataFrame symbol column sample:")
                if 'symbol' in options_df.columns:
                    for i, symbol in enumerate(options_df['symbol'].head(10)):
                        app_logger.debug(f"  DataFrame symbol {i}: {symbol}")
                
                app_logger.debug("Streaming keys sample:")
                for i, key in enumerate(list(streaming_updates.keys())[:10]):
                    app_logger.debug(f"  Streaming key {i}: {key}")
        else:
            app_logger.debug("No streaming updates available")
            print(f"DASHBOARD_APP: No streaming updates available", file=sys.stderr)
        
        # Log the shape of the DataFrame for debugging
        app_logger.debug(f"Updated options DataFrame shape: {options_df.shape}")
        
        # Use the utility function to split options by type
        print(f"DASHBOARD_APP: Splitting options by type", file=sys.stderr)
        calls_data, puts_data = split_options_by_type(
            options_df, 
            expiration_date=expiration_date,
            option_type=option_type,
            last_valid_options=last_valid_options
        )
        
        app_logger.info(f"Split options: {len(calls_data)} calls and {len(puts_data)} puts")
        print(f"DASHBOARD_APP: Split options: {len(calls_data)} calls and {len(puts_data)} puts", file=sys.stderr)
        
        # Create columns for the tables
        if calls_data:
            calls_columns = [{"name": col, "id": col} for col in calls_data[0].keys()]
        else:
            calls_columns = []
        
        if puts_data:
            puts_columns = [{"name": col, "id": col} for col in puts_data[0].keys()]
        else:
            puts_columns = []
        
        return calls_data, calls_columns, puts_data, puts_columns
    
    except Exception as e:
        error_msg = f"Error in update_options_tables: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        print(f"DASHBOARD_APP: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return [], [], [], []

# Streaming Update Callback
@app.callback(
    Output("streaming-options-store", "data"),
    Input("streaming-update-interval", "n_intervals"),
    prevent_initial_call=True
)
def update_streaming_data(n_intervals):
    """Updates the streaming data store with the latest streaming data."""
    print(f"DASHBOARD_APP: update_streaming_data callback triggered with n_intervals={n_intervals}", file=sys.stderr)
    app_logger.debug(f"Streaming update callback triggered. Interval: {n_intervals}")
    
    try:
        # Get the latest streaming data from the streaming manager
        print(f"DASHBOARD_APP: Getting latest data from streaming manager", file=sys.stderr)
        with streaming_manager._lock:
            latest_data = streaming_manager.latest_data_store.copy()
        
        # Create a dictionary for the streaming data store
        streaming_data = {
            "streaming_data": latest_data,
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "update_count": n_intervals
        }
        
        # Log the update
        data_count = len(latest_data)
        app_logger.debug(f"Streaming update: {data_count} contracts available")
        print(f"DASHBOARD_APP: Streaming update: {data_count} contracts available", file=sys.stderr)
        
        # Log a sample of the data for debugging
        if data_count > 0:
            sample_keys = list(latest_data.keys())[:3]
            for key in sample_keys:
                data = latest_data[key]
                app_logger.debug(f"Sample data for {key}: Last={data.get('lastPrice')}, Bid={data.get('bidPrice')}, Ask={data.get('askPrice')}")
                print(f"DASHBOARD_APP: Sample data for {key}: Last={data.get('lastPrice')}, Bid={data.get('bidPrice')}, Ask={data.get('askPrice')}", file=sys.stderr)
        
        return streaming_data
    
    except Exception as e:
        error_msg = f"Error updating streaming data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        print(f"DASHBOARD_APP: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {"streaming_data": {}, "error": error_msg}

# Error Display Callback
@app.callback(
    Output("error-messages", "children"),
    Input("error-store", "data"),
    prevent_initial_call=True
)
def display_error(error_data):
    """Displays error messages from the error store."""
    if not error_data:
        return ""
    
    source = error_data.get("source", "Unknown")
    message = error_data.get("message", "An unknown error occurred")
    timestamp = error_data.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    return f"Error in {source} at {timestamp}: {message}"

# Register recommendation callbacks
register_recommendation_callbacks(app)

# Register download callbacks
register_download_callback(app, "minute-data-download")
register_download_callback(app, "tech-indicators-download")
register_download_callback(app, "options-chain-download")
register_download_callback(app, "recommendations-download")

# Register download click callbacks
register_download_click_callback(app, "minute-data-download")
register_download_click_callback(app, "tech-indicators-download")
register_download_click_callback(app, "options-chain-download")
register_download_click_callback(app, "recommendations-download")

# Register export callbacks
register_export_callbacks(app)

# Clean up streaming on app shutdown
@app.server.teardown_appcontext
def shutdown_streaming(exception=None):
    """Stops streaming when the app shuts down."""
    print(f"DASHBOARD_APP: shutdown_streaming called at {datetime.datetime.now()}", file=sys.stderr)
    try:
        # Check if streaming_manager exists and has stop_streaming method
        if streaming_manager is not None and hasattr(streaming_manager, 'stop_streaming'):
            # Check if streaming is actually running before stopping
            if hasattr(streaming_manager, 'is_running') and streaming_manager.is_running:
                streaming_manager.stop_streaming()
                app_logger.info("Streaming stopped on app shutdown")
                print(f"DASHBOARD_APP: Streaming stopped on app shutdown", file=sys.stderr)
            else:
                app_logger.info("Streaming was not running, no need to stop")
                print(f"DASHBOARD_APP: Streaming was not running, no need to stop", file=sys.stderr)
        else:
            app_logger.warning("streaming_manager not available or missing stop_streaming method")
            print(f"DASHBOARD_APP: streaming_manager not available or missing stop_streaming method", file=sys.stderr)
            
        # Check if debug_monitor exists and has stop_monitoring method
        if debug_monitor is not None and hasattr(debug_monitor, 'stop_monitoring'):
            # Check if monitoring is actually running before stopping
            if hasattr(debug_monitor, 'is_monitoring') and debug_monitor.is_monitoring:
                debug_monitor.stop_monitoring()
                app_logger.info("Debug monitor stopped on app shutdown")
                print(f"DASHBOARD_APP: Debug monitor stopped on app shutdown", file=sys.stderr)
            else:
                app_logger.info("Debug monitor was not running, no need to stop")
                print(f"DASHBOARD_APP: Debug monitor was not running, no need to stop", file=sys.stderr)
        else:
            app_logger.warning("debug_monitor not available or missing stop_monitoring method")
            print(f"DASHBOARD_APP: debug_monitor not available or missing stop_monitoring method", file=sys.stderr)
            
    except Exception as e:
        app_logger.error(f"Error during shutdown_streaming: {e}", exc_info=True)
        print(f"DASHBOARD_APP: Error during shutdown_streaming: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # Don't re-raise the exception to avoid breaking the teardown process

if __name__ == "__main__":
    # Use app.run instead of app.run_server for Dash 3.x compatibility
    print(f"DASHBOARD_APP: Starting app server at {datetime.datetime.now()}", file=sys.stderr)
    app.run(debug=True, host='0.0.0.0', port=8050)

"""
Updates the dashboard_app_streaming.py file to integrate the modular technical indicator system
and confidence scoring components.
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
from dashboard_utils.data_fetchers_updated import get_minute_data, get_technical_indicators, get_options_chain_data, get_option_contract_keys
from dashboard_utils.options_chain_utils import split_options_by_type
from dashboard_utils.recommendation_tab_updated import register_recommendation_callbacks, create_recommendation_tab
from dashboard_utils.streaming_manager import StreamingManager
from dashboard_utils.streaming_field_mapper import StreamingFieldMapper
from dashboard_utils.streaming_debug import create_debug_monitor
from dashboard_utils.contract_utils import normalize_contract_key
from dashboard_utils.download_component import create_download_component, register_download_callback, register_download_click_callback
from dashboard_utils.export_buttons import create_export_button, register_export_callbacks
from dashboard_utils.excel_export import (
    export_minute_data_to_excel,
    export_technical_indicators_to_excel,
    export_options_chain_to_excel,
    export_recommendations_to_excel
)
from dashboard_utils.technical_indicators import get_registered_indicators
from dashboard_utils.confidence_scoring import ConfidenceScorer

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

# Log available indicators from the registry
registered_indicators = get_registered_indicators()
app_logger.info(f"Registered indicators: {list(registered_indicators.keys())}")
print(f"DASHBOARD_APP: Found {len(registered_indicators)} registered indicators", file=sys.stderr)

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
                # Timeframe selector for Technical Indicators
                html.Div([
                    html.Label("Timeframe:"),
                    dcc.Dropdown(
                        id="tech-indicators-timeframe-dropdown",
                        options=[
                            {'label': '1 Minute', 'value': '1min'},
                            {'label': '5 Minutes', 'value': '5min'},
                            {'label': '15 Minutes', 'value': '15min'},
                            {'label': '1 Hour', 'value': '1hour'},
                            {'label': '4 Hours', 'value': '4hour'},
                            {'label': 'Daily', 'value': '1day'}
                        ],
                        value='1hour',
                        clearable=False
                    )
                ], style={'width': '200px', 'margin': '10px 0px'}),
                
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
                
                # Use the updated recommendation tab layout from the utility module
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
    dcc.Store(id="last-valid-options-store"),  # Store to preserve last valid options data
    dcc.Store(id="recommendations-store"),  # Explicit recommendations store
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
            return None, None, None, {"symbol": symbol}, [], None, f"Error: {error}", {"error": error}, None
        
        # Calculate technical indicators
        print(f"DASHBOARD_APP: Calculating technical indicators for {symbol}", file=sys.stderr)
        tech_indicators, error = get_technical_indicators(client, symbol)
        
        if error:
            app_logger.error(f"Error calculating technical indicators: {error}")
            print(f"DASHBOARD_APP: Error calculating technical indicators: {error}", file=sys.stderr)
            return minute_data, None, None, {"symbol": symbol}, [], None, f"Error: {error}", {"error": error}, None
        
        # Fetch options chain
        print(f"DASHBOARD_APP: Fetching options chain for {symbol}", file=sys.stderr)
        options_df, expiration_dates, underlying_price, error = get_options_chain_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching options chain: {error}")
            print(f"DASHBOARD_APP: Error fetching options chain: {error}", file=sys.stderr)
            return minute_data, tech_indicators, None, {"symbol": symbol}, [], None, f"Error: {error}", {"error": error}, None
        
        # Convert options DataFrame to records for JSON serialization
        options_data = {
            "options": options_df.to_dict('records'),
            "underlyingPrice": underlying_price,
            "symbol": symbol
        }
        
        # Create dropdown options for expiration dates
        expiration_options = [{'label': date, 'value': date} for date in expiration_dates]
        
        # Set default expiration date (first one)
        default_expiration = expiration_dates[0] if expiration_dates else None
        
        app_logger.info(f"Successfully refreshed data for {symbol}")
        print(f"DASHBOARD_APP: Successfully refreshed data for {symbol}", file=sys.stderr)
        
        return minute_data, tech_indicators, options_data, {"symbol": symbol}, expiration_options, default_expiration, f"Data refreshed for {symbol}", None, options_data
    
    except Exception as e:
        error_msg = f"Exception in refresh_data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        print(f"DASHBOARD_APP: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None, None, None, {"symbol": symbol}, [], None, f"Error: {str(e)}", {"error": str(e)}, None

# Minute Data Table Callback
@app.callback(
    [
        Output("minute-data-table", "data"),
        Output("minute-data-table", "columns")
    ],
    [Input("minute-data-store", "data")],
    prevent_initial_call=True
)
def update_minute_data_table(minute_data):
    """Updates the minute data table with the fetched data."""
    print(f"DASHBOARD_APP: update_minute_data_table callback triggered", file=sys.stderr)
    
    if not minute_data:
        return [], []
    
    try:
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(minute_data)
        
        # Format timestamp column
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Sort by timestamp (most recent first)
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp', ascending=False)
        
        # Convert back to records for table display
        data = df.to_dict('records')
        
        # Create columns configuration
        columns = [{"name": col, "id": col} for col in df.columns]
        
        app_logger.info(f"Updated minute data table with {len(data)} rows")
        print(f"DASHBOARD_APP: Updated minute data table with {len(data)} rows", file=sys.stderr)
        
        return data, columns
    
    except Exception as e:
        app_logger.error(f"Error updating minute data table: {e}", exc_info=True)
        print(f"DASHBOARD_APP: Error updating minute data table: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return [], []

# Technical Indicators Table Callback
@app.callback(
    [
        Output("tech-indicators-table", "data"),
        Output("tech-indicators-table", "columns")
    ],
    [
        Input("tech-indicators-store", "data"),
        Input("tech-indicators-timeframe-dropdown", "value")
    ],
    prevent_initial_call=True
)
def update_tech_indicators_table(tech_indicators_data, timeframe):
    """Updates the technical indicators table with the fetched data."""
    print(f"DASHBOARD_APP: update_tech_indicators_table callback triggered with timeframe={timeframe}", file=sys.stderr)
    
    if not tech_indicators_data:
        return [], []
    
    try:
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(tech_indicators_data)
        
        # Filter by timeframe if specified
        if timeframe and 'timeframe' in df.columns:
            df = df[df['timeframe'] == timeframe]
        
        # Format timestamp column
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Sort by timestamp (most recent first)
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp', ascending=False)
        
        # Convert back to records for table display
        data = df.to_dict('records')
        
        # Create columns configuration
        columns = [{"name": col, "id": col} for col in df.columns]
        
        app_logger.info(f"Updated technical indicators table with {len(data)} rows for timeframe {timeframe}")
        print(f"DASHBOARD_APP: Updated technical indicators table with {len(data)} rows for timeframe {timeframe}", file=sys.stderr)
        
        return data, columns
    
    except Exception as e:
        app_logger.error(f"Error updating technical indicators table: {e}", exc_info=True)
        print(f"DASHBOARD_APP: Error updating technical indicators table: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return [], []

# Streaming Toggle Callback
@app.callback(
    [
        Output("streaming-status", "children"),
        Output("streaming-update-interval", "disabled")
    ],
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
        
        # Apply streaming updates if available
        if streaming_data and streaming_data.get("streaming_data"):
            streaming_updates = streaming_data["streaming_data"]
            app_logger.info(f"Applying streaming updates for {len(streaming_updates)} contracts")
            print(f"DASHBOARD_APP: Applying streaming updates for {len(streaming_updates)} contracts", file=sys.stderr)
            
            field_mapper = StreamingFieldMapper()
            
            # Update each contract with streaming data
            for contract_key, update_data in streaming_updates.items():
                # Normalize the contract key to match the format in the options DataFrame
                normalized_key = normalize_contract_key(contract_key)
                
                # Find the corresponding row in the DataFrame
                mask = options_df["symbol"] == normalized_key
                
                # If no match found with normalized key, try alternative formats
                if not mask.any():
                    # Try without underscore
                    alt_key = normalized_key.replace("_", "") if normalized_key else ""
                    mask = options_df["symbol"] == alt_key
                    if not mask.any():
                        # Try direct match with original key
                        mask = options_df["symbol"] == contract_key
                
                if mask.any():
                    # Get the mapped fields from the streaming data
                    mapped_fields = field_mapper.map_streaming_fields(update_data)
                    
                    # Update the DataFrame with the streaming data
                    for field, value in mapped_fields.items():
                        if field in options_df.columns:
                            # Use .loc to avoid SettingWithCopyWarning
                            options_df.loc[mask, field] = value
        
        # Filter by expiration date
        if expiration_date:
            options_df = options_df[options_df["expirationDate"] == expiration_date]
        
        # Split options by type
        calls_df, puts_df = split_options_by_type(options_df)
        
        # Apply option type filter
        if option_type == "CALL":
            puts_df = pd.DataFrame()  # Empty DataFrame for puts
        elif option_type == "PUT":
            calls_df = pd.DataFrame()  # Empty DataFrame for calls
        
        # Sort by strike price
        if not calls_df.empty and "strikePrice" in calls_df.columns:
            calls_df = calls_df.sort_values("strikePrice")
        
        if not puts_df.empty and "strikePrice" in puts_df.columns:
            puts_df = puts_df.sort_values("strikePrice")
        
        # Convert to records for table display
        calls_data = calls_df.to_dict('records') if not calls_df.empty else []
        puts_data = puts_df.to_dict('records') if not puts_df.empty else []
        
        # Create columns configuration
        calls_columns = [{"name": col, "id": col} for col in calls_df.columns] if not calls_df.empty else []
        puts_columns = [{"name": col, "id": col} for col in puts_df.columns] if not puts_df.empty else []
        
        app_logger.info(f"Updated options tables with {len(calls_data)} calls and {len(puts_data)} puts")
        print(f"DASHBOARD_APP: Updated options tables with {len(calls_data)} calls and {len(puts_data)} puts", file=sys.stderr)
        
        return calls_data, calls_columns, puts_data, puts_columns
    
    except Exception as e:
        app_logger.error(f"Error updating options tables: {e}", exc_info=True)
        print(f"DASHBOARD_APP: Error updating options tables: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return [], [], [], []

# Streaming Options Store Callback
@app.callback(
    Output("streaming-options-store", "data"),
    [Input("streaming-update-interval", "n_intervals")],
    prevent_initial_call=True
)
def update_streaming_options_store(n_intervals):
    """Updates the streaming options store with the latest data."""
    print(f"DASHBOARD_APP: update_streaming_options_store callback triggered with n_intervals={n_intervals}", file=sys.stderr)
    
    try:
        # Get the latest streaming data
        streaming_data = streaming_manager.get_latest_data()
        
        # Return the streaming data
        return {"streaming_data": streaming_data}
    
    except Exception as e:
        app_logger.error(f"Error updating streaming options store: {e}", exc_info=True)
        print(f"DASHBOARD_APP: Error updating streaming options store: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {"streaming_data": {}}

# Error Display Callback
@app.callback(
    Output("error-messages", "children"),
    [Input("error-store", "data")],
    prevent_initial_call=True
)
def update_error_messages(error_data):
    """Updates the error messages display."""
    if not error_data:
        return ""
    
    try:
        error_msg = error_data.get("error", "Unknown error")
        return f"Error: {error_msg}"
    
    except Exception as e:
        app_logger.error(f"Error updating error messages: {e}", exc_info=True)
        return f"Error: {str(e)}"

# Register recommendation callbacks
register_recommendation_callbacks(app)

# Register export callbacks
register_export_callbacks(app)

# Register download callbacks
register_download_callback(app)
register_download_click_callback(app)

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")

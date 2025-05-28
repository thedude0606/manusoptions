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
from config import APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_FILE_PATH
from dashboard_utils.data_fetchers import get_minute_data, get_technical_indicators, get_options_chain_data, get_option_contract_keys
from dashboard_utils.options_chain_utils import split_options_by_type
from dashboard_utils.recommendation_tab import register_recommendation_callbacks, create_recommendation_tab
from dashboard_utils.streaming_manager import StreamingManager
from dashboard_utils.streaming_field_mapper import StreamingFieldMapper
from dashboard_utils.contract_utils import normalize_contract_key
from dashboard_utils.download_component import create_download_component, register_download_callback, register_download_click_callback
from dashboard_utils.export_buttons import create_export_button, register_export_callbacks
from dashboard_utils.excel_export import (
    export_minute_data_to_excel,
    export_technical_indicators_to_excel,
    export_options_chain_to_excel,
    export_recommendations_to_excel
)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger('dashboard_app')
app_logger.setLevel(logging.DEBUG)  # Set to DEBUG for more verbose logging

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Manus Options Dashboard"

# Initialize Schwab client getter function
def get_schwab_client():
    try:
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKEN_FILE_PATH, capture_callback=False)
        return client
    except Exception as e:
        app_logger.error(f"Error initializing Schwab client: {e}", exc_info=True)
        return None

# Initialize account ID getter function
def get_account_id():
    try:
        client = get_schwab_client()
        if not client:
            return None
        
        response = client.accounts()
        if not response.ok:
            app_logger.error(f"Error fetching accounts: {response.status_code} - {response.text}")
            return None
        
        accounts = response.json()
        if not accounts:
            app_logger.error("No accounts found")
            return None
        
        # Use the first account ID
        account_id = accounts[0].get("accountId")
        return account_id
    except Exception as e:
        app_logger.error(f"Error getting account ID: {e}", exc_info=True)
        return None

# Initialize StreamingManager
streaming_manager = StreamingManager(get_schwab_client, get_account_id)

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
    dcc.Tabs([
        # Minute Data Tab
        dcc.Tab(label="Minute Data", children=[
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
        dcc.Tab(label="Technical Indicators", children=[
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
        dcc.Tab(label="Options Chain", children=[
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
        dcc.Tab(label="Recommendations", children=[
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
    
    # Debug information display
    html.Div([
        html.H3("Streaming Debug Information", style={'marginTop': '20px'}),
        html.Div(id="streaming-debug-info", style={'whiteSpace': 'pre-wrap', 'fontFamily': 'monospace', 'fontSize': '12px'})
    ], style={'marginTop': '30px', 'padding': '10px', 'border': '1px solid #ddd'})
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
    if not n_clicks or not symbol:
        return None, None, None, None, [], None, "", None, None
    
    symbol = symbol.upper()
    app_logger.info(f"Refreshing data for {symbol}")
    
    try:
        # Initialize Schwab client with consistent token file path
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKEN_FILE_PATH, capture_callback=False)
        
        # Fetch minute data
        minute_data, error = get_minute_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching minute data: {error}")
            return None, None, None, None, [], None, f"Error: {error}", {
                "source": "Minute Data",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, None
        
        # Calculate technical indicators
        tech_indicators, error = get_technical_indicators(client, symbol)
        
        if error:
            app_logger.error(f"Error calculating technical indicators: {error}")
            return {"data": minute_data}, None, None, None, [], None, f"Error: {error}", {
                "source": "Technical Indicators",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, None
        
        # Fetch options chain
        options_df, expiration_dates, underlying_price, error = get_options_chain_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching options chain: {error}")
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
        
        # Create selected symbol store
        selected_symbol_store = {
            "symbol": symbol,
            "price": underlying_price,
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        status_message = f"Data refreshed for {symbol} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        app_logger.info(status_message)
        
        # Also store the options data as the last valid options data
        last_valid_options_store = options_data.copy()
        
        # Get option contract keys for streaming
        option_keys = get_option_contract_keys(options_df)
        app_logger.debug(f"Got {len(option_keys)} option contract keys for streaming")
        
        # Start streaming for the option keys if streaming is enabled
        streaming_toggle_value = "ON"  # Default to ON
        if streaming_toggle_value == "ON":
            app_logger.info(f"Starting streaming for {len(option_keys)} option contracts")
            streaming_manager.start_streaming(option_keys)
        
        return minute_data_store, tech_indicators_store, options_data, selected_symbol_store, dropdown_options, default_expiration, status_message, None, last_valid_options_store
    
    except Exception as e:
        error_msg = f"Error refreshing data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, None, None, None, [], None, error_msg, {
            "source": "Data Refresh",
            "message": str(e),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, None

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
    app_logger.info(f"Streaming toggle set to: {toggle_value}")
    
    if not options_data or not options_data.get("options"):
        return "Streaming: No options data available", True
    
    try:
        if toggle_value == "ON":
            # Get option contract keys
            options_df = pd.DataFrame(options_data["options"])
            option_keys = get_option_contract_keys(options_df)
            app_logger.info(f"Starting streaming for {len(option_keys)} option contracts")
            
            # Start streaming
            success = streaming_manager.start_streaming(option_keys)
            
            if success:
                return "Streaming: Active", False
            else:
                return "Streaming: Failed to start", True
        else:
            # Stop streaming
            app_logger.info("Stopping streaming")
            streaming_manager.stop_streaming()
            return "Streaming: Inactive", True
    
    except Exception as e:
        error_msg = f"Error toggling streaming: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return f"Streaming: Error - {str(e)}", True

# Streaming Update Callback
@app.callback(
    [
        Output("streaming-options-store", "data"),
        Output("streaming-debug-info", "children")
    ],
    Input("streaming-update-interval", "n_intervals"),
    State("options-chain-store", "data"),
    prevent_initial_call=True
)
def update_streaming_data(n_intervals, options_data):
    """Updates the streaming options data."""
    app_logger.debug(f"Streaming update callback triggered: interval={n_intervals}")
    
    if not options_data:
        return None, "No options data available"
    
    try:
        # Get the latest streaming data
        streaming_data = streaming_manager.get_latest_data()
        
        # Create debug information
        debug_info = []
        debug_info.append(f"Streaming Update Triggered: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        debug_info.append(f"Interval Count: {n_intervals}")
        
        if not streaming_data:
            debug_info.append("No streaming data available")
            return None, "\n".join(debug_info)
        
        # Add streaming data info to debug
        debug_info.append(f"Streaming Data Available: {len(streaming_data)} contracts")
        
        # Sample a few contracts for debugging
        sample_keys = list(streaming_data.keys())[:3]
        for key in sample_keys:
            data = streaming_data[key]
            debug_info.append(f"\nContract: {key}")
            for field, value in data.items():
                if field in ["bidPrice", "askPrice", "lastPrice", "delta", "gamma", "theta", "vega"]:
                    debug_info.append(f"  {field}: {value}")
        
        # Return the streaming data and debug info
        return {
            "streaming_data": streaming_data,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, "\n".join(debug_info)
    
    except Exception as e:
        error_msg = f"Error in update_streaming_data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, f"Error: {error_msg}"

# Options Chain Tables Callback with Streaming Support
@app.callback(
    [
        Output("calls-table", "data"),
        Output("puts-table", "data")
    ],
    [
        Input("options-chain-store", "data"),
        Input("streaming-options-store", "data"),
        Input("expiration-date-dropdown", "value"),
        Input("option-type-radio", "value")
    ],
    [
        State("last-valid-options-store", "data")  # Added for state preservation
    ],
    prevent_initial_call=True
)
def update_options_tables(options_data, streaming_data, expiration_date, option_type, last_valid_options):
    """Updates the options chain tables with the fetched data and streaming updates."""
    app_logger.info(f"Update options tables callback triggered: expiration={expiration_date}, option_type={option_type}")
    
    try:
        # First, check if we have valid options data
        if not options_data or not options_data.get("options"):
            # If no current options data, try to use last valid options data
            if last_valid_options and last_valid_options.get("options"):
                app_logger.warning("Using last valid options data as fallback")
                options_data = last_valid_options
            else:
                app_logger.warning("No options data available")
                return [], []
        
        # Create a copy of the options data to avoid modifying the original
        options_df = pd.DataFrame(options_data["options"]).copy()
        app_logger.debug(f"Original options DataFrame shape: {options_df.shape}")
        
        # Apply streaming updates if available
        if streaming_data and streaming_data.get("streaming_data"):
            streaming_updates = streaming_data["streaming_data"]
            app_logger.debug(f"Applying streaming updates for {len(streaming_updates)} contracts")
            
            field_mapper = StreamingFieldMapper()
            update_count = 0
            
            # Update each contract with streaming data
            for contract_key, update_data in streaming_updates.items():
                # Normalize the contract key to match the format in the options DataFrame
                normalized_key = normalize_contract_key(contract_key)
                app_logger.debug(f"Processing streaming update for contract: {normalized_key}")
                
                # Find the corresponding row in the DataFrame
                mask = options_df["symbol"] == normalized_key
                if mask.any():
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
                else:
                    app_logger.debug(f"No matching row found for {normalized_key}")
            
            app_logger.info(f"Applied {update_count} field updates from streaming data")
        else:
            app_logger.debug("No streaming updates available")
        
        # Log the shape of the DataFrame for debugging
        app_logger.debug(f"Updated options DataFrame shape: {options_df.shape}")
        
        # Use the utility function to split options by type
        calls_data, puts_data = split_options_by_type(
            options_df, 
            expiration_date=expiration_date,
            option_type=option_type,
            last_valid_options=last_valid_options
        )
        
        app_logger.debug(f"Split options: {len(calls_data)} calls and {len(puts_data)} puts")
        return calls_data, puts_data
    
    except Exception as e:
        error_msg = f"Error in update_options_tables: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return [], []

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
    streaming_manager.stop_streaming()
    app_logger.info("Streaming stopped on app shutdown")

if __name__ == "__main__":
    # Use app.run instead of app.run_server for Dash 3.x compatibility
    app.run(debug=True, host='0.0.0.0', port=8050)

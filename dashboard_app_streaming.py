import os
import sys
import json
import time
import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import dash
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import logging
from logging.handlers import RotatingFileHandler

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utility modules
from dashboard_utils.options_utils import (
    format_options_chain_data, 
    split_options_by_type,
    calculate_implied_volatility,
    normalize_contract_key
)
from dashboard_utils.streaming_manager import StreamingManager, StreamingFieldMapper
from dashboard_utils.recommendation_callbacks import register_recommendation_callbacks
from dashboard_utils.chart_utils import create_stock_chart, create_option_chart
from dashboard_utils.layout_utils import create_app_layout
from dashboard_utils.data_utils import fetch_stock_data, fetch_options_chain
from dashboard_utils.auth_utils import check_auth_status, get_auth_url

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Set up the main application logger
app_logger = logging.getLogger('dashboard_app')
app_logger.setLevel(logging.INFO)

# Create a file handler for the application log
app_handler = RotatingFileHandler(
    os.path.join(log_dir, 'dashboard_app.log'),
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5
)
app_handler.setLevel(logging.INFO)

# Create a formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_handler.setFormatter(formatter)

# Add the handler to the logger
app_logger.addHandler(app_handler)

# Also add a stream handler for console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
app_logger.addHandler(console_handler)

# Initialize the Dash app with Bootstrap styling
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# Set the app title
app.title = "Options Analysis Dashboard"

# Create the app layout
app.layout = create_app_layout()

# Initialize the streaming manager
streaming_manager = StreamingManager()

# Authentication status check callback
@app.callback(
    [
        Output("auth-status", "children"),
        Output("auth-url", "href"),
        Output("auth-button", "style")
    ],
    Input("auth-interval", "n_intervals")
)
def update_auth_status(n):
    """Updates the authentication status display."""
    is_authenticated = check_auth_status()
    
    if is_authenticated:
        return "Authenticated ✓", "#", {"display": "none"}
    else:
        auth_url = get_auth_url()
        return "Not authenticated ✗", auth_url, {"display": "block"}

# Symbol input callback
@app.callback(
    Output("symbol-store", "data"),
    Input("symbol-input", "value"),
    Input("symbol-submit", "n_clicks"),
    State("symbol-input", "value"),
    prevent_initial_call=True
)
def update_symbol(symbol_input, n_clicks, symbol_state):
    """Updates the symbol store with the entered stock symbol."""
    # Determine which input triggered the callback
    ctx = callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Only update if the submit button was clicked or Enter was pressed in the input
    if trigger_id == "symbol-submit" and n_clicks:
        if symbol_state and symbol_state.strip():
            symbol = symbol_state.strip().upper()
            app_logger.info(f"Symbol updated to: {symbol}")
            return {"symbol": symbol}
    elif trigger_id == "symbol-input" and symbol_input and symbol_input.strip():
        symbol = symbol_input.strip().upper()
        app_logger.info(f"Symbol updated to: {symbol}")
        return {"symbol": symbol}
    
    # If no valid input, prevent update
    raise PreventUpdate

# Stock data callback
@app.callback(
    [
        Output("stock-data-store", "data"),
        Output("error-store", "data", allow_duplicate=True)
    ],
    Input("symbol-store", "data"),
    Input("stock-data-interval", "n_intervals"),
    prevent_initial_call=True
)
def update_stock_data(symbol_data, n_intervals):
    """Fetches and updates stock data for the selected symbol."""
    # Check if we have a valid symbol
    if not symbol_data or not symbol_data.get("symbol"):
        app_logger.warning("No symbol provided for stock data update")
        return None, None
    
    symbol = symbol_data["symbol"]
    app_logger.info(f"Fetching stock data for {symbol}")
    
    try:
        # Fetch the stock data
        stock_data = fetch_stock_data(symbol)
        
        if stock_data:
            app_logger.info(f"Successfully fetched stock data for {symbol}")
            return stock_data, None
        else:
            error_message = f"No stock data available for {symbol}"
            app_logger.error(error_message)
            return None, {
                "source": "Stock Data",
                "message": error_message,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception as e:
        error_message = f"Error fetching stock data for {symbol}: {str(e)}"
        app_logger.error(error_message, exc_info=True)
        return None, {
            "source": "Stock Data",
            "message": error_message,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Stock chart callback
@app.callback(
    Output("stock-chart", "figure"),
    Input("stock-data-store", "data"),
    prevent_initial_call=True
)
def update_stock_chart(stock_data):
    """Updates the stock price chart with the fetched data."""
    if not stock_data:
        app_logger.warning("No stock data available for chart update")
        return go.Figure()
    
    try:
        # Create the stock chart
        figure = create_stock_chart(stock_data)
        app_logger.info("Stock chart updated successfully")
        return figure
    except Exception as e:
        app_logger.error(f"Error updating stock chart: {e}", exc_info=True)
        return go.Figure()

# Options chain callback
@app.callback(
    [
        Output("options-chain-store", "data"),
        Output("expiration-date-dropdown", "options"),
        Output("expiration-date-dropdown", "value"),
        Output("last-valid-options-store", "data"),  # Store last valid options data
        Output("error-store", "data", allow_duplicate=True)
    ],
    Input("symbol-store", "data"),
    Input("options-chain-interval", "n_intervals"),
    State("expiration-date-dropdown", "value"),
    prevent_initial_call=True
)
def update_options_chain(symbol_data, n_intervals, current_expiration):
    """Fetches and updates options chain data for the selected symbol."""
    # Check if we have a valid symbol
    if not symbol_data or not symbol_data.get("symbol"):
        app_logger.warning("No symbol provided for options chain update")
        return None, [], None, None, None
    
    symbol = symbol_data["symbol"]
    app_logger.info(f"Fetching options chain for {symbol}")
    
    try:
        # Fetch the options chain
        options_data = fetch_options_chain(symbol)
        
        if options_data and options_data.get("options") and options_data.get("expirations"):
            app_logger.info(f"Successfully fetched options chain for {symbol}")
            
            # Format the expiration dates for the dropdown
            expiration_options = [
                {"label": exp_date, "value": exp_date}
                for exp_date in options_data["expirations"]
            ]
            
            # Determine the expiration date to use
            expiration_date = current_expiration
            if not expiration_date or expiration_date not in options_data["expirations"]:
                # Use the first available expiration date if current is not valid
                expiration_date = options_data["expirations"][0] if options_data["expirations"] else None
            
            return options_data, expiration_options, expiration_date, options_data, None
        else:
            error_message = f"No options data available for {symbol}"
            app_logger.error(error_message)
            return None, [], None, None, {
                "source": "Options Chain",
                "message": error_message,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception as e:
        error_message = f"Error fetching options chain for {symbol}: {str(e)}"
        app_logger.error(error_message, exc_info=True)
        return None, [], None, None, {
            "source": "Options Chain",
            "message": error_message,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Streaming control callback
@app.callback(
    [
        Output("streaming-error", "is_open"),
        Output("streaming-status", "children")
    ],
    [
        Input("streaming-toggle", "value"),
        Input("options-chain-store", "data")
    ],
    prevent_initial_call=True
)
def toggle_streaming(streaming_toggle, options_data):
    """Toggles the streaming data connection based on the toggle switch."""
    app_logger.info(f"Streaming toggle: {streaming_toggle}")
    
    # If streaming is turned off, stop streaming
    if streaming_toggle == "OFF":
        streaming_manager.stop_streaming()
        return False, "Streaming: Disabled"
    
    # If streaming is turned on, start streaming for the options in the chain
    if not options_data or not options_data.get("options"):
        return True, "Streaming: Error - No options data available"
    
    # Extract option contract keys for streaming
    try:
        options_df = pd.DataFrame(options_data["options"])
        option_keys = options_df["symbol"].tolist()
        
        if not option_keys:
            return True, "Streaming: Error - No option contracts found"
        
        # Start streaming
        success = streaming_manager.start_streaming(option_keys)
        
        if success:
            return False, "Streaming: Enabled - Receiving real-time data"
        else:
            return True, "Streaming: Error starting streaming"
    except Exception as e:
        app_logger.error(f"Error setting up streaming: {e}", exc_info=True)
        return True, f"Streaming: Error - {str(e)}"

# Streaming data update callback
@app.callback(
    Output("streaming-options-store", "data"),
    [
        Input("streaming-update-interval", "n_intervals"),
        Input("options-chain-store", "data")  # Add dependency on options chain data
    ],
    prevent_initial_call=True
)
def update_streaming_data(n_intervals, options_data):
    """Updates the streaming data store with the latest data."""
    app_logger.debug(f"Streaming update interval triggered: {n_intervals}")
    
    # Defensive check: ensure we have valid options data
    if not options_data or not options_data.get("options"):
        app_logger.warning("No options data available for streaming update")
        return {
            "data": {},
            "status": {"is_running": False, "status_message": "No options data available"},
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "valid": False  # Flag to indicate this is not valid streaming data
        }
    
    # Get the latest streaming data and status
    latest_data = streaming_manager.get_latest_data()
    status = streaming_manager.get_status()
    
    # If streaming is running and we have data, return it
    if status.get("is_running", False) and latest_data:
        app_logger.debug(f"Streaming data available for {len(latest_data)} contracts")
        
        # Return the data and status with valid flag
        return {
            "data": latest_data,
            "status": status,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "valid": True  # Flag to indicate this is valid streaming data
        }
    else:
        # If no streaming data is available, return with valid=False flag
        app_logger.warning("No streaming data available in this update")
        return {
            "data": {},
            "status": status,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "valid": False  # Flag to indicate this is not valid streaming data
        }

# Options Chain Tables Callback (updated to use streaming data when available)
@app.callback(
    [
        Output("calls-table", "data"),
        Output("puts-table", "data")
    ],
    [
        Input("options-chain-store", "data"),
        Input("streaming-options-store", "data"),
        Input("expiration-date-dropdown", "value"),
        Input("option-type-radio", "value"),
        Input("streaming-toggle", "value")
    ],
    [
        State("calls-table", "data"),  # Add state for current calls table data
        State("puts-table", "data"),   # Add state for current puts table data
        State("last-valid-options-store", "data")  # Add state for last valid options data
    ],
    prevent_initial_call=True
)
def update_options_tables(options_data, streaming_data, expiration_date, option_type, streaming_toggle, 
                          current_calls_data, current_puts_data, last_valid_options):
    """Updates the options chain tables with either fetched data or streaming data."""
    app_logger.info(f"Update options tables callback triggered: expiration={expiration_date}, option_type={option_type}, streaming={streaming_toggle}")
    
    # First, check if we have valid options data
    if not options_data or not options_data.get("options"):
        # If no current options data, try to use last valid options data
        if last_valid_options and last_valid_options.get("options"):
            app_logger.warning("Using last valid options data as fallback")
            options_data = last_valid_options
        else:
            app_logger.warning("No options data available, keeping current table data")
            # Return current table data to prevent table from disappearing
            return current_calls_data or [], current_puts_data or []
    
    # Use the base options data from the REST API
    options_df = pd.DataFrame(options_data["options"])
    
    # If streaming is enabled and we have valid streaming data, update the options data
    if streaming_toggle == "ON" and streaming_data and streaming_data.get("data") and streaming_data.get("valid", False):
        streaming_options = streaming_data.get("data", {})
        
        app_logger.info(f"Streaming data available for {len(streaming_options)} contracts")
        
        if streaming_options:
            try:
                # Create a copy of the options DataFrame to avoid modifying the original
                options_df_copy = options_df.copy()
                
                # Create a normalized symbol column for matching with streaming data
                options_df_copy['normalized_symbol'] = options_df_copy['symbol'].apply(normalize_contract_key)
                
                # Create a mapping from normalized symbol to DataFrame index
                normalized_symbol_to_index = {}
                for index, row in options_df_copy.iterrows():
                    normalized_symbol = row.get('normalized_symbol')
                    if normalized_symbol:
                        normalized_symbol_to_index[normalized_symbol] = index
                
                # Track how many contracts were updated
                updated_contracts = 0
                updated_fields = set()
                
                # Update the options data with streaming data
                for normalized_key, stream_data in streaming_options.items():
                    if normalized_key in normalized_symbol_to_index:
                        index = normalized_symbol_to_index[normalized_key]
                        updated_contracts += 1
                        
                        # Use the StreamingFieldMapper to map streaming data to DataFrame columns
                        for field_name, value in stream_data.items():
                            if field_name == "key":
                                continue  # Skip the key field
                            
                            # Get the corresponding column name using the mapper
                            column_name = StreamingFieldMapper.get_column_name(field_name)
                            
                            # Update the DataFrame if the column exists
                            if column_name in options_df_copy.columns:
                                options_df_copy.at[index, column_name] = value
                                updated_fields.add(column_name)
                            else:
                                # If the column doesn't exist but we have a value, log it for debugging
                                app_logger.debug(f"Column '{column_name}' not found in options DataFrame for field '{field_name}'")
                
                app_logger.info(f"Updated {updated_contracts} contracts with streaming data. Updated fields: {sorted(list(updated_fields))}")
                
                # Only use the updated DataFrame if we actually updated some contracts
                if updated_contracts > 0:
                    # Remove the temporary normalized_symbol column
                    if 'normalized_symbol' in options_df_copy.columns:
                        options_df_copy = options_df_copy.drop(columns=['normalized_symbol'])
                    
                    # Use the updated DataFrame
                    options_df = options_df_copy
                else:
                    app_logger.warning("No contracts were updated with streaming data")
            except Exception as e:
                app_logger.error(f"Error updating options with streaming data: {e}", exc_info=True)
                # Continue with the original options data if there's an error
    else:
        app_logger.info("Using base options data without streaming updates")
    
    # Verify we have data before splitting
    if options_df.empty:
        app_logger.warning("Options DataFrame is empty after processing")
        # Return current table data to prevent table from disappearing
        return current_calls_data or [], current_puts_data or []
    
    try:
        # Use the utility function to split options by type
        calls_data, puts_data = split_options_by_type(options_df, expiration_date, option_type)
        
        # Verify we have data after splitting
        if not calls_data and not puts_data:
            app_logger.warning(f"No options data after splitting by type={option_type} and expiration={expiration_date}")
            
            # Try without expiration filter as fallback
            if expiration_date:
                app_logger.info("Trying without expiration filter as fallback")
                calls_data, puts_data = split_options_by_type(options_df, None, option_type)
                
                # If still no data, return current table data to prevent disappearing
                if not calls_data and not puts_data:
                    app_logger.warning("No data after fallback, keeping current table data")
                    return current_calls_data or [], current_puts_data or []
        
        return calls_data, puts_data
    except Exception as e:
        app_logger.error(f"Error splitting options by type: {e}", exc_info=True)
        # Return current table data to prevent table from disappearing
        return current_calls_data or [], current_puts_data or []

# Error message callback
@app.callback(
    Output("error-messages", "children"),
    Input("error-store", "data"),
    prevent_initial_call=True
)
def update_error_messages(error_data):
    """Updates the error message display."""
    if not error_data:
        return ""
    
    source = error_data.get("source", "Unknown")
    message = error_data.get("message", "An unknown error occurred")
    timestamp = error_data.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    return f"Error in {source} at {timestamp}: {message}"

# Register recommendation callbacks
register_recommendation_callbacks(app)

# Run the app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

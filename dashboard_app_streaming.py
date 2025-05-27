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
from dashboard_utils.streaming_manager import StreamingManager
from dashboard_utils.streaming_field_mapper import StreamingFieldMapper
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

# Create a rotating file handler
log_file = os.path.join(log_dir, 'dashboard_app.log')
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.INFO)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
app_logger.addHandler(file_handler)
app_logger.addHandler(console_handler)

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'Options Dashboard'

# Create a client getter function for the StreamingManager
def get_schwab_client():
    try:
        import schwabdev
        client = schwabdev.Client()
        if client.is_authenticated():
            app_logger.info("Schwab client authenticated")
            return client
        else:
            app_logger.warning("Schwab client not authenticated")
            return None
    except Exception as e:
        app_logger.error(f"Error creating Schwab client: {e}")
        return None

# Create an account ID getter function for the StreamingManager
def get_account_id():
    try:
        import schwabdev
        client = schwabdev.Client()
        if client.is_authenticated():
            accounts = client.accounts()
            if accounts and len(accounts) > 0:
                account_id = accounts[0].get('accountId')
                app_logger.info(f"Using account ID: {account_id}")
                return account_id
            else:
                app_logger.warning("No accounts found")
                return None
        else:
            app_logger.warning("Schwab client not authenticated")
            return None
    except Exception as e:
        app_logger.error(f"Error getting account ID: {e}")
        return None

# Initialize the StreamingManager
streaming_manager = StreamingManager(get_schwab_client, get_account_id)

# Create the app layout
app.layout = create_app_layout()

# Register callbacks
@app.callback(
    [Output('options-chain-calls', 'data'),
     Output('options-chain-puts', 'data'),
     Output('options-expiration-date', 'options'),
     Output('options-expiration-date', 'value'),
     Output('underlying-price', 'children'),
     Output('last-valid-options-store', 'data')],
    [Input('refresh-options-button', 'n_clicks'),
     Input('symbol-input', 'value')],
    [State('options-expiration-date', 'value'),
     State('option-type-dropdown', 'value'),
     State('last-valid-options-store', 'data')]
)
def refresh_data(n_clicks, symbol, expiration_date, option_type, last_valid_options):
    app_logger.info(f"refresh_data called with symbol: {symbol}, expiration_date: {expiration_date}, option_type: {option_type}")
    
    if not symbol:
        app_logger.warning("No symbol provided")
        return [], [], [], None, "Underlying Price: N/A", None
    
    try:
        # Fetch options chain data
        options_data = fetch_options_chain(symbol)
        
        if not options_data:
            app_logger.warning(f"No options data returned for symbol: {symbol}")
            return [], [], [], None, "Underlying Price: N/A", last_valid_options
        
        # Process options chain data
        options_df, expiration_dates, underlying_price = format_options_chain_data(options_data)
        
        if options_df.empty:
            app_logger.warning(f"Empty options DataFrame for symbol: {symbol}")
            return [], [], [], None, "Underlying Price: N/A", last_valid_options
        
        # Create expiration date dropdown options
        expiration_options = [{'label': date, 'value': date} for date in expiration_dates]
        
        # Set default expiration date if not already set
        if not expiration_date or expiration_date not in expiration_dates:
            expiration_date = expiration_dates[0] if expiration_dates else None
        
        # Split options by type
        calls_data, puts_data = split_options_by_type(options_df, expiration_date, option_type)
        
        # Subscribe to streaming data for all options
        if streaming_manager and not streaming_manager.is_running:
            app_logger.info("Starting streaming manager")
            option_keys = options_df['symbol'].tolist()
            streaming_manager.start(option_keys)
        
        # Store the valid options data for future reference
        valid_options = {
            "options": options_df.to_dict('records'),
            "expiration_dates": expiration_dates,
            "underlying_price": underlying_price,
            "symbol": symbol
        }
        
        return calls_data, puts_data, expiration_options, expiration_date, f"Underlying Price: ${underlying_price:.2f}", valid_options
    
    except Exception as e:
        app_logger.error(f"Error in refresh_data: {e}", exc_info=True)
        return [], [], [], None, "Underlying Price: N/A", last_valid_options

@app.callback(
    [Output('options-chain-calls', 'data', allow_duplicate=True),
     Output('options-chain-puts', 'data', allow_duplicate=True)],
    [Input('streaming-data-store', 'data')],
    [State('options-chain-calls', 'data'),
     State('options-chain-puts', 'data'),
     State('options-expiration-date', 'value'),
     State('option-type-dropdown', 'value'),
     State('last-valid-options-store', 'data')],
    prevent_initial_call=True
)
def update_options_tables(streaming_data, calls_data, puts_data, expiration_date, option_type, last_valid_options):
    app_logger.info("update_options_tables called with streaming data")
    
    if not streaming_data or not streaming_data.get('valid', False):
        app_logger.warning("Invalid or empty streaming data")
        return calls_data, puts_data
    
    try:
        # Get the streaming updates
        updates = streaming_data.get('updates', {})
        if not updates:
            app_logger.warning("No updates in streaming data")
            return calls_data, puts_data
        
        # Combine calls and puts data
        all_options = calls_data + puts_data
        if not all_options:
            app_logger.warning("No options data to update")
            
            # Try to use last valid options as fallback
            if last_valid_options and isinstance(last_valid_options, dict) and "options" in last_valid_options:
                app_logger.info("Using last_valid_options as fallback")
                options_df = pd.DataFrame(last_valid_options["options"])
                calls_data, puts_data = split_options_by_type(
                    options_df, 
                    expiration_date, 
                    option_type, 
                    last_valid_options
                )
                return calls_data, puts_data
            
            return calls_data, puts_data
        
        # Convert to DataFrame for easier manipulation
        options_df = pd.DataFrame(all_options)
        
        # Add normalized symbol column for matching with streaming data
        options_df['normalized_symbol'] = options_df['symbol'].apply(normalize_contract_key)
        
        # Create a mapping from normalized symbols to DataFrame indices
        symbol_to_index = {row['normalized_symbol']: i for i, row in options_df.iterrows()}
        
        # Track how many contracts and fields were updated
        contracts_updated = 0
        fields_updated = 0
        
        # Update the DataFrame with streaming data
        for contract_key, fields in updates.items():
            normalized_key = normalize_contract_key(contract_key)
            
            if normalized_key in symbol_to_index:
                idx = symbol_to_index[normalized_key]
                contracts_updated += 1
                
                for field_name, value in fields.items():
                    # Use the StreamingFieldMapper to map streaming data to DataFrame columns
                    if field_name != 'key':  # Skip the key field
                        column_name = StreamingFieldMapper.get_column_name(field_name)
                        
                        # Special handling for contractType (C/P to CALL/PUT)
                        if field_name == 'contractType':
                            if value == 'C':
                                value = 'CALL'
                            elif value == 'P':
                                value = 'PUT'
                        
                        # Update the DataFrame
                        options_df.at[idx, column_name] = value
                        fields_updated += 1
        
        # Remove the temporary normalized_symbol column
        options_df = options_df.drop('normalized_symbol', axis=1)
        
        app_logger.info(f"Updated {contracts_updated} contracts with {fields_updated} fields")
        
        if contracts_updated > 0:
            # Split the updated DataFrame into calls and puts
            calls_data, puts_data = split_options_by_type(options_df, expiration_date, option_type)
        
        return calls_data, puts_data
    
    except Exception as e:
        app_logger.error(f"Error in update_options_tables: {e}", exc_info=True)
        return calls_data, puts_data

@app.callback(
    Output('streaming-data-store', 'data'),
    [Input('streaming-interval', 'n_intervals')],
    [State('streaming-toggle', 'value')]
)
def streaming_data_update(n_intervals, streaming_enabled):
    app_logger.debug(f"streaming_data_update called with n_intervals: {n_intervals}, streaming_enabled: {streaming_enabled}")
    
    if not streaming_enabled:
        app_logger.debug("Streaming disabled, not updating")
        return {'valid': False}
    
    if not streaming_manager or not streaming_manager.is_running:
        app_logger.warning("StreamingManager not running")
        return {'valid': False}
    
    try:
        # Get the latest data from the streaming manager
        with streaming_manager._lock:
            latest_data = streaming_manager.latest_data_store.copy()
        
        if not latest_data:
            app_logger.warning("No streaming data available")
            return {'valid': False}
        
        app_logger.info(f"Got streaming data for {len(latest_data)} contracts")
        
        return {
            'valid': True,
            'updates': latest_data,
            'timestamp': datetime.datetime.now().isoformat()
        }
    
    except Exception as e:
        app_logger.error(f"Error in streaming_data_update: {e}", exc_info=True)
        return {'valid': False}

@app.callback(
    Output('streaming-status', 'children'),
    [Input('streaming-status-interval', 'n_intervals')]
)
def update_streaming_status(n_intervals):
    if not streaming_manager:
        return "Streaming: Not initialized"
    
    with streaming_manager._lock:
        status = streaming_manager.status_message
        error = streaming_manager.error_message
    
    if error:
        return f"Streaming Error: {error}"
    
    return status

@app.callback(
    Output('streaming-interval', 'disabled'),
    [Input('streaming-toggle', 'value')]
)
def toggle_streaming(value):
    app_logger.info(f"toggle_streaming called with value: {value}")
    return not value

# Register recommendation callbacks
register_recommendation_callbacks(app)

# Run the app
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")

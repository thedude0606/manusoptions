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
from dashboard_utils.recommendation_tab import register_recommendation_callbacks
from dashboard_utils.streaming_manager import StreamingManager
from dashboard_utils.streaming_field_mapper import StreamingFieldMapper
from dashboard_utils.contract_utils import normalize_contract_key

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger('dashboard_app')

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
                )
            ])
        ]),
        
        # Technical Indicators Tab
        dcc.Tab(label="Technical Indicators", children=[
            html.Div([
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
                )
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
                ])
            ])
        ]),
        
        # Recommendations Tab
        dcc.Tab(label="Recommendations", children=[
            html.Div([
                # Recommendations controls
                html.Div([
                    html.Button("Generate Recommendations", id="generate-recommendations-button", n_clicks=0)
                ], style={'margin': '10px 0px'}),
                
                # Recommendations table
                dash_table.DataTable(
                    id="recommendations-table",
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
    dcc.Interval(id="update-interval", interval=60000, n_intervals=0),
    dcc.Interval(id="streaming-update-interval", interval=1000, n_intervals=0, disabled=False)
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
        Output("error-store", "data")
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
        return None, None, None, None, [], None, "", None
    
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
            }
        
        # Calculate technical indicators
        tech_indicators, error = get_technical_indicators(client, symbol)
        
        if error:
            app_logger.error(f"Error calculating technical indicators: {error}")
            return {"data": minute_data}, None, None, None, [], None, f"Error: {error}", {
                "source": "Technical Indicators",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Fetch options chain
        options_df, expiration_dates, underlying_price, error = get_options_chain_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching options chain: {error}")
            return {"data": minute_data}, {"data": tech_indicators}, None, None, [], None, f"Error: {error}", {
                "source": "Options Chain",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
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
        
        return minute_data_store, tech_indicators_store, options_data, selected_symbol_store, dropdown_options, default_expiration, status_message, None
    
    except Exception as e:
        error_msg = f"Error refreshing data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, None, None, None, [], None, f"Error: {str(e)}", {
            "source": "Data Refresh",
            "message": error_msg,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Minute Data Table Callback
@app.callback(
    Output("minute-data-table", "data"),
    Output("minute-data-table", "columns"),
    Input("minute-data-store", "data"),
    prevent_initial_call=True
)
def update_minute_data_table(minute_data):
    """Updates the minute data table with the fetched data."""
    if not minute_data or not minute_data.get("data"):
        return [], []
    
    data = minute_data["data"]
    
    # Define columns
    columns = [
        {"name": "Timestamp", "id": "timestamp"},
        {"name": "Open", "id": "open"},
        {"name": "High", "id": "high"},
        {"name": "Low", "id": "low"},
        {"name": "Close", "id": "close"},
        {"name": "Volume", "id": "volume"}
    ]
    
    return data, columns

# Technical Indicators Table Callback
@app.callback(
    Output("tech-indicators-table", "data"),
    Output("tech-indicators-table", "columns"),
    Input("tech-indicators-store", "data"),
    prevent_initial_call=True
)
def update_tech_indicators_table(tech_indicators_data):
    """Updates the technical indicators table with the calculated data."""
    if not tech_indicators_data or not tech_indicators_data.get("data"):
        return [], []
    
    data = tech_indicators_data["data"]
    
    if not data:
        return [], []
    
    # Get column names from the first row
    first_row = data[0]
    columns = [{"name": col, "id": col} for col in first_row.keys()]
    
    # Ensure timeframe column is first
    if "timeframe" in first_row:
        timeframe_col = {"name": "Timeframe", "id": "timeframe"}
        columns = [timeframe_col] + [col for col in columns if col["id"] != "timeframe"]
    
    return data, columns

# Streaming toggle callback
@app.callback(
    [
        Output("streaming-update-interval", "disabled"),
        Output("streaming-status", "children")
    ],
    [
        Input("streaming-toggle", "value"),
        Input("options-chain-store", "data")
    ],
    prevent_initial_call=True
)
def toggle_streaming(streaming_toggle, options_data):
    """Toggles streaming data updates."""
    app_logger.info(f"Streaming toggle: {streaming_toggle}")
    
    if streaming_toggle == "OFF":
        # Stop streaming
        streaming_manager.stop_streaming()
        return True, "Streaming: Disabled"
    
    # Check if we have options data
    if not options_data or not options_data.get("options"):
        return True, "Streaming: No options data available"
    
    # Get option contract keys
    options = options_data.get("options", [])
    option_keys = [option.get("symbol") for option in options if option.get("symbol")]
    
    if not option_keys:
        return True, "Streaming: No option contracts found"
    
    # Start streaming
    success = streaming_manager.start_streaming(option_keys)
    
    if success:
        return False, "Streaming: Enabled - Receiving real-time data"
    else:
        return True, "Streaming: Error starting streaming"

# Streaming data update callback
@app.callback(
    Output("streaming-options-store", "data"),
    Input("streaming-update-interval", "n_intervals"),
    prevent_initial_call=True
)
def update_streaming_data(n_intervals):
    """Updates the streaming data store with the latest data."""
    app_logger.debug(f"Streaming update interval triggered: {n_intervals}")
    
    # Get the latest data from the streaming manager
    latest_data = streaming_manager.get_latest_data()
    status = streaming_manager.get_streaming_status()
    
    # Log some information about the data
    data_count = len(latest_data)
    app_logger.info(f"Received streaming data for {data_count} contracts. Status: {status.get('status_message', 'Unknown')}")
    
    if data_count > 0:
        # Log a sample of the data
        sample_key = next(iter(latest_data))
        sample_data = latest_data[sample_key]
        app_logger.info(f"Sample data for {sample_key}: {sample_data}")
    
    # Return the data and status
    return {
        "data": latest_data,
        "status": status,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    prevent_initial_call=True
)
def update_options_tables(options_data, streaming_data, expiration_date, option_type, streaming_toggle):
    """Updates the options chain tables with either fetched data or streaming data."""
    app_logger.info(f"Update options tables callback triggered: expiration={expiration_date}, option_type={option_type}, streaming={streaming_toggle}")
    
    if not options_data or not options_data.get("options"):
        app_logger.warning("No options data available")
        return [], []
    
    # Use the base options data from the REST API
    options_df = pd.DataFrame(options_data["options"])
    
    # If streaming is enabled and we have streaming data, update the options data
    if streaming_toggle == "ON" and streaming_data and streaming_data.get("data"):
        streaming_options = streaming_data.get("data", {})
        
        app_logger.info(f"Streaming data available for {len(streaming_options)} contracts")
        
        if streaming_options:
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
            
            # Remove the temporary normalized_symbol column
            if 'normalized_symbol' in options_df_copy.columns:
                options_df_copy = options_df_copy.drop(columns=['normalized_symbol'])
            
            # Use the updated DataFrame
            options_df = options_df_copy
    else:
        app_logger.info("Using base options data without streaming updates")
    
    # Use the utility function to split options by type
    calls_data, puts_data = split_options_by_type(options_df, expiration_date, option_type)
    
    return calls_data, puts_data

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

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import datetime
import logging
import schwabdev
import json
import os
import traceback
from config import APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_FILE_PATH
from dashboard_utils.data_fetchers import get_minute_data, get_technical_indicators, get_options_chain_data
from dashboard_utils.options_chain_utils import split_options_by_type, ensure_putcall_field
from dashboard_utils.recommendation_tab import register_recommendation_callbacks
from dashboard_utils.download_component import create_download_component, register_download_callback, register_download_click_callback
from dashboard_utils.export_buttons import create_export_button, register_export_callbacks

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger('dashboard_app')

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Manus Options Dashboard"

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
                    ], style={'display': 'inline-block'})
                ], style={'margin': '10px 0px'}),
                
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
                # Recommendations controls
                html.Div([
                    html.Button("Generate Recommendations", id="generate-recommendations-button", n_clicks=0)
                ], style={'margin': '10px 0px'}),
                
                # Export button for Recommendations
                create_export_button("recommendations", "Export Recommendations to Excel"),
                
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
                ),
                
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
    dcc.Store(id="last-valid-options-store"),  # Added for state preservation
    dcc.Interval(id="update-interval", interval=60000, n_intervals=0)
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
        State("symbol-input", "value"),
        State("last-valid-options-store", "data")  # Added for state preservation
    ],
    prevent_initial_call=True
)
def refresh_data(n_clicks, symbol, last_valid_options):
    """Refreshes all data for the given symbol."""
    if not n_clicks or not symbol:
        return None, None, None, None, [], None, "", None, last_valid_options
    
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
            }, last_valid_options
        
        # Calculate technical indicators
        tech_indicators, error = get_technical_indicators(client, symbol)
        
        if error:
            app_logger.error(f"Error calculating technical indicators: {error}")
            return {"data": minute_data}, None, None, None, [], None, f"Error: {error}", {
                "source": "Technical Indicators",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, last_valid_options
        
        # Fetch options chain
        options_df, expiration_dates, underlying_price, error = get_options_chain_data(client, symbol)
        
        if error:
            app_logger.error(f"Error fetching options chain: {error}")
            return {"data": minute_data}, {"data": tech_indicators}, None, None, [], None, f"Error: {error}", {
                "source": "Options Chain",
                "message": error,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, last_valid_options
        
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
        
        # Ensure putCall field is properly set for all options
        options_df = ensure_putcall_field(options_df)
        
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
        
        return minute_data_store, tech_indicators_store, options_data, selected_symbol_store, dropdown_options, default_expiration, status_message, None, last_valid_options_store
    
    except Exception as e:
        error_msg = f"Error refreshing data: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, None, None, None, [], None, f"Error: {str(e)}", {
            "source": "Data Refresh",
            "message": error_msg,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, last_valid_options

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
    
    data = tech_indicators_data.get("data", [])
    
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

# Options Chain Tables Callback
@app.callback(
    [
        Output("calls-table", "data"),
        Output("puts-table", "data")
    ],
    [
        Input("options-chain-store", "data"),
        Input("expiration-date-dropdown", "value"),
        Input("option-type-radio", "value")
    ],
    [
        State("last-valid-options-store", "data")  # Added for state preservation
    ],
    prevent_initial_call=True
)
def update_options_tables(options_data, expiration_date, option_type, last_valid_options):
    """Updates the options chain tables with the fetched data."""
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
        
        # Use the utility function to split options by type
        options_df = pd.DataFrame(options_data["options"])
        
        # Log the shape of the DataFrame for debugging
        app_logger.debug(f"Options DataFrame shape: {options_df.shape}")
        
        # Use the enhanced split_options_by_type function with last_valid_options
        calls_data, puts_data = split_options_by_type(
            options_df, 
            expiration_date=expiration_date,
            option_type=option_type,
            last_valid_options=last_valid_options
        )
        
        return calls_data, puts_data
    
    except Exception as e:
        app_logger.error(f"Error in update_options_tables: {str(e)}", exc_info=True)
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

if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0', port=8050)

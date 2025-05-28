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
# Import the updated download component instead of the old one
from dashboard_utils.download_component_updated import create_download_component, register_download_callback
from dashboard_utils.export_buttons_updated import create_export_button, register_export_callbacks

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
                
                # Download component for Minute Data - using updated component
                dcc.Download(id="minute-data-download")
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
                
                # Download component for Technical Indicators - using updated component
                dcc.Download(id="tech-indicators-download")
            ])
        ]),
        
        # Options Chain Tab
        dcc.Tab(label="Options Chain", children=[
            html.Div([
                # Export button for Options Chain
                create_export_button("options-chain", "Export Options Chain to Excel"),
                
                # Dropdown for expiration date selection
                html.Div([
                    html.Label("Expiration Date:"),
                    dcc.Dropdown(
                        id="expiration-date-dropdown",
                        options=[],
                        value=None,
                        style={'width': '100%'}
                    )
                ], style={'margin': '10px 0px'}),
                
                # Tabs for calls and puts
                dcc.Tabs([
                    dcc.Tab(label="Calls", children=[
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
                    ]),
                    dcc.Tab(label="Puts", children=[
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
                    ])
                ]),
                
                # Download component for Options Chain - using updated component
                dcc.Download(id="options-chain-download")
            ])
        ]),
        
        # Recommendations Tab
        dcc.Tab(label="Recommendations", children=[
            html.Div([
                # Export button for Recommendations
                create_export_button("recommendations", "Export Recommendations to Excel"),
                
                # Dropdown for timeframe selection
                html.Div([
                    html.Label("Timeframe:"),
                    dcc.Dropdown(
                        id="recommendation-timeframe-dropdown",
                        options=[
                            {'label': 'Short Term (Days)', 'value': 'short'},
                            {'label': 'Medium Term (Weeks)', 'value': 'medium'},
                            {'label': 'Long Term (Months)', 'value': 'long'}
                        ],
                        value='medium',
                        style={'width': '100%'}
                    )
                ], style={'margin': '10px 0px'}),
                
                # Generate recommendations button
                html.Button(
                    "Generate Recommendations",
                    id="generate-recommendations-button",
                    n_clicks=0,
                    style={
                        'backgroundColor': '#2196F3',
                        'color': 'white',
                        'padding': '10px 15px',
                        'border': 'none',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'marginTop': '10px',
                        'marginBottom': '10px',
                        'fontSize': '14px'
                    }
                ),
                
                # Recommendation status
                html.Div(id="recommendation-status", style={'margin': '10px 0px'}),
                
                # Market direction section
                html.Div([
                    html.H4("Market Direction"),
                    html.Div(id="market-direction-content")
                ]),
                
                # Tabs for call and put recommendations
                dcc.Tabs([
                    dcc.Tab(label="Call Recommendations", children=[
                        dash_table.DataTable(
                            id="call-recommendations-table",
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
                    ]),
                    dcc.Tab(label="Put Recommendations", children=[
                        dash_table.DataTable(
                            id="put-recommendations-table",
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
                
                # Download component for Recommendations - using updated component
                dcc.Download(id="recommendations-download")
            ])
        ])
    ]),
    
    # Hidden divs for storing data
    html.Div([
        dcc.Store(id="minute-data-store"),
        dcc.Store(id="tech-indicators-store"),
        dcc.Store(id="options-chain-store"),
        dcc.Store(id="recommendations-store"),
        dcc.Store(id="selected-symbol-store"),
        dcc.Store(id="error-store")
    ], style={'display': 'none'})
])

# Register callbacks
@app.callback(
    Output("selected-symbol-store", "data"),
    Input("symbol-input", "value")
)
def update_selected_symbol(symbol):
    """Update selected symbol in store."""
    if not symbol:
        return {"symbol": "AAPL"}
    return {"symbol": symbol.upper()}

@app.callback(
    [
        Output("minute-data-store", "data"),
        Output("tech-indicators-store", "data"),
        Output("options-chain-store", "data"),
        Output("status-message", "children"),
        Output("error-store", "data", allow_duplicate=True)
    ],
    [Input("refresh-button", "n_clicks")],
    [State("selected-symbol-store", "data")],
    prevent_initial_call=True
)
def refresh_data(n_clicks, selected_symbol):
    """Refresh all data when refresh button is clicked."""
    if not n_clicks:
        return [None, None, None, "", {"error": ""}]
    
    try:
        symbol = selected_symbol.get("symbol", "AAPL") if selected_symbol else "AAPL"
        app_logger.info(f"Refreshing data for {symbol}")
        
        # Get minute data
        minute_data = get_minute_data(symbol)
        
        # Get technical indicators
        tech_indicators = get_technical_indicators(symbol)
        
        # Get options chain
        options_chain = get_options_chain_data(symbol)
        
        status_message = f"Data refreshed for {symbol} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        app_logger.info(status_message)
        
        return [minute_data, tech_indicators, options_chain, status_message, {"error": ""}]
    
    except Exception as e:
        error_message = f"Error refreshing data: {str(e)}"
        app_logger.error(error_message, exc_info=True)
        return [None, None, None, "", {"error": error_message}]

@app.callback(
    Output("minute-data-table", "data"),
    Output("minute-data-table", "columns"),
    Input("minute-data-store", "data")
)
def update_minute_data_table(minute_data):
    """Update minute data table when data is available."""
    if not minute_data or not minute_data.get("data"):
        return [], []
    
    data = minute_data.get("data", [])
    if not data:
        return [], []
    
    # Create columns configuration
    columns = [{"name": col, "id": col} for col in data[0].keys()]
    
    return data, columns

@app.callback(
    Output("tech-indicators-table", "data"),
    Output("tech-indicators-table", "columns"),
    Input("tech-indicators-store", "data")
)
def update_tech_indicators_table(tech_indicators_data):
    """Update technical indicators table when data is available."""
    if not tech_indicators_data or not tech_indicators_data.get("data"):
        return [], []
    
    data = tech_indicators_data.get("data", [])
    if not data:
        return [], []
    
    # Create columns configuration
    columns = [{"name": col, "id": col} for col in data[0].keys()]
    
    return data, columns

@app.callback(
    Output("expiration-date-dropdown", "options"),
    Output("expiration-date-dropdown", "value"),
    Input("options-chain-store", "data")
)
def update_expiration_dates(options_data):
    """Update expiration date dropdown when options data is available."""
    if not options_data or not options_data.get("expiration_dates"):
        return [], None
    
    expiration_dates = options_data.get("expiration_dates", [])
    options = [{"label": date, "value": date} for date in expiration_dates]
    
    # Select first expiration date by default
    default_value = expiration_dates[0] if expiration_dates else None
    
    return options, default_value

@app.callback(
    Output("calls-table", "data"),
    Output("calls-table", "columns"),
    Output("puts-table", "data"),
    Output("puts-table", "columns"),
    Input("options-chain-store", "data"),
    Input("expiration-date-dropdown", "value")
)
def update_options_tables(options_data, selected_expiration):
    """Update options tables when data is available and expiration date is selected."""
    if not options_data or not options_data.get("options") or not selected_expiration:
        return [], [], [], []
    
    options = options_data.get("options", [])
    if not options:
        return [], [], [], []
    
    # Ensure putCall field exists
    options = ensure_putcall_field(options)
    
    # Filter by expiration date
    filtered_options = [opt for opt in options if opt.get("expirationDate") == selected_expiration]
    
    # Split into calls and puts
    calls, puts = split_options_by_type(filtered_options)
    
    # Create columns configuration (use first item to determine columns)
    if calls:
        call_columns = [{"name": col, "id": col} for col in calls[0].keys()]
    else:
        call_columns = []
    
    if puts:
        put_columns = [{"name": col, "id": col} for col in puts[0].keys()]
    else:
        put_columns = []
    
    return calls, call_columns, puts, put_columns

@app.callback(
    Output("error-messages", "children"),
    Input("error-store", "data")
)
def update_error_messages(error_data):
    """Update error messages when error data is available."""
    if not error_data or not error_data.get("error"):
        return ""
    
    error_message = error_data.get("error", "")
    return error_message

# Register recommendation callbacks
register_recommendation_callbacks(app)

# Register export callbacks with updated functions
register_export_callbacks(app)

# Register download callbacks with updated functions
for id_prefix in ["minute-data-download", "tech-indicators-download", "options-chain-download", "recommendations-download"]:
    register_download_callback(app, id_prefix)

# Run the app
if __name__ == "__main__":
    # Updated to use app.run() instead of app.run_server() for compatibility with newer Dash versions
    app.run(debug=True, host="0.0.0.0")

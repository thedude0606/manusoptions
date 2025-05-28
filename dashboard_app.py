"""
Options Trading Dashboard Application
This module provides a web-based dashboard for options trading analysis and recommendations.
"""
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import logging
import os
import traceback
from config import APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_FILE_PATH
from dashboard_utils.data_fetchers import get_minute_data, get_technical_indicators, get_options_chain_data
from dashboard_utils.options_chain_utils import split_options_by_type, ensure_putcall_field
from dashboard_utils.recommendation_tab import register_recommendation_callbacks
from dashboard_utils.download_component import create_download_component, register_download_callback, register_download_click_callback
from dashboard_utils.export_buttons import create_export_button, register_export_callbacks
# Import the enhanced recommendation callbacks
from debug_fixes.recommendations_fix import register_recommendation_callbacks_enhanced

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Define the app layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Options Trading Dashboard", className="dashboard-title"),
        html.Div([
            dcc.Input(
                id="symbol-input",
                type="text",
                placeholder="Enter symbol (e.g., AAPL)",
                value="AAPL",
                className="symbol-input"
            ),
            html.Button("Refresh Data", id="refresh-button", n_clicks=0, className="refresh-button"),
            html.Div(id="status-message", className="status-message")
        ], className="header-controls")
    ], className="dashboard-header"),
    
    # Main content
    html.Div([
        # Tabs
        dcc.Tabs([
            # Minute Data Tab
            dcc.Tab(label="Minute Data", children=[
                html.Div([
                    # Minute data controls
                    html.Div([
                        dcc.Dropdown(
                            id="minute-data-timeframe-dropdown",
                            options=[
                                {"label": "1 Day", "value": "1day"},
                                {"label": "5 Days", "value": "5day"},
                                {"label": "1 Month", "value": "1month"}
                            ],
                            value="1day",
                            clearable=False,
                            className="timeframe-dropdown"
                        )
                    ], className="tab-controls"),
                    
                    # Export button for Minute Data
                    create_export_button("minute-data", "Export Minute Data to Excel"),
                    
                    # Minute data chart
                    dcc.Graph(id="minute-data-chart", className="data-chart"),
                    
                    # Minute data table
                    dash_table.DataTable(
                        id="minute-data-table",
                        page_size=15,
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "textAlign": "left",
                            "padding": "10px",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_header={
                            "backgroundColor": "#f8f9fa",
                            "fontWeight": "bold",
                            "border": "1px solid #ddd"
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "#f5f5f5"
                            }
                        ],
                        className="data-table"
                    )
                ], className="tab-content")
            ]),
            
            # Technical Indicators Tab
            dcc.Tab(label="Technical Indicators", children=[
                html.Div([
                    # Technical indicators controls
                    html.Div([
                        dcc.Dropdown(
                            id="tech-indicators-timeframe-dropdown",
                            options=[
                                {"label": "1 Hour", "value": "1hour"},
                                {"label": "4 Hours", "value": "4hour"},
                                {"label": "1 Day", "value": "1day"}
                            ],
                            value="1hour",
                            clearable=False,
                            className="timeframe-dropdown"
                        )
                    ], className="tab-controls"),
                    
                    # Export button for Technical Indicators
                    create_export_button("tech-indicators", "Export Technical Indicators to Excel"),
                    
                    # Technical indicators table
                    dash_table.DataTable(
                        id="tech-indicators-table",
                        page_size=15,
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "textAlign": "left",
                            "padding": "10px",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_header={
                            "backgroundColor": "#f8f9fa",
                            "fontWeight": "bold",
                            "border": "1px solid #ddd"
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "#f5f5f5"
                            }
                        ],
                        className="data-table"
                    )
                ], className="tab-content")
            ]),
            
            # Options Chain Tab
            dcc.Tab(label="Options Chain", children=[
                html.Div([
                    # Options chain controls
                    html.Div([
                        dcc.Dropdown(
                            id="expiration-date-dropdown",
                            placeholder="Select expiration date",
                            className="expiration-dropdown"
                        )
                    ], className="tab-controls"),
                    
                    # Export button for Options Chain
                    create_export_button("options-chain", "Export Options Chain to Excel"),
                    
                    # Options chain tables
                    html.Div([
                        html.Div([
                            html.H3("Calls", className="table-header"),
                            dash_table.DataTable(
                                id="calls-table",
                                page_size=10,
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "10px",
                                    "whiteSpace": "normal",
                                    "height": "auto"
                                },
                                style_header={
                                    "backgroundColor": "#f8f9fa",
                                    "fontWeight": "bold",
                                    "border": "1px solid #ddd"
                                },
                                style_data_conditional=[
                                    {
                                        "if": {"row_index": "odd"},
                                        "backgroundColor": "#f5f5f5"
                                    }
                                ],
                                className="data-table"
                            )
                        ], className="table-container"),
                        html.Div([
                            html.H3("Puts", className="table-header"),
                            dash_table.DataTable(
                                id="puts-table",
                                page_size=10,
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "10px",
                                    "whiteSpace": "normal",
                                    "height": "auto"
                                },
                                style_header={
                                    "backgroundColor": "#f8f9fa",
                                    "fontWeight": "bold",
                                    "border": "1px solid #ddd"
                                },
                                style_data_conditional=[
                                    {
                                        "if": {"row_index": "odd"},
                                        "backgroundColor": "#f5f5f5"
                                    }
                                ],
                                className="data-table"
                            )
                        ], className="table-container")
                    ], className="options-tables-container")
                ], className="tab-content")
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
                    
                    # Market Direction Panel
                    html.Div([
                        html.H3("Market Direction Analysis", className="panel-header"),
                        html.Div([
                            html.Div([
                                html.Div(id="market-direction-indicator", className="direction-indicator"),
                                html.Div(id="market-direction-text", className="direction-text")
                            ], className="direction-container"),
                            html.Div([
                                html.Div("Bullish Score:", className="score-label"),
                                html.Div(id="bullish-score", className="score-value")
                            ], className="score-container"),
                            html.Div([
                                html.Div("Bearish Score:", className="score-label"),
                                html.Div(id="bearish-score", className="score-value")
                            ], className="score-container")
                        ], className="direction-scores")
                    ], className="panel market-direction-panel"),
                    
                    # Recommendations Tables
                    html.Div([
                        # Call Recommendations
                        html.Div([
                            html.H3("Call Recommendations", className="panel-header"),
                            dash_table.DataTable(
                                id="call-recommendations-table",
                                columns=[
                                    {"name": "Symbol", "id": "symbol"},
                                    {"name": "Strike", "id": "strikePrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Expiration", "id": "expirationDate"},
                                    {"name": "Current Price", "id": "currentPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Target Price", "id": "targetSellPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Expected Profit", "id": "expectedProfitPct", "type": "numeric", "format": {"specifier": ".1f%"}},
                                    {"name": "Confidence", "id": "confidenceScore", "type": "numeric", "format": {"specifier": ".0f%"}}
                                ],
                                data=[],
                                page_size=5,
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "10px",
                                    "whiteSpace": "normal",
                                    "height": "auto"
                                },
                                style_header={
                                    "backgroundColor": "#f8f9fa",
                                    "fontWeight": "bold",
                                    "border": "1px solid #ddd"
                                },
                                style_data_conditional=[
                                    {
                                        "if": {"row_index": "odd"},
                                        "backgroundColor": "#f5f5f5"
                                    }
                                ],
                                row_selectable="single",
                                selected_rows=[],
                                className="data-table"
                            )
                        ], className="panel recommendations-panel"),
                        
                        # Put Recommendations
                        html.Div([
                            html.H3("Put Recommendations", className="panel-header"),
                            dash_table.DataTable(
                                id="put-recommendations-table",
                                columns=[
                                    {"name": "Symbol", "id": "symbol"},
                                    {"name": "Strike", "id": "strikePrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Expiration", "id": "expirationDate"},
                                    {"name": "Current Price", "id": "currentPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Target Price", "id": "targetSellPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Expected Profit", "id": "expectedProfitPct", "type": "numeric", "format": {"specifier": ".1f%"}},
                                    {"name": "Confidence", "id": "confidenceScore", "type": "numeric", "format": {"specifier": ".0f%"}}
                                ],
                                data=[],
                                page_size=5,
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "10px",
                                    "whiteSpace": "normal",
                                    "height": "auto"
                                },
                                style_header={
                                    "backgroundColor": "#f8f9fa",
                                    "fontWeight": "bold",
                                    "border": "1px solid #ddd"
                                },
                                style_data_conditional=[
                                    {
                                        "if": {"row_index": "odd"},
                                        "backgroundColor": "#f5f5f5"
                                    }
                                ],
                                row_selectable="single",
                                selected_rows=[],
                                className="data-table"
                            )
                        ], className="panel recommendations-panel")
                    ], className="recommendations-tables"),
                    
                    # Contract Details Panel
                    html.Div([
                        html.H3("Contract Details", className="panel-header"),
                        html.Div([
                            html.Div([
                                html.Div("Symbol:", className="detail-label"),
                                html.Div(id="detail-symbol", className="detail-value")
                            ], className="detail-item"),
                            html.Div([
                                html.Div("Type:", className="detail-label"),
                                html.Div(id="detail-type", className="detail-value")
                            ], className="detail-item"),
                            html.Div([
                                html.Div("Strike Price:", className="detail-label"),
                                html.Div(id="detail-strike", className="detail-value")
                            ], className="detail-item"),
                            html.Div([
                                html.Div("Expiration:", className="detail-label"),
                                html.Div(id="detail-expiration", className="detail-value")
                            ], className="detail-item"),
                            html.Div([
                                html.Div("Delta:", className="detail-label"),
                                html.Div(id="detail-delta", className="detail-value")
                            ], className="detail-item"),
                            html.Div([
                                html.Div("Gamma:", className="detail-label"),
                                html.Div(id="detail-gamma", className="detail-value")
                            ], className="detail-item"),
                            html.Div([
                                html.Div("Theta:", className="detail-label"),
                                html.Div(id="detail-theta", className="detail-value")
                            ], className="detail-item"),
                            html.Div([
                                html.Div("Vega:", className="detail-label"),
                                html.Div(id="detail-vega", className="detail-value")
                            ], className="detail-item"),
                            html.Div([
                                html.Div("Implied Volatility:", className="detail-label"),
                                html.Div(id="detail-iv", className="detail-value")
                            ], className="detail-item")
                        ], className="panel details-panel")
                    ], className="recommendations-panels"),
                    
                    # Last updated timestamp
                    html.Div(id="recommendations-last-updated", className="last-updated")
                ], className="tab-content")
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
    """Refreshes all data for the selected symbol."""
    if not symbol:
        return None, None, None, None, [], None, "Please enter a valid symbol", {
            "source": "Refresh Data",
            "message": "No symbol provided",
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    try:
        # Get minute data
        minute_data = get_minute_data(symbol)
        if minute_data is None or minute_data.empty:
            return None, None, None, None, [], None, f"No data found for {symbol}", {
                "source": "Refresh Data",
                "message": f"No minute data found for {symbol}",
                "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Calculate technical indicators
        tech_indicators = get_technical_indicators(minute_data)
        
        # Get options chain data
        options_chain = get_options_chain_data(symbol)
        if options_chain is None or not options_chain.get("options"):
            return None, None, None, None, [], None, f"No options data found for {symbol}", {
                "source": "Refresh Data",
                "message": f"No options data found for {symbol}",
                "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Ensure putCall field exists
        options_chain["options"] = ensure_putcall_field(options_chain["options"])
        
        # Get expiration dates
        expiration_dates = sorted(list(set(opt["expirationDate"] for opt in options_chain["options"])))
        expiration_options = [{"label": date, "value": date} for date in expiration_dates]
        
        # Selected symbol data
        selected_symbol = {
            "symbol": symbol,
            "price": options_chain.get("underlyingPrice", 0)
        }
        
        return (
            minute_data.to_dict("records"),
            tech_indicators,
            options_chain,
            selected_symbol,
            expiration_options,
            expiration_dates[0] if expiration_dates else None,
            f"Data for {symbol} refreshed at {pd.Timestamp.now().strftime('%H:%M:%S')}",
            None
        )
        
    except Exception as e:
        error_msg = f"Error refreshing data: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        return None, None, None, None, [], None, f"Error: {str(e)}", {
            "source": "Refresh Data",
            "message": error_msg,
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "traceback": traceback.format_exc()
        }

# Minute Data Chart Callback
@app.callback(
    Output("minute-data-chart", "figure"),
    Input("minute-data-store", "data"),
    Input("minute-data-timeframe-dropdown", "value"),
    prevent_initial_call=True
)
def update_minute_data_chart(minute_data, timeframe):
    """Updates the minute data chart with the selected timeframe."""
    if not minute_data:
        return go.Figure()
    
    df = pd.DataFrame(minute_data)
    
    # Filter data based on timeframe
    if timeframe == "1day":
        df = df.tail(390)  # Approximately one trading day (6.5 hours * 60 minutes)
    elif timeframe == "5day":
        df = df.tail(390 * 5)  # Approximately five trading days
    
    # Create candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=df["timestamp"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350"
    )])
    
    # Add volume as bar chart
    fig.add_trace(go.Bar(
        x=df["timestamp"],
        y=df["volume"],
        marker_color="rgba(128, 128, 128, 0.5)",
        opacity=0.5,
        yaxis="y2",
        name="Volume"
    ))
    
    # Update layout
    fig.update_layout(
        title=f"Minute Data for {df['symbol'].iloc[0] if 'symbol' in df.columns else 'Symbol'}",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        yaxis2=dict(
            title="Volume",
            overlaying="y",
            side="right",
            showgrid=False
        ),
        height=500,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig

# Minute Data Table Callback
@app.callback(
    Output("minute-data-table", "data"),
    Output("minute-data-table", "columns"),
    Input("minute-data-store", "data"),
    Input("minute-data-timeframe-dropdown", "value"),
    prevent_initial_call=True
)
def update_minute_data_table(minute_data, timeframe):
    """Updates the minute data table with the selected timeframe."""
    if not minute_data:
        return [], []
    
    df = pd.DataFrame(minute_data)
    
    # Filter data based on timeframe
    if timeframe == "1day":
        df = df.tail(390)  # Approximately one trading day (6.5 hours * 60 minutes)
    elif timeframe == "5day":
        df = df.tail(390 * 5)  # Approximately five trading days
    
    # Format timestamp
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # Create columns
    columns = [{"name": col.capitalize(), "id": col} for col in df.columns]
    
    return df.to_dict("records"), columns

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
    
    # Get the selected timeframe data
    timeframe_data = tech_indicators_data.get("timeframe_data", {})
    if not timeframe_data:
        return [], []
    
    # Default to 1hour timeframe if available
    timeframe = "1hour"
    if timeframe not in timeframe_data and timeframe_data:
        timeframe = list(timeframe_data.keys())[0]
    
    # Get data for the selected timeframe
    df = pd.DataFrame(timeframe_data.get(timeframe, []))
    if df.empty:
        return [], []
    
    # Format timestamp
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # Create columns
    columns = [{"name": col.capitalize(), "id": col} for col in df.columns]
    
    return df.to_dict("records"), columns

# Options Chain Tables Callback
@app.callback(
    Output("calls-table", "data"),
    Output("calls-table", "columns"),
    Output("puts-table", "data"),
    Output("puts-table", "columns"),
    Output("last-valid-options-store", "data"),
    Input("options-chain-store", "data"),
    Input("expiration-date-dropdown", "value"),
    State("last-valid-options-store", "data"),
    prevent_initial_call=True
)
def update_options_tables(options_chain_data, expiration_date, last_valid_options):
    """Updates the options chain tables with the selected expiration date."""
    if not options_chain_data or not options_chain_data.get("options"):
        return [], [], [], [], last_valid_options
    
    # Get options data
    options = options_chain_data.get("options", [])
    
    # Filter by expiration date
    if expiration_date:
        options = [opt for opt in options if opt.get("expirationDate") == expiration_date]
    
    # Split into calls and puts
    calls, puts = split_options_by_type(options)
    
    if not calls and not puts:
        return [], [], [], [], last_valid_options
    
    # Create DataFrames
    calls_df = pd.DataFrame(calls) if calls else pd.DataFrame()
    puts_df = pd.DataFrame(puts) if puts else pd.DataFrame()
    
    # Sort by strike price
    if not calls_df.empty and "strikePrice" in calls_df.columns:
        calls_df = calls_df.sort_values("strikePrice")
    if not puts_df.empty and "strikePrice" in puts_df.columns:
        puts_df = puts_df.sort_values("strikePrice")
    
    # Create columns for calls
    calls_columns = []
    if not calls_df.empty:
        # Select and order columns
        column_order = [
            "symbol", "strikePrice", "lastPrice", "bid", "ask", "change", "percentChange",
            "volume", "openInterest", "impliedVolatility", "delta", "gamma", "theta", "vega"
        ]
        calls_df = calls_df[[col for col in column_order if col in calls_df.columns]]
        calls_columns = [{"name": col.capitalize(), "id": col} for col in calls_df.columns]
    
    # Create columns for puts
    puts_columns = []
    if not puts_df.empty:
        # Select and order columns
        column_order = [
            "symbol", "strikePrice", "lastPrice", "bid", "ask", "change", "percentChange",
            "volume", "openInterest", "impliedVolatility", "delta", "gamma", "theta", "vega"
        ]
        puts_df = puts_df[[col for col in column_order if col in puts_df.columns]]
        puts_columns = [{"name": col.capitalize(), "id": col} for col in puts_df.columns]
    
    # Store valid options data
    valid_options = {
        "calls": calls_df.to_dict("records") if not calls_df.empty else [],
        "puts": puts_df.to_dict("records") if not puts_df.empty else [],
        "expiration_date": expiration_date
    }
    
    return (
        calls_df.to_dict("records") if not calls_df.empty else [],
        calls_columns,
        puts_df.to_dict("records") if not puts_df.empty else [],
        puts_columns,
        valid_options
    )

# Register callbacks
register_export_callbacks(app)
register_download_callback(app)
register_download_click_callback(app)
# Use the enhanced recommendation callbacks instead of the standard ones
register_recommendation_callbacks_enhanced(app)

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)

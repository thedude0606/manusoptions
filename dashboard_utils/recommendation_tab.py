"""
Recommendation Tab for Options Trading Dashboard

This module provides the UI components and callbacks for the recommendation engine tab,
which displays actionable buy/sell recommendations for options trading.
"""

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import numpy as np
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def create_recommendation_tab():
    """
    Create the recommendation tab layout.
    
    Returns:
        html.Div: The recommendation tab layout
    """
    return html.Div([
        html.Div([
            dcc.Dropdown(
                id="recommendation-timeframe-dropdown",
                options=[
                    {"label": "1 Hour", "value": "1hour"},
                    {"label": "4 Hours", "value": "4hour"}
                ],
                value="1hour",
                clearable=False,
                className="timeframe-dropdown"
            ),
            html.Div(id="recommendation-status", className="recommendation-status")
        ], className="tab-controls"),
        
        html.Div([
            # Market Direction Panel
            html.Div([
                html.H3("Market Direction Analysis", className="panel-header"),
                html.Div([
                    html.Div([
                        html.Div(id="market-direction-indicator", className="direction-indicator"),
                        html.Div(id="market-direction-text", className="direction-text")
                    ], className="direction-container"),
                    html.Div([
                        html.Div([
                            html.Label("Bullish", className="score-label"),
                            html.Div(id="bullish-score", className="score-value")
                        ], className="score-container"),
                        html.Div([
                            html.Label("Bearish", className="score-label"),
                            html.Div(id="bearish-score", className="score-value")
                        ], className="score-container")
                    ], className="scores-container"),
                ], className="market-direction-panel"),
                html.Div(id="market-signals", className="market-signals")
            ], className="panel market-panel"),
            
            # Call Recommendations Panel
            html.Div([
                html.H3("Call Recommendations", className="panel-header"),
                html.Div(id="call-recommendations-loading", children=[
                    dcc.Loading(
                        id="call-recommendations-loading-spinner",
                        type="circle",
                        children=html.Div(id="call-recommendations-container", children=[
                            dash_table.DataTable(
                                id="call-recommendations-table",
                                columns=[
                                    {"name": "Symbol", "id": "symbol"},
                                    {"name": "Strike", "id": "strikePrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Expiration", "id": "expirationDate"},
                                    {"name": "DTE", "id": "daysToExpiration", "type": "numeric"},
                                    {"name": "Current Price", "id": "currentPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Target Price", "id": "targetExitPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Stop Loss", "id": "stopLossPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Entry Time", "id": "optimalEntryTime", "type": "text"},
                                    {"name": "Exit Time", "id": "optimalExitTime", "type": "text"},
                                    {"name": "Expected Profit %", "id": "expectedProfitPct", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Confidence", "id": "confidenceScore", "type": "numeric", "format": {"specifier": ".0f"}},
                                    {"name": "Conf. Interval", "id": "confidenceInterval", "type": "numeric", "format": {"specifier": ".1f"}}
                                ],
                                style_table={'overflowX': 'auto'},
                                style_cell={
                                    'textAlign': 'left',
                                    'padding': '5px',
                                    'minWidth': '80px', 'width': '80px', 'maxWidth': '120px',
                                    'whiteSpace': 'normal'
                                },
                                style_header={
                                    'backgroundColor': 'rgb(230, 230, 230)',
                                    'fontWeight': 'bold'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'column_id': 'confidenceScore', 'filter_query': '{confidenceScore} >= 80'},
                                        'backgroundColor': 'rgba(0, 255, 0, 0.2)',
                                        'color': 'green'
                                    },
                                    {
                                        'if': {'column_id': 'confidenceScore', 'filter_query': '{confidenceScore} < 80 && {confidenceScore} >= 60'},
                                        'backgroundColor': 'rgba(255, 255, 0, 0.2)',
                                        'color': 'darkgreen'
                                    }
                                ],
                                sort_action="native",
                                sort_mode="single",
                                sort_by=[{"column_id": "confidenceScore", "direction": "desc"}]
                            )
                        ])
                    )
                ])
            ], className="panel calls-panel"),
            
            # Put Recommendations Panel
            html.Div([
                html.H3("Put Recommendations", className="panel-header"),
                html.Div(id="put-recommendations-loading", children=[
                    dcc.Loading(
                        id="put-recommendations-loading-spinner",
                        type="circle",
                        children=html.Div(id="put-recommendations-container", children=[
                            dash_table.DataTable(
                                id="put-recommendations-table",
                                columns=[
                                    {"name": "Symbol", "id": "symbol"},
                                    {"name": "Strike", "id": "strikePrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Expiration", "id": "expirationDate"},
                                    {"name": "DTE", "id": "daysToExpiration", "type": "numeric"},
                                    {"name": "Current Price", "id": "currentPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Target Price", "id": "targetExitPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Stop Loss", "id": "stopLossPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Entry Time", "id": "optimalEntryTime", "type": "text"},
                                    {"name": "Exit Time", "id": "optimalExitTime", "type": "text"},
                                    {"name": "Expected Profit %", "id": "expectedProfitPct", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Confidence", "id": "confidenceScore", "type": "numeric", "format": {"specifier": ".0f"}},
                                    {"name": "Conf. Interval", "id": "confidenceInterval", "type": "numeric", "format": {"specifier": ".1f"}}
                                ],
                                style_table={'overflowX': 'auto'},
                                style_cell={
                                    'textAlign': 'left',
                                    'padding': '5px',
                                    'minWidth': '80px', 'width': '80px', 'maxWidth': '120px',
                                    'whiteSpace': 'normal'
                                },
                                style_header={
                                    'backgroundColor': 'rgb(230, 230, 230)',
                                    'fontWeight': 'bold'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'column_id': 'confidenceScore', 'filter_query': '{confidenceScore} >= 80'},
                                        'backgroundColor': 'rgba(0, 255, 0, 0.2)',
                                        'color': 'green'
                                    },
                                    {
                                        'if': {'column_id': 'confidenceScore', 'filter_query': '{confidenceScore} < 80 && {confidenceScore} >= 60'},
                                        'backgroundColor': 'rgba(255, 255, 0, 0.2)',
                                        'color': 'darkgreen'
                                    }
                                ],
                                sort_action="native",
                                sort_mode="single",
                                sort_by=[{"column_id": "confidenceScore", "direction": "desc"}]
                            )
                        ])
                    )
                ])
            ], className="panel puts-panel"),
            
            # Greeks and Details Panel
            html.Div([
                html.H3("Selected Contract Details", className="panel-header"),
                html.Div(id="contract-details-container", children=[
                    html.Div([
                        html.Div([
                            html.Label("Symbol:"),
                            html.Span(id="detail-symbol", className="detail-value")
                        ], className="detail-item"),
                        html.Div([
                            html.Label("Type:"),
                            html.Span(id="detail-type", className="detail-value")
                        ], className="detail-item"),
                        html.Div([
                            html.Label("Strike:"),
                            html.Span(id="detail-strike", className="detail-value")
                        ], className="detail-item"),
                        html.Div([
                            html.Label("Expiration:"),
                            html.Span(id="detail-expiration", className="detail-value")
                        ], className="detail-item")
                    ], className="detail-group"),
                    html.Div([
                        html.Div([
                            html.Label("Delta:"),
                            html.Span(id="detail-delta", className="detail-value")
                        ], className="detail-item"),
                        html.Div([
                            html.Label("Gamma:"),
                            html.Span(id="detail-gamma", className="detail-value")
                        ], className="detail-item"),
                        html.Div([
                            html.Label("Theta:"),
                            html.Span(id="detail-theta", className="detail-value")
                        ], className="detail-item"),
                        html.Div([
                            html.Label("Vega:"),
                            html.Span(id="detail-vega", className="detail-value")
                        ], className="detail-item"),
                        html.Div([
                            html.Label("IV:"),
                            html.Span(id="detail-iv", className="detail-value")
                        ], className="detail-item")
                    ], className="detail-group greeks-group")
                ])
            ], className="panel details-panel")
        ], className="recommendations-panels"),
        
        # Store for recommendation data
        dcc.Store(id="recommendations-store"),
        
        # Last updated timestamp
        html.Div(id="recommendations-last-updated", className="last-updated")
    ], className="tab-content")

def register_recommendation_callbacks(app):
    """
    Register callbacks for the recommendation tab.
    
    Args:
        app: The Dash app instance
    """
    @app.callback(
        [
            Output("recommendations-store", "data"),
            Output("recommendation-status", "children")
        ],
        [
            Input("tech-indicators-store", "data"),
            Input("options-chain-store", "data"),
            Input("recommendation-timeframe-dropdown", "value"),
            Input("update-interval", "n_intervals"),
            Input("streaming-options-store", "data")  # Added streaming data input
        ],
        [
            State("selected-symbol-store", "data")
        ]
    )
    def update_recommendations(tech_indicators_data, options_chain_data, timeframe, n_intervals, streaming_options_data, selected_symbol):
        """Update recommendations based on technical indicators and options chain data."""
        # Import the enhanced recommendation engine instead of the legacy one
        from enhanced_recommendation_engine import EnhancedRecommendationEngine
        
        ctx = dash.callback_context
        trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
        logger.info(f"update_recommendations triggered by: {trigger}")
        
        if not tech_indicators_data or not options_chain_data or not selected_symbol:
            logger.warning(f"Missing required data: tech_indicators_data={bool(tech_indicators_data)}, options_chain_data={bool(options_chain_data)}, selected_symbol={bool(selected_symbol)}")
            return None, "Please load symbol data first."
        
        try:
            # Get the symbol and underlying price
            symbol = selected_symbol.get("symbol", "")
            underlying_price = options_chain_data.get("underlyingPrice", 0)
            logger.info(f"Processing recommendations for symbol: {symbol}, underlying price: {underlying_price}")
            
            if not symbol or not underlying_price:
                logger.warning(f"Missing symbol or price data: symbol={symbol}, underlying_price={underlying_price}")
                return None, "Missing symbol or price data."
            
            # Get technical indicators for all timeframes
            tech_indicators_df = pd.DataFrame()
            if tech_indicators_data and "data" in tech_indicators_data:
                tech_indicators_df = pd.DataFrame(tech_indicators_data["data"])
                logger.info(f"Loaded technical indicators, shape: {tech_indicators_df.shape}")
                logger.info(f"Technical indicators columns: {tech_indicators_df.columns.tolist()}")
            
            if tech_indicators_df.empty:
                logger.warning(f"Empty technical indicators DataFrame")
                return None, f"No technical indicator data available."
            
            # Get options chain data
            options_df = pd.DataFrame()
            if options_chain_data and "options" in options_chain_data:
                options_df = pd.DataFrame(options_chain_data["options"])
                logger.info(f"Loaded options chain data, shape: {options_df.shape}")
                logger.info(f"Options chain columns: {options_df.columns.tolist()}")
            
            if options_df.empty:
                logger.warning("Empty options chain DataFrame")
                return None, "No options chain data available."
            
            # Update options data with streaming data if available
            if streaming_options_data and "data" in streaming_options_data:
                streaming_options = streaming_options_data.get("data", {})
                logger.info(f"Streaming data available for {len(streaming_options)} contracts")
                
                if streaming_options:
                    from dashboard_utils.contract_utils import normalize_contract_key
                    from dashboard_utils.streaming_field_mapper import StreamingFieldMapper
                    
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
                    
                    logger.info(f"Updated {updated_contracts} contracts with streaming data. Updated fields: {sorted(list(updated_fields))}")
                    
                    # Remove the temporary normalized_symbol column
                    if 'normalized_symbol' in options_df_copy.columns:
                        options_df_copy = options_df_copy.drop(columns=['normalized_symbol'])
                    
                    # Use the updated DataFrame
                    options_df = options_df_copy
            
            # Initialize the enhanced recommendation engine
            engine = EnhancedRecommendationEngine()
            
            # Generate recommendations using the enhanced engine
            recommendations = engine.get_recommendations(tech_indicators_df, options_df, underlying_price)
            
            # Add timestamp
            recommendations["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            logger.info(f"Generated recommendations: {len(recommendations.get('calls', []))} calls, {len(recommendations.get('puts', []))} puts")
            
            return recommendations, f"Recommendations updated at {recommendations['timestamp']}"
        
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}", exc_info=True)
            return None, f"Error generating recommendations: {str(e)}"
    
    @app.callback(
        [
            Output("call-recommendations-table", "data"),
            Output("put-recommendations-table", "data"),
            Output("market-direction-indicator", "className"),
            Output("market-direction-text", "children"),
            Output("bullish-score", "children"),
            Output("bearish-score", "children"),
            Output("market-signals", "children"),
            Output("recommendations-last-updated", "children")
        ],
        Input("recommendations-store", "data"),
        prevent_initial_call=True
    )
    def update_recommendation_tables(recommendations_data):
        """Update recommendation tables with the generated recommendations."""
        if not recommendations_data:
            return [], [], "direction-indicator neutral", "Neutral", "50", "50", "", ""
        
        # Get call and put recommendations
        call_recommendations = recommendations_data.get("calls", [])
        put_recommendations = recommendations_data.get("puts", [])
        
        # Get market direction analysis
        market_direction = recommendations_data.get("market_direction", {})
        direction = market_direction.get("direction", "neutral")
        bullish_score = market_direction.get("bullish_score", 50)
        bearish_score = market_direction.get("bearish_score", 50)
        signals = market_direction.get("signals", [])
        
        # Format market direction indicator
        direction_class = f"direction-indicator {direction}"
        direction_text = direction.capitalize()
        
        # Format market signals
        market_signals_html = html.Ul([html.Li(signal) for signal in signals[:10]])
        
        # Format last updated timestamp
        timestamp = recommendations_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        last_updated = f"Last updated: {timestamp}"
        
        return call_recommendations, put_recommendations, direction_class, direction_text, f"{bullish_score:.0f}", f"{bearish_score:.0f}", market_signals_html, last_updated
    
    @app.callback(
        [
            Output("detail-symbol", "children"),
            Output("detail-type", "children"),
            Output("detail-strike", "children"),
            Output("detail-expiration", "children"),
            Output("detail-delta", "children"),
            Output("detail-gamma", "children"),
            Output("detail-theta", "children"),
            Output("detail-vega", "children"),
            Output("detail-iv", "children")
        ],
        [
            Input("call-recommendations-table", "active_cell"),
            Input("put-recommendations-table", "active_cell")
        ],
        [
            State("call-recommendations-table", "data"),
            State("put-recommendations-table", "data")
        ],
        prevent_initial_call=True
    )
    def update_contract_details(call_active_cell, put_active_cell, call_data, put_data):
        """Update contract details when a recommendation is selected."""
        ctx = dash.callback_context
        trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
        
        default_values = ["", "", "", "", "", "", "", "", ""]
        
        try:
            if "call-recommendations-table" in trigger and call_active_cell and call_data:
                row = call_active_cell['row']
                if row < len(call_data):
                    contract = call_data[row]
                    return (
                        contract.get("symbol", ""),
                        "CALL",
                        f"{contract.get('strikePrice', 0):.2f}",
                        contract.get("expirationDate", ""),
                        f"{contract.get('delta', 'N/A')}",
                        f"{contract.get('gamma', 'N/A')}",
                        f"{contract.get('theta', 'N/A')}",
                        f"{contract.get('vega', 'N/A')}",
                        f"{contract.get('iv', 'N/A')}"
                    )
            
            elif "put-recommendations-table" in trigger and put_active_cell and put_data:
                row = put_active_cell['row']
                if row < len(put_data):
                    contract = put_data[row]
                    return (
                        contract.get("symbol", ""),
                        "PUT",
                        f"{contract.get('strikePrice', 0):.2f}",
                        contract.get("expirationDate", ""),
                        f"{contract.get('delta', 'N/A')}",
                        f"{contract.get('gamma', 'N/A')}",
                        f"{contract.get('theta', 'N/A')}",
                        f"{contract.get('vega', 'N/A')}",
                        f"{contract.get('iv', 'N/A')}"
                    )
            
            return default_values
            
        except Exception as e:
            logger.error(f"Error updating contract details: {e}", exc_info=True)
            return default_values

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
                                    {"name": "Target Price", "id": "targetSellPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Target Hours", "id": "targetTimeframeHours", "type": "numeric", "format": {"specifier": ".0f"}},
                                    {"name": "Expected Profit %", "id": "expectedProfitPct", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Confidence", "id": "confidenceScore", "type": "numeric", "format": {"specifier": ".0f"}}
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
                                    {"name": "Target Price", "id": "targetSellPrice", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Target Hours", "id": "targetTimeframeHours", "type": "numeric", "format": {"specifier": ".0f"}},
                                    {"name": "Expected Profit %", "id": "expectedProfitPct", "type": "numeric", "format": {"specifier": ".2f"}},
                                    {"name": "Confidence", "id": "confidenceScore", "type": "numeric", "format": {"specifier": ".0f"}}
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
    # First callback: Update recommendations data
    @app.callback(
        [
            Output("recommendations-store", "data"),
            Output("recommendation-status", "children"),
            Output("error-store", "data", allow_duplicate=True)
        ],
        [
            Input("generate-recommendations-button", "n_clicks"),
            Input("tech-indicators-store", "data"),
            Input("options-chain-store", "data"),
            Input("recommendation-timeframe-dropdown", "value"),
            Input("update-interval", "n_intervals")
        ],
        [
            State("selected-symbol-store", "data")
        ],
        prevent_initial_call=True
    )
    def update_recommendations(n_clicks, tech_indicators_data, options_chain_data, timeframe, n_intervals, selected_symbol):
        """Update recommendations based on technical indicators and options chain data."""
        from recommendation_engine import RecommendationEngine
        
        ctx = dash.callback_context
        trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
        logger.info(f"update_recommendations triggered by: {trigger}")
        
        # Check if this was triggered by the button click
        button_clicked = "generate-recommendations-button" in trigger
        if button_clicked:
            logger.info(f"Generate Recommendations button clicked, n_clicks: {n_clicks}")
            
            # If button was clicked but data is missing, provide clear error feedback
            if not tech_indicators_data or not options_chain_data or not selected_symbol:
                missing_data = []
                if not selected_symbol:
                    missing_data.append("symbol data")
                if not tech_indicators_data:
                    missing_data.append("technical indicators")
                if not options_chain_data:
                    missing_data.append("options chain data")
                
                error_msg = f"Missing required data: {', '.join(missing_data)}. Please refresh data first."
                logger.warning(error_msg)
                
                # Return error to status only, with no update to error-store
                return None, error_msg, dash.no_update
        
        # For non-button triggers, silently return if data is missing
        if not button_clicked and (not tech_indicators_data or not options_chain_data or not selected_symbol):
            logger.info("Non-button trigger with missing data, silently returning")
            return dash.no_update, dash.no_update, dash.no_update
        
        try:
            # Get the symbol and underlying price
            symbol = selected_symbol.get("symbol", "")
            underlying_price = options_chain_data.get("underlyingPrice", 0)
            logger.info(f"Processing recommendations for symbol: {symbol}, underlying price: {underlying_price}")
            
            if not symbol or not underlying_price:
                error_msg = f"Missing symbol or price data. Please refresh data."
                logger.warning(f"{error_msg} symbol={symbol}, underlying_price={underlying_price}")
                
                # Return error to status only, with no update to error-store
                return None, error_msg, dash.no_update
            
            # Get technical indicators for the selected timeframe
            tech_indicators_df = pd.DataFrame()
            if tech_indicators_data and "timeframe_data" in tech_indicators_data:
                timeframe_data = tech_indicators_data.get("timeframe_data", {})
                logger.info(f"Available timeframes in tech_indicators_data: {list(timeframe_data.keys())}")
                if timeframe in timeframe_data:
                    tech_indicators_df = pd.DataFrame(timeframe_data[timeframe])
                    logger.info(f"Loaded technical indicators for {timeframe}, shape: {tech_indicators_df.shape}")
                    logger.info(f"Technical indicators columns: {tech_indicators_df.columns.tolist()}")
                else:
                    logger.warning(f"Timeframe {timeframe} not found in available timeframes")
            else:
                logger.warning("No timeframe_data found in tech_indicators_data")
            
            if tech_indicators_df.empty:
                error_msg = f"No technical indicator data available for {timeframe} timeframe. Try a different timeframe or refresh data."
                logger.warning(error_msg)
                
                # Return error to status only, with no update to error-store
                return None, error_msg, dash.no_update
            
            # Get options chain data
            options_df = pd.DataFrame()
            if options_chain_data and "options" in options_chain_data:
                options_df = pd.DataFrame(options_chain_data["options"])
                logger.info(f"Loaded options chain data, shape: {options_df.shape}")
                logger.info(f"Options chain columns: {options_df.columns.tolist()}")
                logger.info(f"Options chain putCall values: {options_df['putCall'].unique().tolist() if 'putCall' in options_df.columns else 'putCall column not found'}")
            else:
                logger.warning("No options key found in options_chain_data")
            
            if options_df.empty:
                error_msg = "No options chain data available. Please refresh data."
                logger.warning(error_msg)
                
                # Return error to status only, with no update to error-store
                return None, error_msg, dash.no_update
            
            # Generate recommendations
            logger.info("Creating recommendation engine instance")
            engine = RecommendationEngine()
            
            logger.info(f"Calling get_recommendations with timeframe: {timeframe}")
            recommendations = engine.get_recommendations(
                tech_indicators_df,
                options_df,
                underlying_price,
                timeframe
            )
            
            # Log the structure of recommendations
            logger.info(f"Recommendation keys: {list(recommendations.keys())}")
            logger.info(f"Number of call recommendations: {len(recommendations.get('calls', []))}")
            logger.info(f"Number of put recommendations: {len(recommendations.get('puts', []))}")
            logger.info(f"Market direction: {recommendations.get('market_direction', {}).get('direction', 'unknown')}")
            
            # Add timestamp
            recommendations["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            success_msg = f"Recommendations updated for {symbol} ({timeframe})"
            # Return success with no update to error-store
            return recommendations, success_msg, dash.no_update
            
        except Exception as e:
            error_msg = f"Error generating recommendations: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Return error to status only, with no update to error-store
            return None, error_msg, dash.no_update
    
    # Second callback: Update error store based on recommendation status
    @app.callback(
        Output("error-store", "data"),
        Input("recommendation-status", "children"),
        prevent_initial_call=True
    )
    def update_error_store(status_message):
        """Update error store based on recommendation status message."""
        if not status_message:
            return dash.no_update
            
        # Check if status message indicates an error
        if status_message.startswith("Error") or "Missing" in status_message or "No " in status_message:
            return {
                "source": "Recommendations",
                "message": status_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # If not an error, don't update the error store
        return dash.no_update
    
    # Third callback: Update recommendation UI
    @app.callback(
        [
            Output("market-direction-indicator", "children"),
            Output("market-direction-text", "children"),
            Output("bullish-score", "children"),
            Output("bearish-score", "children"),
            Output("market-signals", "children"),
            Output("call-recommendations-table", "data"),
            Output("put-recommendations-table", "data"),
            Output("recommendations-last-updated", "children")
        ],
        [
            Input("recommendations-store", "data")
        ]
    )
    def update_recommendation_ui(recommendations_data):
        """Update the recommendation UI with the latest data."""
        logger.info(f"update_recommendation_ui called with data: {recommendations_data is not None}")
        
        if not recommendations_data:
            logger.warning("No recommendations data available")
            return (
                "N/A", "No data", "N/A", "N/A", 
                "No signals available", [], [], 
                "Last updated: Never"
            )
        
        try:
            # Log the structure of the recommendations data
            logger.info(f"Recommendations data keys: {list(recommendations_data.keys())}")
            
            # Extract market direction data
            market_direction = recommendations_data.get("market_direction", {})
            logger.info(f"Market direction data: {market_direction}")
            
            direction = market_direction.get("direction", "neutral")
            bullish_score = market_direction.get("bullish_score", 50)
            bearish_score = market_direction.get("bearish_score", 50)
            signals = market_direction.get("signals", [])
            
            logger.info(f"Direction: {direction}, Bullish: {bullish_score}, Bearish: {bearish_score}")
            logger.info(f"Number of signals: {len(signals)}")
            
            # Create direction indicator
            if direction == "bullish":
                direction_indicator = "▲"
                direction_text = "BULLISH"
                direction_class = "bullish"
            elif direction == "bearish":
                direction_indicator = "▼"
                direction_text = "BEARISH"
                direction_class = "bearish"
            else:
                direction_indicator = "◆"
                direction_text = "NEUTRAL"
                direction_class = "neutral"
            
            # Format scores
            bullish_score_text = f"{bullish_score}%"
            bearish_score_text = f"{bearish_score}%"
            
            # Format signals
            signals_html = []
            if signals:
                for signal in signals:
                    signal_type = signal.get("type", "")
                    signal_direction = signal.get("direction", "")
                    signal_strength = signal.get("strength", "")
                    signal_text = f"{signal_type}: {signal_direction} ({signal_strength})"
                    signals_html.append(html.Div(signal_text, className=f"signal {signal_direction.lower()}"))
                signals_content = html.Div(signals_html, className="signals-list")
            else:
                signals_content = "No significant signals detected"
            
            # Extract recommendations
            call_recommendations = recommendations_data.get("calls", [])
            put_recommendations = recommendations_data.get("puts", [])
            
            # Format timestamp
            timestamp = recommendations_data.get("timestamp", "Unknown")
            last_updated = f"Last updated: {timestamp}"
            
            return (
                direction_indicator,
                direction_text,
                bullish_score_text,
                bearish_score_text,
                signals_content,
                call_recommendations,
                put_recommendations,
                last_updated
            )
            
        except Exception as e:
            logger.error(f"Error updating recommendation UI: {str(e)}", exc_info=True)
            return (
                "Error", "Error", "Error", "Error",
                f"Error: {str(e)}", [], [],
                "Last updated: Error"
            )
    
    # Fourth callback: Update contract details when a recommendation is clicked
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
        ]
    )
    def update_contract_details(call_active_cell, put_active_cell, call_data, put_data):
        """Update contract details when a recommendation is clicked."""
        ctx = dash.callback_context
        trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
        
        # Default values
        empty_details = ("", "", "", "", "", "", "", "", "")
        
        if not trigger:
            return empty_details
        
        try:
            if "call-recommendations-table" in trigger and call_active_cell:
                row = call_active_cell['row']
                if row < len(call_data):
                    contract = call_data[row]
                    contract_type = "CALL"
                else:
                    return empty_details
            elif "put-recommendations-table" in trigger and put_active_cell:
                row = put_active_cell['row']
                if row < len(put_data):
                    contract = put_data[row]
                    contract_type = "PUT"
                else:
                    return empty_details
            else:
                return empty_details
            
            # Extract contract details
            symbol = contract.get("symbol", "")
            strike = f"${contract.get('strikePrice', 0):.2f}"
            expiration = contract.get("expirationDate", "")
            
            # Extract greeks
            delta = f"{contract.get('delta', 0):.4f}"
            gamma = f"{contract.get('gamma', 0):.4f}"
            theta = f"{contract.get('theta', 0):.4f}"
            vega = f"{contract.get('vega', 0):.4f}"
            iv = f"{contract.get('impliedVolatility', 0) * 100:.2f}%"
            
            return (symbol, contract_type, strike, expiration, delta, gamma, theta, vega, iv)
            
        except Exception as e:
            logger.error(f"Error updating contract details: {str(e)}", exc_info=True)
            return empty_details

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
import json
from dashboard_utils.data_quality_display import create_data_quality_display

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
            
            # Data Quality Panel (New)
            create_data_quality_display(),
            
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
            ], className="panel details-panel"),
            
            # Debug Information Panel
            html.Div([
                html.H3("Recommendation Debug Information", className="panel-header"),
                html.Div(id="recommendation-debug-info", 
                         className="debug-info",
                         style={'whiteSpace': 'pre-wrap', 'fontFamily': 'monospace', 'fontSize': '12px', 'overflowX': 'auto'})
            ], className="panel debug-panel", style={'marginTop': '20px', 'padding': '10px', 'border': '1px solid #ddd'})
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
            Output("recommendation-debug-info", "children"),
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
        
        # Initialize debug information
        debug_info = []
        debug_info.append(f"=== RECOMMENDATION GENERATION DEBUG LOG ===")
        debug_info.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
        
        ctx = dash.callback_context
        trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
        debug_info.append(f"Trigger: {trigger}")
        logger.info(f"update_recommendations triggered by: {trigger}")
        
        # Check if this was triggered by the button click
        button_clicked = "generate-recommendations-button" in trigger
        debug_info.append(f"Button clicked: {button_clicked}")
        if button_clicked:
            debug_info.append(f"Generate Recommendations button clicked, n_clicks: {n_clicks}")
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
                debug_info.append(f"ERROR: {error_msg}")
                logger.warning(error_msg)
                
                # Return error to status only, with no update to error-store
                return None, error_msg, "\n".join(debug_info), dash.no_update
        
        # For non-button triggers, silently return if data is missing
        if not button_clicked and (not tech_indicators_data or not options_chain_data or not selected_symbol):
            debug_info.append("Non-button trigger with missing data, silently returning")
            logger.info("Non-button trigger with missing data, silently returning")
            return dash.no_update, dash.no_update, "\n".join(debug_info), dash.no_update
        
        try:
            # Get the symbol and underlying price
            # Handle both dictionary and string types for selected_symbol
            if isinstance(selected_symbol, dict):
                symbol = selected_symbol.get("symbol", "")
                debug_info.append(f"Selected symbol is a dictionary, extracted symbol: {symbol}")
            else:
                symbol = selected_symbol
                debug_info.append(f"Selected symbol is a string: {symbol}")
            
            underlying_price = options_chain_data.get("underlyingPrice", 0)
            debug_info.append(f"Symbol: {symbol}, Underlying price: {underlying_price}")
            logger.info(f"Processing recommendations for symbol: {symbol}, underlying price: {underlying_price}")
            
            if not symbol or not underlying_price:
                error_msg = f"Missing symbol or price data. Please refresh data."
                debug_info.append(f"ERROR: {error_msg}")
                logger.warning(f"{error_msg} symbol={symbol}, underlying_price={underlying_price}")
                
                # Return error to status only, with no update to error-store
                return None, error_msg, "\n".join(debug_info), dash.no_update
            
            # Get technical indicators for the selected timeframe
            tech_indicators_df = pd.DataFrame()
            if tech_indicators_data and "timeframe_data" in tech_indicators_data:
                timeframe_data = tech_indicators_data.get("timeframe_data", {})
                debug_info.append(f"Available timeframes: {list(timeframe_data.keys())}")
                logger.info(f"Available timeframes in tech_indicators_data: {list(timeframe_data.keys())}")
                if timeframe in timeframe_data:
                    tech_indicators_df = pd.DataFrame(timeframe_data[timeframe])
                    debug_info.append(f"Loaded technical indicators for {timeframe}, shape: {tech_indicators_df.shape}")
                    debug_info.append(f"Technical indicators columns: {tech_indicators_df.columns.tolist()}")
                    logger.info(f"Loaded technical indicators for {timeframe}, shape: {tech_indicators_df.shape}")
                    logger.info(f"Technical indicators columns: {tech_indicators_df.columns.tolist()}")
                else:
                    debug_info.append(f"WARNING: Timeframe {timeframe} not found in available timeframes")
                    logger.warning(f"Timeframe {timeframe} not found in available timeframes")
            else:
                debug_info.append("WARNING: No timeframe_data found in tech_indicators_data")
                logger.warning("No timeframe_data found in tech_indicators_data")
            
            # Create technical indicators dictionary with all available timeframes
            tech_indicators_dict = {}
            if tech_indicators_data and "timeframe_data" in tech_indicators_data:
                for tf, data in tech_indicators_data.get("timeframe_data", {}).items():
                    tech_indicators_dict[tf] = pd.DataFrame(data)
                    debug_info.append(f"Added {tf} to tech_indicators_dict, shape: {tech_indicators_dict[tf].shape}")
            
            # Get options chain data
            options_df = pd.DataFrame()
            if options_chain_data and "options" in options_chain_data:
                options_df = pd.DataFrame(options_chain_data["options"])
                debug_info.append(f"Loaded options chain data, shape: {options_df.shape}")
                debug_info.append(f"Options chain columns: {options_df.columns.tolist()}")
                logger.info(f"Loaded options chain data, shape: {options_df.shape}")
                logger.info(f"Options chain columns: {options_df.columns.tolist()}")
            else:
                debug_info.append("WARNING: No options data found in options_chain_data")
                logger.warning("No options data found in options_chain_data")
            
            # Generate recommendations
            engine = RecommendationEngine()
            debug_info.append("Calling recommendation engine generate_recommendations method")
            recommendations = engine.generate_recommendations(tech_indicators_dict, options_df, underlying_price, symbol)
            
            # Extract data quality information
            data_quality = recommendations.get("data_quality", {})
            tech_quality = data_quality.get("technical_indicators", {}).get("score", 0)
            options_quality = data_quality.get("options_chain", {}).get("score", 0)
            overall_quality = data_quality.get("overall_score", 0)
            
            debug_info.append(f"Data quality scores - Tech: {tech_quality}, Options: {options_quality}, Overall: {overall_quality}")
            
            # Check if we have valid recommendations
            recommendation_list = recommendations.get("recommendations", [])
            debug_info.append(f"Generated {len(recommendation_list)} recommendations")
            
            # Determine status message based on data quality and recommendations
            if len(recommendation_list) == 0:
                if overall_quality < 40:
                    status_msg = f"No recommendations available - Poor data quality ({overall_quality:.0f}/100)"
                else:
                    status_msg = "No recommendations available for current market conditions"
            else:
                if overall_quality < 40:
                    status_msg = f"Low confidence recommendations - Poor data quality ({overall_quality:.0f}/100)"
                elif overall_quality < 60:
                    status_msg = f"Recommendations available - Fair data quality ({overall_quality:.0f}/100)"
                else:
                    status_msg = f"Recommendations available - Good data quality ({overall_quality:.0f}/100)"
            
            debug_info.append(f"Status message: {status_msg}")
            
            # Return the recommendations data, status message, and debug info
            return recommendations, status_msg, "\n".join(debug_info), dash.no_update
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            error_msg = f"Error generating recommendations: {str(e)}"
            debug_info.append(f"ERROR: {error_msg}")
            debug_info.append(error_details)
            logger.error(f"Error in update_recommendations: {str(e)}")
            logger.error(error_details)
            
            # Return error to both status and error-store
            return None, error_msg, "\n".join(debug_info), {"error": error_msg, "details": error_details}
    
    # Second callback: Update market direction display
    @app.callback(
        [
            Output("market-direction-indicator", "children"),
            Output("market-direction-indicator", "className"),
            Output("market-direction-text", "children"),
            Output("bullish-score", "children"),
            Output("bearish-score", "children"),
            Output("market-signals", "children")
        ],
        [Input("recommendations-store", "data")],
        prevent_initial_call=True
    )
    def update_market_direction(recommendations_data):
        """Update market direction display based on recommendations data."""
        if not recommendations_data or "market_direction" not in recommendations_data:
            # Default values when no data is available
            return (
                "?", "direction-indicator neutral", "No Data",
                "N/A", "N/A", "No market signals available"
            )
        
        try:
            # Extract market direction data
            market_direction = recommendations_data["market_direction"]
            direction = market_direction.get("direction", "neutral")
            bullish_score = market_direction.get("bullish_score", 50)
            bearish_score = market_direction.get("bearish_score", 50)
            signals = market_direction.get("signals", [])
            
            # Determine direction indicator and class
            if direction == "bullish":
                indicator = "▲"
                indicator_class = "direction-indicator bullish"
                direction_text = "Bullish"
            elif direction == "bearish":
                indicator = "▼"
                indicator_class = "direction-indicator bearish"
                direction_text = "Bearish"
            else:
                indicator = "◆"
                indicator_class = "direction-indicator neutral"
                direction_text = "Neutral"
            
            # Format signals as a list
            signals_html = html.Ul([html.Li(signal) for signal in signals]) if signals else "No signals available"
            
            return (
                indicator, indicator_class, direction_text,
                f"{bullish_score:.0f}", f"{bearish_score:.0f}", signals_html
            )
        
        except Exception as e:
            logger.error(f"Error updating market direction: {e}")
            return (
                "!", "direction-indicator error", f"Error: {str(e)}",
                "Error", "Error", f"Error: {str(e)}"
            )
    
    # Third callback: Update call recommendations table
    @app.callback(
        Output("call-recommendations-table", "data"),
        [Input("recommendations-store", "data")],
        prevent_initial_call=True
    )
    def update_call_recommendations(recommendations_data):
        """Update call recommendations table based on recommendations data."""
        if not recommendations_data or "recommendations" not in recommendations_data:
            return []
        
        try:
            # Extract recommendations
            recommendations = recommendations_data["recommendations"]
            
            # Filter for call recommendations
            call_recommendations = [r for r in recommendations if r.get("type") == "CALL"]
            
            # Format for data table
            table_data = []
            for rec in call_recommendations:
                table_data.append({
                    "symbol": rec.get("symbol", ""),
                    "strikePrice": rec.get("strike", 0),
                    "expirationDate": rec.get("expiration", ""),
                    "daysToExpiration": rec.get("days_to_expiration", 0),
                    "currentPrice": rec.get("current_price", 0),
                    "targetSellPrice": rec.get("current_price", 0) * (1 + rec.get("expected_profit", 0) / 100),
                    "targetTimeframeHours": rec.get("target_exit_hours", 24),
                    "expectedProfitPct": rec.get("expected_profit", 0),
                    "confidenceScore": rec.get("confidence", 0)
                })
            
            return table_data
        
        except Exception as e:
            logger.error(f"Error updating call recommendations: {e}")
            return []
    
    # Fourth callback: Update put recommendations table
    @app.callback(
        Output("put-recommendations-table", "data"),
        [Input("recommendations-store", "data")],
        prevent_initial_call=True
    )
    def update_put_recommendations(recommendations_data):
        """Update put recommendations table based on recommendations data."""
        if not recommendations_data or "recommendations" not in recommendations_data:
            return []
        
        try:
            # Extract recommendations
            recommendations = recommendations_data["recommendations"]
            
            # Filter for put recommendations
            put_recommendations = [r for r in recommendations if r.get("type") == "PUT"]
            
            # Format for data table
            table_data = []
            for rec in put_recommendations:
                table_data.append({
                    "symbol": rec.get("symbol", ""),
                    "strikePrice": rec.get("strike", 0),
                    "expirationDate": rec.get("expiration", ""),
                    "daysToExpiration": rec.get("days_to_expiration", 0),
                    "currentPrice": rec.get("current_price", 0),
                    "targetSellPrice": rec.get("current_price", 0) * (1 + rec.get("expected_profit", 0) / 100),
                    "targetTimeframeHours": rec.get("target_exit_hours", 24),
                    "expectedProfitPct": rec.get("expected_profit", 0),
                    "confidenceScore": rec.get("confidence", 0)
                })
            
            return table_data
        
        except Exception as e:
            logger.error(f"Error updating put recommendations: {e}")
            return []
    
    # Fifth callback: Update last updated timestamp
    @app.callback(
        Output("recommendations-last-updated", "children"),
        [Input("recommendations-store", "data")],
        prevent_initial_call=True
    )
    def update_last_updated(recommendations_data):
        """Update last updated timestamp based on recommendations data."""
        if recommendations_data:
            return f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return "Not yet updated"
    
    # Register data quality callbacks
    from dashboard_utils.data_quality_display import register_data_quality_callbacks
    register_data_quality_callbacks(app)

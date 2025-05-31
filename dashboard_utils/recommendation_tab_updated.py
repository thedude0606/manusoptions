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
from dashboard_utils.confidence_scoring import ConfidenceScorer

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
            
            # Confidence Score Panel (New)
            html.Div([
                html.H3("Confidence Metrics", className="panel-header"),
                html.Div([
                    html.Div([
                        html.Label("Overall Confidence:"),
                        html.Div(id="overall-confidence", className="confidence-value")
                    ], className="confidence-item"),
                    html.Div([
                        html.Label("Technical Score:"),
                        html.Div(id="technical-confidence", className="confidence-value")
                    ], className="confidence-item"),
                    html.Div([
                        html.Label("Options Score:"),
                        html.Div(id="options-confidence", className="confidence-value")
                    ], className="confidence-item"),
                    html.Div([
                        html.Label("Market Score:"),
                        html.Div(id="market-confidence", className="confidence-value")
                    ], className="confidence-item")
                ], className="confidence-metrics")
            ], className="panel confidence-panel"),
            
            # Data Quality Panel
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
        from dashboard_utils.confidence_scoring import ConfidenceScorer
        
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
                
                # Return error to status only, with no update to error store
                return None, error_msg, "\n".join(debug_info), dash.no_update
        else:
            # If not triggered by button click, don't update
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        try:
            # Extract symbol from selected_symbol_store
            symbol = selected_symbol.get("symbol", "").upper()
            debug_info.append(f"Symbol: {symbol}")
            
            # Filter technical indicators for the selected timeframe
            if tech_indicators_data:
                tech_indicators_df = pd.DataFrame(tech_indicators_data)
                debug_info.append(f"Technical indicators data shape: {tech_indicators_df.shape}")
                
                # Filter by timeframe
                tech_indicators_df = tech_indicators_df[tech_indicators_df['timeframe'] == timeframe]
                debug_info.append(f"Filtered technical indicators for timeframe {timeframe}, shape: {tech_indicators_df.shape}")
                
                # Sort by timestamp (most recent first)
                if 'timestamp' in tech_indicators_df.columns:
                    tech_indicators_df['timestamp'] = pd.to_datetime(tech_indicators_df['timestamp'])
                    tech_indicators_df = tech_indicators_df.sort_values('timestamp', ascending=False)
                    debug_info.append(f"Sorted technical indicators by timestamp")
            else:
                tech_indicators_df = pd.DataFrame()
                debug_info.append(f"No technical indicators data available")
            
            # Convert options chain data to DataFrame
            if options_chain_data and "options" in options_chain_data:
                options_df = pd.DataFrame(options_chain_data["options"])
                debug_info.append(f"Options chain data shape: {options_df.shape}")
            else:
                options_df = pd.DataFrame()
                debug_info.append(f"No options chain data available")
            
            # Initialize the recommendation engine
            engine = RecommendationEngine()
            debug_info.append(f"Initialized RecommendationEngine")
            
            # Initialize the confidence scorer
            confidence_scorer = ConfidenceScorer()
            debug_info.append(f"Initialized ConfidenceScorer")
            
            # Analyze market direction
            market_analysis = engine.analyze_market_direction(tech_indicators_df, timeframe=timeframe)
            debug_info.append(f"Market direction analysis: {market_analysis['direction']} (Bullish: {market_analysis['bullish_score']}, Bearish: {market_analysis['bearish_score']})")
            debug_info.append(f"Market signals: {', '.join(market_analysis['signals'][:5])}...")
            
            # Get underlying price
            underlying_price = options_chain_data.get("underlyingPrice", 0)
            debug_info.append(f"Underlying price: {underlying_price}")
            
            # Evaluate options chain
            options_evaluation = engine.evaluate_options_chain(options_df, market_analysis, underlying_price, symbol)
            debug_info.append(f"Options evaluation complete. Found {len(options_evaluation.get('call_contracts', []))} call contracts and {len(options_evaluation.get('put_contracts', []))} put contracts")
            
            # Calculate confidence scores
            confidence_result = confidence_scorer.calculate_confidence(
                technical_indicators=tech_indicators_df.to_dict('records') if not tech_indicators_df.empty else {},
                options_data=options_df,
                market_data={"direction": market_analysis["direction"]}
            )
            debug_info.append(f"Confidence calculation complete. Overall confidence: {confidence_result['overall_confidence']}")
            
            # Generate recommendations
            recommendations = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "timeframe": timeframe,
                "market_direction": market_analysis,
                "confidence_scores": confidence_result,
                "call_recommendations": options_evaluation.get("call_contracts", []),
                "put_recommendations": options_evaluation.get("put_contracts", [])
            }
            
            # Add detailed explanation for each recommendation
            for rec_type in ["call_recommendations", "put_recommendations"]:
                for i, rec in enumerate(recommendations[rec_type]):
                    # Add confidence score from confidence_result
                    rec["confidenceScore"] = confidence_result["overall_confidence"]
                    
                    # Add explanation based on signals
                    signals = market_analysis["signals"][:3]  # Take top 3 signals
                    rec["explanation"] = f"Based on {', '.join(signals)}"
                    
                    # Add profit target based on confidence
                    profit_target = confidence_result["profit_target_pct"]
                    rec["expectedProfitPct"] = profit_target
                    
                    # Calculate target price
                    current_price = rec.get("currentPrice", rec.get("lastPrice", 0))
                    if rec_type == "call_recommendations":
                        rec["targetSellPrice"] = round(current_price * (1 + profit_target/100), 2)
                    else:
                        rec["targetSellPrice"] = round(current_price * (1 - profit_target/100), 2)
                    
                    # Add target timeframe in hours
                    rec["targetTimeframeHours"] = confidence_result["max_hold_time_minutes"] / 60
            
            debug_info.append(f"Generated {len(recommendations['call_recommendations'])} call recommendations and {len(recommendations['put_recommendations'])} put recommendations")
            
            # Return the recommendations data
            status_message = f"Generated recommendations for {symbol} ({timeframe})"
            logger.info(status_message)
            
            return recommendations, status_message, "\n".join(debug_info), None
            
        except Exception as e:
            error_msg = f"Error generating recommendations: {str(e)}"
            debug_info.append(f"ERROR: {error_msg}")
            logger.error(error_msg, exc_info=True)
            return None, error_msg, "\n".join(debug_info), {"error": error_msg}
    
    # Second callback: Update recommendation display
    @app.callback(
        [
            Output("market-direction-indicator", "children"),
            Output("market-direction-indicator", "style"),
            Output("market-direction-text", "children"),
            Output("bullish-score", "children"),
            Output("bearish-score", "children"),
            Output("market-signals", "children"),
            Output("call-recommendations-table", "data"),
            Output("put-recommendations-table", "data"),
            Output("recommendations-last-updated", "children"),
            Output("overall-confidence", "children"),
            Output("technical-confidence", "children"),
            Output("options-confidence", "children"),
            Output("market-confidence", "children")
        ],
        [Input("recommendations-store", "data")],
        prevent_initial_call=True
    )
    def update_recommendation_display(recommendations_data):
        """Update the recommendation display with the latest data."""
        if not recommendations_data:
            return (
                "?", {}, "No Data", "N/A", "N/A", "No signals available",
                [], [], "Not updated yet", "N/A", "N/A", "N/A", "N/A"
            )
        
        try:
            # Extract market direction data
            market_direction = recommendations_data.get("market_direction", {})
            direction = market_direction.get("direction", "neutral")
            bullish_score = market_direction.get("bullish_score", 0)
            bearish_score = market_direction.get("bearish_score", 0)
            signals = market_direction.get("signals", [])
            
            # Extract confidence scores
            confidence_scores = recommendations_data.get("confidence_scores", {})
            overall_confidence = confidence_scores.get("overall_confidence", 0)
            technical_score = confidence_scores.get("technical_score", 0)
            options_score = confidence_scores.get("options_score", 0)
            market_score = confidence_scores.get("market_score", 0)
            
            # Set direction indicator
            if direction == "bullish":
                direction_indicator = "▲"
                direction_style = {"color": "green", "fontSize": "24px"}
                direction_text = "Bullish"
            elif direction == "bearish":
                direction_indicator = "▼"
                direction_style = {"color": "red", "fontSize": "24px"}
                direction_text = "Bearish"
            else:
                direction_indicator = "◆"
                direction_style = {"color": "gray", "fontSize": "24px"}
                direction_text = "Neutral"
            
            # Format signals as bullet points
            signals_html = [html.Li(signal) for signal in signals[:5]]  # Show top 5 signals
            if len(signals) > 5:
                signals_html.append(html.Li(f"... and {len(signals) - 5} more"))
            
            # Get recommendations
            call_recommendations = recommendations_data.get("call_recommendations", [])
            put_recommendations = recommendations_data.get("put_recommendations", [])
            
            # Format timestamp
            timestamp = recommendations_data.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    formatted_timestamp = f"Last updated: {dt.strftime('%Y-%m-%d %H:%M:%S')}"
                except:
                    formatted_timestamp = f"Last updated: {timestamp}"
            else:
                formatted_timestamp = "Last updated: Unknown"
            
            # Format confidence scores with color coding
            def format_confidence(score):
                if score >= 80:
                    color = "green"
                elif score >= 60:
                    color = "darkgreen"
                elif score >= 40:
                    color = "orange"
                else:
                    color = "red"
                return html.Span(f"{score:.1f}", style={"color": color, "fontWeight": "bold"})
            
            return (
                direction_indicator, direction_style, direction_text,
                f"{bullish_score:.1f}", f"{bearish_score:.1f}",
                html.Ul(signals_html),
                call_recommendations, put_recommendations, formatted_timestamp,
                format_confidence(overall_confidence),
                format_confidence(technical_score),
                format_confidence(options_score),
                format_confidence(market_score)
            )
            
        except Exception as e:
            logger.error(f"Error updating recommendation display: {e}", exc_info=True)
            return (
                "!", {"color": "red"}, "Error", "N/A", "N/A", f"Error: {str(e)}",
                [], [], "Error updating display", "N/A", "N/A", "N/A", "N/A"
            )
    
    # Third callback: Update contract details when a recommendation is clicked
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
        """Update the contract details when a recommendation is clicked."""
        ctx = dash.callback_context
        trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
        
        # Default values
        default_values = ["N/A"] * 9
        
        if not trigger:
            return default_values
        
        try:
            if "call-recommendations-table" in trigger and call_active_cell:
                row = call_active_cell['row']
                if row < len(call_data):
                    contract = call_data[row]
                    contract_type = "CALL"
                else:
                    return default_values
            elif "put-recommendations-table" in trigger and put_active_cell:
                row = put_active_cell['row']
                if row < len(put_data):
                    contract = put_data[row]
                    contract_type = "PUT"
                else:
                    return default_values
            else:
                return default_values
            
            # Extract contract details
            symbol = contract.get("symbol", "N/A")
            strike = f"${contract.get('strikePrice', 0):.2f}"
            expiration = contract.get("expirationDate", "N/A")
            
            # Format Greeks
            delta = f"{contract.get('delta', 0):.4f}"
            gamma = f"{contract.get('gamma', 0):.4f}"
            theta = f"{contract.get('theta', 0):.4f}"
            vega = f"{contract.get('vega', 0):.4f}"
            iv = f"{contract.get('volatility', 0) * 100:.2f}%"
            
            return symbol, contract_type, strike, expiration, delta, gamma, theta, vega, iv
            
        except Exception as e:
            logger.error(f"Error updating contract details: {e}", exc_info=True)
            return default_values

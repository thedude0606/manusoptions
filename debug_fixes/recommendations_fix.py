"""
Fix for recommendations tab functionality issue.

This module contains enhanced versions of the recommendations tab handling functions
with improved error handling, debugging, and callback registration.
"""

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import logging
import traceback
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def register_recommendation_callbacks_enhanced(app):
    """
    Enhanced version of register_recommendation_callbacks with better error handling and debugging.
    
    Args:
        app: The Dash app instance
    """
    logger.info("Registering enhanced recommendation callbacks")
    
    @app.callback(
        [
            Output("recommendations-store", "data"),
            Output("recommendation-status", "children"),
            Output("error-store", "data")  # Added to capture errors
        ],
        [
            Input("generate-recommendations-button", "n_clicks"),
            Input("tech-indicators-store", "data"),
            Input("options-chain-store", "data"),
            Input("recommendation-timeframe-dropdown", "value")
        ],
        [
            State("selected-symbol-store", "data"),
            State("error-store", "data")
        ],
        prevent_initial_call=True
    )
    def update_recommendations_enhanced(n_clicks, tech_indicators_data, options_chain_data, 
                                       timeframe, selected_symbol, current_error):
        """Enhanced update recommendations callback with better error handling and debugging."""
        start_time = time.time()
        
        # Get callback context to determine what triggered the callback
        ctx = dash.callback_context
        trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
        logger.info(f"update_recommendations_enhanced triggered by: {trigger}")
        
        # Check if this was triggered by the button click
        button_clicked = "generate-recommendations-button" in trigger
        if button_clicked:
            logger.info(f"Generate Recommendations button clicked, n_clicks: {n_clicks}")
        
        # Debug log the input data availability
        logger.debug(f"Input data availability: tech_indicators_data={bool(tech_indicators_data)}, "
                    f"options_chain_data={bool(options_chain_data)}, "
                    f"selected_symbol={bool(selected_symbol)}, "
                    f"timeframe={timeframe}")
        
        # Initialize error data
        error_data = current_error or {}
        
        if not tech_indicators_data or not options_chain_data or not selected_symbol:
            logger.warning("Missing required data for recommendations")
            return None, "Please load symbol data first.", {
                "source": "Recommendations",
                "message": "Missing required data for recommendations",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        try:
            # Import here to avoid circular imports
            from recommendation_engine import RecommendationEngine
            
            # Get the symbol and underlying price
            symbol = selected_symbol.get("symbol", "")
            underlying_price = options_chain_data.get("underlyingPrice", 0)
            logger.info(f"Processing recommendations for symbol: {symbol}, underlying price: {underlying_price}")
            
            if not symbol or not underlying_price:
                logger.warning(f"Missing symbol or price data: symbol={symbol}, underlying_price={underlying_price}")
                return None, "Missing symbol or price data.", {
                    "source": "Recommendations",
                    "message": f"Missing symbol or price data: symbol={symbol}, underlying_price={underlying_price}",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # Get technical indicators for the selected timeframe
            tech_indicators_df = pd.DataFrame()
            if tech_indicators_data and "timeframe_data" in tech_indicators_data:
                timeframe_data = tech_indicators_data.get("timeframe_data", {})
                logger.info(f"Available timeframes in tech_indicators_data: {list(timeframe_data.keys())}")
                
                # Debug log the timeframe data structure
                for tf, data in timeframe_data.items():
                    logger.debug(f"Timeframe {tf} has {len(data)} records")
                
                if timeframe in timeframe_data:
                    tech_indicators_df = pd.DataFrame(timeframe_data[timeframe])
                    logger.info(f"Loaded technical indicators for {timeframe}, shape: {tech_indicators_df.shape}")
                    logger.debug(f"Technical indicators columns: {tech_indicators_df.columns.tolist()}")
                else:
                    logger.warning(f"Timeframe {timeframe} not found in available timeframes")
            else:
                logger.warning("No timeframe_data found in tech_indicators_data")
            
            if tech_indicators_df.empty:
                logger.warning(f"Empty technical indicators DataFrame for {timeframe} timeframe")
                return None, f"No technical indicator data available for {timeframe} timeframe.", {
                    "source": "Recommendations",
                    "message": f"No technical indicator data available for {timeframe} timeframe",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # Get options chain data
            options_df = pd.DataFrame()
            if options_chain_data and "options" in options_chain_data:
                options_df = pd.DataFrame(options_chain_data["options"])
                logger.info(f"Loaded options chain data, shape: {options_df.shape}")
                logger.debug(f"Options chain columns: {options_df.columns.tolist()}")
            
            if options_df.empty:
                logger.warning("Empty options chain DataFrame")
                return None, "No options chain data available.", {
                    "source": "Recommendations",
                    "message": "No options chain data available",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # Create recommendation engine
            engine = RecommendationEngine(symbol, underlying_price)
            
            # Generate recommendations
            logger.info("Generating recommendations...")
            recommendations = engine.generate_recommendations(tech_indicators_df, options_df, timeframe)
            
            # Log recommendation results
            call_count = len(recommendations.get("calls", []))
            put_count = len(recommendations.get("puts", []))
            logger.info(f"Generated {call_count} call and {put_count} put recommendations")
            
            # Create recommendations store data
            recommendations_data = {
                "symbol": symbol,
                "timeframe": timeframe,
                "calls": recommendations.get("calls", []),
                "puts": recommendations.get("puts", []),
                "market_direction": recommendations.get("market_direction", {}),
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            logger.info(f"Recommendations generated in {elapsed_time:.2f} seconds")
            
            return recommendations_data, f"Recommendations updated at {time.strftime('%H:%M:%S')}", None
            
        except Exception as e:
            error_msg = f"Error generating recommendations: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            return None, f"Error: {str(e)}", {
                "source": "Recommendations",
                "message": error_msg,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "traceback": traceback.format_exc()
            }
    
    @app.callback(
        [
            Output("call-recommendations-table", "data"),
            Output("put-recommendations-table", "data"),
            Output("market-direction-indicator", "children"),
            Output("market-direction-text", "children"),
            Output("bullish-score", "children"),
            Output("bearish-score", "children"),
            Output("recommendations-last-updated", "children")
        ],
        [
            Input("recommendations-store", "data")
        ],
        prevent_initial_call=True
    )
    def update_recommendation_tables_enhanced(recommendations_data):
        """Enhanced callback to update recommendation tables with better error handling."""
        logger.info("update_recommendation_tables_enhanced triggered")
        
        if not recommendations_data:
            logger.warning("No recommendations data available")
            return [], [], "", "", "", "", ""
        
        try:
            # Get call and put recommendations
            calls_data = recommendations_data.get("calls", [])
            puts_data = recommendations_data.get("puts", [])
            
            # Get market direction data
            market_direction = recommendations_data.get("market_direction", {})
            direction = market_direction.get("direction", "NEUTRAL")
            bullish_score = market_direction.get("bullish_score", 0)
            bearish_score = market_direction.get("bearish_score", 0)
            
            # Create direction indicator
            if direction == "BULLISH":
                direction_indicator = "▲"
                direction_text = "Bullish"
            elif direction == "BEARISH":
                direction_indicator = "▼"
                direction_text = "Bearish"
            else:
                direction_indicator = "◆"
                direction_text = "Neutral"
            
            # Format scores as percentages
            bullish_score_text = f"{bullish_score:.0f}%"
            bearish_score_text = f"{bearish_score:.0f}%"
            
            # Get last update timestamp
            last_updated = recommendations_data.get("last_update", "")
            last_updated_text = f"Last updated: {last_updated}" if last_updated else ""
            
            logger.info(f"Updating recommendation tables with {len(calls_data)} calls and {len(puts_data)} puts")
            
            return calls_data, puts_data, direction_indicator, direction_text, bullish_score_text, bearish_score_text, last_updated_text
            
        except Exception as e:
            error_msg = f"Error updating recommendation tables: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            return [], [], "", "", "", "", f"Error: {str(e)}"

"""
Modified recommendation tab callback integration with symbol context preservation.

This module updates the recommendation tab callbacks to integrate with
the symbol context manager, ensuring symbol context is preserved throughout
the data flow pipeline.
"""

import dash
from dash.dependencies import Input, Output, State
import pandas as pd
import logging
from datetime import datetime
from dashboard_utils.symbol_context_integration import (
    update_symbol_context,
    process_technical_indicators_data,
    process_options_chain_data,
    prepare_data_for_recommendation_engine
)

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def register_symbol_context_callbacks(app):
    """
    Register callbacks to maintain symbol context throughout the dashboard.
    
    Args:
        app: The Dash app instance
    """
    # Update symbol context when symbol is selected
    @app.callback(
        Output("symbol-context-store", "data"),
        [Input("selected-symbol-store", "data")],
        prevent_initial_call=True
    )
    def update_symbol_context_store(selected_symbol):
        """Update symbol context store when symbol is selected."""
        if not selected_symbol:
            logger.warning("No symbol selected for context store")
            return {"symbol": "", "timestamp": datetime.now().isoformat()}
        
        # Update symbol context
        symbol = update_symbol_context(selected_symbol)
        logger.info(f"Updated symbol context store with symbol: {symbol}")
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }
    
    # Process technical indicators data with symbol context
    @app.callback(
        Output("tech-indicators-context-store", "data"),
        [Input("tech-indicators-store", "data")],
        [State("symbol-context-store", "data")],
        prevent_initial_call=True
    )
    def process_tech_indicators_with_context(tech_indicators_data, symbol_context):
        """Process technical indicators data with symbol context."""
        if not tech_indicators_data or not symbol_context:
            logger.warning("Missing data for technical indicators context processing")
            return dash.no_update
        
        # Process technical indicators data with symbol context
        processed_data = process_technical_indicators_data(
            tech_indicators_data,
            symbol_context.get("symbol", "")
        )
        
        logger.info(f"Processed technical indicators data with symbol context: {symbol_context.get('symbol', '')}")
        return processed_data
    
    # Process options chain data with symbol context
    @app.callback(
        Output("options-chain-context-store", "data"),
        [Input("options-chain-store", "data")],
        [State("symbol-context-store", "data")],
        prevent_initial_call=True
    )
    def process_options_chain_with_context(options_chain_data, symbol_context):
        """Process options chain data with symbol context."""
        if not options_chain_data or not symbol_context:
            logger.warning("Missing data for options chain context processing")
            return dash.no_update
        
        # Process options chain data with symbol context
        processed_data = process_options_chain_data(
            options_chain_data,
            symbol_context.get("symbol", "")
        )
        
        logger.info(f"Processed options chain data with symbol context: {symbol_context.get('symbol', '')}")
        return processed_data

def modify_recommendation_callback(app):
    """
    Modify the recommendation callback to use symbol context integration.
    
    Args:
        app: The Dash app instance
    """
    # Override the existing recommendation callback
    @app.callback(
        [
            Output("recommendations-store", "data"),
            Output("recommendation-status", "children"),
            Output("recommendation-debug-info", "children"),
            Output("error-store", "data", allow_duplicate=True)
        ],
        [
            Input("generate-recommendations-button", "n_clicks"),
            Input("tech-indicators-context-store", "data"),
            Input("options-chain-context-store", "data"),
            Input("recommendation-timeframe-dropdown", "value"),
            Input("update-interval", "n_intervals")
        ],
        [
            State("symbol-context-store", "data")
        ],
        prevent_initial_call=True
    )
    def update_recommendations_with_context(n_clicks, tech_indicators_data, options_chain_data, timeframe, n_intervals, symbol_context):
        """Update recommendations with proper symbol context."""
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
        
        # Get symbol from context
        symbol = symbol_context.get("symbol", "") if symbol_context else ""
        debug_info.append(f"Symbol from context: {symbol}")
        
        if button_clicked:
            debug_info.append(f"Generate Recommendations button clicked, n_clicks: {n_clicks}")
            logger.info(f"Generate Recommendations button clicked, n_clicks: {n_clicks}")
            
            # If button was clicked but data is missing, provide clear error feedback
            if not tech_indicators_data or not options_chain_data or not symbol:
                missing_data = []
                if not symbol:
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
        if not button_clicked and (not tech_indicators_data or not options_chain_data or not symbol):
            debug_info.append("Non-button trigger with missing data, silently returning")
            logger.info("Non-button trigger with missing data, silently returning")
            return dash.no_update, dash.no_update, "\n".join(debug_info), dash.no_update
        
        try:
            # Get underlying price
            underlying_price = options_chain_data.get("underlyingPrice", 0)
            debug_info.append(f"Symbol: {symbol}, Underlying price: {underlying_price}")
            logger.info(f"Processing recommendations for symbol: {symbol}, underlying price: {underlying_price}")
            
            if not symbol or not underlying_price:
                error_msg = f"Missing symbol or price data. Please refresh data."
                debug_info.append(f"ERROR: {error_msg}")
                logger.warning(f"{error_msg} symbol={symbol}, underlying_price={underlying_price}")
                
                # Return error to status only, with no update to error-store
                return None, error_msg, "\n".join(debug_info), dash.no_update
            
            # Prepare data for recommendation engine with proper symbol context
            tech_indicators_dict, options_df, validated_symbol = prepare_data_for_recommendation_engine(
                tech_indicators_data,
                options_chain_data,
                symbol
            )
            
            debug_info.append(f"Prepared data for recommendation engine with symbol: {validated_symbol}")
            debug_info.append(f"Technical indicators timeframes: {list(tech_indicators_dict.keys())}")
            debug_info.append(f"Options data shape: {options_df.shape}")
            
            # Generate recommendations
            engine = RecommendationEngine()
            debug_info.append("Calling recommendation engine generate_recommendations method")
            recommendations = engine.generate_recommendations(tech_indicators_dict, options_df, underlying_price, validated_symbol)
            
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

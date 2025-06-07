"""
Export Button Components for Dashboard Tabs

This module provides functions to create export buttons for each dashboard tab
and register the necessary callbacks to handle Excel exports.
"""

import dash
from dash import html, dcc, Output, Input, State, callback
import logging
from dashboard_utils.excel_export import (
    export_minute_data_to_excel,
    export_technical_indicators_to_excel,
    export_options_chain_to_excel,
    export_recommendations_to_excel
)

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def create_export_button(id_prefix, button_text="Export to Excel"):
    """
    Create an export button with consistent styling.
    
    Args:
        id_prefix (str): Prefix for button ID
        button_text (str): Text to display on the button
        
    Returns:
        html.Button: Export button component
    """
    return html.Button(
        button_text,
        id=f"{id_prefix}-export-button",
        className="export-button",
        style={
            'backgroundColor': '#4CAF50',
            'color': 'white',
            'padding': '8px 12px',
            'border': 'none',
            'borderRadius': '4px',
            'cursor': 'pointer',
            'marginTop': '10px',
            'marginBottom': '10px',
            'fontSize': '14px'
        }
    )

def register_export_callbacks(app):
    """
    Register callbacks for all export buttons.
    
    Args:
        app: Dash app instance
    """
    # Minute Data Export Callback
    @app.callback(
        Output("minute-data-download-data", "data"),
        Input("minute-data-export-button", "n_clicks"),
        State("minute-data-store", "data"),
        State("selected-symbol-store", "data"),
        prevent_initial_call=True
    )
    def export_minute_data(n_clicks, minute_data, selected_symbol):
        """Export minute data to Excel when button is clicked."""
        if not n_clicks or not minute_data:
            return None
        
        try:
            # Fix: Handle both string and dictionary types for selected_symbol
            if isinstance(selected_symbol, dict):
                symbol = selected_symbol.get("symbol", "unknown")
            elif isinstance(selected_symbol, str):
                symbol = selected_symbol
            else:
                symbol = "unknown"
                
            timestamp = minute_data.get("last_update", "").replace(":", "-").replace(" ", "_")
            filename = f"{symbol}_minute_data_{timestamp}.xlsx"
            
            logger.info(f"Exporting minute data to Excel: {filename}")
            success, message, download_info = export_minute_data_to_excel(minute_data, filename)
            
            if success and download_info:
                return download_info
            else:
                logger.error(f"Failed to export minute data: {message}")
                return None
        
        except Exception as e:
            logger.error(f"Error in minute data export callback: {str(e)}", exc_info=True)
            return None
    
    # Technical Indicators Export Callback
    @app.callback(
        Output("tech-indicators-download-data", "data"),
        Input("tech-indicators-export-button", "n_clicks"),
        State("tech-indicators-store", "data"),
        State("selected-symbol-store", "data"),
        prevent_initial_call=True
    )
    def export_tech_indicators(n_clicks, tech_indicators_data, selected_symbol):
        """Export technical indicators to Excel when button is clicked."""
        if not n_clicks or not tech_indicators_data:
            return None
        
        try:
            # Fix: Handle both string and dictionary types for selected_symbol
            if isinstance(selected_symbol, dict):
                symbol = selected_symbol.get("symbol", "unknown")
            elif isinstance(selected_symbol, str):
                symbol = selected_symbol
            else:
                symbol = "unknown"
                
            timestamp = tech_indicators_data.get("last_update", "").replace(":", "-").replace(" ", "_")
            filename = f"{symbol}_technical_indicators_{timestamp}.xlsx"
            
            logger.info(f"Exporting technical indicators to Excel: {filename}")
            success, message, download_info = export_technical_indicators_to_excel(tech_indicators_data, filename)
            
            if success and download_info:
                return download_info
            else:
                logger.error(f"Failed to export technical indicators: {message}")
                return None
        
        except Exception as e:
            logger.error(f"Error in technical indicators export callback: {str(e)}", exc_info=True)
            return None
    
    # Options Chain Export Callback
    @app.callback(
        Output("options-chain-download-data", "data"),
        Input("options-chain-export-button", "n_clicks"),
        State("options-chain-store", "data"),
        State("selected-symbol-store", "data"),
        prevent_initial_call=True
    )
    def export_options_chain(n_clicks, options_data, selected_symbol):
        """Export options chain to Excel when button is clicked."""
        if not n_clicks or not options_data:
            return None
        
        try:
            # Fix: Handle both string and dictionary types for selected_symbol
            if isinstance(selected_symbol, dict):
                symbol = selected_symbol.get("symbol", "unknown")
            elif isinstance(selected_symbol, str):
                symbol = selected_symbol
            else:
                symbol = "unknown"
                
            timestamp = options_data.get("last_update", "").replace(":", "-").replace(" ", "_")
            filename = f"{symbol}_options_chain_{timestamp}.xlsx"
            
            logger.info(f"Exporting options chain to Excel: {filename}")
            success, message, download_info = export_options_chain_to_excel(options_data, filename)
            
            if success and download_info:
                return download_info
            else:
                logger.error(f"Failed to export options chain: {message}")
                return None
        
        except Exception as e:
            logger.error(f"Error in options chain export callback: {str(e)}", exc_info=True)
            return None
    
    # Recommendations Export Callback
    @app.callback(
        Output("recommendations-download-data", "data"),
        Input("recommendations-export-button", "n_clicks"),
        State("recommendations-store", "data"),
        State("selected-symbol-store", "data"),
        prevent_initial_call=True
    )
    def export_recommendations(n_clicks, recommendations_data, selected_symbol):
        """Export recommendations to Excel when button is clicked."""
        if not n_clicks or not recommendations_data:
            return None
        
        try:
            # Fix: Handle both string and dictionary types for selected_symbol
            if isinstance(selected_symbol, dict):
                symbol = selected_symbol.get("symbol", "unknown")
            elif isinstance(selected_symbol, str):
                symbol = selected_symbol
            else:
                symbol = "unknown"
                
            timestamp = recommendations_data.get("last_update", "").replace(":", "-").replace(" ", "_") if recommendations_data.get("last_update") else ""
            filename = f"{symbol}_recommendations_{timestamp}.xlsx"
            
            logger.info(f"Exporting recommendations to Excel: {filename}")
            success, message, download_info = export_recommendations_to_excel(recommendations_data, filename)
            
            if success and download_info:
                return download_info
            else:
                logger.error(f"Failed to export recommendations: {message}")
                return None
        
        except Exception as e:
            logger.error(f"Error in recommendations export callback: {str(e)}", exc_info=True)
            return None


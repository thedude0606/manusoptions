"""
Download Component for Dash Applications

This module provides a Dash component for downloading files.
It uses Dash's native dcc.Download component for better cross-browser compatibility,
especially for Safari.
"""

import dash
from dash import html, dcc, Output, Input, State, callback
import base64
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def create_download_component(id_prefix="file-download"):
    """
    Create a download component using Dash's native dcc.Download component.
    
    Args:
        id_prefix (str): Prefix for component IDs
        
    Returns:
        html.Div: Download component
    """
    return html.Div([
        # Native Dash download component for better cross-browser compatibility
        dcc.Download(id=f"{id_prefix}-download"),
        
        # Store for download data
        dcc.Store(id=f"{id_prefix}-data")
    ])

def register_download_callback(app, id_prefix="file-download"):
    """
    Register callback to trigger download when data is available.
    Uses Dash's native dcc.Download component for better Safari compatibility.
    
    Args:
        app: Dash app instance
        id_prefix (str): Prefix for component IDs
    """
    @app.callback(
        Output(f"{id_prefix}-download", "data"),
        Input(f"{id_prefix}-data", "data"),
        prevent_initial_call=True
    )
    def update_download(data):
        """Update download data when available."""
        if not data:
            return None
        
        try:
            # Extract download info
            filename = data.get("filename", "download.xlsx")
            content = data.get("content", "")
            content_type = data.get("type", "application/octet-stream")
            
            if not content:
                logger.warning("No content provided for download")
                return None
            
            # Prepare download data for dcc.Download
            download_data = {
                "content": content,
                "filename": filename,
                "type": "base64"
            }
            
            logger.info(f"Download prepared for {filename}")
            return download_data
        
        except Exception as e:
            logger.error(f"Error preparing download: {str(e)}", exc_info=True)
            return None

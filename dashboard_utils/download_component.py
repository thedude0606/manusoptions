"""
Download Component for Dash Applications

This module provides a custom Dash component for downloading files.
It handles the client-side download process for Excel files and other data exports.
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
    Create a download component with a hidden download link.
    
    Args:
        id_prefix (str): Prefix for component IDs
        
    Returns:
        html.Div: Download component
    """
    return html.Div([
        # Hidden link for downloads
        html.A(
            id=f"{id_prefix}-link",
            style={"display": "none"},
            download="",
            href=""
        ),
        # Store for download data
        dcc.Store(id=f"{id_prefix}-data")
    ])

def register_download_callback(app, id_prefix="file-download"):
    """
    Register callback to trigger download when data is available.
    
    Args:
        app: Dash app instance
        id_prefix (str): Prefix for component IDs
    """
    @app.callback(
        Output(f"{id_prefix}-link", "href"),
        Output(f"{id_prefix}-link", "download"),
        Output(f"{id_prefix}-link", "children"),  # Dummy output to trigger click
        Input(f"{id_prefix}-data", "data"),
        prevent_initial_call=True
    )
    def update_download_link(data):
        """Update download link when data is available."""
        if not data:
            return "", "", ""
        
        try:
            # Extract download info
            filename = data.get("filename", "download.xlsx")
            content = data.get("content", "")
            content_type = data.get("type", "application/octet-stream")
            
            if not content:
                logger.warning("No content provided for download")
                return "", "", ""
            
            # Create data URI
            href = f"data:{content_type};base64,{content}"
            
            # Return values to update link and trigger click
            logger.info(f"Download prepared for {filename}")
            return href, filename, "click"  # The "click" text will be used to trigger the click
        
        except Exception as e:
            logger.error(f"Error preparing download: {str(e)}", exc_info=True)
            return "", "", ""

def register_download_click_callback(app, id_prefix="file-download"):
    """
    Register callback to automatically click the download link when href changes.
    
    Args:
        app: Dash app instance
        id_prefix (str): Prefix for component IDs
    """
    app.clientside_callback(
        """
        function(children) {
            if (children === "click") {
                document.getElementById(arguments[0].split('.')[0]).click();
            }
            return "";
        }
        """,
        Output(f"{id_prefix}-link", "children"),
        Input(f"{id_prefix}-link", "children")
    )

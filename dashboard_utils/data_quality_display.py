"""
Data Quality Display Component for Options Trading Dashboard

This module provides UI components for displaying data quality metrics
to help users understand the reliability of recommendations.
"""

import dash
from dash import html
import logging

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def create_data_quality_display():
    """
    Create the data quality display component.
    
    Returns:
        html.Div: The data quality display component
    """
    return html.Div([
        html.H3("Data Quality Metrics", className="panel-header"),
        html.Div([
            html.Div([
                html.Div("Technical Indicators", className="quality-section-header"),
                html.Div([
                    html.Div([
                        html.Label("Quality Score:"),
                        html.Span(id="tech-indicators-quality-score", className="quality-score")
                    ], className="quality-item"),
                    html.Div([
                        html.Label("Available Timeframes:"),
                        html.Span(id="tech-indicators-timeframes", className="quality-value")
                    ], className="quality-item"),
                    html.Div([
                        html.Label("Symbol Match:"),
                        html.Span(id="tech-indicators-symbol-match", className="quality-value")
                    ], className="quality-item"),
                    html.Div([
                        html.Label("Data Points:"),
                        html.Span(id="tech-indicators-data-points", className="quality-value")
                    ], className="quality-item")
                ], className="quality-details")
            ], className="quality-section"),
            
            html.Div([
                html.Div("Options Chain", className="quality-section-header"),
                html.Div([
                    html.Div([
                        html.Label("Quality Score:"),
                        html.Span(id="options-chain-quality-score", className="quality-score")
                    ], className="quality-item"),
                    html.Div([
                        html.Label("Symbol Match:"),
                        html.Span(id="options-chain-symbol-match", className="quality-value")
                    ], className="quality-item"),
                    html.Div([
                        html.Label("Calls Available:"),
                        html.Span(id="options-chain-calls", className="quality-value")
                    ], className="quality-item"),
                    html.Div([
                        html.Label("Puts Available:"),
                        html.Span(id="options-chain-puts", className="quality-value")
                    ], className="quality-item")
                ], className="quality-details")
            ], className="quality-section"),
            
            html.Div([
                html.Div("Overall Recommendation Quality", className="quality-section-header"),
                html.Div([
                    html.Div([
                        html.Label("Overall Score:"),
                        html.Span(id="overall-quality-score", className="quality-score")
                    ], className="quality-item"),
                    html.Div([
                        html.Label("Status:"),
                        html.Span(id="quality-status", className="quality-status")
                    ], className="quality-item")
                ], className="quality-details")
            ], className="quality-section")
        ], className="quality-container")
    ], className="panel quality-panel")

def register_data_quality_callbacks(app):
    """
    Register callbacks for the data quality display component.
    
    Args:
        app: The Dash app instance
    """
    @app.callback(
        [
            # Technical indicators quality outputs
            dash.Output("tech-indicators-quality-score", "children"),
            dash.Output("tech-indicators-quality-score", "style"),
            dash.Output("tech-indicators-timeframes", "children"),
            dash.Output("tech-indicators-symbol-match", "children"),
            dash.Output("tech-indicators-symbol-match", "style"),
            dash.Output("tech-indicators-data-points", "children"),
            
            # Options chain quality outputs
            dash.Output("options-chain-quality-score", "children"),
            dash.Output("options-chain-quality-score", "style"),
            dash.Output("options-chain-symbol-match", "children"),
            dash.Output("options-chain-symbol-match", "style"),
            dash.Output("options-chain-calls", "children"),
            dash.Output("options-chain-puts", "children"),
            
            # Overall quality outputs
            dash.Output("overall-quality-score", "children"),
            dash.Output("overall-quality-score", "style"),
            dash.Output("quality-status", "children"),
            dash.Output("quality-status", "style")
        ],
        [dash.Input("recommendations-store", "data")],
        prevent_initial_call=True
    )
    def update_data_quality_display(recommendations_data):
        """Update data quality display based on recommendations data."""
        if not recommendations_data or "data_quality" not in recommendations_data:
            # Default values when no data is available
            return (
                "N/A", {"color": "gray"},  # Tech indicators score
                "None", "Unknown", {"color": "gray"}, "0",  # Tech indicators details
                "N/A", {"color": "gray"},  # Options chain score
                "Unknown", {"color": "gray"}, "0", "0",  # Options chain details
                "N/A", {"color": "gray"},  # Overall score
                "No data available", {"color": "red"}  # Status
            )
        
        try:
            # Extract data quality metrics
            data_quality = recommendations_data.get("data_quality", {})
            tech_indicators_quality = data_quality.get("technical_indicators", {"score": 0, "metrics": {}})
            options_chain_quality = data_quality.get("options_chain", {"score": 0, "metrics": {}})
            overall_score = data_quality.get("overall_score", 0)
            
            # Technical indicators metrics
            tech_score = tech_indicators_quality.get("score", 0)
            tech_metrics = tech_indicators_quality.get("metrics", {})
            timeframes = ", ".join(tech_metrics.get("timeframes_available", ["None"]))
            symbol_match_tech = "Yes" if tech_metrics.get("symbol_match", False) else "No"
            
            # Calculate total data points across timeframes
            data_points = 0
            for tf, rows in tech_metrics.get("rows_per_timeframe", {}).items():
                data_points += rows
            
            # Options chain metrics
            options_score = options_chain_quality.get("score", 0)
            options_metrics = options_chain_quality.get("metrics", {})
            symbol_match_options = "Yes" if options_metrics.get("symbol_match", False) else "No"
            calls_count = options_metrics.get("calls", 0)
            puts_count = options_metrics.get("puts", 0)
            
            # Determine status text and color based on overall score
            if overall_score >= 80:
                status_text = "High Quality"
                status_style = {"color": "green", "fontWeight": "bold"}
            elif overall_score >= 60:
                status_text = "Good Quality"
                status_style = {"color": "darkgreen"}
            elif overall_score >= 40:
                status_text = "Fair Quality"
                status_style = {"color": "orange"}
            else:
                status_text = "Poor Quality"
                status_style = {"color": "red"}
            
            # Determine score colors
            def get_score_style(score):
                if score >= 80:
                    return {"color": "green", "fontWeight": "bold"}
                elif score >= 60:
                    return {"color": "darkgreen"}
                elif score >= 40:
                    return {"color": "orange"}
                else:
                    return {"color": "red"}
            
            tech_score_style = get_score_style(tech_score)
            options_score_style = get_score_style(options_score)
            overall_score_style = get_score_style(overall_score)
            
            # Determine symbol match styles
            tech_symbol_match_style = {"color": "green"} if symbol_match_tech == "Yes" else {"color": "red"}
            options_symbol_match_style = {"color": "green"} if symbol_match_options == "Yes" else {"color": "red"}
            
            return (
                f"{tech_score:.0f}/100", tech_score_style,
                timeframes,
                symbol_match_tech, tech_symbol_match_style,
                str(data_points),
                
                f"{options_score:.0f}/100", options_score_style,
                symbol_match_options, options_symbol_match_style,
                str(calls_count),
                str(puts_count),
                
                f"{overall_score:.0f}/100", overall_score_style,
                status_text, status_style
            )
        
        except Exception as e:
            logger.error(f"Error updating data quality display: {e}")
            # Return default values on error
            return (
                "Error", {"color": "red"},
                "Error", "Error", {"color": "red"}, "Error",
                "Error", {"color": "red"},
                "Error", {"color": "red"}, "Error", "Error",
                "Error", {"color": "red"},
                f"Error: {str(e)}", {"color": "red"}
            )

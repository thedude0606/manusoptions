"""
Excel Export Utility for Options Dashboard

This module provides functions to export dashboard data to Excel files.
It handles exporting data from all tabs including Minute Data, Technical Indicators,
Options Chain (Calls and Puts), and Recommendations.
"""

import pandas as pd
import logging
import os
import datetime
import json
from io import BytesIO
import base64

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def export_minute_data_to_excel(minute_data, filename=None):
    """
    Export minute data to Excel file.
    
    Args:
        minute_data (dict): Minute data from the store
        filename (str, optional): Output filename. If None, a default name is generated.
        
    Returns:
        tuple: (success, message, download_info)
    """
    try:
        if not minute_data or not minute_data.get("data"):
            return False, "No minute data available to export", None
        
        # Extract data and metadata
        data = minute_data.get("data", [])
        symbol = minute_data.get("symbol", "unknown")
        last_update = minute_data.get("last_update", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_minute_data_{timestamp}.xlsx"
        
        # Create Excel writer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Minute Data', index=False)
            
            # Add metadata sheet
            metadata = pd.DataFrame([
                {"Key": "Symbol", "Value": symbol},
                {"Key": "Last Update", "Value": last_update},
                {"Key": "Export Time", "Value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"Key": "Number of Records", "Value": len(data)}
            ])
            metadata.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Prepare download info
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        output.seek(0)
        content = output.read()
        b64_content = base64.b64encode(content).decode()
        download_info = {
            "filename": filename,
            "content": b64_content,
            "type": content_type
        }
        
        logger.info(f"Successfully exported {len(data)} minute data records to Excel")
        return True, f"Successfully exported minute data to {filename}", download_info
    
    except Exception as e:
        error_msg = f"Error exporting minute data to Excel: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None

def export_technical_indicators_to_excel(tech_indicators_data, filename=None):
    """
    Export technical indicators data to Excel file.
    
    Args:
        tech_indicators_data (dict): Technical indicators data from the store
        filename (str, optional): Output filename. If None, a default name is generated.
        
    Returns:
        tuple: (success, message, download_info)
    """
    try:
        if not tech_indicators_data:
            return False, "No technical indicators data available to export", None
        
        # Extract data and metadata
        data = tech_indicators_data.get("data", [])
        timeframe_data = tech_indicators_data.get("timeframe_data", {})
        symbol = tech_indicators_data.get("symbol", "unknown")
        last_update = tech_indicators_data.get("last_update", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_technical_indicators_{timestamp}.xlsx"
        
        # Create Excel writer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write all indicators to one sheet
            if data:
                all_df = pd.DataFrame(data)
                all_df.to_excel(writer, sheet_name='All Indicators', index=False)
            
            # Write each timeframe to a separate sheet
            for timeframe, tf_data in timeframe_data.items():
                if tf_data:
                    tf_df = pd.DataFrame(tf_data)
                    sheet_name = f'{timeframe} Indicators'
                    # Excel sheet names have a 31 character limit
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:31]
                    tf_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Add metadata sheet
            metadata = pd.DataFrame([
                {"Key": "Symbol", "Value": symbol},
                {"Key": "Last Update", "Value": last_update},
                {"Key": "Export Time", "Value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"Key": "Number of Records", "Value": len(data)},
                {"Key": "Timeframes", "Value": ", ".join(timeframe_data.keys())}
            ])
            metadata.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Prepare download info
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        output.seek(0)
        content = output.read()
        b64_content = base64.b64encode(content).decode()
        download_info = {
            "filename": filename,
            "content": b64_content,
            "type": content_type
        }
        
        logger.info(f"Successfully exported technical indicators data to Excel with {len(timeframe_data)} timeframes")
        return True, f"Successfully exported technical indicators to {filename}", download_info
    
    except Exception as e:
        error_msg = f"Error exporting technical indicators to Excel: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None

def export_options_chain_to_excel(options_data, filename=None):
    """
    Export options chain data to Excel file.
    
    Args:
        options_data (dict): Options chain data from the store
        filename (str, optional): Output filename. If None, a default name is generated.
        
    Returns:
        tuple: (success, message, download_info)
    """
    try:
        if not options_data or not options_data.get("options"):
            return False, "No options chain data available to export", None
        
        # Extract data and metadata
        options = options_data.get("options", [])
        symbol = options_data.get("symbol", "unknown")
        expiration_dates = options_data.get("expiration_dates", [])
        underlying_price = options_data.get("underlyingPrice", 0)
        last_update = options_data.get("last_update", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        
        # Create DataFrame
        df = pd.DataFrame(options)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_options_chain_{timestamp}.xlsx"
        
        # Create Excel writer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write all options to one sheet
            df.to_excel(writer, sheet_name='All Options', index=False)
            
            # Split into calls and puts
            if 'putCall' in df.columns:
                calls_df = df[df['putCall'] == 'CALL']
                puts_df = df[df['putCall'] == 'PUT']
                
                calls_df.to_excel(writer, sheet_name='Calls', index=False)
                puts_df.to_excel(writer, sheet_name='Puts', index=False)
            
            # Split by expiration date (up to 10 expiration dates to avoid too many sheets)
            if 'expirationDate' in df.columns and expiration_dates:
                for exp_date in expiration_dates[:10]:  # Limit to 10 expiration dates
                    exp_df = df[df['expirationDate'] == exp_date]
                    if not exp_df.empty:
                        sheet_name = f'Exp {exp_date}'
                        # Excel sheet names have a 31 character limit
                        if len(sheet_name) > 31:
                            sheet_name = sheet_name[:31]
                        exp_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Add metadata sheet
            metadata = pd.DataFrame([
                {"Key": "Symbol", "Value": symbol},
                {"Key": "Underlying Price", "Value": underlying_price},
                {"Key": "Last Update", "Value": last_update},
                {"Key": "Export Time", "Value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"Key": "Number of Contracts", "Value": len(options)},
                {"Key": "Number of Calls", "Value": len(calls_df) if 'calls_df' in locals() else "N/A"},
                {"Key": "Number of Puts", "Value": len(puts_df) if 'puts_df' in locals() else "N/A"},
                {"Key": "Expiration Dates", "Value": ", ".join(expiration_dates)}
            ])
            metadata.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Prepare download info
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        output.seek(0)
        content = output.read()
        b64_content = base64.b64encode(content).decode()
        download_info = {
            "filename": filename,
            "content": b64_content,
            "type": content_type
        }
        
        logger.info(f"Successfully exported {len(options)} options contracts to Excel")
        return True, f"Successfully exported options chain to {filename}", download_info
    
    except Exception as e:
        error_msg = f"Error exporting options chain to Excel: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None

def export_recommendations_to_excel(recommendations_data, filename=None):
    """
    Export recommendations data to Excel file.
    
    Args:
        recommendations_data (dict): Recommendations data from the store
        filename (str, optional): Output filename. If None, a default name is generated.
        
    Returns:
        tuple: (success, message, download_info)
    """
    try:
        if not recommendations_data:
            return False, "No recommendations data available to export", None
        
        # Extract data and metadata
        call_recommendations = recommendations_data.get("call_recommendations", [])
        put_recommendations = recommendations_data.get("put_recommendations", [])
        market_direction = recommendations_data.get("market_direction", {})
        symbol = recommendations_data.get("symbol", "unknown")
        timeframe = recommendations_data.get("timeframe", "unknown")
        last_update = recommendations_data.get("last_update", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_recommendations_{timestamp}.xlsx"
        
        # Create Excel writer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write call recommendations
            if call_recommendations:
                calls_df = pd.DataFrame(call_recommendations)
                calls_df.to_excel(writer, sheet_name='Call Recommendations', index=False)
            
            # Write put recommendations
            if put_recommendations:
                puts_df = pd.DataFrame(put_recommendations)
                puts_df.to_excel(writer, sheet_name='Put Recommendations', index=False)
            
            # Write market direction data
            if market_direction:
                # Convert market direction dict to DataFrame
                market_df = pd.DataFrame([
                    {"Metric": key, "Value": value} 
                    for key, value in market_direction.items()
                ])
                market_df.to_excel(writer, sheet_name='Market Direction', index=False)
            
            # Add metadata sheet
            metadata = pd.DataFrame([
                {"Key": "Symbol", "Value": symbol},
                {"Key": "Timeframe", "Value": timeframe},
                {"Key": "Last Update", "Value": last_update},
                {"Key": "Export Time", "Value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"Key": "Number of Call Recommendations", "Value": len(call_recommendations)},
                {"Key": "Number of Put Recommendations", "Value": len(put_recommendations)}
            ])
            metadata.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Prepare download info
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        output.seek(0)
        content = output.read()
        b64_content = base64.b64encode(content).decode()
        download_info = {
            "filename": filename,
            "content": b64_content,
            "type": content_type
        }
        
        logger.info(f"Successfully exported recommendations to Excel")
        return True, f"Successfully exported recommendations to {filename}", download_info
    
    except Exception as e:
        error_msg = f"Error exporting recommendations to Excel: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None

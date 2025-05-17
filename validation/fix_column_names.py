#!/usr/bin/env python3
# fix_column_names.py
# Script to fix column name mismatches in the technical indicators tab

import os
import sys
import pandas as pd
import logging
import argparse

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from technical_analysis import aggregate_candles, calculate_all_technical_indicators

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("column_fix_results.log")
    ]
)
logger = logging.getLogger("column_fix")

def fix_column_names_in_data_fetchers():
    """
    Fix column name mismatches in data_fetchers.py
    
    This function modifies the data_fetchers.py file to ensure column names
    are lowercase to match what technical_analysis.py expects.
    """
    data_fetchers_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "dashboard_utils",
        "data_fetchers.py"
    )
    
    if not os.path.exists(data_fetchers_path):
        logger.error(f"data_fetchers.py not found at {data_fetchers_path}")
        return False
    
    with open(data_fetchers_path, 'r') as f:
        content = f.read()
    
    # Find the section where column renaming happens
    old_rename_section = """    # Rename other relevant columns for consistency
    all_candles_df = all_candles_df.rename(columns={
        "open": "Open", "high": "High", "low": "Low", 
        "close": "Close", "volume": "Volume"
    })"""
    
    new_rename_section = """    # Rename other relevant columns for consistency
    # Using lowercase column names for compatibility with technical_analysis.py
    all_candles_df = all_candles_df.rename(columns={
        "open": "open", "high": "high", "low": "low", 
        "close": "close", "volume": "volume"
    })"""
    
    if old_rename_section in content:
        content = content.replace(old_rename_section, new_rename_section)
        
        # Also update the columns_to_keep section
        old_columns_section = """    # Select the final set of columns, ensuring 'timestamp' is a datetime object.
    # This implicitly drops the original 'datetime' column from the API if it's not in the list.
    columns_to_keep = ["timestamp", "Open", "High", "Low", "Close", "Volume"]"""
        
        new_columns_section = """    # Select the final set of columns, ensuring 'timestamp' is a datetime object.
    # This implicitly drops the original 'datetime' column from the API if it's not in the list.
    # Using lowercase column names for compatibility with technical_analysis.py
    columns_to_keep = ["timestamp", "open", "high", "low", "close", "volume"]"""
        
        if old_columns_section in content:
            content = content.replace(old_columns_section, new_columns_section)
            
            # Write the modified content back to the file
            with open(data_fetchers_path, 'w') as f:
                f.write(content)
            
            logger.info(f"Successfully updated column names in {data_fetchers_path}")
            return True
        else:
            logger.error(f"Could not find columns_to_keep section in {data_fetchers_path}")
            return False
    else:
        logger.error(f"Could not find rename section in {data_fetchers_path}")
        return False

def add_column_normalization_to_dashboard_app():
    """
    Add column normalization to dashboard_app.py
    
    This function modifies the dashboard_app.py file to add a column normalization
    step before technical analysis calculations.
    """
    dashboard_app_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "dashboard_app.py"
    )
    
    if not os.path.exists(dashboard_app_path):
        logger.error(f"dashboard_app.py not found at {dashboard_app_path}")
        return False
    
    with open(dashboard_app_path, 'r') as f:
        content = f.read()
    
    # Find the section where technical analysis is called
    # This is a simplified approach - in a real scenario, you'd want to use
    # a proper Python parser to modify the code
    
    # Look for a section where df_minute is processed before technical analysis
    target_section = """            app_logger.info(f"UpdateDataTabs (TechInd): Converted 'timestamp' column to DatetimeIndex for {symbol}.")
            
            # Step 3: Aggregate data to different timeframes
            app_logger.info(f"UpdateDataTabs (TechInd): Starting data aggregation for {symbol}.")"""
    
    column_normalization_code = """            app_logger.info(f"UpdateDataTabs (TechInd): Converted 'timestamp' column to DatetimeIndex for {symbol}.")
            
            # Normalize column names to lowercase for technical analysis compatibility
            column_rename_map = {}
            for col in df_minute.columns:
                if col.lower() in ['open', 'high', 'low', 'close', 'volume']:
                    column_rename_map[col] = col.lower()
            
            if column_rename_map:
                df_minute = df_minute.rename(columns=column_rename_map)
                app_logger.info(f"UpdateDataTabs (TechInd): Normalized column names to lowercase for {symbol}.")
            
            # Step 3: Aggregate data to different timeframes
            app_logger.info(f"UpdateDataTabs (TechInd): Starting data aggregation for {symbol}.")"""
    
    if target_section in content:
        content = content.replace(target_section, column_normalization_code)
        
        # Write the modified content back to the file
        with open(dashboard_app_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Successfully added column normalization to {dashboard_app_path}")
        return True
    else:
        logger.error(f"Could not find target section in {dashboard_app_path}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Fix column name mismatches in the technical indicators tab')
    parser.add_argument('--fix-data-fetchers', action='store_true', help='Fix column names in data_fetchers.py')
    parser.add_argument('--add-normalization', action='store_true', help='Add column normalization to dashboard_app.py')
    args = parser.parse_args()
    
    if args.fix_data_fetchers:
        success = fix_column_names_in_data_fetchers()
        if success:
            logger.info("Successfully fixed column names in data_fetchers.py")
        else:
            logger.error("Failed to fix column names in data_fetchers.py")
    
    if args.add_normalization:
        success = add_column_normalization_to_dashboard_app()
        if success:
            logger.info("Successfully added column normalization to dashboard_app.py")
        else:
            logger.error("Failed to add column normalization to dashboard_app.py")
    
    if not (args.fix_data_fetchers or args.add_normalization):
        logger.info("No actions specified. Use --fix-data-fetchers or --add-normalization")
        parser.print_help()

if __name__ == '__main__':
    main()

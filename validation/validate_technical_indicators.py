#!/usr/bin/env python3
# validate_technical_indicators.py
# Script to validate technical indicators output against terminal logs

import os
import re
import sys
import pandas as pd
import logging
import argparse
from datetime import datetime

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from technical_analysis import calculate_all_technical_indicators, aggregate_candles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("validation_results.log")
    ]
)
logger = logging.getLogger("validation")

def parse_log_file(log_file_path):
    """Parse the terminal log file to extract technical indicator information."""
    if not os.path.exists(log_file_path):
        logger.error(f"Log file not found: {log_file_path}")
        return None
    
    with open(log_file_path, 'r') as f:
        log_content = f.read()
    
    # Extract relevant information from logs
    log_data = {
        'fetched_candles': {},
        'aggregation_errors': {},
        'indicator_calculations': {},
        'indicator_counts': {}
    }
    
    # Extract fetched candle counts
    candle_matches = re.findall(r"Successfully fetched a total of (\d+) unique minute candles for (\w+)", log_content)
    for count, symbol in candle_matches:
        log_data['fetched_candles'][symbol] = int(count)
    
    # Extract aggregation errors
    agg_error_matches = re.findall(r"technical_analysis - ERROR - Aggregation: (.*?)$", log_content, re.MULTILINE)
    if agg_error_matches:
        log_data['aggregation_errors']['message'] = agg_error_matches
    
    # Extract indicator calculation results
    calc_matches = re.findall(r"UpdateDataTabs \(TechInd\): (\w+) calculation returned DataFrame with shape \((\d+), (\d+)\) for (\w+)", log_content)
    for timeframe, rows, cols, symbol in calc_matches:
        if symbol not in log_data['indicator_calculations']:
            log_data['indicator_calculations'][symbol] = {}
        log_data['indicator_calculations'][symbol][timeframe] = {
            'rows': int(rows),
            'columns': int(cols)
        }
    
    # Extract indicator counts
    count_matches = re.findall(r"UpdateDataTabs \(TechInd\): Found (\d+) indicators for (\w+) for (\w+)", log_content)
    for count, timeframe, symbol in count_matches:
        if symbol not in log_data['indicator_counts']:
            log_data['indicator_counts'][symbol] = {}
        log_data['indicator_counts'][symbol][timeframe] = int(count)
    
    return log_data

def load_sample_data(data_file_path):
    """Load sample data from a CSV file."""
    if not os.path.exists(data_file_path):
        logger.error(f"Sample data file not found: {data_file_path}")
        return None
    
    try:
        df = pd.read_csv(data_file_path)
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        return df
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
        return None

def validate_column_names(df):
    """Validate that the DataFrame has the expected column names for technical analysis."""
    expected_cols = ['open', 'high', 'low', 'close', 'volume']
    actual_cols = [col.lower() for col in df.columns]
    
    missing_cols = [col for col in expected_cols if col not in actual_cols]
    if missing_cols:
        logger.warning(f"Missing expected columns: {missing_cols}")
        return False
    
    # Check if columns exist but with different case
    case_mismatch = []
    for expected in expected_cols:
        if expected not in df.columns and expected.lower() in [col.lower() for col in df.columns]:
            actual = next(col for col in df.columns if col.lower() == expected.lower())
            case_mismatch.append((expected, actual))
    
    if case_mismatch:
        logger.warning(f"Column case mismatch: {case_mismatch}")
        return False
    
    return True

def fix_column_names(df):
    """Fix column names to match expected format for technical analysis."""
    rename_map = {}
    for col in df.columns:
        if col.lower() in ['open', 'high', 'low', 'close', 'volume']:
            rename_map[col] = col.lower()
    
    if rename_map:
        logger.info(f"Renaming columns: {rename_map}")
        df = df.rename(columns=rename_map)
    
    return df

def run_technical_analysis(df, symbol):
    """Run technical analysis on the DataFrame and return results."""
    # Ensure DataFrame has datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        logger.error("DataFrame index is not DatetimeIndex")
        if 'timestamp' in df.columns:
            logger.info("Converting 'timestamp' column to DatetimeIndex")
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        else:
            logger.error("No 'timestamp' column found for conversion to DatetimeIndex")
            return None
    
    # Fix column names if needed
    if not validate_column_names(df):
        logger.info("Fixing column names")
        df = fix_column_names(df)
    
    # Run technical analysis
    try:
        logger.info(f"Running technical analysis for {symbol} on DataFrame with {len(df)} rows")
        df_ta = calculate_all_technical_indicators(df, symbol=symbol)
        return df_ta
    except Exception as e:
        logger.error(f"Error running technical analysis: {e}")
        return None

def run_aggregation(df, rule):
    """Run aggregation on the DataFrame and return results."""
    try:
        logger.info(f"Running aggregation with rule '{rule}' on DataFrame with {len(df)} rows")
        df_agg = aggregate_candles(df, rule)
        return df_agg
    except Exception as e:
        logger.error(f"Error running aggregation: {e}")
        return None

def validate_against_logs(ta_results, log_data, symbol):
    """Validate technical analysis results against log data."""
    validation_results = {
        'passed': True,
        'issues': []
    }
    
    # Check if symbol exists in log data
    if symbol not in log_data.get('fetched_candles', {}):
        validation_results['passed'] = False
        validation_results['issues'].append(f"Symbol {symbol} not found in log data")
        return validation_results
    
    # Check candle count
    expected_candles = log_data['fetched_candles'].get(symbol, 0)
    actual_candles = len(ta_results) if ta_results is not None else 0
    if expected_candles != actual_candles:
        validation_results['passed'] = False
        validation_results['issues'].append(f"Candle count mismatch: expected {expected_candles}, got {actual_candles}")
    
    # Check indicator counts
    if symbol in log_data.get('indicator_counts', {}):
        for timeframe, expected_count in log_data['indicator_counts'][symbol].items():
            if timeframe == '1min':
                actual_count = len(ta_results.columns) if ta_results is not None else 0
                if expected_count != actual_count:
                    validation_results['passed'] = False
                    validation_results['issues'].append(f"Indicator count mismatch for {timeframe}: expected {expected_count}, got {actual_count}")
    
    # Check for aggregation errors
    if log_data.get('aggregation_errors', {}).get('message'):
        validation_results['issues'].append(f"Aggregation errors found in logs: {log_data['aggregation_errors']['message']}")
        # This is not necessarily a failure, as we're validating the error condition
    
    return validation_results

def main():
    parser = argparse.ArgumentParser(description='Validate technical indicators against terminal logs')
    parser.add_argument('--log-file', type=str, required=True, help='Path to terminal log file')
    parser.add_argument('--data-file', type=str, required=True, help='Path to sample data file')
    parser.add_argument('--symbol', type=str, default='MSFT', help='Symbol to validate')
    args = parser.parse_args()
    
    logger.info(f"Starting validation for symbol {args.symbol}")
    
    # Parse log file
    log_data = parse_log_file(args.log_file)
    if log_data is None:
        logger.error("Failed to parse log file")
        return 1
    
    logger.info(f"Log data: {log_data}")
    
    # Load sample data
    df = load_sample_data(args.data_file)
    if df is None:
        logger.error("Failed to load sample data")
        return 1
    
    logger.info(f"Sample data loaded: {len(df)} rows, columns: {df.columns.tolist()}")
    
    # Validate column names
    column_validation = validate_column_names(df)
    logger.info(f"Column validation: {'Passed' if column_validation else 'Failed'}")
    
    # Fix column names if needed
    if not column_validation:
        df = fix_column_names(df)
        logger.info(f"Fixed columns: {df.columns.tolist()}")
    
    # Run technical analysis
    ta_results = run_technical_analysis(df, args.symbol)
    if ta_results is None:
        logger.error("Failed to run technical analysis")
        return 1
    
    logger.info(f"Technical analysis results: {len(ta_results)} rows, {len(ta_results.columns)} columns")
    
    # Run aggregation for different timeframes
    for rule, name in [('15min', '15min'), ('1H', 'Hourly'), ('1D', 'Daily')]:
        agg_results = run_aggregation(df, rule)
        if agg_results is None or agg_results.empty:
            logger.warning(f"Aggregation for {name} returned empty DataFrame")
        else:
            logger.info(f"Aggregation for {name}: {len(agg_results)} rows")
            # Run technical analysis on aggregated data
            agg_ta_results = run_technical_analysis(agg_results, f"{args.symbol}_{name}")
            if agg_ta_results is None:
                logger.warning(f"Technical analysis for {name} failed")
            else:
                logger.info(f"Technical analysis for {name}: {len(agg_ta_results)} rows, {len(agg_ta_results.columns)} columns")
    
    # Validate against logs
    validation_results = validate_against_logs(ta_results, log_data, args.symbol)
    logger.info(f"Validation results: {'Passed' if validation_results['passed'] else 'Failed'}")
    for issue in validation_results['issues']:
        logger.warning(f"Validation issue: {issue}")
    
    return 0 if validation_results['passed'] else 1

if __name__ == '__main__':
    sys.exit(main())

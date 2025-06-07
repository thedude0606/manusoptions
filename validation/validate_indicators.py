#!/usr/bin/env python3
"""
Technical Indicator Validation Script

This script validates the technical indicators implemented in the manusoptions project
by generating synthetic data with known patterns and verifying the calculated indicators
match expected values.

Usage:
    python validate_indicators.py

The script will:
1. Generate synthetic price data with known patterns
2. Calculate technical indicators using the project's implementation
3. Validate the results against expected values
4. Report any discrepancies or issues found
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("indicator_validation_results.log")
    ]
)
logger = logging.getLogger("indicator_validation")

# Import technical analysis functions
try:
    from technical_analysis import (
        calculate_bollinger_bands,
        calculate_rsi,
        calculate_macd,
        calculate_imi,
        calculate_mfi,
        identify_fair_value_gaps,
        calculate_all_technical_indicators
    )
    logger.info("Successfully imported technical analysis functions")
except ImportError as e:
    logger.error(f"Failed to import technical analysis functions: {e}")
    sys.exit(1)

def generate_synthetic_data(pattern_type="trend", num_periods=100, volatility=0.01, seed=42):
    """
    Generate synthetic price data with known patterns.
    
    Args:
        pattern_type (str): Type of pattern to generate ('trend', 'oscillating', 'random')
        num_periods (int): Number of periods to generate
        volatility (float): Volatility factor for price movements
        seed (int): Random seed for reproducibility
        
    Returns:
        pandas.DataFrame: DataFrame with synthetic OHLCV data
    """
    np.random.seed(seed)
    
    # Create date range for the past num_periods minutes
    end_time = datetime.now().replace(second=0, microsecond=0)
    start_time = end_time - timedelta(minutes=num_periods-1)
    date_range = pd.date_range(start=start_time, end=end_time, periods=num_periods)
    
    # Initialize price at 100
    base_price = 100.0
    
    # Generate prices based on pattern type
    if pattern_type == "trend":
        # Uptrend for first half, downtrend for second half
        trend = np.concatenate([
            np.linspace(0, 0.2, num_periods // 2),
            np.linspace(0.2, -0.2, num_periods - num_periods // 2)
        ])
        noise = np.random.normal(0, volatility, num_periods)
        price_changes = trend + noise
        
    elif pattern_type == "oscillating":
        # Oscillating pattern (sine wave)
        periods = 4  # Number of complete oscillations
        amplitude = 0.1
        trend = amplitude * np.sin(np.linspace(0, periods * 2 * np.pi, num_periods))
        noise = np.random.normal(0, volatility, num_periods)
        price_changes = trend + noise
        
    else:  # random
        # Random walk
        price_changes = np.random.normal(0, volatility, num_periods)
    
    # Calculate cumulative price changes
    cum_changes = np.cumsum(price_changes)
    
    # Generate OHLCV data
    close_prices = base_price * (1 + cum_changes)
    
    # Generate open, high, low based on close
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = base_price
    
    # High is max of open and close plus some random amount
    high_prices = np.maximum(open_prices, close_prices) + np.random.uniform(0, volatility * base_price, num_periods)
    
    # Low is min of open and close minus some random amount
    low_prices = np.minimum(open_prices, close_prices) - np.random.uniform(0, volatility * base_price, num_periods)
    
    # Volume increases with price volatility
    volume = np.abs(close_prices - open_prices) * 1000000 + 100000
    
    # Create DataFrame
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume.astype(int)
    }, index=date_range)
    
    return df

def validate_bollinger_bands(df, window=20, num_std=2):
    """
    Validate Bollinger Bands calculation.
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        window (int): Window size for Bollinger Bands
        num_std (int): Number of standard deviations for bands
        
    Returns:
        tuple: (is_valid, issues)
    """
    logger.info(f"Validating Bollinger Bands (window={window}, num_std={num_std})")
    issues = []
    
    # Calculate Bollinger Bands using the project's implementation
    df_with_bb = calculate_bollinger_bands(df.copy())
    
    # Calculate expected values manually
    expected_middle = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    expected_upper = expected_middle + (rolling_std * num_std)
    expected_lower = expected_middle - (rolling_std * num_std)
    
    # Compare results
    if not np.allclose(df_with_bb['bb_middle'].dropna(), expected_middle.dropna(), rtol=1e-5, atol=1e-8):
        issues.append("Middle band values do not match expected values")
    
    if not np.allclose(df_with_bb['bb_upper'].dropna(), expected_upper.dropna(), rtol=1e-5, atol=1e-8):
        issues.append("Upper band values do not match expected values")
    
    if not np.allclose(df_with_bb['bb_lower'].dropna(), expected_lower.dropna(), rtol=1e-5, atol=1e-8):
        issues.append("Lower band values do not match expected values")
    
    # Check for NaN values in the first window-1 periods
    if not df_with_bb['bb_middle'].iloc[:window-1].isna().all():
        issues.append(f"Expected NaN values for first {window-1} periods in middle band")
    
    is_valid = len(issues) == 0
    
    if is_valid:
        logger.info("Bollinger Bands validation: PASSED")
    else:
        logger.warning(f"Bollinger Bands validation: FAILED - {len(issues)} issues found")
        for issue in issues:
            logger.warning(f"  - {issue}")
    
    return is_valid, issues

def validate_rsi(df, window=14):
    """
    Validate RSI calculation.
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        window (int): Window size for RSI
        
    Returns:
        tuple: (is_valid, issues)
    """
    logger.info(f"Validating RSI (window={window})")
    issues = []
    
    # Calculate RSI using the project's implementation
    df_with_rsi = calculate_rsi(df.copy())
    
    # Calculate expected values manually
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    expected_rsi = 100 - (100 / (1 + rs))
    
    # Compare results
    if not np.allclose(df_with_rsi['rsi'].dropna(), expected_rsi.dropna(), rtol=1e-5, atol=1e-8):
        issues.append("RSI values do not match expected values")
    
    # Check for NaN values in the first window periods
    if not df_with_rsi['rsi'].iloc[:window].isna().all():
        issues.append(f"Expected NaN values for first {window} periods")
    
    is_valid = len(issues) == 0
    
    if is_valid:
        logger.info("RSI validation: PASSED")
    else:
        logger.warning(f"RSI validation: FAILED - {len(issues)} issues found")
        for issue in issues:
            logger.warning(f"  - {issue}")
    
    return is_valid, issues

def validate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """
    Validate MACD calculation.
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        fast_period (int): Fast EMA period
        slow_period (int): Slow EMA period
        signal_period (int): Signal line period
        
    Returns:
        tuple: (is_valid, issues)
    """
    logger.info(f"Validating MACD (fast={fast_period}, slow={slow_period}, signal={signal_period})")
    issues = []
    
    # Calculate MACD using the project's implementation
    df_with_macd = calculate_macd(df.copy())
    
    # Calculate expected values manually
    expected_ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
    expected_ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
    expected_macd_line = expected_ema_fast - expected_ema_slow
    expected_macd_signal = expected_macd_line.ewm(span=signal_period, adjust=False).mean()
    expected_macd_histogram = expected_macd_line - expected_macd_signal
    
    # Compare results
    if not np.allclose(df_with_macd['macd_line'].dropna(), expected_macd_line.dropna(), rtol=1e-5, atol=1e-8):
        issues.append("MACD line values do not match expected values")
    
    if not np.allclose(df_with_macd['macd_signal'].dropna(), expected_macd_signal.dropna(), rtol=1e-5, atol=1e-8):
        issues.append("MACD signal values do not match expected values")
    
    if not np.allclose(df_with_macd['macd_histogram'].dropna(), expected_macd_histogram.dropna(), rtol=1e-5, atol=1e-8):
        issues.append("MACD histogram values do not match expected values")
    
    # Check for NaN values in the first slow_period-1 periods
    if not df_with_macd['macd_line'].iloc[:slow_period-1].isna().all():
        issues.append(f"Expected NaN values for first {slow_period-1} periods in MACD line")
    
    is_valid = len(issues) == 0
    
    if is_valid:
        logger.info("MACD validation: PASSED")
    else:
        logger.warning(f"MACD validation: FAILED - {len(issues)} issues found")
        for issue in issues:
            logger.warning(f"  - {issue}")
    
    return is_valid, issues

def validate_imi(df, window=14):
    """
    Validate Intraday Momentum Index (IMI) calculation.
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        window (int): Window size for IMI
        
    Returns:
        tuple: (is_valid, issues)
    """
    logger.info(f"Validating IMI (window={window})")
    issues = []
    
    # Calculate IMI using the project's implementation
    df_with_imi = calculate_imi(df.copy())
    
    # Calculate expected values manually
    up_move = np.where(df['close'] > df['open'], df['close'] - df['open'], 0)
    down_move = np.where(df['open'] > df['close'], df['open'] - df['close'], 0)
    up_sum = pd.Series(up_move).rolling(window=window).sum()
    down_sum = pd.Series(down_move).rolling(window=window).sum()
    expected_imi = 100 * (up_sum / (up_sum + down_sum))
    
    # Compare results
    if not np.allclose(df_with_imi['imi'].dropna(), expected_imi.dropna(), rtol=1e-5, atol=1e-8):
        issues.append("IMI values do not match expected values")
    
    # Check for NaN values in the first window-1 periods
    if not df_with_imi['imi'].iloc[:window-1].isna().all():
        issues.append(f"Expected NaN values for first {window-1} periods")
    
    is_valid = len(issues) == 0
    
    if is_valid:
        logger.info("IMI validation: PASSED")
    else:
        logger.warning(f"IMI validation: FAILED - {len(issues)} issues found")
        for issue in issues:
            logger.warning(f"  - {issue}")
    
    return is_valid, issues

def validate_mfi(df, window=14):
    """
    Validate Money Flow Index (MFI) calculation.
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        window (int): Window size for MFI
        
    Returns:
        tuple: (is_valid, issues)
    """
    logger.info(f"Validating MFI (window={window})")
    issues = []
    
    # Calculate MFI using the project's implementation
    df_with_mfi = calculate_mfi(df.copy())
    
    # Calculate expected values manually
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    money_flow = typical_price * df['volume']
    price_change = typical_price.diff()
    positive_flow = np.where(price_change > 0, money_flow, 0)
    negative_flow = np.where(price_change < 0, money_flow, 0)
    positive_flow_sum = pd.Series(positive_flow).rolling(window=window).sum()
    negative_flow_sum = pd.Series(negative_flow).rolling(window=window).sum()
    money_flow_ratio = positive_flow_sum / negative_flow_sum
    expected_mfi = 100 - (100 / (1 + money_flow_ratio))
    
    # Compare results
    if not np.allclose(df_with_mfi['mfi'].dropna(), expected_mfi.dropna(), rtol=1e-5, atol=1e-8):
        issues.append("MFI values do not match expected values")
    
    # Check for NaN values in the first window periods
    if not df_with_mfi['mfi'].iloc[:window].isna().all():
        issues.append(f"Expected NaN values for first {window} periods")
    
    is_valid = len(issues) == 0
    
    if is_valid:
        logger.info("MFI validation: PASSED")
    else:
        logger.warning(f"MFI validation: FAILED - {len(issues)} issues found")
        for issue in issues:
            logger.warning(f"  - {issue}")
    
    return is_valid, issues

def validate_fair_value_gaps(df):
    """
    Validate Fair Value Gaps (FVG) identification.
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        
    Returns:
        tuple: (is_valid, issues)
    """
    logger.info("Validating Fair Value Gaps")
    issues = []
    
    # Calculate FVGs using the project's implementation
    df_with_fvg = identify_fair_value_gaps(df.copy())
    
    # Check if the required columns were added
    required_columns = ['bullish_fvg', 'bearish_fvg', 'bullish_fvg_size', 'bearish_fvg_size']
    for col in required_columns:
        if col not in df_with_fvg.columns:
            issues.append(f"Column '{col}' not found in result")
    
    if issues:
        is_valid = False
    else:
        # Manually identify FVGs for validation
        bullish_fvg = np.full(len(df), False)
        bearish_fvg = np.full(len(df), False)
        bullish_fvg_size = np.full(len(df), np.nan)
        bearish_fvg_size = np.full(len(df), np.nan)
        
        for i in range(2, len(df)):
            # Bullish FVG (low of candle 1 > high of candle 3)
            if df['low'].iloc[i-2] > df['high'].iloc[i]:
                bullish_fvg[i-1] = True
                bullish_fvg_size[i-1] = df['low'].iloc[i-2] - df['high'].iloc[i]
            
            # Bearish FVG (high of candle 1 < low of candle 3)
            if df['high'].iloc[i-2] < df['low'].iloc[i]:
                bearish_fvg[i-1] = True
                bearish_fvg_size[i-1] = df['low'].iloc[i] - df['high'].iloc[i-2]
        
        # Compare results
        if not np.array_equal(df_with_fvg['bullish_fvg'].values, bullish_fvg):
            issues.append("Bullish FVG identification does not match expected values")
        
        if not np.array_equal(df_with_fvg['bearish_fvg'].values, bearish_fvg):
            issues.append("Bearish FVG identification does not match expected values")
        
        # Compare sizes where FVGs are identified
        bullish_mask = bullish_fvg == True
        if bullish_mask.any() and not np.allclose(
            df_with_fvg.loc[bullish_mask, 'bullish_fvg_size'].dropna(),
            pd.Series(bullish_fvg_size)[bullish_mask].dropna(),
            rtol=1e-5, atol=1e-8
        ):
            issues.append("Bullish FVG size values do not match expected values")
        
        bearish_mask = bearish_fvg == True
        if bearish_mask.any() and not np.allclose(
            df_with_fvg.loc[bearish_mask, 'bearish_fvg_size'].dropna(),
            pd.Series(bearish_fvg_size)[bearish_mask].dropna(),
            rtol=1e-5, atol=1e-8
        ):
            issues.append("Bearish FVG size values do not match expected values")
        
        is_valid = len(issues) == 0
    
    if is_valid:
        logger.info("Fair Value Gaps validation: PASSED")
    else:
        logger.warning(f"Fair Value Gaps validation: FAILED - {len(issues)} issues found")
        for issue in issues:
            logger.warning(f"  - {issue}")
    
    return is_valid, issues

def validate_all_indicators(df):
    """
    Validate all technical indicators.
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        
    Returns:
        dict: Validation results for each indicator
    """
    results = {}
    
    # Validate individual indicators
    results['bollinger_bands'] = validate_bollinger_bands(df)
    results['rsi'] = validate_rsi(df)
    results['macd'] = validate_macd(df)
    results['imi'] = validate_imi(df)
    results['mfi'] = validate_mfi(df)
    results['fair_value_gaps'] = validate_fair_value_gaps(df)
    
    # Validate the all-in-one function
    logger.info("Validating calculate_all_technical_indicators function")
    try:
        df_all = calculate_all_technical_indicators(df.copy(), symbol="TEST")
        if df_all is not None and not df_all.empty:
            results['all_indicators'] = (True, [])
            logger.info("All indicators calculation: PASSED")
        else:
            results['all_indicators'] = (False, ["Function returned None or empty DataFrame"])
            logger.warning("All indicators calculation: FAILED - Function returned None or empty DataFrame")
    except Exception as e:
        results['all_indicators'] = (False, [f"Exception occurred: {str(e)}"])
        logger.error(f"All indicators calculation: FAILED - Exception occurred: {str(e)}")
    
    return results

def validate_timeframe_resampling(df):
    """
    Validate timeframe resampling and indicator calculation on resampled data.
    
    Args:
        df (pandas.DataFrame): DataFrame with minute-level price data
        
    Returns:
        dict: Validation results for each timeframe
    """
    results = {}
    
    # Define timeframes to test
    timeframes = {
        '5min': '5min',
        '15min': '15min',
        '30min': '30min',
        '1hour': '1H'
    }
    
    for tf_name, tf_rule in timeframes.items():
        logger.info(f"Validating resampling to {tf_name} timeframe")
        
        try:
            # Resample data
            resampled_df = df.resample(tf_rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            
            # Calculate indicators on resampled data
            ta_df = calculate_all_technical_indicators(resampled_df, symbol=f"TEST_{tf_name}")
            
            if ta_df is not None and not ta_df.empty:
                results[tf_name] = (True, [])
                logger.info(f"{tf_name} timeframe validation: PASSED")
            else:
                results[tf_name] = (False, ["Function returned None or empty DataFrame"])
                logger.warning(f"{tf_name} timeframe validation: FAILED - Function returned None or empty DataFrame")
        
        except Exception as e:
            results[tf_name] = (False, [f"Exception occurred: {str(e)}"])
            logger.error(f"{tf_name} timeframe validation: FAILED - Exception occurred: {str(e)}")
    
    return results

def plot_indicators(df_with_indicators, output_dir="validation_plots"):
    """
    Generate plots of the technical indicators for visual inspection.
    
    Args:
        df_with_indicators (pandas.DataFrame): DataFrame with calculated indicators
        output_dir (str): Directory to save plots
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Plot price and Bollinger Bands
    if all(col in df_with_indicators.columns for col in ['close', 'bb_middle', 'bb_upper', 'bb_lower']):
        plt.figure(figsize=(12, 6))
        plt.plot(df_with_indicators.index, df_with_indicators['close'], label='Close Price')
        plt.plot(df_with_indicators.index, df_with_indicators['bb_middle'], label='Middle Band')
        plt.plot(df_with_indicators.index, df_with_indicators['bb_upper'], label='Upper Band')
        plt.plot(df_with_indicators.index, df_with_indicators['bb_lower'], label='Lower Band')
        plt.title('Price and Bollinger Bands')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, 'bollinger_bands.png'))
        plt.close()
    
    # Plot RSI
    if 'rsi' in df_with_indicators.columns:
        plt.figure(figsize=(12, 4))
        plt.plot(df_with_indicators.index, df_with_indicators['rsi'], label='RSI')
        plt.axhline(y=70, color='r', linestyle='-', alpha=0.3)
        plt.axhline(y=30, color='g', linestyle='-', alpha=0.3)
        plt.title('Relative Strength Index (RSI)')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, 'rsi.png'))
        plt.close()
    
    # Plot MACD
    if all(col in df_with_indicators.columns for col in ['macd_line', 'macd_signal', 'macd_histogram']):
        plt.figure(figsize=(12, 8))
        
        # MACD line and signal
        plt.subplot(2, 1, 1)
        plt.plot(df_with_indicators.index, df_with_indicators['macd_line'], label='MACD Line')
        plt.plot(df_with_indicators.index, df_with_indicators['macd_signal'], label='Signal Line')
        plt.title('MACD Line and Signal')
        plt.legend()
        plt.grid(True)
        
        # MACD histogram
        plt.subplot(2, 1, 2)
        plt.bar(df_with_indicators.index, df_with_indicators['macd_histogram'], label='MACD Histogram')
        plt.title('MACD Histogram')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'macd.png'))
        plt.close()
    
    # Plot IMI
    if 'imi' in df_with_indicators.columns:
        plt.figure(figsize=(12, 4))
        plt.plot(df_with_indicators.index, df_with_indicators['imi'], label='IMI')
        plt.axhline(y=70, color='r', linestyle='-', alpha=0.3)
        plt.axhline(y=30, color='g', linestyle='-', alpha=0.3)
        plt.title('Intraday Momentum Index (IMI)')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, 'imi.png'))
        plt.close()
    
    # Plot MFI
    if 'mfi' in df_with_indicators.columns:
        plt.figure(figsize=(12, 4))
        plt.plot(df_with_indicators.index, df_with_indicators['mfi'], label='MFI')
        plt.axhline(y=80, color='r', linestyle='-', alpha=0.3)
        plt.axhline(y=20, color='g', linestyle='-', alpha=0.3)
        plt.title('Money Flow Index (MFI)')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, 'mfi.png'))
        plt.close()
    
    # Plot Fair Value Gaps
    if all(col in df_with_indicators.columns for col in ['close', 'bullish_fvg', 'bearish_fvg']):
        plt.figure(figsize=(12, 6))
        plt.plot(df_with_indicators.index, df_with_indicators['close'], label='Close Price')
        
        # Mark bullish FVGs
        bullish_idx = df_with_indicators.index[df_with_indicators['bullish_fvg']]
        if len(bullish_idx) > 0:
            plt.scatter(bullish_idx, df_with_indicators.loc[bullish_idx, 'close'], 
                       marker='^', color='g', s=100, label='Bullish FVG')
        
        # Mark bearish FVGs
        bearish_idx = df_with_indicators.index[df_with_indicators['bearish_fvg']]
        if len(bearish_idx) > 0:
            plt.scatter(bearish_idx, df_with_indicators.loc[bearish_idx, 'close'], 
                       marker='v', color='r', s=100, label='Bearish FVG')
        
        plt.title('Price and Fair Value Gaps')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, 'fair_value_gaps.png'))
        plt.close()
    
    logger.info(f"Indicator plots saved to {output_dir} directory")

def main():
    """Main function to run the validation."""
    logger.info("Starting technical indicator validation")
    
    # Generate synthetic data with different patterns
    patterns = ["trend", "oscillating", "random"]
    validation_results = {}
    
    for pattern in patterns:
        logger.info(f"Testing with {pattern} pattern data")
        
        # Generate data
        df = generate_synthetic_data(pattern_type=pattern, num_periods=200)
        logger.info(f"Generated {len(df)} periods of {pattern} pattern data")
        
        # Validate indicators
        pattern_results = validate_all_indicators(df)
        validation_results[pattern] = pattern_results
        
        # Validate timeframe resampling
        timeframe_results = validate_timeframe_resampling(df)
        validation_results[f"{pattern}_timeframes"] = timeframe_results
        
        # Calculate all indicators for plotting
        df_with_indicators = calculate_all_technical_indicators(df.copy(), symbol=f"TEST_{pattern}")
        
        # Generate plots
        plot_indicators(df_with_indicators, output_dir=f"validation_plots_{pattern}")
    
    # Summarize results
    logger.info("\n=== VALIDATION SUMMARY ===")
    all_passed = True
    
    for pattern, results in validation_results.items():
        if "timeframes" not in pattern:
            logger.info(f"\nPattern: {pattern}")
            for indicator, (is_valid, issues) in results.items():
                status = "PASSED" if is_valid else "FAILED"
                logger.info(f"  {indicator}: {status}")
                if not is_valid:
                    all_passed = False
        else:
            base_pattern = pattern.split("_")[0]
            logger.info(f"\nTimeframe resampling for {base_pattern} pattern:")
            for timeframe, (is_valid, issues) in results.items():
                status = "PASSED" if is_valid else "FAILED"
                logger.info(f"  {timeframe}: {status}")
                if not is_valid:
                    all_passed = False
    
    if all_passed:
        logger.info("\nAll validations PASSED! Technical indicators are calculating correctly.")
    else:
        logger.warning("\nSome validations FAILED. See log for details.")
    
    logger.info("Validation complete. Check the log file and plots for detailed results.")

if __name__ == "__main__":
    main()


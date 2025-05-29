import pandas as pd
import numpy as np
import logging
import datetime
from candlestick_patterns import calculate_all_candlestick_patterns

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ta_logger = logging.getLogger('technical_analysis')

# Technical indicator calculation functions
def calculate_bollinger_bands(df, window=20, num_std=2):
    """Calculate Bollinger Bands."""
    try:
        if 'close' not in df.columns:
            ta_logger.warning("Bollinger Bands: 'close' column not found in DataFrame")
            return df
        
        # Calculate rolling mean and standard deviation
        df['bb_middle'] = df['close'].rolling(window=window).mean()
        rolling_std = df['close'].rolling(window=window).std()
        
        # Calculate upper and lower bands
        df['bb_upper'] = df['bb_middle'] + (rolling_std * num_std)
        df['bb_lower'] = df['bb_middle'] - (rolling_std * num_std)
        
        # Calculate bandwidth and %B
        df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_percent_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        ta_logger.info("Bollinger Bands calculated successfully")
    except Exception as e:
        ta_logger.error(f"Error calculating Bollinger Bands: {e}")
    
    return df

def calculate_rsi(df, window=14):
    """Calculate Relative Strength Index (RSI)."""
    try:
        if 'close' not in df.columns:
            ta_logger.warning("RSI: 'close' column not found in DataFrame")
            return df
        
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        ta_logger.info("RSI calculated successfully")
    except Exception as e:
        ta_logger.error(f"Error calculating RSI: {e}")
    
    return df

def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """Calculate Moving Average Convergence Divergence (MACD)."""
    try:
        if 'close' not in df.columns:
            ta_logger.warning("MACD: 'close' column not found in DataFrame")
            return df
        
        # Calculate EMAs
        df['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line and signal line
        df['macd_line'] = df['ema_fast'] - df['ema_slow']
        df['macd_signal'] = df['macd_line'].ewm(span=signal_period, adjust=False).mean()
        
        # Calculate MACD histogram
        df['macd_histogram'] = df['macd_line'] - df['macd_signal']
        
        ta_logger.info("MACD calculated successfully")
    except Exception as e:
        ta_logger.error(f"Error calculating MACD: {e}")
    
    return df

def calculate_imi(df, window=14):
    """Calculate Intraday Momentum Index (IMI)."""
    try:
        if not all(col in df.columns for col in ['open', 'close']):
            ta_logger.warning("IMI: Required columns not found in DataFrame")
            return df
        
        # Calculate up and down moves
        df['up_move'] = np.where(df['close'] > df['open'], df['close'] - df['open'], 0)
        df['down_move'] = np.where(df['open'] > df['close'], df['open'] - df['close'], 0)
        
        # Calculate sum of up and down moves over window
        df['up_sum'] = df['up_move'].rolling(window=window).sum()
        df['down_sum'] = df['down_move'].rolling(window=window).sum()
        
        # Calculate IMI
        df['imi'] = 100 * (df['up_sum'] / (df['up_sum'] + df['down_sum']))
        
        # Clean up intermediate columns
        df.drop(['up_move', 'down_move', 'up_sum', 'down_sum'], axis=1, inplace=True)
        
        ta_logger.info("IMI calculated successfully")
    except Exception as e:
        ta_logger.error(f"Error calculating IMI: {e}")
    
    return df

def calculate_mfi(df, window=14):
    """Calculate Money Flow Index (MFI)."""
    try:
        if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
            ta_logger.warning("MFI: Required columns not found in DataFrame")
            return df
        
        # Calculate typical price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Calculate money flow
        df['money_flow'] = df['typical_price'] * df['volume']
        
        # Calculate positive and negative money flow
        df['price_change'] = df['typical_price'].diff()
        df['positive_flow'] = np.where(df['price_change'] > 0, df['money_flow'], 0)
        df['negative_flow'] = np.where(df['price_change'] < 0, df['money_flow'], 0)
        
        # Calculate positive and negative money flow sum over window
        df['positive_flow_sum'] = df['positive_flow'].rolling(window=window).sum()
        df['negative_flow_sum'] = df['negative_flow'].rolling(window=window).sum()
        
        # Calculate money flow ratio and MFI
        df['money_flow_ratio'] = df['positive_flow_sum'] / df['negative_flow_sum']
        df['mfi'] = 100 - (100 / (1 + df['money_flow_ratio']))
        
        # Clean up intermediate columns
        df.drop(['typical_price', 'money_flow', 'price_change', 'positive_flow', 'negative_flow', 
                 'positive_flow_sum', 'negative_flow_sum', 'money_flow_ratio'], axis=1, inplace=True)
        
        ta_logger.info("MFI calculated successfully")
    except Exception as e:
        ta_logger.error(f"Error calculating MFI: {e}")
    
    return df

def calculate_timeframe_bias(df, short_ma_period=5, medium_ma_period=20, long_ma_period=50):
    """
    Calculate the timeframe bias indicator showing dominant trend direction.
    
    The bias is calculated using a combination of:
    1. Moving average relationships
    2. Momentum indicators (RSI, MACD)
    3. Price action analysis
    
    Args:
        df: DataFrame containing price data and technical indicators
        short_ma_period: Period for short-term moving average
        medium_ma_period: Period for medium-term moving average
        long_ma_period: Period for long-term moving average
        
    Returns:
        DataFrame with timeframe bias indicators added
    """
    try:
        if 'close' not in df.columns:
            ta_logger.warning("Timeframe Bias: 'close' column not found in DataFrame")
            return df
        
        # Calculate moving averages if not already present
        if f'sma_{short_ma_period}' not in df.columns:
            df[f'sma_{short_ma_period}'] = df['close'].rolling(window=short_ma_period).mean()
        
        if f'sma_{medium_ma_period}' not in df.columns:
            df[f'sma_{medium_ma_period}'] = df['close'].rolling(window=medium_ma_period).mean()
        
        if f'sma_{long_ma_period}' not in df.columns:
            df[f'sma_{long_ma_period}'] = df['close'].rolling(window=long_ma_period).mean()
        
        # Initialize bias score (from -100 to +100)
        df['tf_bias_score'] = 0
        
        # 1. Moving Average Relationships (contributes up to ±50 points)
        # Short MA vs Medium MA
        df['tf_bias_score'] += np.where(
            df[f'sma_{short_ma_period}'] > df[f'sma_{medium_ma_period}'], 
            25, 
            np.where(
                df[f'sma_{short_ma_period}'] < df[f'sma_{medium_ma_period}'], 
                -25, 
                0
            )
        )
        
        # Short MA vs Long MA
        df['tf_bias_score'] += np.where(
            df[f'sma_{short_ma_period}'] > df[f'sma_{long_ma_period}'], 
            25, 
            np.where(
                df[f'sma_{short_ma_period}'] < df[f'sma_{long_ma_period}'], 
                -25, 
                0
            )
        )
        
        # 2. Momentum Indicators (contributes up to ±30 points)
        # RSI
        if 'rsi' in df.columns:
            df['tf_bias_score'] += np.where(
                df['rsi'] > 70, 
                10, 
                np.where(
                    df['rsi'] < 30, 
                    -10, 
                    np.where(
                        df['rsi'] > 50, 
                        5, 
                        -5
                    )
                )
            )
        
        # MACD
        if all(col in df.columns for col in ['macd_line', 'macd_signal']):
            df['tf_bias_score'] += np.where(
                df['macd_line'] > df['macd_signal'], 
                10, 
                np.where(
                    df['macd_line'] < df['macd_signal'], 
                    -10, 
                    0
                )
            )
            
            # MACD Histogram direction
            if 'macd_histogram' in df.columns:
                df['macd_hist_diff'] = df['macd_histogram'].diff()
                df['tf_bias_score'] += np.where(
                    df['macd_hist_diff'] > 0, 
                    10, 
                    np.where(
                        df['macd_hist_diff'] < 0, 
                        -10, 
                        0
                    )
                )
                df.drop(['macd_hist_diff'], axis=1, inplace=True)
        
        # 3. Price Action Analysis (contributes up to ±20 points)
        # Recent price movement vs medium MA
        df['price_vs_medium_ma'] = df['close'] - df[f'sma_{medium_ma_period}']
        df['price_vs_medium_ma_diff'] = df['price_vs_medium_ma'].diff(3)  # 3-period change
        
        df['tf_bias_score'] += np.where(
            df['price_vs_medium_ma_diff'] > 0, 
            10, 
            np.where(
                df['price_vs_medium_ma_diff'] < 0, 
                -10, 
                0
            )
        )
        
        # Higher highs and higher lows (bullish) or lower highs and lower lows (bearish)
        df['rolling_max_5'] = df['high'].rolling(window=5).max()
        df['rolling_min_5'] = df['low'].rolling(window=5).min()
        
        df['prev_rolling_max_5'] = df['rolling_max_5'].shift(5)
        df['prev_rolling_min_5'] = df['rolling_min_5'].shift(5)
        
        df['tf_bias_score'] += np.where(
            (df['rolling_max_5'] > df['prev_rolling_max_5']) & 
            (df['rolling_min_5'] > df['prev_rolling_min_5']), 
            10, 
            np.where(
                (df['rolling_max_5'] < df['prev_rolling_max_5']) & 
                (df['rolling_min_5'] < df['prev_rolling_min_5']), 
                -10, 
                0
            )
        )
        
        # Clean up intermediate columns
        df.drop(['price_vs_medium_ma', 'price_vs_medium_ma_diff', 
                 'rolling_max_5', 'rolling_min_5', 
                 'prev_rolling_max_5', 'prev_rolling_min_5'], axis=1, inplace=True)
        
        # Ensure bias score is within bounds (-100 to +100)
        df['tf_bias_score'] = df['tf_bias_score'].clip(-100, 100)
        
        # Add categorical bias label
        conditions = [
            (df['tf_bias_score'] >= 75),
            (df['tf_bias_score'] >= 50) & (df['tf_bias_score'] < 75),
            (df['tf_bias_score'] >= 25) & (df['tf_bias_score'] < 50),
            (df['tf_bias_score'] > -25) & (df['tf_bias_score'] < 25),
            (df['tf_bias_score'] <= -25) & (df['tf_bias_score'] > -50),
            (df['tf_bias_score'] <= -50) & (df['tf_bias_score'] > -75),
            (df['tf_bias_score'] <= -75)
        ]
        
        choices = [
            'strongly_bullish',
            'bullish',
            'slightly_bullish',
            'neutral',
            'slightly_bearish',
            'bearish',
            'strongly_bearish'
        ]
        
        df['tf_bias_label'] = np.select(conditions, choices, default='neutral')
        
        # Calculate bias confidence (absolute value of bias score)
        df['tf_bias_confidence'] = df['tf_bias_score'].abs()
        
        ta_logger.info("Timeframe bias calculated successfully")
    except Exception as e:
        ta_logger.error(f"Error calculating timeframe bias: {e}")
    
    return df

def identify_fair_value_gaps(df):
    """Identify Fair Value Gaps (FVG) in price data."""
    try:
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            ta_logger.warning("FVG: Required columns not found in DataFrame")
            return df
        
        # Initialize FVG columns
        df['bullish_fvg'] = False
        df['bearish_fvg'] = False
        df['bullish_fvg_size'] = np.nan
        df['bearish_fvg_size'] = np.nan
        
        # Need at least 3 candles to identify FVGs
        if len(df) < 3:
            ta_logger.warning("FVG: Not enough data points to identify Fair Value Gaps")
            return df
        
        # Identify bullish FVGs (low of candle 1 > high of candle 3)
        for i in range(2, len(df)):
            if df['low'].iloc[i-2] > df['high'].iloc[i]:
                df['bullish_fvg'].iloc[i-1] = True
                df['bullish_fvg_size'].iloc[i-1] = df['low'].iloc[i-2] - df['high'].iloc[i]
        
        # Identify bearish FVGs (high of candle 1 < low of candle 3)
        for i in range(2, len(df)):
            if df['high'].iloc[i-2] < df['low'].iloc[i]:
                df['bearish_fvg'].iloc[i-1] = True
                df['bearish_fvg_size'].iloc[i-1] = df['low'].iloc[i] - df['high'].iloc[i-2]
        
        ta_logger.info("Fair Value Gaps identified successfully")
    except Exception as e:
        ta_logger.error(f"Error identifying Fair Value Gaps: {e}")
    
    return df

def resample_ohlcv(df, rule='15min'):
    """
    Resample OHLCV data to a different timeframe.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing OHLCV data with datetime index
    rule : str
        Pandas resampling rule (e.g., '15min', '30min', '1H', '1D')
        
    Returns:
    --------
    pandas.DataFrame
        Resampled OHLCV data
    """
    try:
        # Ensure DataFrame has datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            ta_logger.warning("Resampling requires DatetimeIndex. Attempting to convert...")
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp')
            elif 'datetime' in df.columns:
                df = df.set_index('datetime')
            else:
                ta_logger.error("No datetime column found for resampling")
                return pd.DataFrame()
        
        # Check for required columns
        expected_cols = ['open', 'high', 'low', 'close', 'volume']
        actual_cols = [col for col in expected_cols if col in df.columns]
        
        if len(actual_cols) < 4:  # Need at least OHLC
            ta_logger.error(f"Insufficient columns for resampling. Found: {actual_cols}")
            return pd.DataFrame()
        
        # Create a mapping for any columns that might have different names
        rename_map = {}
        rename_back = {}
        
        for expected_col in expected_cols:
            if expected_col not in df.columns:
                # Look for case-insensitive match
                matches = [col for col in df.columns if col.lower() == expected_col]
                if matches:
                    actual_col = matches[0]
                    rename_map[actual_col] = expected_col
                    rename_back[expected_col] = actual_col
        
        if rename_map:
            ta_logger.info(f"Aggregation: Renaming columns for standard processing: {rename_map}")
            df = df.rename(columns=rename_map)
        
        # Define aggregation functions
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }
        
        # Add volume if it exists
        if 'volume' in df.columns:
            agg_dict['volume'] = 'sum'
        
        # Resample data
        ta_logger.info(f"Resampling data with rule: {rule}")
        aggregated_df = df.resample(rule).agg(agg_dict)
        
        # Rename columns back if needed
        if rename_back:
            ta_logger.info(f"Aggregation: Renaming columns back to standard: {rename_back}")
            aggregated_df = aggregated_df.rename(columns=rename_back)
        
    except Exception as e:
        ta_logger.error(f"Error during resampling with rule '{rule}': {e}")
        return pd.DataFrame()
        
    return aggregated_df

def calculate_all_technical_indicators(df, symbol="N/A"):
    """Calculates all defined technical indicators for the given DataFrame."""
    if df.empty:
        ta_logger.warning(f"TA All: Input DataFrame for {symbol} is empty. Skipping TA calculations.")
        return df
    
    # Ensure DataFrame is a copy to avoid SettingWithCopyWarning on original data from dashboard
    df_ta = df.copy()
    
    # CRITICAL FIX: Ensure data is sorted in ascending chronological order (oldest first)
    # This is required for all technical indicators to calculate correctly
    if isinstance(df_ta.index, pd.DatetimeIndex):
        ta_logger.info(f"Sorting DataFrame by DatetimeIndex in ascending order for {symbol}")
        df_ta = df_ta.sort_index(ascending=True)
    elif 'timestamp' in df_ta.columns:
        ta_logger.info(f"Sorting DataFrame by timestamp column in ascending order for {symbol}")
        df_ta = df_ta.sort_values(by='timestamp', ascending=True)
    else:
        ta_logger.warning(f"No timestamp column or DatetimeIndex found for {symbol}. Technical indicators may not calculate correctly.")
    
    # Standardize column names to lowercase if they exist, for robustness
    # Expected columns: 'open', 'high', 'low', 'close', 'volume'
    # The data_fetchers.py already standardizes to lowercase 'open', 'high', 'low', 'close', 'volume'
    # and sets 'timestamp' as datetime index. So, this step might be redundant if data comes from there.
    # However, it's good practice if this module is used independently.
    rename_map = {col: col.lower() for col in df_ta.columns if col.lower() in ['open', 'high', 'low', 'close', 'volume']}
    if rename_map:
        df_ta.rename(columns=rename_map, inplace=True)
    
    # Check for required columns after potential rename
    required_cols_for_ta = ['open', 'high', 'low', 'close', 'volume'] # MFI needs all, others subsets
    missing_cols = [col for col in required_cols_for_ta if col not in df_ta.columns]
    if any(col not in df_ta.columns for col in ['open', 'close']): # Minimum for most basic TAs
        ta_logger.error(f"TA All: DataFrame for {symbol} is missing essential columns (e.g., 'open', 'close'). Missing: {missing_cols}. Cannot calculate TA.")
        return df # Return original df if essential columns are missing
    
    ta_logger.info(f"Calculating TA for {symbol} on DataFrame with {len(df_ta)} rows.")
    
    # Calculate indicators with improved edge case handling
    df_ta = calculate_bollinger_bands(df_ta)
    df_ta = calculate_rsi(df_ta)
    df_ta = calculate_macd(df_ta)
    df_ta = calculate_imi(df_ta)
    df_ta = calculate_mfi(df_ta)
    df_ta = identify_fair_value_gaps(df_ta)
    
    # Calculate timeframe bias indicator
    df_ta = calculate_timeframe_bias(df_ta)
    
    # Calculate candlestick patterns
    df_ta = calculate_all_candlestick_patterns(df_ta, symbol=symbol)
    
    ta_logger.info(f"Finished TA for {symbol}. DataFrame now has {len(df_ta.columns)} columns.")
    return df_ta

def calculate_multi_timeframe_indicators(df, symbol="N/A"):
    """
    Calculate technical indicators for multiple timeframes.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing OHLCV data with datetime index
    symbol : str
        Symbol for logging purposes
        
    Returns:
    --------
    dict
        Dictionary of DataFrames with technical indicators for each timeframe
    """
    if df.empty:
        ta_logger.warning(f"Multi-timeframe TA: Input DataFrame for {symbol} is empty. Skipping calculations.")
        return {}
    
    # Ensure DataFrame has datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        ta_logger.warning("Multi-timeframe TA requires DatetimeIndex. Attempting to convert...")
        if 'timestamp' in df.columns:
            df = df.set_index('timestamp')
        elif 'datetime' in df.columns:
            df = df.set_index('datetime')
        else:
            ta_logger.error("No datetime column found for multi-timeframe analysis")
            return {}
    
    # Define timeframes to calculate
    timeframes = {
        '1min': '1min',
        '15min': '15min',
        '30min': '30min',
        '1hour': '1H',
        'daily': '1D'
    }
    
    # Initialize result dictionary
    result = {}
    
    # Calculate indicators for each timeframe
    for tf_name, tf_rule in timeframes.items():
        ta_logger.info(f"Calculating indicators for {tf_name} timeframe")
        
        # For 1min timeframe, use original data
        if tf_name == '1min':
            resampled_df = df.copy()
        else:
            # Resample data to the target timeframe
            resampled_df = resample_ohlcv(df, rule=tf_rule)
            
            if resampled_df.empty:
                ta_logger.warning(f"Failed to resample data to {tf_name} timeframe")
                continue
        
        # Calculate technical indicators for this timeframe
        ta_df = calculate_all_technical_indicators(resampled_df, symbol=f"{symbol}_{tf_name}")
        
        # Store in result dictionary
        result[tf_name] = ta_df
        
        ta_logger.info(f"Completed indicators for {tf_name} timeframe with {len(ta_df)} rows and {len(ta_df.columns)} columns")
    
    return result

# Example usage (can be removed or kept for standalone testing)
if __name__ == '__main__':
    # Create a sample DataFrame (mimicking fetched stock data)
    sample_data = {
        'datetime': pd.to_datetime([
            '2023-01-01 09:30:00', '2023-01-01 09:31:00', '2023-01-01 09:32:00',
            '2023-01-01 09:33:00', '2023-01-01 09:34:00', '2023-01-01 09:35:00',
            '2023-01-01 09:36:00', '2023-01-01 09:37:00', '2023-01-01 09:38:00',
            '2023-01-01 09:39:00', '2023-01-01 09:40:00', '2023-01-01 09:41:00',
            '2023-01-01 09:42:00', '2023-01-01 09:43:00', '2023-01-01 09:44:00',
            '2023-01-01 09:45:00', '2023-01-01 09:46:00', '2023-01-01 09:47:00',
            '2023-01-01 09:48:00', '2023-01-01 09:49:00', '2023-01-01 09:50:00',
            '2023-01-01 09:51:00', '2023-01-01 09:52:00', '2023-01-01 09:53:00',
            '2023-01-01 09:54:00', '2023-01-01 09:55:00', '2023-01-01 09:56:00',
            '2023-01-01 09:57:00', '2023-01-01 09:58:00', '2023-01-01 09:59:00',
            '2023-01-01 10:00:00'
        ]),
        'open': [150.0, 150.5, 151.0, 151.5, 152.0, 151.5, 151.0, 150.5, 150.0, 
                149.5, 149.0, 148.5, 148.0, 147.5, 147.0, 147.5, 148.0, 148.5, 
                149.0, 149.5, 150.0, 150.5, 151.0, 151.5, 152.0, 152.5, 153.0, 
                153.5, 154.0, 154.5, 155.0],
        'high': [150.5, 151.0, 151.5, 152.0, 152.5, 152.0, 151.5, 151.0, 150.5, 
                150.0, 149.5, 149.0, 148.5, 148.0, 147.5, 148.0, 148.5, 149.0, 
                149.5, 150.0, 150.5, 151.0, 151.5, 152.0, 152.5, 153.0, 153.5, 
                154.0, 154.5, 155.0, 155.5],
        'low': [149.5, 150.0, 150.5, 151.0, 151.5, 151.0, 150.5, 150.0, 149.5, 
               149.0, 148.5, 148.0, 147.5, 147.0, 146.5, 147.0, 147.5, 148.0, 
               148.5, 149.0, 149.5, 150.0, 150.5, 151.0, 151.5, 152.0, 152.5, 
               153.0, 153.5, 154.0, 154.5],
        'close': [150.5, 151.0, 151.5, 152.0, 151.5, 151.0, 150.5, 150.0, 149.5, 
                 149.0, 148.5, 148.0, 147.5, 147.0, 147.5, 148.0, 148.5, 149.0, 
                 149.5, 150.0, 150.5, 151.0, 151.5, 152.0, 152.5, 153.0, 153.5, 
                 154.0, 154.5, 155.0, 155.5],
        'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 
                  1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 
                  2800, 2900, 3000, 3100, 3200, 3300, 3400, 3500, 3600, 
                  3700, 3800, 3900, 4000]
    }
    
    # Create DataFrame and set datetime as index
    df = pd.DataFrame(sample_data)
    df.set_index('datetime', inplace=True)
    
    # Calculate technical indicators
    ta_df = calculate_all_technical_indicators(df, symbol="SAMPLE")
    
    # Print results
    print(ta_df.tail())
    
    # Calculate multi-timeframe indicators
    multi_tf_results = calculate_multi_timeframe_indicators(df, symbol="SAMPLE")
    
    # Print results for each timeframe
    for tf_name, tf_df in multi_tf_results.items():
        print(f"\nTimeframe: {tf_name}")
        print(tf_df.tail(1))

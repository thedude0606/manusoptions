# technical_analysis.py
import pandas as pd
import numpy as np
import logging

# Configure basic logging for the module
ta_logger = logging.getLogger(__name__)
if not ta_logger.hasHandlers():
    ta_handler = logging.StreamHandler()
    ta_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ta_handler.setFormatter(ta_formatter)
    ta_logger.addHandler(ta_handler)
ta_logger.setLevel(logging.INFO)

def calculate_bollinger_bands(df, window=20, num_std_dev=2):
    """Calculates Bollinger Bands."""
    if 'close' not in df.columns or len(df) < window:
        ta_logger.warning(f"BBands: DataFrame length {len(df)} is less than window {window} or 'close' column missing.")
        df[f'bb_middle_{window}'] = np.nan
        df[f'bb_upper_{window}'] = np.nan
        df[f'bb_lower_{window}'] = np.nan
        return df
    
    rolling_mean = df['close'].rolling(window=window, min_periods=1).mean()
    rolling_std = df['close'].rolling(window=window, min_periods=1).std()

    df[f'bb_middle_{window}'] = rolling_mean
    df[f'bb_upper_{window}'] = rolling_mean + (rolling_std * num_std_dev)
    df[f'bb_lower_{window}'] = rolling_mean - (rolling_std * num_std_dev)
    return df

def calculate_rsi(df, period=14):
    """Calculates Relative Strength Index (RSI)."""
    if 'close' not in df.columns or len(df) < period + 1: # RSI needs at least period+1 to calculate diff then roll
        ta_logger.warning(f"RSI: DataFrame length {len(df)} is less than period {period}+1 or 'close' column missing.")
        df[f"rsi_{period}"] = np.nan
        return df
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
    
    # Avoid division by zero if loss is 0
    # Handle Series objects properly to avoid ambiguous truth value errors
    rs = np.where(loss == 0, np.where(gain > 0, np.inf, 0), gain / loss) # if gain > 0 and loss == 0, RSI is 100. if both 0, RSI is undefined (treat as 0 or 50, here 0 then 100-100/(1+0) = 0)
    
    df[f"rsi_{period}"] = 100 - (100 / (1 + rs))
    df.loc[rs == np.inf, f"rsi_{period}"] = 100 # Handle case where loss is zero and gain is positive
    return df

def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    """Calculates Moving Average Convergence Divergence (MACD)."""
    if 'close' not in df.columns or len(df) < long_window:
        ta_logger.warning(f"MACD: DataFrame length {len(df)} is less than long_window {long_window} or 'close' column missing.")
        df["macd"] = np.nan
        df["macd_signal"] = np.nan
        df["macd_hist"] = np.nan
        return df
    short_ema = df["close"].ewm(span=short_window, adjust=False, min_periods=1).mean()
    long_ema = df["close"].ewm(span=long_window, adjust=False, min_periods=1).mean()
    df["macd"] = short_ema - long_ema
    df["macd_signal"] = df["macd"].ewm(span=signal_window, adjust=False, min_periods=1).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df

def calculate_imi(df, period=14):
    """Calculates Intraday Momentum Index (IMI)."""
    if not all(col in df.columns for col in ["open", "close"]):
        ta_logger.warning("IMI: Requires 'open' and 'close' columns.")
        df[f"imi_{period}"] = np.nan
        return df
    if len(df) < period:
        ta_logger.warning(f"IMI: Not enough data for period {period}. Need {period} rows, got {len(df)}.")
        df[f"imi_{period}"] = np.nan
        return df

    gains = df["close"] - df["open"]
    gains[df["close"] <= df["open"]] = 0
    sum_gains = gains.rolling(window=period, min_periods=1).sum()

    losses = df["open"] - df["close"]
    losses[df["close"] >= df["open"]] = 0
    sum_losses = losses.rolling(window=period, min_periods=1).sum()

    denominator = sum_gains + sum_losses
    imi_values = np.where(denominator == 0, 50.0, (sum_gains / denominator) * 100)
    
    df[f"imi_{period}"] = imi_values
    return df

def calculate_mfi(df, period=14):
    """Calculates Money Flow Index (MFI)."""
    if not all(col in df.columns for col in ["high", "low", "close", "volume"]):
        ta_logger.warning("MFI: Requires 'high', 'low', 'close', and 'volume' columns.")
        df[f"mfi_{period}"] = np.nan
        return df
    if len(df) < period + 1: # MFI uses typical_price.diff(), so needs period+1
        ta_logger.warning(f"MFI: Not enough data for period {period}. Need {period+1} rows, got {len(df)}.")
        df[f"mfi_{period}"] = np.nan
        return df

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    raw_money_flow = typical_price * df["volume"]
    money_flow_direction = typical_price.diff()

    positive_money_flow = raw_money_flow.copy()
    # Shift money_flow_direction to align with raw_money_flow for correct masking
    positive_money_flow[money_flow_direction.shift(-1) <= 0] = 0 

    negative_money_flow = raw_money_flow.copy()
    negative_money_flow[money_flow_direction.shift(-1) > 0] = 0

    sum_positive_money_flow = positive_money_flow.rolling(window=period, min_periods=1).sum()
    sum_negative_money_flow = negative_money_flow.rolling(window=period, min_periods=1).sum()

    money_flow_ratio = np.where(sum_negative_money_flow == 0, np.inf, sum_positive_money_flow / sum_negative_money_flow)
    # Handle cases where both are zero, MFR should be 1 (leading to MFI of 50)
    money_flow_ratio = np.where((sum_positive_money_flow == 0) & (sum_negative_money_flow == 0), 1, money_flow_ratio)

    mfi_values = 100 - (100 / (1 + money_flow_ratio))
    mfi_values = np.where(money_flow_ratio == np.inf, 100, mfi_values) # If sum_negative_money_flow is 0 and sum_positive is not, MFI is 100
    
    df[f"mfi_{period}"] = mfi_values
    return df

def identify_fair_value_gaps(df):
    """Identifies Fair Value Gaps (FVG)."""
    if not all(col in df.columns for col in ["high", "low"]):
        ta_logger.warning("FVG: Requires 'high' and 'low' columns.")
        df["fvg_bullish_top"] = np.nan
        df["fvg_bullish_bottom"] = np.nan
        df["fvg_bearish_top"] = np.nan
        df["fvg_bearish_bottom"] = np.nan
        return df
    
    df["fvg_bullish_top"] = np.nan
    df["fvg_bullish_bottom"] = np.nan
    df["fvg_bearish_top"] = np.nan
    df["fvg_bearish_bottom"] = np.nan

    # Ensure enough data points
    if len(df) < 3:
        ta_logger.warning(f"FVG: Not enough data points to identify gaps. Need at least 3, got {len(df)}.")
        return df

    # Use .values for faster access if df is large, but .iloc is fine for typical candle counts
    highs = df["high"].values
    lows = df["low"].values

    fvg_bullish_top_list = [np.nan] * len(df)
    fvg_bullish_bottom_list = [np.nan] * len(df)
    fvg_bearish_top_list = [np.nan] * len(df)
    fvg_bearish_bottom_list = [np.nan] * len(df)

    for i in range(1, len(df) - 1):
        # Bullish FVG: Current low is above previous high, and next low is above previous high.
        # The gap is between the high of candle i-1 and the low of candle i+1.
        # We mark the gap at candle i+1 (the candle that confirms the FVG).
        if lows[i+1] > highs[i-1]:
            fvg_bullish_top_list[i+1] = lows[i+1]
            fvg_bullish_bottom_list[i+1] = highs[i-1]

        # Bearish FVG: Current high is below previous low, and next high is below previous low.
        # The gap is between the low of candle i-1 and the high of candle i+1.
        # We mark the gap at candle i+1.
        if highs[i+1] < lows[i-1]:
            fvg_bearish_top_list[i+1] = lows[i-1]
            fvg_bearish_bottom_list[i+1] = highs[i+1]
            
    df["fvg_bullish_top"] = fvg_bullish_top_list
    df["fvg_bullish_bottom"] = fvg_bullish_bottom_list
    df["fvg_bearish_top"] = fvg_bearish_top_list
    df["fvg_bearish_bottom"] = fvg_bearish_bottom_list
    return df

def aggregate_candles(df, rule, ohlc_col_names=None):
    """Aggregates candle data to a new timeframe (e.g., '15min', '1H', '1D')."""
    if df.empty:
        ta_logger.warning(f"Aggregation: Input DataFrame is empty for rule {rule}.")
        return pd.DataFrame()
    
    if not isinstance(df.index, pd.DatetimeIndex):
        ta_logger.error("Aggregation: DataFrame index must be a DatetimeIndex.")
        # Attempt to convert if a 'datetime' column exists
        if 'datetime' in df.columns:
            try:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df = df.set_index('datetime')
                ta_logger.info("Aggregation: Converted 'datetime' column to DatetimeIndex.")
            except Exception as e:
                ta_logger.error(f"Aggregation: Failed to convert 'datetime' column to DatetimeIndex: {e}")
                return pd.DataFrame()
        else:
             return pd.DataFrame()

    # Default column names if not provided
    if ohlc_col_names is None:
        ohlc_col_names = {
            'open': 'open', 
            'high': 'high', 
            'low': 'low', 
            'close': 'close', 
            'volume': 'volume'
        }

    agg_funcs = {}
    if ohlc_col_names['open'] in df.columns: agg_funcs[ohlc_col_names['open']] = 'first'
    if ohlc_col_names['high'] in df.columns: agg_funcs[ohlc_col_names['high']] = 'max'
    if ohlc_col_names['low'] in df.columns: agg_funcs[ohlc_col_names['low']] = 'min'
    if ohlc_col_names['close'] in df.columns: agg_funcs[ohlc_col_names['close']] = 'last'
    if ohlc_col_names['volume'] in df.columns: agg_funcs[ohlc_col_names['volume']] = 'sum'
    
    if not agg_funcs:
        ta_logger.error("Aggregation: No valid OHLCV columns found for aggregation.")
        return pd.DataFrame()

    try:
        aggregated_df = df.resample(rule).agg(agg_funcs)
        aggregated_df = aggregated_df.dropna(subset=[ohlc_col_names['close']]) # Drop rows where close is NaN after resampling
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

    # Standardize column names to lowercase if they exist, for robustness
    # Expected columns: 'open', 'high', 'low', 'close', 'volume'
    # The data_fetchers.py already standardizes to lowercase 'open', 'high', 'low', 'close', 'volume', 'timestamp'
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

    df_ta = calculate_bollinger_bands(df_ta)
    df_ta = calculate_rsi(df_ta)
    df_ta = calculate_macd(df_ta)
    df_ta = calculate_imi(df_ta)
    df_ta = calculate_mfi(df_ta)
    df_ta = identify_fair_value_gaps(df_ta)
    
    # Placeholder for candle patterns if needed later
    # df_ta["candle_pattern_bullish"] = False
    # df_ta["candle_pattern_bearish"] = False

    ta_logger.info(f"Finished TA for {symbol}. DataFrame now has {len(df_ta.columns)} columns.")
    return df_ta

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
            '2023-01-01 09:48:00', '2023-01-01 09:49:00', '2023-01-01 09:50:00'
        ]),
        'open': [150.0, 150.2, 150.1, 150.5, 150.6, 150.3, 150.0, 150.2, 150.1, 150.5, 150.6, 150.3, 150.0, 150.2, 150.1, 150.5, 150.6, 150.3, 150.0, 150.2, 150.1],
        'high': [150.5, 150.6, 150.8, 150.9, 150.8, 150.7, 150.5, 150.6, 150.8, 150.9, 150.8, 150.7, 150.5, 150.6, 150.8, 150.9, 150.8, 150.7, 150.5, 150.6, 150.8],
        'low':  [149.8, 150.0, 149.9, 150.2, 150.3, 150.1, 149.8, 150.0, 149.9, 150.2, 150.3, 150.1, 149.8, 150.0, 149.9, 150.2, 150.3, 150.1, 149.8, 150.0, 149.9],
        'close':[150.3, 150.4, 150.6, 150.7, 150.5, 150.6, 150.3, 150.4, 150.6, 150.7, 150.5, 150.6, 150.3, 150.4, 150.6, 150.7, 150.5, 150.6, 150.3, 150.4, 150.6],
        'volume':[1000, 1200, 1100, 1500, 1300, 1400, 1000, 1200, 1100, 1500, 1300, 1400, 1000, 1200, 1100, 1500, 1300, 1400, 1000, 1200, 1100]
    }
    df_minute_raw = pd.DataFrame(sample_data)
    df_minute_raw = df_minute_raw.set_index('datetime')

    ta_logger.info("--- Testing Minute Data TA ---")
    df_minute_ta = calculate_all_technical_indicators(df_minute_raw.copy(), symbol="SAMPLE_MINUTE")
    if not df_minute_ta.empty:
        ta_logger.info("Minute TA Data (last 5 rows):\n%s", df_minute_ta.tail())

    ta_logger.info("\n--- Testing 15-Minute Aggregation & TA ---")
    df_15min_raw = aggregate_candles(df_minute_raw.copy(), rule="15min")
    if not df_15min_raw.empty:
        ta_logger.info("15-Min Aggregated Data (first 5 rows):\n%s", df_15min_raw.head())
        df_15min_ta = calculate_all_technical_indicators(df_15min_raw.copy(), symbol="SAMPLE_15MIN")
        if not df_15min_ta.empty:
            ta_logger.info("15-Min TA Data (last 5 rows):\n%s", df_15min_ta.tail())
    else:
        ta_logger.warning("15-minute aggregation resulted in empty data.")

    ta_logger.info("\n--- Testing Hourly Aggregation & TA ---")
    df_hourly_raw = aggregate_candles(df_minute_raw.copy(), rule="H") # 'H' for hourly
    if not df_hourly_raw.empty:
        ta_logger.info("Hourly Aggregated Data (first 5 rows):\n%s", df_hourly_raw.head())
        df_hourly_ta = calculate_all_technical_indicators(df_hourly_raw.copy(), symbol="SAMPLE_HOURLY")
        if not df_hourly_ta.empty:
            ta_logger.info("Hourly TA Data (last 5 rows):\n%s", df_hourly_ta.tail())
    else:
        ta_logger.warning("Hourly aggregation resulted in empty data.")

    ta_logger.info("\n--- Testing Daily Aggregation & TA ---")
    # For daily, we might need more varied sample data spanning multiple days
    # Using existing df_minute_raw for now, which will result in one daily candle
    df_daily_raw = aggregate_candles(df_minute_raw.copy(), rule="D") # 'D' for daily
    if not df_daily_raw.empty:
        ta_logger.info("Daily Aggregated Data (first 5 rows):\n%s", df_daily_raw.head())
        df_daily_ta = calculate_all_technical_indicators(df_daily_raw.copy(), symbol="SAMPLE_DAILY")
        if not df_daily_ta.empty:
            ta_logger.info("Daily TA Data (last 5 rows):\n%s", df_daily_ta.tail())
    else:
        ta_logger.warning("Daily aggregation resulted in empty data.")

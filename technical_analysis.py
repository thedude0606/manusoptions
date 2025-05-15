import json
import pandas as pd
import numpy as np

# Define input file paths (assuming AAPL for now, can be parameterized later)
MINUTE_DATA_FILE = "AAPL_minute_data_last_90_days.json"
HOURLY_DATA_FILE = "AAPL_hourly_data_last_90_days.json"
DAILY_DATA_FILE = "AAPL_daily_data_last_90_days.json"

# Output files for data with TA
MINUTE_DATA_WITH_TA_FILE = "AAPL_minute_data_with_ta.json"
HOURLY_DATA_WITH_TA_FILE = "AAPL_hourly_data_with_ta.json"
DAILY_DATA_WITH_TA_FILE = "AAPL_daily_data_with_ta.json"
# We also need 15-minute data for TA. We will aggregate this from minute data.
FIFTEEN_MINUTE_DATA_FILE = "AAPL_15_minute_data_last_90_days.json"
FIFTEEN_MINUTE_DATA_WITH_TA_FILE = "AAPL_15_minute_data_with_ta.json"

def load_candles(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        if "candles" not in data or not data["candles"]:
            print(f"No candles found in {file_path}")
            return pd.DataFrame()
        df = pd.DataFrame(data["candles"])
        df["datetime"] = pd.to_datetime(df["datetime"], unit="ms", utc=True)
        df = df.set_index("datetime")
        # Ensure correct data types
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors=\'coerce
olumns or len(df) < period:
        return df
    # Gains (close > open)
    gains = df["close"] - df["open"]
    gains[df["close"] <= df["open"]] = 0
    sum_gains = gains.rolling(window=period).sum()

    # Losses (close < open)
    losses = df["open"] - df["close"]
    losses[df["close"] >= df["open"]] = 0
    sum_losses = losses.rolling(window=period).sum()

    imi = (sum_gains / (sum_gains + sum_losses)) * 100
    df[f"imi_{period}"] = imi
    return df

def calculate_rsi(df, period=14):
    if \'close\' not in df.columns or len(df) < period:
        return df
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df[f"rsi_{period}"] = 100 - (100 / (1 + rs))
    return df

def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    if \'close\' not in df.columns or len(df) < long_window:
        return df
    short_ema = df["close"].ewm(span=short_window, adjust=False).mean()
    long_ema = df["close"].ewm(span=long_window, adjust=False).mean()
    df["macd"] = short_ema - long_ema
    df["macd_signal"] = df["macd"].ewm(span=signal_window, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df

def identify_fair_value_gaps(df):
    if not all(col in df.columns for col in ["high", "low"]):
        return df
    df["fvg_bullish"] = np.nan
    df["fvg_bearish"] = np.nan

    for i in range(1, len(df) - 1):
        prev_high = df["high"].iloc[i-1]
        curr_low = df["low"].iloc[i]
        curr_high = df["high"].iloc[i]
        next_low = df["low"].iloc[i+1]

        if next_low > prev_high:
            df.loc[df.index[i+1], "fvg_bullish_top"] = next_low
            df.loc[df.index[i+1], "fvg_bullish_bottom"] = prev_high
            df.loc[df.index[i+1], "fvg_bullish"] = True

        prev_low = df["low"].iloc[i-1]
        next_high = df["high"].iloc[i+1]
        if next_high < prev_low:
            df.loc[df.index[i+1], "fvg_bearish_top"] = prev_low
            df.loc[df.index[i+1], "fvg_bearish_bottom"] = next_high
            df.loc[df.index[i+1], "fvg_bearish"] = True
    return df

def save_candles_with_ta(df, output_path, symbol="AAPL"):
    if df.empty:
        print(f"DataFrame is empty, not saving to {output_path}")
        return
    df_reset = df.reset_index()
    df_reset["datetime"] = df_reset["datetime"].astype(np.int64) // 10**6
    candles_list = df_reset.to_dict(orient="records")
    with open(output_path, "w") as f:
        json.dump({"symbol": symbol, "candles": candles_list}, f, indent=2)
    print(f"Data with TA saved to {output_path}")

def aggregate_to_15_min(minute_df):
    if minute_df.empty:
        return pd.DataFrame()
    agg_funcs = {
        \'open\': \'first\',
        \'high\': \'max\',
        \'low\': \'min\',
        \'close\': \'last\',
        \'volume\': \'sum\'
    }
    fifteen_min_df = minute_df.resample(\'15min\').agg(agg_funcs)
    fifteen_min_df = fifteen_min_df.dropna()
    return fifteen_min_df

def main():
    data_files = {
        "minute": (MINUTE_DATA_FILE, MINUTE_DATA_WITH_TA_FILE),
        "15_minute": (None, FIFTEEN_MINUTE_DATA_WITH_TA_FILE),
        "hourly": (HOURLY_DATA_FILE, HOURLY_DATA_WITH_TA_FILE),
        "daily": (DAILY_DATA_FILE, DAILY_DATA_WITH_TA_FILE),
    }

    minute_df_raw = load_candles(MINUTE_DATA_FILE)
    if minute_df_raw.empty:
        print("Minute data is empty, cannot proceed with 15-minute aggregation or TA.")
        return

    fifteen_min_df_raw = aggregate_to_15_min(minute_df_raw.copy())
    if not fifteen_min_df_raw.empty:
        save_candles_with_ta(fifteen_min_df_raw, FIFTEEN_MINUTE_DATA_FILE)
        print(f"Aggregated 15-minute data saved to {FIFTEEN_MINUTE_DATA_FILE}")
    else:
        print("15-minute aggregation resulted in empty data.")

    for timeframe, (input_file, output_file) in data_files.items():
        print(f"\nProcessing {timeframe} data...")
        if timeframe == "15_minute":
            df = fifteen_min_df_raw.copy()
        elif input_file:
            df = load_candles(input_file)
        else:
            print(f"No input file for {timeframe}, skipping.")
            continue

        if df.empty:
            print(f"No data loaded for {timeframe}, skipping TA.")
            continue
        
        df = calculate_bollinger_bands(df.copy())
        df = calculate_rsi(df.copy())
        df = calculate_macd(df.copy())
        df = calculate_imi(df.copy()) # Added IMI calculation
        df = identify_fair_value_gaps(df.copy())
        df["candle_pattern_bullish"] = False
        df["candle_pattern_bearish"] = False

        save_candles_with_ta(df, output_file)
        if not df.empty:
            print(f"First 5 rows of {timeframe} data with TA:")
            print(df.head())

if __name__ == "__main__":
    main()



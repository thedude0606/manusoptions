# Technical Indicators

import pandas as pd # Ensure pandas is imported as it's used in RSI

def calculate_bollinger_bands(prices: list[float], window: int = 20, num_std_dev: int = 2) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """
    Calculates Bollinger Bands (BB) for a given list of prices.

    Args:
        prices: A list of numerical price data (e.g., closing prices).
        window: The moving average window (default is 20).
        num_std_dev: The number of standard deviations for the upper and lower bands (default is 2).

    Returns:
        A tuple containing three lists: upper_band, middle_band (SMA), and lower_band.
        Each list contains float values or None for initial periods where calculation is not possible.
    """
    if not prices or len(prices) < window:
        # Not enough data for calculation, return lists of Nones
        return [None] * len(prices), [None] * len(prices), [None] * len(prices)

    middle_band = [None] * (window - 1)  # SMA is undefined for the first window-1 periods
    upper_band = [None] * (window - 1)
    lower_band = [None] * (window - 1)

    for i in range(window - 1, len(prices)):
        current_window_prices = prices[i - window + 1 : i + 1]
        sma = sum(current_window_prices) / window
        std_dev = (sum([(price - sma) ** 2 for price in current_window_prices]) / window) ** 0.5
        
        middle_band.append(sma)
        upper_band.append(sma + (num_std_dev * std_dev))
        lower_band.append(sma - (num_std_dev * std_dev))
        
    return upper_band, middle_band, lower_band

def calculate_rsi(prices: list[float], window: int = 14) -> list[float | None]:
    """
    Calculates the Relative Strength Index (RSI) for a given list of prices.
    Uses Exponential Moving Average (EMA) for smoothing, which is common for RSI.

    Args:
        prices: A list of numerical price data (e.g., closing prices).
        window: The period for RSI calculation (default is 14).

    Returns:
        A list of RSI values (float or None for initial periods where calculation is not possible).
    """
    if not prices or len(prices) <= window:
        return [None] * len(prices)

    price_series = pd.Series(prices)
    delta = price_series.diff(1)
    delta = delta.dropna()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Calculate initial average gain and loss using SMA for the first window period
    avg_gain_initial = gain.iloc[:window].mean()
    avg_loss_initial = loss.iloc[:window].mean()

    # Prepare series for EMA calculation
    avg_gain = pd.Series([None] * len(prices))
    avg_loss = pd.Series([None] * len(prices))

    avg_gain.iloc[window] = avg_gain_initial
    avg_loss.iloc[window] = avg_loss_initial

    # Calculate subsequent average gains and losses using EMA (Wilder's smoothing)
    for i in range(window + 1, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (window - 1) + gain.iloc[i-1]) / window
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (window - 1) + loss.iloc[i-1]) / window

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    # Ensure the output list has the same length as the input prices list
    # The first RSI value is typically at index `window`
    rsi_list = [None] * window + rsi.iloc[window:].tolist()
    
    # If rsi_list is shorter than prices due to calculation steps, pad with None at the end
    while len(rsi_list) < len(prices):
        rsi_list.append(None)

    return rsi_list[:len(prices)] # Ensure it's not longer than prices

# Example Usage (can be removed or commented out in production code)
if __name__ == "__main__":
    sample_prices = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
        45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
        46.23, 46.00, 46.00, 45.80, 45.40, 45.31, 45.57, 45.36, 45.02, 45.35
    ]
    bb_window = 20
    bb_std_dev = 2
    upper, middle, lower = calculate_bollinger_bands(sample_prices, bb_window, bb_std_dev)
    print(f"--- Bollinger Bands (Window={bb_window}, StdDev={bb_std_dev}) ---")
    for i in range(len(sample_prices)):
        u_val = f"{upper[i]:.2f}" if upper[i] is not None else "None"
        m_val = f"{middle[i]:.2f}" if middle[i] is not None else "None"
        l_val = f"{lower[i]:.2f}" if lower[i] is not None else "None"
        print(f"Price: {sample_prices[i]:<6.2f} | Lower: {l_val:<8} | Middle: {m_val:<8} | Upper: {u_val:<8}")

    rsi_window = 14
    rsi_results = calculate_rsi(sample_prices, rsi_window)
    print(f"\n--- RSI (Window={rsi_window}) ---")
    for i in range(len(sample_prices)):
        rsi_val = f"{rsi_results[i]:.2f}" if rsi_results[i] is not None else "None"
        print(f"Price: {sample_prices[i]:<6.2f} | RSI: {rsi_val:<8}")


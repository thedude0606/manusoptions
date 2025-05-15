# Technical Indicators

import statistics

def calculate_bollinger_bands(prices: list[float], window: int = 20, num_std_dev: int = 2) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """
    Calculates Bollinger Bands (Upper, Middle, Lower) for a given list of prices.

    Args:
        prices: A list of numerical price data (e.g., closing prices).
        window: The period for the moving average and standard deviation (default is 20).
        num_std_dev: The number of standard deviations for the upper and lower bands (default is 2).

    Returns:
        A tuple containing three lists: 
        1. Upper Band (list of floats or None for initial periods where calculation is not possible)
        2. Middle Band (SMA - list of floats or None for initial periods)
        3. Lower Band (list of floats or None for initial periods)
    """
    if not prices or len(prices) < window:
        # Not enough data to calculate Bollinger Bands for the given window
        return ([None] * len(prices), [None] * len(prices), [None] * len(prices))

    middle_bands = [None] * (window - 1)
    upper_bands = [None] * (window - 1)
    lower_bands = [None] * (window - 1)

    for i in range(window - 1, len(prices)):
        current_window_prices = prices[i - window + 1 : i + 1]
        
        # Calculate Simple Moving Average (Middle Band)
        sma = sum(current_window_prices) / window
        middle_bands.append(sma)
        
        # Calculate Standard Deviation
        if len(current_window_prices) > 1:
            std_dev = statistics.stdev(current_window_prices)
        else:
            std_dev = 0 # Or handle as an error/None if preferred for single point window
            
        # Calculate Upper and Lower Bands
        upper_band = sma + (num_std_dev * std_dev)
        lower_band = sma - (num_std_dev * std_dev)
        
        upper_bands.append(upper_band)
        lower_bands.append(lower_band)
        
    return upper_bands, middle_bands, lower_bands

# Example Usage (can be removed or commented out in production code)
if __name__ == "__main__":
    sample_prices = [
        10, 10.5, 11, 10.8, 11.2, 11.5, 11.3, 11.8, 12, 12.3, 
        12.5, 12.1, 11.9, 12.4, 12.8, 13, 13.2, 12.9, 13.5, 14,
        14.2, 13.8, 14.5, 15, 14.7, 14.3, 14.8, 15.2, 15.5, 15.1
    ]
    
    window_size = 5
    std_devs = 2
    
    upper, middle, lower = calculate_bollinger_bands(sample_prices, window_size, std_devs)
    
    print(f"Prices: {sample_prices}")
    print(f"Upper Bands (Window={window_size}, StdDev={std_devs}): {upper}")
    print(f"Middle Bands (SMA, Window={window_size}): {middle}")
    print(f"Lower Bands (Window={window_size}, StdDev={std_devs}): {lower}")

    for i in range(len(sample_prices)):
        print(f"Price: {sample_prices[i]:<6} | SMA: {middle[i]:<8.2f} | Upper: {upper[i]:<8.2f} | Lower: {lower[i]:<8.2f}" if middle[i] is not None else f"Price: {sample_prices[i]:<6} | SMA: None     | Upper: None     | Lower: None")


#!/usr/bin/env python3
# sample_data_generator.py
# Script to generate sample data for validation testing

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse

def generate_sample_data(symbol, num_candles=1000, start_date=None):
    """Generate sample OHLCV data for testing."""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=5)
    
    # Generate timestamps at 1-minute intervals
    timestamps = [start_date + timedelta(minutes=i) for i in range(num_candles)]
    
    # Generate random price data with some trend and volatility
    base_price = 150.0
    trend = np.cumsum(np.random.normal(0, 0.1, num_candles))
    volatility = np.random.normal(0, 0.5, num_candles)
    
    # Generate OHLCV data
    data = []
    for i in range(num_candles):
        price = base_price + trend[i] + volatility[i]
        open_price = price
        high_price = price + abs(np.random.normal(0, 0.3))
        low_price = price - abs(np.random.normal(0, 0.3))
        close_price = np.random.normal(price, 0.2)
        volume = int(np.random.normal(1000, 300))
        
        data.append({
            'timestamp': timestamps[i],
            'Open': open_price,
            'High': high_price,
            'Low': low_price,
            'Close': close_price,
            'Volume': volume
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    return df

def save_sample_data(df, output_file):
    """Save sample data to CSV file."""
    df.to_csv(output_file, index=False)
    print(f"Sample data saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Generate sample OHLCV data for validation testing')
    parser.add_argument('--symbol', type=str, default='MSFT', help='Symbol for sample data')
    parser.add_argument('--num-candles', type=int, default=1000, help='Number of candles to generate')
    parser.add_argument('--output-file', type=str, default='sample_data.csv', help='Output file path')
    args = parser.parse_args()
    
    df = generate_sample_data(args.symbol, args.num_candles)
    save_sample_data(df, args.output_file)

if __name__ == '__main__':
    main()

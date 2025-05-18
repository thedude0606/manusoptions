"""
Candlestick Pattern Detection Module

This module provides functions to detect various candlestick patterns in price data.
It includes both traditional Japanese candlestick patterns and advanced price action concepts.

Traditional patterns include:
- Single candle patterns (Hammer, Hanging Man, Doji, etc.)
- Multi-candle patterns (Engulfing, Morning/Evening Star, etc.)

Advanced concepts include:
- Order Blocks
- Liquidity Grabs
- Market Structure Shifts
- Mitigation Blocks
"""

import pandas as pd
import numpy as np
import logging

# Configure basic logging for the module
cs_logger = logging.getLogger(__name__)
if not cs_logger.hasHandlers():
    cs_handler = logging.StreamHandler()
    cs_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    cs_handler.setFormatter(cs_formatter)
    cs_logger.addHandler(cs_handler)
cs_logger.setLevel(logging.INFO)

# =============================================
# Single Candlestick Pattern Detection Functions
# =============================================

def detect_doji(df, doji_threshold=0.05):
    """
    Detects Doji candlestick patterns.
    
    A Doji has nearly equal open and close prices, forming a cross or plus sign.
    It represents indecision in the market with no clear winner between bulls and bears.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    doji_threshold : float, default 0.05
        Maximum percentage difference between open and close relative to the high-low range
        to be considered a Doji
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'doji' column added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Doji: Requires 'open', 'high', 'low', 'close' columns.")
        df['doji'] = np.nan
        return df
    
    # Calculate body size (absolute difference between open and close)
    body_size = abs(df['close'] - df['open'])
    
    # Calculate candle range (high - low)
    candle_range = df['high'] - df['low']
    
    # Avoid division by zero
    valid_range = candle_range > 0
    body_to_range_ratio = np.zeros(len(df))
    body_to_range_ratio[valid_range] = body_size[valid_range] / candle_range[valid_range]
    
    # Identify Doji patterns (body is very small compared to the range)
    df['doji'] = body_to_range_ratio <= doji_threshold
    
    return df

def detect_hammer_hanging_man(df, body_threshold=0.3, shadow_threshold=2.0):
    """
    Detects Hammer and Hanging Man candlestick patterns.
    
    Both patterns have a small body near the top with a long lower shadow.
    - Hammer: appears in a downtrend, signaling potential bullish reversal
    - Hanging Man: appears in an uptrend, signaling potential bearish reversal
    
    The pattern itself is the same; context determines whether it's a Hammer or Hanging Man.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    body_threshold : float, default 0.3
        Maximum ratio of body size to candle range to qualify
    shadow_threshold : float, default 2.0
        Minimum ratio of lower shadow to body size to qualify
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'hammer_hanging_man' column added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Hammer/Hanging Man: Requires 'open', 'high', 'low', 'close' columns.")
        df['hammer_hanging_man'] = np.nan
        return df
    
    # Calculate body size (absolute difference between open and close)
    body_size = abs(df['close'] - df['open'])
    
    # Calculate candle range (high - low)
    candle_range = df['high'] - df['low']
    
    # Calculate upper and lower shadows
    upper_shadow = np.where(df['close'] >= df['open'], 
                           df['high'] - df['close'], 
                           df['high'] - df['open'])
    
    lower_shadow = np.where(df['close'] >= df['open'], 
                           df['open'] - df['low'], 
                           df['close'] - df['low'])
    
    # Avoid division by zero
    valid_range = candle_range > 0
    valid_body = body_size > 0
    
    body_to_range_ratio = np.zeros(len(df))
    body_to_range_ratio[valid_range] = body_size[valid_range] / candle_range[valid_range]
    
    lower_to_body_ratio = np.zeros(len(df))
    lower_to_body_ratio[valid_body] = lower_shadow[valid_body] / body_size[valid_body]
    
    # Identify Hammer/Hanging Man patterns
    # 1. Small body (body_to_range_ratio <= body_threshold)
    # 2. Long lower shadow (lower_to_body_ratio >= shadow_threshold)
    # 3. Small upper shadow (upper_shadow should be small compared to lower_shadow)
    df['hammer_hanging_man'] = (
        (body_to_range_ratio <= body_threshold) & 
        (lower_to_body_ratio >= shadow_threshold) & 
        (upper_shadow < lower_shadow / 2)
    )
    
    return df

def detect_inverted_hammer_shooting_star(df, body_threshold=0.3, shadow_threshold=2.0):
    """
    Detects Inverted Hammer and Shooting Star candlestick patterns.
    
    Both patterns have a small body near the bottom with a long upper shadow.
    - Inverted Hammer: appears in a downtrend, signaling potential bullish reversal
    - Shooting Star: appears in an uptrend, signaling potential bearish reversal
    
    The pattern itself is the same; context determines whether it's an Inverted Hammer or Shooting Star.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    body_threshold : float, default 0.3
        Maximum ratio of body size to candle range to qualify
    shadow_threshold : float, default 2.0
        Minimum ratio of upper shadow to body size to qualify
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'inverted_hammer_shooting_star' column added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Inverted Hammer/Shooting Star: Requires 'open', 'high', 'low', 'close' columns.")
        df['inverted_hammer_shooting_star'] = np.nan
        return df
    
    # Calculate body size (absolute difference between open and close)
    body_size = abs(df['close'] - df['open'])
    
    # Calculate candle range (high - low)
    candle_range = df['high'] - df['low']
    
    # Calculate upper and lower shadows
    upper_shadow = np.where(df['close'] >= df['open'], 
                           df['high'] - df['close'], 
                           df['high'] - df['open'])
    
    lower_shadow = np.where(df['close'] >= df['open'], 
                           df['open'] - df['low'], 
                           df['close'] - df['low'])
    
    # Avoid division by zero
    valid_range = candle_range > 0
    valid_body = body_size > 0
    
    body_to_range_ratio = np.zeros(len(df))
    body_to_range_ratio[valid_range] = body_size[valid_range] / candle_range[valid_range]
    
    upper_to_body_ratio = np.zeros(len(df))
    upper_to_body_ratio[valid_body] = upper_shadow[valid_body] / body_size[valid_body]
    
    # Identify Inverted Hammer/Shooting Star patterns
    # 1. Small body (body_to_range_ratio <= body_threshold)
    # 2. Long upper shadow (upper_to_body_ratio >= shadow_threshold)
    # 3. Small lower shadow (lower_shadow should be small compared to upper_shadow)
    df['inverted_hammer_shooting_star'] = (
        (body_to_range_ratio <= body_threshold) & 
        (upper_to_body_ratio >= shadow_threshold) & 
        (lower_shadow < upper_shadow / 2)
    )
    
    return df

def detect_marubozu(df, body_threshold=0.9):
    """
    Detects Marubozu candlestick patterns.
    
    A Marubozu has a long body with very small or no shadows, indicating strong conviction.
    - Bullish Marubozu: long green candle with little to no shadows
    - Bearish Marubozu: long red candle with little to no shadows
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    body_threshold : float, default 0.9
        Minimum ratio of body size to candle range to qualify as a Marubozu
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'bullish_marubozu' and 'bearish_marubozu' columns added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Marubozu: Requires 'open', 'high', 'low', 'close' columns.")
        df['bullish_marubozu'] = np.nan
        df['bearish_marubozu'] = np.nan
        return df
    
    # Calculate body size (absolute difference between open and close)
    body_size = abs(df['close'] - df['open'])
    
    # Calculate candle range (high - low)
    candle_range = df['high'] - df['low']
    
    # Avoid division by zero
    valid_range = candle_range > 0
    body_to_range_ratio = np.zeros(len(df))
    body_to_range_ratio[valid_range] = body_size[valid_range] / candle_range[valid_range]
    
    # Identify Marubozu patterns
    # Bullish Marubozu: close > open and body takes up most of the range
    df['bullish_marubozu'] = (
        (df['close'] > df['open']) & 
        (body_to_range_ratio >= body_threshold)
    )
    
    # Bearish Marubozu: close < open and body takes up most of the range
    df['bearish_marubozu'] = (
        (df['close'] < df['open']) & 
        (body_to_range_ratio >= body_threshold)
    )
    
    return df

# =============================================
# Multi-Candlestick Pattern Detection Functions
# =============================================

def detect_engulfing(df, body_threshold=0.1):
    """
    Detects Bullish and Bearish Engulfing candlestick patterns.
    
    Engulfing patterns occur when a candle's body completely engulfs the previous candle's body.
    - Bullish Engulfing: a bullish (green) candle engulfs the previous bearish (red) candle
    - Bearish Engulfing: a bearish (red) candle engulfs the previous bullish (green) candle
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    body_threshold : float, default 0.1
        Minimum body size relative to the candle range to be considered significant
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'bullish_engulfing' and 'bearish_engulfing' columns added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Engulfing: Requires 'open', 'high', 'low', 'close' columns.")
        df['bullish_engulfing'] = np.nan
        df['bearish_engulfing'] = np.nan
        return df
    
    if len(df) < 2:
        cs_logger.warning("Engulfing: Requires at least 2 candles.")
        df['bullish_engulfing'] = np.nan
        df['bearish_engulfing'] = np.nan
        return df
    
    # Calculate body size (absolute difference between open and close)
    body_size = abs(df['close'] - df['open'])
    
    # Calculate candle range (high - low)
    candle_range = df['high'] - df['low']
    
    # Avoid division by zero
    valid_range = candle_range > 0
    body_to_range_ratio = np.zeros(len(df))
    body_to_range_ratio[valid_range] = body_size[valid_range] / candle_range[valid_range]
    
    # Initialize pattern columns
    df['bullish_engulfing'] = False
    df['bearish_engulfing'] = False
    
    # Identify Engulfing patterns
    for i in range(1, len(df)):
        # Current candle must have a significant body
        if body_to_range_ratio[i] < body_threshold:
            continue
        
        # Previous candle's body
        prev_open = df['open'].iloc[i-1]
        prev_close = df['close'].iloc[i-1]
        prev_body_min = min(prev_open, prev_close)
        prev_body_max = max(prev_open, prev_close)
        
        # Current candle's body
        curr_open = df['open'].iloc[i]
        curr_close = df['close'].iloc[i]
        curr_body_min = min(curr_open, curr_close)
        curr_body_max = max(curr_open, curr_close)
        
        # Bullish Engulfing: current candle is bullish, previous is bearish, and current body engulfs previous body
        if (curr_close > curr_open and  # Current candle is bullish
            prev_close < prev_open and  # Previous candle is bearish
            curr_body_min <= prev_body_min and  # Current body engulfs previous body
            curr_body_max >= prev_body_max):
            df.loc[df.index[i], 'bullish_engulfing'] = True
        
        # Bearish Engulfing: current candle is bearish, previous is bullish, and current body engulfs previous body
        elif (curr_close < curr_open and  # Current candle is bearish
              prev_close > prev_open and  # Previous candle is bullish
              curr_body_min <= prev_body_min and  # Current body engulfs previous body
              curr_body_max >= prev_body_max):
            df.loc[df.index[i], 'bearish_engulfing'] = True
    
    return df

def detect_morning_evening_star(df, doji_threshold=0.05, body_threshold=0.5):
    """
    Detects Morning Star and Evening Star candlestick patterns.
    
    Morning Star is a bullish reversal pattern consisting of:
    1. A large bearish candle
    2. A small-bodied candle (often a doji) that gaps down
    3. A large bullish candle that closes above the midpoint of the first candle
    
    Evening Star is a bearish reversal pattern consisting of:
    1. A large bullish candle
    2. A small-bodied candle (often a doji) that gaps up
    3. A large bearish candle that closes below the midpoint of the first candle
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    doji_threshold : float, default 0.05
        Maximum ratio of body size to candle range for the middle candle
    body_threshold : float, default 0.5
        Minimum ratio of body size to candle range for the first and third candles
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'morning_star' and 'evening_star' columns added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Morning/Evening Star: Requires 'open', 'high', 'low', 'close' columns.")
        df['morning_star'] = np.nan
        df['evening_star'] = np.nan
        return df
    
    if len(df) < 3:
        cs_logger.warning("Morning/Evening Star: Requires at least 3 candles.")
        df['morning_star'] = np.nan
        df['evening_star'] = np.nan
        return df
    
    # Calculate body size (absolute difference between open and close)
    body_size = abs(df['close'] - df['open'])
    
    # Calculate candle range (high - low)
    candle_range = df['high'] - df['low']
    
    # Avoid division by zero
    valid_range = candle_range > 0
    body_to_range_ratio = np.zeros(len(df))
    body_to_range_ratio[valid_range] = body_size[valid_range] / candle_range[valid_range]
    
    # Initialize pattern columns
    df['morning_star'] = False
    df['evening_star'] = False
    
    # Identify Morning Star and Evening Star patterns
    for i in range(2, len(df)):
        # First candle body size check
        if body_to_range_ratio[i-2] < body_threshold:
            continue
            
        # Middle candle should have a small body (doji-like)
        if body_to_range_ratio[i-1] > doji_threshold:
            continue
            
        # Third candle body size check
        if body_to_range_ratio[i] < body_threshold:
            continue
        
        # Morning Star pattern
        if (df['close'].iloc[i-2] < df['open'].iloc[i-2] and  # First candle is bearish
            df['close'].iloc[i] > df['open'].iloc[i] and  # Third candle is bullish
            max(df['open'].iloc[i-1], df['close'].iloc[i-1]) < df['close'].iloc[i-2] and  # Middle candle gaps down
            df['close'].iloc[i] > (df['open'].iloc[i-2] + df['close'].iloc[i-2]) / 2):  # Third candle closes above midpoint of first
            df.loc[df.index[i], 'morning_star'] = True
        
        # Evening Star pattern
        elif (df['close'].iloc[i-2] > df['open'].iloc[i-2] and  # First candle is bullish
              df['close'].iloc[i] < df['open'].iloc[i] and  # Third candle is bearish
              min(df['open'].iloc[i-1], df['close'].iloc[i-1]) > df['close'].iloc[i-2] and  # Middle candle gaps up
              df['close'].iloc[i] < (df['open'].iloc[i-2] + df['close'].iloc[i-2]) / 2):  # Third candle closes below midpoint of first
            df.loc[df.index[i], 'evening_star'] = True
    
    return df

def detect_harami(df, body_threshold=0.5):
    """
    Detects Bullish and Bearish Harami candlestick patterns.
    
    Harami is a reversal pattern where a small-bodied candle is contained within the body of the previous larger candle.
    - Bullish Harami: a large bearish candle followed by a small bullish candle contained within its body
    - Bearish Harami: a large bullish candle followed by a small bearish candle contained within its body
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    body_threshold : float, default 0.5
        Minimum ratio of first candle's body size to its range to be considered significant
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'bullish_harami' and 'bearish_harami' columns added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Harami: Requires 'open', 'high', 'low', 'close' columns.")
        df['bullish_harami'] = np.nan
        df['bearish_harami'] = np.nan
        return df
    
    if len(df) < 2:
        cs_logger.warning("Harami: Requires at least 2 candles.")
        df['bullish_harami'] = np.nan
        df['bearish_harami'] = np.nan
        return df
    
    # Calculate body size (absolute difference between open and close)
    body_size = abs(df['close'] - df['open'])
    
    # Calculate candle range (high - low)
    candle_range = df['high'] - df['low']
    
    # Avoid division by zero
    valid_range = candle_range > 0
    body_to_range_ratio = np.zeros(len(df))
    body_to_range_ratio[valid_range] = body_size[valid_range] / candle_range[valid_range]
    
    # Initialize pattern columns
    df['bullish_harami'] = False
    df['bearish_harami'] = False
    
    # Identify Harami patterns
    for i in range(1, len(df)):
        # First candle must have a significant body
        if body_to_range_ratio[i-1] < body_threshold:
            continue
        
        # Previous candle's body
        prev_open = df['open'].iloc[i-1]
        prev_close = df['close'].iloc[i-1]
        prev_body_min = min(prev_open, prev_close)
        prev_body_max = max(prev_open, prev_close)
        
        # Current candle's body
        curr_open = df['open'].iloc[i]
        curr_close = df['close'].iloc[i]
        curr_body_min = min(curr_open, curr_close)
        curr_body_max = max(curr_open, curr_close)
        
        # Bullish Harami: previous candle is bearish, current is bullish, and current body is inside previous body
        if (prev_close < prev_open and  # Previous candle is bearish
            curr_close > curr_open and  # Current candle is bullish
            curr_body_min >= prev_body_min and  # Current body is inside previous body
            curr_body_max <= prev_body_max):
            df.loc[df.index[i], 'bullish_harami'] = True
        
        # Bearish Harami: previous candle is bullish, current is bearish, and current body is inside previous body
        elif (prev_close > prev_open and  # Previous candle is bullish
              curr_close < curr_open and  # Current candle is bearish
              curr_body_min >= prev_body_min and  # Current body is inside previous body
              curr_body_max <= prev_body_max):
            df.loc[df.index[i], 'bearish_harami'] = True
    
    return df

# =============================================
# Advanced Price Action Concepts
# =============================================

def detect_order_blocks(df, lookback=10, strength_threshold=0.7):
    """
    Detects potential Order Blocks in price data.
    
    An Order Block is a zone where institutional orders are placed, often appearing as
    a consolidation or opposite-colored candle right before a strong impulse move.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    lookback : int, default 10
        Number of candles to look back for detecting impulse moves
    strength_threshold : float, default 0.7
        Threshold for determining the strength of an impulse move (0-1)
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'bullish_order_block' and 'bearish_order_block' columns added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Order Blocks: Requires 'open', 'high', 'low', 'close' columns.")
        df['bullish_order_block'] = np.nan
        df['bearish_order_block'] = np.nan
        return df
    
    if len(df) < lookback + 2:
        cs_logger.warning(f"Order Blocks: Requires at least {lookback + 2} candles.")
        df['bullish_order_block'] = np.nan
        df['bearish_order_block'] = np.nan
        return df
    
    # Initialize pattern columns
    df['bullish_order_block'] = False
    df['bearish_order_block'] = False
    
    # Calculate candle direction (bullish or bearish)
    candle_bullish = df['close'] > df['open']
    
    # Detect impulse moves and their preceding order blocks
    for i in range(lookback + 1, len(df)):
        # Check for bullish impulse move
        if df['close'].iloc[i] > df['close'].iloc[i-lookback]:
            # Calculate the strength of the move
            move_range = df['close'].iloc[i] - df['close'].iloc[i-lookback]
            max_range = df['high'].iloc[i-lookback:i+1].max() - df['low'].iloc[i-lookback:i+1].min()
            
            if max_range > 0 and move_range / max_range >= strength_threshold:
                # Look for the last bearish candle before the impulse
                for j in range(i-1, i-lookback-1, -1):
                    if not candle_bullish.iloc[j]:
                        # This bearish candle is a potential bullish order block
                        df.loc[df.index[j], 'bullish_order_block'] = True
                        break
        
        # Check for bearish impulse move
        if df['close'].iloc[i] < df['close'].iloc[i-lookback]:
            # Calculate the strength of the move
            move_range = df['close'].iloc[i-lookback] - df['close'].iloc[i]
            max_range = df['high'].iloc[i-lookback:i+1].max() - df['low'].iloc[i-lookback:i+1].min()
            
            if max_range > 0 and move_range / max_range >= strength_threshold:
                # Look for the last bullish candle before the impulse
                for j in range(i-1, i-lookback-1, -1):
                    if candle_bullish.iloc[j]:
                        # This bullish candle is a potential bearish order block
                        df.loc[df.index[j], 'bearish_order_block'] = True
                        break
    
    return df

def detect_liquidity_grabs(df, threshold=0.6):
    """
    Detects potential Liquidity Grab (stop hunt) patterns.
    
    A Liquidity Grab occurs when price temporarily pierces a support/resistance level
    to trigger stop-loss orders, then reverses direction, often leaving a long wick.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    threshold : float, default 0.6
        Minimum ratio of wick to total candle range to qualify as a liquidity grab
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'bullish_liquidity_grab' and 'bearish_liquidity_grab' columns added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Liquidity Grabs: Requires 'open', 'high', 'low', 'close' columns.")
        df['bullish_liquidity_grab'] = np.nan
        df['bearish_liquidity_grab'] = np.nan
        return df
    
    # Calculate body size and position
    body_size = abs(df['close'] - df['open'])
    body_low = df[['open', 'close']].min(axis=1)
    body_high = df[['open', 'close']].max(axis=1)
    
    # Calculate candle range and wicks
    candle_range = df['high'] - df['low']
    upper_wick = df['high'] - body_high
    lower_wick = body_low - df['low']
    
    # Avoid division by zero
    valid_range = candle_range > 0
    
    # Calculate wick to range ratios
    upper_wick_ratio = np.zeros(len(df))
    lower_wick_ratio = np.zeros(len(df))
    
    upper_wick_ratio[valid_range] = upper_wick[valid_range] / candle_range[valid_range]
    lower_wick_ratio[valid_range] = lower_wick[valid_range] / candle_range[valid_range]
    
    # Identify liquidity grabs
    # Bullish liquidity grab: long lower wick (price dropped to grab liquidity then recovered)
    df['bullish_liquidity_grab'] = (
        (lower_wick_ratio >= threshold) & 
        (df['close'] > df['open'])  # Closed bullish after the grab
    )
    
    # Bearish liquidity grab: long upper wick (price rose to grab liquidity then fell)
    df['bearish_liquidity_grab'] = (
        (upper_wick_ratio >= threshold) & 
        (df['close'] < df['open'])  # Closed bearish after the grab
    )
    
    return df

def detect_market_structure_shifts(df, lookback=5):
    """
    Detects Market Structure Shifts (changes in trend structure).
    
    A market structure shift occurs when a series of higher highs/higher lows (uptrend)
    or lower highs/lower lows (downtrend) is broken, indicating a potential trend change.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    lookback : int, default 5
        Number of candles to analyze for structure
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'bullish_structure_shift' and 'bearish_structure_shift' columns added
    """
    if not all(col in df.columns for col in ['high', 'low']):
        cs_logger.warning("Market Structure: Requires 'high' and 'low' columns.")
        df['bullish_structure_shift'] = np.nan
        df['bearish_structure_shift'] = np.nan
        return df
    
    if len(df) < lookback + 2:
        cs_logger.warning(f"Market Structure: Requires at least {lookback + 2} candles.")
        df['bullish_structure_shift'] = np.nan
        df['bearish_structure_shift'] = np.nan
        return df
    
    # Initialize pattern columns
    df['bullish_structure_shift'] = False
    df['bearish_structure_shift'] = False
    
    # Detect structure shifts
    for i in range(lookback + 1, len(df)):
        # Get recent swing lows and highs
        recent_lows = df['low'].iloc[i-lookback:i]
        recent_highs = df['high'].iloc[i-lookback:i]
        
        # Find the minimum low and maximum high in the recent range
        min_low = recent_lows.min()
        max_high = recent_highs.max()
        
        # Bullish structure shift: breaking above recent high after a downtrend
        # We look for a series of lower highs before the breakout
        lower_highs = True
        for j in range(i-lookback+1, i):
            if df['high'].iloc[j] > df['high'].iloc[j-1]:
                lower_highs = False
                break
        
        if lower_highs and df['high'].iloc[i] > max_high:
            df.loc[df.index[i], 'bullish_structure_shift'] = True
        
        # Bearish structure shift: breaking below recent low after an uptrend
        # We look for a series of higher lows before the breakdown
        higher_lows = True
        for j in range(i-lookback+1, i):
            if df['low'].iloc[j] < df['low'].iloc[j-1]:
                higher_lows = False
                break
        
        if higher_lows and df['low'].iloc[i] < min_low:
            df.loc[df.index[i], 'bearish_structure_shift'] = True
    
    return df

def detect_mitigation_blocks(df, lookback=20, retest_threshold=0.05):
    """
    Detects Mitigation Blocks in price data.
    
    A Mitigation Block is a failed order block that still influences price.
    When price returns to this area, large traders often use it to exit positions.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    lookback : int, default 20
        Number of candles to look back for detecting mitigation blocks
    retest_threshold : float, default 0.05
        Maximum percentage difference to consider a level retested
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with 'bullish_mitigation_block' and 'bearish_mitigation_block' columns added
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        cs_logger.warning("Mitigation Blocks: Requires 'open', 'high', 'low', 'close' columns.")
        df['bullish_mitigation_block'] = np.nan
        df['bearish_mitigation_block'] = np.nan
        return df
    
    if len(df) < lookback + 5:  # Need enough data to detect order blocks and their failure
        cs_logger.warning(f"Mitigation Blocks: Requires at least {lookback + 5} candles.")
        df['bullish_mitigation_block'] = np.nan
        df['bearish_mitigation_block'] = np.nan
        return df
    
    # First, detect order blocks
    df = detect_order_blocks(df, lookback=lookback)
    
    # Initialize mitigation block columns
    df['bullish_mitigation_block'] = False
    df['bearish_mitigation_block'] = False
    
    # Identify mitigation blocks (failed order blocks that get retested)
    for i in range(lookback + 5, len(df)):
        # Check for bullish order blocks that failed (price returned below the block)
        for j in range(i-lookback, i-3):
            if df['bullish_order_block'].iloc[j]:
                # Define the order block zone
                ob_high = df['high'].iloc[j]
                ob_low = df['low'].iloc[j]
                ob_mid = (ob_high + ob_low) / 2
                
                # Check if price initially moved up from the order block
                initial_move_up = False
                for k in range(j+1, j+5):
                    if k < len(df) and df['high'].iloc[k] > ob_high:
                        initial_move_up = True
                        break
                
                if initial_move_up:
                    # Check if price later returned below the order block (failure)
                    failed = False
                    for k in range(j+5, i-2):
                        if df['low'].iloc[k] < ob_low:
                            failed = True
                            break
                    
                    if failed:
                        # Check if price is now retesting the failed order block
                        current_price = df['close'].iloc[i]
                        price_diff_pct = abs(current_price - ob_mid) / ob_mid
                        
                        if price_diff_pct <= retest_threshold:
                            df.loc[df.index[i], 'bullish_mitigation_block'] = True
        
        # Check for bearish order blocks that failed (price returned above the block)
        for j in range(i-lookback, i-3):
            if df['bearish_order_block'].iloc[j]:
                # Define the order block zone
                ob_high = df['high'].iloc[j]
                ob_low = df['low'].iloc[j]
                ob_mid = (ob_high + ob_low) / 2
                
                # Check if price initially moved down from the order block
                initial_move_down = False
                for k in range(j+1, j+5):
                    if k < len(df) and df['low'].iloc[k] < ob_low:
                        initial_move_down = True
                        break
                
                if initial_move_down:
                    # Check if price later returned above the order block (failure)
                    failed = False
                    for k in range(j+5, i-2):
                        if df['high'].iloc[k] > ob_high:
                            failed = True
                            break
                    
                    if failed:
                        # Check if price is now retesting the failed order block
                        current_price = df['close'].iloc[i]
                        price_diff_pct = abs(current_price - ob_mid) / ob_mid
                        
                        if price_diff_pct <= retest_threshold:
                            df.loc[df.index[i], 'bearish_mitigation_block'] = True
    
    return df

# =============================================
# Main Function to Calculate All Patterns
# =============================================

def calculate_all_candlestick_patterns(df, symbol="N/A"):
    """
    Calculates all defined candlestick patterns for the given DataFrame.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    symbol : str, default "N/A"
        Symbol identifier for logging purposes
        
    Returns:
    --------
    pandas.DataFrame
        Input DataFrame with all candlestick pattern columns added
    """
    if df.empty:
        cs_logger.warning(f"Candlestick Patterns: Input DataFrame for {symbol} is empty. Skipping calculations.")
        return df

    # Ensure DataFrame is a copy to avoid SettingWithCopyWarning
    df_cs = df.copy()

    # Standardize column names to lowercase if they exist
    rename_map = {col: col.lower() for col in df_cs.columns if col.lower() in ['open', 'high', 'low', 'close', 'volume']}
    if rename_map:
        df_cs.rename(columns=rename_map, inplace=True)

    # Check for required columns
    required_cols = ['open', 'high', 'low', 'close']
    missing_cols = [col for col in required_cols if col not in df_cs.columns]
    if missing_cols:
        cs_logger.error(f"Candlestick Patterns: DataFrame for {symbol} is missing essential columns: {missing_cols}.")
        return df

    cs_logger.info(f"Calculating candlestick patterns for {symbol} on DataFrame with {len(df_cs)} rows.")

    # Calculate single candlestick patterns
    df_cs = detect_doji(df_cs)
    df_cs = detect_hammer_hanging_man(df_cs)
    df_cs = detect_inverted_hammer_shooting_star(df_cs)
    df_cs = detect_marubozu(df_cs)
    
    # Calculate multi-candlestick patterns
    df_cs = detect_engulfing(df_cs)
    df_cs = detect_morning_evening_star(df_cs)
    df_cs = detect_harami(df_cs)
    
    # Calculate advanced price action concepts
    df_cs = detect_order_blocks(df_cs)
    df_cs = detect_liquidity_grabs(df_cs)
    df_cs = detect_market_structure_shifts(df_cs)
    df_cs = detect_mitigation_blocks(df_cs)

    cs_logger.info(f"Finished candlestick pattern detection for {symbol}. DataFrame now has {len(df_cs.columns)} columns.")
    return df_cs

# Example usage (can be removed or kept for standalone testing)
if __name__ == '__main__':
    # Create a sample DataFrame (mimicking fetched stock data)
    sample_data = {
        'datetime': pd.date_range(start='2023-01-01', periods=30, freq='D'),
        'open': [100, 102, 104, 103, 105, 107, 108, 109, 110, 112, 
                 111, 110, 109, 108, 107, 105, 104, 103, 102, 101,
                 100, 99, 97, 95, 94, 93, 92, 91, 90, 92],
        'high': [105, 106, 107, 108, 110, 112, 113, 114, 115, 116, 
                 115, 114, 113, 112, 111, 110, 108, 107, 106, 105,
                 104, 103, 102, 100, 98, 97, 96, 95, 94, 96],
        'low': [98, 100, 102, 101, 103, 105, 106, 107, 108, 110, 
                109, 108, 107, 106, 105, 103, 102, 101, 100, 99,
                98, 97, 95, 93, 92, 91, 90, 89, 88, 90],
        'close': [102, 104, 103, 105, 107, 108, 109, 110, 112, 111, 
                  110, 109, 108, 107, 105, 104, 103, 102, 101, 100,
                  99, 97, 95, 94, 93, 92, 91, 90, 92, 94],
        'volume': [1000, 1200, 1100, 1300, 1500, 1600, 1700, 1800, 2000, 1900,
                   1800, 1700, 1600, 1500, 1400, 1300, 1200, 1100, 1000, 900,
                   800, 700, 600, 500, 400, 300, 200, 100, 200, 300]
    }
    
    sample_df = pd.DataFrame(sample_data)
    sample_df.set_index('datetime', inplace=True)
    
    # Calculate all candlestick patterns
    result_df = calculate_all_candlestick_patterns(sample_df, symbol="SAMPLE")
    
    # Print columns to see what patterns were detected
    print("Candlestick pattern columns:", [col for col in result_df.columns if col not in sample_df.columns])
    
    # Print rows where patterns were detected
    for col in [c for c in result_df.columns if c not in sample_df.columns]:
        if result_df[col].any():
            print(f"\nDetected {col}:")
            print(result_df.loc[result_df[col], ['open', 'high', 'low', 'close']])

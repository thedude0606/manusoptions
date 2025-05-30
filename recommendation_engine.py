"""
Recommendation Engine for Options Trading

This module provides functionality to analyze technical indicators and options chain data
to generate actionable buy/sell recommendations with confidence scores.

The engine focuses on:
1. Analyzing technical indicators to identify potential market direction
2. Evaluating options chain data for optimal strike prices and expiration dates
3. Calculating risk/reward ratios for potential trades
4. Generating actionable buy/sell signals with confidence scores

The recommendations target hourly trading and swing trading with a minimum expected profit of 10%.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Constants for recommendation engine
CONFIDENCE_THRESHOLD = 30  # Minimum confidence score to include in recommendations - Adjusted for better filtering
MAX_RECOMMENDATIONS = 5    # Maximum number of recommendations to return
MIN_EXPECTED_PROFIT = 0.05  # 5% minimum expected profit
MAX_EXPECTED_PROFIT = 0.50  # 50% maximum expected profit - Added cap for realistic profit expectations
TARGET_TIMEFRAMES = ["1hour", "4hour"]  # Target timeframes for analysis

class RecommendationEngine:
    """
    Engine for generating options trading recommendations based on
    technical indicators and options chain data.
    """
    
    def __init__(self):
        """Initialize the recommendation engine."""
        logger.info("Initializing recommendation engine")
    
    def analyze_market_direction(self, tech_indicators_df, timeframe="1hour"):
        """
        Analyze technical indicators to determine potential market direction.
        
        Args:
            tech_indicators_df: DataFrame containing technical indicators
            timeframe: Timeframe to analyze (e.g., "1hour", "4hour")
            
        Returns:
            dict: Market direction analysis with bullish/bearish scores and signals
        """
        logger.info(f"Analyzing market direction for {timeframe} timeframe")
        
        if tech_indicators_df.empty:
            logger.warning("Empty technical indicators DataFrame provided")
            return {
                "direction": "neutral",
                "bullish_score": 50,
                "bearish_score": 50,
                "signals": [],
                "timeframe_bias": {
                    "score": 0,
                    "label": "neutral",
                    "confidence": 0
                }
            }
        
        # Initialize signals list and scores
        signals = []
        bullish_score = 50  # Start at neutral
        bearish_score = 50  # Start at neutral
        
        # Get the most recent data point
        latest_data = tech_indicators_df.iloc[0] if not tech_indicators_df.empty else None
        
        if latest_data is None:
            logger.warning("No data points in technical indicators DataFrame")
            return {
                "direction": "neutral",
                "bullish_score": bullish_score,
                "bearish_score": bearish_score,
                "signals": signals,
                "timeframe_bias": {
                    "score": 0,
                    "label": "neutral",
                    "confidence": 0
                }
            }
        
        # Initialize timeframe bias information
        timeframe_bias = {
            "score": 0,
            "label": "neutral",
            "confidence": 0
        }
        
        # Extract timeframe bias if available
        if 'tf_bias_score' in latest_data and pd.notna(latest_data['tf_bias_score']):
            timeframe_bias["score"] = latest_data['tf_bias_score']
            
            # Add timeframe bias to signals
            signals.append(f"Timeframe bias score: {latest_data['tf_bias_score']:.2f}")
            
            # Adjust bullish/bearish scores based on timeframe bias
            if latest_data['tf_bias_score'] > 0:
                bullish_score += min(latest_data['tf_bias_score'] / 5, 15)  # Max +15 points for strong bullish bias
                signals.append(f"Bullish timeframe bias adding {min(latest_data['tf_bias_score'] / 5, 15):.2f} to bullish score")
            elif latest_data['tf_bias_score'] < 0:
                bearish_score += min(abs(latest_data['tf_bias_score']) / 5, 15)  # Max +15 points for strong bearish bias
                signals.append(f"Bearish timeframe bias adding {min(abs(latest_data['tf_bias_score']) / 5, 15):.2f} to bearish score")
        
        if 'tf_bias_label' in latest_data and pd.notna(latest_data['tf_bias_label']):
            timeframe_bias["label"] = latest_data['tf_bias_label']
            signals.append(f"Timeframe bias: {latest_data['tf_bias_label']}")
        
        if 'tf_bias_confidence' in latest_data and pd.notna(latest_data['tf_bias_confidence']):
            timeframe_bias["confidence"] = latest_data['tf_bias_confidence']
        
        # Analyze RSI
        rsi_columns = [col for col in tech_indicators_df.columns if col.startswith('rsi')]
        for rsi_col in rsi_columns:
            rsi_value = latest_data.get(rsi_col)
            if pd.notna(rsi_value):
                if rsi_value < 30:
                    signals.append(f"{rsi_col} oversold ({rsi_value:.2f})")
                    bullish_score += 10
                elif rsi_value > 70:
                    signals.append(f"{rsi_col} overbought ({rsi_value:.2f})")
                    bearish_score += 10
        
        # Analyze MACD
        if all(col in latest_data for col in ['macd_line', 'macd_signal']):
            macd = latest_data['macd_line']
            macd_signal = latest_data['macd_signal']
            if pd.notna(macd) and pd.notna(macd_signal):
                if macd > macd_signal:
                    signals.append(f"MACD above signal line ({macd:.2f} > {macd_signal:.2f})")
                    bullish_score += 10
                else:
                    signals.append(f"MACD below signal line ({macd:.2f} < {macd_signal:.2f})")
                    bearish_score += 10
        
        # Analyze Bollinger Bands
        bb_middle_cols = [col for col in tech_indicators_df.columns if col.startswith('bb_middle')]
        bb_upper_cols = [col for col in tech_indicators_df.columns if col.startswith('bb_upper')]
        bb_lower_cols = [col for col in tech_indicators_df.columns if col.startswith('bb_lower')]
        
        for i, bb_middle_col in enumerate(bb_middle_cols):
            if i < len(bb_upper_cols) and i < len(bb_lower_cols):
                bb_middle = latest_data.get(bb_middle_col)
                bb_upper = latest_data.get(bb_upper_cols[i])
                bb_lower = latest_data.get(bb_lower_cols[i])
                close = latest_data.get('close')
                
                if pd.notna(bb_middle) and pd.notna(bb_upper) and pd.notna(bb_lower) and pd.notna(close):
                    if close > bb_upper:
                        signals.append(f"Price above upper Bollinger Band ({close:.2f} > {bb_upper:.2f})")
                        bearish_score += 8
                    elif close < bb_lower:
                        signals.append(f"Price below lower Bollinger Band ({close:.2f} < {bb_lower:.2f})")
                        bullish_score += 8
        
        # Analyze MFI
        mfi_columns = [col for col in tech_indicators_df.columns if col.startswith('mfi')]
        for mfi_col in mfi_columns:
            mfi_value = latest_data.get(mfi_col)
            if pd.notna(mfi_value):
                if mfi_value < 20:
                    signals.append(f"{mfi_col} oversold ({mfi_value:.2f})")
                    bullish_score += 8
                elif mfi_value > 80:
                    signals.append(f"{mfi_col} overbought ({mfi_value:.2f})")
                    bearish_score += 8
        
        # Analyze IMI
        imi_columns = [col for col in tech_indicators_df.columns if col.startswith('imi')]
        for imi_col in imi_columns:
            imi_value = latest_data.get(imi_col)
            if pd.notna(imi_value):
                if imi_value < 30:
                    signals.append(f"{imi_col} oversold ({imi_value:.2f})")
                    bullish_score += 7
                elif imi_value > 70:
                    signals.append(f"{imi_col} overbought ({imi_value:.2f})")
                    bearish_score += 7
        
        # Analyze Fair Value Gaps
        if 'bullish_fvg' in latest_data and pd.notna(latest_data['bullish_fvg']) and latest_data['bullish_fvg'] > 0:
            signals.append("Bullish Fair Value Gap detected")
            bullish_score += 12
        
        if 'bearish_fvg' in latest_data and pd.notna(latest_data['bearish_fvg']) and latest_data['bearish_fvg'] > 0:
            signals.append("Bearish Fair Value Gap detected")
            bearish_score += 12
        
        # Analyze candlestick patterns
        if 'bullish_engulfing' in latest_data and pd.notna(latest_data['bullish_engulfing']) and latest_data['bullish_engulfing'] > 0:
            signals.append("Bullish engulfing pattern detected")
            bullish_score += 8
            
        if 'bearish_engulfing' in latest_data and pd.notna(latest_data['bearish_engulfing']) and latest_data['bearish_engulfing'] > 0:
            signals.append("Bearish engulfing pattern detected")
            bearish_score += 8
            
        if 'morning_star' in latest_data and pd.notna(latest_data['morning_star']) and latest_data['morning_star'] > 0:
            signals.append("Morning star pattern detected")
            bullish_score += 10
            
        if 'evening_star' in latest_data and pd.notna(latest_data['evening_star']) and latest_data['evening_star'] > 0:
            signals.append("Evening star pattern detected")
            bearish_score += 10
        
        # Determine overall direction
        direction = "neutral"
        if bullish_score > bearish_score + 10:
            direction = "bullish"
        elif bearish_score > bullish_score + 10:
            direction = "bearish"
        
        # Cap scores at 100
        bullish_score = min(bullish_score, 100)
        bearish_score = min(bearish_score, 100)
        
        # If no signals were detected, add a default signal
        if not signals:
            signals.append("No significant signals detected")
        
        return {
            "direction": direction,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "signals": signals,
            "timeframe_bias": timeframe_bias
        }
    
    def _ensure_required_columns(self, options_df):
        """
        Ensure required columns exist in the options DataFrame, adding defaults if missing.
        
        Args:
            options_df: DataFrame containing options chain data
        """
        # Check for required columns and add defaults if missing
        required_columns = {
            'strikePrice': 0.0,
            'mark': 0.0,
            'lastPrice': 0.0,
            'bidPrice': 0.0,
            'askPrice': 0.0,
            'delta': 0.0,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0,
            'volatility': 0.0,
            'daysToExpiration': 7,
            'openInterest': 10
        }
        
        for col, default_value in required_columns.items():
            if col not in options_df.columns:
                # Check for alternative column names
                if col == 'mark' and 'lastPrice' in options_df.columns:
                    options_df['mark'] = options_df['lastPrice']
                elif col == 'mark' and 'last' in options_df.columns:
                    options_df['mark'] = options_df['last']
                elif col == 'lastPrice' and 'last' in options_df.columns:
                    options_df['lastPrice'] = options_df['last']
                elif col == 'bidPrice' and 'bid' in options_df.columns:
                    options_df['bidPrice'] = options_df['bid']
                elif col == 'askPrice' and 'ask' in options_df.columns:
                    options_df['askPrice'] = options_df['ask']
                else:
                    # Add default column if no alternative exists
                    logger.warning(f"Adding default column '{col}' with value {default_value}")
                    options_df[col] = default_value
    
    def _validate_options_data_for_symbol(self, options_df, symbol):
        """
        Validate that options data is for the specified symbol.
        
        Args:
            options_df: DataFrame containing options chain data
            symbol: Symbol of the underlying asset
            
        Returns:
            tuple: (is_valid, message) where is_valid is a boolean and message is a string
        """
        if options_df.empty:
            return False, "Options DataFrame is empty"
        
        # Check if 'underlying' column exists and matches the symbol
        if 'underlying' in options_df.columns:
            unique_underlyings = options_df['underlying'].unique()
            if len(unique_underlyings) == 0:
                return False, "No underlying values found in options data"
            
            # Check if any underlying matches the symbol (case insensitive)
            symbol_matches = [u for u in unique_underlyings if str(u).upper() == symbol.upper()]
            if not symbol_matches:
                logger.warning(f"Options data underlying ({unique_underlyings}) does not match requested symbol ({symbol})")
                return False, f"Options data is for {unique_underlyings} but requested symbol is {symbol}"
        
        # Check if 'symbol' column exists and contains the symbol
        elif 'symbol' in options_df.columns:
            # Extract base symbols from option symbols (usually the part before the underscore or date)
            option_symbols = options_df['symbol'].astype(str)
            
            # Try different patterns to extract underlying symbol
            contains_symbol = False
            for opt_sym in option_symbols:
                # Check if the option symbol contains the underlying symbol
                if symbol.upper() in opt_sym.upper():
                    contains_symbol = True
                    break
            
            if not contains_symbol:
                logger.warning(f"No option symbols contain the requested symbol {symbol}")
                return False, f"Option symbols do not contain the requested symbol {symbol}"
        
        # If we can't validate the symbol, log a warning but continue
        else:
            logger.warning(f"Cannot validate options data for symbol {symbol} - missing 'underlying' and 'symbol' columns")
            return True, f"Cannot validate options data for symbol {symbol} - missing columns"
        
        return True, f"Options data validated for symbol {symbol}"
    
    def evaluate_options_chain(self, options_df, market_direction, underlying_price, symbol="UNKNOWN"):
        """
        Evaluate options chain data to find optimal contracts based on market direction.
        
        Args:
            options_df: DataFrame containing options chain data
            market_direction: Dict with market direction analysis
            underlying_price: Current price of the underlying asset
            symbol: Symbol of the underlying asset
            
        Returns:
            dict: Evaluated options with scores for calls and puts
        """
        logger.info(f"Evaluating options chain data for symbol {symbol}")
        
        # Validate options data for the specified symbol
        is_valid, validation_message = self._validate_options_data_for_symbol(options_df, symbol)
        logger.info(f"Options data validation: {validation_message}")
        
        if options_df.empty:
            logger.warning("Empty options chain DataFrame provided")
            return {
                "calls": pd.DataFrame(),
                "puts": pd.DataFrame(),
                "validation": {
                    "is_valid": False,
                    "message": "Empty options chain DataFrame provided"
                }
            }
        
        # Ensure required columns exist with fallbacks
        self._ensure_required_columns(options_df)
        
        # Create copies to avoid modifying the original DataFrame
        try:
            calls_df = options_df[options_df['putCall'] == 'CALL'].copy()
            puts_df = options_df[options_df['putCall'] == 'PUT'].copy()
            logger.info(f"Split options into {len(calls_df)} calls and {len(puts_df)} puts")
        except KeyError:
            logger.error("Missing 'putCall' column in options DataFrame")
            # Try to infer from symbol if possible
            if 'symbol' in options_df.columns:
                logger.info("Attempting to infer putCall from symbol")
                options_df['putCall'] = options_df['symbol'].apply(
                    lambda x: 'CALL' if 'C' in str(x).upper() else ('PUT' if 'P' in str(x).upper() else 'UNKNOWN')
                )
                calls_df = options_df[options_df['putCall'] == 'CALL'].copy()
                puts_df = options_df[options_df['putCall'] == 'PUT'].copy()
                logger.info(f"Inferred {len(calls_df)} calls and {len(puts_df)} puts from symbols")
            else:
                logger.error("Cannot determine option types without putCall or symbol columns")
                return {
                    "calls": pd.DataFrame(),
                    "puts": pd.DataFrame(),
                    "validation": {
                        "is_valid": False,
                        "message": "Cannot determine option types without putCall or symbol columns"
                    }
                }
        
        # If either dataframe is empty after splitting, return empty results instead of creating default data
        if calls_df.empty:
            logger.warning(f"No call options found for symbol {symbol}")
        
        if puts_df.empty:
            logger.warning(f"No put options found for symbol {symbol}")
        
        # Initialize confidence scores
        for df in [calls_df, puts_df]:
            if not df.empty:
                df["confidenceScore"] = 60  # Start with a base score of 60 (slightly bullish)
        
        # Adjust confidence based on market direction
        if market_direction["direction"] == "bullish":
            if not calls_df.empty:
                calls_df["confidenceScore"] += 25  # Boost calls for bullish market
                logger.info("Applied bullish market direction boost to calls")
            if not puts_df.empty:
                puts_df["confidenceScore"] -= 15  # Penalize puts for bullish market
                logger.info("Applied bullish market direction penalty to puts")
        elif market_direction["direction"] == "bearish":
            if not puts_df.empty:
                puts_df["confidenceScore"] += 25  # Boost puts for bearish market
                logger.info("Applied bearish market direction boost to puts")
            if not calls_df.empty:
                calls_df["confidenceScore"] -= 15  # Penalize calls for bearish market
                logger.info("Applied bearish market direction penalty to calls")
        
        # Apply timeframe bias adjustments if available
        if "timeframe_bias" in market_direction and "score" in market_direction["timeframe_bias"]:
            bias_score = market_direction["timeframe_bias"]["score"]
            bias_confidence = market_direction["timeframe_bias"].get("confidence", 50) / 100
            
            # Scale adjustment based on bias confidence
            adjustment_factor = abs(bias_score) / 100 * bias_confidence
            
            if bias_score > 0:  # Bullish bias
                if not calls_df.empty:
                    calls_df["confidenceScore"] += 10 * adjustment_factor
                    logger.info(f"Applied bullish timeframe bias adjustment: +{10 * adjustment_factor:.2f} for calls")
                if not puts_df.empty:
                    puts_df["confidenceScore"] -= 5 * adjustment_factor
                    logger.info(f"Applied bullish timeframe bias adjustment: -{5 * adjustment_factor:.2f} for puts")
            elif bias_score < 0:  # Bearish bias
                if not calls_df.empty:
                    calls_df["confidenceScore"] -= 5 * adjustment_factor
                    logger.info(f"Applied bearish timeframe bias adjustment: -{5 * adjustment_factor:.2f} for calls")
                if not puts_df.empty:
                    puts_df["confidenceScore"] += 10 * adjustment_factor
                    logger.info(f"Applied bearish timeframe bias adjustment: +{10 * adjustment_factor:.2f} for puts")
        
        # Calculate additional metrics for scoring
        for df_name, df in [("calls", calls_df), ("puts", puts_df)]:
            if not df.empty:
                # Calculate bid-ask spread percentage with fallbacks for missing fields
                if all(col in df.columns for col in ['askPrice', 'bidPrice']):
                    # Use askPrice and bidPrice if available
                    df['spreadPct'] = df.apply(
                        lambda row: (row['askPrice'] - row['bidPrice']) / ((row['askPrice'] + row['bidPrice']) / 2) 
                        if pd.notna(row['askPrice']) and pd.notna(row['bidPrice']) and
                           row['askPrice'] > 0 and row['bidPrice'] > 0 
                        else 0.5,  # Default to 50% spread if missing or invalid
                        axis=1
                    )
                else:
                    # Default spread if columns missing
                    df['spreadPct'] = 0.5
                
                # Penalize options with wide spreads - IMPROVED: Reduced penalty
                df['confidenceScore'] -= df['spreadPct'] * 20  # 20% spread = -10 points (was -20)
                
                # Prefer options with higher open interest for liquidity
                if 'openInterest' in df.columns:
                    # Normalize open interest to 0-10 scale
                    max_oi = df['openInterest'].max()
                    if max_oi > 0:
                        df['oiScore'] = df['openInterest'] / max_oi * 10
                        df['confidenceScore'] += df['oiScore']
                
                # Prefer options with 5-14 days to expiration for swing trading
                if 'daysToExpiration' in df.columns:
                    df['confidenceScore'] += df.apply(
                        lambda row: 10 if 5 <= row['daysToExpiration'] <= 14 else 
                                   (5 if 3 <= row['daysToExpiration'] < 5 or 14 < row['daysToExpiration'] <= 21 else 0),
                        axis=1
                    )
                
                # Prefer options with delta between 0.3 and 0.7 (absolute value)
                if 'delta' in df.columns:
                    df['confidenceScore'] += df.apply(
                        lambda row: 10 if 0.3 <= abs(row['delta']) <= 0.7 else 
                                   (5 if 0.2 <= abs(row['delta']) < 0.3 or 0.7 < abs(row['delta']) <= 0.8 else 0),
                        axis=1
                    )
                
                # Penalize options with very high IV - IMPROVED: Reduced penalty
                if 'volatility' in df.columns:
                    df['confidenceScore'] -= df.apply(
                        lambda row: 10 if row['volatility'] > 1.0 else  # Over 100% IV
                                   (5 if row['volatility'] > 0.7 else 0),  # Over 70% IV
                        axis=1
                    )
                
                # Calculate strike distance from current price
                df['strikeDist'] = df.apply(
                    lambda row: abs(row['strikePrice'] - underlying_price) / underlying_price,
                    axis=1
                )
                
                # Prefer strikes closer to current price - IMPROVED: Reduced penalty
                df['confidenceScore'] -= df['strikeDist'] * 50  # 10% away = -5 points (was -10)
                
                # Calculate expected profit based on option price and projected move
                # IMPROVED: More realistic profit calculation
                if all(col in df.columns for col in ['mark', 'volatility', 'daysToExpiration']):
                    # Calculate projected move based on volatility and days to expiration
                    # Using a more conservative estimate than the full statistical move
                    df['projectedMovePct'] = df.apply(
                        lambda row: min(
                            row['volatility'] * np.sqrt(row['daysToExpiration'] / 365) * 0.6,  # 60% of statistical move
                            MAX_EXPECTED_PROFIT  # Cap at maximum expected profit
                        ),
                        axis=1
                    )
                    
                    # Calculate target price based on projected move
                    if df_name == "calls":
                        df['targetPrice'] = underlying_price * (1 + df['projectedMovePct'])
                    else:  # puts
                        df['targetPrice'] = underlying_price * (1 - df['projectedMovePct'])
                    
                    # Calculate expected profit
                    df['expectedProfit'] = df.apply(
                        lambda row: (
                            # For calls: (target price - strike) - premium, if target > strike
                            max(row['targetPrice'] - row['strikePrice'], 0) - row['mark']
                        ) / row['mark'] if df_name == "calls" else (
                            # For puts: (strike - target price) - premium, if target < strike
                            max(row['strikePrice'] - row['targetPrice'], 0) - row['mark']
                        ) / row['mark'],
                        axis=1
                    )
                    
                    # Clip expected profit to realistic range
                    df['expectedProfit'] = df['expectedProfit'].clip(MIN_EXPECTED_PROFIT, MAX_EXPECTED_PROFIT)
                    
                    # Boost confidence for options with higher expected profit
                    df['confidenceScore'] += df['expectedProfit'] * 50  # 20% profit = +10 points
                    
                    # Calculate target exit time in hours (based on days to expiration)
                    # IMPROVED: More realistic target timeframes
                    df['targetExitHours'] = df.apply(
                        lambda row: min(max(row['daysToExpiration'] * 4, 4), 72),  # Between 4 and 72 hours
                        axis=1
                    )
                else:
                    # Default values if required columns are missing
                    df['expectedProfit'] = MIN_EXPECTED_PROFIT
                    df['targetExitHours'] = 24
                
                # Ensure confidence score is within reasonable bounds
                df['confidenceScore'] = df['confidenceScore'].clip(0, 100)
        
        return {
            "calls": calls_df,
            "puts": puts_df,
            "validation": {
                "is_valid": is_valid,
                "message": validation_message
            }
        }
    
    def get_recommendations(self, tech_indicators_dict, options_df, underlying_price, symbol="UNKNOWN"):
        """
        Compatibility method for dashboard integration - calls generate_recommendations with the same parameters.
        
        Args:
            tech_indicators_dict: Dictionary of DataFrames with technical indicators for each timeframe
            options_df: DataFrame containing options chain data
            underlying_price: Current price of the underlying asset
            symbol: Symbol of the underlying asset
            
        Returns:
            dict: Recommendations with market direction analysis and options recommendations
        """
        logger.info(f"get_recommendations called for {symbol} - forwarding to generate_recommendations")
        return self.generate_recommendations(tech_indicators_dict, options_df, underlying_price, symbol)
    
    def _validate_technical_indicators(self, tech_indicators_dict, symbol):
        """
        Validate that technical indicators data is for the specified symbol.
        
        Args:
            tech_indicators_dict: Dictionary of DataFrames with technical indicators for each timeframe
            symbol: Symbol of the underlying asset
            
        Returns:
            tuple: (is_valid, message, data_quality) where is_valid is a boolean, message is a string,
                  and data_quality is a dict with quality metrics
        """
        if not tech_indicators_dict:
            return False, "Technical indicators dictionary is empty", {"score": 0, "metrics": {}}
        
        # Initialize data quality metrics
        data_quality = {
            "score": 100,  # Start with perfect score and deduct for issues
            "metrics": {
                "timeframes_available": [],
                "timeframes_missing": [],
                "indicators_per_timeframe": {},
                "rows_per_timeframe": {},
                "symbol_match": False
            }
        }
        
        # Check if any timeframes are available
        available_timeframes = []
        missing_timeframes = []
        
        for tf in TARGET_TIMEFRAMES:
            if tf in tech_indicators_dict:
                available_timeframes.append(tf)
            else:
                missing_timeframes.append(tf)
                data_quality["score"] -= 10  # Deduct for each missing target timeframe
        
        data_quality["metrics"]["timeframes_available"] = available_timeframes
        data_quality["metrics"]["timeframes_missing"] = missing_timeframes
        
        # If no target timeframes are available, check if any timeframes are available
        if not available_timeframes:
            if not tech_indicators_dict:
                return False, "No timeframes available in technical indicators", data_quality
            available_timeframes = list(tech_indicators_dict.keys())
            data_quality["metrics"]["timeframes_available"] = available_timeframes
        
        # Check data for each available timeframe
        symbol_match_found = False
        
        for tf in available_timeframes:
            indicators_df = tech_indicators_dict[tf]
            
            # Skip empty DataFrames
            if not isinstance(indicators_df, pd.DataFrame) or indicators_df.empty:
                data_quality["metrics"]["indicators_per_timeframe"][tf] = 0
                data_quality["metrics"]["rows_per_timeframe"][tf] = 0
                data_quality["score"] -= 15  # Deduct for empty DataFrame
                continue
            
            # Count available indicators and rows
            data_quality["metrics"]["indicators_per_timeframe"][tf] = len(indicators_df.columns)
            data_quality["metrics"]["rows_per_timeframe"][tf] = len(indicators_df)
            
            # Check if symbol column exists and matches
            if 'symbol' in indicators_df.columns:
                unique_symbols = indicators_df['symbol'].unique()
                if symbol.upper() in [str(s).upper() for s in unique_symbols]:
                    symbol_match_found = True
                    data_quality["metrics"]["symbol_match"] = True
            
            # Check for minimum required indicators
            required_indicators = ['rsi', 'macd', 'bb_middle']
            missing_indicators = [ind for ind in required_indicators if not any(col.startswith(ind) for col in indicators_df.columns)]
            
            if missing_indicators:
                data_quality["score"] -= 5 * len(missing_indicators)  # Deduct for each missing indicator type
        
        # If symbol column doesn't exist or doesn't match, we can't validate the symbol
        # but we'll continue with a warning
        if not symbol_match_found:
            logger.warning(f"Cannot validate technical indicators for symbol {symbol} - symbol column missing or mismatch")
            data_quality["score"] -= 20  # Significant deduction for symbol mismatch
        
        # Final validation result
        is_valid = data_quality["score"] >= 50  # Consider valid if score is at least 50
        message = f"Technical indicators validated for symbol {symbol}" if is_valid else f"Technical indicators validation failed for {symbol}"
        
        return is_valid, message, data_quality
    
    def generate_recommendations(self, tech_indicators_dict, options_df, underlying_price, symbol="UNKNOWN"):
        """
        Generate options trading recommendations based on technical indicators and options chain data.
        
        Args:
            tech_indicators_dict: Dictionary of DataFrames with technical indicators for each timeframe
            options_df: DataFrame containing options chain data
            underlying_price: Current price of the underlying asset
            symbol: Symbol of the underlying asset
            
        Returns:
            dict: Recommendations with market direction analysis and options recommendations
        """
        logger.info(f"Generating recommendations for {symbol}")
        
        # Initialize data quality metrics
        data_quality = {
            "technical_indicators": {"score": 0, "metrics": {}},
            "options_chain": {"score": 0, "metrics": {}},
            "overall_score": 0
        }
        
        # Validate technical indicators for the specified symbol
        tech_indicators_valid, tech_indicators_message, tech_indicators_quality = self._validate_technical_indicators(tech_indicators_dict, symbol)
        logger.info(f"Technical indicators validation: {tech_indicators_message}")
        data_quality["technical_indicators"] = tech_indicators_quality
        
        # FIX: Handle case where tech_indicators_dict is not a dictionary
        if not isinstance(tech_indicators_dict, dict):
            logger.warning(f"tech_indicators_dict is not a dictionary, it's a {type(tech_indicators_dict).__name__}")
            # If it's a DataFrame or ndarray, wrap it in a dictionary with the timeframe as key
            if isinstance(tech_indicators_dict, (pd.DataFrame, np.ndarray)):
                tech_indicators_dict = {symbol if isinstance(symbol, str) else "default": tech_indicators_dict}
            else:
                logger.error(f"Unsupported type for tech_indicators_dict: {type(tech_indicators_dict)}")
                return {
                    "symbol": symbol,
                    "price": underlying_price,
                    "market_direction": {
                        "direction": "neutral",
                        "bullish_score": 50,
                        "bearish_score": 50,
                        "signals": ["Invalid technical indicators format"],
                        "timeframe_bias": {
                            "score": 0,
                            "label": "neutral",
                            "confidence": 0
                        }
                    },
                    "recommendations": [],
                    "data_quality": {
                        "technical_indicators": {"score": 0, "metrics": {"error": "Invalid format"}},
                        "options_chain": {"score": 0, "metrics": {}},
                        "overall_score": 0
                    }
                }
        
        # Check if we have technical indicators - FIX: Handle both DataFrames and numpy arrays
        if tech_indicators_dict is None or len(tech_indicators_dict) == 0 or all(
            (isinstance(df, pd.DataFrame) and df.empty) or 
            (isinstance(df, np.ndarray) and df.size == 0) 
            for df in tech_indicators_dict.values()
        ):
            logger.warning("No technical indicators provided")
            return {
                "symbol": symbol,
                "price": underlying_price,
                "market_direction": {
                    "direction": "neutral",
                    "bullish_score": 50,
                    "bearish_score": 50,
                    "signals": ["No technical indicators available"],
                    "timeframe_bias": {
                        "score": 0,
                        "label": "neutral",
                        "confidence": 0
                    }
                },
                "recommendations": [],
                "data_quality": {
                    "technical_indicators": {"score": 0, "metrics": {"error": "No data available"}},
                    "options_chain": {"score": 0, "metrics": {}},
                    "overall_score": 0
                }
            }
        
        # Analyze market direction for each timeframe
        market_direction_analysis = {}
        for timeframe, indicators_df in tech_indicators_dict.items():
            if isinstance(indicators_df, pd.DataFrame) and not indicators_df.empty:
                market_direction_analysis[timeframe] = self.analyze_market_direction(indicators_df, timeframe)
        
        # If no valid timeframes were analyzed, return empty recommendations
        if not market_direction_analysis:
            logger.warning("No valid timeframes for market direction analysis")
            return {
                "symbol": symbol,
                "price": underlying_price,
                "market_direction": {
                    "direction": "neutral",
                    "bullish_score": 50,
                    "bearish_score": 50,
                    "signals": ["No valid timeframes for analysis"],
                    "timeframe_bias": {
                        "score": 0,
                        "label": "neutral",
                        "confidence": 0
                    }
                },
                "recommendations": [],
                "data_quality": data_quality
            }
        
        # Prioritize target timeframes if available
        primary_timeframe = None
        for tf in TARGET_TIMEFRAMES:
            if tf in market_direction_analysis:
                primary_timeframe = tf
                break
        
        # If no target timeframe is available, use the first available
        if primary_timeframe is None:
            primary_timeframe = list(market_direction_analysis.keys())[0]
        
        # Get primary market direction
        primary_direction = market_direction_analysis[primary_timeframe]
        
        # Validate options chain data for the specified symbol
        options_valid, options_message = self._validate_options_data_for_symbol(options_df, symbol)
        logger.info(f"Options chain validation: {options_message}")
        
        # Calculate options chain data quality metrics
        options_quality = {
            "score": 100 if options_valid else 50,  # Start with score based on validation
            "metrics": {
                "rows": len(options_df) if isinstance(options_df, pd.DataFrame) else 0,
                "calls": 0,
                "puts": 0,
                "symbol_match": options_valid
            }
        }
        
        # Count calls and puts if available
        if isinstance(options_df, pd.DataFrame) and not options_df.empty:
            if 'putCall' in options_df.columns:
                options_quality["metrics"]["calls"] = len(options_df[options_df['putCall'] == 'CALL'])
                options_quality["metrics"]["puts"] = len(options_df[options_df['putCall'] == 'PUT'])
            
            # Deduct points for missing data
            if options_quality["metrics"]["calls"] == 0:
                options_quality["score"] -= 25
                logger.warning(f"No call options found for {symbol}")
            
            if options_quality["metrics"]["puts"] == 0:
                options_quality["score"] -= 25
                logger.warning(f"No put options found for {symbol}")
        else:
            options_quality["score"] = 0
            logger.warning(f"Empty or invalid options chain data for {symbol}")
        
        data_quality["options_chain"] = options_quality
        
        # Calculate overall data quality score
        data_quality["overall_score"] = (data_quality["technical_indicators"]["score"] + data_quality["options_chain"]["score"]) / 2
        
        # Evaluate options chain
        evaluated_options = self.evaluate_options_chain(options_df, primary_direction, underlying_price, symbol)
        
        # Generate recommendations
        recommendations = []
        
        # Process calls if market is bullish or neutral
        if primary_direction["direction"] in ["bullish", "neutral"]:
            calls_df = evaluated_options["calls"]
            if not calls_df.empty:
                # Filter by confidence threshold
                confident_calls = calls_df[calls_df["confidenceScore"] >= CONFIDENCE_THRESHOLD]
                
                if not confident_calls.empty:
                    # Sort by confidence score (descending)
                    sorted_calls = confident_calls.sort_values(by="confidenceScore", ascending=False)
                    
                    # Take top recommendations
                    top_calls = sorted_calls.head(MAX_RECOMMENDATIONS)
                    
                    # Format recommendations
                    for _, option in top_calls.iterrows():
                        recommendations.append({
                            "type": "CALL",
                            "symbol": option.get("symbol", f"{symbol}_CALL_{option.get('strikePrice', 0)}"),
                            "strike": option.get("strikePrice", 0),
                            "expiration": option.get("expirationDate", "Unknown"),
                            "days_to_expiration": option.get("daysToExpiration", 0),
                            "current_price": option.get("mark", 0),
                            "confidence": option.get("confidenceScore", 0),
                            "expected_profit": option.get("expectedProfit", 0) * 100,  # Convert to percentage
                            "target_exit_hours": option.get("targetExitHours", 24),
                            "timeframe_bias": primary_direction.get("timeframe_bias", {
                                "score": 0,
                                "label": "neutral",
                                "confidence": 0
                            })
                        })
        
        # Process puts if market is bearish or neutral
        if primary_direction["direction"] in ["bearish", "neutral"]:
            puts_df = evaluated_options["puts"]
            if not puts_df.empty:
                # Filter by confidence threshold
                confident_puts = puts_df[puts_df["confidenceScore"] >= CONFIDENCE_THRESHOLD]
                
                if not confident_puts.empty:
                    # Sort by confidence score (descending)
                    sorted_puts = confident_puts.sort_values(by="confidenceScore", ascending=False)
                    
                    # Take top recommendations
                    top_puts = sorted_puts.head(MAX_RECOMMENDATIONS)
                    
                    # Format recommendations
                    for _, option in top_puts.iterrows():
                        recommendations.append({
                            "type": "PUT",
                            "symbol": option.get("symbol", f"{symbol}_PUT_{option.get('strikePrice', 0)}"),
                            "strike": option.get("strikePrice", 0),
                            "expiration": option.get("expirationDate", "Unknown"),
                            "days_to_expiration": option.get("daysToExpiration", 0),
                            "current_price": option.get("mark", 0),
                            "confidence": option.get("confidenceScore", 0),
                            "expected_profit": option.get("expectedProfit", 0) * 100,  # Convert to percentage
                            "target_exit_hours": option.get("targetExitHours", 24),
                            "timeframe_bias": primary_direction.get("timeframe_bias", {
                                "score": 0,
                                "label": "neutral",
                                "confidence": 0
                            })
                        })
        
        # Sort final recommendations by confidence (descending)
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Limit to maximum recommendations
        recommendations = recommendations[:MAX_RECOMMENDATIONS]
        
        # Compile final result
        result = {
            "symbol": symbol,
            "price": underlying_price,
            "market_direction": primary_direction,
            "timeframe_analysis": market_direction_analysis,
            "recommendations": recommendations,
            "data_quality": data_quality
        }
        
        logger.info(f"Generated {len(recommendations)} recommendations for {symbol}")
        return result

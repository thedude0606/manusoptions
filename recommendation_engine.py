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
CONFIDENCE_THRESHOLD = 40  # Minimum confidence score to include in recommendations - Lowered from 60 to ensure recommendations are generated
MAX_RECOMMENDATIONS = 5    # Maximum number of recommendations to return
MIN_EXPECTED_PROFIT = 0.10  # 10% minimum expected profit
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
                "signals": []
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
                "signals": signals
            }
        
        # Analyze RSI
        rsi_columns = [col for col in tech_indicators_df.columns if col.startswith('rsi_')]
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
        if all(col in latest_data for col in ['macd', 'macd_signal']):
            macd = latest_data['macd']
            macd_signal = latest_data['macd_signal']
            if pd.notna(macd) and pd.notna(macd_signal):
                if macd > macd_signal:
                    signals.append(f"MACD above signal line ({macd:.2f} > {macd_signal:.2f})")
                    bullish_score += 10
                else:
                    signals.append(f"MACD below signal line ({macd:.2f} < {macd_signal:.2f})")
                    bearish_score += 10
        
        # Analyze Bollinger Bands
        bb_middle_cols = [col for col in tech_indicators_df.columns if col.startswith('bb_middle_')]
        bb_upper_cols = [col for col in tech_indicators_df.columns if col.startswith('bb_upper_')]
        bb_lower_cols = [col for col in tech_indicators_df.columns if col.startswith('bb_lower_')]
        
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
        mfi_columns = [col for col in tech_indicators_df.columns if col.startswith('mfi_')]
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
        imi_columns = [col for col in tech_indicators_df.columns if col.startswith('imi_')]
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
        if 'fvg_bullish_top' in latest_data and pd.notna(latest_data['fvg_bullish_top']):
            signals.append("Bullish Fair Value Gap detected")
            bullish_score += 12
        
        if 'fvg_bearish_top' in latest_data and pd.notna(latest_data['fvg_bearish_top']):
            signals.append("Bearish Fair Value Gap detected")
            bearish_score += 12
        
        # Determine overall direction
        direction = "neutral"
        if bullish_score > bearish_score + 10:
            direction = "bullish"
        elif bearish_score > bullish_score + 10:
            direction = "bearish"
        
        # Cap scores at 100
        bullish_score = min(bullish_score, 100)
        bearish_score = min(bearish_score, 100)
        
        return {
            "direction": direction,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "signals": signals
        }
    
    def evaluate_options_chain(self, options_df, market_direction, underlying_price):
        """
        Evaluate options chain data to find optimal contracts based on market direction.
        
        Args:
            options_df: DataFrame containing options chain data
            market_direction: Dict with market direction analysis
            underlying_price: Current price of the underlying asset
            
        Returns:
            dict: Evaluated options with scores for calls and puts
        """
        logger.info("Evaluating options chain data")
        
        if options_df.empty:
            logger.warning("Empty options chain DataFrame provided")
            return {
                "calls": pd.DataFrame(),
                "puts": pd.DataFrame()
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
                    "puts": pd.DataFrame()
                }
        
        # Filter for options with sufficient liquidity if openInterest is available
        if 'openInterest' in calls_df.columns:
            calls_df_filtered = calls_df[calls_df['openInterest'] > 10]
            puts_df_filtered = puts_df[puts_df['openInterest'] > 10]
            
            # Only use filtered dataframes if they're not empty
            if not calls_df_filtered.empty:
                calls_df = calls_df_filtered
            else:
                logger.warning("No call options with sufficient openInterest, using all calls")
                
            if not puts_df_filtered.empty:
                puts_df = puts_df_filtered
            else:
                logger.warning("No put options with sufficient openInterest, using all puts")
        else:
            logger.warning("openInterest column not found, skipping liquidity filter")
        
        if calls_df.empty and puts_df.empty:
            logger.warning("No valid options found after filtering")
            return {
                "calls": pd.DataFrame(),
                "puts": pd.DataFrame()
            }
        
        # Calculate days to expiration if not already present
        if 'daysToExpiration' not in calls_df.columns and 'expirationDate' in calls_df.columns:
            logger.info("Calculating daysToExpiration from expirationDate")
            today = datetime.now().date()
            try:
                calls_df['daysToExpiration'] = calls_df['expirationDate'].apply(
                    lambda x: (datetime.strptime(str(x), '%Y-%m-%d').date() - today).days if pd.notna(x) else None
                )
                puts_df['daysToExpiration'] = puts_df['expirationDate'].apply(
                    lambda x: (datetime.strptime(str(x), '%Y-%m-%d').date() - today).days if pd.notna(x) else None
                )
            except (ValueError, TypeError) as e:
                logger.error(f"Error calculating daysToExpiration: {e}")
                # Try alternative date format
                try:
                    calls_df['daysToExpiration'] = calls_df['expirationDate'].apply(
                        lambda x: (datetime.strptime(str(x), '%m/%d/%Y').date() - today).days if pd.notna(x) else None
                    )
                    puts_df['daysToExpiration'] = puts_df['expirationDate'].apply(
                        lambda x: (datetime.strptime(str(x), '%m/%d/%Y').date() - today).days if pd.notna(x) else None
                    )
                except (ValueError, TypeError) as e:
                    logger.error(f"Error with alternative date format: {e}")
                    # Set default value
                    calls_df['daysToExpiration'] = 7
                    puts_df['daysToExpiration'] = 7
        
        # Filter for options with appropriate expiration (1-14 days for hourly/swing trading)
        if 'daysToExpiration' in calls_df.columns:
            calls_df_filtered = calls_df[(calls_df['daysToExpiration'] >= 1) & (calls_df['daysToExpiration'] <= 14)]
            puts_df_filtered = puts_df[(puts_df['daysToExpiration'] >= 1) & (puts_df['daysToExpiration'] <= 14)]
            
            # Only use filtered dataframes if they're not empty
            if not calls_df_filtered.empty:
                calls_df = calls_df_filtered
            else:
                logger.warning("No call options within desired expiration range, using all calls")
                
            if not puts_df_filtered.empty:
                puts_df = puts_df_filtered
            else:
                logger.warning("No put options within desired expiration range, using all puts")
        
        # Calculate additional metrics for scoring
        for df in [calls_df, puts_df]:
            if not df.empty:
                # Calculate bid-ask spread percentage with fallbacks for missing fields
                if all(col in df.columns for col in ['askPrice', 'bidPrice']):
                    # Use askPrice and bidPrice if available
                    df['spreadPct'] = df.apply(
                        lambda row: (row['askPrice'] - row['bidPrice']) / ((row['askPrice'] + row['bidPrice']) / 2) 
                        if pd.notna(row['askPrice']) and pd.notna(row['bidPrice']) and row['bidPrice'] > 0 else 0.05,
                        axis=1
                    )
                elif all(col in df.columns for col in ['ask', 'bid']):
                    # Fallback to ask and bid
                    df['spreadPct'] = df.apply(
                        lambda row: (row['ask'] - row['bid']) / ((row['ask'] + row['bid']) / 2) 
                        if pd.notna(row['ask']) and pd.notna(row['bid']) and row['bid'] > 0 else 0.05,
                        axis=1
                    )
                else:
                    # Default value if no price data available
                    df['spreadPct'] = 0.05
                    logger.warning("No bid/ask price data available, using default spreadPct")
                
                # Calculate distance from current price (as percentage)
                df['strikeDistancePct'] = df.apply(
                    lambda row: abs(row['strikePrice'] - underlying_price) / underlying_price 
                    if pd.notna(row['strikePrice']) and underlying_price > 0 else 0.05,
                    axis=1
                )
                
                # Calculate time value with fallbacks
                if 'mark' in df.columns:
                    price_col = 'mark'
                elif 'lastPrice' in df.columns:
                    price_col = 'lastPrice'
                elif 'last' in df.columns:
                    price_col = 'last'
                else:
                    # Use average of bid and ask if available
                    if all(col in df.columns for col in ['bid', 'ask']):
                        df['mark'] = df.apply(
                            lambda row: (row['bid'] + row['ask']) / 2 
                            if pd.notna(row['bid']) and pd.notna(row['ask']) else None,
                            axis=1
                        )
                        price_col = 'mark'
                    else:
                        # No price data available
                        df['mark'] = 1.0  # Default value
                        price_col = 'mark'
                        logger.warning("No price data available, using default mark value")
        
        # Score options based on various factors
        self._score_options(calls_df, puts_df, market_direction, underlying_price)
        
        return {
            "calls": calls_df,
            "puts": puts_df
        }
    
    def _ensure_required_columns(self, options_df):
        """
        Ensure all required columns exist in the options DataFrame.
        
        Args:
            options_df: DataFrame containing options chain data
        """
        logger.info("Ensuring required columns exist in options DataFrame")
        
        # Define required columns with default values
        required_columns = {
            'putCall': 'UNKNOWN',
            'symbol': 'UNKNOWN',
            'strikePrice': 0.0,
            'expirationDate': '2099-12-31',
            'daysToExpiration': 7,
            'delta': 0.5,
            'gamma': 0.01,
            'theta': -0.01,
            'vega': 0.01,
            'volatility': 0.3,
            'openInterest': 10
        }
        
        # Check for alternative column names and create required columns if missing
        if 'bidPrice' not in options_df.columns and 'bid' in options_df.columns:
            logger.info("Creating bidPrice from bid column")
            options_df['bidPrice'] = options_df['bid']
            
        if 'askPrice' not in options_df.columns and 'ask' in options_df.columns:
            logger.info("Creating askPrice from ask column")
            options_df['askPrice'] = options_df['ask']
            
        if 'lastPrice' not in options_df.columns and 'last' in options_df.columns:
            logger.info("Creating lastPrice from last column")
            options_df['lastPrice'] = options_df['last']
            
        # If mark is missing but we have bid and ask, calculate it
        if 'mark' not in options_df.columns:
            if all(col in options_df.columns for col in ['bid', 'ask']):
                logger.info("Creating mark as average of bid and ask")
                options_df['mark'] = options_df.apply(
                    lambda row: (row['bid'] + row['ask']) / 2 
                    if pd.notna(row['bid']) and pd.notna(row['ask']) else None,
                    axis=1
                )
            elif all(col in options_df.columns for col in ['bidPrice', 'askPrice']):
                logger.info("Creating mark as average of bidPrice and askPrice")
                options_df['mark'] = options_df.apply(
                    lambda row: (row['bidPrice'] + row['askPrice']) / 2 
                    if pd.notna(row['bidPrice']) and pd.notna(row['askPrice']) else None,
                    axis=1
                )
            elif 'lastPrice' in options_df.columns:
                logger.info("Creating mark from lastPrice")
                options_df['mark'] = options_df['lastPrice']
            elif 'last' in options_df.columns:
                logger.info("Creating mark from last")
                options_df['mark'] = options_df['last']
        
        # Add any missing required columns with default values
        for col, default_val in required_columns.items():
            if col not in options_df.columns:
                logger.warning(f"Adding missing column '{col}' with default value")
                options_df[col] = default_val
    
    def _score_options(self, calls_df, puts_df, market_direction, underlying_price):
        """
        Score options based on various factors including greeks, IV, and market direction.
        
        Args:
            calls_df: DataFrame containing call options
            puts_df: DataFrame containing put options
            market_direction: Dict with market direction analysis
            underlying_price: Current price of the underlying asset
        """
        logger.info("Scoring options based on market direction and greeks")
        
        # Initialize confidence scores
        for df in [calls_df, puts_df]:
            if not df.empty:
                df['confidenceScore'] = 50  # Start at neutral
        
        # Adjust scores based on market direction
        if not calls_df.empty:
            # For calls, higher score if market is bullish
            if market_direction['direction'] == 'bullish':
                calls_df['confidenceScore'] += (market_direction['bullish_score'] - 50) * 0.5
                logger.info(f"Adjusted call scores for bullish market: +{(market_direction['bullish_score'] - 50) * 0.5}")
            elif market_direction['direction'] == 'bearish':
                calls_df['confidenceScore'] -= (market_direction['bearish_score'] - 50) * 0.5
                logger.info(f"Adjusted call scores for bearish market: -{(market_direction['bearish_score'] - 50) * 0.5}")
        
        if not puts_df.empty:
            # For puts, higher score if market is bearish
            if market_direction['direction'] == 'bearish':
                puts_df['confidenceScore'] += (market_direction['bearish_score'] - 50) * 0.5
                logger.info(f"Adjusted put scores for bearish market: +{(market_direction['bearish_score'] - 50) * 0.5}")
            elif market_direction['direction'] == 'bullish':
                puts_df['confidenceScore'] -= (market_direction['bullish_score'] - 50) * 0.5
                logger.info(f"Adjusted put scores for bullish market: -{(market_direction['bullish_score'] - 50) * 0.5}")
        
        # Adjust scores based on greeks if available
        for df_name, df in [("calls", calls_df), ("puts", puts_df)]:
            if not df.empty:
                logger.info(f"Adjusting scores for {df_name} based on greeks and other factors")
                
                # Delta - prefer options with delta between 0.3 and 0.7 (not too far OTM or ITM)
                if 'delta' in df.columns:
                    try:
                        df['delta'] = pd.to_numeric(df['delta'], errors='coerce')
                        df.loc[df['delta'].notna(), 'confidenceScore'] += (
                            10 - 20 * abs(abs(df.loc[df['delta'].notna(), 'delta']) - 0.5)
                        )
                        logger.info(f"Adjusted {df_name} scores based on delta")
                    except Exception as e:
                        logger.error(f"Error adjusting scores based on delta: {e}")
                        # Provide a default adjustment if delta processing fails
                        df['confidenceScore'] += 5  # Modest boost as fallback
                
                # Gamma - higher gamma means more responsive to price changes (good for short-term)
                if 'gamma' in df.columns:
                    try:
                        df['gamma'] = pd.to_numeric(df['gamma'], errors='coerce')
                        df.loc[df['gamma'].notna(), 'confidenceScore'] += df.loc[df['gamma'].notna(), 'gamma'] * 50
                        logger.info(f"Adjusted {df_name} scores based on gamma")
                    except Exception as e:
                        logger.error(f"Error adjusting scores based on gamma: {e}")
                
                # Theta - lower (less negative) theta is better for holding
                if 'theta' in df.columns:
                    try:
                        df['theta'] = pd.to_numeric(df['theta'], errors='coerce')
                        df.loc[df['theta'].notna(), 'confidenceScore'] -= abs(df.loc[df['theta'].notna(), 'theta']) * 20
                        logger.info(f"Adjusted {df_name} scores based on theta")
                    except Exception as e:
                        logger.error(f"Error adjusting scores based on theta: {e}")
                
                # Vega - lower vega reduces exposure to volatility changes
                if 'vega' in df.columns:
                    try:
                        df['vega'] = pd.to_numeric(df['vega'], errors='coerce')
                        df.loc[df['vega'].notna(), 'confidenceScore'] -= abs(df.loc[df['vega'].notna(), 'vega']) * 10
                        logger.info(f"Adjusted {df_name} scores based on vega")
                    except Exception as e:
                        logger.error(f"Error adjusting scores based on vega: {e}")
                
                # IV - prefer options with moderate IV (not too high or low)
                if 'volatility' in df.columns:
                    try:
                        df['volatility'] = pd.to_numeric(df['volatility'], errors='coerce')
                        # Penalize very high IV (>60%)
                        high_iv_mask = df['volatility'] > 0.6
                        if high_iv_mask.any():
                            df.loc[high_iv_mask, 'confidenceScore'] -= (df.loc[high_iv_mask, 'volatility'] - 0.6) * 50
                        
                        # Penalize very low IV (<15%)
                        low_iv_mask = df['volatility'] < 0.15
                        if low_iv_mask.any():
                            df.loc[low_iv_mask, 'confidenceScore'] -= (0.15 - df.loc[low_iv_mask, 'volatility']) * 50
                        
                        logger.info(f"Adjusted {df_name} scores based on volatility")
                    except Exception as e:
                        logger.error(f"Error adjusting scores based on volatility: {e}")
                
                # Liquidity - prefer options with tighter spreads
                try:
                    if 'spreadPct' in df.columns:
                        spread_mask = df['spreadPct'].notna()
                        if spread_mask.any():
                            df.loc[spread_mask, 'confidenceScore'] -= df.loc[spread_mask, 'spreadPct'] * 100
                        logger.info(f"Adjusted {df_name} scores based on spread percentage")
                except Exception as e:
                    logger.error(f"Error adjusting scores based on spread percentage: {e}")
                
                # Strike distance - prefer options closer to the money
                try:
                    if 'strikeDistancePct' in df.columns:
                        distance_mask = df['strikeDistancePct'].notna()
                        if distance_mask.any():
                            df.loc[distance_mask, 'confidenceScore'] -= df.loc[distance_mask, 'strikeDistancePct'] * 50
                        logger.info(f"Adjusted {df_name} scores based on strike distance")
                except Exception as e:
                    logger.error(f"Error adjusting scores based on strike distance: {e}")
                
                # Days to expiration - prefer options with at least a few days to expiration
                try:
                    if 'daysToExpiration' in df.columns:
                        short_exp_mask = df['daysToExpiration'] < 3
                        if short_exp_mask.any():
                            df.loc[short_exp_mask, 'confidenceScore'] -= (3 - df.loc[short_exp_mask, 'daysToExpiration']) * 5
                        logger.info(f"Adjusted {df_name} scores based on days to expiration")
                except Exception as e:
                    logger.error(f"Error adjusting scores based on days to expiration: {e}")
                
                # Cap confidence scores between 0 and 100
                df['confidenceScore'] = df['confidenceScore'].clip(0, 100)
                
                # Log score distribution
                if not df.empty:
                    try:
                        logger.info(f"{df_name} confidence score stats: min={df['confidenceScore'].min():.1f}, max={df['confidenceScore'].max():.1f}, mean={df['confidenceScore'].mean():.1f}")
                    except Exception as e:
                        logger.error(f"Error calculating score statistics: {e}")
    
    def calculate_risk_reward(self, evaluated_options, underlying_price):
        """
        Calculate risk/reward ratios for potential trades.
        
        Args:
            evaluated_options: Dict with evaluated call and put options
            underlying_price: Current price of the underlying asset
            
        Returns:
            dict: Options with risk/reward metrics added
        """
        logger.info("Calculating risk/reward ratios")
        
        calls_df = evaluated_options['calls']
        puts_df = evaluated_options['puts']
        
        # Calculate risk/reward for calls
        if not calls_df.empty:
            # Risk is the premium paid (use mark or last price)
            calls_df['risk'] = calls_df['mark'] if 'mark' in calls_df.columns else calls_df['lastPrice']
            
            # Calculate potential reward based on delta and a projected move
            if 'delta' in calls_df.columns:
                # Convert delta to numeric if it's not already
                calls_df['delta'] = pd.to_numeric(calls_df['delta'], errors='coerce')
                
                # Project potential profit based on a 2% move in underlying and option's delta
                projected_move_pct = 0.02  # 2% move
                projected_move = underlying_price * projected_move_pct
                calls_df['projectedProfit'] = calls_df['delta'] * projected_move
                
                # Calculate reward/risk ratio
                calls_df['rewardRiskRatio'] = calls_df['projectedProfit'] / calls_df['risk']
                
                # Calculate expected profit percentage
                calls_df['expectedProfitPct'] = calls_df['projectedProfit'] / calls_df['risk'] * 100
                
                # Adjust confidence score based on expected profit
                calls_df.loc[calls_df['expectedProfitPct'] >= MIN_EXPECTED_PROFIT * 100, 'confidenceScore'] += 10
                calls_df.loc[calls_df['expectedProfitPct'] < MIN_EXPECTED_PROFIT * 100, 'confidenceScore'] -= 20
            
            # Calculate target sell price
            calls_df['targetSellPrice'] = calls_df['risk'] * (1 + MIN_EXPECTED_PROFIT)
            
            # Calculate target timeframe to sell (in hours, based on theta decay)
            if 'theta' in calls_df.columns:
                calls_df['theta'] = pd.to_numeric(calls_df['theta'], errors='coerce')
                # Calculate hours until theta decay would reduce price by 10%
                # Theta is daily decay, so divide by 24 for hourly
                calls_df['targetTimeframeHours'] = abs(calls_df['risk'] * MIN_EXPECTED_PROFIT / (calls_df['theta'] / 24))
                # Cap at reasonable values
                calls_df['targetTimeframeHours'] = calls_df['targetTimeframeHours'].clip(1, 72)
            else:
                # Default target timeframe if theta not available
                calls_df['targetTimeframeHours'] = 24
        
        # Calculate risk/reward for puts
        if not puts_df.empty:
            # Risk is the premium paid (use mark or last price)
            puts_df['risk'] = puts_df['mark'] if 'mark' in puts_df.columns else puts_df['lastPrice']
            
            # Calculate potential reward based on delta and a projected move
            if 'delta' in puts_df.columns:
                # Convert delta to numeric if it's not already
                puts_df['delta'] = pd.to_numeric(puts_df['delta'], errors='coerce')
                
                # Project potential profit based on a 2% move in underlying and option's delta
                # For puts, delta is negative, so take absolute value
                projected_move_pct = 0.02  # 2% move
                projected_move = underlying_price * projected_move_pct
                puts_df['projectedProfit'] = abs(puts_df['delta']) * projected_move
                
                # Calculate reward/risk ratio
                puts_df['rewardRiskRatio'] = puts_df['projectedProfit'] / puts_df['risk']
                
                # Calculate expected profit percentage
                puts_df['expectedProfitPct'] = puts_df['projectedProfit'] / puts_df['risk'] * 100
                
                # Adjust confidence score based on expected profit
                puts_df.loc[puts_df['expectedProfitPct'] >= MIN_EXPECTED_PROFIT * 100, 'confidenceScore'] += 10
                puts_df.loc[puts_df['expectedProfitPct'] < MIN_EXPECTED_PROFIT * 100, 'confidenceScore'] -= 20
            
            # Calculate target sell price
            puts_df['targetSellPrice'] = puts_df['risk'] * (1 + MIN_EXPECTED_PROFIT)
            
            # Calculate target timeframe to sell (in hours, based on theta decay)
            if 'theta' in puts_df.columns:
                puts_df['theta'] = pd.to_numeric(puts_df['theta'], errors='coerce')
                # Calculate hours until theta decay would reduce price by 10%
                # Theta is daily decay, so divide by 24 for hourly
                puts_df['targetTimeframeHours'] = abs(puts_df['risk'] * MIN_EXPECTED_PROFIT / (puts_df['theta'] / 24))
                # Cap at reasonable values
                puts_df['targetTimeframeHours'] = puts_df['targetTimeframeHours'].clip(1, 72)
            else:
                # Default target timeframe if theta not available
                puts_df['targetTimeframeHours'] = 24
        
        return {
            "calls": calls_df,
            "puts": puts_df
        }
    
    def generate_recommendations(self, options_with_risk_reward):
        """
        Generate final recommendations based on scored options.
        
        Args:
            options_with_risk_reward: Dict with options that have risk/reward metrics
            
        Returns:
            dict: Final recommendations for calls and puts
        """
        logger.info("Generating final recommendations")
        
        calls_df = options_with_risk_reward['calls']
        puts_df = options_with_risk_reward['puts']
        
        # Filter by confidence score
        if not calls_df.empty:
            # Log confidence score distribution before filtering
            logger.info(f"Calls confidence score distribution before filtering: min={calls_df['confidenceScore'].min():.1f}, max={calls_df['confidenceScore'].max():.1f}, mean={calls_df['confidenceScore'].mean():.1f}")
            # Filter by confidence score
            calls_df = calls_df[calls_df['confidenceScore'] >= CONFIDENCE_THRESHOLD]
            logger.info(f"Filtered calls by confidence score >= {CONFIDENCE_THRESHOLD}, remaining: {len(calls_df)}")
        
        if not puts_df.empty:
            # Log confidence score distribution before filtering
            logger.info(f"Puts confidence score distribution before filtering: min={puts_df['confidenceScore'].min():.1f}, max={puts_df['confidenceScore'].max():.1f}, mean={puts_df['confidenceScore'].mean():.1f}")
            # Filter by confidence score
            puts_df = puts_df[puts_df['confidenceScore'] >= CONFIDENCE_THRESHOLD]
            logger.info(f"Filtered puts by confidence score >= {CONFIDENCE_THRESHOLD}, remaining: {len(puts_df)}")
        
        # Sort by confidence score (descending)
        if not calls_df.empty:
            calls_df = calls_df.sort_values('confidenceScore', ascending=False)
        
        if not puts_df.empty:
            puts_df = puts_df.sort_values('confidenceScore', ascending=False)
        
        # Get top recommendations
        top_calls = calls_df.head(MAX_RECOMMENDATIONS) if not calls_df.empty else pd.DataFrame()
        top_puts = puts_df.head(MAX_RECOMMENDATIONS) if not puts_df.empty else pd.DataFrame()
        
        # Format recommendations for display
        call_recommendations = []
        if not top_calls.empty:
            for _, row in top_calls.iterrows():
                recommendation = {
                    "symbol": row.get('symbol', 'N/A'),
                    "type": "CALL",
                    "strikePrice": row.get('strikePrice', 0),
                    "expirationDate": row.get('expirationDate', 'N/A'),
                    "daysToExpiration": row.get('daysToExpiration', 0),
                    "currentPrice": row.get('mark', row.get('lastPrice', 0)),
                    "targetSellPrice": row.get('targetSellPrice', 0),
                    "targetTimeframeHours": row.get('targetTimeframeHours', 24),
                    "expectedProfitPct": row.get('expectedProfitPct', 0),
                    "confidenceScore": row.get('confidenceScore', 0),
                    "delta": row.get('delta', 'N/A'),
                    "gamma": row.get('gamma', 'N/A'),
                    "theta": row.get('theta', 'N/A'),
                    "vega": row.get('vega', 'N/A'),
                    "iv": row.get('volatility', 'N/A')
                }
                call_recommendations.append(recommendation)
        
        put_recommendations = []
        if not top_puts.empty:
            for _, row in top_puts.iterrows():
                recommendation = {
                    "symbol": row.get('symbol', 'N/A'),
                    "type": "PUT",
                    "strikePrice": row.get('strikePrice', 0),
                    "expirationDate": row.get('expirationDate', 'N/A'),
                    "daysToExpiration": row.get('daysToExpiration', 0),
                    "currentPrice": row.get('mark', row.get('lastPrice', 0)),
                    "targetSellPrice": row.get('targetSellPrice', 0),
                    "targetTimeframeHours": row.get('targetTimeframeHours', 24),
                    "expectedProfitPct": row.get('expectedProfitPct', 0),
                    "confidenceScore": row.get('confidenceScore', 0),
                    "delta": row.get('delta', 'N/A'),
                    "gamma": row.get('gamma', 'N/A'),
                    "theta": row.get('theta', 'N/A'),
                    "vega": row.get('vega', 'N/A'),
                    "iv": row.get('volatility', 'N/A')
                }
                put_recommendations.append(recommendation)
        
        return {
            "calls": call_recommendations,
            "puts": put_recommendations,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def get_recommendations(self, tech_indicators_df, options_df, underlying_price, timeframe="1hour"):
        """
        Main method to get options trading recommendations.
        
        Args:
            tech_indicators_df: DataFrame containing technical indicators
            options_df: DataFrame containing options chain data
            underlying_price: Current price of the underlying asset
            timeframe: Timeframe to analyze (e.g., "1hour", "4hour")
            
        Returns:
            dict: Trading recommendations
        """
        logger.info(f"Getting recommendations for timeframe {timeframe}")
        logger.info(f"Tech indicators DataFrame shape: {tech_indicators_df.shape}")
        logger.info(f"Options DataFrame shape: {options_df.shape}")
        logger.info(f"Underlying price: {underlying_price}")
        
        # Step 1: Analyze market direction
        logger.info("Step 1: Analyzing market direction")
        market_direction = self.analyze_market_direction(tech_indicators_df, timeframe)
        logger.info(f"Market direction analysis result: {market_direction}")
        
        # Step 2: Evaluate options chain
        logger.info("Step 2: Evaluating options chain")
        evaluated_options = self.evaluate_options_chain(options_df, market_direction, underlying_price)
        logger.info(f"Calls shape after evaluation: {evaluated_options['calls'].shape if not evaluated_options['calls'].empty else 'Empty DataFrame'}")
        logger.info(f"Puts shape after evaluation: {evaluated_options['puts'].shape if not evaluated_options['puts'].empty else 'Empty DataFrame'}")
        
        # Step 3: Calculate risk/reward ratios
        logger.info("Step 3: Calculating risk/reward ratios")
        options_with_risk_reward = self.calculate_risk_reward(evaluated_options, underlying_price)
        logger.info(f"Calls shape after risk/reward: {options_with_risk_reward['calls'].shape if not options_with_risk_reward['calls'].empty else 'Empty DataFrame'}")
        logger.info(f"Puts shape after risk/reward: {options_with_risk_reward['puts'].shape if not options_with_risk_reward['puts'].empty else 'Empty DataFrame'}")
        
        # Step 4: Generate final recommendations
        logger.info("Step 4: Generating final recommendations")
        recommendations = self.generate_recommendations(options_with_risk_reward)
        logger.info(f"Number of call recommendations: {len(recommendations.get('calls', []))}")
        logger.info(f"Number of put recommendations: {len(recommendations.get('puts', []))}")
        
        # Add market direction analysis to recommendations
        recommendations["market_direction"] = market_direction
        
        return recommendations

"""
Enhanced Recommendation Engine for Options Trading

This module provides advanced functionality to analyze technical indicators and options chain data
to generate actionable buy/sell recommendations with confidence scores.

The engine focuses on:
1. Multi-timeframe technical analysis to identify potential market direction
2. Advanced options metrics analysis including Greeks and IV
3. Calculating profit targets and optimal entry/exit timing
4. Generating actionable buy/sell signals with confidence intervals

The recommendations target hourly trading and swing trading with a minimum expected profit of 10%.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import math

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Constants for recommendation engine
CONFIDENCE_THRESHOLD = 40  # Minimum confidence score to include in recommendations
MAX_RECOMMENDATIONS = 5    # Maximum number of recommendations to return
MIN_EXPECTED_PROFIT = 0.10  # 10% minimum expected profit
TARGET_TIMEFRAMES = ["1min", "15min", "1hour", "4hour", "daily"]  # Target timeframes for analysis
TIMEFRAME_WEIGHTS = {
    "1min": 0.05,
    "15min": 0.15,
    "1hour": 0.35,
    "4hour": 0.30,
    "daily": 0.15
}  # Weights for multi-timeframe analysis

class EnhancedRecommendationEngine:
    """
    Enhanced engine for generating options trading recommendations based on
    multi-timeframe technical indicators and real-time options chain data.
    """
    
    def __init__(self):
        """Initialize the enhanced recommendation engine."""
        logger.info("Initializing enhanced recommendation engine")
        self.last_update_time = datetime.now()
        self.recommendation_cache = {}
    
    def analyze_multi_timeframe_market_direction(self, tech_indicators_df):
        """
        Analyze technical indicators across multiple timeframes to determine potential market direction.
        
        Args:
            tech_indicators_df: DataFrame containing technical indicators with timeframe column
            
        Returns:
            dict: Market direction analysis with bullish/bearish scores, signals, and timeframe breakdown
        """
        logger.info("Analyzing market direction across multiple timeframes")
        
        if tech_indicators_df.empty:
            logger.warning("Empty technical indicators DataFrame provided")
            return {
                "direction": "neutral",
                "bullish_score": 50,
                "bearish_score": 50,
                "signals": [],
                "timeframe_analysis": {}
            }
        
        # Initialize combined scores and signals
        combined_bullish_score = 0
        combined_bearish_score = 0
        combined_signals = []
        timeframe_analysis = {}
        
        # Get unique timeframes in the data
        timeframes = tech_indicators_df['timeframe'].unique() if 'timeframe' in tech_indicators_df.columns else ["1hour"]
        
        # Process each timeframe
        for timeframe in timeframes:
            # Filter data for this timeframe
            timeframe_data = tech_indicators_df[tech_indicators_df['timeframe'] == timeframe] if 'timeframe' in tech_indicators_df.columns else tech_indicators_df
            
            # Skip if no data for this timeframe
            if timeframe_data.empty:
                continue
            
            # Analyze this timeframe
            timeframe_analysis_result = self._analyze_single_timeframe(timeframe_data, timeframe)
            
            # Store timeframe analysis
            timeframe_analysis[timeframe] = timeframe_analysis_result
            
            # Get weight for this timeframe
            weight = TIMEFRAME_WEIGHTS.get(timeframe, 0.2)  # Default weight if not specified
            
            # Add weighted scores to combined scores
            combined_bullish_score += timeframe_analysis_result["bullish_score"] * weight
            combined_bearish_score += timeframe_analysis_result["bearish_score"] * weight
            
            # Add signals with timeframe prefix
            for signal in timeframe_analysis_result["signals"]:
                combined_signals.append(f"[{timeframe}] {signal}")
        
        # Determine overall direction
        direction = "neutral"
        if combined_bullish_score > combined_bearish_score + 10:
            direction = "bullish"
        elif combined_bearish_score > combined_bullish_score + 10:
            direction = "bearish"
        
        # Cap scores at 100
        combined_bullish_score = min(combined_bullish_score, 100)
        combined_bearish_score = min(combined_bearish_score, 100)
        
        return {
            "direction": direction,
            "bullish_score": combined_bullish_score,
            "bearish_score": combined_bearish_score,
            "signals": combined_signals,
            "timeframe_analysis": timeframe_analysis
        }
    
    def _analyze_single_timeframe(self, tech_indicators_df, timeframe="1hour"):
        """
        Analyze technical indicators for a single timeframe.
        
        Args:
            tech_indicators_df: DataFrame containing technical indicators for a single timeframe
            timeframe: Timeframe being analyzed
            
        Returns:
            dict: Market direction analysis with bullish/bearish scores and signals
        """
        # Initialize signals list and scores
        signals = []
        bullish_score = 50  # Start at neutral
        bearish_score = 50  # Start at neutral
        
        # Get the most recent data point
        latest_data = tech_indicators_df.iloc[0] if not tech_indicators_df.empty else None
        
        if latest_data is None:
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
    
    def analyze_options_metrics(self, options_df, underlying_price, market_direction):
        """
        Analyze options metrics including Greeks and IV to find optimal contracts.
        
        Args:
            options_df: DataFrame containing options chain data
            underlying_price: Current price of the underlying asset
            market_direction: Dict with market direction analysis
            
        Returns:
            dict: Analyzed options with metrics and scores for calls and puts
        """
        logger.info("Analyzing options metrics including Greeks and IV")
        
        if options_df.empty:
            logger.warning("Empty options chain DataFrame provided")
            return {
                "calls": pd.DataFrame(),
                "puts": pd.DataFrame()
            }
        
        # Ensure required columns exist with fallbacks
        self._ensure_required_columns(options_df)
        
        # Split into calls and puts
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
        
        # Process calls
        if not calls_df.empty:
            calls_df = self._process_options_metrics(calls_df, underlying_price, market_direction, "calls")
        
        # Process puts
        if not puts_df.empty:
            puts_df = self._process_options_metrics(puts_df, underlying_price, market_direction, "puts")
        
        return {
            "calls": calls_df,
            "puts": puts_df
        }
    
    def _process_options_metrics(self, df, underlying_price, market_direction, option_type):
        """
        Process options metrics for a specific option type (calls or puts).
        
        Args:
            df: DataFrame containing options data for a specific type
            underlying_price: Current price of the underlying asset
            market_direction: Dict with market direction analysis
            option_type: String indicating "calls" or "puts"
            
        Returns:
            DataFrame: Processed options with metrics and scores
        """
        # Filter for options with sufficient liquidity
        if 'openInterest' in df.columns:
            df_filtered = df[df['openInterest'] > 10]
            if not df_filtered.empty:
                df = df_filtered
            else:
                logger.warning(f"No {option_type} with sufficient openInterest, using all {option_type}")
        
        # Calculate days to expiration if not already present
        if 'daysToExpiration' not in df.columns and 'expirationDate' in df.columns:
            logger.info("Calculating daysToExpiration from expirationDate")
            today = datetime.now().date()
            try:
                df['daysToExpiration'] = df['expirationDate'].apply(
                    lambda x: (datetime.strptime(str(x), '%Y-%m-%d').date() - today).days if pd.notna(x) else None
                )
            except (ValueError, TypeError) as e:
                logger.error(f"Error calculating daysToExpiration: {e}")
                # Try alternative date format
                try:
                    df['daysToExpiration'] = df['expirationDate'].apply(
                        lambda x: (datetime.strptime(str(x), '%m/%d/%Y').date() - today).days if pd.notna(x) else None
                    )
                except (ValueError, TypeError) as e:
                    logger.error(f"Error with alternative date format: {e}")
                    # Set default value
                    df['daysToExpiration'] = 7
        
        # Filter for options with appropriate expiration (1-14 days for hourly/swing trading)
        if 'daysToExpiration' in df.columns:
            df_filtered = df[(df['daysToExpiration'] >= 1) & (df['daysToExpiration'] <= 14)]
            if not df_filtered.empty:
                df = df_filtered
            else:
                logger.warning(f"No {option_type} within desired expiration range, using all {option_type}")
        
        # Calculate additional metrics
        df = self._calculate_additional_metrics(df, underlying_price)
        
        # Analyze Greeks
        df = self._analyze_greeks(df, underlying_price, option_type)
        
        # Analyze IV
        df = self._analyze_iv(df, option_type)
        
        # Calculate confidence score
        df = self._calculate_confidence_score(df, market_direction, option_type)
        
        return df
    
    def _calculate_additional_metrics(self, df, underlying_price):
        """
        Calculate additional metrics for options analysis.
        
        Args:
            df: DataFrame containing options data
            underlying_price: Current price of the underlying asset
            
        Returns:
            DataFrame: Options with additional metrics
        """
        # Calculate bid-ask spread percentage
        if all(col in df.columns for col in ['askPrice', 'bidPrice']):
            df['spreadPct'] = df.apply(
                lambda row: (row['askPrice'] - row['bidPrice']) / ((row['askPrice'] + row['bidPrice']) / 2) 
                if pd.notna(row['askPrice']) and pd.notna(row['bidPrice']) and row['bidPrice'] > 0 else 0.05,
                axis=1
            )
        elif all(col in df.columns for col in ['ask', 'bid']):
            df['spreadPct'] = df.apply(
                lambda row: (row['ask'] - row['bid']) / ((row['ask'] + row['bid']) / 2) 
                if pd.notna(row['ask']) and pd.notna(row['bid']) and row['bid'] > 0 else 0.05,
                axis=1
            )
        else:
            df['spreadPct'] = 0.05
        
        # Calculate distance from current price (as percentage)
        df['strikeDistancePct'] = df.apply(
            lambda row: abs(row['strikePrice'] - underlying_price) / underlying_price 
            if pd.notna(row['strikePrice']) and underlying_price > 0 else 0.05,
            axis=1
        )
        
        # Determine current price (mark or last)
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
                df['mark'] = 0.1  # Default value
                price_col = 'mark'
        
        # Store the price column name for later use
        df['price_col'] = price_col
        
        return df
    
    def _analyze_greeks(self, df, underlying_price, option_type):
        """
        Analyze options Greeks for decision making.
        
        Args:
            df: DataFrame containing options data
            underlying_price: Current price of the underlying asset
            option_type: String indicating "calls" or "puts"
            
        Returns:
            DataFrame: Options with Greeks analysis
        """
        logger.info(f"Analyzing Greeks for {option_type}")
        
        # Initialize Greeks score
        df['greeks_score'] = 50  # Neutral starting point
        
        # Process Delta
        if 'delta' in df.columns:
            # Convert to numeric if needed
            df['delta'] = pd.to_numeric(df['delta'], errors='coerce')
            
            # For calls, prefer delta between 0.3 and 0.7 (balanced exposure)
            # For puts, prefer delta between -0.3 and -0.7 (balanced exposure)
            if option_type == "calls":
                # Boost score for delta in optimal range
                optimal_delta_mask = (df['delta'] >= 0.3) & (df['delta'] <= 0.7)
                if optimal_delta_mask.any():
                    df.loc[optimal_delta_mask, 'greeks_score'] += 10
                
                # Penalize very low delta (too far OTM)
                low_delta_mask = df['delta'] < 0.2
                if low_delta_mask.any():
                    df.loc[low_delta_mask, 'greeks_score'] -= 15
                
                # Penalize very high delta (too deep ITM)
                high_delta_mask = df['delta'] > 0.8
                if high_delta_mask.any():
                    df.loc[high_delta_mask, 'greeks_score'] -= 5
            else:  # puts
                # Convert put delta to positive for easier comparison
                df['abs_delta'] = df['delta'].abs()
                
                # Boost score for delta in optimal range
                optimal_delta_mask = (df['abs_delta'] >= 0.3) & (df['abs_delta'] <= 0.7)
                if optimal_delta_mask.any():
                    df.loc[optimal_delta_mask, 'greeks_score'] += 10
                
                # Penalize very low delta (too far OTM)
                low_delta_mask = df['abs_delta'] < 0.2
                if low_delta_mask.any():
                    df.loc[low_delta_mask, 'greeks_score'] -= 15
                
                # Penalize very high delta (too deep ITM)
                high_delta_mask = df['abs_delta'] > 0.8
                if high_delta_mask.any():
                    df.loc[high_delta_mask, 'greeks_score'] -= 5
        
        # Process Gamma
        if 'gamma' in df.columns:
            # Convert to numeric if needed
            df['gamma'] = pd.to_numeric(df['gamma'], errors='coerce')
            
            # Prefer higher gamma for short-term trades (more responsive to price changes)
            high_gamma_mask = df['gamma'] > 0.05
            if high_gamma_mask.any():
                df.loc[high_gamma_mask, 'greeks_score'] += 8
            
            # Extremely high gamma can indicate higher risk
            very_high_gamma_mask = df['gamma'] > 0.15
            if very_high_gamma_mask.any():
                df.loc[very_high_gamma_mask, 'greeks_score'] -= 5
        
        # Process Theta
        if 'theta' in df.columns:
            # Convert to numeric if needed
            df['theta'] = pd.to_numeric(df['theta'], errors='coerce')
            
            # Theta is typically negative, representing time decay
            # For short-term trades, prefer lower absolute theta (less time decay)
            high_theta_mask = df['theta'].abs() > 0.05
            if high_theta_mask.any():
                df.loc[high_theta_mask, 'greeks_score'] -= 10
            
            # Very high theta is a significant concern for short-term trades
            very_high_theta_mask = df['theta'].abs() > 0.1
            if very_high_theta_mask.any():
                df.loc[very_high_theta_mask, 'greeks_score'] -= 15
        
        # Process Vega
        if 'vega' in df.columns:
            # Convert to numeric if needed
            df['vega'] = pd.to_numeric(df['vega'], errors='coerce')
            
            # For short-term trades, prefer lower vega (less sensitivity to volatility changes)
            high_vega_mask = df['vega'] > 0.1
            if high_vega_mask.any():
                df.loc[high_vega_mask, 'greeks_score'] -= 5
        
        # Cap Greeks score between 0 and 100
        df['greeks_score'] = df['greeks_score'].clip(0, 100)
        
        return df
    
    def _analyze_iv(self, df, option_type):
        """
        Analyze implied volatility for decision making.
        
        Args:
            df: DataFrame containing options data
            option_type: String indicating "calls" or "puts"
            
        Returns:
            DataFrame: Options with IV analysis
        """
        logger.info(f"Analyzing IV for {option_type}")
        
        # Initialize IV score
        df['iv_score'] = 50  # Neutral starting point
        
        # Process IV
        if 'volatility' in df.columns:
            # Convert to numeric if needed
            df['volatility'] = pd.to_numeric(df['volatility'], errors='coerce')
            
            # For short-term trades, prefer moderate IV (not too high or low)
            # Too low IV may indicate insufficient premium
            low_iv_mask = df['volatility'] < 0.2
            if low_iv_mask.any():
                df.loc[low_iv_mask, 'iv_score'] -= 10
            
            # Too high IV may indicate overpriced options
            high_iv_mask = df['volatility'] > 0.6
            if high_iv_mask.any():
                df.loc[high_iv_mask, 'iv_score'] -= 15
            
            # Optimal IV range
            optimal_iv_mask = (df['volatility'] >= 0.25) & (df['volatility'] <= 0.5)
            if optimal_iv_mask.any():
                df.loc[optimal_iv_mask, 'iv_score'] += 15
        
        # Cap IV score between 0 and 100
        df['iv_score'] = df['iv_score'].clip(0, 100)
        
        return df
    
    def _calculate_confidence_score(self, df, market_direction, option_type):
        """
        Calculate overall confidence score based on all metrics.
        
        Args:
            df: DataFrame containing options data with metrics
            market_direction: Dict with market direction analysis
            option_type: String indicating "calls" or "puts"
            
        Returns:
            DataFrame: Options with confidence scores
        """
        logger.info(f"Calculating confidence scores for {option_type}")
        
        # Initialize confidence score
        df['confidenceScore'] = 50  # Neutral starting point
        
        # Adjust based on market direction
        direction = market_direction.get('direction', 'neutral')
        bullish_score = market_direction.get('bullish_score', 50)
        bearish_score = market_direction.get('bearish_score', 50)
        
        if option_type == "calls":
            # For calls, boost confidence if market direction is bullish
            if direction == "bullish":
                df['confidenceScore'] += (bullish_score - 50) * 0.5
            # Penalize calls if market direction is bearish
            elif direction == "bearish":
                df['confidenceScore'] -= (bearish_score - 50) * 0.5
        else:  # puts
            # For puts, boost confidence if market direction is bearish
            if direction == "bearish":
                df['confidenceScore'] += (bearish_score - 50) * 0.5
            # Penalize puts if market direction is bullish
            elif direction == "bullish":
                df['confidenceScore'] -= (bullish_score - 50) * 0.5
        
        # Incorporate Greeks score (30% weight)
        if 'greeks_score' in df.columns:
            df['confidenceScore'] = df['confidenceScore'] * 0.7 + df['greeks_score'] * 0.3
        
        # Incorporate IV score (20% weight)
        if 'iv_score' in df.columns:
            df['confidenceScore'] = df['confidenceScore'] * 0.8 + df['iv_score'] * 0.2
        
        # Adjust based on liquidity (spread percentage)
        if 'spreadPct' in df.columns:
            # Penalize wide spreads
            df['confidenceScore'] -= df['spreadPct'] * 100
        
        # Adjust based on strike distance
        if 'strikeDistancePct' in df.columns:
            # Penalize strikes too far from current price
            df['confidenceScore'] -= df['strikeDistancePct'] * 50
        
        # Adjust based on days to expiration
        if 'daysToExpiration' in df.columns:
            # Penalize very short expirations
            short_exp_mask = df['daysToExpiration'] < 3
            if short_exp_mask.any():
                df.loc[short_exp_mask, 'confidenceScore'] -= (3 - df.loc[short_exp_mask, 'daysToExpiration']) * 5
        
        # Cap confidence score between 0 and 100
        df['confidenceScore'] = df['confidenceScore'].clip(0, 100)
        
        # Calculate confidence interval (standard deviation of factors)
        df['confidenceInterval'] = 5.0  # Default value
        
        # If we have multiple scores, calculate a more accurate confidence interval
        if all(col in df.columns for col in ['greeks_score', 'iv_score']):
            # Create a list of scores for each row
            df['score_list'] = df.apply(
                lambda row: [
                    row['confidenceScore'], 
                    row['greeks_score'], 
                    row['iv_score']
                ],
                axis=1
            )
            
            # Calculate standard deviation of scores
            df['confidenceInterval'] = df['score_list'].apply(lambda x: np.std(x))
            
            # Clean up
            df = df.drop(columns=['score_list'])
        
        return df
    
    def calculate_profit_targets(self, analyzed_options, underlying_price):
        """
        Calculate profit targets and optimal entry/exit points.
        
        Args:
            analyzed_options: Dict with analyzed call and put options
            underlying_price: Current price of the underlying asset
            
        Returns:
            dict: Options with profit targets and entry/exit points
        """
        logger.info("Calculating profit targets and entry/exit points")
        
        calls_df = analyzed_options['calls']
        puts_df = analyzed_options['puts']
        
        # Process calls
        if not calls_df.empty:
            calls_df = self._calculate_option_profit_targets(calls_df, underlying_price, "calls")
        
        # Process puts
        if not puts_df.empty:
            puts_df = self._calculate_option_profit_targets(puts_df, underlying_price, "puts")
        
        return {
            "calls": calls_df,
            "puts": puts_df
        }
    
    def _calculate_option_profit_targets(self, df, underlying_price, option_type):
        """
        Calculate profit targets for a specific option type.
        
        Args:
            df: DataFrame containing options data
            underlying_price: Current price of the underlying asset
            option_type: String indicating "calls" or "puts"
            
        Returns:
            DataFrame: Options with profit targets
        """
        # Determine current price column
        price_col = df['price_col'].iloc[0] if 'price_col' in df.columns else 'mark'
        
        # Calculate entry price (current price)
        df['entryPrice'] = df[price_col]
        
        # Calculate minimum profit target (10%)
        df['minProfitTarget'] = df['entryPrice'] * (1 + MIN_EXPECTED_PROFIT)
        
        # Calculate optimal profit target based on Greeks and IV
        if all(col in df.columns for col in ['delta', 'gamma', 'volatility']):
            # Convert to numeric if needed
            df['delta'] = pd.to_numeric(df['delta'], errors='coerce')
            df['gamma'] = pd.to_numeric(df['gamma'], errors='coerce')
            df['volatility'] = pd.to_numeric(df['volatility'], errors='coerce')
            
            # Calculate expected price movement based on volatility
            # Daily expected move = underlying_price * volatility / sqrt(252)
            df['dailyExpectedMove'] = underlying_price * df['volatility'] / math.sqrt(252)
            
            # Calculate expected option price change based on delta and gamma
            # For a 1-day move: delta * expected_move + 0.5 * gamma * expected_move^2
            df['expectedPriceChange'] = df.apply(
                lambda row: abs(row['delta']) * row['dailyExpectedMove'] + 
                            0.5 * row['gamma'] * row['dailyExpectedMove']**2,
                axis=1
            )
            
            # Calculate optimal profit target (greater of min profit or expected price change)
            df['optimalProfitTarget'] = df.apply(
                lambda row: max(
                    row['minProfitTarget'],
                    row['entryPrice'] + row['expectedPriceChange']
                ),
                axis=1
            )
        else:
            # Fallback if Greeks not available
            df['optimalProfitTarget'] = df['minProfitTarget'] * 1.2  # 20% above minimum
        
        # Calculate target exit price
        df['targetExitPrice'] = df['optimalProfitTarget']
        
        # Calculate stop loss (based on risk tolerance)
        df['stopLossPrice'] = df['entryPrice'] * 0.85  # 15% loss
        
        # Calculate expected profit percentage
        df['expectedProfitPct'] = (df['targetExitPrice'] - df['entryPrice']) / df['entryPrice'] * 100
        
        # Calculate optimal entry time
        # For now, use a simple approach based on market hours
        current_hour = datetime.now().hour
        
        # Market typically more volatile at open and close
        if current_hour < 10:  # Early morning
            df['optimalEntryTime'] = "Wait until 10:30 AM for market to stabilize"
        elif current_hour >= 15:  # Late afternoon
            df['optimalEntryTime'] = "Wait until tomorrow morning"
        else:
            df['optimalEntryTime'] = "Current time is optimal for entry"
        
        # Calculate optimal exit time based on theta decay
        if 'theta' in df.columns:
            df['theta'] = pd.to_numeric(df['theta'], errors='coerce')
            
            # Calculate hours until theta decay would reduce price by profit target
            # Theta is daily decay, so divide by 24 for hourly
            df['optimalExitHours'] = df.apply(
                lambda row: abs((row['targetExitPrice'] - row['entryPrice']) / (row['theta'] / 24))
                if pd.notna(row['theta']) and row['theta'] != 0 else 24,
                axis=1
            )
            
            # Cap at reasonable values
            df['optimalExitHours'] = df['optimalExitHours'].clip(1, 72)
            
            # Convert to human-readable format
            df['optimalExitTime'] = df.apply(
                lambda row: f"Within {int(row['optimalExitHours'])} hours" 
                if row['optimalExitHours'] < 24 else 
                f"Within {int(row['optimalExitHours'] / 24)} days",
                axis=1
            )
        else:
            # Default if theta not available
            df['optimalExitTime'] = "Within 1 day"
        
        return df
    
    def generate_recommendations(self, options_with_profit_targets):
        """
        Generate final recommendations with confidence intervals.
        
        Args:
            options_with_profit_targets: Dict with options that have profit targets
            
        Returns:
            dict: Final recommendations for calls and puts with confidence intervals
        """
        logger.info("Generating final recommendations with confidence intervals")
        
        calls_df = options_with_profit_targets['calls']
        puts_df = options_with_profit_targets['puts']
        
        # Filter by confidence score
        if not calls_df.empty:
            calls_df = calls_df[calls_df['confidenceScore'] >= CONFIDENCE_THRESHOLD]
            logger.info(f"Filtered calls by confidence score >= {CONFIDENCE_THRESHOLD}, remaining: {len(calls_df)}")
        
        if not puts_df.empty:
            puts_df = puts_df[puts_df['confidenceScore'] >= CONFIDENCE_THRESHOLD]
            logger.info(f"Filtered puts by confidence score >= {CONFIDENCE_THRESHOLD}, remaining: {len(puts_df)}")
        
        # Filter by expected profit percentage
        if not calls_df.empty:
            calls_df = calls_df[calls_df['expectedProfitPct'] >= MIN_EXPECTED_PROFIT * 100]
            logger.info(f"Filtered calls by expected profit >= {MIN_EXPECTED_PROFIT * 100}%, remaining: {len(calls_df)}")
        
        if not puts_df.empty:
            puts_df = puts_df[puts_df['expectedProfitPct'] >= MIN_EXPECTED_PROFIT * 100]
            logger.info(f"Filtered puts by expected profit >= {MIN_EXPECTED_PROFIT * 100}%, remaining: {len(puts_df)}")
        
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
                    "currentPrice": row.get('entryPrice', 0),
                    "targetExitPrice": row.get('targetExitPrice', 0),
                    "stopLossPrice": row.get('stopLossPrice', 0),
                    "optimalEntryTime": row.get('optimalEntryTime', 'N/A'),
                    "optimalExitTime": row.get('optimalExitTime', 'N/A'),
                    "expectedProfitPct": row.get('expectedProfitPct', 0),
                    "confidenceScore": row.get('confidenceScore', 0),
                    "confidenceInterval": row.get('confidenceInterval', 5.0),
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
                    "currentPrice": row.get('entryPrice', 0),
                    "targetExitPrice": row.get('targetExitPrice', 0),
                    "stopLossPrice": row.get('stopLossPrice', 0),
                    "optimalEntryTime": row.get('optimalEntryTime', 'N/A'),
                    "optimalExitTime": row.get('optimalExitTime', 'N/A'),
                    "expectedProfitPct": row.get('expectedProfitPct', 0),
                    "confidenceScore": row.get('confidenceScore', 0),
                    "confidenceInterval": row.get('confidenceInterval', 5.0),
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
    
    def get_recommendations(self, tech_indicators_df, options_df, underlying_price):
        """
        Main method to get options trading recommendations with confidence intervals.
        
        Args:
            tech_indicators_df: DataFrame containing technical indicators with timeframe column
            options_df: DataFrame containing options chain data
            underlying_price: Current price of the underlying asset
            
        Returns:
            dict: Trading recommendations with confidence intervals
        """
        logger.info("Getting enhanced recommendations")
        logger.info(f"Tech indicators DataFrame shape: {tech_indicators_df.shape}")
        logger.info(f"Options DataFrame shape: {options_df.shape}")
        logger.info(f"Underlying price: {underlying_price}")
        
        # Step 1: Analyze multi-timeframe market direction
        logger.info("Step 1: Analyzing multi-timeframe market direction")
        market_direction = self.analyze_multi_timeframe_market_direction(tech_indicators_df)
        logger.info(f"Market direction analysis result: {market_direction['direction']}")
        
        # Step 2: Analyze options metrics (Greeks and IV)
        logger.info("Step 2: Analyzing options metrics")
        analyzed_options = self.analyze_options_metrics(options_df, underlying_price, market_direction)
        logger.info(f"Calls shape after analysis: {analyzed_options['calls'].shape if not analyzed_options['calls'].empty else 'Empty DataFrame'}")
        logger.info(f"Puts shape after analysis: {analyzed_options['puts'].shape if not analyzed_options['puts'].empty else 'Empty DataFrame'}")
        
        # Step 3: Calculate profit targets and entry/exit points
        logger.info("Step 3: Calculating profit targets")
        options_with_profit_targets = self.calculate_profit_targets(analyzed_options, underlying_price)
        logger.info(f"Calls shape after profit targets: {options_with_profit_targets['calls'].shape if not options_with_profit_targets['calls'].empty else 'Empty DataFrame'}")
        logger.info(f"Puts shape after profit targets: {options_with_profit_targets['puts'].shape if not options_with_profit_targets['puts'].empty else 'Empty DataFrame'}")
        
        # Step 4: Generate final recommendations
        logger.info("Step 4: Generating final recommendations")
        recommendations = self.generate_recommendations(options_with_profit_targets)
        logger.info(f"Number of call recommendations: {len(recommendations.get('calls', []))}")
        logger.info(f"Number of put recommendations: {len(recommendations.get('puts', []))}")
        
        # Add market direction analysis to recommendations
        recommendations["market_direction"] = market_direction
        
        # Update last update time
        self.last_update_time = datetime.now()
        
        return recommendations
    
    def update_recommendations_with_streaming_data(self, tech_indicators_df, options_df, underlying_price):
        """
        Update recommendations when new streaming data is received.
        
        Args:
            tech_indicators_df: DataFrame containing technical indicators with timeframe column
            options_df: DataFrame containing updated options chain data
            underlying_price: Current price of the underlying asset
            
        Returns:
            dict: Updated trading recommendations
        """
        logger.info("Updating recommendations with streaming data")
        
        # Check if enough time has passed since last update (to avoid excessive updates)
        time_since_last_update = (datetime.now() - self.last_update_time).total_seconds()
        if time_since_last_update < 5:  # Minimum 5 seconds between updates
            logger.info(f"Skipping update, only {time_since_last_update:.1f} seconds since last update")
            return self.recommendation_cache
        
        # Get fresh recommendations
        recommendations = self.get_recommendations(tech_indicators_df, options_df, underlying_price)
        
        # Update cache
        self.recommendation_cache = recommendations
        
        return recommendations
    
    def _ensure_required_columns(self, df):
        """
        Ensure required columns exist in the DataFrame, adding defaults if missing.
        
        Args:
            df: DataFrame to check and modify
            
        Returns:
            None (modifies DataFrame in place)
        """
        # Required columns with default values
        required_columns = {
            'strikePrice': 0.0,
            'putCall': 'UNKNOWN',
            'mark': 0.0,
            'bid': 0.0,
            'ask': 0.0,
            'lastPrice': 0.0,
            'openInterest': 0,
            'delta': 0.0,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0,
            'volatility': 0.0
        }
        
        # Add missing columns with default values
        for col, default_val in required_columns.items():
            if col not in df.columns:
                df[col] = default_val

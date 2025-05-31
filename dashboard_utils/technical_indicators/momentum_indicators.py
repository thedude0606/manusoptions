"""
Momentum Indicators Module

This module provides momentum-based technical indicators for options trading.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Set
from .indicator_base import IndicatorBase, register_indicator

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

@register_indicator
class RSI(IndicatorBase):
    """
    Relative Strength Index (RSI) Indicator with Divergence Detection
    
    Oscillator that measures speed and change of price movements with divergence detection.
    Identifies potential reversals and overbought/oversold conditions.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "rsi"
    
    @classmethod
    def get_name(cls) -> str:
        return "Relative Strength Index (RSI)"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Oscillator that measures speed and change of price movements. "
                "Identifies potential reversals and overbought/oversold conditions.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'period': 14,           # Standard RSI period
            'overbought': 70,       # Overbought threshold
            'oversold': 30,         # Oversold threshold
            'divergence_periods': 5  # Periods to look for divergence
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'period': 'Number of periods for RSI calculation',
            'overbought': 'Threshold above which market is considered overbought',
            'oversold': 'Threshold below which market is considered oversold',
            'divergence_periods': 'Number of periods to look for divergence'
        }
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RSI and detect divergences for the given data.
        
        Args:
            data: DataFrame containing price data
            
        Returns:
            DataFrame with RSI values and divergence signals added
        """
        if 'close' not in data.columns:
            logger.warning("close column not found in data")
            data['rsi'] = np.nan
            data['rsi_signal'] = 'neutral'
            data['bullish_divergence'] = False
            data['bearish_divergence'] = False
            return data
        
        period = self.params['period']
        overbought = self.params['overbought']
        oversold = self.params['oversold']
        divergence_periods = self.params['divergence_periods']
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Calculate price changes
        delta = result['close'].diff()
        
        # Separate gains and losses
        gain = delta.copy()
        loss = delta.copy()
        gain[gain < 0] = 0
        loss[loss > 0] = 0
        loss = abs(loss)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        result['rsi'] = 100 - (100 / (1 + rs))
        
        # Generate basic RSI signals
        conditions = [
            result['rsi'] >= overbought,
            result['rsi'] <= oversold
        ]
        choices = ['overbought', 'oversold']
        result['rsi_signal'] = np.select(conditions, choices, default='neutral')
        
        # Detect divergences
        result['bullish_divergence'] = False
        result['bearish_divergence'] = False
        
        # Need at least 2*divergence_periods data points for divergence detection
        if len(result) >= 2 * divergence_periods:
            # Bullish divergence: price making lower lows but RSI making higher lows
            for i in range(divergence_periods, len(result) - divergence_periods):
                # Check if current price is a local low
                if (result['close'].iloc[i] < result['close'].iloc[i-1] and 
                    result['close'].iloc[i] < result['close'].iloc[i+1]):
                    
                    # Look for a previous low within the divergence window
                    for j in range(i - divergence_periods, i):
                        if (result['close'].iloc[j] < result['close'].iloc[j-1] and 
                            result['close'].iloc[j] < result['close'].iloc[j+1]):
                            
                            # Check for bullish divergence
                            if (result['close'].iloc[i] < result['close'].iloc[j] and 
                                result['rsi'].iloc[i] > result['rsi'].iloc[j]):
                                result.loc[result.index[i], 'bullish_divergence'] = True
                                break
            
            # Bearish divergence: price making higher highs but RSI making lower highs
            for i in range(divergence_periods, len(result) - divergence_periods):
                # Check if current price is a local high
                if (result['close'].iloc[i] > result['close'].iloc[i-1] and 
                    result['close'].iloc[i] > result['close'].iloc[i+1]):
                    
                    # Look for a previous high within the divergence window
                    for j in range(i - divergence_periods, i):
                        if (result['close'].iloc[j] > result['close'].iloc[j-1] and 
                            result['close'].iloc[j] > result['close'].iloc[j+1]):
                            
                            # Check for bearish divergence
                            if (result['close'].iloc[i] > result['close'].iloc[j] and 
                                result['rsi'].iloc[i] < result['rsi'].iloc[j]):
                                result.loc[result.index[i], 'bearish_divergence'] = True
                                break
        
        logger.info(f"Calculated RSI with divergence detection for {len(data)} data points")
        return result
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on RSI and divergences.
        
        Args:
            data: DataFrame containing RSI values and divergence signals
            
        Returns:
            Dictionary with signal information
        """
        if 'rsi' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No RSI data available'
            }
        
        # Get the most recent values
        latest_rsi = data['rsi'].iloc[-1]
        latest_signal = data['rsi_signal'].iloc[-1]
        
        # Check for recent divergences (last 3 periods)
        recent_bullish_divergence = data['bullish_divergence'].iloc[-3:].any()
        recent_bearish_divergence = data['bearish_divergence'].iloc[-3:].any()
        
        # Determine signal direction and strength
        if recent_bearish_divergence and latest_signal == 'overbought':
            return {
                'direction': 'bearish',
                'strength': 90,  # Strong signal due to divergence confirmation
                'description': f'Bearish divergence with overbought RSI ({latest_rsi:.1f})'
            }
        elif recent_bullish_divergence and latest_signal == 'oversold':
            return {
                'direction': 'bullish',
                'strength': 90,  # Strong signal due to divergence confirmation
                'description': f'Bullish divergence with oversold RSI ({latest_rsi:.1f})'
            }
        elif latest_signal == 'overbought':
            return {
                'direction': 'bearish',
                'strength': min(100, int((latest_rsi - self.params['overbought']) * 3)),
                'description': f'Overbought RSI ({latest_rsi:.1f})'
            }
        elif latest_signal == 'oversold':
            return {
                'direction': 'bullish',
                'strength': min(100, int((self.params['oversold'] - latest_rsi) * 3)),
                'description': f'Oversold RSI ({latest_rsi:.1f})'
            }
        elif recent_bearish_divergence:
            return {
                'direction': 'bearish',
                'strength': 60,  # Moderate signal due to divergence only
                'description': f'Bearish divergence with RSI at {latest_rsi:.1f}'
            }
        elif recent_bullish_divergence:
            return {
                'direction': 'bullish',
                'strength': 60,  # Moderate signal due to divergence only
                'description': f'Bullish divergence with RSI at {latest_rsi:.1f}'
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f'Neutral RSI ({latest_rsi:.1f})'
            }

@register_indicator
class MACD(IndicatorBase):
    """
    Moving Average Convergence Divergence (MACD) Indicator with Fast Settings
    
    Trend-following momentum indicator showing relationship between two moving averages.
    Uses faster settings for short-term trading.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "macd"
    
    @classmethod
    def get_name(cls) -> str:
        return "Moving Average Convergence Divergence (MACD)"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Trend-following momentum indicator showing relationship between two moving averages. "
                "Uses faster settings for short-term trading.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'fast_period': 5,    # Fast EMA period (standard is 12)
            'slow_period': 12,   # Slow EMA period (standard is 26)
            'signal_period': 4,  # Signal line period (standard is 9)
            'use_fast_settings': True  # Whether to use fast settings for short-term trading
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'fast_period': 'Number of periods for fast EMA',
            'slow_period': 'Number of periods for slow EMA',
            'signal_period': 'Number of periods for signal line',
            'use_fast_settings': 'Whether to use fast settings for short-term trading'
        }
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD for the given data.
        
        Args:
            data: DataFrame containing price data
            
        Returns:
            DataFrame with MACD values added
        """
        if 'close' not in data.columns:
            logger.warning("close column not found in data")
            data['macd'] = np.nan
            data['macd_signal'] = np.nan
            data['macd_histogram'] = np.nan
            data['macd_crossover_signal'] = 'neutral'
            return data
        
        # Determine which settings to use
        if self.params['use_fast_settings']:
            fast_period = self.params['fast_period']
            slow_period = self.params['slow_period']
            signal_period = self.params['signal_period']
        else:
            # Standard settings
            fast_period = 12
            slow_period = 26
            signal_period = 9
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Calculate EMAs
        result['ema_fast'] = result['close'].ewm(span=fast_period, adjust=False).mean()
        result['ema_slow'] = result['close'].ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line
        result['macd'] = result['ema_fast'] - result['ema_slow']
        
        # Calculate signal line
        result['macd_signal'] = result['macd'].ewm(span=signal_period, adjust=False).mean()
        
        # Calculate histogram
        result['macd_histogram'] = result['macd'] - result['macd_signal']
        
        # Generate crossover signals
        result['macd_crossover_signal'] = 'neutral'
        
        # Bullish crossover: MACD crosses above signal line
        bullish_crossover = (result['macd'] > result['macd_signal']) & (result['macd'].shift(1) <= result['macd_signal'].shift(1))
        result.loc[bullish_crossover, 'macd_crossover_signal'] = 'bullish'
        
        # Bearish crossover: MACD crosses below signal line
        bearish_crossover = (result['macd'] < result['macd_signal']) & (result['macd'].shift(1) >= result['macd_signal'].shift(1))
        result.loc[bearish_crossover, 'macd_crossover_signal'] = 'bearish'
        
        # Clean up intermediate columns
        result = result.drop(['ema_fast', 'ema_slow'], axis=1)
        
        logger.info(f"Calculated MACD for {len(data)} data points using {'fast' if self.params['use_fast_settings'] else 'standard'} settings")
        return result
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on MACD.
        
        Args:
            data: DataFrame containing MACD values
            
        Returns:
            Dictionary with signal information
        """
        if 'macd' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No MACD data available'
            }
        
        # Get the most recent values
        latest_macd = data['macd'].iloc[-1]
        latest_signal = data['macd_signal'].iloc[-1]
        latest_histogram = data['macd_histogram'].iloc[-1]
        latest_crossover = data['macd_crossover_signal'].iloc[-1]
        
        # Check for recent crossovers (last 2 periods)
        recent_crossovers = data['macd_crossover_signal'].iloc[-2:].tolist()
        
        # Determine signal direction and strength
        if 'bullish' in recent_crossovers:
            # Strength based on histogram value and whether MACD is positive
            strength = min(100, int(abs(latest_histogram) * 100) + (30 if latest_macd > 0 else 0))
            return {
                'direction': 'bullish',
                'strength': strength,
                'description': f'Bullish MACD crossover (MACD: {latest_macd:.3f}, Signal: {latest_signal:.3f})'
            }
        elif 'bearish' in recent_crossovers:
            # Strength based on histogram value and whether MACD is negative
            strength = min(100, int(abs(latest_histogram) * 100) + (30 if latest_macd < 0 else 0))
            return {
                'direction': 'bearish',
                'strength': strength,
                'description': f'Bearish MACD crossover (MACD: {latest_macd:.3f}, Signal: {latest_signal:.3f})'
            }
        elif latest_macd > latest_signal:
            # Bullish trend but no recent crossover
            strength = min(80, int(abs(latest_histogram) * 80))
            return {
                'direction': 'bullish',
                'strength': strength,
                'description': f'MACD above signal line (MACD: {latest_macd:.3f}, Signal: {latest_signal:.3f})'
            }
        elif latest_macd < latest_signal:
            # Bearish trend but no recent crossover
            strength = min(80, int(abs(latest_histogram) * 80))
            return {
                'direction': 'bearish',
                'strength': strength,
                'description': f'MACD below signal line (MACD: {latest_macd:.3f}, Signal: {latest_signal:.3f})'
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f'Neutral MACD (MACD: {latest_macd:.3f}, Signal: {latest_signal:.3f})'
            }

@register_indicator
class RateOfChange(IndicatorBase):
    """
    Rate of Change (ROC) Indicator
    
    Measures the percentage change in price over a specific period.
    Identifies acceleration or deceleration in price movement.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "rate_of_change"
    
    @classmethod
    def get_name(cls) -> str:
        return "Rate of Change (ROC)"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Measures the percentage change in price over a specific period. "
                "Identifies acceleration or deceleration in price movement.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'period': 5,            # Period for ROC calculation
            'high_threshold': 2.0,   # Threshold for high ROC (%)
            'low_threshold': -2.0    # Threshold for low ROC (%)
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'period': 'Number of periods for ROC calculation',
            'high_threshold': 'Threshold above which ROC is considered high (%)',
            'low_threshold': 'Threshold below which ROC is considered low (%)'
        }
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Rate of Change for the given data.
        
        Args:
            data: DataFrame containing price data
            
        Returns:
            DataFrame with ROC values added
        """
        if 'close' not in data.columns:
            logger.warning("close column not found in data")
            data['roc'] = np.nan
            data['roc_signal'] = 'neutral'
            return data
        
        period = self.params['period']
        high_threshold = self.params['high_threshold']
        low_threshold = self.params['low_threshold']
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Calculate ROC
        result['roc'] = ((result['close'] - result['close'].shift(period)) / result['close'].shift(period)) * 100
        
        # Generate signal based on ROC thresholds
        conditions = [
            result['roc'] >= high_threshold,
            result['roc'] <= low_threshold
        ]
        choices = ['high_momentum', 'low_momentum']
        result['roc_signal'] = np.select(conditions, choices, default='neutral')
        
        logger.info(f"Calculated Rate of Change for {len(data)} data points")
        return result
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on ROC.
        
        Args:
            data: DataFrame containing ROC values
            
        Returns:
            Dictionary with signal information
        """
        if 'roc' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No ROC data available'
            }
        
        # Get the most recent values
        latest_roc = data['roc'].iloc[-1]
        latest_signal = data['roc_signal'].iloc[-1]
        
        if latest_signal == 'high_momentum':
            return {
                'direction': 'bullish',
                'strength': min(100, int((latest_roc - self.params['high_threshold']) * 10)),
                'description': f'High positive momentum (ROC: {latest_roc:.2f}%)'
            }
        elif latest_signal == 'low_momentum':
            return {
                'direction': 'bearish',
                'strength': min(100, int((self.params['low_threshold'] - latest_roc) * 10)),
                'description': f'High negative momentum (ROC: {latest_roc:.2f}%)'
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f'Neutral momentum (ROC: {latest_roc:.2f}%)'
            }

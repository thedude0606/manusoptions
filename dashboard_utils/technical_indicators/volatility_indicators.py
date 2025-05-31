"""
Volatility Indicators Module

This module provides volatility-based technical indicators for options trading.
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
class IVPercentile(IndicatorBase):
    """
    Implied Volatility (IV) Percentile Indicator
    
    Measures where current IV stands relative to its historical range.
    Critical for identifying potentially mispriced options.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "iv_percentile"
    
    @classmethod
    def get_name(cls) -> str:
        return "IV Percentile"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Measures where current implied volatility stands relative to its historical range. "
                "Helps identify potentially overpriced or underpriced options.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'lookback_period': 252,  # Trading days in a year
            'smoothing_period': 5,   # Days for smoothing
            'high_threshold': 80,    # Percentile threshold for high IV
            'low_threshold': 20      # Percentile threshold for low IV
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'lookback_period': 'Number of historical data points to use for percentile calculation',
            'smoothing_period': 'Number of periods for smoothing the IV values',
            'high_threshold': 'Percentile threshold above which IV is considered high',
            'low_threshold': 'Percentile threshold below which IV is considered low'
        }
    
    @classmethod
    def get_required_data(cls) -> Set[str]:
        return {'implied_volatility'}
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate IV Percentile for the given data.
        
        Args:
            data: DataFrame containing implied_volatility data
            
        Returns:
            DataFrame with IV percentile values added
        """
        if 'implied_volatility' not in data.columns:
            logger.warning("implied_volatility column not found in data")
            data['iv_percentile'] = np.nan
            data['iv_percentile_signal'] = 'neutral'
            return data
        
        lookback = self.params['lookback_period']
        smoothing = self.params['smoothing_period']
        high_threshold = self.params['high_threshold']
        low_threshold = self.params['low_threshold']
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Apply smoothing to IV if specified
        if smoothing > 1:
            result['iv_smooth'] = result['implied_volatility'].rolling(window=smoothing).mean()
        else:
            result['iv_smooth'] = result['implied_volatility']
        
        # Calculate percentile for each IV value relative to its history
        result['iv_percentile'] = result['iv_smooth'].rolling(window=lookback).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100,
            raw=False
        )
        
        # Generate signal based on percentile thresholds
        conditions = [
            result['iv_percentile'] >= high_threshold,
            result['iv_percentile'] <= low_threshold
        ]
        choices = ['high_iv', 'low_iv']
        result['iv_percentile_signal'] = np.select(conditions, choices, default='neutral')
        
        logger.info(f"Calculated IV Percentile for {len(data)} data points")
        return result
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on IV Percentile.
        
        Args:
            data: DataFrame containing IV percentile values
            
        Returns:
            Dictionary with signal information
        """
        if 'iv_percentile' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No IV percentile data available'
            }
        
        # Get the most recent IV percentile value
        latest_iv_percentile = data['iv_percentile'].iloc[-1]
        latest_signal = data['iv_percentile_signal'].iloc[-1]
        
        high_threshold = self.params['high_threshold']
        low_threshold = self.params['low_threshold']
        
        if latest_signal == 'high_iv':
            return {
                'direction': 'bearish',  # High IV suggests selling options
                'strength': min(100, int((latest_iv_percentile - high_threshold) * 2)),
                'description': f'High IV percentile ({latest_iv_percentile:.1f}%) suggests selling options strategies'
            }
        elif latest_signal == 'low_iv':
            return {
                'direction': 'bullish',  # Low IV suggests buying options
                'strength': min(100, int((low_threshold - latest_iv_percentile) * 2)),
                'description': f'Low IV percentile ({latest_iv_percentile:.1f}%) suggests buying options strategies'
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f'Neutral IV percentile ({latest_iv_percentile:.1f}%)'
            }

@register_indicator
class BollingerBandWidth(IndicatorBase):
    """
    Bollinger Band Width Indicator
    
    Measures the distance between upper and lower Bollinger Bands,
    identifying periods of contraction (low volatility) that often precede explosive moves.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "bollinger_band_width"
    
    @classmethod
    def get_name(cls) -> str:
        return "Bollinger Band Width"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Measures the distance between upper and lower Bollinger Bands. "
                "Identifies periods of contraction (low volatility) that often precede explosive moves.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'period': 20,           # Standard Bollinger Band period
            'std_dev': 2,           # Standard deviations for bands
            'low_width_percentile': 10,  # Percentile for identifying low width
            'lookback_period': 100  # Period for percentile calculation
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'period': 'Number of periods for the moving average',
            'std_dev': 'Number of standard deviations for the bands',
            'low_width_percentile': 'Percentile threshold for identifying low band width',
            'lookback_period': 'Period for percentile calculation'
        }
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Bollinger Band Width for the given data.
        
        Args:
            data: DataFrame containing price data
            
        Returns:
            DataFrame with Bollinger Band Width values added
        """
        if 'close' not in data.columns:
            logger.warning("close column not found in data")
            data['bb_width'] = np.nan
            data['bb_width_percentile'] = np.nan
            data['bb_width_signal'] = 'neutral'
            return data
        
        period = self.params['period']
        std_dev = self.params['std_dev']
        low_width_percentile = self.params['low_width_percentile']
        lookback_period = self.params['lookback_period']
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Calculate middle band (simple moving average)
        result['bb_middle'] = result['close'].rolling(window=period).mean()
        
        # Calculate standard deviation
        result['bb_std'] = result['close'].rolling(window=period).std()
        
        # Calculate upper and lower bands
        result['bb_upper'] = result['bb_middle'] + (result['bb_std'] * std_dev)
        result['bb_lower'] = result['bb_middle'] - (result['bb_std'] * std_dev)
        
        # Calculate band width (normalized by middle band)
        result['bb_width'] = (result['bb_upper'] - result['bb_lower']) / result['bb_middle']
        
        # Calculate percentile of current width relative to history
        result['bb_width_percentile'] = result['bb_width'].rolling(window=lookback_period).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100,
            raw=False
        )
        
        # Generate signal based on width percentile
        result['bb_width_signal'] = np.where(
            result['bb_width_percentile'] <= low_width_percentile,
            'low_width',
            'normal_width'
        )
        
        logger.info(f"Calculated Bollinger Band Width for {len(data)} data points")
        return result
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on Bollinger Band Width.
        
        Args:
            data: DataFrame containing Bollinger Band Width values
            
        Returns:
            Dictionary with signal information
        """
        if 'bb_width' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No Bollinger Band Width data available'
            }
        
        # Get the most recent values
        latest_width_percentile = data['bb_width_percentile'].iloc[-1]
        latest_signal = data['bb_width_signal'].iloc[-1]
        
        if latest_signal == 'low_width':
            return {
                'direction': 'volatile_soon',  # Low width suggests upcoming volatility
                'strength': min(100, int((self.params['low_width_percentile'] - latest_width_percentile) * 2)),
                'description': f'Low Bollinger Band Width ({latest_width_percentile:.1f}%) suggests imminent volatility expansion'
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f'Normal Bollinger Band Width ({latest_width_percentile:.1f}%)'
            }

@register_indicator
class AverageTrueRange(IndicatorBase):
    """
    Average True Range (ATR) Indicator
    
    Measures market volatility by decomposing the entire range of an asset price for a period.
    Helps set appropriate stop-loss and take-profit levels.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "average_true_range"
    
    @classmethod
    def get_name(cls) -> str:
        return "Average True Range (ATR)"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Measures market volatility by decomposing the entire range of an asset price for a period. "
                "Helps set appropriate stop-loss and take-profit levels.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'period': 14,           # Standard ATR period
            'high_percentile': 80,  # Percentile for high ATR
            'low_percentile': 20,   # Percentile for low ATR
            'lookback_period': 100  # Period for percentile calculation
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'period': 'Number of periods for ATR calculation',
            'high_percentile': 'Percentile threshold for identifying high ATR',
            'low_percentile': 'Percentile threshold for identifying low ATR',
            'lookback_period': 'Period for percentile calculation'
        }
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Average True Range for the given data.
        
        Args:
            data: DataFrame containing price data
            
        Returns:
            DataFrame with ATR values added
        """
        if not all(col in data.columns for col in ['high', 'low', 'close']):
            logger.warning("Required columns (high, low, close) not found in data")
            data['atr'] = np.nan
            data['atr_percentile'] = np.nan
            data['atr_signal'] = 'neutral'
            return data
        
        period = self.params['period']
        high_percentile = self.params['high_percentile']
        low_percentile = self.params['low_percentile']
        lookback_period = self.params['lookback_period']
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Calculate True Range
        result['tr1'] = abs(result['high'] - result['low'])
        result['tr2'] = abs(result['high'] - result['close'].shift(1))
        result['tr3'] = abs(result['low'] - result['close'].shift(1))
        result['true_range'] = result[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Calculate ATR using Wilder's smoothing method
        result['atr'] = result['true_range'].rolling(window=period).mean()
        
        # Calculate ATR percentile
        result['atr_percentile'] = result['atr'].rolling(window=lookback_period).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100,
            raw=False
        )
        
        # Generate signal based on ATR percentile
        conditions = [
            result['atr_percentile'] >= high_percentile,
            result['atr_percentile'] <= low_percentile
        ]
        choices = ['high_volatility', 'low_volatility']
        result['atr_signal'] = np.select(conditions, choices, default='normal_volatility')
        
        # Clean up intermediate columns
        result = result.drop(['tr1', 'tr2', 'tr3'], axis=1)
        
        logger.info(f"Calculated Average True Range for {len(data)} data points")
        return result
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on ATR.
        
        Args:
            data: DataFrame containing ATR values
            
        Returns:
            Dictionary with signal information
        """
        if 'atr' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No ATR data available'
            }
        
        # Get the most recent values
        latest_atr = data['atr'].iloc[-1]
        latest_percentile = data['atr_percentile'].iloc[-1]
        latest_signal = data['atr_signal'].iloc[-1]
        latest_close = data['close'].iloc[-1]
        
        # Calculate expected price movement based on ATR
        expected_movement = latest_atr
        expected_movement_percent = (expected_movement / latest_close) * 100
        
        if latest_signal == 'high_volatility':
            return {
                'direction': 'volatile',
                'strength': min(100, int((latest_percentile - self.params['high_percentile']) * 2)),
                'description': f'High volatility (ATR: {latest_atr:.2f}, {expected_movement_percent:.1f}% expected movement)'
            }
        elif latest_signal == 'low_volatility':
            return {
                'direction': 'stable',
                'strength': min(100, int((self.params['low_percentile'] - latest_percentile) * 2)),
                'description': f'Low volatility (ATR: {latest_atr:.2f}, {expected_movement_percent:.1f}% expected movement)'
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f'Normal volatility (ATR: {latest_atr:.2f}, {expected_movement_percent:.1f}% expected movement)'
            }

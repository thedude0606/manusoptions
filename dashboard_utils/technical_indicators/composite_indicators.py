"""
Composite Indicators Module

This module provides composite technical indicators that combine multiple signals
for more robust options trading recommendations.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Set, Type
from .indicator_base import IndicatorBase, register_indicator, get_registered_indicators

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

@register_indicator
class TechnicalConfluenceIndicator(IndicatorBase):
    """
    Technical Confluence Indicator
    
    Composite indicator that measures agreement among multiple technical signals.
    Reduces false signals by requiring confirmation from multiple indicators.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "technical_confluence"
    
    @classmethod
    def get_name(cls) -> str:
        return "Technical Confluence Indicator"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Composite indicator that measures agreement among multiple technical signals. "
                "Reduces false signals by requiring confirmation from multiple indicators.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'indicators': [
                {'id': 'rsi', 'weight': 1.0},
                {'id': 'macd', 'weight': 1.0},
                {'id': 'bollinger_band_width', 'weight': 0.8},
                {'id': 'average_true_range', 'weight': 0.7}
            ],
            'high_confluence_threshold': 0.7,  # Threshold for high confluence
            'medium_confluence_threshold': 0.5  # Threshold for medium confluence
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'indicators': 'List of indicators to include in confluence calculation with weights',
            'high_confluence_threshold': 'Threshold above which confluence is considered high',
            'medium_confluence_threshold': 'Threshold above which confluence is considered medium'
        }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize the Technical Confluence Indicator.
        
        Args:
            params: Dictionary of parameters to customize the indicator
        """
        super().__init__(params)
        self.indicator_instances = {}
        self._initialize_indicators()
    
    def _initialize_indicators(self):
        """Initialize all component indicators."""
        registered_indicators = get_registered_indicators()
        
        for indicator_config in self.params['indicators']:
            indicator_id = indicator_config['id']
            
            if indicator_id in registered_indicators:
                # Create instance of the indicator
                indicator_class = registered_indicators[indicator_id]
                self.indicator_instances[indicator_id] = indicator_class()
                logger.info(f"Initialized component indicator: {indicator_id}")
            else:
                logger.warning(f"Unknown indicator ID: {indicator_id}, skipping")
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Technical Confluence for the given data.
        
        Args:
            data: DataFrame containing price/volume data
            
        Returns:
            DataFrame with confluence values added
        """
        if data.empty:
            logger.warning("Empty DataFrame provided")
            # Create a summary DataFrame with confluence metrics
            summary = pd.DataFrame({
                'date': [pd.Timestamp.now()],
                'bullish_confluence': [np.nan],
                'bearish_confluence': [np.nan],
                'volatility_confluence': [np.nan],
                'overall_confluence': [np.nan],
                'confluence_signal': ['neutral']
            })
            return summary
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Calculate each component indicator
        indicator_signals = {}
        for indicator_id, indicator in self.indicator_instances.items():
            try:
                # Calculate the indicator
                indicator_result = indicator.calculate(result)
                
                # Get the signal
                signal = indicator.get_signal(indicator_result)
                
                # Store the signal
                indicator_signals[indicator_id] = signal
                logger.info(f"Calculated signal for {indicator_id}: {signal['direction']} (strength: {signal['strength']})")
            except Exception as e:
                logger.error(f"Error calculating {indicator_id}: {e}")
                indicator_signals[indicator_id] = {
                    'direction': 'neutral',
                    'strength': 0,
                    'description': f"Error: {str(e)}"
                }
        
        # Calculate confluence scores
        bullish_score = 0
        bearish_score = 0
        volatility_score = 0
        total_weight = 0
        
        for indicator_config in self.params['indicators']:
            indicator_id = indicator_config['id']
            weight = indicator_config.get('weight', 1.0)
            
            if indicator_id in indicator_signals:
                signal = indicator_signals[indicator_id]
                direction = signal['direction']
                strength = signal['strength'] / 100  # Normalize to 0-1
                
                if direction == 'bullish' or direction == 'contrarian_bullish':
                    bullish_score += strength * weight
                elif direction == 'bearish' or direction == 'contrarian_bearish':
                    bearish_score += strength * weight
                elif direction in ['volatile', 'volatile_soon', 'volatile_bearish', 'high_volatility']:
                    volatility_score += strength * weight
                
                total_weight += weight
        
        # Normalize scores
        if total_weight > 0:
            bullish_score /= total_weight
            bearish_score /= total_weight
            volatility_score /= total_weight
        
        # Calculate overall confluence (max of directional scores)
        overall_confluence = max(bullish_score, bearish_score)
        
        # Determine confluence signal
        high_threshold = self.params['high_confluence_threshold']
        medium_threshold = self.params['medium_confluence_threshold']
        
        if overall_confluence >= high_threshold:
            if bullish_score > bearish_score:
                signal = 'strong_bullish'
            else:
                signal = 'strong_bearish'
        elif overall_confluence >= medium_threshold:
            if bullish_score > bearish_score:
                signal = 'moderate_bullish'
            else:
                signal = 'moderate_bearish'
        elif volatility_score >= medium_threshold:
            signal = 'volatility_expected'
        else:
            signal = 'neutral'
        
        # Create a summary DataFrame with confluence metrics
        summary = pd.DataFrame({
            'date': [pd.Timestamp.now()],
            'bullish_confluence': [bullish_score],
            'bearish_confluence': [bearish_score],
            'volatility_confluence': [volatility_score],
            'overall_confluence': [overall_confluence],
            'confluence_signal': [signal]
        })
        
        logger.info(f"Calculated Technical Confluence: {signal} (overall: {overall_confluence:.2f})")
        return summary
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on Technical Confluence.
        
        Args:
            data: DataFrame containing confluence values
            
        Returns:
            Dictionary with signal information
        """
        if 'confluence_signal' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No Technical Confluence data available'
            }
        
        # Get the most recent values
        latest_signal = data['confluence_signal'].iloc[-1]
        bullish_score = data['bullish_confluence'].iloc[-1]
        bearish_score = data['bearish_confluence'].iloc[-1]
        volatility_score = data['volatility_confluence'].iloc[-1]
        overall_score = data['overall_confluence'].iloc[-1]
        
        # Map signal to direction and strength
        if latest_signal == 'strong_bullish':
            return {
                'direction': 'bullish',
                'strength': int(bullish_score * 100),
                'description': f"Strong bullish confluence ({bullish_score:.2f})",
                'details': {
                    'bullish_score': bullish_score,
                    'bearish_score': bearish_score,
                    'volatility_score': volatility_score
                }
            }
        elif latest_signal == 'moderate_bullish':
            return {
                'direction': 'bullish',
                'strength': int(bullish_score * 80),
                'description': f"Moderate bullish confluence ({bullish_score:.2f})",
                'details': {
                    'bullish_score': bullish_score,
                    'bearish_score': bearish_score,
                    'volatility_score': volatility_score
                }
            }
        elif latest_signal == 'strong_bearish':
            return {
                'direction': 'bearish',
                'strength': int(bearish_score * 100),
                'description': f"Strong bearish confluence ({bearish_score:.2f})",
                'details': {
                    'bullish_score': bullish_score,
                    'bearish_score': bearish_score,
                    'volatility_score': volatility_score
                }
            }
        elif latest_signal == 'moderate_bearish':
            return {
                'direction': 'bearish',
                'strength': int(bearish_score * 80),
                'description': f"Moderate bearish confluence ({bearish_score:.2f})",
                'details': {
                    'bullish_score': bullish_score,
                    'bearish_score': bearish_score,
                    'volatility_score': volatility_score
                }
            }
        elif latest_signal == 'volatility_expected':
            return {
                'direction': 'volatile',
                'strength': int(volatility_score * 90),
                'description': f"High volatility expected ({volatility_score:.2f})",
                'details': {
                    'bullish_score': bullish_score,
                    'bearish_score': bearish_score,
                    'volatility_score': volatility_score
                }
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f"No clear confluence signal (overall: {overall_score:.2f})",
                'details': {
                    'bullish_score': bullish_score,
                    'bearish_score': bearish_score,
                    'volatility_score': volatility_score
                }
            }

@register_indicator
class VolatilityAdjustedMomentum(IndicatorBase):
    """
    Volatility-Adjusted Momentum Indicator
    
    Adjusts momentum indicators based on current volatility regime.
    Adapts to changing market conditions automatically.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "volatility_adjusted_momentum"
    
    @classmethod
    def get_name(cls) -> str:
        return "Volatility-Adjusted Momentum"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Adjusts momentum indicators based on current volatility regime. "
                "Adapts to changing market conditions automatically.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'momentum_indicator': 'rsi',  # Momentum indicator to adjust
            'volatility_indicator': 'average_true_range',  # Volatility indicator to use
            'lookback_period': 20,  # Period for volatility normalization
            'high_volatility_threshold': 0.8,  # Percentile for high volatility
            'low_volatility_threshold': 0.2   # Percentile for low volatility
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'momentum_indicator': 'Momentum indicator to adjust (e.g., rsi, macd)',
            'volatility_indicator': 'Volatility indicator to use (e.g., average_true_range)',
            'lookback_period': 'Period for volatility normalization',
            'high_volatility_threshold': 'Percentile threshold for high volatility',
            'low_volatility_threshold': 'Percentile threshold for low volatility'
        }
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize the Volatility-Adjusted Momentum Indicator.
        
        Args:
            params: Dictionary of parameters to customize the indicator
        """
        super().__init__(params)
        self.momentum_indicator = None
        self.volatility_indicator = None
        self._initialize_indicators()
    
    def _initialize_indicators(self):
        """Initialize component indicators."""
        registered_indicators = get_registered_indicators()
        
        # Initialize momentum indicator
        momentum_id = self.params['momentum_indicator']
        if momentum_id in registered_indicators:
            self.momentum_indicator = registered_indicators[momentum_id]()
            logger.info(f"Initialized momentum indicator: {momentum_id}")
        else:
            logger.warning(f"Unknown momentum indicator ID: {momentum_id}")
        
        # Initialize volatility indicator
        volatility_id = self.params['volatility_indicator']
        if volatility_id in registered_indicators:
            self.volatility_indicator = registered_indicators[volatility_id]()
            logger.info(f"Initialized volatility indicator: {volatility_id}")
        else:
            logger.warning(f"Unknown volatility indicator ID: {volatility_id}")
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Volatility-Adjusted Momentum for the given data.
        
        Args:
            data: DataFrame containing price/volume data
            
        Returns:
            DataFrame with volatility-adjusted momentum values added
        """
        if data.empty or self.momentum_indicator is None or self.volatility_indicator is None:
            logger.warning("Empty DataFrame or missing component indicators")
            # Create a summary DataFrame
            summary = pd.DataFrame({
                'date': [pd.Timestamp.now()],
                'vol_adj_momentum': [np.nan],
                'volatility_regime': ['unknown'],
                'raw_momentum_signal': ['neutral'],
                'adjusted_signal': ['neutral']
            })
            return summary
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Calculate momentum indicator
        momentum_result = self.momentum_indicator.calculate(result)
        momentum_signal = self.momentum_indicator.get_signal(momentum_result)
        
        # Calculate volatility indicator
        volatility_result = self.volatility_indicator.calculate(result)
        volatility_signal = self.volatility_indicator.get_signal(volatility_result)
        
        # Extract key values based on indicator types
        if self.params['momentum_indicator'] == 'rsi':
            momentum_value = momentum_result['rsi'].iloc[-1] if 'rsi' in momentum_result.columns else np.nan
            momentum_direction = momentum_signal['direction']
            momentum_strength = momentum_signal['strength'] / 100  # Normalize to 0-1
        elif self.params['momentum_indicator'] == 'macd':
            momentum_value = momentum_result['macd_histogram'].iloc[-1] if 'macd_histogram' in momentum_result.columns else np.nan
            momentum_direction = momentum_signal['direction']
            momentum_strength = momentum_signal['strength'] / 100  # Normalize to 0-1
        else:
            momentum_value = np.nan
            momentum_direction = 'neutral'
            momentum_strength = 0
        
        if self.params['volatility_indicator'] == 'average_true_range':
            volatility_value = volatility_result['atr'].iloc[-1] if 'atr' in volatility_result.columns else np.nan
            volatility_percentile = volatility_result['atr_percentile'].iloc[-1] if 'atr_percentile' in volatility_result.columns else np.nan
        elif self.params['volatility_indicator'] == 'bollinger_band_width':
            volatility_value = volatility_result['bb_width'].iloc[-1] if 'bb_width' in volatility_result.columns else np.nan
            volatility_percentile = volatility_result['bb_width_percentile'].iloc[-1] if 'bb_width_percentile' in volatility_result.columns else np.nan
        else:
            volatility_value = np.nan
            volatility_percentile = np.nan
        
        # Determine volatility regime
        high_threshold = self.params['high_volatility_threshold'] * 100
        low_threshold = self.params['low_volatility_threshold'] * 100
        
        if volatility_percentile >= high_threshold:
            volatility_regime = 'high'
            # In high volatility, reduce momentum strength to avoid false signals
            adjusted_strength = momentum_strength * 0.7
        elif volatility_percentile <= low_threshold:
            volatility_regime = 'low'
            # In low volatility, increase momentum strength for earlier signals
            adjusted_strength = min(1.0, momentum_strength * 1.3)
        else:
            volatility_regime = 'normal'
            adjusted_strength = momentum_strength
        
        # Determine adjusted signal
        if adjusted_strength >= 0.7:
            if momentum_direction == 'bullish':
                adjusted_signal = 'strong_bullish'
            elif momentum_direction == 'bearish':
                adjusted_signal = 'strong_bearish'
            else:
                adjusted_signal = 'neutral'
        elif adjusted_strength >= 0.4:
            if momentum_direction == 'bullish':
                adjusted_signal = 'moderate_bullish'
            elif momentum_direction == 'bearish':
                adjusted_signal = 'moderate_bearish'
            else:
                adjusted_signal = 'neutral'
        else:
            adjusted_signal = 'neutral'
        
        # Create a summary DataFrame
        summary = pd.DataFrame({
            'date': [pd.Timestamp.now()],
            'vol_adj_momentum': [adjusted_strength],
            'volatility_regime': [volatility_regime],
            'raw_momentum_signal': [momentum_direction],
            'adjusted_signal': [adjusted_signal],
            'momentum_value': [momentum_value],
            'volatility_value': [volatility_value],
            'volatility_percentile': [volatility_percentile]
        })
        
        logger.info(f"Calculated Volatility-Adjusted Momentum: {adjusted_signal} (regime: {volatility_regime})")
        return summary
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on Volatility-Adjusted Momentum.
        
        Args:
            data: DataFrame containing volatility-adjusted momentum values
            
        Returns:
            Dictionary with signal information
        """
        if 'adjusted_signal' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No Volatility-Adjusted Momentum data available'
            }
        
        # Get the most recent values
        latest_signal = data['adjusted_signal'].iloc[-1]
        adjusted_strength = data['vol_adj_momentum'].iloc[-1]
        volatility_regime = data['volatility_regime'].iloc[-1]
        raw_signal = data['raw_momentum_signal'].iloc[-1]
        
        # Map signal to direction and strength
        if latest_signal == 'strong_bullish':
            return {
                'direction': 'bullish',
                'strength': int(adjusted_strength * 100),
                'description': f"Strong bullish momentum in {volatility_regime} volatility regime",
                'details': {
                    'volatility_regime': volatility_regime,
                    'raw_signal': raw_signal,
                    'adjusted_strength': adjusted_strength
                }
            }
        elif latest_signal == 'moderate_bullish':
            return {
                'direction': 'bullish',
                'strength': int(adjusted_strength * 100),
                'description': f"Moderate bullish momentum in {volatility_regime} volatility regime",
                'details': {
                    'volatility_regime': volatility_regime,
                    'raw_signal': raw_signal,
                    'adjusted_strength': adjusted_strength
                }
            }
        elif latest_signal == 'strong_bearish':
            return {
                'direction': 'bearish',
                'strength': int(adjusted_strength * 100),
                'description': f"Strong bearish momentum in {volatility_regime} volatility regime",
                'details': {
                    'volatility_regime': volatility_regime,
                    'raw_signal': raw_signal,
                    'adjusted_strength': adjusted_strength
                }
            }
        elif latest_signal == 'moderate_bearish':
            return {
                'direction': 'bearish',
                'strength': int(adjusted_strength * 100),
                'description': f"Moderate bearish momentum in {volatility_regime} volatility regime",
                'details': {
                    'volatility_regime': volatility_regime,
                    'raw_signal': raw_signal,
                    'adjusted_strength': adjusted_strength
                }
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f"Neutral momentum in {volatility_regime} volatility regime",
                'details': {
                    'volatility_regime': volatility_regime,
                    'raw_signal': raw_signal,
                    'adjusted_strength': adjusted_strength
                }
            }

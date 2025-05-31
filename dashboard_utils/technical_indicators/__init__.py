"""
Technical Indicators Module

This package provides a modular framework for calculating and managing technical indicators
for options trading recommendations.
"""

from .indicator_base import IndicatorBase, register_indicator, get_registered_indicators
from .volatility_indicators import IVPercentile, BollingerBandWidth, AverageTrueRange
from .momentum_indicators import RSI, MACD, RateOfChange
from .options_indicators import OptionsVolumeOpenInterestRatio, PutCallRatio, IVSkewAnalysis
from .composite_indicators import TechnicalConfluenceIndicator, VolatilityAdjustedMomentum

__all__ = [
    'IndicatorBase',
    'register_indicator',
    'get_registered_indicators',
    'IVPercentile',
    'BollingerBandWidth',
    'AverageTrueRange',
    'RSI',
    'MACD',
    'RateOfChange',
    'OptionsVolumeOpenInterestRatio',
    'PutCallRatio',
    'IVSkewAnalysis',
    'TechnicalConfluenceIndicator',
    'VolatilityAdjustedMomentum'
]

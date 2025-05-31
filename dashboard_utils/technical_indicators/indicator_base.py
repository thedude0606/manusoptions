"""
Base Indicator Module

This module provides the base class and registration mechanism for all technical indicators.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Type, Set, Callable
from abc import ABC, abstractmethod

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Registry to store all indicator classes
_INDICATOR_REGISTRY: Dict[str, Type['IndicatorBase']] = {}

def register_indicator(indicator_class: Type['IndicatorBase']) -> Type['IndicatorBase']:
    """
    Decorator to register an indicator class in the global registry.
    
    Args:
        indicator_class: The indicator class to register
        
    Returns:
        The same indicator class (allows use as a decorator)
    
    Example:
        @register_indicator
        class MyIndicator(IndicatorBase):
            ...
    """
    indicator_id = indicator_class.get_id()
    if indicator_id in _INDICATOR_REGISTRY:
        logger.warning(f"Indicator with ID '{indicator_id}' already registered. Overwriting.")
    
    _INDICATOR_REGISTRY[indicator_id] = indicator_class
    logger.info(f"Registered indicator: {indicator_id}")
    return indicator_class

def get_registered_indicators() -> Dict[str, Type['IndicatorBase']]:
    """
    Get all registered indicator classes.
    
    Returns:
        Dictionary mapping indicator IDs to indicator classes
    """
    return _INDICATOR_REGISTRY.copy()

class IndicatorBase(ABC):
    """
    Base class for all technical indicators.
    
    All indicator implementations should inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize the indicator with optional parameters.
        
        Args:
            params: Dictionary of parameters to customize the indicator
        """
        self.params = params or {}
        self.result = None
        self.symbol = None
        self._validate_params()
        logger.info(f"Initialized {self.get_id()} indicator with params: {self.params}")
    
    @classmethod
    @abstractmethod
    def get_id(cls) -> str:
        """
        Get the unique identifier for this indicator.
        
        Returns:
            String identifier for the indicator
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """
        Get the human-readable name for this indicator.
        
        Returns:
            Human-readable name for the indicator
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """
        Get a description of what this indicator measures and how it's used.
        
        Returns:
            Description of the indicator
        """
        pass
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """
        Get the default parameters for this indicator.
        
        Returns:
            Dictionary of default parameter values
        """
        return {}
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        """
        Get descriptions for each parameter.
        
        Returns:
            Dictionary mapping parameter names to descriptions
        """
        return {}
    
    @classmethod
    def get_required_data(cls) -> Set[str]:
        """
        Get the set of data fields required by this indicator.
        
        Returns:
            Set of field names required in the input data
        """
        return {'open', 'high', 'low', 'close'}
    
    def _validate_params(self) -> None:
        """
        Validate the provided parameters against defaults and constraints.
        
        Raises:
            ValueError: If parameters are invalid
        """
        default_params = self.get_default_params()
        
        # Apply defaults for missing parameters
        for key, default_value in default_params.items():
            if key not in self.params:
                self.params[key] = default_value
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the indicator values for the given data.
        
        Args:
            data: DataFrame containing price/volume data
            
        Returns:
            DataFrame with indicator values added as new columns
        """
        pass
    
    def calculate_incremental(self, data: pd.DataFrame, previous_result: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicator values incrementally when new data arrives.
        
        This method can be overridden for more efficient incremental calculations.
        The default implementation recalculates everything.
        
        Args:
            data: DataFrame containing the latest price/volume data
            previous_result: DataFrame containing previous calculation results
            
        Returns:
            Updated DataFrame with indicator values
        """
        # Default implementation just recalculates everything
        return self.calculate(data)
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on the indicator values.
        
        Args:
            data: DataFrame containing price data and indicator values
            
        Returns:
            Dictionary with signal information (direction, strength, etc.)
        """
        # Default implementation returns no signal
        return {
            'direction': 'neutral',
            'strength': 0,
            'description': 'No signal implementation for base indicator'
        }
    
    def get_visualization_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get data formatted for visualization of this indicator.
        
        Args:
            data: DataFrame containing price data and indicator values
            
        Returns:
            Dictionary with visualization data
        """
        # Default implementation returns empty visualization data
        return {
            'type': 'line',
            'data': [],
            'layout': {}
        }
    
    def set_symbol(self, symbol: str) -> None:
        """
        Set the symbol context for this indicator.
        
        Args:
            symbol: The symbol string
        """
        self.symbol = symbol
        logger.info(f"Set symbol context for {self.get_id()}: {symbol}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert indicator configuration to dictionary for serialization.
        
        Returns:
            Dictionary representation of the indicator
        """
        return {
            'id': self.get_id(),
            'name': self.get_name(),
            'params': self.params,
            'symbol': self.symbol
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndicatorBase':
        """
        Create an indicator instance from a dictionary representation.
        
        Args:
            data: Dictionary representation of the indicator
            
        Returns:
            Indicator instance
        """
        indicator_id = data.get('id')
        if indicator_id not in _INDICATOR_REGISTRY:
            raise ValueError(f"Unknown indicator ID: {indicator_id}")
        
        indicator_class = _INDICATOR_REGISTRY[indicator_id]
        instance = indicator_class(params=data.get('params', {}))
        
        if 'symbol' in data:
            instance.set_symbol(data['symbol'])
        
        return instance

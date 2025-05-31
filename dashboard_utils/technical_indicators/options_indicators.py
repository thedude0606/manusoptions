"""
Options-Specific Indicators Module

This module provides options-specific technical indicators for options trading.
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
class OptionsVolumeOpenInterestRatio(IndicatorBase):
    """
    Options Volume/Open Interest Ratio Indicator
    
    Ratio of current day's options volume to open interest.
    Identifies unusual options activity that may indicate informed trading.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "volume_oi_ratio"
    
    @classmethod
    def get_name(cls) -> str:
        return "Options Volume/Open Interest Ratio"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Ratio of current day's options volume to open interest. "
                "Identifies unusual options activity that may indicate informed trading.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'high_ratio_threshold': 0.5,  # Threshold for high V/OI ratio
            'extreme_ratio_threshold': 1.0,  # Threshold for extreme V/OI ratio
            'min_volume': 100  # Minimum volume to consider
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'high_ratio_threshold': 'Threshold above which V/OI ratio is considered high',
            'extreme_ratio_threshold': 'Threshold above which V/OI ratio is considered extreme',
            'min_volume': 'Minimum volume to consider for analysis'
        }
    
    @classmethod
    def get_required_data(cls) -> Set[str]:
        return {'volume', 'openInterest'}
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Volume/Open Interest Ratio for the given options data.
        
        Args:
            data: DataFrame containing options data
            
        Returns:
            DataFrame with V/OI ratio values added
        """
        if not all(col in data.columns for col in ['volume', 'openInterest']):
            logger.warning("Required columns (volume, openInterest) not found in data")
            data['volume_oi_ratio'] = np.nan
            data['volume_oi_signal'] = 'neutral'
            return data
        
        high_ratio = self.params['high_ratio_threshold']
        extreme_ratio = self.params['extreme_ratio_threshold']
        min_volume = self.params['min_volume']
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Calculate V/OI ratio, handling division by zero
        result['volume_oi_ratio'] = np.where(
            result['openInterest'] > 0,
            result['volume'] / result['openInterest'],
            np.nan
        )
        
        # Generate signal based on ratio thresholds and minimum volume
        conditions = [
            (result['volume_oi_ratio'] >= extreme_ratio) & (result['volume'] >= min_volume),
            (result['volume_oi_ratio'] >= high_ratio) & (result['volume'] >= min_volume)
        ]
        choices = ['extreme_activity', 'high_activity']
        result['volume_oi_signal'] = np.select(conditions, choices, default='normal_activity')
        
        logger.info(f"Calculated Volume/Open Interest Ratio for {len(data)} options contracts")
        return result
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on Volume/Open Interest Ratio.
        
        Args:
            data: DataFrame containing V/OI ratio values
            
        Returns:
            Dictionary with signal information
        """
        if 'volume_oi_ratio' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No Volume/Open Interest data available'
            }
        
        # Filter for contracts with signals
        high_activity = data[data['volume_oi_signal'] == 'high_activity']
        extreme_activity = data[data['volume_oi_signal'] == 'extreme_activity']
        
        # Count contracts with unusual activity
        high_count = len(high_activity)
        extreme_count = len(extreme_activity)
        total_count = len(data)
        
        # Calculate average ratios
        avg_ratio = data['volume_oi_ratio'].mean()
        
        if extreme_count > 0:
            # Get the top 3 extreme contracts by ratio
            top_extreme = extreme_activity.nlargest(3, 'volume_oi_ratio')
            
            # Extract strike prices and option types
            strikes = top_extreme['strikePrice'].tolist()
            option_types = top_extreme['putCall'].tolist()
            
            # Determine if activity is concentrated in calls or puts
            call_count = option_types.count('CALL')
            put_count = option_types.count('PUT')
            
            if call_count > put_count:
                direction = 'bullish'
                description = f"Extreme call activity detected ({extreme_count} contracts, avg ratio: {avg_ratio:.2f})"
            elif put_count > call_count:
                direction = 'bearish'
                description = f"Extreme put activity detected ({extreme_count} contracts, avg ratio: {avg_ratio:.2f})"
            else:
                direction = 'volatile'
                description = f"Extreme mixed activity detected ({extreme_count} contracts, avg ratio: {avg_ratio:.2f})"
            
            # Strength based on percentage of contracts with extreme activity
            strength = min(100, int((extreme_count / total_count) * 100) + 50)
            
            return {
                'direction': direction,
                'strength': strength,
                'description': description,
                'details': {
                    'top_strikes': strikes,
                    'top_types': option_types,
                    'extreme_count': extreme_count,
                    'high_count': high_count
                }
            }
        
        elif high_count > 0:
            # Get the top 3 high activity contracts by ratio
            top_high = high_activity.nlargest(3, 'volume_oi_ratio')
            
            # Extract strike prices and option types
            strikes = top_high['strikePrice'].tolist()
            option_types = top_high['putCall'].tolist()
            
            # Determine if activity is concentrated in calls or puts
            call_count = option_types.count('CALL')
            put_count = option_types.count('PUT')
            
            if call_count > put_count:
                direction = 'bullish'
                description = f"High call activity detected ({high_count} contracts, avg ratio: {avg_ratio:.2f})"
            elif put_count > call_count:
                direction = 'bearish'
                description = f"High put activity detected ({high_count} contracts, avg ratio: {avg_ratio:.2f})"
            else:
                direction = 'volatile'
                description = f"High mixed activity detected ({high_count} contracts, avg ratio: {avg_ratio:.2f})"
            
            # Strength based on percentage of contracts with high activity
            strength = min(80, int((high_count / total_count) * 100) + 30)
            
            return {
                'direction': direction,
                'strength': strength,
                'description': description,
                'details': {
                    'top_strikes': strikes,
                    'top_types': option_types,
                    'high_count': high_count
                }
            }
        
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f"Normal options activity (avg ratio: {avg_ratio:.2f})"
            }

@register_indicator
class PutCallRatio(IndicatorBase):
    """
    Put/Call Ratio with Volume Analysis
    
    Ratio of put volume to call volume with additional volume analysis.
    Sentiment indicator that can identify extreme market positioning.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "put_call_ratio"
    
    @classmethod
    def get_name(cls) -> str:
        return "Put/Call Ratio"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Ratio of put volume to call volume with additional volume analysis. "
                "Sentiment indicator that can identify extreme market positioning.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'high_ratio_threshold': 1.5,  # Threshold for high put/call ratio
            'low_ratio_threshold': 0.5,   # Threshold for low put/call ratio
            'lookback_period': 5,         # Days to look back for average ratio
            'min_total_volume': 1000      # Minimum total volume to consider
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'high_ratio_threshold': 'Threshold above which put/call ratio is considered high',
            'low_ratio_threshold': 'Threshold below which put/call ratio is considered low',
            'lookback_period': 'Number of days to look back for average ratio',
            'min_total_volume': 'Minimum total volume to consider for analysis'
        }
    
    @classmethod
    def get_required_data(cls) -> Set[str]:
        return {'volume', 'putCall'}
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Put/Call Ratio for the given options data.
        
        Args:
            data: DataFrame containing options data
            
        Returns:
            DataFrame with put/call ratio values added
        """
        if not all(col in data.columns for col in ['volume', 'putCall']):
            logger.warning("Required columns (volume, putCall) not found in data")
            # Create a summary DataFrame with the ratio
            summary = pd.DataFrame({
                'date': [pd.Timestamp.now()],
                'put_call_ratio': [np.nan],
                'put_volume': [np.nan],
                'call_volume': [np.nan],
                'total_volume': [np.nan],
                'put_call_signal': ['neutral']
            })
            return summary
        
        high_ratio = self.params['high_ratio_threshold']
        low_ratio = self.params['low_ratio_threshold']
        min_total_volume = self.params['min_total_volume']
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Calculate total put and call volume
        put_volume = result[result['putCall'] == 'PUT']['volume'].sum()
        call_volume = result[result['putCall'] == 'CALL']['volume'].sum()
        total_volume = put_volume + call_volume
        
        # Calculate put/call ratio, handling division by zero
        put_call_ratio = put_volume / call_volume if call_volume > 0 else np.nan
        
        # Generate signal based on ratio thresholds and minimum volume
        if total_volume >= min_total_volume:
            if put_call_ratio >= high_ratio:
                signal = 'high_put_call'
            elif put_call_ratio <= low_ratio:
                signal = 'low_put_call'
            else:
                signal = 'normal_put_call'
        else:
            signal = 'insufficient_volume'
        
        # Create a summary DataFrame with the ratio
        summary = pd.DataFrame({
            'date': [pd.Timestamp.now()],
            'put_call_ratio': [put_call_ratio],
            'put_volume': [put_volume],
            'call_volume': [call_volume],
            'total_volume': [total_volume],
            'put_call_signal': [signal]
        })
        
        logger.info(f"Calculated Put/Call Ratio: {put_call_ratio:.2f} (Put Vol: {put_volume}, Call Vol: {call_volume})")
        return summary
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on Put/Call Ratio.
        
        Args:
            data: DataFrame containing put/call ratio values
            
        Returns:
            Dictionary with signal information
        """
        if 'put_call_ratio' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No Put/Call Ratio data available'
            }
        
        # Get the most recent values
        latest_ratio = data['put_call_ratio'].iloc[-1]
        latest_signal = data['put_call_signal'].iloc[-1]
        put_volume = data['put_volume'].iloc[-1]
        call_volume = data['call_volume'].iloc[-1]
        total_volume = data['total_volume'].iloc[-1]
        
        if latest_signal == 'high_put_call':
            # High put/call ratio often indicates excessive bearishness (contrarian bullish)
            strength = min(100, int((latest_ratio - self.params['high_ratio_threshold']) * 50) + 50)
            return {
                'direction': 'contrarian_bullish',
                'strength': strength,
                'description': f"High put/call ratio ({latest_ratio:.2f}) suggests excessive bearishness",
                'details': {
                    'put_volume': put_volume,
                    'call_volume': call_volume,
                    'total_volume': total_volume
                }
            }
        elif latest_signal == 'low_put_call':
            # Low put/call ratio often indicates excessive bullishness (contrarian bearish)
            strength = min(100, int((self.params['low_ratio_threshold'] / latest_ratio) * 50) + 50)
            return {
                'direction': 'contrarian_bearish',
                'strength': strength,
                'description': f"Low put/call ratio ({latest_ratio:.2f}) suggests excessive bullishness",
                'details': {
                    'put_volume': put_volume,
                    'call_volume': call_volume,
                    'total_volume': total_volume
                }
            }
        elif latest_signal == 'insufficient_volume':
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f"Insufficient volume for reliable put/call ratio analysis (total: {total_volume})"
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f"Normal put/call ratio ({latest_ratio:.2f})"
            }

@register_indicator
class IVSkewAnalysis(IndicatorBase):
    """
    IV Skew Analysis Indicator
    
    Measures the difference in IV between OTM puts and calls.
    Identifies market sentiment and potential hedging demand.
    """
    
    @classmethod
    def get_id(cls) -> str:
        return "iv_skew"
    
    @classmethod
    def get_name(cls) -> str:
        return "IV Skew Analysis"
    
    @classmethod
    def get_description(cls) -> str:
        return ("Measures the difference in IV between OTM puts and calls. "
                "Identifies market sentiment and potential hedging demand.")
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            'otm_range_pct': 10,     # Percentage OTM to analyze
            'high_skew_threshold': 1.3,  # Threshold for high put skew
            'low_skew_threshold': 0.8    # Threshold for low put skew
        }
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        return {
            'otm_range_pct': 'Percentage OTM to analyze for skew calculation',
            'high_skew_threshold': 'Threshold above which put skew is considered high',
            'low_skew_threshold': 'Threshold below which put skew is considered low'
        }
    
    @classmethod
    def get_required_data(cls) -> Set[str]:
        return {'strikePrice', 'putCall', 'impliedVolatility'}
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate IV Skew for the given options data.
        
        Args:
            data: DataFrame containing options data
            
        Returns:
            DataFrame with IV skew values added
        """
        required_cols = ['strikePrice', 'putCall', 'impliedVolatility']
        if not all(col in data.columns for col in required_cols):
            logger.warning(f"Required columns {required_cols} not found in data")
            # Create a summary DataFrame with the skew metrics
            summary = pd.DataFrame({
                'date': [pd.Timestamp.now()],
                'put_skew': [np.nan],
                'call_skew': [np.nan],
                'skew_ratio': [np.nan],
                'iv_skew_signal': ['neutral']
            })
            return summary
        
        otm_range_pct = self.params['otm_range_pct'] / 100
        high_skew = self.params['high_skew_threshold']
        low_skew = self.params['low_skew_threshold']
        
        # Make a copy to avoid modifying the original
        result = data.copy()
        
        # Find the at-the-money (ATM) strike price
        # Assuming the data includes an 'underlyingPrice' column
        if 'underlyingPrice' in result.columns:
            underlying_price = result['underlyingPrice'].iloc[0]
        else:
            # If no underlying price, estimate it as the middle of the strike range
            underlying_price = (result['strikePrice'].min() + result['strikePrice'].max()) / 2
            logger.warning(f"No underlyingPrice column found, estimating as {underlying_price}")
        
        # Define OTM ranges
        otm_put_min = underlying_price * (1 - otm_range_pct)
        otm_put_max = underlying_price
        otm_call_min = underlying_price
        otm_call_max = underlying_price * (1 + otm_range_pct)
        
        # Filter for OTM puts and calls
        otm_puts = result[(result['putCall'] == 'PUT') & 
                          (result['strikePrice'] >= otm_put_min) & 
                          (result['strikePrice'] <= otm_put_max)]
        
        otm_calls = result[(result['putCall'] == 'CALL') & 
                           (result['strikePrice'] >= otm_call_min) & 
                           (result['strikePrice'] <= otm_call_max)]
        
        # Calculate average IV for OTM puts and calls
        avg_put_iv = otm_puts['impliedVolatility'].mean() if not otm_puts.empty else np.nan
        avg_call_iv = otm_calls['impliedVolatility'].mean() if not otm_calls.empty else np.nan
        
        # Calculate skew ratio (put IV / call IV)
        skew_ratio = avg_put_iv / avg_call_iv if not np.isnan(avg_put_iv) and not np.isnan(avg_call_iv) and avg_call_iv > 0 else np.nan
        
        # Generate signal based on skew ratio
        if np.isnan(skew_ratio):
            signal = 'insufficient_data'
        elif skew_ratio >= high_skew:
            signal = 'high_put_skew'
        elif skew_ratio <= low_skew:
            signal = 'low_put_skew'
        else:
            signal = 'normal_skew'
        
        # Create a summary DataFrame with the skew metrics
        summary = pd.DataFrame({
            'date': [pd.Timestamp.now()],
            'put_skew': [avg_put_iv],
            'call_skew': [avg_call_iv],
            'skew_ratio': [skew_ratio],
            'iv_skew_signal': [signal]
        })
        
        logger.info(f"Calculated IV Skew Ratio: {skew_ratio:.2f} (Put IV: {avg_put_iv:.2f}, Call IV: {avg_call_iv:.2f})")
        return summary
    
    def get_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signals based on IV Skew.
        
        Args:
            data: DataFrame containing IV skew values
            
        Returns:
            Dictionary with signal information
        """
        if 'skew_ratio' not in data.columns or data.empty:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': 'No IV Skew data available'
            }
        
        # Get the most recent values
        latest_ratio = data['skew_ratio'].iloc[-1]
        latest_signal = data['iv_skew_signal'].iloc[-1]
        put_iv = data['put_skew'].iloc[-1]
        call_iv = data['call_skew'].iloc[-1]
        
        if latest_signal == 'high_put_skew':
            # High put skew indicates market fear/hedging (potential volatility)
            strength = min(100, int((latest_ratio - self.params['high_skew_threshold']) * 50) + 50)
            return {
                'direction': 'volatile_bearish',
                'strength': strength,
                'description': f"High put skew ({latest_ratio:.2f}) suggests market fear and potential volatility",
                'details': {
                    'put_iv': put_iv,
                    'call_iv': call_iv
                }
            }
        elif latest_signal == 'low_put_skew':
            # Low put skew indicates market complacency (potential vulnerability)
            strength = min(100, int((self.params['low_skew_threshold'] / latest_ratio) * 50) + 50)
            return {
                'direction': 'complacent_bullish',
                'strength': strength,
                'description': f"Low put skew ({latest_ratio:.2f}) suggests market complacency",
                'details': {
                    'put_iv': put_iv,
                    'call_iv': call_iv
                }
            }
        elif latest_signal == 'insufficient_data':
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': "Insufficient data for IV skew analysis"
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'description': f"Normal IV skew ({latest_ratio:.2f})"
            }

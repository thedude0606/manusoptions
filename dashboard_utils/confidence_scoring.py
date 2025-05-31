"""
Confidence Scoring System for Options Recommendations

This module provides a framework for calculating confidence scores for options trading recommendations
based on multiple technical indicators, options data, and market conditions.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class ConfidenceScorer:
    """
    Calculates confidence scores for options trading recommendations based on
    technical indicators, options data, and market conditions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the confidence scorer with optional configuration.
        
        Args:
            config: Dictionary of configuration parameters
        """
        self.config = config or {}
        self.default_config = {
            'min_confidence_threshold': 60,  # Minimum confidence score to generate a recommendation
            'technical_weight': 0.5,         # Weight for technical indicators
            'options_weight': 0.3,           # Weight for options-specific data
            'market_weight': 0.2,            # Weight for market conditions
            'profit_target_pct': 10.0,       # Target profit percentage
            'max_hold_time_minutes': 60,     # Maximum hold time in minutes
            'indicator_weights': {
                'iv_percentile': 0.15,
                'rsi': 0.15,
                'macd': 0.10,
                'bollinger_band_width': 0.10,
                'average_true_range': 0.10,
                'volume_oi_ratio': 0.15,
                'put_call_ratio': 0.10,
                'iv_skew': 0.10,
                'technical_confluence': 0.20,
                'volatility_adjusted_momentum': 0.15
            }
        }
        
        # Apply defaults for missing config values
        for key, default_value in self.default_config.items():
            if key not in self.config:
                self.config[key] = default_value
        
        # Normalize indicator weights to sum to 1.0
        total_weight = sum(self.config['indicator_weights'].values())
        if total_weight != 1.0:
            for key in self.config['indicator_weights']:
                self.config['indicator_weights'][key] /= total_weight
        
        logger.info(f"Initialized ConfidenceScorer with config: {self.config}")
    
    def calculate_confidence(self, 
                            technical_indicators: Dict[str, Any],
                            options_data: pd.DataFrame,
                            market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate confidence score for options trading recommendations.
        
        Args:
            technical_indicators: Dictionary of technical indicator results
            options_data: DataFrame containing options chain data
            market_data: Optional dictionary of market condition data
            
        Returns:
            Dictionary with confidence scores and recommendation details
        """
        logger.info("Calculating confidence scores for options recommendations")
        
        # Initialize result dictionary
        result = {
            'timestamp': datetime.now(),
            'overall_confidence': 0,
            'technical_score': 0,
            'options_score': 0,
            'market_score': 0,
            'direction': 'neutral',
            'recommended_contracts': [],
            'profit_target_pct': self.config['profit_target_pct'],
            'max_hold_time_minutes': self.config['max_hold_time_minutes'],
            'indicator_signals': {},
            'debug_info': {}
        }
        
        # Calculate technical indicators score
        technical_score, direction, indicator_signals = self._calculate_technical_score(technical_indicators)
        result['technical_score'] = technical_score
        result['indicator_signals'] = indicator_signals
        
        # Calculate options data score
        options_score, options_signals = self._calculate_options_score(options_data, direction)
        result['options_score'] = options_score
        result['options_signals'] = options_signals
        
        # Calculate market conditions score
        market_score = self._calculate_market_score(market_data)
        result['market_score'] = market_score
        
        # Calculate overall confidence score (weighted average)
        overall_confidence = (
            technical_score * self.config['technical_weight'] +
            options_score * self.config['options_weight'] +
            market_score * self.config['market_weight']
        )
        result['overall_confidence'] = round(overall_confidence, 1)
        
        # Determine final direction based on technical and options scores
        if technical_score >= 60 and direction == 'bullish':
            result['direction'] = 'bullish'
        elif technical_score >= 60 and direction == 'bearish':
            result['direction'] = 'bearish'
        else:
            result['direction'] = 'neutral'
        
        # Find recommended contracts if confidence is above threshold
        if result['overall_confidence'] >= self.config['min_confidence_threshold'] and result['direction'] != 'neutral':
            result['recommended_contracts'] = self._find_recommended_contracts(
                options_data, 
                result['direction'],
                result['overall_confidence']
            )
        
        # Add debug information
        result['debug_info'] = {
            'config': self.config,
            'technical_details': indicator_signals,
            'options_details': options_signals,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Calculated confidence score: {result['overall_confidence']} ({result['direction']})")
        return result
    
    def _calculate_technical_score(self, 
                                  technical_indicators: Dict[str, Any]) -> Tuple[float, str, Dict[str, Any]]:
        """
        Calculate score based on technical indicators.
        
        Args:
            technical_indicators: Dictionary of technical indicator results
            
        Returns:
            Tuple of (score, direction, indicator_signals)
        """
        if not technical_indicators:
            logger.warning("No technical indicators provided")
            return 0, 'neutral', {}
        
        # Initialize scores and signals
        bullish_score = 0
        bearish_score = 0
        total_weight = 0
        indicator_signals = {}
        
        # Process each indicator
        for indicator_id, indicator_data in technical_indicators.items():
            if indicator_id not in self.config['indicator_weights']:
                logger.warning(f"Unknown indicator: {indicator_id}, skipping")
                continue
            
            weight = self.config['indicator_weights'][indicator_id]
            
            # Extract signal from indicator data
            if isinstance(indicator_data, dict) and 'signal' in indicator_data:
                signal = indicator_data['signal']
            elif isinstance(indicator_data, pd.DataFrame) and not indicator_data.empty:
                # Try to get signal from the last row
                if 'direction' in indicator_data.columns:
                    signal = {
                        'direction': indicator_data['direction'].iloc[-1],
                        'strength': indicator_data['strength'].iloc[-1] if 'strength' in indicator_data.columns else 50
                    }
                else:
                    # No clear signal column, skip this indicator
                    logger.warning(f"No signal information found for {indicator_id}")
                    continue
            else:
                # No valid data, skip this indicator
                logger.warning(f"Invalid data format for {indicator_id}")
                continue
            
            # Store signal for debugging
            indicator_signals[indicator_id] = signal
            
            # Update scores based on signal direction and strength
            direction = signal.get('direction', 'neutral')
            strength = signal.get('strength', 50) / 100  # Normalize to 0-1
            
            if direction == 'bullish':
                bullish_score += strength * weight
            elif direction == 'bearish':
                bearish_score += strength * weight
            
            total_weight += weight
        
        # Normalize scores if we have any valid indicators
        if total_weight > 0:
            bullish_score = (bullish_score / total_weight) * 100
            bearish_score = (bearish_score / total_weight) * 100
        
        # Determine overall direction and score
        if bullish_score > bearish_score:
            direction = 'bullish'
            score = bullish_score
        elif bearish_score > bullish_score:
            direction = 'bearish'
            score = bearish_score
        else:
            direction = 'neutral'
            score = 0
        
        logger.info(f"Technical score: {score:.1f} ({direction})")
        return score, direction, indicator_signals
    
    def _calculate_options_score(self, 
                               options_data: pd.DataFrame,
                               technical_direction: str) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate score based on options-specific data.
        
        Args:
            options_data: DataFrame containing options chain data
            technical_direction: Direction from technical indicators
            
        Returns:
            Tuple of (score, options_signals)
        """
        if options_data is None or options_data.empty:
            logger.warning("No options data provided")
            return 0, {}
        
        # Initialize options signals dictionary
        options_signals = {
            'iv_percentile': 0,
            'volume_oi_ratio': 0,
            'put_call_volume_ratio': 0,
            'skew': 0,
            'liquidity': 0
        }
        
        try:
            # Calculate IV percentile (if available)
            if 'impliedVolatility' in options_data.columns:
                iv_values = options_data['impliedVolatility'].dropna()
                if not iv_values.empty:
                    avg_iv = iv_values.mean()
                    # This is a simplified IV percentile calculation
                    # In a real implementation, you'd compare to historical IV
                    options_signals['iv_percentile'] = min(100, avg_iv * 100)
            
            # Calculate volume/OI ratio
            if all(col in options_data.columns for col in ['volume', 'openInterest']):
                valid_data = options_data[options_data['openInterest'] > 0]
                if not valid_data.empty:
                    ratios = valid_data['volume'] / valid_data['openInterest']
                    avg_ratio = ratios.mean()
                    options_signals['volume_oi_ratio'] = min(100, avg_ratio * 100)
            
            # Calculate put/call volume ratio
            if all(col in options_data.columns for col in ['volume', 'putCall']):
                put_volume = options_data[options_data['putCall'] == 'PUT']['volume'].sum()
                call_volume = options_data[options_data['putCall'] == 'CALL']['volume'].sum()
                if call_volume > 0:
                    put_call_ratio = put_volume / call_volume
                    options_signals['put_call_volume_ratio'] = put_call_ratio
            
            # Calculate liquidity score
            if all(col in options_data.columns for col in ['bid', 'ask']):
                spreads = options_data['ask'] - options_data['bid']
                relative_spreads = spreads / ((options_data['bid'] + options_data['ask']) / 2)
                avg_relative_spread = relative_spreads.mean()
                # Lower spread = higher liquidity score
                options_signals['liquidity'] = max(0, 100 - (avg_relative_spread * 100))
            
            # Calculate overall options score
            # This is a simplified scoring model
            iv_score = 0
            if options_signals['iv_percentile'] > 70:
                # High IV is good for selling options
                iv_score = 80 if technical_direction == 'bearish' else 40
            elif options_signals['iv_percentile'] < 30:
                # Low IV is good for buying options
                iv_score = 80 if technical_direction == 'bullish' else 40
            else:
                iv_score = 50
            
            volume_score = min(100, options_signals['volume_oi_ratio'])
            liquidity_score = options_signals['liquidity']
            
            # Combine scores with weights
            options_score = (iv_score * 0.4) + (volume_score * 0.3) + (liquidity_score * 0.3)
            
            logger.info(f"Options score: {options_score:.1f}")
            return options_score, options_signals
            
        except Exception as e:
            logger.error(f"Error calculating options score: {e}")
            return 0, options_signals
    
    def _calculate_market_score(self, market_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate score based on market conditions.
        
        Args:
            market_data: Dictionary of market condition data
            
        Returns:
            Market conditions score
        """
        if not market_data:
            logger.warning("No market data provided, using neutral market score")
            return 50  # Neutral score
        
        # This is a placeholder for market condition scoring
        # In a real implementation, you'd analyze market data more thoroughly
        
        # Default to neutral score
        market_score = 50
        
        logger.info(f"Market score: {market_score:.1f}")
        return market_score
    
    def _find_recommended_contracts(self, 
                                  options_data: pd.DataFrame,
                                  direction: str,
                                  confidence: float) -> List[Dict[str, Any]]:
        """
        Find recommended option contracts based on direction and confidence.
        
        Args:
            options_data: DataFrame containing options chain data
            direction: Trading direction ('bullish' or 'bearish')
            confidence: Overall confidence score
            
        Returns:
            List of recommended contracts with details
        """
        if options_data is None or options_data.empty:
            logger.warning("No options data provided for contract recommendations")
            return []
        
        try:
            # Filter for required columns
            required_cols = ['putCall', 'strikePrice', 'bid', 'ask', 'impliedVolatility', 
                            'delta', 'gamma', 'theta', 'vega', 'daysToExpiration']
            
            missing_cols = [col for col in required_cols if col not in options_data.columns]
            if missing_cols:
                logger.warning(f"Missing required columns for contract recommendations: {missing_cols}")
                return []
            
            # Make a copy to avoid modifying the original
            options = options_data.copy()
            
            # Filter based on direction
            if direction == 'bullish':
                # For bullish direction, recommend call options
                filtered_options = options[options['putCall'] == 'CALL']
            else:
                # For bearish direction, recommend put options
                filtered_options = options[options['putCall'] == 'PUT']
            
            if filtered_options.empty:
                logger.warning(f"No {direction} options found")
                return []
            
            # Filter for reasonable expiration (7-30 days)
            filtered_options = filtered_options[
                (filtered_options['daysToExpiration'] >= 7) & 
                (filtered_options['daysToExpiration'] <= 30)
            ]
            
            if filtered_options.empty:
                logger.warning("No options with suitable expiration found")
                return []
            
            # Calculate mid price
            filtered_options['mid_price'] = (filtered_options['bid'] + filtered_options['ask']) / 2
            
            # Filter for reasonable delta (0.3-0.7 for directional trades)
            if direction == 'bullish':
                delta_filter = (filtered_options['delta'] >= 0.3) & (filtered_options['delta'] <= 0.7)
            else:
                # For puts, delta is negative, so we take absolute value
                delta_filter = (filtered_options['delta'].abs() >= 0.3) & (filtered_options['delta'].abs() <= 0.7)
            
            filtered_options = filtered_options[delta_filter]
            
            if filtered_options.empty:
                logger.warning("No options with suitable delta found")
                return []
            
            # Calculate a score for each contract based on multiple factors
            # This is a simplified scoring model
            filtered_options['contract_score'] = (
                # Higher delta is better for directional trades (normalized to 0-1)
                filtered_options['delta'].abs() * 0.3 +
                # Higher gamma is better for short-term trades
                filtered_options['gamma'] * 100 * 0.2 +
                # Lower theta (less negative) is better
                (1 + filtered_options['theta']) * 0.2 +
                # Lower IV is better for buying options
                (1 - filtered_options['impliedVolatility'] / filtered_options['impliedVolatility'].max()) * 0.2 +
                # Tighter bid-ask spread is better
                (1 - (filtered_options['ask'] - filtered_options['bid']) / filtered_options['mid_price']) * 0.1
            )
            
            # Sort by score and take top 3
            top_contracts = filtered_options.nlargest(3, 'contract_score')
            
            # Format results
            recommendations = []
            for _, contract in top_contracts.iterrows():
                # Calculate expected profit based on confidence and target
                target_profit_pct = self.config['profit_target_pct']
                confidence_factor = confidence / 100
                expected_profit_pct = target_profit_pct * confidence_factor
                
                # Calculate target price
                if direction == 'bullish':
                    target_price = contract['mid_price'] * (1 + expected_profit_pct / 100)
                else:
                    target_price = contract['mid_price'] * (1 + expected_profit_pct / 100)
                
                # Format recommendation
                recommendation = {
                    'symbol': contract.get('symbol', 'Unknown'),
                    'underlying': contract.get('underlying', 'Unknown'),
                    'type': contract['putCall'],
                    'strike': contract['strikePrice'],
                    'expiration': contract.get('expirationDate', 'Unknown'),
                    'days_to_expiration': contract['daysToExpiration'],
                    'entry_price': contract['mid_price'],
                    'target_price': round(target_price, 2),
                    'target_profit_pct': round(expected_profit_pct, 1),
                    'max_hold_time': self.config['max_hold_time_minutes'],
                    'confidence': round(confidence, 1),
                    'delta': contract['delta'],
                    'gamma': contract['gamma'],
                    'theta': contract['theta'],
                    'vega': contract['vega'],
                    'implied_volatility': contract['impliedVolatility'],
                    'contract_score': round(contract['contract_score'] * 100, 1)
                }
                
                recommendations.append(recommendation)
            
            logger.info(f"Found {len(recommendations)} recommended contracts")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error finding recommended contracts: {e}")
            return []
    
    def get_confidence_level_description(self, confidence: float) -> str:
        """
        Get a human-readable description of the confidence level.
        
        Args:
            confidence: Confidence score (0-100)
            
        Returns:
            Description of confidence level
        """
        if confidence >= 90:
            return "Very High"
        elif confidence >= 75:
            return "High"
        elif confidence >= 60:
            return "Moderate"
        elif confidence >= 40:
            return "Low"
        else:
            return "Very Low"
    
    def format_recommendation_for_display(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format recommendation for display in the dashboard.
        
        Args:
            recommendation: Raw recommendation dictionary
            
        Returns:
            Formatted recommendation for display
        """
        if not recommendation or 'recommended_contracts' not in recommendation:
            return {
                'status': 'No recommendation available',
                'confidence': 0,
                'direction': 'neutral',
                'contracts': []
            }
        
        confidence = recommendation['overall_confidence']
        direction = recommendation['direction']
        contracts = recommendation['recommended_contracts']
        
        # Format for display
        display_recommendation = {
            'status': 'Recommendation available' if contracts else 'No suitable contracts found',
            'confidence': confidence,
            'confidence_level': self.get_confidence_level_description(confidence),
            'direction': direction,
            'timestamp': recommendation['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'profit_target': f"{recommendation['profit_target_pct']}%",
            'max_hold_time': f"{recommendation['max_hold_time_minutes']} minutes",
            'contracts': []
        }
        
        # Format each contract
        for contract in contracts:
            display_contract = {
                'symbol': contract['symbol'],
                'type': contract['type'],
                'strike': f"${contract['strike']:.2f}",
                'expiration': contract['expiration'],
                'entry_price': f"${contract['entry_price']:.2f}",
                'target_price': f"${contract['target_price']:.2f}",
                'target_profit': f"{contract['target_profit_pct']}%",
                'confidence': f"{contract['confidence']}%",
                'days_to_expiration': contract['days_to_expiration'],
                'greeks': f"Δ:{contract['delta']:.2f} Γ:{contract['gamma']:.4f} Θ:{contract['theta']:.4f} V:{contract['vega']:.4f}",
                'iv': f"{contract['implied_volatility'] * 100:.1f}%"
            }
            display_recommendation['contracts'].append(display_contract)
        
        return display_recommendation

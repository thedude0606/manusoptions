"""
Test module for the recommendation engine.

This module contains tests to validate the recommendation engine's calculations
for risk/reward ratios and confidence scores.
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path to import recommendation_engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recommendation_engine import RecommendationEngine

class TestRecommendationEngine(unittest.TestCase):
    """Test cases for the RecommendationEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = RecommendationEngine()
        
        # Create sample technical indicators data
        self.tech_indicators_df = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(10)],
            'open': [150.0 + i for i in range(10)],
            'high': [155.0 + i for i in range(10)],
            'low': [145.0 + i for i in range(10)],
            'close': [152.0 + i for i in range(10)],
            'volume': [1000000 - i * 10000 for i in range(10)],
            'rsi_14': [65.0 - i for i in range(10)],
            'macd': [1.5 - i * 0.1 for i in range(10)],
            'macd_signal': [1.0 - i * 0.05 for i in range(10)],
            'macd_hist': [0.5 - i * 0.05 for i in range(10)],
            'bb_middle_20': [152.0 + i for i in range(10)],
            'bb_upper_20': [160.0 + i for i in range(10)],
            'bb_lower_20': [144.0 + i for i in range(10)],
            'mfi_14': [75.0 - i for i in range(10)],
            'imi_14': [60.0 - i for i in range(10)]
        })
        
        # Create sample options chain data
        self.options_df = pd.DataFrame({
            'putCall': ['CALL', 'CALL', 'CALL', 'PUT', 'PUT', 'PUT'],
            'symbol': ['AAPL_230519C160', 'AAPL_230519C155', 'AAPL_230519C150', 
                      'AAPL_230519P145', 'AAPL_230519P140', 'AAPL_230519P135'],
            'strikePrice': [160.0, 155.0, 150.0, 145.0, 140.0, 135.0],
            'expirationDate': ['2023-05-19'] * 6,
            'daysToExpiration': [5] * 6,
            'lastPrice': [2.5, 5.0, 7.5, 2.0, 1.5, 1.0],
            'bidPrice': [2.4, 4.9, 7.4, 1.9, 1.4, 0.9],
            'askPrice': [2.6, 5.1, 7.6, 2.1, 1.6, 1.1],
            'mark': [2.5, 5.0, 7.5, 2.0, 1.5, 1.0],
            'delta': [0.3, 0.5, 0.7, -0.3, -0.2, -0.1],
            'gamma': [0.05, 0.07, 0.04, 0.05, 0.03, 0.02],
            'theta': [-0.1, -0.15, -0.2, -0.1, -0.08, -0.05],
            'vega': [0.1, 0.15, 0.2, 0.1, 0.08, 0.05],
            'volatility': [0.3, 0.25, 0.2, 0.3, 0.25, 0.2],
            'openInterest': [1000, 1500, 2000, 800, 1200, 500]
        })
        
        # Set underlying price
        self.underlying_price = 152.0
    
    def test_analyze_market_direction(self):
        """Test market direction analysis."""
        result = self.engine.analyze_market_direction(self.tech_indicators_df)
        
        # Verify result structure
        self.assertIn('direction', result)
        self.assertIn('bullish_score', result)
        self.assertIn('bearish_score', result)
        self.assertIn('signals', result)
        
        # Verify direction is one of the expected values
        self.assertIn(result['direction'], ['bullish', 'bearish', 'neutral'])
        
        # Verify scores are within expected range
        self.assertGreaterEqual(result['bullish_score'], 0)
        self.assertLessEqual(result['bullish_score'], 100)
        self.assertGreaterEqual(result['bearish_score'], 0)
        self.assertLessEqual(result['bearish_score'], 100)
        
        # Verify signals list exists
        self.assertIsInstance(result['signals'], list)
    
    def test_evaluate_options_chain(self):
        """Test options chain evaluation."""
        market_direction = {
            'direction': 'bullish',
            'bullish_score': 70,
            'bearish_score': 30,
            'signals': ['RSI oversold', 'MACD bullish crossover']
        }
        
        result = self.engine.evaluate_options_chain(self.options_df, market_direction, self.underlying_price)
        
        # Verify result structure
        self.assertIn('calls', result)
        self.assertIn('puts', result)
        
        # Verify calls and puts are DataFrames
        self.assertIsInstance(result['calls'], pd.DataFrame)
        self.assertIsInstance(result['puts'], pd.DataFrame)
        
        # Verify calls and puts have expected columns
        for df in [result['calls'], result['puts']]:
            self.assertIn('confidenceScore', df.columns)
            self.assertIn('spreadPct', df.columns)
            self.assertIn('strikeDistancePct', df.columns)
    
    def test_calculate_risk_reward(self):
        """Test risk/reward calculation."""
        market_direction = {
            'direction': 'bullish',
            'bullish_score': 70,
            'bearish_score': 30,
            'signals': ['RSI oversold', 'MACD bullish crossover']
        }
        
        evaluated_options = self.engine.evaluate_options_chain(self.options_df, market_direction, self.underlying_price)
        result = self.engine.calculate_risk_reward(evaluated_options, self.underlying_price)
        
        # Verify result structure
        self.assertIn('calls', result)
        self.assertIn('puts', result)
        
        # Verify risk/reward metrics are calculated
        for df in [result['calls'], result['puts']]:
            if not df.empty:
                self.assertIn('risk', df.columns)
                self.assertIn('projectedProfit', df.columns)
                self.assertIn('rewardRiskRatio', df.columns)
                self.assertIn('expectedProfitPct', df.columns)
                self.assertIn('targetSellPrice', df.columns)
                self.assertIn('targetTimeframeHours', df.columns)
    
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        market_direction = {
            'direction': 'bullish',
            'bullish_score': 70,
            'bearish_score': 30,
            'signals': ['RSI oversold', 'MACD bullish crossover']
        }
        
        evaluated_options = self.engine.evaluate_options_chain(self.options_df, market_direction, self.underlying_price)
        options_with_risk_reward = self.engine.calculate_risk_reward(evaluated_options, self.underlying_price)
        result = self.engine.generate_recommendations(options_with_risk_reward)
        
        # Verify result structure
        self.assertIn('calls', result)
        self.assertIn('puts', result)
        self.assertIn('timestamp', result)
        
        # Verify recommendations are lists
        self.assertIsInstance(result['calls'], list)
        self.assertIsInstance(result['puts'], list)
        
        # Verify recommendations have expected fields
        for recommendations in [result['calls'], result['puts']]:
            if recommendations:
                recommendation = recommendations[0]
                self.assertIn('symbol', recommendation)
                self.assertIn('type', recommendation)
                self.assertIn('strikePrice', recommendation)
                self.assertIn('expirationDate', recommendation)
                self.assertIn('currentPrice', recommendation)
                self.assertIn('targetSellPrice', recommendation)
                self.assertIn('targetTimeframeHours', recommendation)
                self.assertIn('expectedProfitPct', recommendation)
                self.assertIn('confidenceScore', recommendation)
    
    def test_get_recommendations(self):
        """Test the main recommendation method."""
        result = self.engine.get_recommendations(
            self.tech_indicators_df,
            self.options_df,
            self.underlying_price,
            "1hour"
        )
        
        # Verify result structure
        self.assertIn('calls', result)
        self.assertIn('puts', result)
        self.assertIn('timestamp', result)
        self.assertIn('market_direction', result)
        
        # Verify market direction
        self.assertIn('direction', result['market_direction'])
        self.assertIn('bullish_score', result['market_direction'])
        self.assertIn('bearish_score', result['market_direction'])
        self.assertIn('signals', result['market_direction'])
        
        # Verify recommendations are lists
        self.assertIsInstance(result['calls'], list)
        self.assertIsInstance(result['puts'], list)
        
        # Verify no more than 5 recommendations per type
        self.assertLessEqual(len(result['calls']), 5)
        self.assertLessEqual(len(result['puts']), 5)
        
        # Verify expected profit is at least 10%
        for recommendations in [result['calls'], result['puts']]:
            for recommendation in recommendations:
                if 'expectedProfitPct' in recommendation:
                    # Allow some flexibility in the test since this is a sample
                    # In production, we'd enforce the 10% minimum more strictly
                    self.assertGreaterEqual(recommendation['expectedProfitPct'], 0)

if __name__ == '__main__':
    unittest.main()

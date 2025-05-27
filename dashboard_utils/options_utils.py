"""
Utility functions for options data processing and analysis.
This module provides functions for formatting options chain data and calculating implied volatility.
"""

import logging
import pandas as pd
import numpy as np
import math
from scipy.stats import norm

# Import existing functions from other modules
from dashboard_utils.contract_utils import normalize_contract_key
from dashboard_utils.options_chain_utils import split_options_by_type

# Configure logging
logger = logging.getLogger(__name__)

def format_options_chain_data(options_data):
    """
    Format options chain data for display and analysis.
    
    Args:
        options_data (dict): Raw options chain data
        
    Returns:
        pd.DataFrame: Formatted options chain DataFrame
    """
    logger.info("Formatting options chain data")
    
    try:
        if not options_data or not isinstance(options_data, dict):
            logger.warning("Invalid options data provided to format_options_chain_data")
            return pd.DataFrame()
        
        # Extract options list
        options_list = options_data.get("options", [])
        if not options_list:
            logger.warning("No options found in options_data")
            return pd.DataFrame()
        
        # Convert to DataFrame
        options_df = pd.DataFrame(options_list)
        
        # Format price columns
        price_columns = ["lastPrice", "bidPrice", "askPrice", "strikePrice", "markPrice"]
        for col in price_columns:
            if col in options_df.columns:
                options_df[col] = pd.to_numeric(options_df[col], errors='coerce')
        
        # Format date columns
        date_columns = ["expirationDate", "tradeDate", "quoteDate"]
        for col in date_columns:
            if col in options_df.columns:
                options_df[col] = pd.to_datetime(options_df[col], errors='coerce')
        
        # Calculate mid price if bid and ask are available
        if "bidPrice" in options_df.columns and "askPrice" in options_df.columns:
            options_df["midPrice"] = (options_df["bidPrice"] + options_df["askPrice"]) / 2
        
        # Add normalized symbol for consistent matching
        if "symbol" in options_df.columns:
            options_df["normalized_symbol"] = options_df["symbol"].apply(normalize_contract_key)
        
        logger.info(f"Formatted options chain with {len(options_df)} contracts")
        return options_df
        
    except Exception as e:
        logger.error(f"Error formatting options chain data: {e}", exc_info=True)
        return pd.DataFrame()

def calculate_implied_volatility(options_df, underlying_price, risk_free_rate=0.05):
    """
    Calculate implied volatility for options using the Black-Scholes model.
    
    Args:
        options_df (pd.DataFrame): Options chain DataFrame
        underlying_price (float): Current price of the underlying asset
        risk_free_rate (float, optional): Risk-free interest rate. Defaults to 0.05.
        
    Returns:
        pd.DataFrame: DataFrame with implied volatility calculations
    """
    logger.info("Calculating implied volatility")
    
    try:
        if options_df is None or options_df.empty:
            logger.warning("Empty DataFrame provided to calculate_implied_volatility")
            return pd.DataFrame()
        
        # Make a copy to avoid modifying the original
        df = options_df.copy()
        
        # Ensure required columns exist
        required_columns = ["putCall", "strikePrice", "expirationDate", "lastPrice"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Missing required columns for IV calculation: {missing_columns}")
            return df
        
        # Convert expiration date to time to expiry in years
        if "expirationDate" in df.columns:
            try:
                # Ensure expirationDate is datetime
                if not pd.api.types.is_datetime64_any_dtype(df["expirationDate"]):
                    df["expirationDate"] = pd.to_datetime(df["expirationDate"], errors='coerce')
                
                # Calculate time to expiry in years
                current_date = pd.Timestamp.now()
                df["timeToExpiry"] = (df["expirationDate"] - current_date).dt.total_seconds() / (365.25 * 24 * 60 * 60)
                
                # Filter out expired options
                df = df[df["timeToExpiry"] > 0]
            except Exception as e:
                logger.error(f"Error calculating time to expiry: {e}")
                df["timeToExpiry"] = 0.1  # Default fallback
        
        # Initialize implied volatility column
        df["impliedVolatility"] = np.nan
        
        # Calculate IV for each option
        for idx, row in df.iterrows():
            try:
                # Skip if missing data
                if pd.isna(row["lastPrice"]) or pd.isna(row["strikePrice"]) or pd.isna(row["timeToExpiry"]):
                    continue
                
                # Extract option parameters
                S = underlying_price  # Current stock price
                K = row["strikePrice"]  # Strike price
                T = row["timeToExpiry"]  # Time to expiry in years
                r = risk_free_rate  # Risk-free rate
                option_price = row["lastPrice"]  # Option price
                option_type = row["putCall"]  # Option type (CALL or PUT)
                
                # Skip if time to expiry is too small
                if T < 0.01:
                    continue
                
                # Calculate implied volatility using binary search
                iv = _binary_search_iv(option_price, S, K, T, r, option_type)
                df.at[idx, "impliedVolatility"] = iv
                
            except Exception as e:
                logger.warning(f"Error calculating IV for option {row.get('symbol', 'unknown')}: {e}")
        
        # Convert IV to percentage
        df["impliedVolatilityPercent"] = df["impliedVolatility"] * 100
        
        logger.info(f"Calculated implied volatility for {df['impliedVolatility'].notna().sum()} options")
        return df
        
    except Exception as e:
        logger.error(f"Error in calculate_implied_volatility: {e}", exc_info=True)
        return options_df

def _binary_search_iv(option_price, S, K, T, r, option_type, precision=0.0001, max_iterations=100):
    """
    Helper function to calculate implied volatility using binary search.
    
    Args:
        option_price (float): Market price of the option
        S (float): Current stock price
        K (float): Strike price
        T (float): Time to expiry in years
        r (float): Risk-free rate
        option_type (str): Option type ('CALL' or 'PUT')
        precision (float, optional): Desired precision. Defaults to 0.0001.
        max_iterations (int, optional): Maximum iterations. Defaults to 100.
        
    Returns:
        float: Implied volatility
    """
    # Set initial bounds
    low = 0.001
    high = 5.0  # 500% volatility as upper bound
    
    # Check if option price is valid
    if option_price <= 0:
        return np.nan
    
    # Binary search
    for i in range(max_iterations):
        mid = (low + high) / 2
        price = _black_scholes(S, K, T, r, mid, option_type)
        
        if abs(price - option_price) < precision:
            return mid
        
        if price > option_price:
            high = mid
        else:
            low = mid
    
    # Return the midpoint if max iterations reached
    return (low + high) / 2

def _black_scholes(S, K, T, r, sigma, option_type):
    """
    Calculate option price using Black-Scholes formula.
    
    Args:
        S (float): Current stock price
        K (float): Strike price
        T (float): Time to expiry in years
        r (float): Risk-free rate
        sigma (float): Volatility
        option_type (str): Option type ('CALL' or 'PUT')
        
    Returns:
        float: Option price
    """
    # Handle edge cases
    if sigma <= 0 or T <= 0:
        return 0
    
    # Calculate d1 and d2
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Calculate option price based on type
    if option_type == "CALL":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:  # PUT
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price

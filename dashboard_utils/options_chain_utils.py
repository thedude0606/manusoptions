"""
Utility functions for handling options chain data in the dashboard application.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)

def process_options_chain_data(options_data):
    """
    Process options chain data for display in the dashboard.
    
    Args:
        options_data (dict): Raw options chain data from the API
        
    Returns:
        tuple: (processed_options_df, expiration_dates, underlying_price)
    """
    if not options_data:
        logger.warning("No options data provided to process_options_chain_data")
        return pd.DataFrame(), [], 0
    
    # Extract options and create DataFrame
    options = options_data.get("options", [])
    if not options:
        logger.warning("No options found in options_data")
        return pd.DataFrame(), [], 0
    
    # Convert to DataFrame
    options_df = pd.DataFrame(options)
    
    # Extract expiration dates
    expiration_dates = []
    if "expirationDate" in options_df.columns:
        expiration_dates = sorted(options_df["expirationDate"].unique().tolist())
    
    # Extract underlying price
    underlying_price = options_data.get("underlyingPrice", 0)
    
    # Ensure required columns exist
    required_columns = ["putCall", "strikePrice", "expirationDate", "symbol"]
    for col in required_columns:
        if col not in options_df.columns:
            logger.warning(f"Required column '{col}' not found in options data")
            options_df[col] = None
    
    # Ensure price columns exist
    price_columns = ["lastPrice", "bidPrice", "askPrice"]
    for col in price_columns:
        if col not in options_df.columns:
            logger.warning(f"Price column '{col}' not found in options data")
            options_df[col] = None
    
    # Log summary of processed data
    logger.info(f"Processed options chain with {len(options_df)} contracts across {len(expiration_dates)} expiration dates")
    
    return options_df, expiration_dates, underlying_price

def split_options_by_type(options_df, expiration_date=None, option_type=None):
    """
    Split options DataFrame into calls and puts, with optional filtering.
    
    Args:
        options_df (DataFrame): Options chain DataFrame
        expiration_date (str, optional): Filter by expiration date
        option_type (str, optional): Filter by option type ('CALL', 'PUT', or 'BOTH')
        
    Returns:
        tuple: (calls_data, puts_data)
    """
    if options_df.empty:
        logger.warning("Empty options DataFrame provided to split_options_by_type")
        return [], []
    
    # Filter by expiration date if provided
    if expiration_date and "expirationDate" in options_df.columns:
        options_df = options_df[options_df["expirationDate"] == expiration_date]
    
    # Split into calls and puts
    if "putCall" in options_df.columns:
        calls_df = options_df[options_df["putCall"] == "CALL"]
        puts_df = options_df[options_df["putCall"] == "PUT"]
    else:
        # If putCall column is missing, try to infer from symbol
        if "symbol" in options_df.columns:
            options_df["putCall"] = options_df["symbol"].apply(
                lambda x: "CALL" if "C" in str(x).upper() else ("PUT" if "P" in str(x).upper() else "UNKNOWN")
            )
            calls_df = options_df[options_df["putCall"] == "CALL"]
            puts_df = options_df[options_df["putCall"] == "PUT"]
        else:
            # Can't determine option type
            logger.error("Cannot determine option type - missing both 'putCall' and 'symbol' columns")
            return [], []
    
    # Sort by strike price
    if "strikePrice" in calls_df.columns:
        calls_df = calls_df.sort_values(by="strikePrice")
    
    if "strikePrice" in puts_df.columns:
        puts_df = puts_df.sort_values(by="strikePrice")
    
    # Filter by option type if "BOTH" is not selected
    if option_type == "CALL":
        puts_df = pd.DataFrame()  # Empty DataFrame for puts
    elif option_type == "PUT":
        calls_df = pd.DataFrame()  # Empty DataFrame for calls
    
    # Convert to records for Dash table
    calls_data = calls_df.to_dict("records") if not calls_df.empty else []
    puts_data = puts_df.to_dict("records") if not puts_df.empty else []
    
    logger.info(f"Split options into {len(calls_data)} calls and {len(puts_data)} puts")
    
    return calls_data, puts_data

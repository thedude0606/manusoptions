"""
Utility functions for handling options chain data in the dashboard application.
"""

import pandas as pd
import logging
import json
import time

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

def ensure_putcall_field(options_df):
    """
    Enhanced version of ensure_putcall_field with better error handling and logging.
    
    Args:
        options_df (DataFrame): Options chain DataFrame
        
    Returns:
        DataFrame: Updated options DataFrame with putCall field
    """
    if options_df is None:
        logger.warning("ensure_putcall_field received None instead of DataFrame")
        return pd.DataFrame()
        
    if options_df.empty:
        logger.debug("ensure_putcall_field received empty DataFrame")
        return options_df
    
    # Make a copy to avoid modifying the original
    options_df = options_df.copy()
    
    # Log the columns for debugging
    logger.debug(f"DataFrame columns before putCall processing: {options_df.columns.tolist()}")
    
    # If putCall already exists and has no missing values, return as is
    if "putCall" in options_df.columns and not options_df["putCall"].isna().any():
        logger.debug("putCall field already exists and is complete")
        return options_df
    
    # If contractType exists (from streaming data), map it to putCall
    if "contractType" in options_df.columns:
        logger.info("Mapping contractType to putCall for streaming data")
        # Create or update putCall column based on contractType
        options_df["putCall"] = options_df["contractType"].apply(
            lambda x: "CALL" if x == "C" else ("PUT" if x == "P" else None)
        )
    # If symbol exists but putCall is missing, infer from symbol
    elif "symbol" in options_df.columns:
        logger.info("Inferring putCall from symbol")
        options_df["putCall"] = options_df["symbol"].apply(
            lambda x: "CALL" if "C" in str(x).upper() else ("PUT" if "P" in str(x).upper() else None)
        )
    
    # Log how many calls and puts we identified
    if "putCall" in options_df.columns:
        call_count = (options_df["putCall"] == "CALL").sum()
        put_count = (options_df["putCall"] == "PUT").sum()
        logger.info(f"Identified {call_count} calls and {put_count} puts")
    else:
        logger.warning("Failed to create putCall field")
    
    return options_df

def split_options_by_type(options_df, expiration_date=None, option_type=None, last_valid_options=None):
    """
    Enhanced version of split_options_by_type with better error handling and state preservation.
    
    Args:
        options_df (DataFrame): Options chain DataFrame
        expiration_date (str, optional): Filter by expiration date
        option_type (str, optional): Filter by option type ('CALL', 'PUT', or 'ALL')
        last_valid_options (dict, optional): Last valid options data for fallback
        
    Returns:
        tuple: (calls_data, puts_data)
    """
    # Start timing for performance monitoring
    start_time = time.time()
    
    # Check if we have valid data
    if options_df is None or options_df.empty:
        logger.warning("Empty or None options DataFrame provided to split_options_by_type")
        
        # Try to use last valid options as fallback
        if last_valid_options and isinstance(last_valid_options, dict) and "options" in last_valid_options:
            logger.info("Using last_valid_options as fallback")
            try:
                options_df = pd.DataFrame(last_valid_options["options"])
            except Exception as e:
                logger.error(f"Error creating DataFrame from last_valid_options: {e}")
                return [], []
        else:
            logger.warning("No fallback data available")
            return [], []
    
    # Log the shape and a sample of the data
    logger.debug(f"Options DataFrame shape: {options_df.shape}")
    if not options_df.empty:
        logger.debug(f"Sample columns: {options_df.columns[:10].tolist()}")
        if len(options_df) > 0:
            logger.debug(f"First row sample: {options_df.iloc[0].to_dict()}")
    
    # Ensure putCall field is properly set using the enhanced function
    options_df = ensure_putcall_field(options_df)
    
    # Filter by expiration date if provided
    if expiration_date and "expirationDate" in options_df.columns:
        filtered_df = options_df[options_df["expirationDate"] == expiration_date]
        # If filtering results in empty DataFrame, log warning and use original
        if filtered_df.empty:
            logger.warning(f"No options found for expiration date {expiration_date}")
            # Continue with unfiltered data
        else:
            options_df = filtered_df
            logger.debug(f"Filtered to {len(options_df)} options for expiration date {expiration_date}")
    
    # Split into calls and puts
    if "putCall" in options_df.columns:
        calls_df = options_df[options_df["putCall"] == "CALL"]
        puts_df = options_df[options_df["putCall"] == "PUT"]
        
        # Log counts for debugging
        logger.info(f"After splitting: {len(calls_df)} calls and {len(puts_df)} puts")
    else:
        # Can't determine option type
        logger.error("Cannot determine option type - missing putCall column and failed to infer it")
        return [], []
    
    # Sort by strike price
    if "strikePrice" in calls_df.columns:
        calls_df = calls_df.sort_values(by="strikePrice")
    
    if "strikePrice" in puts_df.columns:
        puts_df = puts_df.sort_values(by="strikePrice")
    
    # Filter by option type if not "ALL"
    if option_type == "CALL":
        puts_df = pd.DataFrame()  # Empty DataFrame for puts
        logger.debug("Filtered to show only CALL options")
    elif option_type == "PUT":
        calls_df = pd.DataFrame()  # Empty DataFrame for calls
        logger.debug("Filtered to show only PUT options")
    
    # Convert to records for Dash table, handling complex fields
    calls_data = prepare_options_for_dash_table(calls_df) if not calls_df.empty else []
    puts_data = prepare_options_for_dash_table(puts_df) if not puts_df.empty else []
    
    # Log performance metrics
    elapsed_time = time.time() - start_time
    logger.info(f"Split options in {elapsed_time:.3f} seconds: {len(calls_data)} calls and {len(puts_data)} puts")
    
    return calls_data, puts_data

def prepare_options_for_dash_table(options_df):
    """
    Enhanced version of prepare_options_for_dash_table with better error handling.
    
    Args:
        options_df (DataFrame): Options DataFrame
        
    Returns:
        list: List of dictionaries with properly formatted data for Dash DataTable
    """
    if options_df is None or options_df.empty:
        return []
    
    try:
        # Convert DataFrame to records
        records = options_df.to_dict("records")
        
        # Process each record to handle complex fields
        for record in records:
            # Handle optionDeliverablesList - convert to string or remove
            if "optionDeliverablesList" in record:
                if record["optionDeliverablesList"] is None:
                    # If None, keep as is
                    pass
                elif isinstance(record["optionDeliverablesList"], (list, dict)):
                    # Convert complex objects to string representation
                    try:
                        record["optionDeliverablesList"] = json.dumps(record["optionDeliverablesList"])
                    except:
                        # If conversion fails, set to a descriptive string
                        record["optionDeliverablesList"] = str(record["optionDeliverablesList"])
                else:
                    # Ensure it's a string, number, or boolean
                    record["optionDeliverablesList"] = str(record["optionDeliverablesList"])
            
            # Check for other complex fields that might cause issues
            for key, value in list(record.items()):
                if not isinstance(value, (str, int, float, bool, type(None))):
                    # Convert complex objects to string representation
                    try:
                        record[key] = json.dumps(value)
                    except:
                        record[key] = str(value)
        
        return records
    except Exception as e:
        logger.error(f"Error preparing options for Dash table: {e}")
        return []

# dashboard_utils/data_fetchers.py
import schwabdev
import os
import datetime
import json
import pandas as pd
import logging
import time # For adding delays between API calls
import math # For ceiling function
from dotenv import load_dotenv
import re # For contract key formatting
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
TOKENS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tokens.json")

# Define log_file variable at module level to ensure it's always available
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"data_fetchers_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Configure basic logging for this module with both console and file handlers
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    # Console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
logger.setLevel(logging.INFO)
logger.info(f"Data fetchers logger initialized. Logging to console and file: {log_file}")

def get_schwab_client():
    """Helper to initialize and return a Schwab client if tokens exist."""
    app_key = os.getenv("APP_KEY")
    app_secret = os.getenv("APP_SECRET")
    callback_url = os.getenv("CALLBACK_URL")
    if not all([app_key, app_secret, callback_url]):
        return None, "Error: APP_KEY, APP_SECRET, or CALLBACK_URL not found in environment variables."
    if not os.path.exists(TOKENS_FILE):
        return None, f"Error: Tokens file not found at {TOKENS_FILE}. Please run authentication."
    
    try:
        client = schwabdev.Client(app_key, app_secret, callback_url, tokens_file=TOKENS_FILE, capture_callback=False)
        # Verify authentication by checking for access token
        if not (client.tokens and client.tokens.access_token):
            return None, "Error: No valid access token found. Please re-authenticate."
        
        logger.info("Schwab client initialized successfully.")
        return client, None
    except Exception as e:
        logger.error(f"Error initializing Schwab client: {e}", exc_info=True)
        return None, f"Error initializing Schwab client: {str(e)}"

def get_minute_data(client: schwabdev.Client, symbol: str, days_history: int = 1, since_timestamp=None):
    """
    Fetches 1-minute historical price data for the given symbol.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to fetch data for
        days_history: Number of days of history to fetch (used if since_timestamp is None)
        since_timestamp: If provided, only fetch data since this timestamp
        
    Returns:
        DataFrame with minute data, error message (if any)
    """
    if not client:
        return pd.DataFrame(), "Schwab client not initialized for get_minute_data."
    
    if since_timestamp:
        logger.info(f"Fetching minute data for {symbol} since {since_timestamp}.")
    else:
        logger.info(f"Fetching {days_history} days of minute data for {symbol}.")
    all_candles_df = pd.DataFrame()
    
    # Schwab API limits minute data to 10 days per call for periodType="day"
    # We will fetch in chunks of `max_days_per_call`.
    max_days_per_call = 10 
    api_call_delay_seconds = 1 # Delay between API calls to be respectful
    current_end_date = datetime.datetime.now()
    # Ensure we don't request future data if current_end_date is slightly ahead due to execution time
    current_end_date = min(current_end_date, datetime.datetime.now())
    
    # If we have a since_timestamp, use that instead of days_history for start date
    if since_timestamp:
        # Convert since_timestamp to datetime if it's a string
        if isinstance(since_timestamp, str):
            try:
                since_timestamp = pd.to_datetime(since_timestamp)
            except Exception as e:
                logger.error(f"Error converting since_timestamp to datetime: {e}")
                since_timestamp = None
                
        # If conversion successful, use it as the start date
        if since_timestamp is not None:
            # Add a small buffer to avoid missing data (e.g., 5 minutes)
            buffer_minutes = 5
            start_date = since_timestamp - datetime.timedelta(minutes=buffer_minutes)
            # Calculate days_history based on the difference between now and since_timestamp
            days_diff = (current_end_date - start_date).total_seconds() / (24 * 60 * 60)
            days_history = max(1, min(90, math.ceil(days_diff)))  # Ensure between 1 and 90 days
            logger.info(f"Calculated {days_history} days of history based on since_timestamp {since_timestamp}")
        else:
            # If conversion failed, fall back to days_history
            start_date = current_end_date - datetime.timedelta(days=days_history)
            logger.info(f"Using default days_history ({days_history}) due to since_timestamp conversion failure")
    else:
        # No since_timestamp provided, use days_history
        start_date = current_end_date - datetime.timedelta(days=days_history)
        logger.info(f"Using default days_history ({days_history})")
    
    # Limit to 90 days maximum (Schwab API limitation)
    days_history = min(days_history, 90)
    
    # Calculate number of chunks needed
    num_chunks = math.ceil(days_history / max_days_per_call)
    logger.info(f"Fetching {days_history} days of data in {num_chunks} chunks of {max_days_per_call} days each")
    
    # Fetch data in chunks
    chunk_end_date = current_end_date
    for chunk in range(num_chunks):
        # Calculate chunk start date (limited by max_days_per_call)
        days_in_chunk = min(max_days_per_call, days_history - (chunk * max_days_per_call))
        chunk_start_date = chunk_end_date - datetime.timedelta(days=days_in_chunk)
        
        # Ensure we don't go before the overall start_date
        chunk_start_date = max(chunk_start_date, start_date)
        
        # Skip this chunk if start date is after end date (shouldn't happen, but just in case)
        if chunk_start_date >= chunk_end_date:
            logger.warning(f"Skipping chunk {chunk+1}/{num_chunks} because start date {chunk_start_date} is not before end date {chunk_end_date}")
            continue
        
        logger.info(f"Fetching chunk {chunk+1}/{num_chunks}: {chunk_start_date.strftime('%Y-%m-%d')} to {chunk_end_date.strftime('%Y-%m-%d')}")
        
        try:
            response = client.price_history(
                symbol=symbol,
                frequencyType="minute",
                frequency=1,
                startDate=chunk_start_date,
                endDate=chunk_end_date,
                needExtendedHoursData=False
            )
            
            if response.ok:
                price_data = response.json()
                
                if price_data.get("candles"):
                    candles = price_data["candles"]
                    logger.info(f"Received {len(candles)} candles for chunk {chunk+1}/{num_chunks}")
                    
                    # Convert to DataFrame
                    chunk_df = pd.DataFrame(candles)
                    
                    # Convert datetime column
                    if "datetime" in chunk_df.columns:
                        # Convert milliseconds to datetime
                        chunk_df["timestamp"] = pd.to_datetime(chunk_df["datetime"], unit="ms")
                        chunk_df.drop("datetime", axis=1, inplace=True)
                    
                    # Append to all_candles_df
                    all_candles_df = pd.concat([all_candles_df, chunk_df], ignore_index=True)
                elif price_data.get("empty") == True:
                    logger.warning(f"No data returned for chunk {chunk+1}/{num_chunks} (API returned empty=True)")
                else:
                    logger.warning(f"Unexpected response format for chunk {chunk+1}/{num_chunks}")
            else:
                logger.error(f"Error fetching price data for chunk {chunk+1}/{num_chunks}: {response.status_code} - {response.text}")
                return all_candles_df, f"API error: {response.status_code} - {response.text}"
        
        except Exception as e:
            logger.error(f"Exception during price history fetch for chunk {chunk+1}/{num_chunks}: {e}", exc_info=True)
            return all_candles_df, f"Exception during fetch: {str(e)}"
        
        # Update chunk_end_date for next iteration
        chunk_end_date = chunk_start_date
        
        # Add delay between API calls
        if chunk < num_chunks - 1:  # Don't delay after the last chunk
            time.sleep(api_call_delay_seconds)
    
    # Process the combined data
    if not all_candles_df.empty:
        # Remove duplicates
        all_candles_df.drop_duplicates(subset=["timestamp"], inplace=True)
        
        # Sort by timestamp
        all_candles_df.sort_values(by="timestamp", ascending=False, inplace=True)
        
        # Filter by since_timestamp if provided
        if since_timestamp is not None:
            # Keep only rows with timestamp >= since_timestamp
            all_candles_df = all_candles_df[all_candles_df["timestamp"] >= since_timestamp]
            logger.info(f"Filtered to {len(all_candles_df)} rows with timestamp >= {since_timestamp}")
        
        logger.info(f"Successfully fetched and processed {len(all_candles_df)} minute data rows for {symbol}")
        
        # Log date range of the data
        if not all_candles_df.empty:
            min_date = all_candles_df["timestamp"].min()
            max_date = all_candles_df["timestamp"].max()
            logger.info(f"Data ranges from {min_date} to {max_date}")
    else:
        logger.warning(f"No minute data returned for {symbol}")
    
    return all_candles_df, None

def get_options_chain_data(client: schwabdev.Client, symbol: str):
    """
    Fetches options chain data for the given symbol.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to fetch options for
        
    Returns:
        DataFrame with options data, list of expiration dates, error message (if any)
    """
    if not client:
        return pd.DataFrame(), [], "Schwab client not initialized for get_options_chain_data."
    
    try:
        logger.info(f"Fetching options chain for {symbol}")
        response = client.option_chains(
            symbol=symbol.upper(),
            contractType="ALL",
            includeUnderlyingQuote=True,
            expMonth="ALL",
            optionType="ALL"
        )
        
        if not response.ok:
            return pd.DataFrame(), [], f"Error fetching option chains: {response.status_code} - {response.text}"
        
        options_data = response.json()
        
        if options_data.get("status") == "FAILED":
            return pd.DataFrame(), [], f"Failed to fetch option chains: {options_data.get('error', 'Unknown API error')}"
        
        # Extract expiration dates
        expiration_dates = []
        all_options = []
        
        # Process call options
        if "callExpDateMap" in options_data and options_data["callExpDateMap"]:
            for date_str, strikes in options_data["callExpDateMap"].items():
                # Extract date from format like "2023-06-16:2"
                exp_date = date_str.split(":")[0]
                if exp_date not in expiration_dates:
                    expiration_dates.append(exp_date)
                
                # Process each strike price
                for strike_price, contracts in strikes.items():
                    for contract in contracts:
                        contract["putCall"] = "CALL"
                        contract["expirationDate"] = exp_date
                        contract["strikePrice"] = float(strike_price)
                        
                        # Ensure last, bid, and ask fields are always present
                        if "lastPrice" not in contract or contract["lastPrice"] is None:
                            contract["lastPrice"] = 0.0
                            logger.debug(f"Added default lastPrice for {contract.get('symbol', 'unknown')}")
                        
                        if "bidPrice" not in contract or contract["bidPrice"] is None:
                            contract["bidPrice"] = 0.0
                            logger.debug(f"Added default bidPrice for {contract.get('symbol', 'unknown')}")
                        
                        if "askPrice" not in contract or contract["askPrice"] is None:
                            contract["askPrice"] = 0.0
                            logger.debug(f"Added default askPrice for {contract.get('symbol', 'unknown')}")
                        
                        all_options.append(contract)
        
        # Process put options
        if "putExpDateMap" in options_data and options_data["putExpDateMap"]:
            for date_str, strikes in options_data["putExpDateMap"].items():
                # Extract date from format like "2023-06-16:2"
                exp_date = date_str.split(":")[0]
                if exp_date not in expiration_dates:
                    expiration_dates.append(exp_date)
                
                # Process each strike price
                for strike_price, contracts in strikes.items():
                    for contract in contracts:
                        contract["putCall"] = "PUT"
                        contract["expirationDate"] = exp_date
                        contract["strikePrice"] = float(strike_price)
                        
                        # Ensure last, bid, and ask fields are always present
                        if "lastPrice" not in contract or contract["lastPrice"] is None:
                            contract["lastPrice"] = 0.0
                            logger.debug(f"Added default lastPrice for {contract.get('symbol', 'unknown')}")
                        
                        if "bidPrice" not in contract or contract["bidPrice"] is None:
                            contract["bidPrice"] = 0.0
                            logger.debug(f"Added default bidPrice for {contract.get('symbol', 'unknown')}")
                        
                        if "askPrice" not in contract or contract["askPrice"] is None:
                            contract["askPrice"] = 0.0
                            logger.debug(f"Added default askPrice for {contract.get('symbol', 'unknown')}")
                        
                        all_options.append(contract)
        
        # Convert to DataFrame
        if all_options:
            options_df = pd.DataFrame(all_options)
            
            # Log a sample of the data to verify fields
            if not options_df.empty:
                sample_row = options_df.iloc[0]
                logger.info(f"Sample option data - Symbol: {sample_row.get('symbol')}, Last: {sample_row.get('lastPrice')}, Bid: {sample_row.get('bidPrice')}, Ask: {sample_row.get('askPrice')}")
            
            logger.info(f"Successfully fetched options chain for {symbol} with {len(options_df)} contracts across {len(expiration_dates)} expiration dates")
            return options_df, expiration_dates, None
        else:
            logger.warning(f"No options data returned for {symbol}")
            return pd.DataFrame(), [], None
    
    except Exception as e:
        logger.error(f"Error in get_options_chain_data for {symbol}: {e}", exc_info=True)
        return pd.DataFrame(), [], f"An error occurred while fetching options chain data for {symbol}: {str(e)}"

def format_contract_key_for_streaming(contract_key):
    """
    Formats an option contract key for streaming compatibility.
    
    Args:
        contract_key: Option contract key/symbol from the Schwab API
        
    Returns:
        Formatted contract key for streaming
    """
    try:
        if not contract_key:
            return contract_key
        
        # Extract components from the Schwab API format
        # Example: AAPL_240621C190
        pattern = r'([A-Z]+)_(\d{6})([CP])(\d+(?:\.\d+)?)'
        match = re.match(pattern, contract_key)
        
        if not match:
            # Try alternative pattern for Schwab's standard format
            # Example: AAPL240621C00190000
            alt_pattern = r'([A-Z]+)(\d{6})([CP])(\d{8})'
            match = re.match(alt_pattern, contract_key)
            
            if not match:
                logger.warning(f"Could not parse contract key: {contract_key}, using as-is")
                return contract_key
        
        symbol, exp_date, cp_flag, strike = match.groups()
        
        # Format strike price (multiply by 1000 if needed and pad with leading zeros)
        strike_float = float(strike)
        strike_int = int(strike_float * 1000) if strike_float < 1000 else int(strike_float)
        strike_padded = f"{strike_int:08d}"
        
        # Format symbol (pad with spaces to 6 chars)
        symbol_padded = f"{symbol:<6}"
        
        # Combine all parts
        formatted_key = f"{symbol_padded}{exp_date}{cp_flag}{strike_padded}"
        logger.debug(f"Formatted contract key: {contract_key} -> {formatted_key}")
        
        return formatted_key
    except Exception as e:
        logger.error(f"Error formatting contract key {contract_key}: {e}", exc_info=True)
        return contract_key

def get_option_contract_keys(client: schwabdev.Client, symbol: str):
    """Fetches option contract keys (symbols) for the given underlying symbol, filtered by OI > 0."""
    if not client:
        return set(), "Schwab client not initialized for get_option_contract_keys."
    
    contract_keys = set()
    try:
        response = client.option_chains(
            symbol=symbol.upper(),
            contractType="ALL",
            includeUnderlyingQuote=False,
            expMonth="ALL",
            optionType="ALL"
        )
        
        if not response.ok:
            return set(), f"Error fetching option chains: {response.status_code} - {response.text}"
        
        options_data = response.json()
        
        # Process call options
        if "callExpDateMap" in options_data and options_data["callExpDateMap"]:
            for date_str, strikes in options_data["callExpDateMap"].items():
                for strike_price, contracts in strikes.items():
                    for contract in contracts:
                        # Only include contracts with open interest > 0
                        if contract.get("openInterest", 0) > 0:
                            contract_keys.add(contract.get("symbol"))
        
        # Process put options
        if "putExpDateMap" in options_data and options_data["putExpDateMap"]:
            for date_str, strikes in options_data["putExpDateMap"].items():
                for strike_price, contracts in strikes.items():
                    for contract in contracts:
                        # Only include contracts with open interest > 0
                        if contract.get("openInterest", 0) > 0:
                            contract_keys.add(contract.get("symbol"))
        
        logger.info(f"Found {len(contract_keys)} option contracts with OI > 0 for {symbol}")
        return contract_keys, None
    
    except Exception as e:
        logger.error(f"Error in get_option_contract_keys for {symbol}: {e}", exc_info=True)
        return set(), f"An error occurred while fetching option contract keys for {symbol}: {str(e)}"

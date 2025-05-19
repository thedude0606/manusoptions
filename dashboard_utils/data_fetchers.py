# dashboard_utils/data_fetchers.py

import schwabdev
import os
import datetime
import json
import pandas as pd
import logging
import time # For adding delays between API calls
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
TOKENS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tokens.json")

# Configure basic logging for this module with both console and file handlers
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    # Console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # File handler
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"data_fetchers_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
        if not (client.tokens and client.tokens.access_token):
            error_msg = "Error: No valid access token in loaded tokens.json."
            if client.tokens and client.tokens.refresh_token:
                logger.info("Attempting to refresh token...")
                try:
                    client.tokens.update_tokens_from_refresh_token()
                    if client.tokens and client.tokens.access_token:
                        logger.info("Token refreshed successfully.")
                        return client, None
                    else:
                        return None, error_msg + " Token refresh failed."
                except Exception as refresh_e:
                    return None, error_msg + f" Token refresh attempt failed: {str(refresh_e)}"
            else:
                return None, error_msg + " No refresh token available."
        return client, None
    except Exception as e:
        return None, f"Error initializing Schwab client: {str(e)}"

def get_minute_data(client: schwabdev.Client, symbol: str, days_history: int = 1):
    """Fetches 1-minute historical price data for the given symbol for the specified number of past days."""
    if not client:
        return pd.DataFrame(), "Schwab client not initialized for get_minute_data."
    
    logger.info(f"Fetching {days_history} days of minute data for {symbol}.")
    all_candles_df = pd.DataFrame()
    
    # Schwab API limits minute data to 10 days per call for periodType="day"
    # We will fetch in chunks of `max_days_per_call`.
    max_days_per_call = 10 
    api_call_delay_seconds = 1 # Delay between API calls to be respectful

    current_end_date = datetime.datetime.now()
    # Ensure we don't request future data if current_end_date is slightly ahead due to execution time
    current_end_date = min(current_end_date, datetime.datetime.now())

    # Iterate backwards in chunks
    for i in range(0, days_history, max_days_per_call):
        days_to_go_back_for_this_chunk_end = i
        days_to_go_back_for_this_chunk_start = min(i + max_days_per_call, days_history)

        # Calculate chunk_end_date and chunk_start_date for this iteration
        # Iterating backwards: the "end" of our current chunk is further in the past than its "start"
        chunk_end_date_dt = current_end_date - datetime.timedelta(days=days_to_go_back_for_this_chunk_end)
        chunk_start_date_dt = current_end_date - datetime.timedelta(days=days_to_go_back_for_this_chunk_start)
        
        # Ensure start date is not after end date (can happen for the last partial chunk if days_history is not a multiple of max_days_per_call)
        if chunk_start_date_dt >= chunk_end_date_dt:
            if days_history == days_to_go_back_for_this_chunk_start: # Exact multiple, last chunk is full
                 chunk_start_date_dt = current_end_date - datetime.timedelta(days=days_history)
            else: # Partial last chunk, start date should be overall start
                 chunk_start_date_dt = current_end_date - datetime.timedelta(days=days_history)
                 if chunk_start_date_dt >= chunk_end_date_dt: # if days_history < max_days_per_call
                    chunk_end_date_dt = current_end_date # ensure end date is current for single small chunk

        # Adjust if chunk_start_date_dt is before the actual overall start date we need
        overall_start_date_limit = current_end_date - datetime.timedelta(days=days_history)
        chunk_start_date_dt = max(chunk_start_date_dt, overall_start_date_limit)

        # If the calculated chunk_start_date_dt is now same or after chunk_end_date_dt, means we've covered enough
        if chunk_start_date_dt >= chunk_end_date_dt and i > 0: # i > 0 to ensure first chunk is always attempted
            logger.info(f"Chunk {i // max_days_per_call + 1}: Start date {chunk_start_date_dt.strftime('%Y-%m-%d')} is on or after end date {chunk_end_date_dt.strftime('%Y-%m-%d')}. Assuming all required data fetched.")
            break

        logger.info(f"Chunk {i // max_days_per_call + 1}: Fetching from {chunk_start_date_dt.strftime('%Y-%m-%d')} to {chunk_end_date_dt.strftime('%Y-%m-%d')}")

        try:
            response = client.price_history(
                symbol=symbol.upper(),
                frequencyType="minute",
                frequency=1,
                startDate=chunk_start_date_dt, 
                endDate=chunk_end_date_dt,
                needExtendedHoursData=True
            )

            if response.ok:
                price_data = response.json()
                if price_data.get("candles"):
                    chunk_df = pd.DataFrame(price_data["candles"])
                    all_candles_df = pd.concat([all_candles_df, chunk_df], ignore_index=True)
                    logger.info(f"Chunk {i // max_days_per_call + 1}: Fetched {len(chunk_df)} candles.")
                elif price_data.get("empty") == True:
                    logger.info(f"Chunk {i // max_days_per_call + 1}: No minute data returned (API response empty) for period.")
                else:
                    logger.warning(f"Chunk {i // max_days_per_call + 1}: Unexpected response format: {price_data}")
            else:
                error_text = response.text
                logger.error(f"Chunk {i // max_days_per_call + 1}: Error fetching minute data: {response.status_code} - {error_text}")
                # If one chunk fails, we might want to stop or continue. For now, log and continue.
                # return pd.DataFrame(), f"Error fetching minute data for {symbol} (chunk {i // max_days_per_call + 1}): {response.status_code} - {error_text}"
        except Exception as e:
            logger.error(f"Chunk {i // max_days_per_call + 1}: An error occurred: {str(e)}", exc_info=True)
            # return pd.DataFrame(), f"An error occurred while fetching minute data for {symbol} (chunk {i // max_days_per_call + 1}): {str(e)}"
        
        # Delay before next API call if not the last chunk
        if (i + max_days_per_call) < days_history:
            logger.info(f"Waiting for {api_call_delay_seconds}s before next chunk...")
            time.sleep(api_call_delay_seconds)

    if all_candles_df.empty:
        return pd.DataFrame(), f"No minute data found for {symbol} after attempting to fetch {days_history} days."

    # Process the combined DataFrame
    # Convert API 'datetime' (epoch ms) to pandas datetime objects, store in 'timestamp' column (America/New_York timezone)
    all_candles_df["timestamp"] = pd.to_datetime(all_candles_df["datetime"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    
    # Rename other relevant columns for consistency
    # Using lowercase column names for compatibility with technical_analysis.py
    all_candles_df = all_candles_df.rename(columns={
        "open": "open", "high": "high", "low": "low", 
        "close": "close", "volume": "volume"
    })
    
    # Select the final set of columns, ensuring 'timestamp' is a datetime object.
    # This implicitly drops the original 'datetime' column from the API if it's not in the list.
    # Using lowercase column names for compatibility with technical_analysis.py
    columns_to_keep = ["timestamp", "open", "high", "low", "close", "volume"]
    all_candles_df = all_candles_df[columns_to_keep]
    
    # Remove duplicate entries based on the 'timestamp'
    all_candles_df = all_candles_df.drop_duplicates(subset=["timestamp"])
    
    # Sort data by timestamp, typically newest first for financial time series
    all_candles_df = all_candles_df.sort_values(by="timestamp", ascending=False)
    
    # IMPORTANT: The 'timestamp' column is now a datetime object.
    # DO NOT convert it to a string here. String formatting for display will be handled by the consuming function (e.g., in dashboard_app.py).
    
    logger.info(f"Successfully fetched a total of {len(all_candles_df)} unique minute candles for {symbol} over {days_history} days.")
    return all_candles_df, None

def get_options_chain_data(client: schwabdev.Client, symbol: str):
    """Fetches options chain data for the given symbol, for REST polling."""
    if not client:
        return pd.DataFrame(), pd.DataFrame(), "Schwab client not initialized for get_options_chain_data."

    try:
        response = client.option_chains(
            symbol=symbol.upper(),
            contractType="ALL",
            includeUnderlyingQuote=False,
            expMonth="ALL",
            optionType="ALL"
        )

        if not response.ok:
            return pd.DataFrame(), pd.DataFrame(), f"Error fetching options chain for {symbol}: {response.status_code} - {response.text}"

        options_data = response.json()
        if options_data.get("status") == "FAILED":
             return pd.DataFrame(), pd.DataFrame(), f"Failed to fetch options chain for {symbol}: {options_data.get('error', 'Unknown API error')}"

        calls_list = []
        puts_list = []
        columns = ["Expiration Date", "Strike", "Last", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility", "Delta", "Gamma", "Theta", "Vega", "Contract Key"]

        for exp_date_map_type, contract_list_to_append in [("callExpDateMap", calls_list), ("putExpDateMap", puts_list)]:
            if exp_date_map_type in options_data and options_data[exp_date_map_type]:
                for date, strikes in options_data[exp_date_map_type].items():
                    for strike_price, contracts in strikes.items():
                        for contract in contracts:
                            if contract.get("openInterest", 0) > 0:
                                record = {
                                    "Expiration Date": contract.get("expirationDate"), # Use actual expirationDate field
                                    "Strike": contract.get("strikePrice"),
                                    "Last": contract.get("lastPrice"),
                                    "Bid": contract.get("bidPrice"),
                                    "Ask": contract.get("askPrice"),
                                    "Volume": contract.get("totalVolume"),
                                    "Open Interest": contract.get("openInterest"),
                                    "Implied Volatility": contract.get("volatility"),
                                    "Delta": contract.get("delta"),
                                    "Gamma": contract.get("gamma"),
                                    "Theta": contract.get("theta"),
                                    "Vega": contract.get("vega"),
                                    "Contract Key": contract.get("symbol") # This is the option symbol/key
                                }
                                contract_list_to_append.append(record)
        
        calls_df = pd.DataFrame(calls_list)
        puts_df = pd.DataFrame(puts_list)

        # Correctly ensure columns and order for calls_df
        if not calls_df.empty:
            for col in columns:
                if col not in calls_df.columns:
                    calls_df[col] = None
            calls_df = calls_df[columns]
            # Log the first row to verify Last, Bid, Ask values
            logger.info(f"Sample call option data - Last: {calls_df['Last'].iloc[0] if 'Last' in calls_df.columns else 'N/A'}, " +
                       f"Bid: {calls_df['Bid'].iloc[0] if 'Bid' in calls_df.columns else 'N/A'}, " +
                       f"Ask: {calls_df['Ask'].iloc[0] if 'Ask' in calls_df.columns else 'N/A'}")
        else:
            calls_df = pd.DataFrame(columns=columns)

        # Correctly ensure columns and order for puts_df
        if not puts_df.empty:
            for col in columns:
                if col not in puts_df.columns:
                    puts_df[col] = None
            puts_df = puts_df[columns]
            # Log the first row to verify Last, Bid, Ask values
            logger.info(f"Sample put option data - Last: {puts_df['Last'].iloc[0] if 'Last' in puts_df.columns else 'N/A'}, " +
                       f"Bid: {puts_df['Bid'].iloc[0] if 'Bid' in puts_df.columns else 'N/A'}, " +
                       f"Ask: {puts_df['Ask'].iloc[0] if 'Ask' in puts_df.columns else 'N/A'}")
        else:
            puts_df = pd.DataFrame(columns=columns)

        return calls_df, puts_df, None

    except Exception as e:
        logger.error(f"Error in get_options_chain_data for {symbol}: {e}", exc_info=True)
        return pd.DataFrame(), pd.DataFrame(), f"An error occurred while fetching options chain for {symbol}: {str(e)}"

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
            return set(), f"Error fetching option chains for keys: {response.status_code} - {response.text}"

        options_data = response.json()
        if options_data.get("status") == "FAILED":
            return set(), f"Failed to fetch option chains for keys: {options_data.get('error', 'Unknown API error')}"

        for exp_date_map_type in ["callExpDateMap", "putExpDateMap"]:
            if exp_date_map_type in options_data and options_data[exp_date_map_type]:
                for _date, strikes in options_data[exp_date_map_type].items():
                    for _strike_price, contracts_at_strike in strikes.items():
                        for contract in contracts_at_strike:
                            if contract.get("openInterest", 0) > 0 and contract.get("symbol"):
                                contract_keys.add(contract.get("symbol"))
        return contract_keys, None
    except Exception as e:
        logger.error(f"Error in get_option_contract_keys for {symbol}: {e}", exc_info=True)
        return set(), f"An error occurred while fetching option contract keys for {symbol}: {str(e)}"


if __name__ == "__main__":
    print("Testing data_fetchers.py...")
    test_client, client_error = get_schwab_client()
    if client_error:
        print(client_error)
    if test_client:
        print("Schwab client initialized successfully.")
        
        symbol_to_test = "AAPL" 
        days_to_test = 5 # Test with a smaller number of days first
        print(f"\nFetching {days_to_test} days of minute data for {symbol_to_test}...")
        minute_df, error = get_minute_data(test_client, symbol_to_test, days_history=days_to_test)
        if error:
            print(f"Error: {error}")
        elif not minute_df.empty:
            print(f"Successfully fetched minute data for {symbol_to_test} ({len(minute_df)} rows):")
            print("Minute Data Head:")
            print(minute_df.head())
            print("\nMinute Data Tail:")
            print(minute_df.tail())
            # Verify date range roughly
            if not minute_df.empty:
                min_date_str = minute_df["timestamp"].min()
                max_date_str = minute_df["timestamp"].max()
                print(f"Data ranges from {min_date_str} to {max_date_str}")
        else:
            print("No minute data returned.")

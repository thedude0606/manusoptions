# dashboard_utils/data_fetchers.py

import schwabdev
import os
import datetime
import json
import pandas as pd
import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
TOKENS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tokens.json")

# Configure basic logging for this module if not already configured by app
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
                logging.info("Attempting to refresh token...")
                try:
                    client.tokens.update_tokens_from_refresh_token()
                    if client.tokens and client.tokens.access_token:
                        logging.info("Token refreshed successfully.")
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

def get_minute_data(client: schwabdev.Client, symbol: str):
    """Fetches 1-minute historical price data for the given symbol for the last trading day."""
    if not client:
        return pd.DataFrame(), "Schwab client not initialized for get_minute_data."
    
    try:
        end_date = datetime.datetime.now()
        # Ensure start_date is a trading day if possible, or just go back. For simplicity, 1 day.
        start_date = end_date - datetime.timedelta(days=1) 

        response = client.price_history(
            symbol=symbol.upper(),
            frequencyType="minute",
            frequency=1,
            startDate=start_date, 
            endDate=end_date,
            needExtendedHoursData=True
        )

        if response.ok:
            price_data = response.json()
            if price_data.get("candles"):
                df = pd.DataFrame(price_data["candles"])
                df["datetime"] = pd.to_datetime(df["datetime"], unit="ms", utc=True).dt.tz_convert("America/New_York")
                df = df.rename(columns={
                    "datetime": "Timestamp", "open": "Open", "high": "High",
                    "low": "Low", "close": "Close", "volume": "Volume"
                })
                df = df[["Timestamp", "Open", "High", "Low", "Close", "Volume"]]
                df["Timestamp"] = df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S %Z")
                return df.sort_values(by="Timestamp", ascending=False), None
            elif price_data.get("empty") == True:
                return pd.DataFrame(), f"No minute data returned for {symbol} (API response empty)."
            else:
                return pd.DataFrame(), f"Unexpected response format for {symbol} minute data: {price_data}"
        else:
            return pd.DataFrame(), f"Error fetching minute data for {symbol}: {response.status_code} - {response.text}"

    except Exception as e:
        return pd.DataFrame(), f"An error occurred while fetching minute data for {symbol}: {str(e)}"

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
        else:
            calls_df = pd.DataFrame(columns=columns)

        # Correctly ensure columns and order for puts_df
        if not puts_df.empty:
            for col in columns:
                if col not in puts_df.columns:
                    puts_df[col] = None
            puts_df = puts_df[columns]
        else:
            puts_df = pd.DataFrame(columns=columns)

        return calls_df, puts_df, None

    except Exception as e:
        logging.error(f"Error in get_options_chain_data for {symbol}: {e}", exc_info=True)
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
        logging.error(f"Error in get_option_contract_keys for {symbol}: {e}", exc_info=True)
        return set(), f"An error occurred while fetching option contract keys for {symbol}: {str(e)}"


if __name__ == "__main__":
    print("Testing data_fetchers.py...")
    test_client, client_error = get_schwab_client()
    if client_error:
        print(client_error)
    if test_client:
        print("Schwab client initialized successfully.")
        
        symbol_to_test = "AAPL" # Ensure this symbol has liquid options for testing
        print(f"\nFetching minute data for {symbol_to_test}...")
        minute_df, error = get_minute_data(test_client, symbol_to_test)
        if error:
            print(f"Error: {error}")
        elif not minute_df.empty:
            print(f"Successfully fetched minute data for {symbol_to_test}:")
            print(minute_df.head())
        else:
            print(f"No minute data returned for {symbol_to_test}.")

        print(f"\nFetching options chain data (REST) for {symbol_to_test}...")
        calls_df, puts_df, error = get_options_chain_data(test_client, symbol_to_test)
        if error:
            print(f"Error: {error}")
        else:
            print(f"Successfully fetched options chain for {symbol_to_test}:")
            print("Calls Head:")
            print(calls_df.head())
            print("\nPuts Head:")
            print(puts_df.head())
            if calls_df.empty and puts_df.empty:
                print("No options data returned (both calls and puts are empty via REST).")

        print(f"\nFetching option contract keys for {symbol_to_test}...")
        keys, keys_error = get_option_contract_keys(test_client, symbol_to_test)
        if keys_error:
            print(f"Error fetching keys: {keys_error}")
        elif keys:
            print(f"Successfully fetched {len(keys)} option contract keys for {symbol_to_test}. First 5: {list(keys)[:5]}")
        else:
            print(f"No option contract keys with OI > 0 found for {symbol_to_test}.")

    else:
        print("Failed to initialize Schwab client. Ensure .env and tokens.json are correct and valid.")


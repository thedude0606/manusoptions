# dashboard_utils/data_fetchers.py

import schwabdev
import os
import datetime
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
TOKENS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tokens.json")

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
                print("Attempting to refresh token...") # Log to console
                try:
                    client.tokens.update_tokens_from_refresh_token()
                    if client.tokens and client.tokens.access_token:
                        print("Token refreshed successfully.") # Log to console
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
    """Fetches options chain data for the given symbol."""
    if not client:
        return pd.DataFrame(), pd.DataFrame(), "Schwab client not initialized for get_options_chain_data."

    try:
        response = client.option_chains(
            symbol=symbol.upper(),
            contractType="ALL",
            includeUnderlyingQuote=False,
            expMonth="ALL", # Fetch for all available expiration months
            optionType="ALL"
        )

        if not response.ok:
            return pd.DataFrame(), pd.DataFrame(), f"Error fetching options chain for {symbol}: {response.status_code} - {response.text}"

        options_data = response.json()
        if options_data.get("status") == "FAILED":
             return pd.DataFrame(), pd.DataFrame(), f"Failed to fetch options chain for {symbol}: {options_data.get('error', 'Unknown API error')}"


        calls_list = []
        puts_list = []
        
        # Define desired columns, matching the placeholder and user request
        # 'volatility' in API is 'volatility', 'openInterest' is 'openInterest'
        # Greeks: delta, gamma, theta, vega
        # Other: strikePrice, lastPrice, bidPrice, askPrice, totalVolume
        columns = ["Expiration Date", "Strike", "Last", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility", "Delta", "Gamma", "Theta", "Vega"]

        for exp_date_map_type, contract_list_to_append in [("callExpDateMap", calls_list), ("putExpDateMap", puts_list)]:
            if exp_date_map_type in options_data and options_data[exp_date_map_type]:
                for date, strikes in options_data[exp_date_map_type].items():
                    for strike_price, contracts in strikes.items():
                        for contract in contracts:
                            if contract.get("openInterest", 0) > 0:
                                record = {
                                    "Expiration Date": date,
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
                                    "Vega": contract.get("vega")
                                }
                                contract_list_to_append.append(record)
        
        calls_df = pd.DataFrame(calls_list)
        puts_df = pd.DataFrame(puts_list)

        # Ensure all desired columns are present, even if some contracts don't have all greeks (e.g. far OTM)
        for df in [calls_df, puts_df]:
            if not df.empty:
                for col in columns:
                    if col not in df.columns:
                        df[col] = None # or pd.NA or 0 depending on desired fill value
                # Reorder columns to the defined order
                df = df[columns]
            else: # If df is empty, create it with the correct columns
                df = pd.DataFrame(columns=columns)

        return calls_df, puts_df, None

    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), f"An error occurred while fetching options chain for {symbol}: {str(e)}"

if __name__ == "__main__":
    print("Testing data_fetchers.py...")
    test_client, client_error = get_schwab_client()
    if client_error:
        print(client_error)
    if test_client:
        print("Schwab client initialized successfully.")
        
        symbol_to_test = "AAPL"
        print(f"\nFetching minute data for {symbol_to_test}...")
        minute_df, error = get_minute_data(test_client, symbol_to_test)
        if error:
            print(f"Error: {error}")
        elif not minute_df.empty:
            print(f"Successfully fetched minute data for {symbol_to_test}:")
            print(minute_df.head())
        else:
            print(f"No minute data returned for {symbol_to_test}.")

        print(f"\nFetching options chain data for {symbol_to_test}...")
        calls_df, puts_df, error = get_options_chain_data(test_client, symbol_to_test)
        if error:
            print(f"Error: {error}")
        else:
            print(f"Successfully fetched options chain for {symbol_to_test}:")
            print("Calls:")
            print(calls_df.head())
            print("\nPuts:")
            print(puts_df.head())
            if calls_df.empty and puts_df.empty:
                print("No options data returned (both calls and puts are empty).")
    else:
        print("Failed to initialize Schwab client. Ensure .env and tokens.json are correct and valid.")


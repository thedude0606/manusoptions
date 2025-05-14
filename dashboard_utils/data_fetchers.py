# dashboard_utils/data_fetchers.py

import schwabdev
import os
import datetime
import json
import pandas as pd
from dotenv import load_dotenv

# It's better to initialize client and pass it, rather than re-initializing per call.
# However, for simplicity in these helper functions, we might need to handle client setup
# or expect an initialized client to be passed.

# Load environment variables if .env file is present in the root
# This might be redundant if the main app loads it, but good for standalone testing.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
TOKENS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tokens.json")

def get_schwab_client():
    """Helper to initialize and return a Schwab client if tokens exist."""
    app_key = os.getenv("APP_KEY")
    app_secret = os.getenv("APP_SECRET")
    callback_url = os.getenv("CALLBACK_URL")

    if not all([app_key, app_secret, callback_url]):
        print("Error: APP_KEY, APP_SECRET, or CALLBACK_URL not found in environment variables.")
        return None

    if not os.path.exists(TOKENS_FILE):
        print(f"Error: Tokens file not found at {TOKENS_FILE}. Please run authentication.")
        return None
    
    try:
        client = schwabdev.Client(app_key, app_secret, callback_url, tokens_file=TOKENS_FILE, capture_callback=False)
        if not (client.tokens and client.tokens.access_token):
            print("Error: No valid access token in loaded tokens.json. Please re-authenticate.")
            # Attempt to refresh token if refresh token is available
            if client.tokens and client.tokens.refresh_token:
                print("Attempting to refresh token...")
                client.tokens.update_tokens_from_refresh_token()
                if not (client.tokens and client.tokens.access_token):
                    print("Token refresh failed.")
                    return None
                print("Token refreshed successfully.")
            else:
                return None
        return client
    except Exception as e:
        print(f"Error initializing Schwab client: {e}")
        return None

def get_minute_data(client: schwabdev.Client, symbol: str):
    """Fetches 1-minute historical price data for the given symbol for the last trading day."""
    if not client:
        return pd.DataFrame(), "Schwab client not initialized."
    
    try:
        # Fetch data for the last trading day. Schwab API might have limitations on intraday history.
        # For simplicity, let's try to get data for today.
        # The API usually provides data for the current or previous trading day for minute frequency.
        # Let's aim for the last 1 day of minute data.
        end_date = datetime.datetime.now()
        # Schwab API's price_history for minute data typically returns data for a single day or a few days.
        # Let's request for the current day. It might return previous day if market is closed.
        start_date = end_date - datetime.timedelta(days=1) # Requesting for the last 24 hours to ensure we get the last trading day's data

        response = client.price_history(
            symbol=symbol.upper(),
            frequencyType="minute",
            frequency=1,
            startDate=start_date, 
            endDate=end_date,
            needExtendedHoursData=True # User asked for all available fields, so include extended hours
        )

        if response.ok:
            price_data = response.json()
            if price_data.get("candles"):
                df = pd.DataFrame(price_data["candles"])
                df["datetime"] = pd.to_datetime(df["datetime"], unit="ms", utc=True).dt.tz_convert("America/New_York")
                df = df.rename(columns={
                    "datetime": "Timestamp",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume"
                })
                df = df[["Timestamp", "Open", "High", "Low", "Close", "Volume"]]
                df["Timestamp"] = df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S %Z") # Format for display
                return df.sort_values(by="Timestamp", ascending=False), None
            elif price_data.get("empty") == True:
                return pd.DataFrame(), f"No minute data returned for {symbol} (API response empty)."
            else:
                return pd.DataFrame(), f"Unexpected response format for {symbol} minute data: {price_data}"
        else:
            return pd.DataFrame(), f"Error fetching minute data for {symbol}: {response.status_code} - {response.text}"

    except Exception as e:
        return pd.DataFrame(), f"An error occurred while fetching minute data for {symbol}: {str(e)}"

if __name__ == "__main__":
    # Example usage (requires .env and tokens.json to be set up in parent directory)
    print("Testing data_fetchers.py...")
    # This assumes your .env and tokens.json are in the 'manusoptions' directory
    # Adjust path if running this file directly from a different location or for testing.
    
    # Test client initialization
    test_client = get_schwab_client()
    if test_client:
        print("Schwab client initialized successfully.")
        
        # Test minute data fetching
        symbol_to_test = "AAPL" # Change to a symbol you want to test
        print(f"\nFetching minute data for {symbol_to_test}...")
        minute_df, error = get_minute_data(test_client, symbol_to_test)
        if error:
            print(f"Error: {error}")
        elif not minute_df.empty:
            print(f"Successfully fetched minute data for {symbol_to_test}:")
            print(minute_df.head())
        else:
            print(f"No minute data returned for {symbol_to_test}.")
    else:
        print("Failed to initialize Schwab client. Ensure .env and tokens.json are correct.")


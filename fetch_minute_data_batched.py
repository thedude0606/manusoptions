import schwabdev
import os
from dotenv import load_dotenv
import datetime
import json
import time
import pandas as pd
from tqdm import tqdm
from config import APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_FILE_PATH, MINUTE_DATA_CONFIG

# Placeholder for symbol, user can provide this later
SYMBOL = MINUTE_DATA_CONFIG['default_symbol']

def fetch_minute_data_for_day(client, symbol, day_date):
    """
    Fetch minute data for a specific day.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to fetch data for
        day_date: Date to fetch data for
        
    Returns:
        list: List of candle data for the day
    """
    try:
        # Set start and end time for the day (market hours)
        start_date = day_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = day_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        print(f"Fetching minute data for {symbol} on {start_date.strftime('%Y-%m-%d')}")
        
        response = client.price_history(
            symbol=symbol,
            frequencyType="minute",
            frequency=1,
            startDate=start_date,
            endDate=end_date,
            needExtendedHoursData=False
        )
        
        if response.ok:
            price_data = response.json()
            if price_data.get("candles"):
                print(f"Retrieved {len(price_data['candles'])} candles for {start_date.strftime('%Y-%m-%d')}")
                return price_data['candles']
            elif price_data.get("empty") == True:
                print(f"No data available for {symbol} on {start_date.strftime('%Y-%m-%d')}")
            else:
                print(f"Unexpected response format for {start_date.strftime('%Y-%m-%d')}")
        else:
            print(f"Error fetching data for {start_date.strftime('%Y-%m-%d')}: {response.status_code}")
            print(f"Response: {response.text}")
            
        # Sleep to avoid rate limiting
        time.sleep(0.5)
        
        return []
    
    except Exception as e:
        print(f"Exception while fetching data for {start_date.strftime('%Y-%m-%d')}: {e}")
        return []

def main():
    print(f"Attempting to fetch 60 days of minute data for {SYMBOL}")
    if not os.path.exists(TOKEN_FILE_PATH):
        print(f"Error: Tokens file not found at {TOKEN_FILE_PATH}. Please run the authentication script first.")
        return
    try:
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKEN_FILE_PATH, capture_callback=False)
        # Verify authentication by checking for access token
        if not (client.tokens and client.tokens.access_token):
            print("Error: No valid access token found. Please re-authenticate.")
            return
        print("Client initialized and token appears to be loaded.")
        # Calculate start and end dates for the last 60 days
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=60)
        
        print(f"Fetching 60 days of 1-minute data for {SYMBOL} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Create a list of dates to fetch (market days only)
        # For simplicity, we'll request all days and handle empty responses
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += datetime.timedelta(days=1)
        
        # Fetch data for each day and aggregate
        all_candles = []
        for day_date in tqdm(date_list, desc="Fetching daily data"):
            day_candles = fetch_minute_data_for_day(client, SYMBOL, day_date)
            all_candles.extend(day_candles)
        
        # Sort candles by datetime
        all_candles.sort(key=lambda x: x['datetime'])
        
        # Create aggregated result
        aggregated_data = {
            "symbol": SYMBOL,
            "candles": all_candles
        }
        
        # Save to a file
        output_filename = f"{SYMBOL}_minute_data_last_60_days.json"
        with open(output_filename, "w") as f:
            json.dump(aggregated_data, f, indent=2)
        
        print(f"Successfully fetched and aggregated {len(all_candles)} minute candles over 60 days")
        print(f"Data saved to {output_filename}")
        
        # Display summary statistics
        if all_candles:
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(all_candles)
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
            df.set_index('datetime', inplace=True)
            
            # Group by day and count
            daily_counts = df.groupby(df.index.date).size()
            
            print("\nSummary of data retrieved:")
            print(f"Total days with data: {len(daily_counts)}")
            print(f"Total candles: {len(all_candles)}")
            print(f"Date range: {df.index.min().date()} to {df.index.max().date()}")
            print(f"Average candles per day: {len(all_candles) / len(daily_counts) if len(daily_counts) > 0 else 0:.1f}")
            
            # Display first few candles as an example
            print("\nFirst 3 candles:")
            for candle in all_candles[:3]:
                dt = datetime.datetime.fromtimestamp(candle['datetime']/1000)
                print(f"{dt}: Open: {candle['open']}, High: {candle['high']}, Low: {candle['low']}, Close: {candle['close']}, Volume: {candle['volume']}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

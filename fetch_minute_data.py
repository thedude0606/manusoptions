import schwabdev
import os
from dotenv import load_dotenv
import datetime
import json
import pandas as pd
from config import APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_FILE_PATH, MINUTE_DATA_CONFIG

# Placeholder for symbol, user can provide this later
SYMBOL = MINUTE_DATA_CONFIG['default_symbol']

def main():
    print(f"Attempting to fetch minute data for {SYMBOL}")
    
    if not os.path.exists(TOKEN_FILE_PATH):
        print(f"Error: Tokens file not found at {TOKEN_FILE_PATH}. Please run the authentication script first.")
        return
    
    try:
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKEN_FILE_PATH, capture_callback=False)
        
        # Verify authentication by checking for access token
        if not (client.tokens and client.tokens.access_token):
            print("Error: No valid access token found. Please re-authenticate.")
            # Optionally, could try to refresh here, but auth_script should handle initial setup.
            # client.tokens.update_refresh_token() # This would require the handle_redirect_uri logic again
            return
        
        print("Client initialized and token appears to be loaded.")
        
        # Calculate start and end dates for the last 60 days (changed from 90 days)
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=MINUTE_DATA_CONFIG['default_days'])
        
        # Format dates as milliseconds since epoch, as required by some APIs or as yyyy-MM-dd
        # The schwabdev library documentation for price_history indicates it can handle datetime objects directly
        # or strings. Let's try with datetime objects first, or format if needed.
        # The documentation for the underlying Schwab API states: 
        # startDate: Start date as yyyy-MM-dd or epoch milliseconds.
        # endDate: End date as yyyy-MM-dd or epoch milliseconds.
        # Let's use epoch milliseconds for precision with time, though the library might abstract this.
        # The schwabdev library's client.py shows it converts datetime to milliseconds if needed.
        
        print(f"Fetching 1-minute data for {SYMBOL} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        response = client.price_history(
            symbol=SYMBOL,
            frequencyType="minute",
            frequency=1,
            startDate=start_date, # Using datetime object
            endDate=end_date,     # Using datetime object
            needExtendedHoursData=False # As per user request for 'available information'
        )
        
        if response.ok:
            price_data = response.json()
            print(f"Successfully fetched price data for {SYMBOL}.")
            # print(json.dumps(price_data, indent=2))
            
            if price_data.get("candles"):
                print(f"Number of candles received: {len(price_data['candles'])}")
                
                # Save to a file for inspection
                output_filename = f"{SYMBOL}_minute_data_last_60_days.json"
                with open(output_filename, "w") as f:
                    json.dump(price_data, f, indent=2)
                print(f"Data saved to {output_filename}")
                
                # Display first few candles as an example
                if len(price_data['candles']) > 0:
                    print("First 3 candles:")
                    for candle in price_data['candles'][:3]:
                        print(candle)
                else:
                    print("No candles returned in the response.")
            elif price_data.get("empty") == True:
                 print("API returned an empty result, possibly no data for the period or symbol.")
            else:
                print("Response format unexpected. Full response:")
                print(json.dumps(price_data, indent=2))
        else:
            print(f"Error fetching price data: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

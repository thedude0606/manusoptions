import schwabdev
import os
import json
from dotenv import load_dotenv
import datetime

# Load environment variables from .env file
load_dotenv()

APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")
TOKENS_FILE = "tokens.json"  # Relative path for local execution

# Placeholder for symbol, user can modify this
SYMBOL = "AAPL"
OUTPUT_FILE = f"{SYMBOL}_options_chain.json" # Relative path for output

def main():
    print(f"Attempting to fetch options chain data for {SYMBOL}")

    if not os.path.exists(TOKENS_FILE):
        print(f"Error: Tokens file 	{TOKENS_FILE} not found. Please run the authentication script first.")
        return

    try:
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKENS_FILE, capture_callback=False)

        if not (client.tokens and client.tokens.access_token):
            print("Error: No valid access token found in tokens file. Please re-authenticate.")
            return
        print("Client initialized and token appears to be loaded.")

        # Example: Fetch options for the nearest expiration date
        # You might want to specify contractType, strikeCount, expirationDate, etc.
        # For simplicity, let's try to get all available for the nearest standard expiration
        # The API might require more specific parameters for a successful call.
        # Refer to Schwab API documentation for get_options_chain parameters.
        # For now, let's try a broad request and see the response structure or errors.
        # Common parameters: symbol, contractType (CALL, PUT, ALL), strikeCount, includeUnderlyingQuote, strategy, interval, strike, range, fromDate, toDate, volatility, underlyingPrice, interestRate, daysToExpiration, expMonth, optionType

        print(f"Fetching options chain for {SYMBOL}...")
        response = client.get_options_chain(
            symbol=SYMBOL,
            contractType="ALL", # Fetch both calls and puts
            # strikeCount=10, # Number of strikes to return above and below the at-the-money price
            # includeUnderlyingQuote=True,
            # strategy="SINGLE", # SINGLE, ANALYTICAL, COVERED, VERTICAL, CALENDAR, STRANGLE, STRADDLE, BUTTERFLY, CONDOR, DIAGONAL, COLLAR, ROLL
            # expMonth="ALL" # ALL, JAN, FEB, etc.
            # fromDate=(datetime.date.today()).strftime("%Y-%m-%d"),
            # toDate=(datetime.date.today() + datetime.timedelta(days=45)).strftime("%Y-%m-%d") # Example: next 45 days
        )

        if response.ok:
            options_data = response.json()
            print(f"Successfully fetched options chain data for {SYMBOL}.")
            
            with open(OUTPUT_FILE, "w") as f:
                json.dump(options_data, f, indent=2)
            print(f"Options chain data saved to {OUTPUT_FILE}")

            # Optionally, print some summary
            if "callExpDateMap" in options_data and options_data["callExpDateMap"]:
                print(f"Call options found for {len(options_data[	'callExpDateMap	'])} expiration dates.")
            if "putExpDateMap" in options_data and options_data["putExpDateMap"]:
                print(f"Put options found for {len(options_data[	'putExpDateMap	'])} expiration dates.")
            if not options_data.get("callExpDateMap") and not options_data.get("putExpDateMap") and options_data.get("status") == "SUCCESS" and options_data.get("underlying") is not None:
                 print("Options data retrieved, but no call/put maps found. This might mean no options for the selected criteria or a different response structure.")
                 print(json.dumps(options_data, indent=2))

        else:
            print(f"Error fetching options chain data: {response.status_code}")
            print(f"Response: {response.text}")
            # Save error response for debugging
            with open(f"{SYMBOL}_options_chain_error.json", "w") as f:
                f.write(response.text)
            print(f"Error response saved to {SYMBOL}_options_chain_error.json")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


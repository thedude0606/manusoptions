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
TOKENS_FILE = "tokens.json"  # Assumes tokens.json is in the same directory

# --- Symbol to fetch --- (User can change this)
SYMBOL = "AAPL"
# --- Options Chain Parameters --- (User can adjust these as needed)
CONTRACT_TYPE = "ALL"  # "ALL", "CALL", "PUT"
STRIKE_COUNT = None  # Number of strikes around the at-the-money price
INCLUDE_UNDERLYING_QUOTE = True
STRATEGY = "SINGLE"  # e.g., SINGLE, STRADDLE, etc.
RANGE = "ALL" # e.g., ITM, NTM, OTM, ALL
# Dates can be datetime objects or strings like "YYYY-MM-DD"
# By default, fetches for the nearest available expiration dates if fromDate/toDate are None
FROM_DATE = None 
TO_DATE = None 
EXP_MONTH = "ALL" # e.g., JAN, FEB, ALL
OPTION_TYPE = "ALL" # e.g., S, NS, ALL


def main():
    print(f"Attempting to fetch options chain data for {SYMBOL}")

    if not all([APP_KEY, APP_SECRET, CALLBACK_URL]):
        print("Error: APP_KEY, APP_SECRET, or CALLBACK_URL not found in .env file.")
        return

    client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKENS_FILE, capture_callback=False)

    if not os.path.exists(TOKENS_FILE):
        print(f"Error: {TOKENS_FILE} not found. Please run auth_script.py first.")
        return
    
    if not client.token_manager.tokens_valid():
        print("Tokens are invalid or expired. Attempting to refresh...")
        try:
            client.token_manager.refresh_tokens()
            if client.token_manager.tokens_valid():
                print("Tokens refreshed successfully.")
            else:
                print("Failed to refresh tokens. Please re-authenticate using auth_script.py.")
                return
        except Exception as e:
            print(f"Error refreshing tokens: {e}. Please re-authenticate using auth_script.py.")
            return

    print("Client initialized and token appears to be loaded and valid.")
    print(f"Fetching options chain for {SYMBOL} using client.option_chains()...")

    try:
        response = client.option_chains(
            symbol=SYMBOL,
            contractType=CONTRACT_TYPE,
            strikeCount=STRIKE_COUNT,
            includeUnderlyingQuote=INCLUDE_UNDERLYING_QUOTE,
            strategy=STRATEGY,
            range=RANGE,
            fromDate=FROM_DATE,
            toDate=TO_DATE,
            expMonth=EXP_MONTH,
            optionType=OPTION_TYPE
        )

        if response.ok:
            options_data = response.json()
            output_filename = f"{SYMBOL}_options_chain.json"
            with open(output_filename, "w") as f:
                json.dump(options_data, f, indent=4)
            print(f"Options chain data successfully fetched and saved to {output_filename}")
            
            # Optional: Print some basic info from the response
            if options_data.get('status') == "SUCCESS":
                print(f"Symbol: {options_data.get('symbol')}")
                print(f"Underlying Price: {options_data.get('underlyingPrice')}")
                print(f"Number of Contracts: {options_data.get('numberOfContracts')}")
                if options_data.get('callExpDateMap'):
                    print(f"Number of call expiration dates: {len(options_data['callExpDateMap'])}")
                if options_data.get('putExpDateMap'):
                    print(f"Number of put expiration dates: {len(options_data['putExpDateMap'])}")
            else:
                print(f"API call successful but status is not SUCCESS: {options_data.get('status')}")

        else:
            error_message = f"Error fetching options chain data: {response.status_code}"
            try:
                error_details = response.json()
                error_message += f"\nResponse: {json.dumps(error_details)}"
                output_filename = f"{SYMBOL}_options_chain_error.json"
                with open(output_filename, "w") as f:
                    json.dump(error_details, f, indent=4)
                print(f"Error response saved to {output_filename}")
            except json.JSONDecodeError:
                error_message += f"\nResponse: {response.text}"
            print(error_message)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


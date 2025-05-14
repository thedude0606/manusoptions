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

        print(f"Fetching options chain for {SYMBOL} using instruments endpoint...")
        # The `instruments` endpoint with projection="optionchain" should provide options data.
        # The Schwab API itself for options chains might take other parameters like contractType, strikeCount, etc.
        # The schwabdev library might pass these through or have specific ways to handle them.
        # For now, this is the most direct way to get the option chain via the instruments endpoint based on typical API structures.
        response = client.instruments(symbol=SYMBOL, projection="optionchain")

        if response.ok:
            options_data = response.json()
            print(f"Successfully fetched options chain data for {SYMBOL}.")
            
            with open(OUTPUT_FILE, "w") as f:
                json.dump(options_data, f, indent=2)
            print(f"Options chain data saved to {OUTPUT_FILE}")

            # The structure of the options_data from client.instruments might be different
            # from a dedicated options chain endpoint. We need to inspect it.
            # Common structures involve a map of expiration dates to strikes.
            # Example check (actual keys might vary based on schwabdev library's parsing of the response):
            if options_data.get(SYMBOL) and isinstance(options_data[SYMBOL], list) and options_data[SYMBOL][0].get("optionChain"):
                print("Option chain data seems to be present in the expected structure.")
                # Further parsing would go here based on actual response structure
            elif options_data.get("callExpDateMap") or options_data.get("putExpDateMap"):
                 print("Options data retrieved with call/put expiration date maps.")
            else:
                print("Options data retrieved, but the structure needs inspection. Full response:")
                # print(json.dumps(options_data, indent=2)) # Potentially very large output
                if len(json.dumps(options_data)) < 2000: # Print only if reasonably small
                    print(json.dumps(options_data, indent=2))
                else:
                    print("Response is large, not printing to console. Check the output file.")

        else:
            print(f"Error fetching options chain data: {response.status_code}")
            print(f"Response: {response.text}")
            error_output_file = f"{SYMBOL}_options_chain_error.json"
            with open(error_output_file, "w") as f:
                f.write(response.text)
            print(f"Error response saved to {error_output_file}")

    except AttributeError as ae:
        print(f"An AttributeError occurred: {ae}")
        print("This might indicate that the method or attribute is not available in the schwabdev library version you are using, or the client object was not initialized correctly.")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


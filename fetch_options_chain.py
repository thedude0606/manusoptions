import schwabdev
import os
import sys
from dotenv import load_dotenv
import datetime
import json
from config import APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_FILE_PATH, OPTIONS_CHAIN_CONFIG

# App mode (FETCH or STREAM)
APP_MODE = "FETCH"  # Default to FETCH mode

# Fetch mode configuration
FETCH_SYMBOL = "AAPL"  # Default symbol for fetch mode
CONTRACT_TYPE_FETCH = OPTIONS_CHAIN_CONFIG['contract_type']
STRIKE_COUNT_FETCH = OPTIONS_CHAIN_CONFIG['strike_count']
INCLUDE_UNDERLYING_QUOTE_FETCH = OPTIONS_CHAIN_CONFIG['include_underlying_quote']
STRATEGY_FETCH = OPTIONS_CHAIN_CONFIG['strategy']
RANGE_FETCH = OPTIONS_CHAIN_CONFIG['range']
OPTION_TYPE_FETCH = OPTIONS_CHAIN_CONFIG['option_type']
FROM_DATE_FETCH = None  # Optional: YYYY-MM-DD
TO_DATE_FETCH = None    # Optional: YYYY-MM-DD
EXP_MONTH_FETCH = None  # Optional: YYYY-MM (only used if FROM_DATE and TO_DATE not provided)

# Stream mode configuration
STREAMING_SYMBOLS = ["AAPL", "MSFT", "GOOGL"]  # Default symbols for stream mode

# Configure logging
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def normalize_contract_key(contract_key):
    """Normalize contract key for consistent matching."""
    return contract_key.strip().upper()

def run_options_streaming_mode(client, symbols):
    """Run the options streaming mode for the specified symbols."""
    print(f"Starting options streaming for symbols: {', '.join(symbols)}")
    
    # Dictionary to store current contract data
    current_contracts_data = {}
    detected_changes = []
    
    # Define the fields to stream
    fields = [
        "key", "cusip", "assetMainType", "symbol", 
        "description", "bidPrice", "bidSize", "askPrice", 
        "askSize", "lastPrice", "lastSize", "openPrice", 
        "highPrice", "lowPrice", "closePrice", "netChange", 
        "totalVolume", "quoteTimeInLong", "tradeTimeInLong", 
        "mark", "openInterest", "volatility", "moneyIntrinsicValue", 
        "multiplier", "strikePrice", "contractType", "underlying", 
        "timeValue", "deliverables", "delta", "gamma", "theta", 
        "vega", "rho", "securityStatus", "theoreticalOptionValue", 
        "underlyingPrice", "uvExpirationType", "exchange", "exchangeName", 
        "settlementType", "netPercentChangeInDouble", "markChangeInDouble", 
        "markPercentChangeInDouble", "impliedYield", "isPennyPilot", "daysToExpiration"
    ]
    
    # Define callback for streaming data
    def on_message(message):
        nonlocal current_contracts_data, detected_changes
        
        try:
            # Check if the message contains option data
            if message.get("service") == "OPTION" and message.get("content"):
                content = message.get("content")
                
                # Extract the contract key and normalize it
                contract_key = content.get("key", "")
                if not contract_key:
                    logger.warning("Received option data without a key")
                    return
                
                normalized_key = normalize_contract_key(contract_key)
                
                # Check if this is a new contract or an update
                is_new = normalized_key not in current_contracts_data
                
                # If new, store all fields
                if is_new:
                    current_contracts_data[normalized_key] = content
                    logger.info(f"New contract added: {normalized_key}")
                else:
                    # If update, check for changes in specific fields
                    old_data = current_contracts_data[normalized_key]
                    
                    # Fields to monitor for changes
                    monitored_fields = ["bidPrice", "askPrice", "lastPrice", "mark", "delta", "gamma", "theta", "vega", "impliedVolatility", "openInterest", "totalVolume"]
                    
                    for field in monitored_fields:
                        if field in content and (field not in old_data or content[field] != old_data[field]):
                            # Record the change
                            detected_changes.append({
                                "contract": normalized_key,
                                "metric": field,
                                "old": old_data.get(field, "N/A"),
                                "new": content[field]
                            })
                            
                            # Update the field in our stored data
                            old_data[field] = content[field]
                
                # Check if we have price fields in any contract
                has_bid = any("bidPrice" in data for data in current_contracts_data.values())
                has_ask = any("askPrice" in data for data in current_contracts_data.values())
                has_last = any("lastPrice" in data for data in current_contracts_data.values())
                logger.info(f"Price fields present in any contract: Bid={has_bid}, Ask={has_ask}, Last={has_last}")
                
                if detected_changes:
                    if os.name == "nt":
                        os.system("cls")
                    else:
                        os.system("clear")
                    print(f"--- Option Changes Detected ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
                    print(f"Total changes in this batch: {len(detected_changes)}")
                    print("{:<25} | {:<16} | {:<20} | {:<20}".format("Contract", "Metric", "Old Value", "New Value"))
                    print("-" * 90)
                    for change in detected_changes:
                        print("{:<25} | {:<16} | {:<20} | {:<20}".format(change['contract'], change['metric'], str(change['old']), str(change['new'])))
                    sys.stdout.flush()
                    detected_changes.clear()
        except Exception as e:
            logger.error(f"Error processing streaming message: {e}")
    
    try:
        # Create and start the streamer
        streamer = client.create_streamer()
        streamer.add_options_handler(on_message)
        
        # Add symbols to stream
        for symbol in symbols:
            streamer.add_option_chain(symbol, fields)
        
        # Start streaming
        streamer.start()
        print("Streamer started. Press Ctrl+C to stop.")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
            # Check if we have price fields in any contract
            if current_contracts_data:
                has_bid = any("bidPrice" in data for data in current_contracts_data.values())
                has_ask = any("askPrice" in data for data in current_contracts_data.values())
                has_last = any("lastPrice" in data for data in current_contracts_data.values())
                logger.info(f"Price fields present in any contract: Bid={has_bid}, Ask={has_ask}, Last={has_last}")
                
                if detected_changes:
                    if os.name == "nt":
                        os.system("cls")
                    else:
                        os.system("clear")
                    print(f"--- Option Changes Detected ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
                    print(f"Total changes in this batch: {len(detected_changes)}")
                    print("{:<25} | {:<16} | {:<20} | {:<20}".format("Contract", "Metric", "Old Value", "New Value"))
                    print("-" * 90)
                    for change in detected_changes:
                        print("{:<25} | {:<16} | {:<20} | {:<20}".format(change['contract'], change['metric'], str(change['old']), str(change['new'])))
                    sys.stdout.flush()
                    detected_changes.clear()
    except KeyboardInterrupt:
        print("\nUser requested stop. Shutting down streamer...")
    finally:
        if hasattr(streamer, 'is_alive') and streamer.is_alive():
            streamer.stop()
            print("Streamer stopped.")
        elif hasattr(streamer, 'running') and streamer.running: # Alternative check if is_alive not present
             streamer.stop()
             print("Streamer stopped via .running check.")
        else:
            print("Streamer was not running or already stopped, or status cannot be determined.")

def run_fetch_mode(client, symbol_to_fetch):
    print(f"Attempting to fetch options chain data for {symbol_to_fetch}")
    api_params_fetch = {
        "symbol": symbol_to_fetch,
        "contractType": CONTRACT_TYPE_FETCH,
        "strikeCount": STRIKE_COUNT_FETCH,
        "includeUnderlyingQuote": INCLUDE_UNDERLYING_QUOTE_FETCH,
        "strategy": STRATEGY_FETCH,
        "range": RANGE_FETCH,
        "optionType": OPTION_TYPE_FETCH
    }
    if FROM_DATE_FETCH:
        api_params_fetch["fromDate"] = FROM_DATE_FETCH
    if TO_DATE_FETCH:
        api_params_fetch["toDate"] = TO_DATE_FETCH
    if not FROM_DATE_FETCH and not TO_DATE_FETCH: # Only use expMonth if specific dates aren't given
        api_params_fetch["expMonth"] = EXP_MONTH_FETCH
    try:
        response = client.option_chains(**api_params_fetch)
        if response.ok:
            options_data = response.json()
            output_filename = f"{symbol_to_fetch}_options_chain.json"
            with open(output_filename, "w") as f:
                json.dump(options_data, f, indent=4)
            print(f"Options chain data successfully fetched and saved to {output_filename}")
            if options_data.get("status") == "SUCCESS":
                print(f"Symbol: {options_data.get('symbol')}, Underlying Price: {options_data.get('underlyingPrice')}")
            else:
                print(f"API call successful but status is not SUCCESS: {options_data.get('status')}")
        else:
            print(f"Error fetching options chain data: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"An unexpected error occurred during fetch: {e}")
        import traceback
        traceback.print_exc()

def main():
    if not all([APP_KEY, APP_SECRET, CALLBACK_URL]):
        print("Error: APP_KEY, APP_SECRET, or CALLBACK_URL not found in .env file.")
        return
    if not os.path.exists(TOKEN_FILE_PATH):
        print(f"Error: {TOKEN_FILE_PATH} not found. Please run auth_script.py first.")
        return
    
    client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKEN_FILE_PATH, capture_callback=False)
    if not (hasattr(client, "tokens") and client.tokens and client.tokens.access_token):
        print(f"No valid access token in {TOKEN_FILE_PATH}. Run auth_script.py.")
        return
    print("Ensuring tokens are up-to-date...")
    try:
        client.tokens.update_tokens()
        if not (client.tokens and client.tokens.access_token):
            print("Critical: Failed to update/validate tokens. Re-authenticate with auth_script.py.")
            return
        print("Tokens are valid.")
    except Exception as e:
        print(f"Error updating tokens: {e}. Re-authenticate with auth_script.py.")
        return
    if APP_MODE == "FETCH":
        print(f"Running in FETCH mode for symbol: {FETCH_SYMBOL}")
        run_fetch_mode(client, FETCH_SYMBOL)
    elif APP_MODE == "STREAM":
        if not STREAMING_SYMBOLS:
            print("Error: STREAMING_SYMBOLS list is empty. Cannot start stream mode.")
            return
        print(f"Running in STREAM mode for symbols: {', '.join(STREAMING_SYMBOLS)}")
        run_options_streaming_mode(client, STREAMING_SYMBOLS)
    else:
        print(f"Error: Unknown APP_MODE '{APP_MODE}'. Set to 'FETCH' or 'STREAM'.")

if __name__ == "__main__":
    main()

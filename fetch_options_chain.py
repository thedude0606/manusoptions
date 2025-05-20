import schwabdev
import os
import json
from dotenv import load_dotenv
import datetime
import time
import threading
import sys # For flushing output
import logging # For detailed logging
import re # For contract key formatting

# Import utility functions for contract key formatting
from dashboard_utils.contract_utils import normalize_contract_key, format_contract_key_for_streaming

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("options_streaming.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("options_streaming")

# Load environment variables from .env file
load_dotenv()

APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")
TOKENS_FILE = "tokens.json"
DIAG_LOG_FILE = "raw_contracts_diag.log" # Log file for raw contract data

# --- Application Mode --- 
# "FETCH" for one-time options chain fetch and save to file
# "STREAM" for continuous streaming of option changes
APP_MODE = "STREAM"  # User can change this to "FETCH"

# --- Configuration for FETCH Mode --- (Used if APP_MODE is "FETCH")
FETCH_SYMBOL = "AAPL"
CONTRACT_TYPE_FETCH = "ALL"
STRIKE_COUNT_FETCH = None
INCLUDE_UNDERLYING_QUOTE_FETCH = True
STRATEGY_FETCH = "SINGLE"
RANGE_FETCH = "ALL"
FROM_DATE_FETCH = None # Example: "2025-05-15"
TO_DATE_FETCH = None   # Example: "2025-05-15"
EXP_MONTH_FETCH = "ALL"
OPTION_TYPE_FETCH = "ALL"

# --- Configuration for STREAM Mode --- (Used if APP_MODE is "STREAM")
STREAMING_SYMBOLS = ["AAPL"]  # List of underlying symbols to stream (e.g., ["AAPL", "MSFT"])

# Filters for selecting contracts to stream:
STREAMING_FILTER_MIN_OPEN_INTEREST = 1  # Minimum open interest required
STREAMING_FILTER_DTE = 0  # Target Days To Expiration (e.g., 0 for 0DTE). Set to None to disable DTE filter.

# Updated to include both numeric and string field IDs
STREAMING_OPTION_FIELDS_REQUEST = "0,2,3,4,9,10,20,27,28,29,30,31,32"
STREAMING_FIELD_MAPPING = {
    # Numeric field IDs
    0: "key",
    2: "bidPrice",
    3: "askPrice",
    4: "lastPrice",
    9: "openInterest",
    10: "volatility",
    20: "strikePrice", 
    27: "daysToExpiration",
    28: "delta",
    29: "gamma",
    30: "theta",
    31: "vega",
    32: "rho",
    # String field IDs (for robustness)
    "0": "key",
    "2": "bidPrice",
    "3": "askPrice",
    "4": "lastPrice",
    "9": "openInterest",
    "10": "volatility",
    "20": "strikePrice", 
    "27": "daysToExpiration",
    "28": "delta",
    "29": "gamma",
    "30": "theta",
    "31": "vega",
    "32": "rho"
}
MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION = 300

# Global state for streaming
current_contracts_data = {} 
detected_changes = []
stream_data_lock = threading.Lock()

def stream_message_handler(message_json_str):
    global current_contracts_data, detected_changes
    logger.debug(f"Received message: {message_json_str[:200]}..." if len(message_json_str) > 200 else message_json_str)
    
    try:
        data_packets = json.loads(message_json_str)
        logger.debug(f"Parsed data packets: {json.dumps(data_packets)[:500]}..." if len(json.dumps(data_packets)) > 500 else json.dumps(data_packets))
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return

    for packet in data_packets:
        if packet.get("service") == "LEVELONE_OPTIONS":
            logger.info(f"Processing LEVELONE_OPTIONS packet with {len(packet.get('content', []))} content items")
            
            for contract_item in packet.get("content", []):
                contract_key = contract_item.get("key")
                if not contract_key:
                    logger.warning(f"Skipping contract item without key: {contract_item}")
                    continue

                # Normalize the contract key for consistent matching
                normalized_key = normalize_contract_key(contract_key)
                logger.debug(f"Processing contract: {contract_key} (normalized: {normalized_key}) with fields: {contract_item}")
                
                # Log specific price fields if they exist
                for price_field in ["2", "3", "4"]:  # bidPrice, askPrice, lastPrice
                    if price_field in contract_item:
                        field_name = STREAMING_FIELD_MAPPING.get(price_field, f"Unknown-{price_field}")
                        logger.info(f"PRICE FIELD FOUND: Contract {normalized_key} has {field_name}={contract_item[price_field]}")

                with stream_data_lock:
                    if normalized_key not in current_contracts_data:
                        logger.debug(f"Creating new entry for contract: {normalized_key}")
                        current_contracts_data[normalized_key] = {}

                    for field_idx_str, new_value in contract_item.items():
                        if field_idx_str == "key":
                            continue
                        
                        # Handle both string and numeric field IDs
                        if field_idx_str in STREAMING_FIELD_MAPPING:
                            metric_name = STREAMING_FIELD_MAPPING[field_idx_str]
                            logger.debug(f"Field {field_idx_str} maps to metric {metric_name}")
                        else:
                            try:
                                field_idx = int(field_idx_str)
                                if field_idx in STREAMING_FIELD_MAPPING:
                                    metric_name = STREAMING_FIELD_MAPPING[field_idx]
                                    logger.debug(f"Field {field_idx} maps to metric {metric_name}")
                                else:
                                    logger.warning(f"Unknown field index: {field_idx_str}")
                                    continue
                            except ValueError:
                                logger.warning(f"Non-integer field index: {field_idx_str}")
                                continue
                            
                        try:
                            if isinstance(new_value, str):
                                if "." in new_value or "e" in new_value.lower():
                                    new_value_typed = float(new_value)
                                    logger.debug(f"Converted string '{new_value}' to float: {new_value_typed}")
                                elif new_value.lstrip("-").isdigit():
                                    new_value_typed = int(new_value)
                                    logger.debug(f"Converted string '{new_value}' to int: {new_value_typed}")
                                else:
                                    new_value_typed = new_value
                                    logger.debug(f"Kept string value as is: {new_value_typed}")
                            else:
                                new_value_typed = new_value
                                logger.debug(f"Non-string value, kept as is: {new_value_typed}")
                        except ValueError as e:
                            new_value_typed = new_value
                            logger.warning(f"Value conversion error for {new_value}: {e}")
                        
                        current_metric_value = current_contracts_data[normalized_key].get(metric_name)
                        logger.debug(f"Current value for {metric_name}: {current_metric_value}")

                        # Special logging for price fields
                        if field_idx_str in ["2", "3", "4"] or (isinstance(field_idx_str, int) and field_idx_str in [2, 3, 4]):
                            logger.info(f"PRICE UPDATE: Contract {normalized_key}, {metric_name}: {current_metric_value} -> {new_value_typed}")

                        if current_metric_value != new_value_typed:
                            logger.debug(f"Value changed for {normalized_key}.{metric_name}: {current_metric_value} -> {new_value_typed}")
                            detected_changes.append({
                                "contract": normalized_key,
                                "metric": metric_name,
                                "old": current_metric_value if current_metric_value is not None else "N/A",
                                "new": new_value_typed,
                                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                            })
                            current_contracts_data[normalized_key][metric_name] = new_value_typed
                        elif current_metric_value is None:
                            logger.debug(f"Setting initial value for {normalized_key}.{metric_name}: {new_value_typed}")
                            current_contracts_data[normalized_key][metric_name] = new_value_typed

def get_filtered_option_contract_keys(client, underlying_symbol):
    print(f"Fetching and filtering option contract keys for {underlying_symbol}...")
    print(f"Filters: Min Open Interest > {STREAMING_FILTER_MIN_OPEN_INTEREST-1}, DTE == {STREAMING_FILTER_DTE if STREAMING_FILTER_DTE is not None else 'Any'}")
    print(f"Raw contract data will be logged to: {DIAG_LOG_FILE}")
    keys = []
    api_params = {
        "symbol": underlying_symbol,
        "contractType": "ALL",
        "strikeCount": None,
        "includeUnderlyingQuote": False,
        "strategy": "SINGLE",
        "range": "ALL",
        "optionType": "ALL"
    }

    if STREAMING_FILTER_DTE == 0:
        today_date_str = datetime.date.today().strftime("%Y-%m-%d")
        api_params["fromDate"] = today_date_str
        api_params["toDate"] = today_date_str
        print(f"Querying for 0DTE: fromDate={today_date_str}, toDate={today_date_str}")
    else:
        api_params["expMonth"] = "ALL" # Default for non-0DTE or if DTE filter is off
        # If STREAMING_FILTER_DTE is a specific number (e.g., 30), the filtering happens *after* fetching all months.
        # For more targeted non-0DTE fetches, one might need to map DTE to specific expMonth values if desired.

    try:
        with open(DIAG_LOG_FILE, "a") as diag_file: # Open log file in append mode
            diag_file.write(f"\nDiagnostic Log for {underlying_symbol} - {datetime.datetime.now()}\n")
            diag_file.write(f"API Params: {json.dumps(api_params)}\n")
            diag_file.write("--- Raw Contract Data Before Filtering ---\n")
            
            response = client.option_chains(**api_params)

            if response.ok:
                options_data = response.json()
                if options_data.get("status") == "SUCCESS":
                    for map_type in ["callExpDateMap", "putExpDateMap"]:
                        if map_type in options_data:
                            for exp_date_key, strikes_map in options_data[map_type].items():
                                for _, contract_list in strikes_map.items():
                                    for contract in contract_list:
                                        diag_symbol = contract.get("symbol", "N/A")
                                        diag_oi = contract.get("openInterest", "N/A")
                                        diag_dte = contract.get("daysToExpiration", "N/A")
                                        log_line = f"  Raw Contract: {diag_symbol}, OI: {diag_oi}, DTE: {diag_dte}\n"
                                        diag_file.write(log_line)
                                        
                                        open_interest = contract.get("openInterest", 0)
                                        days_to_expiration = contract.get("daysToExpiration")
                                        passes_oi_filter = open_interest >= STREAMING_FILTER_MIN_OPEN_INTEREST
                                        
                                        passes_dte_filter = False
                                        if STREAMING_FILTER_DTE is None: # If DTE filter is off, it passes
                                            passes_dte_filter = True
                                        elif days_to_expiration is not None:
                                            if STREAMING_FILTER_DTE == 0: # For 0DTE, check if DTE is 0 or if it's today's expiration
                                                contract_exp_date_str = diag_symbol[len(underlying_symbol):len(underlying_symbol)+6]
                                                try:
                                                    contract_exp_date = datetime.datetime.strptime(contract_exp_date_str, "%y%m%d").date()
                                                    if contract_exp_date == datetime.date.today() or days_to_expiration == 0:
                                                        passes_dte_filter = True
                                                except ValueError:
                                                    if days_to_expiration == 0: # Fallback if date parsing fails
                                                        passes_dte_filter = True
                                            elif days_to_expiration == STREAMING_FILTER_DTE:
                                                passes_dte_filter = True
                                        
                                        if passes_oi_filter and passes_dte_filter and "symbol" in contract:
                                            # Normalize the contract key before adding to the list
                                            normalized_key = normalize_contract_key(contract["symbol"])
                                            keys.append(normalized_key)
                    diag_file.write("--- End of Raw Contract Data ---\n")
                    filtered_keys = list(set(keys))
                    print(f"Found {len(filtered_keys)} unique contract keys for {underlying_symbol} after filtering.")
                    if not filtered_keys:
                        print(f"Warning: No contracts for {underlying_symbol} matched the filters.")
                else:
                    error_msg = f"API Error (Option Chain for {underlying_symbol}): Status not SUCCESS - {options_data.get('status')}\n"
                    print(error_msg.strip())
                    diag_file.write(error_msg)
            else:
                error_msg = f"HTTP Error (Option Chain for {underlying_symbol}): {response.status_code} - {response.text}\n"
                print(error_msg.strip())
                diag_file.write(error_msg)
    except Exception as e:
        error_msg = f"Exception while fetching/filtering option keys for {underlying_symbol}: {e}\n"
        print(error_msg.strip())
        if 'diag_file' in locals() and diag_file and not diag_file.closed:
             diag_file.write(error_msg)
        import traceback
        traceback.print_exc()
    return list(set(keys))

def run_options_streaming_mode(client, symbols_to_stream):
    logger.info("Starting options streaming mode")
    streamer = client.stream
    all_contract_keys_to_stream = []
    for symbol in symbols_to_stream:
        logger.info(f"Getting filtered option contract keys for {symbol}")
        keys = get_filtered_option_contract_keys(client, symbol)
        if keys:
            logger.info(f"Found {len(keys)} keys for {symbol}")
            all_contract_keys_to_stream.extend(keys)
    all_contract_keys_to_stream = list(set(all_contract_keys_to_stream))

    if not all_contract_keys_to_stream:
        logger.error("No option contracts found for any specified symbols matching filters. Streaming cannot start.")
        print("No option contracts found for any specified symbols matching filters. Streaming cannot start.")
        return

    logger.info(f"Total unique option contracts to stream after filtering: {len(all_contract_keys_to_stream)}")
    print(f"Total unique option contracts to stream after filtering: {len(all_contract_keys_to_stream)}")

    # Log the field request configuration
    logger.info(f"Using field request: {STREAMING_OPTION_FIELDS_REQUEST}")
    logger.info(f"Field mapping configuration: {STREAMING_FIELD_MAPPING}")

    for i in range(0, len(all_contract_keys_to_stream), MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION):
        chunk = all_contract_keys_to_stream[i:i + MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION]
        
        # Format contract keys for streaming
        formatted_keys = [format_contract_key_for_streaming(key) for key in chunk]
        keys_str_chunk = ",".join(formatted_keys)
        
        logger.info(f"Subscribing to {len(chunk)} option contracts (Chunk {i // MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION + 1})...")
        print(f"Subscribing to {len(chunk)} option contracts (Chunk {i // MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION + 1})...")
        
        # Create and log the subscription payload
        subscription_payload = streamer.level_one_options(keys_str_chunk, STREAMING_OPTION_FIELDS_REQUEST)
        logger.debug(f"Subscription payload: {json.dumps(subscription_payload)[:500]}..." if len(json.dumps(subscription_payload)) > 500 else json.dumps(subscription_payload))
        
        streamer.send(subscription_payload)
        logger.info(f"Sent subscription for chunk {i // MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION + 1}")
        time.sleep(1.5)

    logger.info("Starting stream handler...")
    print("Starting stream handler...")
    streamer.start(stream_message_handler, daemon=True)
    logger.info("Stream started. Monitoring for changes.")
    print("Stream started. Monitoring for changes every 5 seconds. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(5)
            with stream_data_lock:
                # Log current state of data store periodically
                logger.info(f"Current data store size: {len(current_contracts_data)} contracts")
                
                # Log a sample of the current data for price fields
                sample_count = 0
                for contract_key, contract_data in list(current_contracts_data.items())[:5]:  # Sample first 5 contracts
                    price_info = {
                        "bidPrice": contract_data.get("bidPrice", "N/A"),
                        "askPrice": contract_data.get("askPrice", "N/A"),
                        "lastPrice": contract_data.get("lastPrice", "N/A")
                    }
                    logger.info(f"Sample contract {contract_key} price data: {price_info}")
                    sample_count += 1
                
                if sample_count == 0 and current_contracts_data:
                    # If we have contracts but none were sampled, log one anyway
                    contract_key = next(iter(current_contracts_data))
                    contract_data = current_contracts_data[contract_key]
                    price_info = {
                        "bidPrice": contract_data.get("bidPrice", "N/A"),
                        "askPrice": contract_data.get("askPrice", "N/A"),
                        "lastPrice": contract_data.get("lastPrice", "N/A")
                    }
                    logger.info(f"Single sample contract {contract_key} price data: {price_info}")
                
                # Check if we have any price fields at all
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

    if not os.path.exists(TOKENS_FILE):
        print(f"Error: {TOKENS_FILE} not found. Please run auth_script.py first.")
        return
    
    client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKENS_FILE, capture_callback=False)

    if not (hasattr(client, "tokens") and client.tokens and client.tokens.access_token):
        print(f"No valid access token in {TOKENS_FILE}. Run auth_script.py.")
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

import schwabdev
import os
import json
from dotenv import load_dotenv
import datetime
import time
import threading
import sys # For flushing output

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

STREAMING_OPTION_FIELDS_REQUEST = "0,2,3,4,9,10,20,27,28,29,30,31,32"
STREAMING_FIELD_MAPPING = {
    0: "ContractKey",
    2: "BidPrice",
    3: "AskPrice",
    4: "LastPrice",
    9: "OpenInterest",
    10: "Volatility",
    20: "StrikePrice", 
    27: "DaysToExpiration",
    28: "Delta",
    29: "Gamma",
    30: "Theta",
    31: "Vega",
    32: "Rho"
}
MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION = 300

# Global state for streaming
current_contracts_data = {} 
detected_changes = []
stream_data_lock = threading.Lock()

def stream_message_handler(message_json_str):
    global current_contracts_data, detected_changes
    try:
        data_packets = json.loads(message_json_str)
    except json.JSONDecodeError:
        return

    for packet in data_packets:
        if packet.get("service") == "LEVELONE_OPTIONS":
            for contract_item in packet.get("content", []):
                contract_key = contract_item.get("key")
                if not contract_key:
                    continue

                with stream_data_lock:
                    if contract_key not in current_contracts_data:
                        current_contracts_data[contract_key] = {}

                    for field_idx_str, new_value in contract_item.items():
                        if field_idx_str == "key":
                            continue
                        try:
                            field_idx = int(field_idx_str)
                        except ValueError:
                            continue

                        if field_idx in STREAMING_FIELD_MAPPING:
                            metric_name = STREAMING_FIELD_MAPPING[field_idx]
                            try:
                                if isinstance(new_value, str):
                                    if "." in new_value or "e" in new_value.lower():
                                        new_value_typed = float(new_value)
                                    elif new_value.lstrip("-").isdigit():
                                        new_value_typed = int(new_value)
                                    else:
                                        new_value_typed = new_value
                                else:
                                    new_value_typed = new_value
                            except ValueError:
                                new_value_typed = new_value
                            
                            current_metric_value = current_contracts_data[contract_key].get(metric_name)

                            if current_metric_value != new_value_typed:
                                detected_changes.append({
                                    "contract": contract_key,
                                    "metric": metric_name,
                                    "old": current_metric_value if current_metric_value is not None else "N/A",
                                    "new": new_value_typed,
                                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                                })
                                current_contracts_data[contract_key][metric_name] = new_value_typed
                            elif current_metric_value is None:
                                current_contracts_data[contract_key][metric_name] = new_value_typed

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
                                            keys.append(contract["symbol"])
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
    streamer = client.stream
    all_contract_keys_to_stream = []
    for symbol in symbols_to_stream:
        keys = get_filtered_option_contract_keys(client, symbol)
        if keys:
            all_contract_keys_to_stream.extend(keys)
    all_contract_keys_to_stream = list(set(all_contract_keys_to_stream))

    if not all_contract_keys_to_stream:
        print("No option contracts found for any specified symbols matching filters. Streaming cannot start.")
        return

    print(f"Total unique option contracts to stream after filtering: {len(all_contract_keys_to_stream)}")

    for i in range(0, len(all_contract_keys_to_stream), MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION):
        chunk = all_contract_keys_to_stream[i:i + MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION]
        keys_str_chunk = ",".join(chunk)
        print(f"Subscribing to {len(chunk)} option contracts (Chunk {i // MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION + 1})...")
        streamer.send(streamer.level_one_options(keys_str_chunk, STREAMING_OPTION_FIELDS_REQUEST))
        time.sleep(1.5)

    print("Starting stream handler...")
    streamer.start(stream_message_handler, daemon=True)
    print("Stream started. Monitoring for changes every 5 seconds. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(5)
            with stream_data_lock:
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


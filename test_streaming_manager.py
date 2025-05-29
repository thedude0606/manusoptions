"""
Test script for validating the streaming manager fixes.

This script creates a simple test environment to validate the streaming manager's
connection stability, error handling, reconnection logic, and data flow.
"""

import sys
import time
import logging
import datetime
import threading
import json
from dashboard_utils.streaming_manager import StreamingManager
from config import APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_FILE_PATH
import schwabdev

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_streaming')

# Print startup message
print(f"TEST_STREAMING: Starting test at {datetime.datetime.now()}", file=sys.stderr)

# Initialize Schwab client getter function
def get_schwab_client():
    print(f"TEST_STREAMING: get_schwab_client called at {datetime.datetime.now()}", file=sys.stderr)
    try:
        client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file=TOKEN_FILE_PATH, capture_callback=False)
        print(f"TEST_STREAMING: Successfully created Schwab client", file=sys.stderr)
        return client
    except Exception as e:
        logger.error(f"Error initializing Schwab client: {e}", exc_info=True)
        print(f"TEST_STREAMING: Error initializing Schwab client: {e}", file=sys.stderr)
        return None

# Initialize account ID getter function
def get_account_id():
    print(f"TEST_STREAMING: get_account_id called at {datetime.datetime.now()}", file=sys.stderr)
    try:
        client = get_schwab_client()
        if not client:
            print(f"TEST_STREAMING: Failed to get Schwab client in get_account_id", file=sys.stderr)
            return None
        
        response = client.accounts()
        if not response.ok:
            logger.error(f"Error fetching accounts: {response.status_code} - {response.text}")
            print(f"TEST_STREAMING: Error fetching accounts: {response.status_code} - {response.text}", file=sys.stderr)
            return None
        
        accounts = response.json()
        if not accounts:
            logger.error("No accounts found")
            print(f"TEST_STREAMING: No accounts found", file=sys.stderr)
            return None
        
        # Use the first account ID
        account_id = accounts[0].get("accountId")
        print(f"TEST_STREAMING: Successfully got account ID: {account_id[:4]}...", file=sys.stderr)
        return account_id
    except Exception as e:
        logger.error(f"Error getting account ID: {e}", exc_info=True)
        print(f"TEST_STREAMING: Error getting account ID: {e}", file=sys.stderr)
        return None

# Function to get option contract keys for a symbol
def get_option_contract_keys(symbol):
    print(f"TEST_STREAMING: Getting option contract keys for {symbol}", file=sys.stderr)
    try:
        client = get_schwab_client()
        if not client:
            print(f"TEST_STREAMING: Failed to get Schwab client", file=sys.stderr)
            return []
        
        # Get option chain data
        response = client.option_chain(
            symbol=symbol,
            contract_type="ALL",
            strike_count=10,  # Limit to 10 strikes around the money for testing
            include_quotes=True,
            strategy="SINGLE",
            interval=None,
            strike=None,
            range="NTM",  # Near the money
            from_date=None,
            to_date=None,
            exp_month="ALL",
            option_type="ALL"
        )
        
        if not response.ok:
            logger.error(f"Error fetching option chain: {response.status_code} - {response.text}")
            print(f"TEST_STREAMING: Error fetching option chain: {response.status_code} - {response.text}", file=sys.stderr)
            return []
        
        option_chain = response.json()
        
        # Extract contract keys
        contract_keys = []
        
        # Process call options
        call_exp_date_map = option_chain.get("callExpDateMap", {})
        for exp_date, strikes in call_exp_date_map.items():
            for strike, contracts in strikes.items():
                for contract in contracts:
                    if contract.get("openInterest", 0) > 0:  # Only include contracts with open interest
                        symbol = contract.get("symbol", "")
                        if symbol:
                            contract_keys.append(symbol)
        
        # Process put options
        put_exp_date_map = option_chain.get("putExpDateMap", {})
        for exp_date, strikes in put_exp_date_map.items():
            for strike, contracts in strikes.items():
                for contract in contracts:
                    if contract.get("openInterest", 0) > 0:  # Only include contracts with open interest
                        symbol = contract.get("symbol", "")
                        if symbol:
                            contract_keys.append(symbol)
        
        print(f"TEST_STREAMING: Found {len(contract_keys)} contract keys", file=sys.stderr)
        return contract_keys
    except Exception as e:
        logger.error(f"Error getting option contract keys: {e}", exc_info=True)
        print(f"TEST_STREAMING: Error getting option contract keys: {e}", file=sys.stderr)
        return []

# Function to monitor streaming status
def monitor_streaming_status(streaming_manager, duration=120):
    print(f"TEST_STREAMING: Starting streaming monitor for {duration} seconds", file=sys.stderr)
    
    start_time = time.time()
    check_interval = 5  # seconds
    
    while time.time() - start_time < duration:
        status = streaming_manager.get_status()
        data = streaming_manager.get_latest_data()
        
        print(f"\nTEST_STREAMING: Status at {datetime.datetime.now()}", file=sys.stderr)
        print(f"  Is Running: {status['is_running']}", file=sys.stderr)
        print(f"  Status Message: {status['status_message']}", file=sys.stderr)
        print(f"  Error Message: {status['error_message']}", file=sys.stderr)
        print(f"  Subscriptions Count: {status['subscriptions_count']}", file=sys.stderr)
        print(f"  Data Count: {status['data_count']}", file=sys.stderr)
        print(f"  Message Counter: {status['message_counter']}", file=sys.stderr)
        
        if 'last_data_update' in status:
            print(f"  Last Data Update: {status['last_data_update']}", file=sys.stderr)
        
        if 'last_heartbeat' in status:
            print(f"  Last Heartbeat: {status['last_heartbeat']}", file=sys.stderr)
        
        # Print a sample of the data if available
        if data:
            sample_keys = list(data.keys())[:3]
            print(f"  Data Sample ({len(sample_keys)} of {len(data)} contracts):", file=sys.stderr)
            for key in sample_keys:
                print(f"    {key}: Bid={data[key].get('bidPrice', 'N/A')}, Ask={data[key].get('askPrice', 'N/A')}, Last={data[key].get('lastPrice', 'N/A')}", file=sys.stderr)
        
        time.sleep(check_interval)
    
    print(f"TEST_STREAMING: Monitoring completed after {duration} seconds", file=sys.stderr)

# Main test function
def main():
    print(f"TEST_STREAMING: Starting main test function", file=sys.stderr)
    
    # Initialize StreamingManager
    print(f"TEST_STREAMING: Creating StreamingManager", file=sys.stderr)
    streaming_manager = StreamingManager(get_schwab_client, get_account_id)
    
    # Get option contract keys for a test symbol
    symbol = "AAPL"  # Use Apple as a test symbol
    print(f"TEST_STREAMING: Getting contract keys for {symbol}", file=sys.stderr)
    contract_keys = get_option_contract_keys(symbol)
    
    if not contract_keys:
        print(f"TEST_STREAMING: No contract keys found for {symbol}. Exiting test.", file=sys.stderr)
        return
    
    print(f"TEST_STREAMING: Starting stream with {len(contract_keys)} contract keys", file=sys.stderr)
    streaming_manager.start_stream(contract_keys)
    
    # Monitor streaming status for 2 minutes
    monitor_streaming_status(streaming_manager, duration=120)
    
    # Stop the stream
    print(f"TEST_STREAMING: Stopping stream", file=sys.stderr)
    streaming_manager.stop_stream()
    
    print(f"TEST_STREAMING: Test completed", file=sys.stderr)

if __name__ == "__main__":
    main()

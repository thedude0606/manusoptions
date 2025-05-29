import threading
import time
import logging
import json # Added for JSON parsing
import schwabdev # Import the main schwabdev library
import os
import datetime
import traceback
import sys

# Import utility functions for contract key formatting
from dashboard_utils.contract_utils import normalize_contract_key, format_contract_key_for_streaming

# Configure basic logging with both console and file handlers
logger = logging.getLogger(__name__) # Use __name__ for module-specific logger

# Always define log_file regardless of handler state
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"streaming_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Add immediate console print for debugging
print(f"STREAMING_MANAGER: Initializing module, log file will be: {log_file}", file=sys.stderr)

if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    # Console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
logger.setLevel(logging.DEBUG) # Set to DEBUG for verbose logging during diagnosis
logger.info(f"Streaming manager logger initialized. Logging to console and file: {log_file}")
print(f"STREAMING_MANAGER: Logger initialized with level DEBUG", file=sys.stderr)

# To get more detailed logs from schwabdev library itself, uncomment the following line:
logging.getLogger("schwabdev").setLevel(logging.DEBUG)

class StreamingManager:
    # Updated field list to ensure we get all price data
    SCHWAB_FIELD_IDS_TO_REQUEST = "0,2,3,4,8,9,10,12,16,17,18,20,21,23,26,28,29,30,31"
    
    # Updated field mapping to handle both string and numeric field IDs
    SCHWAB_FIELD_MAP = {
        # Numeric field IDs
        0: "key",
        2: "bidPrice",
        3: "askPrice",
        4: "lastPrice",
        8: "totalVolume",
        9: "openInterest",
        10: "volatility", # Implied Volatility
        12: "expirationYear",
        16: "bidSize",
        17: "askSize",
        18: "lastSize",
        20: "strikePrice",
        21: "contractType", # C or P
        23: "expirationMonth",
        26: "expirationDay",
        28: "delta",
        29: "gamma",
        30: "theta",
        31: "vega",
        # String field IDs
        "0": "key",
        "2": "bidPrice",
        "3": "askPrice",
        "4": "lastPrice",
        "8": "totalVolume",
        "9": "openInterest",
        "10": "volatility",
        "12": "expirationYear",
        "16": "bidSize",
        "17": "askSize",
        "18": "lastSize",
        "20": "strikePrice",
        "21": "contractType",
        "23": "expirationMonth",
        "26": "expirationDay",
        "28": "delta",
        "29": "gamma",
        "30": "theta",
        "31": "vega"
    }

    def __init__(self, schwab_client_getter, account_id_getter):
        print(f"STREAMING_MANAGER: __init__ called at {datetime.datetime.now()}", file=sys.stderr)
        self.schwab_client_getter = schwab_client_getter
        self.account_id_getter = account_id_getter
        self.stream_client = None
        self.is_running = False
        self.stream_thread = None
        self.current_subscriptions = set()
        self.latest_data_store = {}
        self.error_message = None
        self.status_message = "Idle"
        self._lock = threading.RLock() # Changed to RLock for reentrancy safety in complex interactions
        self.message_counter = 0
        
        # Create a separate log file specifically for raw stream messages
        self.raw_stream_log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", 
                                               f"raw_stream_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        self.raw_stream_logger = logging.getLogger(f"{__name__}.raw_stream")
        if not self.raw_stream_logger.hasHandlers():
            raw_handler = logging.FileHandler(self.raw_stream_log_file)
            raw_formatter = logging.Formatter("%(asctime)s - %(message)s")
            raw_handler.setFormatter(raw_formatter)
            self.raw_stream_logger.addHandler(raw_handler)
            self.raw_stream_logger.setLevel(logging.DEBUG)
        
        logger.info(f"StreamingManager initialized with RLock. Raw stream logs will be written to: {self.raw_stream_log_file}")
        print(f"STREAMING_MANAGER: Initialization complete, raw stream logs: {self.raw_stream_log_file}", file=sys.stderr)

    def _get_schwab_client(self):
        print(f"STREAMING_MANAGER: _get_schwab_client called at {datetime.datetime.now()}", file=sys.stderr)
        try:
            client = self.schwab_client_getter()
            if not client:
                self.error_message = "Failed to get Schwab client."
                logger.error(self.error_message)
                print(f"STREAMING_MANAGER: Failed to get Schwab client", file=sys.stderr)
                return None
            logger.debug("_get_schwab_client: Successfully obtained Schwab client.")
            print(f"STREAMING_MANAGER: Successfully obtained Schwab client", file=sys.stderr)
            return client
        except Exception as e:
            self.error_message = f"Error obtaining Schwab client: {e}"
            logger.error(self.error_message, exc_info=True) # Log full traceback
            print(f"STREAMING_MANAGER: Error obtaining Schwab client: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return None

    def _stream_worker(self, option_keys_to_subscribe_tuple):
        print(f"STREAMING_MANAGER: _stream_worker started at {datetime.datetime.now()} with {len(option_keys_to_subscribe_tuple)} keys", file=sys.stderr)
        option_keys_to_subscribe = set(option_keys_to_subscribe_tuple)
        logger.info(f"_stream_worker started for {len(option_keys_to_subscribe)} keys: {list(option_keys_to_subscribe)[:5]}...")
        
        # Log a sample of the keys to verify format
        for i, key in enumerate(list(option_keys_to_subscribe)[:10]):
            logger.info(f"Sample key {i}: '{key}'")
            print(f"STREAMING_MANAGER: Sample key {i}: '{key}'", file=sys.stderr)
        
        with self._lock:
            self.status_message = "Stream: Initializing worker..."
            self.error_message = None # Clear previous errors

        schwab_api_client = self._get_schwab_client()
        if not schwab_api_client:
            with self._lock:
                self.status_message = f"Stream: Error - {self.error_message or 'Failed to get Schwab client in worker'}"
                self.is_running = False # Ensure is_running is false if client fails
            logger.error("_stream_worker: Failed to get Schwab client. Worker terminating.")
            print(f"STREAMING_MANAGER: Failed to get Schwab client. Worker terminating.", file=sys.stderr)
            return

        account_hash = self.account_id_getter()
        if account_hash:
            logger.info(f"_stream_worker: Account hash provided (first 4 chars for log): {str(account_hash)[:4]}...")
            print(f"STREAMING_MANAGER: Account hash provided: {str(account_hash)[:4]}...", file=sys.stderr)
        else:
            logger.info("_stream_worker: No account hash provided; not strictly required for LEVELONE_OPTIONS.")
            print(f"STREAMING_MANAGER: No account hash provided", file=sys.stderr)

        try:
            with self._lock:
                self.stream_client = schwab_api_client.stream
            logger.info("_stream_worker: Schwab stream object obtained via client.stream")
            print(f"STREAMING_MANAGER: Schwab stream object obtained via client.stream", file=sys.stderr)

            if not option_keys_to_subscribe:
                logger.warning("_stream_worker: No symbols to subscribe.")
                print(f"STREAMING_MANAGER: No symbols to subscribe.", file=sys.stderr)
                with self._lock:
                    self.status_message = "Stream: No symbols to subscribe."
                    self.is_running = False
                return

            # Define a custom handler that logs raw messages before processing
            def custom_stream_handler(raw_message):
                try:
                    # Log the raw message to the dedicated raw stream log file
                    self.raw_stream_logger.debug(f"RAW MESSAGE: {raw_message}")
                    print(f"STREAMING_MANAGER: Received raw message: {str(raw_message)[:100]}...", file=sys.stderr)
                    
                    # Process the message with our regular handler
                    self._handle_stream_message(raw_message)
                except Exception as e:
                    logger.error(f"Error in custom_stream_handler: {e}", exc_info=True)
                    print(f"STREAMING_MANAGER: Error in custom_stream_handler: {e}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
            
            logger.info("_stream_worker: Starting schwabdev's stream listener with custom handler...")
            print(f"STREAMING_MANAGER: Starting schwabdev's stream listener with custom handler...", file=sys.stderr)
            self.stream_client.start(custom_stream_handler)
            logger.info("_stream_worker: schwabdev's stream_client.start() called. Listener should be active in its own thread.")
            print(f"STREAMING_MANAGER: schwabdev's stream_client.start() called", file=sys.stderr)

            time.sleep(3) # Allow time for connection
            logger.info("_stream_worker: Waited 3s for connection, proceeding with subscriptions.")
            print(f"STREAMING_MANAGER: Waited 3s for connection, proceeding with subscriptions", file=sys.stderr)

            # Format contract keys properly for streaming using the utility function
            formatted_keys = []
            for key in option_keys_to_subscribe:
                # Ensure the key is properly formatted with spaces for streaming
                formatted_key = format_contract_key_for_streaming(key)
                formatted_keys.append(formatted_key)
            
            # Log the original and formatted keys for debugging
            logger.info(f"_stream_worker: Original keys sample: {list(option_keys_to_subscribe)[:5]}")
            logger.info(f"_stream_worker: Formatted keys sample: {formatted_keys[:5]}")
            print(f"STREAMING_MANAGER: Original keys sample: {list(option_keys_to_subscribe)[:5]}", file=sys.stderr)
            print(f"STREAMING_MANAGER: Formatted keys sample: {formatted_keys[:5]}", file=sys.stderr)
            
            keys_str = ",".join(formatted_keys)
            fields_str = self.SCHWAB_FIELD_IDS_TO_REQUEST
            
            subscription_payload = self.stream_client.level_one_options(keys_str, fields_str, command="ADD")
            logger.info(f"_stream_worker: Preparing to send LEVELONE_OPTIONS subscription. Keys count: {len(formatted_keys)}. Fields: {fields_str}.")
            logger.debug(f"_stream_worker: Full subscription payload being sent: {json.dumps(subscription_payload)}")
            print(f"STREAMING_MANAGER: Preparing to send LEVELONE_OPTIONS subscription with {len(formatted_keys)} keys", file=sys.stderr)
            
            # Log the full payload to the raw stream log
            self.raw_stream_logger.debug(f"SENDING SUBSCRIPTION: {json.dumps(subscription_payload)}")
            
            self.stream_client.send(subscription_payload)
            logger.info(f"_stream_worker: Subscription payload sent for {len(formatted_keys)} keys.")
            print(f"STREAMING_MANAGER: Subscription payload sent for {len(formatted_keys)} keys", file=sys.stderr)

            with self._lock:
                self.current_subscriptions = set(formatted_keys)
                self.status_message = f"Stream: Subscriptions sent for {len(self.current_subscriptions)} contracts. Monitoring..."
            
            logger.info("_stream_worker: Subscriptions sent. Now entering main monitoring loop.")
            print(f"STREAMING_MANAGER: Subscriptions sent. Now entering main monitoring loop", file=sys.stderr)
            loop_counter = 0
            while True:
                with self._lock:
                    if not self.is_running:
                        logger.info("_stream_worker: self.is_running is False. Exiting monitoring loop.")
                        print(f"STREAMING_MANAGER: self.is_running is False. Exiting monitoring loop", file=sys.stderr)
                        break
                
                if loop_counter % 20 == 0: # Log every 10 seconds (0.5 * 20)
                    logger.debug(f"_stream_worker: Monitoring loop active. is_running: {self.is_running}. Subscriptions: {len(self.current_subscriptions)}")
                    
                    # Every 10 seconds, check if we've received any data
                    with self._lock:
                        data_count = len(self.latest_data_store)
                        if data_count > 0:
                            logger.info(f"_stream_worker: Currently storing data for {data_count} contracts.")
                            print(f"STREAMING_MANAGER: Currently storing data for {data_count} contracts", file=sys.stderr)
                            # Log a sample of the stored data
                            sample_keys = list(self.latest_data_store.keys())[:3]
                            for key in sample_keys:
                                data = self.latest_data_store[key]
                                logger.info(f"Sample data for {key}: Last={data.get('lastPrice')}, Bid={data.get('bidPrice')}, Ask={data.get('askPrice')}")
                                print(f"STREAMING_MANAGER: Sample data for {key}: Last={data.get('lastPrice')}, Bid={data.get('bidPrice')}, Ask={data.get('askPrice')}", file=sys.stderr)
                        else:
                            logger.warning("_stream_worker: No data received from stream yet.")
                            print(f"STREAMING_MANAGER: No data received from stream yet", file=sys.stderr)
                
                time.sleep(0.5) 
                loop_counter +=1
            logger.info("_stream_worker: Exited monitoring loop.")
            print(f"STREAMING_MANAGER: Exited monitoring loop", file=sys.stderr)

        except Exception as e:
            logger.error(f"Error in _stream_worker's main try block: {e}", exc_info=True)
            print(f"STREAMING_MANAGER: Error in _stream_worker's main try block: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            with self._lock:
                self.error_message = f"Stream worker error: {e}"
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False # Critical: ensure is_running is set to false on error
        finally:
            logger.info("_stream_worker: Reached finally block.")
            print(f"STREAMING_MANAGER: Reached finally block", file=sys.stderr)
            with self._lock:
                if self.is_running: 
                    logger.warning("_stream_worker in finally, but self.is_running is still true. Forcing to False.")
                    print(f"STREAMING_MANAGER: self.is_running is still true. Forcing to False", file=sys.stderr)
                    self.is_running = False

                if self.error_message:
                    self.status_message = f"Stream: Error - {self.error_message}"
                elif self.status_message == "Stream: Stopping...":
                    self.status_message = "Stream: Stopped."
                elif self.status_message not in ["Stream: Stopped.", "Stream: No symbols to subscribe."]:
                    self.status_message = "Stream: Stopped unexpectedly."
            
            active_schwab_stream_client = None
            with self._lock:
                active_schwab_stream_client = self.stream_client

            if active_schwab_stream_client and hasattr(active_schwab_stream_client, "stop") and active_schwab_stream_client.active:
                try:
                    logger.info("_stream_worker's finally block: Attempting to stop schwabdev stream client.")
                    print(f"STREAMING_MANAGER: Attempting to stop schwabdev stream client", file=sys.stderr)
                    active_schwab_stream_client.stop()
                    logger.info("_stream_worker's finally block: schwabdev stream client stop() called.")
                    print(f"STREAMING_MANAGER: schwabdev stream client stop() called", file=sys.stderr)
                except Exception as e_stop:
                    logger.error(f"_stream_worker's finally block: Error stopping schwabdev stream client: {e_stop}", exc_info=True)
                    print(f"STREAMING_MANAGER: Error stopping schwabdev stream client: {e_stop}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
            else:
                logger.info("_stream_worker's finally block: Schwabdev stream client not active/stoppable or already None.")
                print(f"STREAMING_MANAGER: Schwabdev stream client not active/stoppable or already None", file=sys.stderr)
            
            with self._lock:
                self.stream_client = None
            logger.info("_stream_worker finished.")
            print(f"STREAMING_MANAGER: _stream_worker finished", file=sys.stderr)

    def _handle_stream_message(self, raw_message):
        self.message_counter += 1
        current_message_id = self.message_counter
        
        # Always log the full raw message to the dedicated raw stream log
        self.raw_stream_logger.debug(f"[MsgID:{current_message_id}] RECEIVED: {raw_message}")
        
        log_msg_content = str(raw_message)
        if len(log_msg_content) > 1000:
            log_msg_content = log_msg_content[:1000] + "... (truncated)"
        logger.debug(f"[MsgID:{current_message_id}] _handle_stream_message received raw_message (type: {type(raw_message)}). Content: {log_msg_content}")
        
        try:
            message_dict = None
            if isinstance(raw_message, str):
                try:
                    message_dict = json.loads(raw_message)
                    # Log the parsed JSON for debugging
                    logger.debug(f"[MsgID:{current_message_id}] Parsed JSON: {json.dumps(message_dict)[:1000]}...")
                except json.JSONDecodeError as jde:
                    logger.error(f"[MsgID:{current_message_id}] Failed to decode JSON: {jde} - Raw (first 200): {raw_message[:200]}", exc_info=True)
                    print(f"STREAMING_MANAGER: Failed to decode JSON: {jde} - Raw (first 200): {raw_message[:200]}", file=sys.stderr)
                    return
            elif isinstance(raw_message, dict):
                message_dict = raw_message
                logger.debug(f"[MsgID:{current_message_id}] Received dict message: {json.dumps(message_dict)[:1000]}...")
            else:
                logger.warning(f"[MsgID:{current_message_id}] Unexpected message type: {type(raw_message)}. Raw: {raw_message}")
                print(f"STREAMING_MANAGER: Unexpected message type: {type(raw_message)}", file=sys.stderr)
                return
            
            # Log the full message for debugging
            self.raw_stream_logger.debug(f"[MsgID:{current_message_id}] PARSED: {json.dumps(message_dict)}")

            if "data" in message_dict:
                data_items = message_dict.get("data", [])
                logger.info(f"[MsgID:{current_message_id}] Identified \"data\" message with {len(data_items)} items.")
                print(f"STREAMING_MANAGER: Identified \"data\" message with {len(data_items)} items", file=sys.stderr)
                updated_keys_in_batch = []
                for item_index, item in enumerate(data_items):
                    if not isinstance(item, dict):
                        logger.warning(f"[MsgID:{current_message_id}] Skipping non-dict data item #{item_index}: {item}")
                        continue
                    
                    # Extract service and content
                    service = item.get("service")
                    content_list = item.get("content", [])
                    
                    if service == "LEVELONE_OPTIONS" and content_list:
                        logger.info(f"[MsgID:{current_message_id}] Processing LEVELONE_OPTIONS data with {len(content_list)} content items.")
                        print(f"STREAMING_MANAGER: Processing LEVELONE_OPTIONS data with {len(content_list)} content items", file=sys.stderr)
                        
                        for content_item in content_list:
                            if not isinstance(content_item, dict):
                                logger.warning(f"[MsgID:{current_message_id}] Skipping non-dict content item: {content_item}")
                                continue
                            
                            # Get the contract key
                            contract_key = content_item.get("key")
                            if not contract_key:
                                logger.warning(f"[MsgID:{current_message_id}] Content item missing key: {content_item}")
                                continue
                            
                            # Normalize the contract key for consistent matching
                            normalized_key = normalize_contract_key(contract_key)
                            logger.debug(f"[MsgID:{current_message_id}] Processing contract: {contract_key} (normalized: {normalized_key})")
                            
                            # Process fields
                            with self._lock:
                                if normalized_key not in self.latest_data_store:
                                    self.latest_data_store[normalized_key] = {}
                                
                                # Process each field in the content item
                                for field_id, value in content_item.items():
                                    if field_id == "key":
                                        continue  # Skip the key field
                                    
                                    # Map field ID to field name using the field map
                                    # Handle both string and numeric field IDs
                                    if field_id in self.SCHWAB_FIELD_MAP:
                                        field_name = self.SCHWAB_FIELD_MAP[field_id]
                                    else:
                                        try:
                                            numeric_field_id = int(field_id)
                                            if numeric_field_id in self.SCHWAB_FIELD_MAP:
                                                field_name = self.SCHWAB_FIELD_MAP[numeric_field_id]
                                            else:
                                                logger.warning(f"[MsgID:{current_message_id}] Unknown field ID: {field_id}")
                                                continue
                                        except (ValueError, TypeError):
                                            logger.warning(f"[MsgID:{current_message_id}] Non-numeric field ID: {field_id}")
                                            continue
                                    
                                    # Convert value to appropriate type
                                    typed_value = value
                                    if isinstance(value, str):
                                        try:
                                            if "." in value or "e" in value.lower():
                                                typed_value = float(value)
                                            elif value.lstrip("-").isdigit():
                                                typed_value = int(value)
                                        except ValueError:
                                            # Keep as string if conversion fails
                                            pass
                                    
                                    # Special logging for price fields
                                    if field_name in ["bidPrice", "askPrice", "lastPrice"]:
                                        old_value = self.latest_data_store[normalized_key].get(field_name)
                                        logger.info(f"[MsgID:{current_message_id}] PRICE UPDATE: {normalized_key}.{field_name}: {old_value} -> {typed_value}")
                                        print(f"STREAMING_MANAGER: PRICE UPDATE: {normalized_key}.{field_name}: {old_value} -> {typed_value}", file=sys.stderr)
                                    
                                    # Update the data store
                                    self.latest_data_store[normalized_key][field_name] = typed_value
                                    
                                    # Add to updated keys list if not already there
                                    if normalized_key not in updated_keys_in_batch:
                                        updated_keys_in_batch.append(normalized_key)
                
                if updated_keys_in_batch:
                    logger.info(f"[MsgID:{current_message_id}] Updated {len(updated_keys_in_batch)} contracts in this batch.")
                    print(f"STREAMING_MANAGER: Updated {len(updated_keys_in_batch)} contracts in this batch", file=sys.stderr)
                    # Log a sample of the updated contracts
                    for key in updated_keys_in_batch[:3]:
                        with self._lock:
                            if key in self.latest_data_store:
                                data = self.latest_data_store[key]
                                price_info = {
                                    "bidPrice": data.get("bidPrice", "N/A"),
                                    "askPrice": data.get("askPrice", "N/A"),
                                    "lastPrice": data.get("lastPrice", "N/A")
                                }
                                logger.info(f"[MsgID:{current_message_id}] Updated contract {key} price data: {price_info}")
                                print(f"STREAMING_MANAGER: Updated contract {key} price data: {price_info}", file=sys.stderr)
            
            elif "notify" in message_dict:
                # Handle notification messages
                notify_items = message_dict.get("notify", [])
                logger.info(f"[MsgID:{current_message_id}] Received notification with {len(notify_items)} items.")
                print(f"STREAMING_MANAGER: Received notification with {len(notify_items)} items", file=sys.stderr)
                for notify_item in notify_items:
                    if isinstance(notify_item, dict):
                        heartbeat = notify_item.get("heartbeat")
                        if heartbeat:
                            logger.debug(f"[MsgID:{current_message_id}] Received heartbeat: {heartbeat}")
                        else:
                            logger.info(f"[MsgID:{current_message_id}] Received notification: {notify_item}")
                            print(f"STREAMING_MANAGER: Received notification: {notify_item}", file=sys.stderr)
            
            elif "response" in message_dict:
                # Handle response messages
                response_items = message_dict.get("response", [])
                logger.info(f"[MsgID:{current_message_id}] Received response with {len(response_items)} items.")
                print(f"STREAMING_MANAGER: Received response with {len(response_items)} items", file=sys.stderr)
                for response_item in response_items:
                    if isinstance(response_item, dict):
                        service = response_item.get("service")
                        command = response_item.get("command")
                        content = response_item.get("content")
                        logger.info(f"[MsgID:{current_message_id}] Response for {service}/{command}: {content}")
                        print(f"STREAMING_MANAGER: Response for {service}/{command}: {content}", file=sys.stderr)
            
            else:
                # Handle other message types
                logger.warning(f"[MsgID:{current_message_id}] Unhandled message type: {message_dict.keys()}")
                print(f"STREAMING_MANAGER: Unhandled message type: {message_dict.keys()}", file=sys.stderr)
        
        except Exception as e:
            logger.error(f"[MsgID:{current_message_id}] Error processing message: {e}", exc_info=True)
            print(f"STREAMING_MANAGER: Error processing message: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    def start_streaming(self, option_keys):
        """
        Start streaming for the given option keys.
        
        Args:
            option_keys: List or set of option contract keys to stream
        
        Returns:
            bool: True if streaming started successfully, False otherwise
        """
        print(f"STREAMING_MANAGER: start_streaming called with {len(option_keys)} option keys at {datetime.datetime.now()}", file=sys.stderr)
        logger.info(f"start_streaming called with {len(option_keys)} option keys")
        
        with self._lock:
            if self.is_running:
                logger.warning("start_streaming called but streaming is already running. Stopping first.")
                print(f"STREAMING_MANAGER: Streaming is already running. Stopping first", file=sys.stderr)
                self.stop_streaming()
            
            self.status_message = "Stream: Starting..."
            self.error_message = None
            self.is_running = True
            self.latest_data_store = {}  # Clear any previous data
        
        try:
            # Convert option_keys to a tuple to ensure it's hashable for thread args
            option_keys_tuple = tuple(option_keys)
            
            # Start the streaming thread
            self.stream_thread = threading.Thread(
                target=self._stream_worker,
                args=(option_keys_tuple,),
                name="StreamWorker"
            )
            self.stream_thread.daemon = True  # Make thread a daemon so it exits when main thread exits
            self.stream_thread.start()
            
            logger.info(f"Stream thread started with {len(option_keys_tuple)} option keys")
            print(f"STREAMING_MANAGER: Stream thread started with {len(option_keys_tuple)} option keys", file=sys.stderr)
            return True
        
        except Exception as e:
            logger.error(f"Error starting streaming: {e}", exc_info=True)
            print(f"STREAMING_MANAGER: Error starting streaming: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            with self._lock:
                self.error_message = f"Error starting streaming: {e}"
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False
            return False

    def stop_streaming(self):
        """Stop streaming."""
        print(f"STREAMING_MANAGER: stop_streaming called at {datetime.datetime.now()}", file=sys.stderr)
        logger.info("stop_streaming called")
        
        with self._lock:
            if not self.is_running:
                logger.info("stop_streaming called but streaming is not running")
                print(f"STREAMING_MANAGER: Streaming is not running", file=sys.stderr)
                return
            
            self.status_message = "Stream: Stopping..."
            self.is_running = False
        
        # Wait for the stream thread to exit
        if self.stream_thread and self.stream_thread.is_alive():
            logger.info("Waiting for stream thread to exit...")
            print(f"STREAMING_MANAGER: Waiting for stream thread to exit...", file=sys.stderr)
            self.stream_thread.join(timeout=5)
            if self.stream_thread.is_alive():
                logger.warning("Stream thread did not exit within timeout")
                print(f"STREAMING_MANAGER: Stream thread did not exit within timeout", file=sys.stderr)
        
        with self._lock:
            self.status_message = "Stream: Stopped."
            self.stream_thread = None
        
        logger.info("Streaming stopped")
        print(f"STREAMING_MANAGER: Streaming stopped", file=sys.stderr)

    def get_streaming_data(self):
        """
        Get the latest streaming data.
        
        Returns:
            dict: The latest streaming data
        """
        with self._lock:
            return self.latest_data_store.copy()

    def get_status(self):
        """
        Get the current status of the streaming manager.
        
        Returns:
            dict: The current status
        """
        with self._lock:
            return {
                "is_running": self.is_running,
                "status_message": self.status_message,
                "error_message": self.error_message,
                "subscriptions_count": len(self.current_subscriptions),
                "data_count": len(self.latest_data_store)
            }

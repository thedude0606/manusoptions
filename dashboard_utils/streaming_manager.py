# dashboard_utils/streaming_manager.py

import threading
import time
import logging
import json # Added for JSON parsing
import schwabdev # Import the main schwabdev library
import os
import datetime
import traceback

# Configure basic logging with both console and file handlers
logger = logging.getLogger(__name__) # Use __name__ for module-specific logger
if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    # Console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # File handler
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"streaming_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
logger.setLevel(logging.DEBUG) # Set to DEBUG for verbose logging during diagnosis
logger.info(f"Streaming manager logger initialized. Logging to console and file: {log_file}")

# To get more detailed logs from schwabdev library itself, uncomment the following line:
logging.getLogger("schwabdev").setLevel(logging.DEBUG)

class StreamingManager:
    # Updated field list to ensure we get all price data
    SCHWAB_FIELD_IDS_TO_REQUEST = "0,2,3,4,8,9,10,12,16,17,18,20,21,23,26,28,29,30,31"
    
    SCHWAB_FIELD_MAP = {
        "0": "key", # Symbol/Contract Key (numeric ID)
        "key": "key", # Symbol/Contract Key (string ID, as seen in PDF examples)
        "2": "bidPrice",
        "3": "askPrice",
        "4": "lastPrice",
        "8": "totalVolume",
        "9": "openInterest",
        "10": "volatility", # Implied Volatility
        "12": "expirationYear",
        "16": "bidSize",
        "17": "askSize",
        "18": "lastSize",
        "20": "strikePrice",
        "21": "contractType", # C or P
        "23": "expirationMonth",
        "26": "expirationDay",
        "28": "delta",
        "29": "gamma",
        "30": "theta",
        "31": "vega"
    }

    def __init__(self, schwab_client_getter, account_id_getter):
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

    def _get_schwab_client(self):
        try:
            client = self.schwab_client_getter()
            if not client:
                self.error_message = "Failed to get Schwab client."
                logger.error(self.error_message)
                return None
            logger.debug("_get_schwab_client: Successfully obtained Schwab client.")
            return client
        except Exception as e:
            self.error_message = f"Error obtaining Schwab client: {e}"
            logger.error(self.error_message, exc_info=True) # Log full traceback
            return None

    def _stream_worker(self, option_keys_to_subscribe_tuple):
        option_keys_to_subscribe = set(option_keys_to_subscribe_tuple)
        logger.info(f"_stream_worker started for {len(option_keys_to_subscribe)} keys: {list(option_keys_to_subscribe)[:5]}...")
        
        # Log a sample of the keys to verify format
        for i, key in enumerate(list(option_keys_to_subscribe)[:10]):
            logger.info(f"Sample key {i}: '{key}'")
        
        with self._lock:
            self.status_message = "Stream: Initializing worker..."
            self.error_message = None # Clear previous errors

        schwab_api_client = self._get_schwab_client()
        if not schwab_api_client:
            with self._lock:
                self.status_message = f"Stream: Error - {self.error_message or 'Failed to get Schwab client in worker'}"
                self.is_running = False # Ensure is_running is false if client fails
            logger.error("_stream_worker: Failed to get Schwab client. Worker terminating.")
            return

        account_hash = self.account_id_getter()
        if account_hash:
            logger.info(f"_stream_worker: Account hash provided (first 4 chars for log): {str(account_hash)[:4]}...")
        else:
            logger.info("_stream_worker: No account hash provided; not strictly required for LEVELONE_OPTIONS.")

        try:
            with self._lock:
                self.stream_client = schwab_api_client.stream
            logger.info("_stream_worker: Schwab stream object obtained via client.stream")

            if not option_keys_to_subscribe:
                logger.warning("_stream_worker: No symbols to subscribe.")
                with self._lock:
                    self.status_message = "Stream: No symbols to subscribe."
                    self.is_running = False
                return

            # Define a custom handler that logs raw messages before processing
            def custom_stream_handler(raw_message):
                try:
                    # Log the raw message to the dedicated raw stream log file
                    self.raw_stream_logger.debug(f"RAW MESSAGE: {raw_message}")
                    
                    # Process the message with our regular handler
                    self._handle_stream_message(raw_message)
                except Exception as e:
                    logger.error(f"Error in custom_stream_handler: {e}", exc_info=True)
            
            logger.info("_stream_worker: Starting schwabdev's stream listener with custom handler...")
            self.stream_client.start(custom_stream_handler)
            logger.info("_stream_worker: schwabdev's stream_client.start() called. Listener should be active in its own thread.")

            time.sleep(3) # Allow time for connection
            logger.info("_stream_worker: Waited 3s for connection, proceeding with subscriptions.")

            # Format contract keys properly for streaming
            formatted_keys = []
            for key in option_keys_to_subscribe:
                # Ensure the key is properly formatted with spaces for streaming
                # Example: "AAPL_051720C150" should be "AAPL  051720C00150000"
                formatted_key = self._format_contract_key_for_streaming(key)
                formatted_keys.append(formatted_key)
            
            # Log the original and formatted keys for debugging
            logger.info(f"_stream_worker: Original keys sample: {list(option_keys_to_subscribe)[:5]}")
            logger.info(f"_stream_worker: Formatted keys sample: {formatted_keys[:5]}")
            
            keys_str = ",".join(formatted_keys)
            fields_str = self.SCHWAB_FIELD_IDS_TO_REQUEST
            
            subscription_payload = self.stream_client.level_one_options(keys_str, fields_str, command="ADD")
            logger.info(f"_stream_worker: Preparing to send LEVELONE_OPTIONS subscription. Keys count: {len(formatted_keys)}. Fields: {fields_str}.")
            logger.debug(f"_stream_worker: Full subscription payload being sent: {json.dumps(subscription_payload)}")
            
            # Log the full payload to the raw stream log
            self.raw_stream_logger.debug(f"SENDING SUBSCRIPTION: {json.dumps(subscription_payload)}")
            
            self.stream_client.send(subscription_payload)
            logger.info(f"_stream_worker: Subscription payload sent for {len(formatted_keys)} keys.")

            with self._lock:
                self.current_subscriptions = set(formatted_keys)
                self.status_message = f"Stream: Subscriptions sent for {len(self.current_subscriptions)} contracts. Monitoring..."
            
            logger.info("_stream_worker: Subscriptions sent. Now entering main monitoring loop.")
            loop_counter = 0
            while True:
                with self._lock:
                    if not self.is_running:
                        logger.info("_stream_worker: self.is_running is False. Exiting monitoring loop.")
                        break
                
                if loop_counter % 20 == 0: # Log every 10 seconds (0.5 * 20)
                    logger.debug(f"_stream_worker: Monitoring loop active. is_running: {self.is_running}. Subscriptions: {len(self.current_subscriptions)}")
                    
                    # Every 10 seconds, check if we've received any data
                    with self._lock:
                        data_count = len(self.latest_data_store)
                        if data_count > 0:
                            logger.info(f"_stream_worker: Currently storing data for {data_count} contracts.")
                            # Log a sample of the stored data
                            sample_keys = list(self.latest_data_store.keys())[:3]
                            for key in sample_keys:
                                data = self.latest_data_store[key]
                                logger.info(f"Sample data for {key}: Last={data.get('lastPrice')}, Bid={data.get('bidPrice')}, Ask={data.get('askPrice')}")
                        else:
                            logger.warning("_stream_worker: No data received from stream yet.")
                
                time.sleep(0.5) 
                loop_counter +=1
            logger.info("_stream_worker: Exited monitoring loop.")

        except Exception as e:
            logger.error(f"Error in _stream_worker's main try block: {e}", exc_info=True)
            with self._lock:
                self.error_message = f"Stream worker error: {e}"
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False # Critical: ensure is_running is set to false on error
        finally:
            logger.info("_stream_worker: Reached finally block.")
            with self._lock:
                if self.is_running: 
                    logger.warning("_stream_worker in finally, but self.is_running is still true. Forcing to False.")
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
                    active_schwab_stream_client.stop()
                    logger.info("_stream_worker's finally block: schwabdev stream client stop() called.")
                except Exception as e_stop:
                    logger.error(f"_stream_worker's finally block: Error stopping schwabdev stream client: {e_stop}", exc_info=True)
            else:
                logger.info("_stream_worker's finally block: Schwabdev stream client not active/stoppable or already None.")
            
            with self._lock:
                self.stream_client = None
            logger.info("_stream_worker finished.")

    def _format_contract_key_for_streaming(self, contract_key):
        """
        Format contract key for streaming according to Schwab API requirements.
        
        The Schwab streaming API requires option symbols in a specific format:
        - Underlying symbol (padded with spaces to 6 chars)
        - Expiration date (YYMMDD)
        - Call/Put indicator (C/P)
        - Strike price (padded with leading zeros to 8 chars)
        
        Example: "AAPL  240621C00190000" for Apple $190 call expiring June 21, 2024
        """
        try:
            # Log the original contract key
            logger.debug(f"Formatting contract key: {contract_key}")
            
            # Check if the key is already in the correct format
            if len(contract_key) >= 21 and ' ' in contract_key:
                logger.debug(f"Contract key appears to be already formatted: {contract_key}")
                return contract_key
            
            # Extract components using regex
            import re
            # Pattern to match: symbol_YYMMDDCNNN or symbol_YYMMDDpNNN
            pattern = r'([A-Z]+)_(\d{6})([CP])(\d+(?:\.\d+)?)'
            match = re.match(pattern, contract_key)
            
            if not match:
                # Try alternative pattern for Schwab's standard format
                # Example: AAPL240621C00190000
                alt_pattern = r'([A-Z]+)(\d{6})([CP])(\d{8})'
                match = re.match(alt_pattern, contract_key)
                
                if not match:
                    logger.warning(f"Could not parse contract key: {contract_key}, using as-is")
                    return contract_key
            
            symbol, exp_date, cp_flag, strike = match.groups()
            
            # Format strike price (multiply by 1000 if needed and pad with leading zeros)
            strike_float = float(strike)
            strike_int = int(strike_float * 1000) if strike_float < 1000 else int(strike_float)
            strike_padded = f"{strike_int:08d}"
            
            # Format symbol (pad with spaces to 6 chars)
            symbol_padded = f"{symbol:<6}"
            
            # Combine all parts
            formatted_key = f"{symbol_padded}{exp_date}{cp_flag}{strike_padded}"
            logger.debug(f"Formatted contract key: {contract_key} -> {formatted_key}")
            
            return formatted_key
        except Exception as e:
            logger.error(f"Error formatting contract key {contract_key}: {e}", exc_info=True)
            return contract_key

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
                    return
            elif isinstance(raw_message, dict):
                message_dict = raw_message
                logger.debug(f"[MsgID:{current_message_id}] Received dict message: {json.dumps(message_dict)[:1000]}...")
            else:
                logger.warning(f"[MsgID:{current_message_id}] Unexpected message type: {type(raw_message)}. Raw: {raw_message}")
                return
            
            # Log the full message for debugging
            self.raw_stream_logger.debug(f"[MsgID:{current_message_id}] PARSED: {json.dumps(message_dict)}")

            if "data" in message_dict:
                data_items = message_dict.get("data", [])
                logger.info(f"[MsgID:{current_message_id}] Identified \"data\" message with {len(data_items)} items.")
                updated_keys_in_batch = []
                for item_index, item in enumerate(data_items):
                    if not isinstance(item, dict):
                        logger.warning(f"[MsgID:{current_message_id}] Skipping non-dict data item #{item_index}: {item}")
                        continue
                    
                    # Log the service type for all data items
                    service_type = item.get("service", "UNKNOWN")
                    logger.info(f"[MsgID:{current_message_id}] Data item #{item_index} service: {service_type}")
                    
                    if service_type != "LEVELONE_OPTIONS" or "content" not in item:
                        logger.warning(f"[MsgID:{current_message_id}] Skipping non-LEVELONE_OPTIONS or malformed data item #{item_index}: {item}")
                        continue
                    
                    content_list = item.get("content", [])
                    logger.info(f"[MsgID:{current_message_id}] Processing {len(content_list)} content items for LEVELONE_OPTIONS")
                    
                    for content_index, contract_data_from_stream in enumerate(content_list):
                        if not isinstance(contract_data_from_stream, dict):
                            logger.warning(f"[MsgID:{current_message_id}] Skipping non-dict contract_data #{content_index}: {contract_data_from_stream}")
                            continue
                        
                        # Log the raw contract data for debugging
                        self.raw_stream_logger.debug(f"[MsgID:{current_message_id}] RAW CONTRACT DATA: {json.dumps(contract_data_from_stream)}")
                        
                        contract_key = contract_data_from_stream.get("key")
                        if not contract_key:
                            contract_key = contract_data_from_stream.get("0")
                        
                        if not contract_key:
                            logger.warning(f"[MsgID:{current_message_id}] Skipping contract_data with missing contract key (tried \"key\" and \"0\"): {contract_data_from_stream}")
                            continue
                        
                        # Prepare new data from the current stream message
                        new_update_data = {}
                        for field_id, value in contract_data_from_stream.items():
                            if field_id in self.SCHWAB_FIELD_MAP:
                                field_name = self.SCHWAB_FIELD_MAP[field_id]
                                new_update_data[field_name] = value
                                
                                # Log each field value for debugging
                                logger.debug(f"[MsgID:{current_message_id}] Field {field_id} -> {field_name}: {value}")
                            # Handle numeric field IDs as strings
                            elif field_id.isdigit() and int(field_id) in self.SCHWAB_FIELD_MAP:
                                field_name = self.SCHWAB_FIELD_MAP[int(field_id)]
                                new_update_data[field_name] = value
                                
                                # Log each field value for debugging
                                logger.debug(f"[MsgID:{current_message_id}] Field {field_id} (numeric) -> {field_name}: {value}")
                        
                        if "key" not in new_update_data: # Ensure the contract key itself is in the update if it was mapped from "0"
                            new_update_data["key"] = contract_key
                        
                        new_update_data["lastUpdated"] = time.time()
                        
                        # Log the presence of last, bid, ask values for debugging
                        if "lastPrice" in new_update_data or "bidPrice" in new_update_data or "askPrice" in new_update_data:
                            logger.info(f"[MsgID:{current_message_id}] Received price data for {contract_key}: " +
                                      f"Last: {new_update_data.get('lastPrice', 'N/A')}, " +
                                      f"Bid: {new_update_data.get('bidPrice', 'N/A')}, " +
                                      f"Ask: {new_update_data.get('askPrice', 'N/A')}")
                        
                        logger.info(f"[MsgID:{current_message_id}] Processing update for key \"{contract_key}\". New data: {new_update_data}")
                        updated_keys_in_batch.append(contract_key)
                        
                        # Update the data store with the new data
                        with self._lock:
                            if contract_key in self.latest_data_store:
                                # Update existing data
                                self.latest_data_store[contract_key].update(new_update_data)
                                logger.debug(f"[MsgID:{current_message_id}] Updated existing data for {contract_key}")
                            else:
                                # Create new entry
                                self.latest_data_store[contract_key] = new_update_data
                                logger.debug(f"[MsgID:{current_message_id}] Created new data entry for {contract_key}")
                
                if updated_keys_in_batch:
                    logger.info(f"[MsgID:{current_message_id}] Updated {len(updated_keys_in_batch)} contracts in this batch.")
                else:
                    logger.warning(f"[MsgID:{current_message_id}] No contracts were updated in this batch.")
            
            elif "notify" in message_dict:
                notify_items = message_dict.get("notify", [])
                logger.info(f"[MsgID:{current_message_id}] Received \"notify\" message with {len(notify_items)} items.")
                
                for notify_index, notify_item in enumerate(notify_items):
                    if not isinstance(notify_item, dict):
                        logger.warning(f"[MsgID:{current_message_id}] Skipping non-dict notify item #{notify_index}: {notify_item}")
                        continue
                    
                    heartbeat = notify_item.get("heartbeat")
                    if heartbeat is not None:
                        logger.debug(f"[MsgID:{current_message_id}] Received heartbeat: {heartbeat}")
                        continue
                    
                    service = notify_item.get("service")
                    if service:
                        logger.info(f"[MsgID:{current_message_id}] Received service notification for {service}")
                    
                    command = notify_item.get("command")
                    if command:
                        logger.info(f"[MsgID:{current_message_id}] Received command notification: {command}")
            
            elif "response" in message_dict:
                response_items = message_dict.get("response", [])
                logger.info(f"[MsgID:{current_message_id}] Received \"response\" message with {len(response_items)} items.")
                
                for response_index, response_item in enumerate(response_items):
                    if not isinstance(response_item, dict):
                        logger.warning(f"[MsgID:{current_message_id}] Skipping non-dict response item #{response_index}: {response_item}")
                        continue
                    
                    service = response_item.get("service")
                    command = response_item.get("command")
                    content = response_item.get("content")
                    
                    if service and command:
                        logger.info(f"[MsgID:{current_message_id}] Response for service {service}, command {command}")
                        
                        if content:
                            logger.debug(f"[MsgID:{current_message_id}] Response content: {content}")
                            
                            # Check for errors in the response
                            if isinstance(content, dict) and content.get("code") != 0:
                                error_msg = f"Error in response: {content.get('msg', 'Unknown error')}"
                                logger.error(f"[MsgID:{current_message_id}] {error_msg}")
                                with self._lock:
                                    self.error_message = error_msg
            else:
                logger.warning(f"[MsgID:{current_message_id}] Unrecognized message format: {message_dict.keys()}")
                
        except Exception as e:
            logger.error(f"[MsgID:{current_message_id}] Error processing stream message: {e}", exc_info=True)

    def start_streaming(self, option_keys):
        """Start streaming for the given option contract keys."""
        logger.info(f"start_streaming called with {len(option_keys)} option keys.")
        
        with self._lock:
            if self.is_running:
                logger.warning("start_streaming: Already running. Call stop_streaming first.")
                return False, "Streaming is already active. Stop first before starting a new stream."
            
            self.is_running = True
            self.status_message = "Stream: Starting..."
            self.error_message = None
        
        try:
            # Start in a new thread
            self.stream_thread = threading.Thread(
                target=self._stream_worker,
                args=(option_keys,),
                daemon=True
            )
            self.stream_thread.start()
            logger.info(f"start_streaming: Started stream_thread for {len(option_keys)} option keys.")
            return True, None
        except Exception as e:
            with self._lock:
                self.is_running = False
                self.error_message = f"Failed to start streaming: {e}"
                self.status_message = f"Stream: Error - {self.error_message}"
            logger.error(f"start_streaming: Error starting stream: {e}", exc_info=True)
            return False, str(e)

    def stop_streaming(self):
        """Stop any active streaming."""
        logger.info("stop_streaming called.")
        
        with self._lock:
            if not self.is_running:
                logger.info("stop_streaming: Not currently running.")
                return True, None
            
            self.is_running = False
            self.status_message = "Stream: Stopping..."
        
        # Wait for thread to terminate (with timeout)
        if self.stream_thread and self.stream_thread.is_alive():
            logger.info("stop_streaming: Waiting for stream thread to terminate...")
            self.stream_thread.join(timeout=5.0)
            if self.stream_thread.is_alive():
                logger.warning("stop_streaming: Stream thread did not terminate within timeout.")
            else:
                logger.info("stop_streaming: Stream thread terminated successfully.")
        
        with self._lock:
            self.stream_thread = None
            if self.status_message == "Stream: Stopping...":
                self.status_message = "Stream: Stopped."
        
        return True, None

    def get_status(self):
        """Get the current streaming status."""
        with self._lock:
            return {
                "is_running": self.is_running,
                "status_message": self.status_message,
                "error_message": self.error_message,
                "subscription_count": len(self.current_subscriptions),
                "data_count": len(self.latest_data_store)
            }

    def get_streaming_data(self):
        """Get a copy of the current streaming data."""
        with self._lock:
            # Return a deep copy to avoid threading issues
            return {k: v.copy() if isinstance(v, dict) else v for k, v in self.latest_data_store.items()}

    def get_streaming_data_for_key(self, contract_key):
        """Get streaming data for a specific contract key."""
        with self._lock:
            data = self.latest_data_store.get(contract_key)
            if data:
                return data.copy()  # Return a copy to avoid threading issues
            return None

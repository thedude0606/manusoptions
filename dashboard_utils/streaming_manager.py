import threading
import time
import logging
import json # Added for JSON parsing
import schwabdev # Import the main schwabdev library
import os
import datetime
import traceback
import sys
from queue import Queue, Empty

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
        self.data_count = 0
        self.last_data_update = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        self.message_queue = Queue()
        self.heartbeat_thread = None
        self.last_heartbeat = None
        self.heartbeat_interval = 30  # seconds
        self.subscriptions_count = 0
        
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

    def _handle_stream_message(self, message):
        """
        Process incoming stream messages and update the data store.
        
        Args:
            message: The raw message from the stream
        """
        try:
            # Log the raw message to the dedicated raw stream log file
            self.raw_stream_logger.debug(f"RAW MESSAGE: {message}")
            
            # Increment message counter
            with self._lock:
                self.message_counter += 1
                
            # Check if this is a heartbeat message
            if isinstance(message, dict) and message.get("service") == "ADMIN" and message.get("command") == "HEARTBEAT":
                with self._lock:
                    self.last_heartbeat = datetime.datetime.now()
                    logger.debug(f"Received heartbeat message: {message}")
                    print(f"STREAMING_MANAGER: Received heartbeat message", file=sys.stderr)
                return
                
            # Check if this is a response to our subscription
            if isinstance(message, dict) and message.get("response") and message.get("service") == "LEVELONE_OPTIONS":
                with self._lock:
                    response_code = message.get("response", {}).get("code")
                    if response_code == 0:  # Success
                        self.status_message = "Stream: Subscription successful"
                        self.subscriptions_count = len(self.current_subscriptions)
                        logger.info(f"Subscription successful for {self.subscriptions_count} contracts")
                        print(f"STREAMING_MANAGER: Subscription successful for {self.subscriptions_count} contracts", file=sys.stderr)
                    else:
                        error_msg = message.get("response", {}).get("msg", "Unknown error")
                        self.error_message = f"Subscription error: {error_msg}"
                        self.status_message = f"Stream: Error - {self.error_message}"
                        logger.error(f"Subscription error: {message}")
                        print(f"STREAMING_MANAGER: Subscription error: {error_msg}", file=sys.stderr)
                return
                
            # Process data messages
            if isinstance(message, dict) and message.get("data"):
                data_list = message.get("data", [])
                if not data_list:
                    return
                    
                with self._lock:
                    for data_item in data_list:
                        # Extract the contract key and content
                        content = data_item.get("content", {})
                        if not content:
                            continue
                            
                        # Process each content item
                        for key, fields in content.items():
                            # Normalize the key for consistent matching
                            normalized_key = normalize_contract_key(key)
                            
                            # Create or update the data entry
                            if normalized_key not in self.latest_data_store:
                                self.latest_data_store[normalized_key] = {}
                                
                            # Update fields
                            for field_id, value in fields.items():
                                field_name = self.SCHWAB_FIELD_MAP.get(field_id)
                                if field_name:
                                    self.latest_data_store[normalized_key][field_name] = value
                    
                    # Update data count and timestamp
                    self.data_count = len(self.latest_data_store)
                    self.last_data_update = datetime.datetime.now()
                    
                    # Update status message
                    self.status_message = f"Stream: Receiving data ({self.data_count} contracts)"
                    
                    # Log data update
                    if self.message_counter % 10 == 0:  # Log every 10 messages to avoid excessive logging
                        logger.info(f"Updated data store with {self.data_count} contracts. Last update: {self.last_data_update}")
                        print(f"STREAMING_MANAGER: Updated data store with {self.data_count} contracts", file=sys.stderr)
                        
        except Exception as e:
            logger.error(f"Error processing stream message: {e}", exc_info=True)
            print(f"STREAMING_MANAGER: Error processing stream message: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            with self._lock:
                self.error_message = f"Stream message processing error: {e}"

    def _message_processor(self):
        """
        Process messages from the queue to avoid blocking the stream handler.
        """
        logger.info("Message processor thread started")
        print(f"STREAMING_MANAGER: Message processor thread started", file=sys.stderr)
        
        while self.is_running:
            try:
                # Get a message from the queue with a timeout
                try:
                    message = self.message_queue.get(timeout=1.0)
                    self._handle_stream_message(message)
                    self.message_queue.task_done()
                except Empty:
                    # No message in queue, just continue
                    pass
                    
            except Exception as e:
                logger.error(f"Error in message processor: {e}", exc_info=True)
                print(f"STREAMING_MANAGER: Error in message processor: {e}", file=sys.stderr)
                time.sleep(1)  # Sleep briefly on error
                
        logger.info("Message processor thread stopped")
        print(f"STREAMING_MANAGER: Message processor thread stopped", file=sys.stderr)

    def _heartbeat_monitor(self):
        """
        Monitor heartbeats and reconnect if necessary.
        """
        logger.info("Heartbeat monitor thread started")
        print(f"STREAMING_MANAGER: Heartbeat monitor thread started", file=sys.stderr)
        
        while self.is_running:
            try:
                with self._lock:
                    if self.last_heartbeat:
                        time_since_heartbeat = (datetime.datetime.now() - self.last_heartbeat).total_seconds()
                        if time_since_heartbeat > self.heartbeat_interval * 2:
                            logger.warning(f"No heartbeat received for {time_since_heartbeat} seconds. Reconnecting...")
                            print(f"STREAMING_MANAGER: No heartbeat received for {time_since_heartbeat} seconds. Reconnecting...", file=sys.stderr)
                            self._reconnect()
                    
                    # Also check if we've received any data
                    if self.last_data_update:
                        time_since_data = (datetime.datetime.now() - self.last_data_update).total_seconds()
                        if time_since_data > 60 and self.subscriptions_count > 0:  # If no data for 1 minute and we have subscriptions
                            logger.warning(f"No data received for {time_since_data} seconds. Reconnecting...")
                            print(f"STREAMING_MANAGER: No data received for {time_since_data} seconds. Reconnecting...", file=sys.stderr)
                            self._reconnect()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}", exc_info=True)
                print(f"STREAMING_MANAGER: Error in heartbeat monitor: {e}", file=sys.stderr)
                time.sleep(10)  # Sleep longer on error
                
        logger.info("Heartbeat monitor thread stopped")
        print(f"STREAMING_MANAGER: Heartbeat monitor thread stopped", file=sys.stderr)

    def _reconnect(self):
        """
        Attempt to reconnect the stream.
        """
        with self._lock:
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                logger.error(f"Maximum reconnect attempts ({self.max_reconnect_attempts}) reached. Giving up.")
                print(f"STREAMING_MANAGER: Maximum reconnect attempts reached. Giving up.", file=sys.stderr)
                self.error_message = f"Maximum reconnect attempts ({self.max_reconnect_attempts}) reached"
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False
                return False
                
            self.reconnect_attempts += 1
            logger.info(f"Attempting to reconnect (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            print(f"STREAMING_MANAGER: Attempting to reconnect (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})", file=sys.stderr)
            self.status_message = f"Stream: Reconnecting (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})..."
            
            # Save current subscriptions
            current_subs = list(self.current_subscriptions)
            
            # Stop the current stream
            self._stop_stream_internal()
            
            # Wait before reconnecting
            time.sleep(self.reconnect_delay)
            
            # Restart with the same subscriptions
            if current_subs:
                return self.start_stream(current_subs)
            else:
                logger.warning("No subscriptions to reconnect with")
                print(f"STREAMING_MANAGER: No subscriptions to reconnect with", file=sys.stderr)
                self.status_message = "Stream: No subscriptions to reconnect with"
                self.is_running = False
                return False

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
            self.reconnect_attempts = 0  # Reset reconnect attempts

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

            # Define a custom handler that queues messages for processing
            def custom_stream_handler(raw_message):
                try:
                    # Log the raw message to the dedicated raw stream log file
                    self.raw_stream_logger.debug(f"RAW MESSAGE: {raw_message}")
                    print(f"STREAMING_MANAGER: Received raw message: {str(raw_message)[:100]}...", file=sys.stderr)
                    
                    # Queue the message for processing
                    self.message_queue.put(raw_message)
                except Exception as e:
                    logger.error(f"Error in custom_stream_handler: {e}", exc_info=True)
                    print(f"STREAMING_MANAGER: Error in custom_stream_handler: {e}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
            
            # Start the message processor thread
            message_processor_thread = threading.Thread(
                target=self._message_processor,
                name="MessageProcessor"
            )
            message_processor_thread.daemon = True
            message_processor_thread.start()
            
            # Start the heartbeat monitor thread
            heartbeat_thread = threading.Thread(
                target=self._heartbeat_monitor,
                name="HeartbeatMonitor"
            )
            heartbeat_thread.daemon = True
            heartbeat_thread.start()
            
            with self._lock:
                self.heartbeat_thread = heartbeat_thread
            
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
                self.subscriptions_count = len(self.current_subscriptions)
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
                    self.status_message = "Stream: Stopped due to unknown error."

    def _stop_stream_internal(self):
        """
        Internal method to stop the stream without locking.
        """
        logger.info("_stop_stream_internal: Stopping stream...")
        print(f"STREAMING_MANAGER: _stop_stream_internal: Stopping stream...", file=sys.stderr)
        
        # Set status first to avoid race conditions
        self.status_message = "Stream: Stopping..."
        self.is_running = False
        
        # Stop the stream client if it exists
        if self.stream_client:
            try:
                logger.info("_stop_stream_internal: Calling stream_client.stop()...")
                print(f"STREAMING_MANAGER: Calling stream_client.stop()...", file=sys.stderr)
                self.stream_client.stop()
                logger.info("_stop_stream_internal: stream_client.stop() called successfully.")
                print(f"STREAMING_MANAGER: stream_client.stop() called successfully", file=sys.stderr)
            except Exception as e:
                logger.error(f"Error stopping stream client: {e}", exc_info=True)
                print(f"STREAMING_MANAGER: Error stopping stream client: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
        
        # Clear data and reset state
        self.stream_client = None
        self.current_subscriptions = set()
        self.subscriptions_count = 0
        self.status_message = "Stream: Stopped."
        
        logger.info("_stop_stream_internal: Stream stopped.")
        print(f"STREAMING_MANAGER: Stream stopped", file=sys.stderr)

    def start_stream(self, option_keys):
        """
        Start streaming data for the given option keys.
        
        Args:
            option_keys: List or set of option contract keys to stream
            
        Returns:
            bool: True if stream started successfully, False otherwise
        """
        print(f"STREAMING_MANAGER: start_stream called with {len(option_keys)} keys at {datetime.datetime.now()}", file=sys.stderr)
        logger.info(f"start_stream: Called with {len(option_keys)} keys")
        
        with self._lock:
            # If already running, stop first
            if self.is_running:
                logger.info("start_stream: Stream is already running. Stopping first.")
                print(f"STREAMING_MANAGER: Stream is already running. Stopping first", file=sys.stderr)
                self._stop_stream_internal()
            
            # Reset state
            self.is_running = True
            self.error_message = None
            self.status_message = "Stream: Starting..."
            self.message_counter = 0
            self.data_count = 0
            self.last_data_update = None
            self.last_heartbeat = datetime.datetime.now()  # Initialize with current time
            
            # Start the stream thread
            self.stream_thread = threading.Thread(
                target=self._stream_worker,
                args=(tuple(option_keys),),  # Convert to tuple for thread safety
                name="StreamWorker"
            )
            self.stream_thread.daemon = True
            self.stream_thread.start()
            
            logger.info(f"start_stream: Stream thread started for {len(option_keys)} keys")
            print(f"STREAMING_MANAGER: Stream thread started for {len(option_keys)} keys", file=sys.stderr)
            return True

    def stop_stream(self):
        """
        Stop the current stream.
        
        Returns:
            bool: True if stream was stopped, False if no stream was running
        """
        print(f"STREAMING_MANAGER: stop_stream called at {datetime.datetime.now()}", file=sys.stderr)
        logger.info("stop_stream: Called")
        
        with self._lock:
            if not self.is_running:
                logger.info("stop_stream: Stream is not running.")
                print(f"STREAMING_MANAGER: Stream is not running", file=sys.stderr)
                return False
                
            self._stop_stream_internal()
            return True

    def get_latest_data(self):
        """
        Get the latest data from the stream.
        
        Returns:
            dict: The latest data store
        """
        with self._lock:
            # Return a copy to avoid thread safety issues
            return self.latest_data_store.copy()

    def get_status(self):
        """
        Get the current status of the stream.
        
        Returns:
            dict: Status information
        """
        with self._lock:
            status = {
                "is_running": self.is_running,
                "status_message": self.status_message,
                "error_message": self.error_message,
                "subscriptions_count": len(self.current_subscriptions),
                "data_count": len(self.latest_data_store),
                "message_counter": self.message_counter
            }
            
            if self.last_data_update:
                status["last_data_update"] = self.last_data_update.isoformat()
                
            if self.last_heartbeat:
                status["last_heartbeat"] = self.last_heartbeat.isoformat()
                
            return status

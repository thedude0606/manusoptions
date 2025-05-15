# dashboard_utils/streaming_manager.py

import threading
import time
import logging
import json # Added for JSON parsing
import schwabdev # Import the main schwabdev library

# Configure basic logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(threadName)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class StreamingManager:
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
        self._lock = threading.Lock()
        logger.info("StreamingManager initialized.")

    def _get_schwab_client(self):
        try:
            client = self.schwab_client_getter()
            if not client:
                self.error_message = "Failed to get Schwab client."
                logger.error(self.error_message)
                return None
            return client
        except Exception as e:
            self.error_message = f"Error obtaining Schwab client: {e}"
            logger.error(self.error_message)
            return None

    def _stream_worker(self, option_keys_to_subscribe_tuple):
        option_keys_to_subscribe = set(option_keys_to_subscribe_tuple)
        logger.info(f"Stream worker started for {len(option_keys_to_subscribe)} keys.")
        with self._lock:
            self.status_message = "Stream: Initializing..."
            self.error_message = None
            # self.is_running is already True, set by start_stream

        schwab_api_client = self._get_schwab_client()
        if not schwab_api_client:
            with self._lock:
                self.status_message = f"Stream: Error - {self.error_message or 'Failed to get Schwab client'}"
                self.is_running = False # Critical failure, stop
            logger.error("Stream worker: Failed to get Schwab client. Worker terminating.")
            return

        account_hash = self.account_id_getter()
        if account_hash:
            logger.info(f"Account hash provided (first 4 chars for log): {str(account_hash)[:4]}...")
        else:
            logger.info("No account hash provided; not strictly required for LEVELONE_OPTIONS.")

        try:
            # Assign to self.stream_client under lock for thread-safety if accessed elsewhere, though primarily used in this thread
            with self._lock:
                self.stream_client = schwab_api_client.stream
            logger.info("Schwab stream object obtained via client.stream")

            if not option_keys_to_subscribe:
                logger.info("Stream worker: No symbols to subscribe.")
                with self._lock:
                    self.status_message = "Stream: No symbols to subscribe."
                    self.is_running = False # Nothing to do, stop
                return

            logger.info("Stream worker: Starting schwabdev's stream listener (which runs in its own thread)...")
            self.stream_client.start(self._handle_stream_message)
            logger.info("Stream worker: schwabdev's stream_client.start() called. Listener should be active in its own thread.")

            time.sleep(2) # Give a moment for the connection to establish before sending subscriptions

            keys_str = ",".join(list(option_keys_to_subscribe))
            fields_str = "0,2,7,8,9,10,11,15,16,17,18,19,21,26,27,23,24,25"
            
            logger.info(f"Stream worker: Sending LEVELONE_OPTIONS subscription for keys: {keys_str}")
            self.stream_client.send(self.stream_client.level_one_options(keys_str, fields_str, command="ADD"))

            with self._lock:
                self.current_subscriptions = set(option_keys_to_subscribe)
                self.status_message = f"Stream: Subscriptions sent for {len(self.current_subscriptions)} contracts. Monitoring..."
            
            logger.info("Stream worker: Subscriptions sent. Now entering main monitoring loop to keep this worker alive.")

            while True:
                should_break = False
                with self._lock:
                    if not self.is_running:
                        should_break = True
                
                if should_break:
                    logger.info("Stream worker: self.is_running is False. Exiting monitoring loop.")
                    break
                
                time.sleep(0.5) # Keep the loop from busy-waiting, check stop flag periodically

            logger.info("Stream worker: Exited monitoring loop.")

        except Exception as e:
            logger.error(f"Error in stream worker's main try block: {e}", exc_info=True)
            with self._lock:
                self.error_message = f"Stream error: {e}"
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False # Critical error, ensure manager knows to stop
        finally:
            logger.info("Stream worker: Reached finally block.")
            with self._lock:
                if self.is_running: 
                    logger.warning("Stream worker in finally, but self.is_running is still true. Forcing to False.")
                    self.is_running = False

                if self.error_message:
                    pass # Status already reflects an error
                elif self.status_message == "Stream: Stopping...":
                    self.status_message = "Stream: Stopped."
                elif self.status_message not in ["Stream: Stopped.", "Stream: No symbols to subscribe."]:
                    self.status_message = "Stream: Stopped unexpectedly."
                elif self.status_message in ["Stream: Initializing...", "Stream: Starting..."] and not self.error_message:
                    self.status_message = "Stream: Failed to start or connect."
            
            active_schwab_client = None
            with self._lock:
                active_schwab_client = self.stream_client

            if active_schwab_client and hasattr(active_schwab_client, 'stop') and active_schwab_client.active:
                try:
                    logger.info("Stream worker's finally block: Attempting to stop schwabdev stream client.")
                    active_schwab_client.stop()
                except Exception as e_stop:
                    logger.error(f"Stream worker's finally block: Error stopping schwabdev stream client: {e_stop}")
            
            with self._lock:
                self.stream_client = None # Clear the client reference
            logger.info("Stream worker finished.")

    def _handle_stream_message(self, raw_message):
        logger.debug(f"_handle_stream_message received raw_message (type: {type(raw_message)}): {raw_message}")
        try:
            message_dict = None
            if isinstance(raw_message, str):
                try:
                    message_dict = json.loads(raw_message)
                    logger.debug(f"_handle_stream_message: Parsed JSON: {message_dict}")
                except json.JSONDecodeError as jde:
                    logger.error(f"Failed to decode JSON message: {jde} - Raw Message: {raw_message}")
                    return
            elif isinstance(raw_message, dict): 
                message_dict = raw_message
                logger.debug(f"_handle_stream_message: Received dict directly: {message_dict}")
            else:
                logger.warning(f"Unexpected message type received by handler: {type(raw_message)}. Raw Message: {raw_message}")
                return

            if "data" in message_dict:
                data_items = message_dict.get("data", [])
                logger.debug(f"_handle_stream_message: Processing {len(data_items)} data items.")
                for item_index, item in enumerate(data_items):
                    logger.debug(f"_handle_stream_message: Processing data item #{item_index}: {item}")
                    if not isinstance(item, dict) or item.get("service") != "LEVELONE_OPTIONS" or "content" not in item:
                        logger.warning(f"_handle_stream_message: Skipping non-LEVELONE_OPTIONS or malformed data item: {item}")
                        continue
                    content_list = item.get("content", [])
                    for content_index, contract_data in enumerate(content_list):
                        logger.debug(f"_handle_stream_message: Processing content #{content_index} from item #{item_index}: {contract_data}")
                        if not isinstance(contract_data, dict) or "key" not in contract_data:
                            logger.warning(f"_handle_stream_message: Skipping malformed contract_data (no key): {contract_data}")
                            continue
                        contract_key = contract_data.get("key")
                        if not contract_key:
                            logger.warning(f"_handle_stream_message: Skipping contract_data with empty key: {contract_data}")
                            continue
                        
                        processed_data = {
                            "key": contract_key,
                            "lastPrice": contract_data.get("2"), "askPrice": contract_data.get("7"),
                            "bidPrice": contract_data.get("8"), "askSize": contract_data.get("9"),
                            "bidSize": contract_data.get("10"), "totalVolume": contract_data.get("11"),
                            "volatility": contract_data.get("15"), "delta": contract_data.get("16"),
                            "gamma": contract_data.get("17"), "theta": contract_data.get("18"),
                            "vega": contract_data.get("19"), "openInterest": contract_data.get("21"),
                            "strikePrice": contract_data.get("26"), "contractType": contract_data.get("27"),
                            "expirationDay": contract_data.get("23"), "expirationMonth": contract_data.get("24"),
                            "expirationYear": contract_data.get("25"), "lastUpdated": time.time()
                        }
                        logger.debug(f"_handle_stream_message: Processed data for key {contract_key}: {processed_data}")
                        with self._lock:
                            self.latest_data_store[contract_key] = processed_data
                            if self.status_message not in ["Stream: Actively receiving data..."]:
                                if "Connecting" in self.status_message or "Subscribing" in self.status_message or "Initializing" in self.status_message or "Starting listener" in self.status_message or "Subscriptions sent" in self.status_message:
                                    self.status_message = f"Stream: Actively receiving data for {len(self.current_subscriptions)} contracts."
                logger.debug(f"_handle_stream_message: Data store size: {len(self.latest_data_store)}")
            elif "response" in message_dict or "responses" in message_dict or "notify" in message_dict:
                logger.info(f"Stream admin/response/notify: {message_dict}")
            else:
                logger.warning(f"Unhandled message structure: {message_dict}")

        except Exception as e:
            logger.error(f"Error processing stream message: {e} - Original Raw Message: {raw_message}", exc_info=True)
            with self._lock:
                self.error_message = f"Processing error: {e}"

    def start_stream(self, option_keys_to_subscribe):
        keys_set = set(option_keys_to_subscribe)
        with self._lock:
            if self.is_running:
                logger.info("Stream start requested, but already running. Checking subscriptions...")
                if self.current_subscriptions == keys_set and self.stream_thread and self.stream_thread.is_alive():
                    logger.info("Subscriptions are current and stream is live. No action needed.")
                    return True
                else:
                    logger.info("New subscriptions requested or stream not live. Restarting stream...")
                    self._internal_stop_stream(wait_for_thread=True)

            self.is_running = True 
            self.error_message = None
            self.status_message = "Stream: Starting..."
            self.latest_data_store.clear()

        self.stream_thread = threading.Thread(target=self._stream_worker, args=(tuple(keys_set),), name="SchwabStreamWorker", daemon=True)
        self.stream_thread.start()
        logger.info(f"Stream thread initiated for {len(keys_set)} keys.")
        return True

    def _internal_stop_stream(self, wait_for_thread=False):
        # This method is called with self._lock already held by stop_stream or start_stream (for restart)
        # or it's called without lock from _stream_worker's finally (which is not ideal, but for cleanup)
        # For safety, let's assume it might be called without lock and acquire it if needed.
        # However, the original design implies it's an internal helper. Let's stick to that.
        # It's primarily called from stop_stream which holds the lock.
        
        logger.info("Internal stop stream called.")
        self.is_running = False # Signal the worker thread to stop its loop
        
        active_stream_client_local = self.stream_client # Read under lock if possible, but self.stream_client is mostly managed by worker

        if active_stream_client_local and hasattr(active_stream_client_local, "stop") and active_stream_client_local.active:
            try:
                logger.info("Calling schwabdev's stream_client.stop()...")
                active_stream_client_local.stop()
            except Exception as e:
                logger.error(f"Exception during stream_client.stop(): {e}", exc_info=True)
        else:
            logger.info("No active schwabdev stream_client to stop, or it does not have a stop method, or not active.")

        thread_to_join = self.stream_thread
        if wait_for_thread and thread_to_join and thread_to_join.is_alive():
            logger.info("Waiting for stream worker thread to join after stop signal...")
            thread_to_join.join(timeout=10) 
            if thread_to_join.is_alive():
                logger.warning("Stream worker thread did not terminate gracefully after stop request and join timeout.")
            else:
                logger.info("Stream worker thread joined successfully.")
        self.stream_thread = None
        # self.stream_client = None # Clearing this here might be too soon if worker's finally needs it.
                                  # Worker's finally block will clear its own view of self.stream_client.

    def stop_stream(self):
        with self._lock:
            if not self.is_running and (self.stream_thread is None or not self.stream_thread.is_alive()):
                logger.info("Stream stop requested, but not running or thread already stopped.")
                if self.status_message not in ["Idle", "Stream: Stopped."]:
                     self.status_message = "Idle"
                return

            logger.info("Requesting stream stop...")
            self.status_message = "Stream: Stopping..."
            self._internal_stop_stream(wait_for_thread=True)
        
        # Final status update after lock released, or within lock if preferred
        with self._lock:
            # self.stream_client = None # Moved to worker's finally for safer cleanup
            if self.status_message == "Stream: Stopping...": 
                 self.status_message = "Stream: Stopped."
            elif not self.is_running and self.status_message != "Stream: Stopped.": 
                 # If it was stopped by an error, status would reflect that.
                 # If simply not running and not explicitly stopped, set to Idle.
                 if not self.error_message: # Avoid overwriting error status
                    self.status_message = "Idle"
        logger.info("Stream stop process complete.")

    def get_latest_data(self):
        with self._lock:
            logger.debug(f"get_latest_data called, returning {len(self.latest_data_store)} items.")
            return dict(self.latest_data_store)

    def get_status(self):
        with self._lock:
            # Check if the worker thread died unexpectedly
            if self.is_running and (self.stream_thread is None or not self.stream_thread.is_alive()) \
               and self.status_message not in ["Stream: Starting...", "Stream: Initializing..."]:
                if not self.error_message:
                    self.error_message = "Worker thread died unexpectedly."
                self.status_message = f"Stream: Error - {self.error_message or 'Worker thread died'}"
                self.is_running = False 
            return self.status_message, self.error_message

if __name__ == "__main__":
    pass


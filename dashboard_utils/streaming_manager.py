# dashboard_utils/streaming_manager.py

import threading
import time
import logging
import json # Added for JSON parsing
import schwabdev # Import the main schwabdev library

# Configure basic logging
logger = logging.getLogger(__name__) # Use __name__ for module-specific logger
if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
    handler = logging.StreamHandler()
    # Added %(name)s to formatter for clarity on logger origin
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG) # Set to DEBUG for verbose logging during diagnosis

# To get more detailed logs from schwabdev library itself, uncomment the following line:
# logging.getLogger("schwabdev").setLevel(logging.DEBUG)

class StreamingManager:
    # Corrected Field map based on user-provided list
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
        logger.info("StreamingManager initialized with RLock.")

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
        logger.info(f"_stream_worker started for {len(option_keys_to_subscribe)} keys: {option_keys_to_subscribe}")
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

            logger.info("_stream_worker: Starting schwabdev\"s stream listener (self.stream_client.start)...")
            self.stream_client.start(self._handle_stream_message)
            logger.info("_stream_worker: schwabdev\"s stream_client.start() called. Listener should be active in its own thread.")

            time.sleep(3) # Allow time for connection
            logger.info("_stream_worker: Waited 3s for connection, proceeding with subscriptions.")

            keys_str = ",".join(list(option_keys_to_subscribe))
            fields_str = self.SCHWAB_FIELD_IDS_TO_REQUEST
            
            subscription_payload = self.stream_client.level_one_options(keys_str, fields_str, command="ADD")
            logger.info(f"_stream_worker: Preparing to send LEVELONE_OPTIONS subscription. Keys: {keys_str}. Fields: {fields_str}.")
            logger.debug(f"_stream_worker: Full subscription payload being sent: {json.dumps(subscription_payload)}")
            
            self.stream_client.send(subscription_payload)
            logger.info(f"_stream_worker: Subscription payload sent for {len(option_keys_to_subscribe)} keys.")

            with self._lock:
                self.current_subscriptions = set(option_keys_to_subscribe)
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
                
                time.sleep(0.5) 
                loop_counter +=1
            logger.info("_stream_worker: Exited monitoring loop.")

        except Exception as e:
            logger.error(f"Error in _stream_worker\"s main try block: {e}", exc_info=True)
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
                    logger.info("_stream_worker\"s finally block: Attempting to stop schwabdev stream client.")
                    active_schwab_stream_client.stop()
                    logger.info("_stream_worker\"s finally block: schwabdev stream client stop() called.")
                except Exception as e_stop:
                    logger.error(f"_stream_worker\"s finally block: Error stopping schwabdev stream client: {e_stop}", exc_info=True)
            else:
                logger.info("_stream_worker\"s finally block: Schwabdev stream client not active/stoppable or already None.")
            
            with self._lock:
                self.stream_client = None
            logger.info("_stream_worker finished.")

    def _handle_stream_message(self, raw_message):
        self.message_counter += 1
        current_message_id = self.message_counter
        log_msg_content = str(raw_message)
        if len(log_msg_content) > 1000:
            log_msg_content = log_msg_content[:1000] + "... (truncated)"
        logger.debug(f"[MsgID:{current_message_id}] _handle_stream_message received raw_message (type: {type(raw_message)}). Content: {log_msg_content}")
        
        try:
            message_dict = None
            if isinstance(raw_message, str):
                try:
                    message_dict = json.loads(raw_message)
                except json.JSONDecodeError as jde:
                    logger.error(f"[MsgID:{current_message_id}] Failed to decode JSON: {jde} - Raw (first 200): {raw_message[:200]}", exc_info=True)
                    return
            elif isinstance(raw_message, dict):
                message_dict = raw_message
            else:
                logger.warning(f"[MsgID:{current_message_id}] Unexpected message type: {type(raw_message)}. Raw: {raw_message}")
                return
            logger.debug(f"[MsgID:{current_message_id}] Parsed/received message_dict: {message_dict}")

            if "data" in message_dict:
                data_items = message_dict.get("data", [])
                logger.info(f"[MsgID:{current_message_id}] Identified \"data\" message with {len(data_items)} items.")
                updated_keys_in_batch = []
                for item_index, item in enumerate(data_items):
                    if not isinstance(item, dict) or item.get("service") != "LEVELONE_OPTIONS" or "content" not in item:
                        logger.warning(f"[MsgID:{current_message_id}] Skipping non-LEVELONE_OPTIONS or malformed data item #{item_index}: {item}")
                        continue
                    
                    content_list = item.get("content", [])
                    for content_index, contract_data_from_stream in enumerate(content_list):
                        if not isinstance(contract_data_from_stream, dict):
                            logger.warning(f"[MsgID:{current_message_id}] Skipping non-dict contract_data #{content_index}: {contract_data_from_stream}")
                            continue
                        
                        # Attempt to get contract key from "key" field first, then fallback to "0"
                        contract_key = contract_data_from_stream.get("key")
                        if not contract_key:
                            contract_key = contract_data_from_stream.get("0")
                        
                        if not contract_key:
                            logger.warning(f"[MsgID:{current_message_id}] Skipping contract_data with missing contract key (tried 'key' and '0'): {contract_data_from_stream}")
                            continue
                        
                        processed_data = {}
                        for field_id, value in contract_data_from_stream.items():
                            if field_id in self.SCHWAB_FIELD_MAP:
                                processed_data[self.SCHWAB_FIELD_MAP[field_id]] = value
                        
                        # Ensure the primary key from the stream is always present in our processed_data, using the determined contract_key
                        if "key" not in processed_data:
                             processed_data["key"] = contract_key # Store the identified key as "key"
                        
                        processed_data["lastUpdated"] = time.time()
                        
                        logger.info(f"[MsgID:{current_message_id}] Preparing to store data for key \"{contract_key}\". Data: {processed_data}")
                        updated_keys_in_batch.append(contract_key)
                        with self._lock:
                            self.latest_data_store[contract_key] = processed_data
                            new_store_size = len(self.latest_data_store)
                            current_status = self.status_message
                            if not current_status.startswith("Stream: Error") and \
                               (not current_status.startswith("Stream: Actively receiving data") or \
                                f"for {len(self.current_subscriptions)} contracts" not in current_status or \
                                f"Store size: {new_store_size}" not in current_status):
                                self.status_message = f"Stream: Actively receiving data for {len(self.current_subscriptions)} contracts. Store size: {new_store_size}."
                                logger.info(f"[MsgID:{current_message_id}] Status updated: {self.status_message}")
                            logger.debug(f"[MsgID:{current_message_id}] Data stored for key \"{contract_key}\". New store size: {new_store_size}.")
                
                if updated_keys_in_batch:
                     logger.info(f"[MsgID:{current_message_id}] Batch processed. Updated keys: {updated_keys_in_batch}. Store size: {len(self.latest_data_store)}. Sample: {list(self.latest_data_store.keys())[:3]}")
                else:
                    logger.info(f"[MsgID:{current_message_id}] Batch processed. No new option data keys updated. Store size: {len(self.latest_data_store)}.")

            elif "response" in message_dict or "responses" in message_dict:
                logger.info(f"[MsgID:{current_message_id}] Stream admin/response: {message_dict}")
                if isinstance(message_dict.get("response"), list):
                    for resp_item in message_dict["response"]:
                        if resp_item.get("service") == "LEVELONE_OPTIONS" and resp_item.get("command") == "ADD":
                            if resp_item.get("code") == 0:
                                logger.info(f"[MsgID:{current_message_id}] Subscription ADD successful for LEVELONE_OPTIONS.")
                                with self._lock:
                                     self.status_message = f"Stream: Subscription confirmed for {len(self.current_subscriptions)} contracts. Waiting for data..."
                            else:
                                err_msg = f"Subscription ADD failed for LEVELONE_OPTIONS. Code: {resp_item.get('code')}, Msg: {resp_item.get('msg')}"
                                logger.error(f"[MsgID:{current_message_id}] {err_msg}")
                                with self._lock:
                                    self.error_message = err_msg
                                    self.status_message = f"Stream: Error - {self.error_message}"
            elif "notify" in message_dict:
                logger.info(f"[MsgID:{current_message_id}] Stream notify (heartbeat): {message_dict}")
            else:
                logger.warning(f"[MsgID:{current_message_id}] Unhandled message structure: {message_dict}")

        except Exception as e:
            logger.error(f"[MsgID:{current_message_id}] Error in _handle_stream_message: {e}", exc_info=True)
            with self._lock:
                self.error_message = f"Message processing error: {e}"
                if not self.status_message.startswith("Stream: Error"):
                    self.status_message = f"Stream: Error - {self.error_message}"

    def start_stream(self, option_keys_to_subscribe):
        logger.info(f"start_stream called with {len(option_keys_to_subscribe)} keys: {list(option_keys_to_subscribe)[:5]}...") # Log only a few keys if many
        keys_set = set(option_keys_to_subscribe)

        if not keys_set:
            logger.warning("start_stream called with no option keys. Stream will not be started.")
            with self._lock:
                self.status_message = "Stream: Idle - No keys to subscribe."
            return False

        stop_first = False
        with self._lock:
            if self.is_running:
                if not (self.current_subscriptions == keys_set and self.stream_thread and self.stream_thread.is_alive()):
                    logger.info("Stream running with different state/subscriptions or thread issue. Marking for restart.")
                    stop_first = True
                else:
                    logger.info("Stream is already running with the correct subscriptions. No action needed.")
                    return True 

        if stop_first:
            logger.info("Stopping existing stream before starting new one...")
            self._internal_stop_stream(wait_for_thread=True) 
            logger.info("Existing stream stopped.")

        logger.info("Proceeding to start/restart stream operation.")
        with self._lock:
            if self.stream_thread and self.stream_thread.is_alive():
                 logger.error("CRITICAL: Attempting to start stream, but previous thread is still alive after stop attempt. Aborting start.")
                 self.status_message = "Stream: Error - Failed to stop previous stream thread."
                 return False

            self.latest_data_store.clear()
            self.current_subscriptions.clear() 
            logger.info("Cleared latest_data_store and current_subscriptions for new stream.")

            self.is_running = True 
            self.error_message = None
            self.status_message = "Stream: Starting worker..."
            
            self.stream_thread = threading.Thread(target=self._stream_worker, args=(tuple(keys_set),), name="SchwabStreamWorker")
            self.stream_thread.daemon = True
            self.stream_thread.start()
            logger.info(f"SchwabStreamWorker thread initiated for {len(keys_set)} keys. Thread ID: {self.stream_thread.ident}. Status: {self.status_message}")
        return True

    def get_status(self):
        with self._lock:
            status = self.status_message
            error = self.error_message
        # logger.debug(f"get_status() called. Returning status: \"{status}\", error: \"{error}\"") # Can be noisy
        return status, error

    def get_latest_data(self):
        with self._lock:
            data_copy = dict(self.latest_data_store)
        logger.debug(f"get_latest_data() called. Returning data store with {len(data_copy)} items. Sample keys: {list(data_copy.keys())[:3]}")
        return data_copy

    def _internal_stop_stream(self, wait_for_thread=True):
        logger.info(f"_internal_stop_stream called. wait_for_thread={wait_for_thread}")
        thread_to_join = None
        initial_status_before_stop = ""

        with self._lock:
            initial_status_before_stop = self.status_message
            if not self.is_running and not (self.stream_thread and self.stream_thread.is_alive()):
                logger.info(f"Stream already stopped/not running. is_running={self.is_running}, thread_alive={(self.stream_thread and self.stream_thread.is_alive())}.")
                if self.status_message not in ["Stream: Stopped.", "Stream: Idle", "Stream: Idle - No keys to subscribe.", "Stream: No symbols to subscribe."] and not self.status_message.startswith("Stream: Error"):
                    self.status_message = "Stream: Stopped."
                return

            logger.info(f"Proceeding with _internal_stop_stream. Current is_running: {self.is_running}, thread: {self.stream_thread}")
            self.is_running = False 
            self.status_message = "Stream: Stopping..."
            if self.stream_thread:
                thread_to_join = self.stream_thread
        
        if wait_for_thread and thread_to_join and thread_to_join.is_alive():
            logger.info(f"Waiting for stream worker thread (Name: {thread_to_join.name}, ID: {thread_to_join.ident}) to join...")
            thread_to_join.join(timeout=10) 
            if thread_to_join.is_alive():
                logger.warning(f"Stream worker thread (ID: {thread_to_join.ident}) did not join after 10 seconds.")
            else:
                logger.info(f"Stream worker thread (ID: {thread_to_join.ident}) joined successfully.")
        elif thread_to_join:
             logger.info(f"Stream worker thread (ID: {thread_to_join.ident}) was not alive or wait_for_thread was false.")
        else:
            logger.info("_internal_stop_stream: No thread to join.")

        with self._lock:
            self.stream_thread = None 
            self.current_subscriptions.clear()
            self.latest_data_store.clear()
            
            if self.error_message and "Error" in initial_status_before_stop:
                 self.status_message = f"Stream: Error - {self.error_message}"
            elif self.status_message == "Stream: Stopping...":
                 self.status_message = "Stream: Stopped."
            logger.info(f"_internal_stop_stream: Resources cleaned. Final status: {self.status_message}")

    def stop_stream(self):
        logger.info("stop_stream() (public) called.")
        self._internal_stop_stream(wait_for_thread=True)
        logger.info("stop_stream() (public) completed.")


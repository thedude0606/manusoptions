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
logger.setLevel(logging.INFO) # Set to INFO for general, DEBUG for verbose

# To get more detailed logs from schwabdev library itself, uncomment the following line:
# logging.getLogger('schwabdev').setLevel(logging.DEBUG)

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
        self.message_counter = 0 # For uniquely identifying messages
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

        schwab_api_client = self._get_schwab_client()
        if not schwab_api_client:
            with self._lock:
                self.status_message = f"Stream: Error - {self.error_message or 'Failed to get Schwab client'}"
                self.is_running = False
            logger.error("Stream worker: Failed to get Schwab client. Worker terminating.")
            return

        account_hash = self.account_id_getter()
        if account_hash:
            logger.info(f"Account hash provided (first 4 chars for log): {str(account_hash)[:4]}...")
        else:
            logger.info("No account hash provided; not strictly required for LEVELONE_OPTIONS.")

        try:
            with self._lock:
                self.stream_client = schwab_api_client.stream
            logger.info("Schwab stream object obtained via client.stream")

            if not option_keys_to_subscribe:
                logger.info("Stream worker: No symbols to subscribe.")
                with self._lock:
                    self.status_message = "Stream: No symbols to subscribe."
                    self.is_running = False
                return

            logger.info("Stream worker: Starting schwabdev's stream listener (which runs in its own thread)...")
            self.stream_client.start(self._handle_stream_message)
            logger.info("Stream worker: schwabdev's stream_client.start() called. Listener should be active in its own thread.")

            time.sleep(2) 

            keys_str = ",".join(list(option_keys_to_subscribe))
            # Fields for LEVELONE_OPTIONS: 0=Symbol, 2=Last Price, 7=Ask Price, 8=Bid Price, 9=Ask Size, 10=Bid Size, 11=Total Volume,
            # 15=Volatility, 16=Delta, 17=Gamma, 18=Theta, 19=Vega, 21=Open Interest,
            # 26=Strike Price, 27=Contract Type (CALL/PUT), 23=Expiration Day, 24=Expiration Month, 25=Expiration Year
            fields_str = "0,2,7,8,9,10,11,15,16,17,18,19,21,23,24,25,26,27"
            
            subscription_payload = self.stream_client.level_one_options(keys_str, fields_str, command="ADD")
            logger.info(f"Stream worker: Preparing to send LEVELONE_OPTIONS subscription. Keys: {keys_str}. Fields: {fields_str}.")
            logger.info(f"Stream worker: Full subscription payload being sent: {json.dumps(subscription_payload)}")
            self.stream_client.send(subscription_payload)

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
                
                time.sleep(0.5) 

            logger.info("Stream worker: Exited monitoring loop.")

        except Exception as e:
            logger.error(f"Error in stream worker's main try block: {e}", exc_info=True)
            with self._lock:
                self.error_message = f"Stream error: {e}"
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False
        finally:
            logger.info("Stream worker: Reached finally block.")
            with self._lock:
                if self.is_running: 
                    logger.warning("Stream worker in finally, but self.is_running is still true. Forcing to False.")
                    self.is_running = False

                if self.error_message:
                    pass 
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
                self.stream_client = None
            logger.info("Stream worker finished.")

    def _handle_stream_message(self, raw_message):
        self.message_counter += 1
        current_message_id = self.message_counter
        logger.info(f"[MsgID:{current_message_id}] _handle_stream_message received raw_message (type: {type(raw_message)}). Full message: {raw_message}")
        
        try:
            message_dict = None
            if isinstance(raw_message, str):
                try:
                    message_dict = json.loads(raw_message)
                    logger.debug(f"[MsgID:{current_message_id}] Parsed JSON: {message_dict}")
                except json.JSONDecodeError as jde:
                    logger.error(f"[MsgID:{current_message_id}] Failed to decode JSON message: {jde} - Raw Message: {raw_message}")
                    return
            elif isinstance(raw_message, dict): 
                message_dict = raw_message
                logger.debug(f"[MsgID:{current_message_id}] Received dict directly: {message_dict}")
            else:
                logger.warning(f"[MsgID:{current_message_id}] Unexpected message type received by handler: {type(raw_message)}. Raw Message: {raw_message}")
                return

            if "data" in message_dict:
                data_items = message_dict.get("data", [])
                logger.info(f"[MsgID:{current_message_id}] Processing {len(data_items)} data items.")
                updated_keys_in_batch = []
                for item_index, item in enumerate(data_items):
                    logger.debug(f"[MsgID:{current_message_id}] Processing data item #{item_index}: {item}")
                    if not isinstance(item, dict) or item.get("service") != "LEVELONE_OPTIONS" or "content" not in item:
                        logger.warning(f"[MsgID:{current_message_id}] Skipping non-LEVELONE_OPTIONS or malformed data item: {item}")
                        continue
                    content_list = item.get("content", [])
                    for content_index, contract_data in enumerate(content_list):
                        logger.debug(f"[MsgID:{current_message_id}] Processing content #{content_index} from item #{item_index}: {contract_data}")
                        if not isinstance(contract_data, dict) or "key" not in contract_data:
                            logger.warning(f"[MsgID:{current_message_id}] Skipping malformed contract_data (no key): {contract_data}")
                            continue
                        contract_key = contract_data.get("key")
                        if not contract_key:
                            logger.warning(f"[MsgID:{current_message_id}] Skipping contract_data with empty key: {contract_data}")
                            continue
                        
                        processed_data = {
                            "key": contract_key,
                            "lastPrice": contract_data.get("2"), "askPrice": contract_data.get("7"),
                            "bidPrice": contract_data.get("8"), "askSize": contract_data.get("9"),
                            "bidSize": contract_data.get("10"), "totalVolume": contract_data.get("11"),
                            "volatility": contract_data.get("15"), "delta": contract_data.get("16"),
                            "gamma": contract_data.get("17"), "theta": contract_data.get("18"),
                            "vega": contract_data.get("19"), "openInterest": contract_data.get("21"),
                            "expirationDay": contract_data.get("23"), "expirationMonth": contract_data.get("24"),
                            "expirationYear": contract_data.get("25"),
                            "strikePrice": contract_data.get("26"), "contractType": contract_data.get("27"),
                             "lastUpdated": time.time()
                        }
                        logger.info(f"[MsgID:{current_message_id}] Storing data for key {contract_key}: {processed_data}")
                        updated_keys_in_batch.append(contract_key)
                        with self._lock:
                            self.latest_data_store[contract_key] = processed_data
                            if self.status_message not in ["Stream: Actively receiving data..."]:
                                if "Connecting" in self.status_message or "Subscribing" in self.status_message or "Initializing" in self.status_message or "Starting listener" in self.status_message or "Subscriptions sent" in self.status_message:
                                    self.status_message = f"Stream: Actively receiving data for {len(self.current_subscriptions)} contracts."
                with self._lock:
                    logger.info(f"[MsgID:{current_message_id}] Batch processed. Updated keys: {updated_keys_in_batch}. Current data store size: {len(self.latest_data_store)}. Sample keys in store: {list(self.latest_data_store.keys())[:5]}")
            elif "response" in message_dict or "responses" in message_dict or "notify" in message_dict:
                logger.info(f"[MsgID:{current_message_id}] Stream admin/response/notify: {message_dict}")
            else:
                logger.warning(f"[MsgID:{current_message_id}] Unhandled message structure: {message_dict}")

        except Exception as e:
            logger.error(f"[MsgID:{current_message_id}] Error processing stream message: {e} - Original Raw Message: {raw_message}", exc_info=True)
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
            logger.info("latest_data_store cleared before starting stream.")

        self.stream_thread = threading.Thread(target=self._stream_worker, args=(tuple(keys_set),), name="SchwabStreamWorker", daemon=True)
        self.stream_thread.start()
        logger.info(f"Stream thread initiated for {len(keys_set)} keys.")
        return True

    def _internal_stop_stream(self, wait_for_thread=False):
        logger.info("Internal stop stream called.")
        self.is_running = False
        
        active_stream_client_local = self.stream_client

        if active_stream_client_local and hasattr(active_stream_client_local, 'stop') and active_stream_client_local.active:
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
        
        with self._lock:
            if self.status_message == "Stream: Stopping...": 
                 self.status_message = "Stream: Stopped."
            elif not self.is_running and self.status_message != "Stream: Stopped.": 
                 if not self.error_message: 
                    self.status_message = "Idle"
            logger.info("latest_data_store cleared on stop_stream if stream was stopping.")
            self.latest_data_store.clear() # Clear data when stream is explicitly stopped

        logger.info("Stream stop process complete.")

    def get_latest_data(self):
        with self._lock:
            store_size = len(self.latest_data_store)
            sample_data_log = ""
            if store_size > 0:
                sample_keys = list(self.latest_data_store.keys())[:3] 
                sample_data_log = f" Sample keys: {sample_keys}."
            
            logger.info(f"get_latest_data called. Store size: {store_size}.{sample_data_log}")
            return dict(self.latest_data_store) # Return a copy

    def get_status(self):
        with self._lock:
            if self.is_running and (self.stream_thread is None or not self.stream_thread.is_alive()) \
               and self.status_message not in ["Stream: Starting...", "Stream: Initializing..."]:
                if not self.error_message:
                    self.error_message = "Worker thread died unexpectedly."
                self.status_message = f"Stream: Error - {self.error_message or 'Worker thread died'}"
                self.is_running = False 
            return self.status_message, self.error_message

if __name__ == "__main__":
    pass


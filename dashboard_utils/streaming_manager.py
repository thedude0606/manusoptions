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
# logging.getLogger("schwabdev").setLevel(logging.DEBUG)

class StreamingManager:
    # Corrected Field map based on user-provided list
    # Steamer number - streamer field
    # 0-Symbol, 2-Bid Price, 3-Ask Price, 4-Last Price, 8-Total Volume, 9-Open Interest,
    # 10-Volatility, 12-Expiration Year, 16-Bid Size, 17-Ask Size, 18-Last Size,
    # 20-Strike Price, 21-Contract Type, 23-Expiration Month, 26-Expiration Day,
    # 28-Delta, 29-Gamma, 30-Theta, 31-Vega
    SCHWAB_FIELD_IDS_TO_REQUEST = "0,2,3,4,8,9,10,12,16,17,18,20,21,23,26,28,29,30,31"
    
    # Mapping from Schwab numeric field ID (as string) to our internal descriptive key
    SCHWAB_FIELD_MAP = {
        "0": "key", # Symbol/Contract Key
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
        # Add other fields here if needed in the future, e.g.:
        # "1": "description", "5": "highPrice", "6": "lowPrice", "7": "closePrice",
        # "11": "moneyIntrinsicValue", "13": "multiplier", "14": "digits", "15": "openPrice",
        # "19": "netChange", "22": "underlying", "24": "deliverables", "25": "timeValue",
        # "27": "daysToExpiration", "32": "rho", "33": "securityStatus", 
        # "34": "theoreticalOptionValue", "35": "underlyingPrice", "36": "uvExpirationType",
        # "37": "markPrice", "38": "quoteTimeInLong", "39": "tradeTimeInLong", 
        # "40": "exchange", "41": "exchangeName", "42": "lastTradingDay", 
        # "43": "settlementType", "44": "netPercentChange", "45": "markPriceNetChange",
        # "46": "markPricePercentChange", "47": "impliedYield", "48": "isPennyPilot",
        # "49": "optionRoot", "50": "52WeekHigh", "51": "52WeekLow",
        # "52": "indicativeAskPrice", "53": "indicativeBidPrice", "54": "indicativeQuoteTime",
        # "55": "exerciseType"
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

            logger.info("Stream worker: Starting schwabdev\'s stream listener (which runs in its own thread)...")
            self.stream_client.start(self._handle_stream_message)
            logger.info("Stream worker: schwabdev\'s stream_client.start() called. Listener should be active in its own thread.")

            time.sleep(2) 

            keys_str = ",".join(list(option_keys_to_subscribe))
            fields_str = self.SCHWAB_FIELD_IDS_TO_REQUEST
            
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
            logger.error(f"Error in stream worker\'s main try block: {e}", exc_info=True)
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

            if active_schwab_client and hasattr(active_schwab_client, "stop") and active_schwab_client.active:
                try:
                    logger.info("Stream worker\'s finally block: Attempting to stop schwabdev stream client.")
                    active_schwab_client.stop()
                except Exception as e_stop:
                    logger.error(f"Stream worker\'s finally block: Error stopping schwabdev stream client: {e_stop}")
            
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
                    for content_index, contract_data_from_stream in enumerate(content_list):
                        logger.debug(f"[MsgID:{current_message_id}] Processing content #{content_index} from item #{item_index}: {contract_data_from_stream}")
                        if not isinstance(contract_data_from_stream, dict) or "key" not in contract_data_from_stream:
                            logger.warning(f"[MsgID:{current_message_id}] Skipping malformed contract_data (no key): {contract_data_from_stream}")
                            continue
                        contract_key = contract_data_from_stream.get("key")
                        if not contract_key:
                            logger.warning(f"[MsgID:{current_message_id}] Skipping contract_data with empty key: {contract_data_from_stream}")
                            continue
                        
                        # Map numeric field IDs from stream to descriptive names
                        processed_data = {}
                        for field_id, value in contract_data_from_stream.items():
                            if field_id in self.SCHWAB_FIELD_MAP:
                                processed_data[self.SCHWAB_FIELD_MAP[field_id]] = value
                            # else: # Optionally log unmapped fields if needed for debugging
                                # logger.debug(f"[MsgID:{current_message_id}] Unmapped field ID {field_id} for key {contract_key}")
                        
                        # Ensure the primary key from the stream is always present in our processed_data
                        if "key" not in processed_data and contract_key:
                             processed_data["key"] = contract_key
                        
                        processed_data["lastUpdated"] = time.time()
                        
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

        if active_stream_client_local and hasattr(active_stream_client_local, "stop") and active_stream_client_local.active:
            try:
                logger.info("Calling schwabdev\'s stream_client.stop()...")
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
            self.current_subscriptions.clear()
            # Do not clear latest_data_store here, let it persist until next start
            logger.info("Stream stopped. Subscriptions cleared.")

    def get_latest_data(self):
        with self._lock:
            # Return a copy to avoid modification issues if the caller modifies it
            # and to ensure thread safety during iteration if the store is modified elsewhere.
            store_copy = dict(self.latest_data_store)
            logger.info(f"get_latest_data called. Returning {len(store_copy)} items. Current status: {self.status_message}")
            if store_copy:
                 logger.debug(f"Sample item from get_latest_data: {json.dumps(list(store_copy.values())[0], indent=2)}")
            return store_copy

    def get_status(self):
        with self._lock:
            return self.status_message, self.error_message

    @property
    def is_active(self):
        with self._lock:
            return self.is_running and self.stream_thread is not None and self.stream_thread.is_alive()


# dashboard_utils/streaming_manager.py

import threading
import time
import logging
from schwabdev.streamer_client import StreamerClient # Correct import for StreamerClient

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s")

class StreamingManager:
    def __init__(self, schwab_client_getter, account_id_getter):
        """
        Initializes the StreamingManager.
        schwab_client_getter: A function that returns an authenticated Schwab client instance.
        account_id_getter: A function that returns the account ID (account hash for streaming).
        """
        self.schwab_client_getter = schwab_client_getter
        self.account_id_getter = account_id_getter
        self.streamer_instance = None
        self.is_running = False
        self.stream_thread = None
        self.current_subscriptions = set()
        self.latest_data_store = {}
        self.error_message = None
        self.status_message = "Idle"
        self._lock = threading.Lock()

    def _get_schwab_client(self):
        """Helper to get client, handling potential errors."""
        try:
            client = self.schwab_client_getter()
            if not client:
                self.error_message = "Failed to get Schwab client."
                logging.error(self.error_message)
                return None
            return client
        except Exception as e:
            self.error_message = f"Error obtaining Schwab client: {e}"
            logging.error(self.error_message)
            return None

    def _stream_worker(self, option_keys_to_subscribe_tuple):
        """The actual worker function that runs in a separate thread."""
        option_keys_to_subscribe = set(option_keys_to_subscribe_tuple)
        logging.info(f"Stream worker started for {len(option_keys_to_subscribe)} keys.")
        with self._lock:
            self.status_message = "Stream: Initializing..."
            self.error_message = None

        schwab_client = self._get_schwab_client()
        if not schwab_client:
            with self._lock:
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False
            return
        
        account_hash = self.account_id_getter()
        if not account_hash:
            logging.error("Stream worker: Account hash (SCHWAB_ACCOUNT_HASH) not available or not provided.")
            with self._lock:
                self.error_message = "Account hash (SCHWAB_ACCOUNT_HASH) for streaming is missing."
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False
            return

        try:
            # Correctly instantiate StreamerClient
            self.streamer_instance = StreamerClient(client=schwab_client, account_id=account_hash)
            logging.info(f"StreamerClient instantiated for account hash: {account_hash}")
            
            if not option_keys_to_subscribe:
                logging.info("Stream worker: No symbols to subscribe.")
                with self._lock:
                    self.status_message = "Stream: No symbols to subscribe."
                    self.is_running = False
                return

            keys_string = ",".join(list(option_keys_to_subscribe))
            fields_to_request = "0,2,7,8,9,10,11,15,16,17,18,19,21,26,27,23,24,25"
            
            logging.info(f"Stream worker: Subscribing to {len(option_keys_to_subscribe)} option keys.")
            with self._lock:
                self.current_subscriptions = set(option_keys_to_subscribe)
                self.status_message = f"Stream: Connecting and subscribing to {len(self.current_subscriptions)} contracts..."

            self.streamer_instance.start(
                handler=self._handle_stream_message, 
                service=self.streamer_instance.StreamService.LEVELONE_OPTIONS, 
                symbols=keys_string, 
                fields=fields_to_request
            )
            logging.info("Stream worker: streamer_instance.start() returned. Stream has ended.")

        except Exception as e:
            logging.error(f"Error in stream worker: {e}", exc_info=True)
            with self._lock:
                self.error_message = f"Stream error: {e}"
                self.status_message = f"Stream: Error - {self.error_message}"
        finally:
            with self._lock:
                self.is_running = False
                if not self.error_message:
                    self.status_message = "Stream: Stopped."
            self.streamer_instance = None
            logging.info("Stream worker finished.")

    def _handle_stream_message(self, message_list):
        """Handles incoming messages from the WebSocket stream."""
        try:
            if not isinstance(message_list, list):
                logging.warning(f"Unexpected message type: {type(message_list)}. Expected list. Message: {message_list}")
                return

            for item in message_list:
                if not isinstance(item, dict) or item.get("service") != "LEVELONE_OPTIONS" or "content" not in item:
                    continue
                
                content_list = item.get("content", [])
                for contract_data in content_list:
                    if not isinstance(contract_data, dict) or "key" not in contract_data:
                        continue
                    
                    contract_key = contract_data.get("key")
                    if not contract_key:
                        continue

                    processed_data = {
                        "key": contract_key,
                        "lastPrice": contract_data.get("2"),
                        "askPrice": contract_data.get("7"),
                        "bidPrice": contract_data.get("8"),
                        "askSize": contract_data.get("9"),
                        "bidSize": contract_data.get("10"),
                        "totalVolume": contract_data.get("11"),
                        "volatility": contract_data.get("15"),
                        "delta": contract_data.get("16"),
                        "gamma": contract_data.get("17"),
                        "theta": contract_data.get("18"),
                        "vega": contract_data.get("19"),
                        "openInterest": contract_data.get("21"),
                        "strikePrice": contract_data.get("26"),
                        "contractType": contract_data.get("27"),
                        "expirationDay": contract_data.get("23"),
                        "expirationMonth": contract_data.get("24"),
                        "expirationYear": contract_data.get("25"),
                        "lastUpdated": time.time()
                    }

                    with self._lock:
                        self.latest_data_store[contract_key] = processed_data
                        if "Connecting" in self.status_message or "Subscribing" in self.status_message:
                            self.status_message = f"Stream: Actively receiving data for {len(self.current_subscriptions)} contracts."

        except Exception as e:
            logging.error(f"Error processing stream message: {e} - Message: {message_list}", exc_info=True)
            with self._lock:
                self.error_message = f"Processing error: {e}"

    def start_stream(self, option_keys_to_subscribe):
        """Starts the WebSocket stream in a new thread."""
        keys_set = set(option_keys_to_subscribe)
        with self._lock:
            if self.is_running:
                logging.info("Stream start requested, but already running. Checking subscriptions...")
                if self.current_subscriptions == keys_set:
                    logging.info("Subscriptions are current. No action needed.")
                    return True
                else:
                    logging.info("New subscriptions requested. Restarting stream...")
                    self._internal_stop_stream()
            
            self.is_running = True
            self.error_message = None
            self.status_message = "Stream: Starting..."
            self.latest_data_store.clear()
            self.current_subscriptions = set()

        self.stream_thread = threading.Thread(target=self._stream_worker, args=(tuple(keys_set),), name="SchwabStreamWorker", daemon=True)
        self.stream_thread.start()
        logging.info(f"Stream thread initiated for {len(keys_set)} keys.")
        return True

    def _internal_stop_stream(self):
        """Internal method to stop the stream."""
        if self.streamer_instance and hasattr(self.streamer_instance, "stop"):
            try:
                logging.info("Calling streamer_instance.stop()...")
                self.streamer_instance.stop()
            except Exception as e:
                logging.error(f"Exception during streamer_instance.stop(): {e}", exc_info=True)
        self.is_running = False

    def stop_stream(self):
        """Public method to stop the WebSocket stream."""
        with self._lock:
            if not self.is_running and (self.stream_thread is None or not self.stream_thread.is_alive()):
                logging.info("Stream stop requested, but not running or thread already stopped.")
                self.status_message = "Idle"
                return

            logging.info("Requesting stream stop...")
            self.status_message = "Stream: Stopping..."
            self._internal_stop_stream()
        
        if self.stream_thread and self.stream_thread.is_alive():
            logging.info("Waiting for stream thread to join...")
            self.stream_thread.join(timeout=10)
            if self.stream_thread.is_alive():
                logging.warning("Stream thread did not terminate gracefully after stop request.")
            else:
                logging.info("Stream thread joined successfully.")
        
        self.stream_thread = None
        with self._lock:
            if self.status_message == "Stream: Stopping...":
                 self.status_message = "Idle"
        logging.info("Stream stop process complete.")

    def get_latest_data(self):
        with self._lock:
            return dict(self.latest_data_store) 

    def get_status(self):
        with self._lock:
            if self.is_running and (self.stream_thread is None or not self.stream_thread.is_alive()):
                if not self.error_message:
                    self.error_message = "Worker thread died unexpectedly."
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False
            return self.status_message, self.error_message

if __name__ == "__main__":
    pass

# dashboard_utils/streaming_manager.py

import threading
import time
import logging
import schwabdev # Import the main schwabdev library

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
        self.account_id_getter = account_id_getter # account_id is needed for client.stream() if not part of client
        self.stream_client = None # Renamed from streamer_instance for clarity with new API
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

        schwab_api_client = self._get_schwab_client() # This is the main API client
        if not schwab_api_client:
            with self._lock:
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False
            return
        
        # account_hash = self.account_id_getter() # account_hash might be implicitly handled by schwab_api_client or needed for stream object
        # The documentation for client.stream doesn't explicitly show account_id. Let's assume it's part of the client or handled by the library.
        # If errors occur, we may need to pass account_hash to schwab_api_client.stream() if supported.

        try:
            # Instantiate the streamer using the new API: client.stream
            self.stream_client = schwab_api_client.stream
            logging.info(f"Schwab stream object obtained via client.stream")
            
            if not option_keys_to_subscribe:
                logging.info("Stream worker: No symbols to subscribe.")
                with self._lock:
                    self.status_message = "Stream: No symbols to subscribe."
                    self.is_running = False
                return

            keys_string = ",".join(list(option_keys_to_subscribe))
            # Fields for LEVELONE_OPTIONS. These might need verification against the new stream object's capabilities or Schwab API docs.
            fields_to_request = "0,2,7,8,9,10,11,15,16,17,18,19,21,26,27,23,24,25"
            
            logging.info(f"Stream worker: Subscribing to {len(option_keys_to_subscribe)} option keys.")
            with self._lock:
                self.current_subscriptions = set(option_keys_to_subscribe)
                self.status_message = f"Stream: Connecting and subscribing to {len(self.current_subscriptions)} contracts..."

            # The .start() method signature might have changed. 
            # The documentation shows streamer.start(handler), but the old code used service, symbols, fields.
            # We need to check how to specify these with the new client.stream object.
            # For now, attempting a similar structure. This will likely need adjustment based on schwabdev's stream.py or Streamer Guide.
            # From the `Using the Streamer` documentation: `streamer.start(my_handler)`
            # It also mentions `streamer.start_auto` for automatic start/stop.
            # The original code used `StreamService.LEVELONE_OPTIONS`. This needs to be mapped to the new API.
            # The schwabdev library's stream.py would have the actual implementation details.
            # For now, let's assume it takes similar parameters or we might need to make separate calls to subscribe.
            
            # Based on common patterns, subscriptions are often set before starting or as part of start.
            # Let's assume for now that subscriptions are handled by a different method or implicitly by the service.
            # The original StreamerClient had `StreamService` as an enum. This might now be a string or constant within `schwabdev.stream`.
            # Trying to adapt the old .start() call. This is a guess and might fail.
            # A more robust approach would be to inspect the `schwab_api_client.stream` object or consult detailed examples/source.

            # According to schwab-py (a similar library often mentioned alongside schwabdev), 
            # you typically add subscriptions first, then start the stream handler.
            # e.g., stream_client.add_level_one_option_handler(self._handle_stream_message)
            # stream_client.level_one_option_subs(keys_string, fields_to_request)
            # stream_client.start()

            # Let's try to adapt the old way first, as the user's code was structured like that.
            # If StreamService is not available, this will fail.
            # It's more likely that we need to call a subscribe method on self.stream_client first.
            # The `stream_demo.py` in tylerebowers/Schwabdev would be the best reference.
            # For now, let's assume the old service parameter might still be used or mapped.
            # The old code: service=self.streamer_instance.StreamService.LEVELONE_OPTIONS
            # This implies StreamService was an attribute of the old StreamerClient instance.
            # The new `client.stream` object might have these services differently.
            # The `schwabdev` library's `stream.py` shows `StreamService` enum is still available directly from `schwabdev.stream` module.
            # So, we might need: from schwabdev.stream import StreamService

            from schwabdev.stream import StreamService # Attempting to import StreamService

            self.stream_client.start(
                handler=self._handle_stream_message, 
                service=StreamService.LEVELONE_OPTIONS, # Using the imported StreamService
                symbols=keys_string, 
                fields=fields_to_request,
                account_id=self.account_id_getter() # Adding account_id here as it was part of old StreamerClient init
            )
            logging.info("Stream worker: stream_client.start() returned. Stream has ended.")

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
            self.stream_client = None
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
        # The new stream_client (obtained from client.stream) should also have a stop method.
        if self.stream_client and hasattr(self.stream_client, "stop"):
            try:
                logging.info("Calling stream_client.stop()...")
                self.stream_client.stop()
            except Exception as e:
                logging.error(f"Exception during stream_client.stop(): {e}", exc_info=True)
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


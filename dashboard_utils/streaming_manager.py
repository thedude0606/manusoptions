# dashboard_utils/streaming_manager.py

import threading
import time
import logging
# Assuming schwabdev.Client is the main client, and it has a .streamer() method
# from schwabdev import Client # This would be in the main app
from schwabdev import SchwabStreamer # Corrected import for StreamService enum

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
        self.account_id_getter = account_id_getter # May not be used if client.streamer() handles it
        self.streamer = None # This will be the schwabdev.client.StreamerWrapper instance
        self.is_running = False
        self.stream_thread = None
        self.current_subscriptions = set() # Set of contract keys currently subscribed to
        self.latest_data_store = {} # {contract_key: {field: value, ...}}
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
            self.error_message = None # Clear previous error on new start

        schwab_client = self._get_schwab_client()
        if not schwab_client:
            with self._lock:
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False # Ensure is_running is false if client fails
            return

        try:
            self.streamer = schwab_client.streamer() # Get the streamer instance
            
            if not option_keys_to_subscribe:
                logging.info("Stream worker: No symbols to subscribe.")
                with self._lock:
                    self.status_message = "Stream: No symbols to subscribe."
                    self.is_running = False
                return

            keys_string = ",".join(list(option_keys_to_subscribe))
            # Fields for LEVELONE_OPTIONS based on documentation and needs
            fields_to_request = "0,2,7,8,9,10,11,15,16,17,18,19,21,26,27,23,24,25"
            
            logging.info(f"Stream worker: Subscribing to {len(option_keys_to_subscribe)} option keys.")
            with self._lock:
                self.current_subscriptions = set(option_keys_to_subscribe) # Use the local copy
                self.status_message = f"Stream: Connecting and subscribing to {len(self.current_subscriptions)} contracts..."

            # The streamer.start() method is blocking and handles its own loop for messages.
            # It will call self._handle_stream_message for each message.
            self.streamer.start(
                handler=self._handle_stream_message, 
                service=SchwabStreamer.StreamService.LEVELONE_OPTIONS, # Corrected usage
                symbols=keys_string, 
                fields=fields_to_request
            )
            # If streamer.start() returns, it means the stream was stopped or an unhandled error occurred.
            logging.info("Stream worker: streamer.start() returned. Stream has ended.")

        except Exception as e:
            logging.error(f"Error in stream worker: {e}", exc_info=True)
            with self._lock:
                self.error_message = f"Stream error: {e}"
                self.status_message = f"Stream: Error - {self.error_message}"
        finally:
            with self._lock:
                self.is_running = False # Ensure is_running is set to False
                if not self.error_message: # If no specific error, set to stopped
                    self.status_message = "Stream: Stopped."
                # else status_message will retain the error that caused the stop
            self.streamer = None # Clear streamer instance
            logging.info("Stream worker finished.")

    def _handle_stream_message(self, message_list):
        """Handles incoming messages from the WebSocket stream. Expects a list of message dicts."""
        # Based on schwabdev stream_demo.py, handler receives a list of dictionaries.
        # logging.debug(f"Raw stream message list: {message_list}") 
        try:
            if not isinstance(message_list, list):
                logging.warning(f"Unexpected message type: {type(message_list)}. Expected list. Message: {message_list}")
                return

            for item in message_list:
                if not isinstance(item, dict) or item.get("service") != "LEVELONE_OPTIONS" or "content" not in item:
                    # logging.warning(f"Skipping malformed or non-option stream item: {item}")
                    continue
                
                content_list = item.get("content", [])
                for contract_data in content_list:
                    if not isinstance(contract_data, dict) or "key" not in contract_data:
                        # logging.warning(f"Skipping malformed contract data: {contract_data}")
                        continue
                    
                    contract_key = contract_data.get("key")
                    if not contract_key:
                        continue

                    # Map numbered fields to human-readable names
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
                        # Update status to show data is flowing, if it was just connecting
                        if "Connecting" in self.status_message or "Subscribing" in self.status_message:
                            self.status_message = f"Stream: Actively receiving data for {len(self.current_subscriptions)} contracts."
                    # logging.debug(f"Updated data for {contract_key}")

        except Exception as e:
            logging.error(f"Error processing stream message: {e} - Message: {message_list}", exc_info=True)
            with self._lock:
                self.error_message = f"Processing error: {e}"
                # Potentially update status_message too, or let the main worker thread handle it

    def start_stream(self, option_keys_to_subscribe):
        """Starts the WebSocket stream in a new thread."""
        keys_set = set(option_keys_to_subscribe)
        with self._lock:
            if self.is_running:
                logging.info("Stream start requested, but already running. Checking subscriptions...")
                if self.current_subscriptions == keys_set:
                    logging.info("Subscriptions are current. No action needed.")
                    # self.status_message remains (e.g. "Actively receiving data...")
                    return True
                else:
                    logging.info("New subscriptions requested. Restarting stream...")
                    self._internal_stop_stream() # Stop existing stream before starting new one
            
            self.is_running = True
            self.error_message = None
            self.status_message = "Stream: Starting..."
            self.latest_data_store.clear()
            self.current_subscriptions = set() # Will be set in worker

        # Pass tuple to thread args as sets are not always directly passable depending on context
        self.stream_thread = threading.Thread(target=self._stream_worker, args=(tuple(keys_set),), name="SchwabStreamWorker", daemon=True)
        self.stream_thread.start()
        logging.info(f"Stream thread initiated for {len(keys_set)} keys.")
        return True

    def _internal_stop_stream(self):
        """Internal method to stop the stream, called with lock already acquired or from within manager."""
        if self.streamer and hasattr(self.streamer, "stop"):
            try:
                logging.info("Calling streamer.stop()...")
                self.streamer.stop() # This should make streamer.start() return in the worker thread
            except Exception as e:
                logging.error(f"Exception during streamer.stop(): {e}", exc_info=True)
        self.is_running = False # Signal to worker, though streamer.stop() is primary
        # Worker thread will handle its own cleanup and status update on exit

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
            # Status should be updated by the worker upon exit, or here if it was already stopped.
            if self.status_message == "Stream: Stopping...": # If worker didn\t update it
                 self.status_message = "Idle"
        logging.info("Stream stop process complete.")

    def get_latest_data(self):
        with self._lock:
            return dict(self.latest_data_store) 

    def get_status(self):
        with self._lock:
            # If the thread died unexpectedly, is_running might be true but thread is dead
            if self.is_running and (self.stream_thread is None or not self.stream_thread.is_alive()):
                # This indicates an abnormal stop of the worker thread
                if not self.error_message:
                    self.error_message = "Worker thread died unexpectedly."
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False # Correct the state
            return self.status_message, self.error_message

# Example usage (conceptual, needs real client)
if __name__ == "__main__":
    pass # Main app will instantiate and use this. Testing here requires mock client setup.


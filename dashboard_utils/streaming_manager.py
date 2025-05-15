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
        account_id_getter: A function that returns the account ID (account hash for streaming), if available and needed.
        """
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

        schwab_api_client = self._get_schwab_client()
        if not schwab_api_client:
            with self._lock:
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False
            return

        account_hash = self.account_id_getter()
        if account_hash:
            logging.info(f"Account hash provided (first 4 chars for log): {str(account_hash)[:4]}...")
        else:
            logging.info("No account hash provided; not strictly required for LEVELONE_OPTIONS.")

        try:
            self.stream_client = schwab_api_client.stream
            logging.info(f"Schwab stream object obtained via client.stream")

            if not option_keys_to_subscribe:
                logging.info("Stream worker: No symbols to subscribe.")
                with self._lock:
                    self.status_message = "Stream: No symbols to subscribe."
                    self.is_running = False
                return

            keys_str = ",".join(list(option_keys_to_subscribe))
            # Fields for LEVELONE_OPTIONS: 0=Symbol, 1=Description, 2=Last Price, 3=Open Price, 4=High Price, 5=Low Price, 
            # 6=Close Price, 7=Ask Price, 8=Bid Price, 9=Ask Size, 10=Bid Size, 11=Total Volume, 12=Last Trade Size, 
            # 13=Last Trade Time, 14=Quote Time, 15=Volatility, 16=Delta, 17=Gamma, 18=Theta, 19=Vega, 20=Rho, 
            # 21=Open Interest, 22=Money Intrinsic Value, 23=Expiration Day, 24=Expiration Month, 25=Expiration Year, 
            # 26=Strike Price, 27=Contract Type (CALL/PUT)
            fields_str = "0,2,7,8,9,10,11,15,16,17,18,19,21,26,27,23,24,25" # Key fields for options
            
            logging.info(f"Stream worker: Sending LEVELONE_OPTIONS subscription for keys: {keys_str}")
            # Correct way to subscribe using the send method and the specific service request
            self.stream_client.send(self.stream_client.level_one_options(keys_str, fields_str, command="ADD"))

            with self._lock:
                self.current_subscriptions = set(option_keys_to_subscribe)
                self.status_message = f"Stream: Subscribed to {len(self.current_subscriptions)} contracts. Starting listener..."

            # Start the stream listener. The handler function will be called with received messages.
            self.stream_client.start(handler=self._handle_stream_message)
            logging.info("Stream worker: stream_client.start() returned. Stream has ended or was stopped.")

        except Exception as e:
            logging.error(f"Error in stream worker: {e}", exc_info=True)
            with self._lock:
                self.error_message = f"Stream error: {e}"
                self.status_message = f"Stream: Error - {self.error_message}"
        finally:
            with self._lock:
                self.is_running = False
                if not self.error_message and self.status_message not in ["Stream: Stopped.", "Stream: No symbols to subscribe."] :
                    self.status_message = "Stream: Stopped unexpectedly."
                elif not self.error_message and self.status_message == "Stream: Initializing...":
                    self.status_message = "Stream: Failed to start or connect."
            self.stream_client = None
            logging.info("Stream worker finished.")

    def _handle_stream_message(self, message_list):
        """Handles incoming messages from the WebSocket stream."""
        try:
            if not isinstance(message_list, list):
                if isinstance(message_list, dict) and (
                    message_list.get("service") == "ADMIN" or
                    message_list.get("responses") or
                    message_list.get("notify")
                ):
                    logging.info(f"Stream admin/response/notify: {message_list}")
                else:
                    logging.warning(f"Unexpected message type: {type(message_list)}. Expected list for data. Message: {message_list}")
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
                        if "Connecting" in self.status_message or "Subscribing" in self.status_message or "Initializing" in self.status_message or "Starting listener" in self.status_message:
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
                if self.current_subscriptions == keys_set and self.stream_thread and self.stream_thread.is_alive():
                    logging.info("Subscriptions are current and stream is live. No action needed.")
                    return True
                else:
                    logging.info("New subscriptions requested or stream not live. Restarting stream...")
                    self._internal_stop_stream(wait_for_thread=True)

            self.is_running = True
            self.error_message = None
            self.status_message = "Stream: Starting..."
            self.latest_data_store.clear()

        self.stream_thread = threading.Thread(target=self._stream_worker, args=(tuple(keys_set),), name="SchwabStreamWorker", daemon=True)
        self.stream_thread.start()
        logging.info(f"Stream thread initiated for {len(keys_set)} keys.")
        return True

    def _internal_stop_stream(self, wait_for_thread=False):
        """Internal method to stop the stream. Optionally waits for thread to join."""
        stream_client_to_stop = self.stream_client
        if stream_client_to_stop and hasattr(stream_client_to_stop, "stop"):
            try:
                logging.info("Calling stream_client.stop()...")
                stream_client_to_stop.stop()
            except Exception as e:
                logging.error(f"Exception during stream_client.stop(): {e}", exc_info=True)
        
        self.is_running = False

        if wait_for_thread and self.stream_thread and self.stream_thread.is_alive():
            logging.info("Waiting for stream thread to join after stop signal...")
            self.stream_thread.join(timeout=10)
            if self.stream_thread.is_alive():
                logging.warning("Stream thread did not terminate gracefully after stop request and join timeout.")
            else:
                logging.info("Stream thread joined successfully.")
        self.stream_thread = None

    def stop_stream(self):
        """Public method to stop the WebSocket stream."""
        with self._lock:
            if not self.is_running and (self.stream_thread is None or not self.stream_thread.is_alive()):
                logging.info("Stream stop requested, but not running or thread already stopped.")
                if self.status_message not in ["Idle", "Stream: Stopped."]:
                     self.status_message = "Idle"
                return

            logging.info("Requesting stream stop...")
            self.status_message = "Stream: Stopping..."
            self._internal_stop_stream(wait_for_thread=True)
        
        with self._lock:
            if self.status_message == "Stream: Stopping...":
                 self.status_message = "Stream: Stopped."
            elif not self.is_running and self.status_message != "Stream: Stopped.":
                 self.status_message = "Idle"
        logging.info("Stream stop process complete.")

    def get_latest_data(self):
        with self._lock:
            return dict(self.latest_data_store)

    def get_status(self):
        with self._lock:
            if self.is_running and (self.stream_thread is None or not self.stream_thread.is_alive()) and self.status_message not in ["Stream: Starting..."]:
                if not self.error_message:
                    self.error_message = "Worker thread died unexpectedly."
                self.status_message = f"Stream: Error - {self.error_message}"
                self.is_running = False
            return self.status_message, self.error_message

if __name__ == "__main__":
    pass


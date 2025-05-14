# Design for WebSocket Streaming in Dash Options Chain

This document outlines the design for integrating WebSocket-based real-time data streaming for the Options Chain tab in the Dash dashboard.

## 1. Core Objectives

- Replace the current polling mechanism for the Options Chain tab with a WebSocket stream from the Schwab API.
- Provide real-time updates for option contract details (prices, greeks, volume, etc.).
- Ensure robust connection management and error handling.
- Clearly indicate stream status to the user.

## 2. Key Components & Libraries

- **Dash:** For the web application framework.
- **schwabdev / schwab-py:** Python libraries for interacting with the Schwab API, specifically their streaming capabilities.
- **Python `threading` or `asyncio`:** To run the WebSocket client in a background process without blocking the main Dash application thread.
- **`dcc.Store` and `dcc.Interval`:** Standard Dash components likely to be used for passing data from the background stream to the frontend and triggering UI updates.

## 3. Architectural Approach

We will adopt a multi-threaded approach where the Schwab WebSocket stream runs in a dedicated background thread. The main Dash application thread will handle UI interactions and updates based on data shared from the streaming thread.

### 3.1. Streaming Utility (`dashboard_utils/streaming_manager.py` - New File)

A new module will be created to encapsulate all streaming logic.

**`StreamingManager` Class:**
   - **Initialization (`__init__`):**
     - Takes the `schwabdev.Client` instance (or the necessary components to create one).
     - Initializes internal state variables (e.g., `is_running`, `current_subscriptions`, `latest_data_store`, `error_message`).
     - Uses a `threading.Lock` for safe access to shared data structures like `latest_data_store`.
   - **Stream Connection (`start_stream`):**
     - Takes a list of option contract symbols (keys) to subscribe to.
     - If a stream is already running for different symbols, it might need to stop and restart, or manage adding/removing subscriptions if the API supports it efficiently.
     - Initializes the `StreamClient` from `schwabdev` (or `schwab-py`).
     - Performs login to the stream (`await stream_client.login()` in an async context, or the equivalent synchronous call if the library handles the async loop internally when run in a thread).
     - Subscribes to the `LEVELONE_OPTIONS` service for the given contract keys.
     - Registers a handler function (`_handle_stream_message`).
     - Starts a loop (e.g., `while self.is_running: await stream_client.handle_message()`) to process incoming messages. This loop will run in the background thread.
   - **Message Handler (`_handle_stream_message`):**
     - Receives raw messages from the stream.
     - Parses the message to extract relevant option data (bid, ask, last, volume, greeks, etc.).
     - Updates an internal data structure (`self.latest_data_store`) with the new data. This store will likely be a dictionary where keys are contract symbols and values are their latest data points.
     - With the lock, updates `self.latest_data_store`.
   - **Data Retrieval (`get_latest_data`):**
     - Called by the Dash app (main thread) to get the current snapshot of options data.
     - Returns a copy of `self.latest_data_store` (or structured DataFrames for calls/puts) to avoid direct modification by the Dash thread.
     - Accesses `self.latest_data_store` with the lock.
   - **Stream Control (`stop_stream`):**
     - Sets `self.is_running` to `False` to signal the background thread to exit its loop.
     - Performs logout from the stream (`await stream_client.logout()`).
     - Joins the background thread to ensure clean shutdown.
   - **Status & Error Reporting:**
     - Methods to get current stream status (e.g., `get_status() -> str` returning "Connected", "Disconnected", "Error: ...").
     - Stores and provides access to any critical error messages.

### 3.2. Dash Application Integration (`dashboard_app.py`)

- **Global StreamingManager Instance:** A single instance of `StreamingManager` will be created when the Dash app starts.
- **Callbacks for Stream Control:**
  - When a symbol is selected in the `symbol-filter-dropdown` and the "Options Chain" tab is active:
    - A callback will trigger that first fetches the list of relevant option contract keys (with OI > 0) for the selected underlying symbol (similar to current `get_options_chain_data` but just for keys).
    - It will then call `streaming_manager.start_stream(option_keys)`.
  - When the selected symbol changes or the tab is navigated away from, `streaming_manager.stop_stream()` might be called to conserve resources, or the stream could be kept alive and subscriptions modified (if efficient).
- **Callbacks for UI Updates:**
  - A `dcc.Interval` component will trigger a callback every 1-2 seconds (adjustable).
  - This callback will:
    1. Call `streaming_manager.get_latest_data()` to fetch the most recent options data.
    2. Call `streaming_manager.get_status()` to get the stream status.
    3. Process the data into two pandas DataFrames (calls and puts).
    4. Update the `data` property of the `options-calls-table` and `options-puts-table`.
    5. Update an `html.Div` (e.g., `id="options-chain-stream-status"`) to display the current stream status and any error messages.
- **`dcc.Store` for Intermediate Data (Optional but Recommended):**
  - The streaming thread could update a `dcc.Store` with the latest data. The interval callback would then read from this `dcc.Store`. This can sometimes be a cleaner pattern for inter-thread communication in Dash if direct calls to the manager object become complex to synchronize.

## 4. Data Flow

1.  User selects a symbol for the Options Chain tab.
2.  Dash callback: Fetches option contract keys for the symbol.
3.  Dash callback: Calls `streaming_manager.start_stream(keys)`.
4.  `StreamingManager` (background thread): Connects to Schwab, subscribes, and starts listening.
5.  Schwab API: Pushes real-time option data via WebSocket.
6.  `StreamingManager` (`_handle_stream_message`): Processes message, updates its internal `latest_data_store`.
7.  Dash `dcc.Interval`: Triggers a callback periodically.
8.  Dash callback: Calls `streaming_manager.get_latest_data()` and `streaming_manager.get_status()`.
9.  Dash callback: Updates the Calls DataTable, Puts DataTable, and Stream Status Div with the retrieved data and status.

## 5. Error Handling and Status Display

- **Connection Errors:** The `StreamingManager` will catch exceptions during login, subscription, and message handling. These will be reflected in its status.
- **Disconnections:** The design needs to consider how to detect and handle unexpected disconnections. The `handle_message` loop might break, or the library might provide callbacks for such events.
- **UI Indication:**
  - A dedicated area in the Options Chain tab will display:
    - Stream Status: e.g., "Connecting...", "Streaming AAPL Options", "Disconnected. Retrying...", "Error: [message]".
    - Last message received timestamp (optional, could be useful for debugging).

## 6. Key Challenges and Considerations

- **Asynchronous Operations in a Synchronous Framework (Dash):** Running `asyncio`-based libraries like `schwab-py` or parts of `schwabdev` for streaming within a separate thread that communicates with the main Dash (Flask) thread requires careful synchronization (locks, thread-safe queues if needed).
- **Dash UI Updates from Background Threads:** Dash component properties should only be updated via callbacks in the main thread. The `dcc.Interval` polling the `StreamingManager` is the standard way to achieve this.
- **Resource Management:** Ensuring streams are properly closed when not needed or when the app shuts down.
- **API Rate Limits/Subscription Limits:** Be mindful of how many contracts are subscribed to. The current approach of fetching all OI > 0 contracts might be too many for some underlyings. This might need refinement (e.g., allowing user to specify strike range, DTE range for streaming).
- **Initial Data Load vs. Streamed Updates:** When a stream starts, it might not provide a full snapshot immediately. The initial population of the table might still need a REST API call, with the stream then providing updates. This needs to be clarified based on API behavior.

## 7. Next Steps (Implementation Plan based on this Design)

1.  Create `dashboard_utils/streaming_manager.py` with the basic `StreamingManager` class structure.
2.  Implement the `start_stream`, `_handle_stream_message`, and `stop_stream` methods, focusing on thread management and basic message processing (initially just printing to console from the thread).
3.  Modify `dashboard_app.py` to instantiate `StreamingManager`.
4.  Add callbacks to trigger `start_stream` and `stop_stream` based on symbol selection and tab visibility.
5.  Implement the `dcc.Interval` and its callback to call `get_latest_data` and `get_status` from `StreamingManager` and update placeholder UI elements.
6.  Refine data parsing in `_handle_stream_message` to populate `latest_data_store` correctly.
7.  Connect the `get_latest_data` output to the actual Dash DataTables.
8.  Implement robust status display and error message propagation.
9.  Thorough testing and refinement.

This design provides a roadmap. Specific implementation details will be refined as development progresses and library behaviors are further understood in the context of a Dash app.

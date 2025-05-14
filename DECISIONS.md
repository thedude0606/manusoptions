## Decision Log

### Key Architectural Choices

*   **Application Modes (`fetch_options_chain.py`):** Implemented `APP_MODE` in `fetch_options_chain.py` to allow switching between a one-time "FETCH" mode and a continuous "STREAM" mode for options data. This provides flexibility for different use cases.
*   **Streaming Logic (`fetch_options_chain.py`):**
    *   Utilized `schwabdev.Client.stream` for handling the WebSocket connection.
    *   Implemented a custom `stream_message_handler` to process incoming `LEVELONE_OPTIONS` data.
    *   Employed a threaded approach for the streamer to run in the background (`daemon=True`).
    *   Implemented change detection by comparing incoming stream data with a stored `current_contracts_data` state.
    *   Aggregated and displayed changes every 5 seconds, clearing the console for a refreshed view.
*   **Contract Filtering (`fetch_options_chain.py`):**
    *   Implemented pre-streaming filtering of option contracts by fetching the option chain via `client.option_chains()` and then applying filters locally before subscribing to the stream. This was chosen because the `option_chains` endpoint provides necessary fields like `openInterest` and `daysToExpiration` which might not be available for filtering directly in a stream subscription request for *all* contracts of an underlying.
    *   Filters implemented: Minimum Open Interest and specific Days To Expiration (DTE).
    *   **0DTE Contract Fetching:** When `STREAMING_FILTER_DTE` is set to 0, the script now modifies the `client.option_chains()` API call to use `fromDate` and `toDate` parameters set to the current day. This is intended to specifically request today\s expiring contracts from the API.
*   **Configuration (Scripts):** Key parameters for both FETCH and STREAM modes in `fetch_options_chain.py`, including symbols, filters, and API field requests, are defined as global variables at the top of the script for easy modification.
*   **Error Handling (Scripts - Basic):** Included `try-except` blocks for API calls, token updates, and JSON parsing in the stream handler. The script will print error messages but may not have advanced retry logic for all scenarios yet.
*   **Credential Management:** Relies on `.env` file for API keys and `tokens.json` for OAuth tokens, managed by `auth_script.py` (as per existing structure). This is used by both standalone scripts and the dashboard.
*   **Diagnostic Logging (`fetch_options_chain.py`):** Raw contract data fetched before filtering is logged to `raw_contracts_diag.log` to aid in debugging filter behavior.

*   **Web Dashboard Architecture (`dashboard_app.py`):**
    *   **Framework:** Dash by Plotly selected for building the interactive web UI, as requested.
    *   **Structure:** Single-page application with a tabbed interface for different data views (Minute Data, Technical Indicators, Options Chain).
    *   **Symbol Handling:** Implemented a text input for comma-separated symbols and a subsequent dropdown filter to select a single symbol for display across all tabs. Processed symbols are stored in `dcc.Store`.
    *   **Data Display:** Dash DataTables (`dash_table.DataTable`) are used for presenting tabular data in each tab. Pagination is enabled for better readability.
    *   **Modularity:** Data fetching and streaming logic are separated into `dashboard_utils/data_fetchers.py` and `dashboard_utils/streaming_manager.py` modules.
    *   **API Client Management:** A global Schwab client instance (`SCHWAB_CLIENT`) is initialized at app startup in `dashboard_app.py`. Callbacks attempt re-initialization if needed.
    *   **Error Handling (Dashboard):** API errors, client initialization issues, and streaming errors are caught and displayed in the UI via a `dcc.Store` and an error log display area.
    *   **Callback Structure:** Callbacks manage UI updates, data fetching, and stream lifecycle.
    *   **Options Chain Streaming:**
        *   Prioritized WebSocket streaming for the Options Chain tab for real-time data, crucial for an options recommendation platform.
        *   Implemented a `StreamingManager` class in `dashboard_utils/streaming_manager.py` to handle the Schwab API WebSocket connection, subscriptions, message processing, and data storage in a dedicated background thread. This encapsulates the complexity of managing the `schwabdev.client.StreamerWrapper`.
        *   The `StreamingManager` is started/stopped based on symbol selection and whether the "Options Chain (Stream)" tab is active.
        *   UI updates for the options tables are driven by data retrieved from the `StreamingManager` via a `dcc.Interval` component, which periodically polls the manager for the latest data.
        *   A dedicated UI section in the Options Chain tab displays the real-time status of the WebSocket stream (e.g., Idle, Connecting, Streaming, Error) and any error messages from the `StreamingManager`.

### Technology Selections

*   **Primary API Library:** `schwabdev` Python library for all Charles Schwab API interactions (REST and Streaming).
*   **Web Dashboard:** Dash by Plotly.
*   **Data Handling:** Pandas for data manipulation.
*   **Environment Management:** `python-dotenv` for API credentials.
*   **Concurrency:** `threading` module for running the WebSocket stream in a background thread without blocking the Dash application.
*   **Standard Libraries:** `json`, `os`, `datetime`, `time`, `logging`.

### Design Patterns Used

*   **Observer Pattern (Implicit):** The `StreamingManager` processes messages from the stream and updates its internal data store; the Dash app then observes this store.
*   **Stateful Change Detection (Original `fetch_options_chain.py`):** Maintained state to identify changes in streamed data.
*   **Configuration-Driven (Scripts & Dashboard):** Behavior influenced by configurations (e.g., API keys in `.env`).
*   **Utility/Helper Modules:** Separated concerns (data fetching, streaming management) into `dashboard_utils`.
*   **Background Worker Thread (StreamingManager):** The WebSocket streaming logic runs in a separate thread to prevent blocking the main Dash application thread, allowing the UI to remain responsive.

### Rationale for Important Decisions

*   **Prioritizing WebSocket for Options Chain:** Based on the goal of building an options recommendation platform, WebSocket streaming was chosen for the Options Chain tab to ensure timely and accurate data, despite the increased complexity compared to polling.
*   **Dedicated `StreamingManager` Class:** To manage the complexities of WebSocket lifecycle, subscriptions, message handling, and thread management, a dedicated class was created. This improves modularity and separation of concerns.
*   **UI Updates via Polling `StreamingManager`:** While the `StreamingManager` receives data in real-time via WebSockets, the Dash UI updates its tables by periodically polling the `StreamingManager` for the latest data using a `dcc.Interval`. This is a common pattern for integrating asynchronous data sources with Dash, as Dash callbacks are typically triggered by client-side events or intervals, not directly by server-side pushes from background threads without more complex setups (like `dash-extensions` Server-Sent Events).
*   **Stream Lifecycle Management:** The stream is automatically started when a symbol is selected and the "Options Chain (Stream)" tab is active. It is stopped when the tab is changed or no symbol is selected, to conserve resources and API usage.
*   **Error and Status Display:** Providing clear UI feedback on the stream\s status and any errors is crucial for usability and debugging.
*   **Using `schwabdev.client.StreamerWrapper`:** Leveraged the `streamer()` method from the `schwabdev` client, which provides a convenient wrapper for managing stream services and handlers, simplifying the direct WebSocket interaction code.
*   **Account Hash for Streaming:** Emphasized the need for `SCHWAB_ACCOUNT_HASH` (not the account number) for streaming, as per Schwab API requirements.
nature.
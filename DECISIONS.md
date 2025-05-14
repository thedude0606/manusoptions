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
    *   **0DTE Contract Fetching:** When `STREAMING_FILTER_DTE` is set to 0, the script now modifies the `client.option_chains()` API call to use `fromDate` and `toDate` parameters set to the current day. This is intended to specifically request today's expiring contracts from the API.
*   **Configuration (Scripts):** Key parameters for both FETCH and STREAM modes in `fetch_options_chain.py`, including symbols, filters, and API field requests, are defined as global variables at the top of the script for easy modification.
*   **Error Handling (Scripts - Basic):** Included `try-except` blocks for API calls, token updates, and JSON parsing in the stream handler. The script will print error messages but may not have advanced retry logic for all scenarios yet.
*   **Credential Management:** Relies on `.env` file for API keys and `tokens.json` for OAuth tokens, managed by `auth_script.py` (as per existing structure). This is used by both standalone scripts and the dashboard.
*   **Diagnostic Logging (`fetch_options_chain.py`):** Raw contract data fetched before filtering is logged to `raw_contracts_diag.log` to aid in debugging filter behavior.

*   **Web Dashboard Architecture (`dashboard_app.py`):**
    *   **Framework:** Dash by Plotly selected for building the interactive web UI, as requested.
    *   **Structure:** Single-page application with a tabbed interface for different data views (Minute Data, Technical Indicators, Options Chain).
    *   **Symbol Handling:** Implemented a text input for comma-separated symbols and a subsequent dropdown filter to select a single symbol for display across all tabs. Processed symbols are stored in `dcc.Store`.
    *   **Data Display:** Dash DataTables (`dash_table.DataTable`) are used for presenting tabular data in each tab. Pagination is enabled for better readability.
    *   **Modularity:** Data fetching logic is separated into a `dashboard_utils/data_fetchers.py` module to keep the main `dashboard_app.py` cleaner and promote reusability.
    *   **API Client Management:** A global Schwab client instance (`SCHWAB_CLIENT`) is initialized at app startup in `dashboard_app.py` and reused across callbacks. If initialization fails or the client is None, callbacks attempt to re-initialize it. This is a simpler approach for this stage; more complex state management might be needed for a production app.
    *   **Error Handling (Dashboard):** API errors and client initialization issues are caught in callbacks. Error messages (with timestamps) are stored in a `dcc.Store` (`error-message-store`) and displayed in a dedicated `html.Div` (`error-log-display`) in the UI, showing the last few errors.
    *   **Callback Structure:** Callbacks are used to update UI components based on user input (symbol selection) and intervals (for options chain). `suppress_callback_exceptions=True` is set for the Dash app due to dynamically generated content/callbacks for tabs.

### Technology Selections

*   **Primary API Library:** `schwabdev` Python library for all Charles Schwab API interactions (REST and Streaming).
*   **Web Dashboard:** Dash by Plotly.
*   **Data Handling:** Pandas for data manipulation before display in Dash tables.
*   **Environment Management:** `python-dotenv` for loading API credentials from a `.env` file.
*   **Standard Libraries:** `json`, `os`, `datetime`, `time`, `threading`, `sys`.

### Design Patterns Used

*   **Observer Pattern (Implicit in `fetch_options_chain.py`):** The `stream_message_handler` acts as an observer of messages from the streamer.
*   **Stateful Change Detection (`fetch_options_chain.py`):** The streaming logic maintains the state of `current_contracts_data` to compare with new data and identify changes.
*   **Configuration-Driven (Scripts):** Script behavior (mode, symbols, filters) is driven by global configuration variables.
*   **Utility/Helper Functions (Dashboard):** Data fetching logic encapsulated in `dashboard_utils.data_fetchers` to separate concerns from the UI layout and callbacks in `dashboard_app.py`.

### Rationale for Important Decisions

*   **Iterative F-string Correction (`fetch_options_chain.py`):** Switched problematic f-strings to use `.format()` or ensured correct quote usage to resolve `SyntaxError` issues.
*   **Chunked Stream Subscriptions (`fetch_options_chain.py`):** Implemented `MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION` as a pre-emptive measure against potential API limits.
*   **Console as "Data Chart" (`fetch_options_chain.py`):** Used `os.system("clear")` for simple console refresh; GUI/web chart is a future enhancement.
*   **Filtering Post-Chain Fetch (`fetch_options_chain.py` - General Case):** Fetched broader option chains first then filtered locally for reliability in getting all necessary contract details.
*   **Targeted 0DTE Fetch (`fetch_options_chain.py`):** Modified API call parameters (`fromDate`, `toDate`) for specific 0DTE contract requests.
*   **Global Schwab Client (Dashboard):** Opted for a global client instance in `dashboard_app.py` for simplicity in the initial dashboard version. Callbacks attempt re-initialization if it's `None`. This balances ease of use with basic robustness for now.
*   **Error Display in UI (Dashboard):** Chose to display errors directly in the dashboard UI via a `dcc.Store` and an `html.Div` to provide immediate feedback to the user about data fetching or client issues.
*   **REST for Dashboard Data (Minute Data & Options Chain):** Started with REST API calls for minute data and options chain in the dashboard due to simpler integration with Dash callbacks compared to setting up a persistent WebSocket stream within the Dash app's lifecycle for the initial versions. 
    *   For **Options Chain**, the `client.option_chains()` API is called with `expMonth="ALL"` to retrieve a comprehensive set of contracts. Filtering for `openInterest > 0` is then performed client-side (in Python) to meet user requirements. A "Last Updated" timestamp is displayed to indicate data freshness due to the polling nature.
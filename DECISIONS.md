## Decision Log

### Key Architectural Choices

*   **Application Modes:** Implemented `APP_MODE` in `fetch_options_chain.py` to allow switching between a one-time "FETCH" mode and a continuous "STREAM" mode for options data. This provides flexibility for different use cases.
*   **Streaming Logic:**
    *   Utilized `schwabdev.Client.stream` for handling the WebSocket connection.
    *   Implemented a custom `stream_message_handler` to process incoming `LEVELONE_OPTIONS` data.
    *   Employed a threaded approach for the streamer to run in the background (`daemon=True`).
    *   Implemented change detection by comparing incoming stream data with a stored `current_contracts_data` state.
    *   Aggregated and displayed changes every 5 seconds, clearing the console for a refreshed view.
*   **Contract Filtering:**
    *   Implemented pre-streaming filtering of option contracts by fetching the option chain via `client.option_chains()` and then applying filters locally before subscribing to the stream. This was chosen because the `option_chains` endpoint provides necessary fields like `openInterest` and `daysToExpiration` which might not be available for filtering directly in a stream subscription request for *all* contracts of an underlying.
    *   Filters implemented: Minimum Open Interest and specific Days To Expiration (DTE).
    *   **0DTE Contract Fetching:** When `STREAMING_FILTER_DTE` is set to 0, the script now modifies the `client.option_chains()` API call to use `fromDate` and `toDate` parameters set to the current day. This is intended to specifically request today's expiring contracts from the API.
*   **Configuration:** Key parameters for both FETCH and STREAM modes, including symbols, filters, and API field requests, are defined as global variables at the top of the script for easy modification.
*   **Error Handling (Basic):** Included `try-except` blocks for API calls, token updates, and JSON parsing in the stream handler. The script will print error messages but may not have advanced retry logic for all scenarios yet.
*   **Credential Management:** Relies on `.env` file for API keys and `tokens.json` for OAuth tokens, managed by `auth_script.py` (as per existing structure).
*   **Diagnostic Logging:** Raw contract data fetched before filtering is logged to `raw_contracts_diag.log` to aid in debugging filter behavior.

### Technology Selections

*   **Primary Library:** `schwabdev` Python library for all Charles Schwab API interactions (REST and Streaming).
*   **Environment Management:** `python-dotenv` for loading API credentials from a `.env` file.
*   **Standard Libraries:** `json` for data serialization, `os` for file/system operations, `datetime` and `time` for time-related functions, `threading` for concurrent stream handling, `sys` for output flushing.

### Design Patterns Used

*   **Observer Pattern (Implicit):** The `stream_message_handler` acts as an observer of messages from the streamer.
*   **Stateful Change Detection:** The streaming logic maintains the state of `current_contracts_data` to compare with new data and identify changes.
*   **Configuration-Driven:** Script behavior (mode, symbols, filters) is driven by global configuration variables.

### Rationale for Important Decisions

*   **Iterative F-string Correction:** Switched problematic f-strings (those with nested quotes or complex formatting needs) to use the `.format()` method or ensured correct single/double quote usage within f-strings to resolve persistent `SyntaxError` issues. This was a pragmatic choice for clarity and correctness over strict adherence to f-strings in all cases.
*   **Chunked Stream Subscriptions:** Implemented `MAX_CONTRACTS_PER_STREAM_SUBSCRIPTION` to break down large lists of contract keys into smaller chunks for subscription. This is a pre-emptive measure against potential API limits on the number of keys per subscription request, although the exact limit for `LEVELONE_OPTIONS` might be higher.
*   **Console as "Data Chart":** For the requirement of an overwriting "data chart," the current implementation uses `os.system("clear")` (or `cls`) to refresh the console output every 5 seconds. This is a simple, cross-platform approach for now. More sophisticated GUI/web-based charting is a future enhancement.
*   **Filtering Post-Chain Fetch (General Case):** For non-0DTE specific DTE filtering, the decision to fetch a broader set of option chains first (e.g., `expMonth="ALL"`) and then filter locally was made because the `option_chains` REST API call is the most reliable way to get all necessary contract details (like open interest, DTE) needed for the specified filters. Attempting to filter *before* this initial fetch for arbitrary DTEs would be more complex or might not be fully supported by the API for all desired filter types simultaneously.
*   **Targeted 0DTE Fetch:** Based on diagnostic logs showing no 0DTE contracts with `expMonth="ALL"`, the logic was refined. When `STREAMING_FILTER_DTE = 0`, the script now specifically sets `fromDate` and `toDate` to the current day in the `client.option_chains()` call to directly request 0DTE contracts from the API. This is a more targeted approach for this specific use case.

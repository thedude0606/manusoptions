## TODO List

### Setup and Initial Debugging

- [x] Clone GitHub repository (`https://github.com/thedude0606/manusoptions`)
- [x] Analyze `fetch_options_chain.py` for `AttributeError`
- [x] Review `auth_script.py` and `schwabdev` library usage for token management
- [x] Create `PROGRESS.md` and populate initial content
- [x] Create `TODO.md` and populate initial tasks
- [x] Create `DECISIONS.md` and populate initial decisions/observations
- [x] Modify `fetch_options_chain.py` to fix `AttributeError` by using `client.tokens` (or equivalent `schwabdev` methods) for token validation and refresh.
- [x] Test the corrected `fetch_options_chain.py` (AttributeError resolved; script now proceeds to credential/token validation).
- [x] Push all code changes and tracking files (PROGRESS.md, TODO.md, DECISIONS.md) to the GitHub repository.
- [x] Investigate and fix `AttributeError: 'Tokens' object has no attribute 'is_access_token_expired'` by using `client.tokens.update_tokens()`.

### Streaming Functionality Implementation (`fetch_options_chain.py`)

- [x] Clarify streaming requirements with user (data scope, symbols, data handling, script structure, duration).
- [x] Review provided `schwabdev` streaming examples and documentation.
- [x] Design and implement initial streaming logic in `fetch_options_chain.py`:
    - [x] Add `APP_MODE` to switch between "FETCH" and "STREAM".
    - [x] Implement `stream_message_handler` for `LEVELONE_OPTIONS`.
    - [x] Implement change detection for streamed contract metrics.
    - [x] Add 5-second interval display for detected changes.
    - [x] Support multiple underlying symbols for streaming.
    - [x] Fetch all option contract keys for specified symbols.
    - [x] Implement subscription to option contracts in chunks.
- [x] Clarify and implement efficient contract filtering for streaming:
    - [x] Filter out contracts with zero open interest.
    - [x] Add filter for expiration date (DTE), including 0DTE.
    - [x] Update `get_filtered_option_contract_keys` to apply these filters.
- [x] Systematically scan and correct all f-string and other syntax/formatting errors in `fetch_options_chain.py`.
- [x] Verify script runs without syntax errors (up to credential validation).

### Debugging Contract Filtering (`fetch_options_chain.py`)

- [x] Modify `get_filtered_option_contract_keys` to write raw contract data (symbol, OI, DTE) to a log file (`raw_contracts_diag.log`) for comprehensive analysis.
- [x] User to run the modified `fetch_options_chain.py` and provide the `raw_contracts_diag.log` file.
- [x] Analyze the diagnostic log to understand how the API reports OI and DTE for the specified symbols (e.g., AAPL 0DTE).
- [x] Refine the contract filtering logic in `get_filtered_option_contract_keys` based on the analysis of the diagnostic output. Specifically, when `STREAMING_FILTER_DTE = 0`, the script now uses `fromDate` and `toDate` set to the current day in the `client.option_chains()` API call to target 0DTE contracts.

### Web Dashboard Development

- [x] Clone and review existing `manusoptions` repository for dashboard integration.
- [x] Design basic structure for a Dash web dashboard (`dashboard_app.py`).
- [x] Implement symbol input (comma-separated) and a dropdown filter for selecting a processed symbol.
- [x] Build the main tab structure: Minute Streaming Data, Technical Indicators, Options Chain.
- [x] Create UI placeholders (Dash DataTables) for each tab.
- [x] Develop a utility module `dashboard_utils/data_fetchers.py` for Schwab API interactions.
    - [x] Implement `get_schwab_client()` for client initialization.
    - [x] Implement `get_minute_data()` to fetch 1-minute historical data.
- [x] Integrate `get_minute_data()` into the "Minute Streaming Data" tab callback in `dashboard_app.py`.
- [x] Implement error handling for API calls and client initialization within the dashboard.
- [x] Add an error log display area in the dashboard UI, updated via a `dcc.Store`.
- [x] **Options Chain Tab:**
    - [x] Create a utility function `get_options_chain_data()` in `dashboard_utils/data_fetchers.py` to fetch options chain data.
        - [x] Function takes a symbol as input.
        - [x] Fetches options chain (puts and calls) using `client.option_chains()` for `expMonth="ALL"`.
        - [x] Filters contracts for `openInterest > 0`.
        - [x] Selects relevant fields (Expiration Date, Strike, Last, Bid, Ask, Volume, Open Interest, Implied Volatility, Delta, Gamma, Theta, Vega).
        - [x] Returns two DataFrames (one for calls, one for puts).
    - [x] Integrate `get_options_chain_data()` into the "Options Chain" tab callback in `dashboard_app.py`.
    - [x] Implement the 5-second refresh interval for this tab using `dcc.Interval`.
    - [x] Add a "Last Updated: [timestamp]" display to the Options Chain tab.
    - [x] Ensure error handling and logging are implemented for options chain data fetching.
- [ ] **Technical Indicators Tab:**
    - [ ] Create a utility function in `dashboard_utils/data_fetchers.py` (or a new `technical_analysis_utils.py`) to adapt logic from `technical_analysis.py`.
        - [ ] Function should take a symbol and raw price data (e.g., minute data DataFrame) as input.
        - [ ] Calculate required indicators (RSI, MACD, FVG) for 1-min, 15-min, 1-hour, and daily intervals.
        - [ ] Return a structured DataFrame or dictionary suitable for a Dash DataTable (Indicator, 1min, 15min, 1hour, Daily).
    - [ ] Integrate this utility into the "Technical Indicators" tab callback in `dashboard_app.py`.
    - [ ] Ensure error handling and logging are implemented.
- [ ] **General Dashboard Refinements:**
    - [ ] Ensure all requested fields are displayed in the respective tables for all tabs.
    - [ ] Verify that the dashboard refreshes only the necessary components (e.g., options chain tab every 5s, other tabs on symbol change or less frequently).
    - [ ] Test dashboard with multiple symbols and edge cases (e.g., invalid symbol, API errors, no options data for a symbol).

### Broader Testing & Next Steps (Post-Dashboard V1)

- [ ] User to test `fetch_options_chain.py` in "STREAM" mode with the latest 0DTE filtering logic and valid Schwab API credentials and `tokens.json`. Provide the new `raw_contracts_diag.log` and console output.
- [ ] Analyze the new diagnostic log to confirm if 0DTE contracts are now being fetched and correctly filtered by `fetch_options_chain.py`.
- [ ] Address any issues identified during user's live streaming tests with `fetch_options_chain.py`.
- [ ] User to test the fully implemented Dash web dashboard locally.
- [ ] Discuss and implement further enhancements (e.g., more sophisticated "data chart", additional filtering options, error handling for stream disconnects if streaming is added to dashboard).

### Future Enhancements (Placeholder)

- [ ] Develop options buying recommendation logic.
- [ ] Integrate advanced technical indicators if requested.
- [ ] Implement comprehensive backtesting features.
- [ ] Package application for easy local deployment (if beyond simple `python dashboard_app.py`).

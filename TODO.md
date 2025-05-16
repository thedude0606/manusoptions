# TODO

## Phase 1: Core Functionality & Refinements

### High Priority
- [X] **Refactor `technical_analysis.py`:** (Completed)
  - [X] Modify TA calculation functions (BB, RSI, MACD, IMI, MFI, FVG) to accept a Pandas DataFrame and symbol as input.
  - [X] Ensure functions return DataFrames with new indicator columns.
  - [X] Remove AAPL-specific hardcoding and file I/O dependencies for dashboard integration.
  - [X] Create a helper function to calculate all indicators for a given DataFrame.
- [X] **Implement Data Aggregation in `dashboard_app.py`:** (Completed)
  - [X] In `update_tech_indicators_tab` callback (now part of merged callback), fetch minute data for the selected symbol.
  - [X] Implement/adapt logic to aggregate minute data into 15-minute, hourly, and daily DataFrames.
    - Leverage `technical_analysis.py::aggregate_candles`.
- [X] **Integrate TA Calculations into `dashboard_app.py`:** (Completed)
  - [X] In `update_tech_indicators_tab` (now part of merged callback), call refactored TA functions from `technical_analysis.py` for each aggregated DataFrame (1-min, 15-min, 1-hour, Daily).
  - [X] Handle cases with insufficient data for calculations (basic handling in TA functions, UI shows N/A).
- [X] **Format and Display TA Data in UI:** (Completed)
  - [X] Structure the calculated TA values (latest values) into a list of dictionaries suitable for `dash_table.DataTable`.
  - [X] Update the `columns` and `data` properties of `tech-indicators-table` to display real data, replacing dummy data.
  - [X] Ensure columns are: "Indicator", "1min", "15min", "Hourly", "Daily".
- [X] **Fix `SyntaxError` in `dashboard_app.py` (f-string quotes & backslashes):** (Completed)
  - [X] Corrected nested quote usage in f-strings for 'Implied Volatility', 'Delta', 'Gamma', 'Theta', and 'Vega' fields in the `update_options_chain_stream_data` callback.
  - [X] Removed erroneous backslashes from f-string expressions for 'Gamma', 'Theta', and 'Vega'.
- [X] **Merge Callbacks for Minute Data and Technical Indicators (2025-05-16):** (Completed)
  - [X] Merged `update_minute_data_tab` and `update_tech_indicators_tab` into a single callback `update_data_for_active_tab`.
  - [X] Ensured the new callback correctly updates both tables and the `new-error-event-store` without `allow_duplicate=True`.
  - [X] Verified functionality and error handling.
- [X] **Update Dash App Execution for Dash 3.x (2025-05-16):** (Completed)
  - [X] Changed `app.run_server()` to `app.run()` in `dashboard_app.py` for Dash 3.x compatibility.
- [ ] **Enhance Error Handling:** (Not Started)
  - [ ] Improve error messages displayed in the UI for TA calculation failures and data fetching issues.
- [ ] **Code Cleanup and Optimization:** (Not Started)
  - [ ] Review integrated code for clarity, efficiency, and best practices.

### Low Priority
- [ ] **Advanced TA Features (Future):** (Not Started)
  - [ ] Consider adding more indicators or customization options for existing ones (e.g., RSI overbought/oversold levels).
  - [ ] Explore TA charting capabilities.
  - [ ] Improve FVG display in the UI table.

## Dependencies
- Schwab API client setup and data fetching (`dashboard_utils.data_fetchers`) must be functional (requires user environment setup for APP_KEY, APP_SECRET, CALLBACK_URL for full client features).
- Base Dash app structure (`dashboard_app.py`) should be stable.

## Previous Investigations
- [X] **Investigate Dash Callback Error (Original User Report - 2025-05-16):** (Completed)
  - [X] User reported: `In the callback for output(s): tech-indicators-table.columns tech-indicators-table.data error-message-store.data@... Output 2 (error-message-store.data@...) is already in use.`
  - [X] Initial review confirmed `allow_duplicate=True` was used. This item is now superseded by the callback merge which addresses the root concern.


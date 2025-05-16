# TODO

## Phase 1: Technical Analysis Integration

### High Priority
- [X] **Refactor `technical_analysis.py`:** (Completed)
  - [X] Modify TA calculation functions (BB, RSI, MACD, IMI, MFI, FVG) to accept a Pandas DataFrame and symbol as input.
  - [X] Ensure functions return DataFrames with new indicator columns.
  - [X] Remove AAPL-specific hardcoding and file I/O dependencies for dashboard integration.
  - [X] Create a helper function to calculate all indicators for a given DataFrame.
- [X] **Implement Data Aggregation in `dashboard_app.py`:** (Completed)
  - [X] In `update_tech_indicators_tab` callback, fetch minute data for the selected symbol.
  - [X] Implement/adapt logic to aggregate minute data into 15-minute, hourly, and daily DataFrames.
    - Leverage `technical_analysis.py::aggregate_candles` (renamed from `aggregate_to_15_min` and generalized).
- [X] **Integrate TA Calculations into `dashboard_app.py`:** (Completed)
  - [X] In `update_tech_indicators_tab`, call refactored TA functions from `technical_analysis.py` for each aggregated DataFrame (1-min, 15-min, 1-hour, Daily).
  - [X] Handle cases with insufficient data for calculations (basic handling in TA functions, UI shows N/A).
- [X] **Format and Display TA Data in UI:** (Completed)
  - [X] Structure the calculated TA values (latest values) into a list of dictionaries suitable for `dash_table.DataTable`.
  - [X] Update the `columns` and `data` properties of `tech-indicators-table` to display real data, replacing dummy data.
  - [X] Ensure columns are: "Indicator", "1min", "15min", "Hourly", "Daily".
- [X] **Fix `SyntaxError` in `dashboard_app.py` (f-string quotes & backslashes):** (Completed)
  - [X] Corrected nested quote usage in f-strings for 'Implied Volatility', 'Delta', 'Gamma', 'Theta', and 'Vega' fields in the `update_options_chain_stream_data` callback.
  - [X] Removed erroneous backslashes from f-string expressions for 'Gamma', 'Theta', and 'Vega' that were causing `SyntaxError: f-string expression part cannot include a backslash`.
- [ ] **Enhance Error Handling:** (Not Started)
  - [ ] Improve error messages displayed in the UI for TA calculation failures.
- [ ] **Code Cleanup and Optimization:** (Not Started)
  - [ ] Review integrated code for clarity, efficiency, and best practices.

### Low Priority
- [ ] **Advanced TA Features (Future):** (Not Started)
  - [ ] Consider adding more indicators or customization options.
  - [ ] Explore TA charting capabilities.

## Dependencies
- Schwab API client setup and data fetching (`dashboard_utils.data_fetchers`) must be functional.
- Base Dash app structure (`dashboard_app.py`) should be stable.



- [X] **Investigate Dash Callback Error (2025-05-16):** (Completed)
  - [X] User reported: `In the callback for output(s): tech-indicators-table.columns tech-indicators-table.data error-message-store.data@... Output 2 (error-message-store.data@...) is already in use.`
  - [X] Reviewed `dashboard_app.py` and confirmed all callbacks outputting to `error-message-store.data` (i.e., `update_minute_data_tab`, `update_tech_indicators_tab`, `manage_options_stream`, `update_options_chain_stream_data`) correctly use `allow_duplicate=True`.
  - [X] Conclusion: No code change required in the repository. The error likely originated from an out-of-sync local file or an older version.

# Callback Analysis for error-message-store.data

This document lists all callbacks in `dashboard_app.py` (as of the latest version in the `main` branch) that output to `dcc.Store(id="error-message-store")` and verifies the presence of `allow_duplicate=True`.

**Objective:** To confirm that all necessary `allow_duplicate=True` flags are correctly set, as the user is still experiencing a duplicate output error.

**Findings:**

Based on a thorough review of `/home/ubuntu/manusoptions/dashboard_app.py` from the `main` branch, the following four callbacks target `Output("error-message-store", "data")`:

1.  **`update_minute_data_tab` (Lines approx. 170-175):**
    ```python
    @app.callback(
        Output("minute-data-table", "columns"),
        Output("minute-data-table", "data"),
        Output("error-message-store", "data", allow_duplicate=True), # CORRECT
        Input("selected-symbol-store", "data"),
        State("error-message-store", "data"),
        prevent_initial_call=True
    )
    # ... function definition ...
    ```
    **Verification:** `allow_duplicate=True` is present and correctly set.

2.  **`update_tech_indicators_tab` (Lines approx. 230-236):**
    ```python
    @app.callback(
        Output("tech-indicators-table", "columns"),
        Output("tech-indicators-table", "data"),
        Output("error-message-store", "data", allow_duplicate=True), # CORRECT
        Input("selected-symbol-store", "data"),
        State("error-message-store", "data"),
        prevent_initial_call=True
    )
    # ... function definition ...
    ```
    **Verification:** `allow_duplicate=True` is present and correctly set. This is the callback context mentioned in the user's error message.

3.  **`manage_options_stream` (Lines approx. 351-356):**
    ```python
    @app.callback(
        Output("current-option-keys-store", "data"),
        Output("error-message-store", "data", allow_duplicate=True), # CORRECT
        Input("selected-symbol-store", "data"),
        Input("tabs-main", "value"),
        State("error-message-store", "data"),
        prevent_initial_call=True
    )
    # ... function definition ...
    ```
    **Verification:** `allow_duplicate=True` is present and correctly set.

4.  **`update_options_chain_stream_data` (Lines approx. 411-419):**
    ```python
    @app.callback(
        Output("options-calls-table", "columns"),
        Output("options-calls-table", "data"),
        Output("options-puts-table", "columns"),
        Output("options-puts-table", "data"),
        Output("options-chain-stream-status", "children"),
        Output("error-message-store", "data", allow_duplicate=True), # CORRECT
        Input("options-chain-interval", "n_intervals"),
        State("selected-symbol-store", "data"),
        State("error-message-store", "data"),
        prevent_initial_call=True # Note: This callback was missing prevent_initial_call=True in one of the earlier versions I saw, but it's present now.
    )
    # ... function definition ...
    ```
    **Verification:** `allow_duplicate=True` is present and correctly set.

**Conclusion from Code Review:**
All identified callbacks that output to `error-message-store` in the current `main` branch version of `dashboard_app.py` correctly use the `allow_duplicate=True` parameter.

If the error persists for the user even after `git pull origin main` and with `use_reloader=False`, the cause is likely not a missing `allow_duplicate=True` in the current codebase. Other potential causes could be:
*   The user's local environment is somehow running a different version of the code despite `git pull` (e.g., uncommitted local changes, incorrect file path being executed).
*   A more subtle issue with how Dash is processing the callbacks in the user's specific environment, or an interaction not immediately apparent from static code analysis.
*   An issue within the `dashboard_utils` or `technical_analysis` modules if they are somehow re-importing or re-defining the app or callbacks, though this is less conventional.

**Next Recommended Debugging Step:**
To isolate the issue further, we could try commenting out some of the callbacks that write to `error-message-store` to see if the error disappears, which might help pinpoint a problematic interaction if one exists.

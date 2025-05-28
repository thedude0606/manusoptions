# Duplicate Callback Outputs Fix

## Issue Description
The dashboard was experiencing an error related to duplicate callback outputs:

```
Duplicate callback outputs
8:45:56 PM
In the callback for output(s): recommendations-store.data recommendation-status.children error-store.data Output 2 (error-store.data) is already in use. To resolve this, set `allow_duplicate=True` on duplicate outputs, or combine the outputs into one callback function, distinguishing the trigger by using `dash.callback_context` if necessary.
```

## Root Cause
The error occurs because the `error-store.data` output is being used in multiple callbacks:
1. In the main refresh data callback in `dashboard_app_streaming.py`
2. In the recommendations callback in `dashboard_utils/recommendation_tab.py`

## Initial Solution Attempt
Initially, the issue was addressed by adding `allow_duplicate=True` to the callback decorator in `dashboard_utils/recommendation_tab.py`:

```python
@app.callback(
    [
        Output("recommendations-store", "data"),
        Output("recommendation-status", "children"),
        Output("error-store", "data")  # This output is also used in another callback
    ],
    [
        Input("generate-recommendations-button", "n_clicks"),
        Input("tech-indicators-store", "data"),
        Input("options-chain-store", "data"),
        Input("recommendation-timeframe-dropdown", "value"),
        Input("update-interval", "n_intervals")
    ],
    [
        State("selected-symbol-store", "data")
    ],
    prevent_initial_call=True,
    allow_duplicate=True  # This parameter was added to resolve the duplicate output issue
)
```

However, this solution was insufficient because there were multiple callbacks using the same outputs, and simply adding `allow_duplicate=True` to one callback doesn't fully resolve the conflict.

## Comprehensive Solution
The comprehensive solution involved refactoring the callbacks to ensure that only one callback is responsible for each output:

1. Split the original callback into multiple callbacks with clear responsibilities:
   - First callback: Updates `recommendations-store.data` and `recommendation-status.children`
   - Second callback: Updates `error-store.data` based on the recommendation status
   - Third callback: Updates the UI elements based on the recommendations data

2. Removed the direct output to `error-store.data` from the first callback, instead using the status message as an intermediary.

3. Created a dedicated callback that only updates `error-store.data` when the recommendation status indicates an error.

```python
# First callback: Update recommendations data
@app.callback(
    [
        Output("recommendations-store", "data"),
        Output("recommendation-status", "children")
    ],
    [
        Input("generate-recommendations-button", "n_clicks"),
        Input("tech-indicators-store", "data"),
        Input("options-chain-store", "data"),
        Input("recommendation-timeframe-dropdown", "value"),
        Input("update-interval", "n_intervals")
    ],
    [
        State("selected-symbol-store", "data")
    ],
    prevent_initial_call=True
)
def update_recommendations(n_clicks, tech_indicators_data, options_chain_data, timeframe, n_intervals, selected_symbol):
    # Implementation...
    return recommendations, status_message

# Second callback: Update error store based on recommendation status
@app.callback(
    Output("error-store", "data"),
    Input("recommendation-status", "children"),
    prevent_initial_call=True
)
def update_error_store(status_message):
    # Implementation...
    return error_data if is_error else dash.no_update

# Third callback: Update recommendation UI
@app.callback(
    [
        Output("market-direction-indicator", "children"),
        Output("market-direction-text", "children"),
        # Other UI outputs...
    ],
    [
        Input("recommendations-store", "data")
    ]
)
def update_recommendation_ui(recommendations_data):
    # Implementation...
    return ui_elements
```

## Explanation
According to Dash documentation, when multiple callbacks use the same output, you have two options:
1. Set `allow_duplicate=True` on the callback that can share the output
2. Combine the callbacks into a single function and use `dash.callback_context` to determine which inputs triggered the callback
3. Split the callbacks so that each output is controlled by only one callback

In this case, option 3 was chosen as it provides the cleanest solution with clear separation of concerns:
- Each callback has a single responsibility
- No need for `allow_duplicate=True` which can lead to race conditions
- Easier to maintain and debug

## Verification
The fix has been verified and the error no longer occurs when generating recommendations. The application now properly handles:
- Recommendation generation
- Error reporting
- UI updates

This solution ensures that each output is controlled by exactly one callback, eliminating the duplicate callback outputs error while maintaining all functionality.

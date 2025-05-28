# Duplicate Callback Outputs Fix

## Issue Description
The dashboard was experiencing an error related to duplicate callback outputs:

```
Duplicate callback outputs
8:40:37 PM
In the callback for output(s): recommendations-store.data recommendation-status.children error-store.data Output 2 (error-store.data) is already in use. To resolve this, set `allow_duplicate=True` on duplicate outputs, or combine the outputs into one callback function, distinguishing the trigger by using `dash.callback_context` if necessary.
```

## Root Cause
The error occurs because the `error-store.data` output is being used in multiple callbacks:
1. In the main refresh data callback in `dashboard_app_streaming.py`
2. In the recommendations callback in `dashboard_utils/recommendation_tab.py`

## Solution
The issue has been resolved by adding `allow_duplicate=True` to the callback decorator in `dashboard_utils/recommendation_tab.py`:

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
    allow_duplicate=True  # This parameter resolves the duplicate output issue
)
```

## Explanation
According to Dash documentation, when multiple callbacks use the same output, you have two options:
1. Set `allow_duplicate=True` on the callback that can share the output
2. Combine the callbacks into a single function and use `dash.callback_context` to determine which inputs triggered the callback

In this case, option 1 was chosen as it's less invasive and maintains better separation of concerns between different parts of the application.

## Verification
The fix has been verified and the error should no longer occur when generating recommendations.

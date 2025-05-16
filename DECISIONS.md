# DECISIONS.md

## Key Architectural Choices

- Maintaining consistent column naming conventions across the application
- Using vectorized operations for pandas Series objects to avoid ambiguous truth value errors
- Ensuring proper handling of DatetimeIndex for time series data

## Technology Selections

- Python for the main application logic
- Git for version control
- Pandas for data manipulation and analysis
- NumPy for numerical operations

## Design Patterns Used

- Factory pattern for client initialization
- Observer pattern for error handling and notification

## Rationale for Important Decisions

- **Fix for `calculate_all_technical_indicators()` TypeError (2025-05-16):**
    - **Issue:** The function `calculate_all_technical_indicators` was called with an unexpected keyword argument `period_name` in `dashboard_app.py` (line 333).
    - **Investigation:** The function definition in `technical_analysis.py` (`def calculate_all_technical_indicators(df, symbol="N/A")`) showed it only accepts `df` and `symbol` as arguments.
    - **Decision:** Modified the call in `dashboard_app.py` to remove the `period_name` argument. The period information, which was previously passed via `period_name`, is now concatenated with the `selected_symbol` and passed as the `symbol` argument (e.g., `symbol=f"{selected_symbol}_{period}"`). This aligns the function call with its definition and ensures the period context is still available if needed within the function or for logging/debugging purposes via the symbol string.
    - **Rationale:** This change directly addresses the `TypeError` by ensuring the function is called with the correct arguments. Passing the period information as part of the symbol string is a common practice to provide context without altering the function signature, especially if the function itself doesn't strictly require the period for its internal calculations but the context is useful for downstream processing or identification of the resulting data.

- **Fix for `MinData-Format-SPY: Index is not DatetimeIndex after fetch` Error (2025-05-16):**
    - **Issue:** The application was logging an error `Index is not DatetimeIndex after fetch` in `dashboard_app.py` when processing minute data. This occurred because the DataFrame returned by `get_minute_data` in `dashboard_utils/data_fetchers.py` did not have a `DatetimeIndex`, and the expected `timestamp` column (as a datetime object) was not correctly prepared for `dashboard_app.py`.
    - **Investigation:** Analysis of `dashboard_utils/data_fetchers.py` revealed two issues in the `get_minute_data` function:
        1. The timestamp column, after conversion from epoch milliseconds to a datetime object, was being renamed to `"Timestamp"` (capitalized).
        2. Crucially, this `"Timestamp"` column was then being converted to a string using `.dt.strftime(...)` before the DataFrame was returned.
        In `dashboard_app.py`, the code attempts to convert a column named `"timestamp"` (lowercase) to a `DatetimeIndex` and then set it as the index. This failed because the column was named `"Timestamp"` and was already a string.
    - **Decision:** Modified `dashboard_utils/data_fetchers.py` within the `get_minute_data` function:
        1. Ensured the column resulting from `pd.to_datetime(all_candles_df["datetime"], unit="ms", utc=True).dt.tz_convert("America/New_York")` is named `"timestamp"` (lowercase).
        2. Removed the line `all_candles_df["Timestamp"] = all_candles_df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S %Z")`. The `"timestamp"` column is now returned as a proper datetime object.
        3. Updated the `columns_to_keep` list to use `"timestamp"`.
        4. Added a comment to emphasize that the `"timestamp"` column should remain a datetime object and string formatting should be handled by the consuming function if needed for display purposes.
    - **Rationale:** This change ensures that `get_minute_data` returns a DataFrame with a `"timestamp"` column containing datetime objects. This aligns with the expectations of `dashboard_app.py`, allowing it to correctly convert this column to a `DatetimeIndex` and perform further time-based operations or technical analysis calculations. Delaying string formatting to the presentation layer (e.g., just before displaying in a Dash table) is a better practice as it keeps the underlying data in its correct type for processing.

- **Fix for `The truth value of a Series is ambiguous` Error in RSI Calculation (2025-05-16):**
    - **Issue:** The application was throwing a `ValueError: The truth value of a Series is ambiguous. Use a.empty, a.bool(), a.item(), a.any() or a.all()` error in the RSI calculation within `technical_analysis.py`. This occurred in the `calculate_rsi` function when attempting to use a pandas Series in a scalar context within a conditional expression.
    - **Investigation:** The error was occurring at this line:
      ```python
      rs = np.where(loss == 0, np.inf if gain > 0 else 0, gain / loss)
      ```
      The issue is that `gain` is a pandas Series, but it's being used in a scalar context with the conditional expression `np.inf if gain > 0 else 0`. In pandas, you can't directly use a Series in an if-statement because it's ambiguous whether it should evaluate to True if any value is true, all values are true, etc.
    - **Decision:** Modified the line to use nested `np.where` calls instead of the scalar conditional:
      ```python
      rs = np.where(loss == 0, np.where(gain > 0, np.inf, 0), gain / loss)
      ```
      This approach properly handles Series objects by using vectorized operations throughout, avoiding any ambiguous truth value evaluations.
    - **Rationale:** The fix ensures that all operations on pandas Series objects use proper vectorized methods, avoiding the ambiguous truth value error. Using nested `np.where` calls is a common pattern for handling complex conditional logic with pandas Series objects, as it maintains the vectorized nature of the operations and avoids scalar context evaluations. This approach is more efficient and correctly handles element-wise operations on the Series data.

- **Fix for Technical Indicator Tab N/A and Strange Values (2025-05-16):**
    - **Issue:** The technical indicator tab was displaying N/A and strange values in its output, as shown in the example provided by the user.
    - **Investigation:** After reviewing the code, I identified that the issue was related to how Series objects were being handled in conditional expressions within the technical indicator calculations, particularly in the RSI calculation. Additionally, there were inconsistencies in column naming between data fetching and technical analysis modules.
    - **Decision:** 
      1. Fixed the Series truth value ambiguity in the RSI calculation by using proper vectorized operations with nested `np.where` calls.
      2. Ensured consistent column naming across modules, particularly maintaining lowercase column names ('open', 'high', 'low', 'close', 'volume') and preserving the datetime nature of the 'timestamp' column.
      3. Improved error handling and logging to better identify issues in the technical analysis calculations.
    - **Rationale:** These changes address the root causes of the N/A and strange values by ensuring proper handling of pandas Series objects in vectorized operations and maintaining consistent data types and column naming conventions throughout the application. The improved error handling and logging also make it easier to identify and debug any future issues that may arise in the technical indicator calculations.

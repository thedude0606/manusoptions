# Architectural Decisions

## Callback Refactoring (May 20, 2025)

### Problem
The Dash application is experiencing errors due to duplicate callback outputs, particularly for:
- error-store.data
- options-chain-store.data
- expiration-date-dropdown.options
- expiration-date-dropdown.value
- options-chain-status.children

These errors occur because multiple callbacks are targeting the same outputs, which is not allowed in Dash unless explicitly permitted with `allow_duplicate=True`. While using `allow_duplicate=True` is a quick fix, it's not the recommended approach as it can lead to race conditions and unpredictable behavior.

### Solution
Refactor the callbacks by combining those that share outputs into single callback functions. This approach:
1. Eliminates the need for `allow_duplicate=True`
2. Reduces the risk of race conditions
3. Improves code maintainability
4. Follows Dash best practices

### Implementation Strategy
1. Identify all callbacks that share outputs
2. Combine these callbacks into unified functions
3. Use `dash.callback_context` to determine which input triggered the callback
4. Preserve all existing logic while consolidating the output generation
5. Ensure all edge cases are handled properly

### Benefits
- Resolves the duplicate callback outputs error
- Improves application stability
- Reduces potential for race conditions
- Makes the codebase more maintainable
- Follows Dash framework best practices

## Options Chain Data Fix (May 20, 2025)

### Problem
The options chain tab in the dashboard was displaying blank values for last, bid, and ask fields, making it difficult for users to evaluate option contracts effectively.

### Root Cause
The backend data fetcher was not ensuring that these critical price fields were always populated. When the Schwab API returned null or missing values for these fields, they remained blank in the UI.

### Solution
Modified the `get_options_chain_data` function in `dashboard_utils/data_fetchers.py` to:
1. Check for missing or null values in lastPrice, bidPrice, and askPrice fields
2. Provide default values (0.0) when these fields are missing or null
3. Add debug logging to track when default values are applied
4. Add sample data logging to verify field population

### Implementation Details
- Added explicit checks for each price field (lastPrice, bidPrice, askPrice)
- Applied consistent default values (0.0) when fields are missing or null
- Added logging to track when defaults are applied and to verify data structure
- Maintained the existing data flow and UI rendering logic

### Benefits
- Ensures consistent display of price data in the options chain tab
- Improves user experience by eliminating blank fields
- Maintains data integrity by using appropriate default values
- Provides better debugging information through enhanced logging

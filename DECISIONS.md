# Design Decisions

## Options Generations (Recommendations) Tab

### Issue Identified
- Options generations tab (implemented as the Recommendations tab) was not functioning
- No visible errors in the UI, but the tab failed to display any recommendations

### Investigation
- Examined the recommendation_tab.py implementation and its callback dependencies
- Found that the Recommendations tab relies on a data store called "selected-symbol-store"
- This store was defined in dashboard_app_old.py but missing from the current dashboard_app.py
- Without this store, the recommendation callbacks couldn't access the selected symbol data

### Implementation Approach
- Added the missing "selected-symbol-store" to dashboard_app.py
- Added an update interval component for periodic refreshes
- Updated the refresh_data callback to populate the selected-symbol-store
- Enhanced the technical indicators store to include a timeframe_data structure for compatibility
- Ensured all error handling paths correctly handle the new store

## Schwab API Options Chain Method

### Issue Identified
- Options chain tab was failing with error: `'Client' object has no attribute 'get_option_chain'`
- Code was inconsistently using both `get_option_chain` and `option_chains` methods

### Investigation
- Reviewed Schwab API client documentation and source code
- Confirmed that the correct method name is `option_chains`, not `get_option_chain`
- Identified all occurrences of the incorrect method name in the codebase

### Implementation Approach
- Updated `data_fetchers.py` to use the correct `option_chains` method
- Ensured parameter names match the API documentation (e.g., `includeUnderlyingQuote` instead of `includeQuotes`)
- Verified no other occurrences of the incorrect method name remained in the codebase

## Minute Data Handling

### Current Implementation
- `fetch_minute_data.py` currently pulls 90 days of 1-minute data
- `fetch_minute_data_batched.py` already implements a 60-day pull for 1-minute data
- Configuration in `config.py` has `MINUTE_DATA_CONFIG` with `default_days: 60`

### Required Changes
- Standardize all minute data pulls to always use 60 days without a time frame option
- Ensure consistency between both fetch scripts
- Update any references to time frames in the codebase

### Implementation Approach
- Modify `fetch_minute_data.py` to use the 60-day setting from config
- Ensure `fetch_minute_data_batched.py` consistently uses 60 days
- Remove any user-configurable time frame options for minute data pulls

## Technical Indicators Calculation

### Current Implementation
- `technical_analysis.py` has a flexible indicator calculation pipeline
- Currently calculates indicators for a single timeframe (the input data timeframe)
- Has `resample_ohlcv` function that can aggregate data to different timeframes
- No explicit multi-timeframe support in the main calculation functions

### Required Changes
- Implement technical indicator calculations for multiple timeframes:
  - 1 minute
  - 15 minute
  - 30 minute
  - 1 hour
  - Daily

### Implementation Approach
- Create a new function to handle multi-timeframe calculations
- Use the existing `resample_ohlcv` function to generate different timeframe data
- Calculate indicators for each timeframe
- Return a dictionary of DataFrames, one for each timeframe with its indicators
- Ensure proper error handling and logging for each timeframe calculation

## Data Structure Design

### Current Implementation
- Single DataFrame with indicators for one timeframe

### New Implementation
- Dictionary of DataFrames, keyed by timeframe string
- Each DataFrame contains the indicators for that specific timeframe
- Consistent column naming across timeframes
- Example structure:
  ```
  {
    '1min': DataFrame with 1-minute indicators,
    '15min': DataFrame with 15-minute indicators,
    '30min': DataFrame with 30-minute indicators,
    '1hour': DataFrame with 1-hour indicators,
    'daily': DataFrame with daily indicators
  }
  ```

## Integration with Existing Code

### Dashboard Integration
- Update dashboard code to handle multi-timeframe data
- Add timeframe selection in the UI
- Display indicators for the selected timeframe

### API Integration
- Ensure API endpoints can handle multi-timeframe data
- Update documentation to reflect new data structure

## Performance Considerations

### Data Volume
- Processing multiple timeframes increases computation time
- Consider implementing caching for higher timeframes
- Optimize resampling operations

### Memory Usage
- Multiple DataFrames will increase memory usage
- Consider implementing lazy loading or on-demand calculation for less frequently used timeframes

## Testing Strategy

### Unit Tests
- Create tests for each timeframe calculation
- Verify indicator values match expected results for each timeframe

### Integration Tests
- Test end-to-end flow from data fetching to multi-timeframe indicator calculation
- Verify dashboard correctly displays indicators for each timeframe

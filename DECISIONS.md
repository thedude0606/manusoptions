# Design Decisions

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

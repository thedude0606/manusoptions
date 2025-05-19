# Design Decisions

## Incremental Update Strategy (May 19, 2025)

### Current Implementation Analysis
- The app currently fetches all 90 days of historical data every time a symbol is selected or a tab is changed
- There's no caching mechanism to store previously fetched data
- This causes unnecessary API calls and processing overhead
- The `get_minute_data` function already supports a `since_timestamp` parameter but it's not fully utilized

### Cache Design
- **Structure**: Global dictionary to store data by symbol
  ```python
  MINUTE_DATA_CACHE = {
      'SYMBOL': {
          'data': pandas_dataframe,
          'last_update': datetime_object,
          'timeframe_data': {
              '1min': dataframe_or_records,
              '5min': dataframe_or_records,
              # other timeframes
          }
      }
  }
  ```
- **Cache Invalidation**: 
  - Default maximum age: 24 hours (configurable)
  - Force refresh on explicit user action (symbol change, manual refresh)
  - Automatic periodic updates every 30 seconds

### Incremental Update Logic
1. Check if symbol exists in cache
   - If not, fetch full 90-day history
   - If yes, check last update timestamp
2. For updates, fetch only data since last update (minus small buffer to avoid gaps)
3. Merge new data with cached data
4. Update cache timestamp

### Technical Indicator Recalculation
- Only recalculate indicators for timeframes being viewed
- Only process new data points, not the entire dataset
- Store calculated indicators in the cache to avoid redundant calculations

### Error Handling
- Display clear error messages when data fetching fails
- Fall back to cached data when possible
- Implement retry mechanism with exponential backoff for transient errors

### Loading State Management
- Show loading indicators during initial data fetch
- Use non-blocking updates for periodic refreshes
- Provide visual feedback when new data is being merged

### Periodic Update Implementation
- Use Dash's interval component to trigger updates every 30 seconds
- Consider future enhancement to use WebSocket streaming for real-time updates

### Performance Considerations
- Minimize redundant calculations
- Use efficient data structures for merging
- Implement debouncing for rapid user interactions

This design balances responsiveness with efficiency, reducing unnecessary API calls while ensuring users have access to the most current data.

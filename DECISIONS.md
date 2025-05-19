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

## Table Sorting and Filtering Strategy (May 19, 2025)

### Requirements Analysis
- All tables need both simple and advanced filtering capabilities
- Users should be able to sort by any column
- Multi-column sorting should be supported
- Filter UI should appear when column headers are clicked
- Clear visual indicators for sorting and filtering should be present

### Design Approach
- **Consistent Implementation**: Use the same approach for all tables (minute data, technical indicators, options chain)
- **Dash DataTable Features**: Leverage built-in Dash DataTable sorting and filtering capabilities
- **Filter Types**:
  - Simple text-based filtering for quick searches
  - Advanced filtering with operators (equals, greater than, less than, etc.)
  - Toggle between filter types via UI controls

### Implementation Strategy
1. **Table Configuration**:
   - Enable `sort_action="native"` for client-side sorting
   - Set `filter_action="native"` for client-side filtering
   - Configure `sort_mode="multi"` to allow sorting by multiple columns

2. **Column Definitions**:
   - Define filter operators for each column based on data type
   - Numeric columns: Support comparison operators (>, <, =, etc.)
   - Text columns: Support contains, exact match, starts with, etc.
   - Date columns: Support date range filtering

3. **UI Enhancements**:
   - Add filter icons in column headers
   - Provide visual feedback for active filters and sort direction
   - Include filter reset functionality

4. **Callback Structure**:
   - Maintain existing data flow while adding filter state persistence
   - Ensure filters persist across data refreshes
   - Preserve user-defined sorting across updates

This approach provides a powerful yet intuitive interface for data exploration while maintaining consistency across all tables in the application.

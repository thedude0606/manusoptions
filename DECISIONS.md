# Design Decisions

## Callback Structure and Duplicate Output Resolution (May 20, 2025)

### Issue Analysis
- The application was experiencing a "Duplicate callback outputs" error
- Error specifically mentioned outputs: options-chain-store.data, expiration-date-dropdown.options, expiration-date-dropdown.value, options-chain-status.children, and error-store.data
- This occurs when multiple callbacks attempt to update the same output component without proper handling

### Code Audit Findings
- A comprehensive audit of all callbacks in the codebase was conducted
- All callbacks that output to the same components (particularly error-store.data) already have `allow_duplicate=True` flags set
- The error is not due to missing flags in the code but likely due to a stale or misconfigured environment

### Resolution Strategy
- **Environment Refresh**: Rather than code changes, a complete environment refresh is recommended:
  1. Create a fresh virtual environment
  2. Reinstall all dependencies
  3. Clear browser cache
  4. Restart the Dash server with `use_reloader=False`

- **Documentation**: Added comprehensive documentation about callback structure and potential environment issues
- **Future Prevention**: Consider implementing a callback registration system that automatically checks for and prevents duplicate outputs

### Technical Rationale
- Dash's callback system requires explicit handling of duplicate outputs
- When multiple callbacks target the same output, each must include `allow_duplicate=True` except for the first one
- In complex applications, stale environments can sometimes maintain outdated callback registrations
- A complete environment refresh ensures all callbacks are properly registered with the current code

This approach addresses the root cause without introducing unnecessary code changes that could potentially create new issues.

## Recommendation Engine Architecture (May 19, 2025)

### Requirements Analysis
- The recommendation engine needs to analyze technical indicators to identify market direction
- It must evaluate options chain data for optimal strike prices and expiration dates
- It should calculate risk/reward ratios for potential trades
- It must generate actionable buy/sell signals with confidence scores
- The UI should be simple, showing only the top 5 contracts with highest confidence
- Each recommendation should include target buy price, target sell price, and timeframe
- The focus is on hourly trading and swing trading with minimum 10% expected profit
- Recommendations should consider Greeks and IV in the evaluation

### Architecture Design
- **Modular Component Structure**: Separate the recommendation engine logic from the UI components
- **Data Flow**: Technical indicators and options chain data → Recommendation engine → UI display
- **Calculation Pipeline**:
  1. Market direction analysis based on technical indicators
  2. Options chain filtering and evaluation
  3. Risk/reward calculation
  4. Confidence score generation
  5. Top recommendations selection

### Key Components
1. **RecommendationEngine Class**:
   - Core logic encapsulated in a single class
   - Stateless design for easy testing and maintenance
   - Public methods for each step in the recommendation pipeline
   - Configurable parameters for thresholds and filters

2. **Recommendation Tab Module**:
   - Separate UI module following the existing tab pattern
   - Callback registration function for clean integration
   - Responsive layout with panels for different information types

3. **Data Integration**:
   - Leverage existing data stores (tech-indicators-store, options-chain-store)
   - Use callback context to determine update triggers
   - Maintain consistency with the existing caching strategy

### Technical Indicator Analysis
- **Market Direction Determination**:
  - Use a scoring system (0-100) for bullish and bearish signals
  - Consider multiple indicators with weighted importance
  - RSI, MACD, Bollinger Bands given higher weight
  - MFI and IMI used as confirming indicators
  - Fair Value Gaps given significant weight when present

### Options Evaluation Strategy
- **Filtering Criteria**:
  - Minimum open interest threshold to ensure liquidity
  - Days to expiration range (1-14 days) for hourly/swing trading
  - Bid-ask spread percentage to avoid illiquid options

- **Scoring System**:
  - Base score adjusted by market direction alignment
  - Greeks evaluation with optimal ranges:
    - Delta: Prefer 0.3-0.7 range (not too far OTM or ITM)
    - Gamma: Higher gamma preferred for short-term trades
    - Theta: Lower absolute theta preferred to minimize time decay
    - Vega: Lower vega preferred to reduce volatility exposure
  - IV evaluation with penalties for very high (>60%) or very low (<15%) values
  - Strike distance from current price factored into score

### Risk/Reward Calculation
- **Risk Definition**: Premium paid for the option
- **Reward Projection**:
  - Based on delta and projected underlying price movement
  - Default projection of 2% move in underlying
  - Expected profit percentage calculated as (projected profit / risk) * 100
  - Minimum threshold of 10% expected profit

- **Target Price and Timeframe**:
  - Target sell price = current price * (1 + minimum expected profit)
  - Target timeframe calculated based on theta decay
  - Formula: hours until theta decay would reduce price by expected profit percentage
  - Reasonable bounds applied (1-72 hours)

### Confidence Score System
- **Base Score**: 50 (neutral)
- **Market Direction Adjustment**:
  - For calls: +/- based on bullish/bearish score
  - For puts: +/- based on bearish/bullish score
- **Greeks Adjustments**:
  - Delta: +10 for optimal range, decreasing as delta moves toward 0 or 1
  - Gamma: +50 * gamma value (higher gamma = higher score)
  - Theta: -20 * abs(theta) (more negative theta = lower score)
  - Vega: -10 * abs(vega) (higher vega = lower score)
- **Other Factors**:
  - Spread percentage: -100 * spread_pct (wider spread = lower score)
  - Strike distance: -50 * distance_pct (further from ATM = lower score)
  - Days to expiration: -5 * (3 - DTE) for DTE < 3 (too short = lower score)
  - Expected profit: +10 if >= 10%, -20 if < 10%

### UI Design Decisions
- **Panel-Based Layout**:
  - Market direction panel with visual indicators
  - Separate tables for call and put recommendations
  - Contract details panel for selected recommendation

- **Visual Indicators**:
  - Color coding for bullish (green), bearish (red), neutral (gray)
  - Confidence score highlighting (green for high confidence)
  - Clear display of target prices and timeframes

- **Interaction Model**:
  - Click on recommendation to see detailed Greeks
  - Dropdown for timeframe selection
  - Automatic updates with the global update interval

### Testing Strategy
- **Unit Tests**:
  - Test each component of the recommendation pipeline
  - Validate calculations with known inputs and expected outputs
  - Ensure confidence scores and risk/reward ratios are calculated correctly

- **Integration Tests**:
  - Verify data flow from stores to recommendation engine
  - Validate UI updates with recommendation changes

### Performance Considerations
- **Calculation Efficiency**:
  - Perform calculations only when necessary (new data available)
  - Reuse market direction analysis for multiple options evaluation
  - Filter options early in the pipeline to reduce processing load

- **UI Responsiveness**:
  - Use loading indicators for calculation processes
  - Separate store for recommendations to avoid redundant calculations
  - Leverage Dash's callback prevention for unchanged inputs

This architecture balances accuracy, performance, and usability while maintaining consistency with the existing application structure and data flow patterns.

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

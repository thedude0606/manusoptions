# Design Decisions

## Multi-Timeframe Technical Indicators

### Decision
Implement technical indicators calculation for multiple timeframes (1min, 15min, 30min, 1hour, daily) in a single function.

### Rationale
- Users need to analyze market data across different timeframes to make informed trading decisions
- Calculating indicators for multiple timeframes in a single function reduces code duplication
- Storing all timeframe data in a single table with a timeframe column simplifies the UI implementation

### Implementation Details
- Created `calculate_multi_timeframe_indicators` function in technical_analysis.py
- Modified `get_technical_indicators` in data_fetchers.py to return a single table with a timeframe column
- Updated dashboard_app.py to handle the new data structure

## Standardized 60-Day Minute Data Pull

### Decision
Standardize minute data pulls to always use 60 days of data.

### Rationale
- Consistent data window ensures reliable technical indicator calculations
- Reduces API calls and improves performance
- Simplifies the UI by removing the need for a date range selector

### Implementation Details
- Updated `fetch_minute_data.py` to consistently use 60-day data pull
- Modified `get_minute_data` in data_fetchers.py to always use 60 days

## Streaming Functionality Troubleshooting

### Decision
Investigate and fix the streaming functionality that is not working despite correct configuration.

### Rationale
- The streaming interval component is correctly set to disabled=False by default
- The toggle callback logic is properly implemented
- Debug logging is present throughout the code
- Yet streaming functionality is still not working

### Implementation Details
- Created logs directory which was missing, preventing proper logging
- Enhanced debug logging to trace the streaming lifecycle
- Identified potential issues:
  1. StreamingManager may not be initializing properly
  2. Callback wiring may be incorrect
  3. Authentication or connection issues with Schwab API
  4. File system permissions may be preventing log creation

### Technical Considerations
- The absence of logs directory suggests the StreamingManager initialization code may not be executing
- Need to verify that dashboard_app_streaming.py is being used instead of dashboard_app.py
- Need to ensure proper authentication with Schwab API
- Need to verify WebSocket connection establishment
- Need to trace data flow from StreamingManager to UI components

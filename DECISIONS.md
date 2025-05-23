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

## Options Chain Real-Time Updates

### Decision
Integrate the existing StreamingManager into dashboard_app.py to enable real-time updates for the options chain.

### Rationale
- The current implementation relies on polling and REST API calls, which doesn't provide real-time updates
- A fully implemented StreamingManager exists but is not being used in dashboard_app.py
- WebSocket-based streaming provides more efficient and timely updates compared to polling

### Implementation Details
- Integrate StreamingManager into dashboard_app.py
- Add callbacks to handle streaming data updates in the UI
- Add status indicators for streaming connection in the options chain tab
- Use dcc.Interval for periodic UI updates from the streaming data
- Set real-time updates to be enabled by default per user request
- Ensure streaming interval component has disabled=False by default in the layout
- Implement toggle callback to correctly enable/disable the interval based on user selection
- Add comprehensive debug logging to verify data flow from StreamingManager to UI

### Technical Considerations
- The StreamingManager runs in a background thread to avoid blocking the main Dash application thread
- Thread-safe data sharing is handled through locks in the StreamingManager
- The UI is updated through periodic polling of the StreamingManager's latest data
- Real-time updates are always enabled by default to provide immediate market data
- Debug logging is implemented at key points in the data flow to facilitate troubleshooting

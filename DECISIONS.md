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

## Streaming Data Field Mapping

### Decision
Implement a robust, dynamic mapping system between streaming data contract fields and options table DataFrame columns.

### Rationale
- The original implementation used hardcoded field mappings that were incomplete
- Streaming data contract fields use numeric indices (0-55) that need to be mapped to meaningful column names
- Different field names may be used between the streaming contract and the DataFrame columns
- A comprehensive mapping ensures all relevant data is updated in real-time

### Implementation Details
- Created a dedicated `StreamingFieldMapper` class in a new module
- Implemented a complete mapping of all 56 streamer field numbers (0-55) to field names
- Added a secondary mapping from field names to DataFrame column names
- Integrated the mapper into the options table update callback
- Enhanced logging to track which fields are being updated from streaming data

### Technical Considerations
- The mapper provides a single source of truth for field mappings
- Dynamic mapping allows for future expansion without code changes
- Improved error handling for missing or mismatched fields
- Better debugging capabilities through detailed logging of field updates

## Contract Key Normalization

### Decision
Synchronize contract key normalization between streaming data and DataFrame rows to ensure proper matching.

### Rationale
- Streaming data uses normalized contract keys (e.g., AAPL_250523C190.0)
- DataFrame rows use non-normalized symbols (e.g., AAPL  250523C00190000)
- This mismatch prevents the UI from updating with streaming data
- Consistent normalization ensures proper matching between streaming data and DataFrame rows

### Implementation Details
- Added normalization of DataFrame 'symbol' column in the update_options_tables callback
- Created a mapping from normalized symbols to DataFrame indices for efficient lookups
- Used the existing normalize_contract_key function from contract_utils.py
- Enhanced logging to track the number of contracts and fields updated

### Technical Considerations
- Normalization is performed only during the update process, not modifying the original data
- The temporary normalized_symbol column is removed after processing
- This approach maintains compatibility with other parts of the application
- Performance impact is minimal as normalization is only done once per update cycle

## Enhanced Contract Key Normalization

### Decision
Enhance contract key normalization to handle additional format patterns, including Schwab streaming format with spaces.

### Rationale
- The existing normalization logic didn't handle all possible contract key formats
- Schwab streaming data can include contract keys with spaces in specific positions
- Missing a format pattern can lead to failed matches between streaming data and DataFrame rows
- Comprehensive pattern matching ensures robust handling of all contract key formats

### Implementation Details
- Added Pattern 4 to normalize_contract_key function to handle Schwab streaming format with spaces
- Pattern 4 regex: r'([A-Z]+)\s+(\d{6})([CP])(\d{8})'
- This handles formats like "AAPL  250523C00190000" with spaces after the symbol
- Updated documentation to reflect the enhancement

### Technical Considerations
- The enhancement maintains backward compatibility with existing code
- No changes to the normalized output format were required
- The approach follows the existing pattern-matching strategy
- This fix addresses edge cases that may have been causing streaming data mismatches

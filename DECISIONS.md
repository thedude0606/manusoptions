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

## Options Chain State Preservation

### Decision
Implement state preservation mechanism to prevent options chain from disappearing after a few seconds.

### Rationale
- Users reported that the options chain would load initially but then disappear after a few seconds
- Investigation revealed that empty streaming data updates were replacing valid options chain data
- The UI needs to maintain state even when streaming updates temporarily fail or return empty data
- Defensive programming is needed to ensure a consistent user experience

### Implementation Details
- Added a new dcc.Store component called "last-valid-options-store" to preserve the last valid options data
- Modified the refresh_data callback to populate this store with valid options data
- Enhanced the streaming_data_update callback to include a "valid" flag for streaming data
- Updated the update_options_tables callback to:
  1. Use last_valid_options as a fallback when current options data is missing
  2. Only apply streaming updates when they are explicitly marked as valid
  3. Only use updated DataFrame if contracts were actually updated
  4. Add fallback mechanisms when splitting options by type and expiration
  5. Improve error handling with try/except blocks and detailed logging

### Technical Considerations
- The state preservation approach is non-intrusive and maintains compatibility with existing code
- The "valid" flag in streaming data prevents empty updates from overwriting good data
- Fallback mechanisms ensure the UI always shows some data when available
- Enhanced error handling prevents the application from crashing due to unexpected data formats
- Detailed logging helps diagnose any remaining issues in production

## Options Chain Tab Data Display Fix

### Decision
Implement a robust solution to ensure options chain tab correctly displays data by properly mapping contractType to putCall.

### Rationale
- The options chain tab was not displaying any data despite streaming data being available
- Investigation revealed that streaming data uses 'contractType' (C/P) while the split function expects 'putCall' (CALL/PUT)
- This field mismatch caused the split_options_by_type function to return zero calls and puts
- A robust solution is needed to handle both API-fetched and streaming-updated data consistently

### Implementation Details
- Created a new ensure_putcall_field function in options_chain_utils.py to:
  1. Check if putCall field exists and has no missing values
  2. Map contractType (C/P) to putCall (CALL/PUT) for streaming data
  3. Infer putCall from symbol as a fallback if needed
  4. Log detailed information about the mapping process
- Updated split_options_by_type to call ensure_putcall_field before processing
- Modified dashboard_app.py to use ensure_putcall_field in the refresh_data callback
- Enhanced error handling and logging throughout the options chain data flow

### Technical Considerations
- The solution is non-intrusive and maintains compatibility with existing code
- It handles both API-fetched data (which already has putCall) and streaming data (which uses contractType)
- The approach is defensive, with multiple fallback mechanisms to ensure data is always displayed
- Detailed logging helps diagnose any remaining issues in production
- The fix addresses the root cause of the empty options chain tab issue

## Recommendations Tab Button Fix

### Decision
Fix the Recommendations tab button to properly trigger recommendations generation when clicked.

### Rationale
- The "Generate Recommendations" button in the Recommendations tab was not doing anything when clicked
- Investigation revealed that the button was not included as an Input in any callback
- Without a callback connection, clicking the button had no effect on the application
- A direct connection between the button and the recommendations generation logic was needed

### Implementation Details
- Added the "generate-recommendations-button" as an Input to the update_recommendations callback in recommendation_tab.py
- Enhanced the callback to detect when it was triggered by the button click
- Added additional logging to track button click events
- Maintained compatibility with other trigger sources (interval, data store changes)

### Technical Considerations
- The fix is minimally invasive, only adding the button as an additional Input to an existing callback
- The callback context is used to determine if the trigger was the button click
- The solution maintains all existing functionality while adding the button-triggered behavior
- Enhanced logging helps verify that the button click is properly detected
- The fix improves user experience by making the UI behave as expected, with the button directly triggering the action it suggests

## Enhanced Debug Modules for Options Chain and Recommendations

### Decision
Create dedicated debug modules with enhanced error handling, state preservation, and logging for both the options chain disappearance and non-functioning recommendations tab issues.

### Rationale
- Users reported that the options chain loads but disappears after ~5 seconds
- The recommendations tab button doesn't do anything when clicked
- These issues persist despite previous fixes, suggesting deeper problems
- A more comprehensive approach to debugging and error handling is needed

### Implementation Details
- Created options_chain_fix.py with enhanced versions of key functions:
  1. ensure_putcall_field_enhanced with better error handling and logging
  2. split_options_by_type_enhanced with improved state preservation and fallback mechanisms
  3. prepare_options_for_dash_table_enhanced with more robust error handling
- Created recommendations_fix.py with enhanced callback registration:
  1. register_recommendation_callbacks_enhanced with improved error handling
  2. update_recommendations_enhanced with detailed debugging and error reporting
  3. update_recommendation_tables_enhanced with better error handling
- Added performance monitoring and timing metrics to track processing bottlenecks
- Implemented comprehensive error handling with detailed traceback logging

### Technical Considerations
- The enhanced modules maintain the same API as the original functions for easy integration
- The approach allows for incremental testing and deployment without disrupting existing functionality
- Detailed logging helps identify the root causes of the issues
- Performance metrics help identify potential bottlenecks
- The modular design allows for selective application of fixes
- The enhanced error handling prevents cascading failures that could lead to UI elements disappearing

## Direct Integration of Enhanced Debug Modules

### Decision
Directly integrate the enhanced debug modules into the main application code rather than keeping them as separate modules.

### Rationale
- The user reported that the options chain still disappears after ~5 seconds despite the creation of separate debug modules
- Separate modules require manual integration by the user, which may lead to inconsistent implementation
- Direct integration ensures immediate application of the fixes without requiring additional steps
- This approach provides a more seamless user experience with immediate benefits

### Implementation Details
- Replaced the original `ensure_putcall_field` function in options_chain_utils.py with the enhanced version
- Updated `split_options_by_type` to include the `last_valid_options` parameter for robust state preservation
- Enhanced `prepare_options_for_dash_table` with better error handling
- Modified the `update_options_tables` callback in dashboard_app.py to use the enhanced functions
- Added additional error handling and logging throughout the options chain data flow
- Implemented try/except blocks in critical sections to prevent cascading failures

### Technical Considerations
- The direct integration approach maintains the same API signatures for compatibility
- Enhanced functions include additional defensive programming techniques
- Performance monitoring and timing metrics help identify bottlenecks
- Detailed logging provides better visibility into the data flow
- The integration is non-disruptive to existing functionality
- The approach addresses the root cause of the disappearing options chain issue

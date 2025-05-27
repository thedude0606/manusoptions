# TODO List

## High Priority
- [x] Analyze repository structure and code
- [x] Document design decisions for required changes
- [x] Update `fetch_minute_data.py` to consistently use 60-day data pull
- [x] Implement multi-timeframe technical indicator calculations
- [x] Update configuration files if needed
- [x] Push code changes to GitHub repository
- [x] Fix options chain tab API method error
- [x] Fix options generations (Recommendations) tab functionality
- [x] Integrate StreamingManager into dashboard_app.py for real-time options chain updates
- [x] Add callbacks to handle streaming data updates in the UI
- [x] Add status indicators for streaming connection in the options chain tab
- [x] Set real-time updates to be enabled by default
- [x] Test real-time updates with various symbols
- [x] Fix mapping issue between streaming data contract keys and options table data
- [x] Implement robust field mapping for all streamer contract fields
- [x] Fix contract key normalization mismatch between streaming data and DataFrame rows
- [x] Enhance contract key normalization to handle additional format patterns
- [x] Fix issue where options chain disappears after a few seconds
- [x] Implement state preservation for options chain data
- [x] Fix options chain tab not showing any data due to missing putCall field mapping
- [x] Implement robust ensure_putcall_field function for both API and streaming data
- [x] Fix Recommendations tab button not working by adding it as a callback trigger
- [x] Create enhanced debug modules for options chain and recommendations tab issues
- [x] Implement improved error handling and state preservation for options chain
- [x] Fix non-numeric field ID warnings in streaming manager
- [x] Enhance recommendations tab callback registration and error handling
- [x] Directly integrate enhanced debug modules into main application code
- [x] Update options_chain_utils.py with robust error handling
- [x] Modify dashboard_app.py to use enhanced functions with proper fallback mechanisms
- [x] Fix Dash API deprecation error by updating app.run_server to app.run
- [x] Fix ModuleNotFoundError in dashboard_app_streaming.py
- [x] Create missing options_utils.py module with required functions
- [x] Implement format_options_chain_data function in options_utils.py
- [x] Implement calculate_implied_volatility function in options_utils.py
- [x] Add scipy dependency to requirements.txt for Black-Scholes calculations
- [x] Fix ImportError for StreamingFieldMapper in dashboard_app_streaming.py
- [x] Fix ModuleNotFoundError for recommendation_callbacks in dashboard_app_streaming.py

## Medium Priority
- [x] Update any dependent code to handle multi-timeframe data
- [ ] Create tests for the new functionality
- [x] Update documentation to reflect changes
- [x] Optimize streaming performance and error handling
- [ ] Add visual indicators for fields updated via streaming data
- [ ] Implement caching for normalized contract keys to improve performance
- [ ] Add comprehensive testing for the Recommendations tab functionality
- [ ] Implement additional debugging tools for easier troubleshooting
- [ ] Add more detailed logging for streaming data processing
- [ ] Add unit tests for the newly created options_utils.py functions
- [ ] Ensure all modules have proper docstrings and comments for maintainability
- [ ] Verify all required dependencies are properly documented in requirements.txt
- [ ] Review import statements across the codebase to ensure consistency

## Low Priority
- [ ] Optimize performance for multi-timeframe calculations
- [ ] Consider UI improvements for timeframe selection
- [ ] Add user controls for streaming settings (e.g., update frequency)
- [ ] Create a debug mode toggle for enhanced logging in production

## Dependencies
- Multi-timeframe indicator implementation depends on standardized 60-day data pull
- Dashboard updates depend on multi-timeframe indicator implementation
- Options chain functionality depends on correct Schwab API method usage
- Recommendations tab functionality depends on selected-symbol-store being properly populated
- Real-time options updates depend on StreamingManager integration with dashboard_app.py
- Complete UI updates depend on proper mapping between streaming data fields and DataFrame columns
- Proper matching of streaming data to DataFrame rows depends on consistent contract key normalization
- Stable options chain display depends on proper state preservation between streaming updates
- Options chain data display depends on proper putCall field mapping from contractType
- Recommendations generation depends on button click being properly connected to callback
- Enhanced debug modules depend on core functionality being correctly implemented
- Improved error handling depends on comprehensive understanding of data flow and failure points
- Direct integration of enhanced modules depends on maintaining API compatibility
- dashboard_app_streaming.py depends on options_utils.py module and its functions
- options_utils.py depends on scipy package for Black-Scholes calculations
- dashboard_app_streaming.py depends on StreamingFieldMapper from dashboard_utils.streaming_field_mapper

## Status Legend
- [x] Completed
- [ ] Not Started/In Progress

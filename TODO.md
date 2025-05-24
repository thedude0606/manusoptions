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
- [x] Design enhanced recommendation engine with multi-timeframe analysis
- [x] Implement enhanced recommendation engine with Greeks and IV analysis
- [x] Add profit target and exit price calculation to recommendation engine
- [x] Implement confidence interval calculation for recommendations
- [x] Integrate enhanced recommendation engine with dashboard UI
- [x] Add comprehensive debugging and logging to recommendation engine
- [x] Verify recommendations auto-load without manual button interaction
- [x] Enhance error reporting in the UI with detailed debug information
- [x] Fix options chain tab disappearing after streaming updates
- [x] Fix recommendations not loading issue
- [x] Enhance putCall field handling to ensure proper mapping after streaming updates
- [ ] Monitor logs to verify the putCall field fix resolves both UI issues
- [ ] Add visual indicators for recommendations with high confidence

## Medium Priority

- [ ] Update any dependent code to handle multi-timeframe data
- [ ] Create tests for the new functionality
- [ ] Update documentation to reflect changes
- [ ] Optimize streaming performance and error handling
- [ ] Add visual indicators for fields updated via streaming data
- [ ] Implement caching for normalized contract keys to improve performance

## Low Priority

- [ ] Optimize performance for multi-timeframe calculations
- [ ] Consider UI improvements for timeframe selection
- [ ] Add user controls for streaming settings (e.g., update frequency)
- [ ] Add more sophisticated profit target calculations based on volatility surface

## Dependencies

- [x] Multi-timeframe indicator implementation depends on standardized 60-day data pull
- [x] Dashboard updates depend on multi-timeframe indicator implementation
- [x] Options chain functionality depends on correct Schwab API method usage
- [x] Recommendations tab functionality depends on selected-symbol-store being properly populated
- [x] Real-time options updates depend on StreamingManager integration with dashboard_app.py
- [x] Complete UI updates depend on proper mapping between streaming data fields and DataFrame columns
- [x] Proper matching of streaming data to DataFrame rows depends on consistent contract key normalization
- [x] Enhanced recommendation engine depends on proper integration with dashboard UI
- [x] Diagnosing recommendation loading issues depends on comprehensive logging and debugging
- [x] Options chain tab display depends on proper putCall field maintenance after streaming updates
- [x] Recommendations loading depends on correct putCall values in options data

## Status

- [x] Completed
- [ ] Not Started/In Progress

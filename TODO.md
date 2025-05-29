# TODO List

## Dashboard App
- [x] Fix minute tab data table display
- [x] Fix technical indicators tab data table display
- [x] Add comprehensive debugging for recommendation engine
- [x] Add debug information panel to recommendation tab UI
- [x] Fix recommendation engine to generate actionable recommendations
- [x] Implement improved confidence scoring
- [x] Refine filtering logic to be less aggressive
- [x] Fix profit calculation for realistic outputs
- [x] Implement timeframe bias indicator for trend direction analysis
- [x] Integrate timeframe bias with recommendation engine
- [x] Fix TypeError in recommendation engine when handling numpy arrays
- [x] Fix TypeError when tech_indicators_dict is not a dictionary
- [x] Fix options chain data table not updating with streaming data
- [x] Add enhanced debugging to streaming data updates for contract key matching
- [x] Fix AttributeError in recommendation generation when selected_symbol is a string
- [x] Add comprehensive streaming debug monitor
- [x] Enhance logging for streaming data updates
- [x] Add dedicated streaming debug panel with real-time statistics
- [x] Fix streaming manager to prevent premature stopping
- [x] Implement message queue system for streaming data processing
- [x] Add heartbeat monitoring and automatic reconnection for streaming
- [x] Improve contract key normalization for streaming data
- [x] Fix application loading error in shutdown_streaming function
- [x] Fix method name mismatch in streaming functionality (start_streaming → start_stream)
- [ ] Fix recommendation engine symbol-specific data handling
- [ ] Add symbol validation throughout data pipeline
- [ ] Enhance error handling for missing symbol-specific data
- [ ] Add data quality metrics for recommendation reliability
- [ ] Test enhanced streaming manager with real-world data
- [ ] Validate automatic reconnection logic across different conditions
- [ ] Test timeframe bias indicator across different market conditions
- [ ] Add UI components to display timeframe bias information
- [ ] Fix Safari export button compatibility issue
- [ ] Add additional error handling for data fetching
- [ ] Improve UI responsiveness on mobile devices
- [ ] Enhance streaming data integration with recommendation engine
- [ ] Add automated testing for streaming data updates

## Documentation
- [x] Update PROGRESS.md with current status
- [x] Update TODO.md with prioritized tasks
- [x] Update DECISIONS.md with technical rationale
- [x] Document streaming manager improvements and rationale
- [x] Document recommendation engine issues and fixes
- [ ] Create user guide for recommendation engine features
- [ ] Document timeframe bias indicator usage and interpretation
- [ ] Document streaming debug monitor usage and interpretation
- [ ] Create troubleshooting guide for streaming data issues

## Dependencies
- UI improvements depend on core functionality fixes
- Additional features depend on validation of current enhancements
- Timeframe bias UI display depends on validation of indicator accuracy
- Recommendation updates depend on reliable streaming data flow
- Automated testing depends on stable streaming implementation
- Symbol-specific recommendations depend on fixing data flow issues

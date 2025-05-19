# TODO List

## Sorting and Filtering Implementation

### High Priority
- [x] Analyze current data flow and codebase
- [x] Design incremental update strategy
- [x] Implement global data cache structure
- [x] Modify `get_minute_data` function to better utilize `since_timestamp`
- [x] Implement data merging logic for incremental updates
- [x] Add periodic update mechanism (30-second interval)
- [x] Implement selective technical indicator recalculation
- [x] Add loading indicators for initial data fetch
- [x] Implement error handling for failed updates

### New Features - Sorting and Filtering
- [x] Clarify sorting and filtering requirements with user
- [x] Analyze current table implementations
- [x] Design sorting and filtering strategy for all tables
- [x] Implement sorting and filtering on minute data table
- [x] Implement sorting and filtering on technical indicators table
- [x] Implement sorting and filtering on options chain tables
- [x] Validate sorting and filtering functionality
- [x] Update documentation with new features

### Medium Priority
- [ ] Optimize cache memory usage
- [ ] Add cache invalidation logic (24-hour max age)
- [ ] Implement manual refresh functionality
- [ ] Add visual feedback for data updates

### Low Priority
- [ ] Evaluate WebSocket streaming for future enhancement
- [ ] Add configuration options for update frequency
- [ ] Implement analytics to track API call reduction

### Dependencies
- Global cache structure must be implemented before incremental updates
- Periodic update mechanism depends on cache and merging logic
- Selective recalculation depends on data merging implementation

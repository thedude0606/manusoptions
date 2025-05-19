# TODO List

## Incremental Update Strategy Implementation

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

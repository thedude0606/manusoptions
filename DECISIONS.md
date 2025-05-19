# DECISIONS.md

## Technical Architecture Decisions

### Options Chain Streaming Field Configuration

- **Decision**: Update options chain streaming to include Last, Bid, and Ask price fields.
- **Rationale**: These fields are essential for options trading decisions but were missing from the original streaming configuration, causing blank values in the UI.
- **Alternatives Considered**:
  - Keeping the limited field set to reduce data volume
  - Using periodic polling instead of streaming for these fields
  - Fetching these values on-demand when users interact with specific options
- **Trade-offs**:
  - Including more fields increases data volume but provides critical price information
  - Streaming approach ensures real-time updates for time-sensitive trading decisions
  - Consistent field mapping between fetch_options_chain.py and StreamingManager improves maintainability
- **Implementation**:
  - Added field codes 2 (Bid), 3 (Ask), and 4 (Last) to STREAMING_OPTION_FIELDS_REQUEST
  - Updated STREAMING_FIELD_MAPPING to include these fields with appropriate names
  - Ensured naming consistency with StreamingManager's field mapping

### Technical Indicators Implementation

- **Decision**: Implement technical indicators using pandas DataFrame operations.
- **Rationale**: Pandas provides efficient vectorized operations for time series data, which is ideal for technical analysis calculations.
- **Alternatives Considered**: 
  - Using a third-party library like TA-Lib
  - Implementing indicators with pure Python loops
- **Trade-offs**: 
  - Pandas approach is more maintainable and readable than pure Python loops
  - Custom implementation gives more control than third-party libraries
  - Performance may be slightly lower than optimized C/C++ libraries like TA-Lib

### Data Ordering for Technical Indicators

- **Decision**: Modify technical indicator calculation to sort data in ascending chronological order before processing.
- **Rationale**: The current implementation incorrectly assumes data is already in ascending order, causing issues with MACD and potentially other indicators when data is in reverse order.
- **Alternatives Considered**:
  - Modifying each indicator function to handle both ascending and descending orders
  - Keeping the current implementation and documenting the requirement for ascending order
  - Adding a configuration parameter to specify the expected data order
- **Trade-offs**:
  - Sorting before calculation ensures consistent behavior regardless of input order
  - Slight performance impact from sorting operation is outweighed by correctness benefits
  - Centralizing the sorting logic improves maintainability compared to handling in each indicator
- **Implementation**:
  - Add sorting by timestamp in ascending order in the `calculate_all_technical_indicators()` function
  - Add clear documentation about the importance of data ordering for time-dependent calculations
  - Consider adding warning logs when data is detected to be in reverse order

### MFI Calculation Standardization

- **Decision**: Update the Money Flow Index (MFI) calculation to use the standard textbook approach.
- **Rationale**: The previous implementation used a non-standard approach with shifted price direction, which produced values inconsistent with established financial literature.
- **Alternatives Considered**:
  - Keeping the non-standard implementation with added documentation
  - Providing both implementations with an option to choose
  - Maintaining backward compatibility with a flag
- **Trade-offs**:
  - Standard implementation ensures consistency with other financial tools and platforms
  - Improves reliability for trading decisions based on MFI
  - Changes existing indicator values, which may affect historical analysis
  - More intuitive implementation that doesn't rely on future price information
- **Implementation**:
  - Replace the shifted money flow direction logic with standard current-period price change
  - Add comprehensive documentation explaining the MFI calculation formula
  - Validate against standard implementations to ensure accuracy

### Technical Indicator Validation

- **Decision**: Implement comprehensive validation of technical indicators across all timeframes.
- **Rationale**: Ensuring accurate calculation of indicators is critical for trading decisions and strategy development.
- **Alternatives Considered**:
  - Relying on visual inspection alone
  - Using third-party validation tools
  - Implementing automated testing without manual verification
- **Trade-offs**:
  - Manual cross-verification provides highest confidence but requires more effort
  - Detailed code analysis helps understand edge cases and expected behavior
  - Documentation of findings provides reference for future development
- **Implementation**:
  - Analyzed CSV exports across different timeframes (1-minute, 15-minute, Hourly, Daily)
  - Reviewed implementation code to understand calculation logic and requirements
  - Cross-referenced code with observed data patterns to validate calculations
  - Identified critical issue with MACD calculation when data is in reverse chronological order
  - Created detailed documentation of findings and recommended solutions

### Candlestick Pattern Detection Implementation

- **Decision**: Create a dedicated module for candlestick pattern detection with comprehensive coverage of both traditional and advanced patterns.
- **Rationale**: Separating candlestick pattern logic into its own module provides better organization, maintainability, and allows for focused development of this complex feature.
- **Alternatives Considered**:
  - Integrating pattern detection directly into technical_analysis.py
  - Using a third-party library for pattern detection
  - Implementing only basic patterns instead of comprehensive coverage
- **Trade-offs**:
  - Dedicated module increases code organization but adds another file to maintain
  - Custom implementation provides full control over pattern definitions and thresholds
  - Comprehensive coverage increases utility but also complexity
  - Vectorized implementation balances performance with readability
- **Implementation**:
  - Created candlestick_patterns.py with modular functions for each pattern type
  - Implemented traditional single-candle patterns (Doji, Hammer/Hanging Man, etc.)
  - Implemented traditional multi-candle patterns (Engulfing, Morning/Evening Star, etc.)
  - Implemented advanced price action concepts (Order Blocks, Liquidity Grabs, etc.)
  - Used consistent error handling and logging approach matching technical_analysis.py
  - Designed for integration with existing technical indicator workflows

### Data Fetching and Processing

- **Decision**: Standardize column names in lowercase format for technical analysis.
- **Rationale**: Consistent column naming convention simplifies code and reduces errors.
- **Alternatives Considered**:
  - Using uppercase column names throughout
  - Case-insensitive column access
- **Trade-offs**:
  - Lowercase is Python convention for variable names
  - Requires explicit conversion when interfacing with APIs that use different conventions

### Dashboard Implementation

- **Decision**: Use Dash for interactive dashboard.
- **Rationale**: Dash provides a Python-based framework for building interactive web applications without requiring JavaScript expertise.
- **Alternatives Considered**:
  - Flask with JavaScript frontend
  - Streamlit
- **Trade-offs**:
  - Dash has a steeper learning curve than Streamlit
  - More flexible and powerful than Streamlit for complex applications
  - More integrated Python workflow than Flask+JavaScript

### CSV Export Functionality for Minute Data

- **Decision**: Implement CSV export for minute data tab.
- **Rationale**: Allows users to verify data accuracy and perform external analysis of the raw data.
- **Alternatives Considered**:
  - JSON export format
  - Excel export format
  - Direct database connection
- **Trade-offs**:
  - CSV is universally compatible with analysis tools
  - Simple implementation with built-in pandas functionality
  - Lightweight compared to Excel export
  - Less structured than JSON for complex nested data
- **Implementation**:
  - Added "Export to CSV" button to minute data tab UI
  - Created callback to generate and serve CSV files using Dash's dcc.Download component
  - Added data storage mechanism to ensure all minute data is available for export
  - Included symbol name and timestamp in filename for easy identification

### CSV Export Functionality for Technical Indicators

- **Decision**: Implement CSV export for technical indicators tab.
- **Rationale**: Provides consistency with minute data tab and allows users to export technical analysis results for further analysis or record-keeping.
- **Alternatives Considered**:
  - Using a different export format than CSV
  - Exporting only specific indicators rather than all indicators
  - Combining minute data and technical indicators in a single export
- **Trade-offs**:
  - Consistent user experience across tabs with similar export functionality
  - CSV format maintains the tabular structure of technical indicators data
  - Separate exports for minute data and technical indicators keeps files focused and manageable
  - Simpler implementation by reusing existing export pattern
- **Implementation**:
  - Added "Export to CSV" button to technical indicators tab UI with same styling as minute data tab
  - Created dedicated data store (tech-indicators-store) for technical indicators export data
  - Implemented callback to generate and serve CSV files using the same pattern as minute data export
  - Ensured exported CSV files include symbol name and timestamp in filename for easy identification
  - Modified update_data_for_active_tab callback to populate the tech-indicators-store

### Full Historical Technical Indicators Display and Export

- **Decision**: Modify technical indicators tab to display and export full historical series instead of just the most recent value.
- **Rationale**: Provides users with complete historical data for each indicator, enabling more comprehensive analysis and visualization.
- **Alternatives Considered**:
  - Keeping the current approach of showing only the most recent value
  - Creating a separate tab for historical indicator data
  - Implementing a hybrid approach with summary view and detailed view options
- **Trade-offs**:
  - Full historical data provides more analytical value but requires more complex UI
  - Timeframe selector helps manage the potentially large amount of data
  - Increased memory usage on client side when handling large datasets
  - More complex data structure in the store component
- **Implementation**:
  - Added a timeframe dropdown selector to allow viewing different timeframes (1min, 15min, Hourly, Daily)
  - Modified the data storage mechanism to store complete historical data for all timeframes
  - Created a new callback to update the table based on selected timeframe
  - Enhanced the CSV export functionality to export the full historical series for the selected timeframe
  - Included timeframe information in exported CSV filenames

## Bug Fix Decisions

### MACD Calculation with Reverse Chronological Data

- **Decision**: Sort DataFrame by timestamp in ascending order before calculating technical indicators.
- **Rationale**: The current implementation incorrectly marks recent values as NaN when data is in reverse chronological order, causing MACD and potentially other indicators to show blank values for recent timestamps.
- **Alternatives Considered**:
  - Modifying each indicator function to detect and handle data ordering
  - Adding a parameter to specify expected data order
  - Documenting the requirement for ascending order without changing code
- **Trade-offs**:
  - Centralizing sorting logic in one place improves maintainability
  - Slight performance impact from sorting is justified by correctness benefits
  - Ensures consistent behavior regardless of input data ordering
- **Implementation**:
  - Add sorting by timestamp in the `calculate_all_technical_indicators()` function
  - Add clear documentation about the importance of data ordering
  - Consider adding warning logs when reverse order is detected

### MFI Calculation Standardization

- **Decision**: Replace non-standard MFI implementation with standard textbook approach.
- **Rationale**: The previous implementation used a shifted money flow direction approach that was inconsistent with established financial literature and standard practice.
- **Alternatives Considered**:
  - Keeping the non-standard implementation with added documentation
  - Supporting both implementations with a configuration option
  - Maintaining backward compatibility
- **Trade-offs**:
  - Standard implementation ensures consistency with other financial tools
  - Improves reliability for trading decisions
  - Changes existing indicator values, which may affect historical analysis
  - More intuitive implementation that doesn't rely on future price information
- **Implementation**:
  - Updated the MFI calculation to use current period price changes for determining money flow direction
  - Added comprehensive documentation explaining the formula and approach
  - Validated against standard implementations to ensure accuracy

### `period_name` Argument Error

- **Decision**: Remove `period_name` parameter from `calculate_all_technical_indicators()` calls.
- **Rationale**: The function definition does not include this parameter, causing runtime errors.
- **Implementation**: Updated all call sites to use the correct parameter signature.

### DatetimeIndex Error

- **Decision**: Ensure 'timestamp' column remains a datetime object and is named consistently.
- **Rationale**: Technical analysis functions expect a DatetimeIndex for proper time-based operations.
- **Implementation**: Modified data fetchers to maintain datetime objects and consistent column naming.

### Series Truth Value Error

- **Decision**: Use `np.where()` for conditional operations on pandas Series objects.
- **Rationale**: Direct boolean operations on Series objects can lead to ambiguous truth value errors.
- **Implementation**: Refactored conditional logic in technical indicator calculations to use `np.where()`.

### Schwab Client Tuple Handling

- **Decision**: Store only the client instance, not the tuple returned by `get_schwab_client()`.
- **Rationale**: Functions expect the client object directly, not a tuple containing the client and error message.
- **Implementation**: Modified client initialization to extract only the client instance from the returned tuple.

### Dict vs DataFrame Error

- **Decision**: Ensure consistent use of DataFrames for technical indicator results.
- **Rationale**: Some functions expected DataFrame objects but received dictionaries, causing attribute errors.
- **Implementation**: Standardized all technical indicator processing to use DataFrames consistently.

## Column Name Standardization Decisions

### Column Name Mismatch Issue

- **Decision**: Standardize on lowercase column names throughout the codebase.
- **Rationale**: The mismatch between uppercase column names in data fetchers and lowercase names expected by technical analysis functions was causing aggregation failures.
- **Alternatives Considered**:
  - Modifying technical analysis functions to accept uppercase column names
  - Adding case-insensitive column access throughout the codebase
- **Trade-offs**:
  - Lowercase naming follows Python conventions
  - Consistent naming reduces errors and simplifies code
  - Required changes in multiple files but provides a more robust solution
- **Implementation**: 
  - Modified data_fetchers.py to return lowercase column names
  - Added column normalization in dashboard_app.py as a fallback mechanism
  - Comprehensive testing confirmed the fix resolves aggregation errors

### Validation Framework

- **Decision**: Create a validation framework to detect and fix column name mismatches.
- **Rationale**: Provides a way to verify that terminal output matches technical indicators tab and helps identify similar issues in the future.
- **Alternatives Considered**:
  - Direct code fixes without validation
  - Manual testing only
- **Trade-offs**:
  - Validation approach allows detection and correction with automated testing
  - More complex than direct fixes but provides better long-term maintainability
  - Helps prevent regression of similar issues
- **Implementation**: 
  - Created validation scripts to parse terminal logs and compare with technical analysis results
  - Added column name normalization function to fix mismatches
  - Generated sample data for testing the validation process

## Future Enhancement Decisions

### Technical Indicator Enhancements

- **Decision**: Consider implementing recommended enhancements for technical indicators.
- **Rationale**: While current implementation is functioning correctly, several improvements could enhance usability and maintainability.
- **Alternatives Considered**:
  - Maintaining current implementation without changes
  - Complete rewrite using third-party libraries
- **Trade-offs**:
  - Incremental improvements maintain compatibility while enhancing functionality
  - Enhanced logging improves transparency without significant performance impact
  - Standardizing early value handling improves code consistency and maintainability
- **Potential Implementations**:
  - Add more detailed logging for FVG detection
  - Standardize approaches for handling early values across all indicators
  - Add visualization aids for insufficient data vs. absent patterns
  - Develop specific unit tests for edge cases

### Performance Optimization

- **Decision**: Consider vectorized operations for performance-critical calculations.
- **Rationale**: Some technical indicators may become performance bottlenecks with large datasets.
- **Alternatives Considered**:
  - Using multiprocessing for parallel calculations
  - Implementing critical sections in Cython or Numba
- **Trade-offs**:
  - Vectorized operations maintain code readability while improving performance
  - More complex optimizations may reduce maintainability

### Additional Technical Indicators

- **Decision**: Design modular framework for adding new indicators.
- **Rationale**: Trading strategies often require specialized indicators beyond the basic set.
- **Implementation**: Each indicator is implemented as a separate function that accepts and returns a DataFrame.

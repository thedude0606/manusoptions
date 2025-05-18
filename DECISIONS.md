# DECISIONS.md

## Technical Architecture Decisions

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

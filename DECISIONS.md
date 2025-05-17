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

## Validation Framework Decisions

### Column Name Mismatch Issue

- **Decision**: Create a validation framework to detect and fix column name mismatches.
- **Rationale**: The mismatch between uppercase column names in data fetchers and lowercase names expected by technical analysis functions causes aggregation failures.
- **Alternatives Considered**:
  - Modifying data fetchers to return lowercase column names
  - Modifying technical analysis functions to accept uppercase column names
  - Adding a normalization step in the dashboard application
- **Trade-offs**:
  - Validation approach allows detection and correction without changing existing code
  - Provides a way to verify that terminal output matches technical indicators tab
  - More complex than directly fixing the column names in one place
- **Implementation**: 
  - Created validation scripts to parse terminal logs and compare with technical analysis results
  - Added column name normalization function to fix mismatches
  - Generated sample data for testing the validation process

### Sample Data Generation

- **Decision**: Create a sample data generator for testing.
- **Rationale**: Testing with consistent, reproducible data allows for more reliable validation.
- **Alternatives Considered**:
  - Using real market data for testing
  - Using static test data files
- **Trade-offs**:
  - Generated data can be customized for specific test scenarios
  - May not capture all edge cases present in real market data
  - More flexible than static test files
- **Implementation**: Created a script to generate realistic OHLCV data with configurable parameters.

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

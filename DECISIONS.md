# Design Decisions

## Architecture
- Using Dash for interactive web application framework
- Modular design with separate modules for data fetching, analysis, and UI components
- Asynchronous data loading to improve user experience
- Centralized contract key normalization for consistent data matching

## Technology Selections
- Python for backend processing and data analysis
- Pandas for data manipulation and analysis
- Dash and Plotly for interactive visualizations
- Schwab API for real-time and historical market data
- Regular expressions for robust contract key parsing and formatting

## Design Patterns
- Observer pattern for real-time data updates
- Factory pattern for creating different types of technical indicators
- Strategy pattern for implementing different trading strategies
- Utility pattern for shared functionality like contract key normalization

## Key Decisions

### May 20, 2025
- **Centralized Contract Key Normalization**: Created a dedicated utility module (`contract_utils.py`) to handle contract key normalization and formatting. This ensures consistent contract key formats between REST API data and streaming data, fixing the issue with blank price fields in the options chain dashboard.

- **Enhanced Field Mapping**: Updated the field mapping logic to handle both string and numeric field IDs from the stream. This makes the application more robust against variations in the Schwab API response format and ensures all price data is properly captured and displayed.

- **Robust Type Conversion**: Implemented more robust type conversion for field values, ensuring that numeric values are properly parsed regardless of whether they're received as strings or native numeric types.

- **Consistent Normalization Strategy**: Adopted a consistent normalization strategy across all modules that handle contract keys, ensuring that keys are always normalized before comparison or storage. This prevents mismatches between different data sources and improves data integrity.

### Previous Decisions
- **Options Chain Data Handling**: Modified the options chain data fetching logic to preserve actual API values for lastPrice, bidPrice, and askPrice fields. Only add default values (None) when fields are completely missing from the API response. This ensures the UI displays real market data rather than placeholder zeros.

- **Data Validation**: Added validation at both the contract level and DataFrame level to ensure required fields are always present, improving application robustness.

- **Error Logging**: Enhanced logging to track when fields are missing or added, facilitating future debugging.

- Implemented streaming data architecture for real-time updates
- Chose to separate data fetching from UI rendering for better maintainability
- Decided to use Dash callbacks for reactive UI updates

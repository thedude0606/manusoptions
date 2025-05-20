# Design Decisions

## Architecture
- Using Dash for interactive web application framework
- Modular design with separate modules for data fetching, analysis, and UI components
- Asynchronous data loading to improve user experience

## Technology Selections
- Python for backend processing and data analysis
- Pandas for data manipulation and analysis
- Dash and Plotly for interactive visualizations
- Schwab API for real-time and historical market data

## Design Patterns
- Observer pattern for real-time data updates
- Factory pattern for creating different types of technical indicators
- Strategy pattern for implementing different trading strategies

## Key Decisions

### May 20, 2025
- **Options Chain Data Handling (Updated)**: Modified the options chain data fetching logic to preserve actual API values for lastPrice, bidPrice, and askPrice fields. Only add default values (None) when fields are completely missing from the API response. This ensures the UI displays real market data rather than placeholder zeros.
- **Data Validation**: Added validation at both the contract level and DataFrame level to ensure required fields are always present, improving application robustness.
- **Error Logging**: Enhanced logging to track when fields are missing or added, facilitating future debugging.

### Previous Decisions
- Implemented streaming data architecture for real-time updates
- Chose to separate data fetching from UI rendering for better maintainability
- Decided to use Dash callbacks for reactive UI updates

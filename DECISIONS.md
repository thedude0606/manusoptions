# Design Decisions

## Architecture

### Dashboard Structure
- **Modular Design**: Separated dashboard components into distinct modules for better maintainability
- **Callback Pattern**: Used Dash callback pattern for reactive updates
- **Data Flow**: Implemented unidirectional data flow from API to UI components

### Data Processing
- **Batched Data Retrieval**: Implemented day-by-day batched retrieval for minute data to handle API limitations
- **Data Transformation**: Standardized data formats between API responses and UI components
- **Caching Strategy**: Used client-side stores for temporary data caching

## Technology Selections

### Frontend
- **Dash**: Selected for its ability to create interactive data visualization applications with Python
- **Plotly**: Used for interactive charts and visualizations
- **Bootstrap Components**: Incorporated for responsive UI elements

### Backend
- **Python**: Primary language for all backend processing
- **Schwab API**: Used for financial data retrieval
- **Pandas**: Selected for data manipulation and analysis

## Design Patterns

### Data Processing Patterns
- **Factory Pattern**: Used for creating different types of data processors
- **Strategy Pattern**: Implemented for different technical analysis strategies
- **Observer Pattern**: Used in the dashboard for reactive updates

### Error Handling
- **Centralized Error Management**: Implemented a central error store for consistent error handling
- **Graceful Degradation**: Designed components to function with partial data when errors occur
- **Error Trigger Pattern**: Used hidden stores as error triggers to avoid duplicate callback outputs

## Key Decisions and Rationale

### Centralized Configuration Approach
- **Issue**: Inconsistent token file paths across different modules causing authentication issues
- **Solution**: Created a centralized config.py module with standardized TOKEN_FILE_PATH
- **Rationale**: Ensures consistent token file handling across all components, preventing authentication failures
- **Implementation**: Updated all modules to import and use the centralized token file path

### Centralized Error Handling Fix
- **Issue**: Duplicate callback outputs error when multiple callbacks tried to update error-store.data
- **Solution**: Implemented a centralized error handling pattern with hidden trigger stores
- **Rationale**: Prevents multiple callbacks from directly updating the same output, resolving Dash's duplicate output constraint
- **Implementation**: Created separate error trigger stores for each data source and a single callback to update the main error store

### Options Chain Display Fix
- **Issue**: Options chain table was not displaying due to inconsistent data processing
- **Solution**: Created a dedicated options_chain_utils.py module to standardize options data processing
- **Rationale**: Modularizing the options chain logic improves maintainability and isolates the data processing from the UI components
- **Implementation**: Added robust data validation and normalization to handle inconsistent API responses

### Minute Data Error Fix
- **Issue**: Minute data errors occurred due to improper error handling
- **Solution**: Enhanced error handling in minute data processing and display
- **Rationale**: Proper error handling ensures the application remains functional even when API responses are incomplete or malformed
- **Implementation**: Added validation checks and fallback mechanisms for minute data processing

### Authentication Approach
- **Decision**: Used token-based authentication with refresh capability
- **Rationale**: Provides secure access to the API while minimizing the need for user interaction
- **Implementation**: Implemented token refresh logic to maintain session validity

### Data Fetching Strategy
- **Decision**: Implemented batched data retrieval for historical data
- **Rationale**: Overcomes API limitations for large data requests and improves reliability
- **Implementation**: Created day-by-day fetching with aggregation for minute data

### UI/UX Decisions
- **Decision**: Used tabbed interface for different data views
- **Rationale**: Provides clear separation of concerns and improves user navigation
- **Implementation**: Created separate tabs for minute data, technical indicators, options chain, and recommendations

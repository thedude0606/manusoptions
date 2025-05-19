# Design Decisions

## Architecture

### Dashboard Structure
- **Decision**: Use a tab-based layout for the dashboard
- **Rationale**: Tabs provide a clean way to separate different types of data and functionality while maintaining a cohesive user experience
- **Alternatives Considered**: Multi-page application, single scrolling dashboard
- **Trade-offs**: Tabs limit the amount of information visible at once but provide better organization and focus

### Data Fetching
- **Decision**: Implement separate data fetchers for different data types (minute data, options chain)
- **Rationale**: Separation of concerns makes the code more maintainable and allows for independent optimization of each data fetcher
- **Alternatives Considered**: Single unified data fetcher
- **Trade-offs**: More code to maintain but better organization and flexibility

### Streaming Implementation
- **Decision**: Use a dedicated StreamingManager class with its own thread
- **Rationale**: Streaming requires continuous connection and processing that should not block the main application thread
- **Alternatives Considered**: Using callbacks or polling
- **Trade-offs**: More complex implementation but better performance and user experience

### Fix for Last, Bid, Ask Values Not Showing in Options Streaming Tab
- **Decision**: Enhance the options chain callback to explicitly update with streaming data
- **Rationale**: The original implementation was not properly integrating streaming data with the displayed options chain
- **Implementation Details**:
  1. Added code to update calls and puts DataFrames with streaming data before display
  2. Enhanced logging to better track streaming data flow
  3. Improved error handling for streaming data updates
- **Alternatives Considered**: Creating a separate streaming-only display or using polling instead of streaming
- **Trade-offs**: More complex code but provides real-time updates without requiring full data refresh

## Technology Choices

### Dash Framework
- **Decision**: Use Dash for the web application framework
- **Rationale**: Dash provides interactive visualization capabilities with Python backend, ideal for financial data
- **Alternatives Considered**: Flask with JavaScript frontend, Django
- **Trade-offs**: Less flexibility than a custom JavaScript frontend but faster development and easier integration with Python data processing

### Pandas for Data Processing
- **Decision**: Use Pandas for data manipulation and analysis
- **Rationale**: Pandas provides powerful tools for time series data and financial calculations
- **Alternatives Considered**: NumPy arrays, custom data structures
- **Trade-offs**: Memory overhead but significant productivity gains and built-in functionality

### Logging System
- **Decision**: Implement comprehensive logging with both console and file outputs
- **Rationale**: Detailed logging is essential for debugging streaming and API issues
- **Implementation**: Module-specific loggers with consistent formatting
- **Trade-offs**: Performance impact but crucial for troubleshooting complex issues

## Design Patterns

### Observer Pattern
- **Decision**: Use observer pattern for streaming data updates
- **Rationale**: Allows components to subscribe to data changes without tight coupling
- **Implementation**: StreamingManager notifies subscribers of data updates
- **Trade-offs**: More complex than direct updates but more flexible and maintainable

### Factory Pattern
- **Decision**: Use factory functions for client creation and data fetching
- **Rationale**: Encapsulates creation logic and provides consistent error handling
- **Implementation**: Functions like get_schwab_client() that handle initialization and error states
- **Trade-offs**: Additional layer of abstraction but better error handling and consistency

### Repository Pattern
- **Decision**: Use repository pattern for data access
- **Rationale**: Abstracts data sources and provides consistent interface
- **Implementation**: Data fetcher modules that handle API interactions
- **Trade-offs**: More code but better separation of concerns and testability

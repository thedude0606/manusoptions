# Key Architectural Decisions

## Dashboard Framework Updates

- **Decision**: Update from app.run_server to app.run in Dash application
- **Rationale**: The app.run_server method has been deprecated in newer versions of Dash in favor of app.run
- **Alternatives Considered**: Downgrading Dash version (not viable for long-term maintenance)
- **Consequences**: 
  - Ensures compatibility with current and future Dash versions
  - Eliminates obsolete attribute exceptions
  - Maintains consistent API usage with Dash best practices

## Authentication

- **Decision**: Use Schwabdev library for authentication
- **Rationale**: Provides a robust and well-tested implementation for Schwab API authentication
- **Alternatives Considered**: Custom OAuth implementation
- **Consequences**: Dependency on third-party library, but significantly reduces development time and potential security issues

## Data Retrieval

- **Decision**: Implement batched retrieval for minute data
- **Rationale**: Schwab API has a limitation where it only returns 1 day of minute data per request regardless of the date range specified
- **Alternatives Considered**: 
  - Single request with extended date range (not viable due to API limitation)
  - Streaming data (more complex, requires continuous connection)
- **Consequences**: 
  - Increased number of API calls
  - Potential rate limiting concerns
  - More complex error handling required
  - Better resilience through smaller, atomic requests

## Dashboard Integration

- **Decision**: Configure dashboard to request 60 days of minute data by default
- **Rationale**: Provides users with a comprehensive view of historical data while handling API limitations transparently
- **Alternatives Considered**:
  - User-configurable time range (adds complexity)
  - Separate batch processing outside the dashboard (less integrated experience)
- **Consequences**:
  - Increased initial load time
  - Larger memory footprint
  - More comprehensive data for analysis
  - Better user experience with complete dataset available immediately

## Data Storage

- **Decision**: Store aggregated data in JSON format
- **Rationale**: Simple, human-readable format that can be easily loaded into various analysis tools
- **Alternatives Considered**: SQL database, CSV files
- **Consequences**: May have performance implications for very large datasets, but provides flexibility and ease of use

## Technical Analysis

- **Decision**: Implement technical analysis using custom algorithms
- **Rationale**: Provides full control over indicators and calculations
- **Alternatives Considered**: Third-party libraries like TA-Lib
- **Consequences**: More development effort but better customization options

## Dashboard Application

- **Decision**: Use Dash for interactive visualization
- **Rationale**: Python-based, easy integration with data processing pipeline
- **Alternatives Considered**: Streamlit, custom web application
- **Consequences**: Some limitations in customization but rapid development

## Minute Data Batching Implementation

- **Decision**: Sequential day-by-day requests with aggregation
- **Rationale**: Simplifies error handling and provides clear progress tracking
- **Alternatives Considered**: 
  - Parallel requests (could trigger rate limiting)
  - Asynchronous requests (more complex error handling)
- **Consequences**: 
  - Slower overall retrieval but more reliable
  - Easier to implement retry logic for specific days
  - Better visibility into progress

# Key Architectural Decisions

## Technology Stack
- **Python**: Primary programming language for backend and data processing
- **Dash**: Web application framework for building interactive dashboards
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computing
- **SchwabDev**: API client for accessing Schwab trading data
- **Technical Analysis Libraries**: For market indicators and signals

## Design Patterns
- **MVC Pattern**: Separation of data (models), user interface (views), and business logic (controllers)
- **Observer Pattern**: Used in dashboard callbacks to respond to data changes
- **Factory Pattern**: For creating different types of technical indicators
- **Strategy Pattern**: For implementing different recommendation strategies

## Key Decisions

### Data Retrieval
- **Batched Data Retrieval**: Implemented batched retrieval of minute data for 60 days to support extended analysis periods
- **Incremental Updates**: Added support for incremental data updates to reduce API calls and improve performance
- **Data Caching**: Implemented caching mechanism to store and reuse data between sessions

### Technical Analysis
- **Modular Indicator System**: Created a modular system for technical indicators that can be easily extended
- **Timeframe Aggregation**: Implemented candle aggregation to support multiple timeframes (1min to 1day)
- **Combined Signal Approach**: Used a combination of technical indicators for market direction analysis

### Recommendation Engine
- **Confidence Threshold**: Lowered confidence threshold from 60 to 40 to ensure recommendations are generated while maintaining quality
- **Underlying Price Extraction**: Modified options chain data retrieval to properly extract and pass the underlying price to the recommendation engine
- **Multi-factor Scoring**: Implemented a scoring system that considers multiple factors for generating recommendations

### Dashboard Interface
- **Tab-based Layout**: Organized dashboard into tabs for different types of data and analysis
- **Real-time Updates**: Implemented periodic updates to keep data current
- **Responsive Design**: Ensured dashboard works well on different screen sizes

### Error Handling
- **Centralized Error Store**: Implemented a central error store to capture and display errors
- **Graceful Degradation**: Designed system to continue functioning with partial data when errors occur

### Dependency Management
- **Version Pinning**: Specified exact versions for numpy (1.24.4) and pandas (2.0.3) to ensure binary compatibility
- **Compatibility Testing**: Verified compatibility between critical numerical libraries to prevent binary interface mismatches
- **Platform-Specific Installation**: Added special installation instructions for Python 3.12 on Apple Silicon (ARM) to address build issues with numpy and pandas

## Rationale for Critical Fixes

### Underlying Price Extraction Fix
- **Problem**: The underlying price was not being extracted from the options chain API response and passed to the recommendation engine, causing recommendations to fail
- **Solution**: Modified the `get_options_chain_data` function to extract the underlying price and return it as part of the function result, then updated the dashboard app to include this price in the options chain store data
- **Rationale**: The recommendation engine requires the underlying price to calculate appropriate option recommendations. Without this value, it cannot determine which options are in/out of the money or calculate potential profit percentages

### Confidence Threshold Adjustment
- **Problem**: The confidence threshold was set too high (60), causing all potential recommendations to be filtered out
- **Solution**: Lowered the confidence threshold to 40 to allow more recommendations to pass through while still maintaining quality standards
- **Rationale**: The original threshold was too restrictive for the current market conditions and signal strength. The adjusted value provides a better balance between recommendation quality and quantity

### Numpy/Pandas Binary Incompatibility Fix
- **Problem**: Binary incompatibility between numpy and pandas versions causing application startup failure with error "numpy.dtype size changed, may indicate binary incompatibility"
- **Solution**: Specified compatible versions in requirements.txt (numpy==1.24.4 and pandas==2.0.3) to ensure binary compatibility
- **Rationale**: The error occurs when the installed numpy version has a different binary interface than what pandas was compiled against. By pinning specific compatible versions, we ensure consistent binary interfaces between the libraries, preventing the incompatibility error during import.

### Python 3.12 on Apple Silicon (ARM) Compatibility
- **Problem**: Build failures when installing numpy and pandas from source on Python 3.12 with Apple Silicon (ARM) architecture
- **Solution**: Added platform-specific installation instructions in requirements.txt to use conda or pre-built wheels instead of building from source
- **Rationale**: Python 3.12 is relatively new and some packages like numpy and pandas may have compatibility issues when building from source on ARM architecture. Using pre-built binaries via conda or pip with the --only-binary flag avoids compilation issues while maintaining version compatibility.

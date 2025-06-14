# Design Decisions

## Dashboard Architecture
- Used Dash for interactive web components and real-time data visualization
- Implemented modular design with separate modules for data fetching, UI components, and business logic
- Created streaming data architecture to handle real-time updates efficiently

## Recommendation Engine
- Added comprehensive debugging panel to diagnose recommendation generation issues
- Implemented detailed logging throughout the recommendation generation process
- Added fallback mechanisms for missing data fields to improve robustness
- Designed UI to clearly display market direction analysis and recommendation confidence

## Recommendation Engine Enhancements
- Improved confidence scoring algorithm with higher base scores (60 instead of 50)
- Increased market direction impact on confidence scores (25 point boost instead of 20)
- Added liquidity preference based on open interest to favor more liquid options
- Implemented preference for options with 5-14 days to expiration for swing trading
- Reduced penalties for IV, spread percentage, and strike distance to generate more recommendations
- Added cap on expected profit (50% maximum) to ensure realistic projections
- Improved projected move calculation based on days to expiration and volatility
- Enhanced target timeframe calculation with more realistic bounds (4-72 hours)
- Fixed type handling in recommendation engine to properly handle both pandas DataFrames and numpy arrays in technical indicators dictionary
- Added robust type checking for tech_indicators_dict to ensure proper handling of non-dictionary inputs
- Implemented type checking for selected_symbol to handle both dictionary and string formats, preventing AttributeError

## Streaming Data Architecture
- Implemented robust contract key normalization to handle different formats between REST API and streaming data
- Added fallback matching logic to ensure streaming updates are correctly applied to options data tables
- Enhanced logging for streaming data updates to improve debugging and troubleshooting
- Implemented multiple key format attempts to maximize successful matches between streaming data and DataFrame rows
- Used a layered approach to contract key matching: normalized format, alternative format without underscore, and direct matching
- Added detailed debugging to track contract key formats and matching success rates
- Created dedicated StreamingDebugMonitor class to provide real-time diagnostics and monitoring
- Implemented comprehensive logging of streaming data flow with timestamps and statistics
- Added streaming debug panel to dashboard UI for real-time monitoring of streaming status
- Enhanced streaming update interval callback to ensure consistent data flow and recommendation updates
- Implemented thread-safe data access with proper locking mechanisms to prevent race conditions

## Streaming Manager Improvements (May 29, 2025)
- Implemented message queue system to decouple message reception from processing, preventing blocking in stream handler
- Added dedicated message processor thread to handle incoming messages without blocking the stream
- Implemented heartbeat monitoring system to detect connection issues and trigger automatic reconnection
- Added automatic reconnection logic with configurable retry limits and backoff delays
- Enhanced error handling with detailed error messages and proper state management during failures
- Improved contract key normalization to ensure consistent matching between REST API and streaming data
- Added comprehensive status tracking with detailed metrics (message count, data count, last update time)
- Implemented proper thread synchronization with RLock to prevent race conditions in multi-threaded environment
- Added data flow monitoring to detect and recover from situations where subscriptions exist but no data is received
- Enhanced logging with detailed timestamps and context information for better troubleshooting
- Implemented proper cleanup of resources when stopping the stream to prevent resource leaks
- Added robust shutdown mechanism with proper state checking to prevent application crashes during teardown

## Timeframe Bias Indicator
- Implemented a comprehensive timeframe bias indicator to show dominant trend direction across timeframes
- Used a multi-factor approach combining moving averages, momentum indicators, and price action analysis
- Designed a scoring system from -100 (strongly bearish) to +100 (strongly bullish) for quantifiable bias measurement
- Added categorical labels for easy interpretation (strongly_bearish, bearish, slightly_bearish, neutral, slightly_bullish, bullish, strongly_bullish)
- Included confidence metrics to indicate the strength and reliability of the bias signal
- Integrated bias scores with recommendation engine to enhance confidence scoring
- Applied weighted adjustments to recommendation confidence based on bias strength and direction
- Designed the indicator to be additive to existing technical signals rather than replacing them
- Implemented the bias calculation for all timeframes (1min, 15min, 30min, 1hour, daily) to provide complete market context

## Data Tables Display Fix
- Fixed minute tab and technical indicators tab data tables by implementing proper callback functions
- Ensured consistent data formatting across all tables
- Added error handling to prevent UI crashes when data is missing or malformed

## Debugging Approach
- Added dedicated debug information panel to recommendation tab for transparent troubleshooting
- Implemented detailed step-by-step logging of the recommendation generation process
- Added data validation checks at each stage of processing
- Designed debug output to clearly show data flow from technical indicators to final recommendations
- Enhanced streaming data debugging to show contract key formats and matching statistics
- Created dedicated StreamingDebugMonitor class for continuous monitoring of streaming data flow
- Implemented comprehensive logging with timestamps for all streaming events
- Added real-time statistics tracking for streaming data updates and match rates

## Error Handling
- Improved error messages to provide clear guidance to users
- Added graceful fallbacks when expected data is missing
- Implemented comprehensive exception catching to prevent UI crashes
- Added detailed logging of contract key matching attempts and failures to aid in troubleshooting
- Added type checking for selected_symbol parameter to handle both dictionary and string formats
- Implemented defensive programming approach to handle variable data types in callback parameters
- Implemented exception-safe shutdown mechanism with proper state checking to prevent application crashes during teardown


## Excel Export Functionality (June 7, 2025)
- Replaced custom download implementation with Dash's native dcc.Download component for better cross-browser compatibility
- Eliminated the need for client-side callbacks by using Dash's built-in download mechanism
- Improved Safari compatibility by using a more standardized approach to file downloads
- Simplified the download process by removing the multi-step approach (generate download link, then click it)
- Enhanced the export button callbacks to work directly with the native download component
- Maintained the same Excel file generation logic while improving the delivery mechanism
- Preserved all metadata and formatting in Excel exports while fixing the download functionality
- Implemented a more robust base64 encoding approach for binary file content


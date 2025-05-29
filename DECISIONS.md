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

## Data Tables Display Fix
- Fixed minute tab and technical indicators tab data tables by implementing proper callback functions
- Ensured consistent data formatting across all tables
- Added error handling to prevent UI crashes when data is missing or malformed

## Debugging Approach
- Added dedicated debug information panel to recommendation tab for transparent troubleshooting
- Implemented detailed step-by-step logging of the recommendation generation process
- Added data validation checks at each stage of processing
- Designed debug output to clearly show data flow from technical indicators to final recommendations

## Error Handling
- Improved error messages to provide clear guidance to users
- Added graceful fallbacks when expected data is missing
- Implemented comprehensive exception catching to prevent UI crashes

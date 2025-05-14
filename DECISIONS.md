# Decisions

## Key Architectural Choices

- **Modular Design:** The application will be built with a modular design, separating concerns like data fetching, data processing, technical analysis, and UI presentation. This will allow for easier maintenance, testing, and scalability.
- **API Wrapper:** Utilize the `schwabdev` Python library as a wrapper for the Schwab API to simplify authentication and API calls.

## Technology Selections

- **Programming Language:** Python will be the primary language for backend development, data processing, and API interaction due to its extensive libraries for data analysis and web development.
- **Data Handling:** Pandas will be used for data manipulation and aggregation (e.g., converting minute data to hourly/daily).
- **Technical Analysis:** Libraries like TA-Lib or custom implementations will be used for technical indicators (MACD, RSI, etc.) and pattern recognition.
- **Dashboard UI:** (To be decided - will likely be a web framework like Flask or Dash, depending on the complexity and interactivity required for the dashboard).
- **Version Control:** Git and GitHub for version control and collaborative development.

## Design Patterns Used

- (To be determined as development progresses. Will likely include patterns like Observer for real-time data updates if a UI is built).

## Rationale for Important Decisions

- **Schwabdev Library:** Chosen to expedite development by leveraging an existing, tested library for Schwab API interaction, rather than building a custom solution from scratch. This also helps in managing the complexities of the OAuth 2.0 authentication flow.
- **Python & Pandas:** Selected for their strong data science ecosystem, making it efficient to handle and analyze financial time-series data.

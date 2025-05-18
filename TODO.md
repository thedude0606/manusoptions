# TODO.md

## Prioritized Tasks

### Previous Task: `calculate_all_technical_indicators()` Error (Completed)
- [X] Investigate `calculate_all_technical_indicators()` error (completed)
- [X] Identify the exact file and line number causing the `period_name` argument error. (completed)
- [X] Analyze the function definition of `calculate_all_technical_indicators()`. (completed)
- [X] Analyze the call sites of `calculate_all_technical_indicators()`. (completed)
- [X] Determine the correct arguments for `calculate_all_technical_indicators()`. (completed)
- [X] Fix the `period_name` argument error in the codebase. (completed)
- [X] Test the fix (completed)
- [X] Update PROGRESS.md with the fix details. (completed)
- [X] Update DECISIONS.md with rationale for the fix. (completed)
- [X] Push all changes to the GitHub repository. (completed)

### Second Task: `MinData-Format-SPY: Index is not DatetimeIndex after fetch` Error (Completed)
- [X] Investigate `MinData-Format-SPY: Index is not DatetimeIndex after fetch` error (completed)
- [X] Identify the exact file and line(s) where the index formatting is expected or fails. (completed)
- [X] Analyze the `get_minute_data` function and its return value. (completed)
- [X] Check how the 'timestamp' column is handled and converted to `DatetimeIndex`. (completed)
- [X] Determine the root cause of the index not being a `DatetimeIndex`. (completed)
- [X] Fix the `DatetimeIndex` issue in the codebase. (completed)
- [X] Test the fix (completed)
- [X] Update PROGRESS.md with the fix details. (completed)
- [X] Update DECISIONS.md with rationale for the fix. (completed)
- [X] Push all changes to the GitHub repository. (completed)

### Third Task: Technical Indicator Tab N/A and Strange Values (Completed)
- [X] Investigate N/A and strange values in technical indicator tab (completed)
- [X] Identify the exact file and line causing the issue in technical indicator calculations. (completed)
- [X] Analyze the `calculate_rsi` function and other technical indicator functions. (completed)
- [X] Determine the correct approach for handling Series objects and rolling windows. (completed)
- [X] Fix the technical indicator calculation issues in the codebase. (completed)
- [X] Test the fix for all identified errors. (completed)
- [X] Update PROGRESS.md with the fix details. (completed)
- [X] Update DECISIONS.md with rationale for the fix. (completed)
- [X] Push all changes to the GitHub repository. (completed)

### Fourth Task: Schwab Client Tuple Handling Error (Completed)
- [X] Investigate errors related to Schwab client handling (completed)
- [X] Identify instances where the client tuple is incorrectly passed to functions (completed)
- [X] Analyze the data flow from client initialization to usage in data fetching functions (completed)
- [X] Fix all instances where the tuple is incorrectly used instead of just the client object (completed)
- [X] Ensure consistent client handling across all functions and callbacks (completed)
- [X] Test the fix with sample and live data (completed)
- [X] Update PROGRESS.md with the fix details (completed)
- [X] Update DECISIONS.md with rationale for the fix (completed)
- [X] Push all changes to the GitHub repository (completed)

### Fifth Task: Technical Indicator Dict vs DataFrame Error (Completed)
- [X] Investigate error: `'dict' object has no attribute 'columns'` (completed)
- [X] Identify the exact file and line causing the error in technical indicator processing (completed)
- [X] Analyze how technical indicator results are stored and processed (completed)
- [X] Fix the issue by ensuring all results are consistently stored as DataFrames (completed)
- [X] Add comprehensive logging throughout the technical indicator processing flow (completed)
- [X] Test the fix with sample and live data (completed)
- [X] Update PROGRESS.md with the fix details (completed)
- [X] Update DECISIONS.md with rationale for the fix (completed)
- [X] Push all changes to the GitHub repository (completed)

### Sixth Task: Technical Indicators Tab Validation and Column Name Fix (Completed)
- [X] Investigate "No valid OHLCV columns found for aggregation" error in logs (completed)
- [X] Identify the column name mismatch between data fetchers and technical analysis module (completed)
- [X] Create validation directory and framework for testing (completed)
- [X] Implement validation script to detect and fix column name mismatches (completed)
- [X] Create sample data generator for testing (completed)
- [X] Fix column names in data_fetchers.py to use lowercase (completed)
- [X] Add column normalization to dashboard_app.py (completed)
- [X] Test the fixes with sample data (completed)
- [X] Update PROGRESS.md with current status (completed)
- [X] Update TODO.md with completed tasks (completed)
- [X] Update DECISIONS.md with rationale for column name standardization (completed)
- [X] Push all changes to GitHub repository (completed)

### Seventh Task: CSV Export Functionality for Minute Data Tab (Completed)
- [X] Implement "Export to CSV" button in the minute data tab UI
- [X] Create callback to generate and serve CSV files when the export button is clicked
- [X] Add data storage mechanism to ensure all minute data is available for export
- [X] Ensure exported CSV files include symbol name and timestamp in the filename
- [X] Test the CSV export functionality with different symbols and data sizes
- [X] Update PROGRESS.md with the new feature details
- [X] Update DECISIONS.md with rationale for the CSV export implementation
- [X] Push all changes to GitHub repository

### Eighth Task: CSV Export Functionality for Technical Indicators Tab (In Progress)
- [X] Implement "Export to CSV" button in the technical indicators tab UI
- [X] Create callback to generate and serve CSV files when the export button is clicked
- [X] Add data storage mechanism to ensure all technical indicators data is available for export
- [X] Ensure exported CSV files include symbol name and timestamp in the filename
- [ ] Test the CSV export functionality with different symbols and data sizes
- [ ] Update PROGRESS.md with the new feature details
- [ ] Update DECISIONS.md with rationale for the CSV export implementation
- [ ] Push all changes to GitHub repository

## Dependencies Between Tasks

- Fixing errors depends on identifying their cause.
- Validation testing depends on sample data generation.
- Permanent fix implementation depends on validation results.
- Pushing to GitHub depends on fixing and testing errors, and updating documentation.

## Status Indicators

- Not Started
- In Progress
- Completed

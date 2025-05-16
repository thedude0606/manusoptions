# TODO.md

## Prioritized Tasks

### Previous Task: `calculate_all_technical_indicators()` Error (Completed)
- [X] Investigate `calculate_all_technical_indicators()` error (completed)
- [X] Identify the exact file and line number causing the `period_name` argument error. (completed)
- [X] Analyze the function definition of `calculate_all_technical_indicators()`. (completed)
- [X] Analyze the call sites of `calculate_all_technical_indicators()`. (completed)
- [X] Determine the correct arguments for `calculate_all_technical_indicators()`. (completed)
- [X] Fix the `period_name` argument error in the codebase. (completed)
- [ ] Test the fix (Skipped due to new error, will be tested together).
- [X] Update PROGRESS.md with the fix details. (completed)
- [X] Update DECISIONS.md with rationale for the fix. (completed)
- [X] Push all changes to the GitHub repository. (completed)

### Current Task: `MinData-Format-SPY: Index is not DatetimeIndex after fetch` Error
- [X] Investigate `MinData-Format-SPY: Index is not DatetimeIndex after fetch` error (completed)
- [X] Identify the exact file and line(s) where the index formatting is expected or fails. (completed)
- [X] Analyze the `get_minute_data` function and its return value. (completed)
- [X] Check how the 'timestamp' column is handled and converted to `DatetimeIndex`. (completed)
- [X] Determine the root cause of the index not being a `DatetimeIndex`. (completed)
- [X] Fix the `DatetimeIndex` issue in the codebase. (completed)
- [ ] Test the fix for both this error and the previous one.
- [X] Update PROGRESS.md with the fix details. (completed)
- [ ] Update DECISIONS.md if any significant decisions are made during this fix. (in progress)
- [ ] Push all changes to the GitHub repository.

## Dependencies Between Tasks

- Fixing errors depends on identifying their cause.
- Pushing to GitHub depends on fixing and testing errors, and updating documentation.

## Status Indicators

- Not Started
- In Progress
- Completed

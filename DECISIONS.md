# DECISIONS.md

## Key Architectural Choices

- (To be filled as decisions are made)

## Technology Selections

- Python for the main application logic.
- Git for version control.

## Design Patterns Used

- (To be filled as patterns are identified or implemented)

## Rationale for Important Decisions

- **Fix for `calculate_all_technical_indicators()` TypeError (2025-05-16):**
    - **Issue:** The function `calculate_all_technical_indicators` was called with an unexpected keyword argument `period_name` in `dashboard_app.py` (line 333).
    - **Investigation:** The function definition in `technical_analysis.py` (`def calculate_all_technical_indicators(df, symbol="N/A")`) showed it only accepts `df` and `symbol` as arguments.
    - **Decision:** Modified the call in `dashboard_app.py` to remove the `period_name` argument. The period information, which was previously passed via `period_name`, is now concatenated with the `selected_symbol` and passed as the `symbol` argument (e.g., `symbol=f"{selected_symbol}_{period}"`). This aligns the function call with its definition and ensures the period context is still available if needed within the function or for logging/debugging purposes via the symbol string.
    - **Rationale:** This change directly addresses the `TypeError` by ensuring the function is called with the correct arguments. Passing the period information as part of the symbol string is a common practice to provide context without altering the function signature, especially if the function itself doesn't strictly require the period for its internal calculations but the context is useful for downstream processing or identification of the resulting data.


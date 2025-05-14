## Decision Log

### Key Architectural Choices

*   **Token Management in `fetch_options_chain.py` (2025-05-14):**
    *   **Observation:** The script `fetch_options_chain.py` was attempting to use `client.token_manager.tokens_valid()` and `client.token_manager.refresh_tokens()`.
    *   **Issue:** The `schwabdev.Client` object, as imported and used, does not possess a `token_manager` attribute. This was identified as the cause of the `AttributeError`.
    *   **Decision:** Modify `fetch_options_chain.py` to handle token validation and refresh by interacting with the `client.tokens` object (e.g., checking `client.tokens.access_token`, `client.tokens.is_access_token_expired()`, and using `client.tokens.update_refresh_token()` or similar methods available directly on the `client` or `client.tokens` object from the `schwabdev` library). This approach aligns with the usage pattern observed in `auth_script.py` and common practices for API client libraries where token data is often encapsulated within a `tokens` attribute of the client instance or managed via client methods.
    *   **Rationale:** This change is necessary to resolve the `AttributeError` and to correctly interact with the `schwabdev` library for authentication and token management as per its likely design. The `schwabdev` example repository and documentation (if available within the library or its source) should be the primary guide for the exact methods to use.

### Technology Selections

*   **Primary Language:** Python (as per existing codebase).
*   **API Interaction Library:** `schwabdev` (as per existing codebase and user direction).
*   **Environment Management:** `.env` files for credentials (as per existing codebase).

### Design Patterns Used

*   (To be updated as development progresses and patterns are identified or implemented.)

### Rationale for Important Decisions

*   (To be updated as more significant decisions are made.)

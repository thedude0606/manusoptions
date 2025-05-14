## Decision Log

### Key Architectural Choices

*   **Token Management in `fetch_options_chain.py` (2025-05-14):**
    *   **Observation (Initial):** The script `fetch_options_chain.py` was attempting to use `client.token_manager.tokens_valid()` and `client.token_manager.refresh_tokens()`.
    *   **Issue (Initial):** The `schwabdev.Client` object, as imported and used, does not possess a `token_manager` attribute. This was identified as the cause of the first `AttributeError`.
    *   **Decision (Initial Fix):** Modify `fetch_options_chain.py` to handle token validation and refresh by interacting with the `client.tokens` object (e.g., checking `client.tokens.access_token`, and using methods like `client.tokens.update_refresh_token()`).
    *   **Rationale (Initial Fix):** This change was necessary to resolve the first `AttributeError` and to correctly interact with the `schwabdev` library for authentication and token management as per its likely design.

*   **Token Expiration Check in `fetch_options_chain.py` (2025-05-14 - Update):**
    *   **Observation (Second):** After the initial fix, the script encountered `AttributeError: 'Tokens' object has no attribute 'is_access_token_expired'`. The method `client.tokens.is_access_token_expired()` was an incorrect assumption.
    *   **Investigation:** Examination of the `schwabdev/tokens.py` source code revealed that the `Tokens` class has an `update_tokens()` method. This method internally checks if the access token or refresh token needs updating (e.g., due to expiry) and attempts to refresh them. It does not expose a direct boolean property like `is_access_token_expired` for external checking prior to calling an update method.
    *   **Decision (Second Fix):** Modify `fetch_options_chain.py` to call `client.tokens.update_tokens()` before making API calls. This method handles the logic of checking expiry and refreshing tokens internally. After calling `update_tokens()`, the script should verify that `client.tokens.access_token` is still valid.
    *   **Rationale (Second Fix):** This aligns with the `schwabdev` library's apparent design where token state management (including expiry checks and refreshes) is encapsulated within the `update_tokens()` method of the `Tokens` class. Relying on this method ensures that the library's own logic for token maintenance is used.

### Technology Selections

*   **Primary Language:** Python (as per existing codebase).
*   **API Interaction Library:** `schwabdev` (as per existing codebase and user direction).
*   **Environment Management:** `.env` files for credentials (as per existing codebase).

### Design Patterns Used

*   (To be updated as development progresses and patterns are identified or implemented.)

### Rationale for Important Decisions

*   (To be updated as more significant decisions are made.)

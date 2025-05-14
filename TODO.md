## TODO List

### Setup and Initial Debugging

- [x] Clone GitHub repository (`https://github.com/thedude0606/manusoptions`)
- [x] Analyze `fetch_options_chain.py` for `AttributeError`
- [x] Review `auth_script.py` and `schwabdev` library usage for token management
- [x] Create `PROGRESS.md` and populate initial content
- [x] Create `TODO.md` and populate initial tasks
- [x] Create `DECISIONS.md` and populate initial decisions/observations
- [x] Modify `fetch_options_chain.py` to fix `AttributeError` by using `client.tokens` (or equivalent `schwabdev` methods) for token validation and refresh.
- [x] Test the corrected `fetch_options_chain.py` (AttributeError resolved; script now proceeds to credential/token validation).
- [x] Push all code changes and tracking files (PROGRESS.md, TODO.md, DECISIONS.md) to the GitHub repository.
- [x] Investigate and fix `AttributeError: 'Tokens' object has no attribute 'is_access_token_expired'` by using `client.tokens.update_tokens()`.

### Streaming Functionality Implementation

- [x] Clarify streaming requirements with user (data scope, symbols, data handling, script structure, duration).
- [x] Review provided `schwabdev` streaming examples and documentation.
- [x] Design and implement initial streaming logic in `fetch_options_chain.py`:
    - [x] Add `APP_MODE` to switch between "FETCH" and "STREAM".
    - [x] Implement `stream_message_handler` for `LEVELONE_OPTIONS`.
    - [x] Implement change detection for streamed contract metrics.
    - [x] Add 5-second interval display for detected changes.
    - [x] Support multiple underlying symbols for streaming.
    - [x] Fetch all option contract keys for specified symbols.
    - [x] Implement subscription to option contracts in chunks.
- [x] Clarify and implement efficient contract filtering for streaming:
    - [x] Filter out contracts with zero open interest.
    - [x] Add filter for expiration date (DTE), including 0DTE.
    - [x] Update `get_filtered_option_contract_keys` to apply these filters.
- [x] Systematically scan and correct all f-string and other syntax/formatting errors in `fetch_options_chain.py`.
- [x] Verify script runs without syntax errors (up to credential validation).

### Debugging Contract Filtering (Current Focus)

- [x] ~~Add diagnostic printing to `get_filtered_option_contract_keys` in `fetch_options_chain.py` to show raw contract data (symbol, OI, DTE) before filters are applied.~~ (Superseded by log file)
- [x] Modify `get_filtered_option_contract_keys` to write raw contract data (symbol, OI, DTE) to a log file (`raw_contracts_diag.log`) for comprehensive analysis.
- [ ] User to run the modified `fetch_options_chain.py` and provide the `raw_contracts_diag.log` file.
- [ ] Analyze the diagnostic log to understand how the API reports OI and DTE for the specified symbols (e.g., AAPL 0DTE).
- [ ] Refine the contract filtering logic in `get_filtered_option_contract_keys` based on the analysis of the diagnostic output, if necessary.
- [ ] Test the refined filtering to ensure it correctly identifies contracts based on user criteria (0DTE, OI > 0).

### Next Steps & Broader Testing

- [ ] User to test `fetch_options_chain.py` in "STREAM" mode with refined filters and valid Schwab API credentials and `tokens.json`.
- [ ] Address any issues identified during user's live streaming tests.
- [ ] Discuss and implement further enhancements (e.g., more sophisticated "data chart", additional filtering options, error handling for stream disconnects).

### Future Enhancements (Placeholder)

- [ ] Develop options buying recommendation logic.
- [ ] Integrate advanced technical indicators.
- [ ] Build an interactive UI.
- [ ] Implement comprehensive backtesting features.
- [ ] Package application for easy local deployment.

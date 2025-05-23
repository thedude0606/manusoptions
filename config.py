"""
Centralized configuration for the Manus Options application.
This module provides consistent configuration values across all components.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API credentials
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")

# Token file path - centralized for consistency
# Use absolute path with os.path.abspath to ensure consistency
TOKEN_FILE_PATH = os.path.abspath("token.json")

# Cache configuration
CACHE_CONFIG = {
    'update_interval_seconds': 60,  # Update data every 60 seconds
    'cache_expiry_seconds': 300,    # Cache expires after 5 minutes
}

# Options chain configuration
OPTIONS_CHAIN_CONFIG = {
    'contract_type': 'ALL',
    'strike_count': 20,
    'include_underlying_quote': True,
    'strategy': 'SINGLE',
    'range': 'ALL',
    'option_type': 'ALL'
}

# Minute data configuration
MINUTE_DATA_CONFIG = {
    'default_symbol': 'AAPL',
    'default_days': 60
}

"""
Centralized configuration for the Manus Options application.
This module provides consistent configuration values across all components.
"""

import os
import platform
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API credentials
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")

# Token file path - centralized for consistency
# First check if TOKEN_FILE_PATH is defined in .env
# If not, create a platform-appropriate path in user's home directory
def get_token_file_path():
    # Check if TOKEN_FILE_PATH is defined in environment variables
    env_token_path = os.getenv("TOKEN_FILE_PATH")
    if env_token_path:
        return env_token_path
    
    # If not defined, create a platform-appropriate path in user's home directory
    home_dir = os.path.expanduser("~")
    app_dir = os.path.join(home_dir, ".manusoptions")
    
    # Create the directory if it doesn't exist
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True)
    
    return os.path.join(app_dir, "token.json")

# Set the token file path
TOKEN_FILE_PATH = get_token_file_path()

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

"""
Utility functions for contract key formatting and normalization.
This module provides consistent contract key formatting between REST and streaming data.
"""

import re
import logging

# Configure logging
logger = logging.getLogger(__name__)

def normalize_contract_key(contract_key):
    """
    Normalize contract key to a standard format for consistent matching between REST and streaming data.
    
    Args:
        contract_key (str): The contract key to normalize
        
    Returns:
        str: Normalized contract key
    """
    try:
        # Log the original contract key
        logger.debug(f"Normalizing contract key: {contract_key}")
        
        # If the key is empty or None, return as is
        if not contract_key:
            return contract_key
            
        # Remove any spaces in the key
        clean_key = contract_key.replace(" ", "")
        
        # Extract components using regex
        # Try different patterns to match various formats
        
        # Pattern 1: Standard format with underscore (AAPL_YYMMDDCNNN)
        pattern1 = r'([A-Z]+)_(\d{6})([CP])(\d+(?:\.\d+)?)'
        match = re.match(pattern1, clean_key)
        
        if not match:
            # Pattern 2: Standard format without underscore (AAPLYYMMDDCNNN)
            pattern2 = r'([A-Z]+)(\d{6})([CP])(\d+(?:\.\d+)?)'
            match = re.match(pattern2, clean_key)
            
        if not match:
            # Pattern 3: Format with padded strike price (AAPLYYMMDDCNNNNNNNN)
            pattern3 = r'([A-Z]+)(\d{6})([CP])(\d{8})'
            match = re.match(pattern3, clean_key)
            
        if not match:
            # Pattern 4: Schwab streaming format with spaces (AAPL  YYMMDDCNNNNNNNN)
            pattern4 = r'([A-Z]+)\s+(\d{6})([CP])(\d{8})'
            match = re.match(pattern4, clean_key)
            
        if not match:
            logger.warning(f"Could not parse contract key: {contract_key}, returning as-is")
            return contract_key
            
        symbol, exp_date, cp_flag, strike = match.groups()
        
        # Create a canonical format: SYMBOL_YYMMDDCNNN
        # This format is used for internal storage and matching
        try:
            if len(strike) == 8:  # If it's already padded to 8 digits
                strike_value = int(strike) / 1000
            else:
                strike_value = float(strike)
                
            normalized_key = f"{symbol}_{exp_date}{cp_flag}{strike_value}"
            logger.debug(f"Normalized contract key: {contract_key} -> {normalized_key}")
            return normalized_key
        except ValueError:
            logger.warning(f"Error converting strike price in {contract_key}")
            return contract_key
            
    except Exception as e:
        logger.error(f"Error normalizing contract key {contract_key}: {e}", exc_info=True)
        return contract_key

def format_contract_key_for_streaming(contract_key):
    """
    Format contract key for streaming according to Schwab API requirements.
    
    The Schwab streaming API requires option symbols in a specific format:
    - Underlying symbol (padded with spaces to 6 chars)
    - Expiration date (YYMMDD)
    - Call/Put indicator (C/P)
    - Strike price (padded with leading zeros to 8 chars)
    
    Example: "AAPL  240621C00190000" for Apple $190 call expiring June 21, 2024
    
    Args:
        contract_key (str): The contract key to format
        
    Returns:
        str: Formatted contract key for streaming
    """
    try:
        # Log the original contract key
        logger.debug(f"Formatting contract key for streaming: {contract_key}")
        
        # Check if the key is already in the correct format
        if len(contract_key) >= 21 and ' ' in contract_key:
            logger.debug(f"Contract key appears to be already formatted: {contract_key}")
            return contract_key
        
        # Remove any spaces in the key
        clean_key = contract_key.replace(" ", "")
        
        # Extract components using regex
        # Pattern to match: symbol_YYMMDDCNNN or symbol_YYMMDDpNNN
        pattern = r'([A-Z]+)_?(\d{6})([CP])(\d+(?:\.\d+)?)'
        match = re.match(pattern, clean_key)
        
        if not match:
            # Try alternative pattern for Schwab's standard format
            # Example: AAPL240621C00190000
            alt_pattern = r'([A-Z]+)(\d{6})([CP])(\d{8})'
            match = re.match(alt_pattern, clean_key)
            
            if not match:
                logger.warning(f"Could not parse contract key: {contract_key}, using as-is")
                return contract_key
        
        symbol, exp_date, cp_flag, strike = match.groups()
        
        # Format strike price (multiply by 1000 if needed and pad with leading zeros)
        try:
            strike_float = float(strike)
            strike_int = int(strike_float * 1000) if strike_float < 1000 else int(strike_float)
            strike_padded = f"{strike_int:08d}"
        except ValueError:
            # If we can't convert the strike, try to use it as is
            if len(strike) == 8 and strike.isdigit():
                strike_padded = strike
            else:
                logger.warning(f"Could not format strike price: {strike}")
                return contract_key
        
        # Format symbol (pad with spaces to 6 chars)
        symbol_padded = f"{symbol:<6}"
        
        # Combine all parts
        formatted_key = f"{symbol_padded}{exp_date}{cp_flag}{strike_padded}"
        logger.debug(f"Formatted contract key for streaming: {contract_key} -> {formatted_key}")
        
        return formatted_key
    except Exception as e:
        logger.error(f"Error formatting contract key {contract_key}: {e}", exc_info=True)
        return contract_key

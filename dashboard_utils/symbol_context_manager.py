"""
Symbol Context Manager for Options Trading Dashboard

This module provides utilities to ensure symbol context is preserved
throughout the dashboard data flow pipeline.
"""

import logging
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class SymbolContextManager:
    """
    Manager class to ensure symbol context is preserved throughout the data pipeline.
    """
    
    def __init__(self):
        """Initialize the symbol context manager."""
        self.current_symbol = None
        logger.info("Symbol context manager initialized")
    
    def set_symbol(self, symbol):
        """
        Set the current symbol context.
        
        Args:
            symbol: Symbol string or dictionary with symbol information
            
        Returns:
            str: The normalized symbol string
        """
        if isinstance(symbol, dict):
            symbol_str = symbol.get("symbol", "")
            logger.info(f"Setting symbol context from dictionary: {symbol_str}")
        else:
            symbol_str = str(symbol) if symbol else ""
            logger.info(f"Setting symbol context from string: {symbol_str}")
        
        self.current_symbol = symbol_str.upper() if symbol_str else ""
        return self.current_symbol
    
    def get_symbol(self):
        """
        Get the current symbol context.
        
        Returns:
            str: The current symbol string
        """
        return self.current_symbol
    
    def validate_data_for_symbol(self, data, data_type):
        """
        Validate that data is for the current symbol context.
        
        Args:
            data: Data to validate (DataFrame, dict, or list)
            data_type: Type of data being validated (e.g., "technical_indicators", "options_chain")
            
        Returns:
            tuple: (is_valid, message, data_with_symbol)
        """
        if not self.current_symbol:
            logger.warning(f"No current symbol context set for {data_type} validation")
            return False, "No symbol context set", data
        
        logger.info(f"Validating {data_type} data for symbol: {self.current_symbol}")
        
        # Handle different data types
        if isinstance(data, pd.DataFrame):
            return self._validate_dataframe(data, data_type)
        elif isinstance(data, dict):
            return self._validate_dict(data, data_type)
        elif isinstance(data, list):
            return self._validate_list(data, data_type)
        else:
            logger.warning(f"Unsupported data type for validation: {type(data).__name__}")
            return False, f"Unsupported data type: {type(data).__name__}", data
    
    def _validate_dataframe(self, df, data_type):
        """
        Validate DataFrame data for the current symbol context.
        
        Args:
            df: DataFrame to validate
            data_type: Type of data being validated
            
        Returns:
            tuple: (is_valid, message, df_with_symbol)
        """
        if df.empty:
            logger.warning(f"Empty DataFrame provided for {data_type} validation")
            return False, "Empty DataFrame", df
        
        # Check if symbol column exists
        if 'symbol' in df.columns:
            # Get unique symbols in the DataFrame
            unique_symbols = df['symbol'].unique()
            
            # Check if current symbol is in the DataFrame
            if self.current_symbol in [str(s).upper() for s in unique_symbols]:
                logger.info(f"DataFrame contains data for symbol {self.current_symbol}")
                return True, f"Valid data for symbol {self.current_symbol}", df
            else:
                logger.warning(f"DataFrame does not contain data for symbol {self.current_symbol}, found: {unique_symbols}")
                return False, f"Data is for symbols {unique_symbols}, not {self.current_symbol}", df
        
        # If no symbol column, check for underlying column (options data)
        elif 'underlying' in df.columns:
            unique_underlyings = df['underlying'].unique()
            
            if self.current_symbol in [str(u).upper() for u in unique_underlyings]:
                logger.info(f"DataFrame contains data for underlying {self.current_symbol}")
                return True, f"Valid data for underlying {self.current_symbol}", df
            else:
                logger.warning(f"DataFrame does not contain data for underlying {self.current_symbol}, found: {unique_underlyings}")
                return False, f"Data is for underlyings {unique_underlyings}, not {self.current_symbol}", df
        
        # If no symbol or underlying column, add symbol column
        logger.info(f"No symbol column found in DataFrame, adding symbol column with value {self.current_symbol}")
        df['symbol'] = self.current_symbol
        return True, f"Added symbol {self.current_symbol} to DataFrame", df
    
    def _validate_dict(self, data_dict, data_type):
        """
        Validate dictionary data for the current symbol context.
        
        Args:
            data_dict: Dictionary to validate
            data_type: Type of data being validated
            
        Returns:
            tuple: (is_valid, message, dict_with_symbol)
        """
        if not data_dict:
            logger.warning(f"Empty dictionary provided for {data_type} validation")
            return False, "Empty dictionary", data_dict
        
        # Check if symbol key exists
        if 'symbol' in data_dict:
            dict_symbol = str(data_dict['symbol']).upper()
            
            if dict_symbol == self.current_symbol:
                logger.info(f"Dictionary contains data for symbol {self.current_symbol}")
                return True, f"Valid data for symbol {self.current_symbol}", data_dict
            else:
                logger.warning(f"Dictionary contains data for symbol {dict_symbol}, not {self.current_symbol}")
                
                # Update the symbol to match current context
                logger.info(f"Updating dictionary symbol from {dict_symbol} to {self.current_symbol}")
                data_dict['symbol'] = self.current_symbol
                return True, f"Updated symbol from {dict_symbol} to {self.current_symbol}", data_dict
        
        # If no symbol key, add it
        logger.info(f"No symbol key found in dictionary, adding symbol with value {self.current_symbol}")
        data_dict['symbol'] = self.current_symbol
        return True, f"Added symbol {self.current_symbol} to dictionary", data_dict
    
    def _validate_list(self, data_list, data_type):
        """
        Validate list data for the current symbol context.
        
        Args:
            data_list: List to validate
            data_type: Type of data being validated
            
        Returns:
            tuple: (is_valid, message, list_with_symbol)
        """
        if not data_list:
            logger.warning(f"Empty list provided for {data_type} validation")
            return False, "Empty list", data_list
        
        # Check if list items are dictionaries with symbol keys
        symbols_found = set()
        has_symbol_key = False
        
        for item in data_list:
            if isinstance(item, dict) and 'symbol' in item:
                has_symbol_key = True
                symbols_found.add(str(item['symbol']).upper())
        
        if has_symbol_key:
            if self.current_symbol in symbols_found:
                logger.info(f"List contains data for symbol {self.current_symbol}")
                return True, f"Valid data for symbol {self.current_symbol}", data_list
            else:
                logger.warning(f"List contains data for symbols {symbols_found}, not {self.current_symbol}")
                
                # Update all items to have the current symbol
                for item in data_list:
                    if isinstance(item, dict):
                        item['symbol'] = self.current_symbol
                
                return True, f"Updated all items to have symbol {self.current_symbol}", data_list
        
        # If no items have symbol keys, add symbol to all dictionary items
        if any(isinstance(item, dict) for item in data_list):
            logger.info(f"No symbol keys found in list items, adding symbol {self.current_symbol} to all dictionary items")
            for item in data_list:
                if isinstance(item, dict):
                    item['symbol'] = self.current_symbol
            return True, f"Added symbol {self.current_symbol} to all dictionary items", data_list
        
        # If list doesn't contain dictionaries, we can't add symbol context
        logger.warning(f"Cannot add symbol context to list of {type(data_list[0]).__name__} items")
        return False, f"Cannot add symbol context to list of {type(data_list[0]).__name__} items", data_list
    
    def ensure_symbol_in_technical_indicators(self, tech_indicators_dict):
        """
        Ensure all technical indicators DataFrames have the current symbol.
        
        Args:
            tech_indicators_dict: Dictionary of technical indicators DataFrames by timeframe
            
        Returns:
            dict: Updated technical indicators dictionary with symbol context
        """
        if not self.current_symbol:
            logger.warning("No current symbol context set for technical indicators")
            return tech_indicators_dict
        
        if not tech_indicators_dict or not isinstance(tech_indicators_dict, dict):
            logger.warning(f"Invalid technical indicators dictionary: {type(tech_indicators_dict).__name__}")
            return tech_indicators_dict
        
        logger.info(f"Ensuring symbol {self.current_symbol} in technical indicators for {len(tech_indicators_dict)} timeframes")
        
        # Process each timeframe DataFrame
        for timeframe, df in tech_indicators_dict.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                if 'symbol' not in df.columns:
                    logger.info(f"Adding symbol column to {timeframe} DataFrame")
                    df['symbol'] = self.current_symbol
                elif df['symbol'].iloc[0] != self.current_symbol:
                    logger.info(f"Updating symbol in {timeframe} DataFrame from {df['symbol'].iloc[0]} to {self.current_symbol}")
                    df['symbol'] = self.current_symbol
        
        return tech_indicators_dict
    
    def ensure_symbol_in_options_chain(self, options_df):
        """
        Ensure options chain DataFrame has the current symbol.
        
        Args:
            options_df: Options chain DataFrame
            
        Returns:
            pd.DataFrame: Updated options chain DataFrame with symbol context
        """
        if not self.current_symbol:
            logger.warning("No current symbol context set for options chain")
            return options_df
        
        if not isinstance(options_df, pd.DataFrame) or options_df.empty:
            logger.warning(f"Invalid options chain DataFrame: {type(options_df).__name__}")
            return options_df
        
        logger.info(f"Ensuring symbol {self.current_symbol} in options chain DataFrame with {len(options_df)} rows")
        
        # Check if underlying column exists
        if 'underlying' in options_df.columns:
            if options_df['underlying'].iloc[0] != self.current_symbol:
                logger.info(f"Updating underlying in options chain from {options_df['underlying'].iloc[0]} to {self.current_symbol}")
                options_df['underlying'] = self.current_symbol
        else:
            logger.info("Adding underlying column to options chain DataFrame")
            options_df['underlying'] = self.current_symbol
        
        return options_df

# Create a singleton instance
symbol_context_manager = SymbolContextManager()

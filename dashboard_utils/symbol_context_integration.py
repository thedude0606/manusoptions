"""
Integration module for Symbol Context Manager with dashboard callbacks.

This module provides functions to integrate the Symbol Context Manager
with dashboard callbacks to ensure symbol context is preserved throughout
the data flow pipeline.
"""

import logging
import pandas as pd
from dashboard_utils.symbol_context_manager import symbol_context_manager

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def update_symbol_context(selected_symbol):
    """
    Update the symbol context manager with the selected symbol.
    
    Args:
        selected_symbol: Selected symbol (string or dictionary)
        
    Returns:
        str: The normalized symbol string
    """
    return symbol_context_manager.set_symbol(selected_symbol)

def process_technical_indicators_data(tech_indicators_data, selected_symbol):
    """
    Process technical indicators data to ensure symbol context is preserved.
    
    Args:
        tech_indicators_data: Technical indicators data from store
        selected_symbol: Selected symbol (string or dictionary)
        
    Returns:
        dict: Processed technical indicators data with symbol context
    """
    if not tech_indicators_data:
        logger.warning("No technical indicators data to process")
        return tech_indicators_data
    
    # Update symbol context
    symbol = update_symbol_context(selected_symbol)
    logger.info(f"Processing technical indicators data for symbol: {symbol}")
    
    # Process timeframe data
    if "timeframe_data" in tech_indicators_data:
        timeframe_data = tech_indicators_data["timeframe_data"]
        
        # Convert each timeframe's data to DataFrame, add symbol, and convert back
        for timeframe, data in timeframe_data.items():
            if data:
                df = pd.DataFrame(data)
                if 'symbol' not in df.columns:
                    df['symbol'] = symbol
                elif df['symbol'].iloc[0] != symbol:
                    df['symbol'] = symbol
                
                # Update the data in the dictionary
                timeframe_data[timeframe] = df.to_dict('records')
                logger.info(f"Added symbol context to {timeframe} data with {len(df)} rows")
        
        # Update the timeframe data in the original dictionary
        tech_indicators_data["timeframe_data"] = timeframe_data
    
    # Add symbol to the main dictionary if not present
    if "symbol" not in tech_indicators_data:
        tech_indicators_data["symbol"] = symbol
    elif tech_indicators_data["symbol"] != symbol:
        tech_indicators_data["symbol"] = symbol
    
    return tech_indicators_data

def process_options_chain_data(options_chain_data, selected_symbol):
    """
    Process options chain data to ensure symbol context is preserved.
    
    Args:
        options_chain_data: Options chain data from store
        selected_symbol: Selected symbol (string or dictionary)
        
    Returns:
        dict: Processed options chain data with symbol context
    """
    if not options_chain_data:
        logger.warning("No options chain data to process")
        return options_chain_data
    
    # Update symbol context
    symbol = update_symbol_context(selected_symbol)
    logger.info(f"Processing options chain data for symbol: {symbol}")
    
    # Add symbol to the main dictionary if not present
    if "symbol" not in options_chain_data:
        options_chain_data["symbol"] = symbol
    elif options_chain_data["symbol"] != symbol:
        options_chain_data["symbol"] = symbol
    
    # Process options data
    if "options" in options_chain_data:
        options_data = options_chain_data["options"]
        
        if options_data:
            # Convert to DataFrame, add underlying, and convert back
            df = pd.DataFrame(options_data)
            if 'underlying' not in df.columns:
                df['underlying'] = symbol
            elif df['underlying'].iloc[0] != symbol:
                df['underlying'] = symbol
            
            # Update the options data in the dictionary
            options_chain_data["options"] = df.to_dict('records')
            logger.info(f"Added symbol context to options data with {len(df)} rows")
    
    return options_chain_data

def prepare_data_for_recommendation_engine(tech_indicators_data, options_chain_data, selected_symbol):
    """
    Prepare data for the recommendation engine with proper symbol context.
    
    Args:
        tech_indicators_data: Technical indicators data from store
        options_chain_data: Options chain data from store
        selected_symbol: Selected symbol (string or dictionary)
        
    Returns:
        tuple: (tech_indicators_dict, options_df, symbol)
    """
    # Update symbol context
    symbol = update_symbol_context(selected_symbol)
    logger.info(f"Preparing data for recommendation engine for symbol: {symbol}")
    
    # Process technical indicators data
    tech_indicators_dict = {}
    if tech_indicators_data and "timeframe_data" in tech_indicators_data:
        for timeframe, data in tech_indicators_data.get("timeframe_data", {}).items():
            if data:
                df = pd.DataFrame(data)
                if 'symbol' not in df.columns:
                    df['symbol'] = symbol
                elif df['symbol'].iloc[0] != symbol:
                    df['symbol'] = symbol
                
                tech_indicators_dict[timeframe] = df
                logger.info(f"Prepared {timeframe} data with {len(df)} rows and symbol context")
    
    # Process options chain data
    options_df = pd.DataFrame()
    if options_chain_data and "options" in options_chain_data:
        options_data = options_chain_data["options"]
        if options_data:
            options_df = pd.DataFrame(options_data)
            if 'underlying' not in options_df.columns:
                options_df['underlying'] = symbol
            elif options_df['underlying'].iloc[0] != symbol:
                options_df['underlying'] = symbol
            
            logger.info(f"Prepared options data with {len(options_df)} rows and symbol context")
    
    # Ensure symbol context in all data
    tech_indicators_dict = symbol_context_manager.ensure_symbol_in_technical_indicators(tech_indicators_dict)
    options_df = symbol_context_manager.ensure_symbol_in_options_chain(options_df)
    
    return tech_indicators_dict, options_df, symbol

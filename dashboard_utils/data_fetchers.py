"""
Utility functions for fetching data for the dashboard.
"""
import datetime
import logging
import pandas as pd
import numpy as np
from technical_analysis import calculate_multi_timeframe_indicators

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('data_fetchers')

def get_minute_data(client, symbol):
    """
    Fetch minute data for a symbol.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to fetch data for
        
    Returns:
        tuple: (minute_data, error_message)
    """
    # Always fetch 60 days of data as per requirements
    days = 60
    logger.info(f"Fetching minute data for {symbol} for the last {days} days")
    
    try:
        # Calculate start and end dates
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Fetch minute data
        response = client.price_history(
            symbol=symbol,
            frequencyType="minute",
            frequency=1,
            startDate=start_date,
            endDate=end_date,
            needExtendedHoursData=False
        )
        
        if not response.ok:
            error_msg = f"Error fetching minute data: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return None, error_msg
        
        price_data = response.json()
        
        if not price_data.get("candles"):
            error_msg = "No candle data returned from API"
            logger.error(error_msg)
            return None, error_msg
        
        # Convert to DataFrame
        candles = price_data["candles"]
        df = pd.DataFrame(candles)
        
        # Convert datetime from milliseconds to datetime objects
        df['timestamp'] = pd.to_datetime(df['datetime'], unit='ms')
        
        # Drop original datetime column to avoid confusion
        df = df.drop(columns=['datetime'])
        
        # Reorder columns to put timestamp first
        cols = ['timestamp'] + [col for col in df.columns if col != 'timestamp']
        df = df[cols]
        
        # Convert to records for JSON serialization
        minute_data = df.to_dict('records')
        
        logger.info(f"Successfully fetched {len(minute_data)} minute data points for {symbol}")
        return minute_data, None
    
    except Exception as e:
        error_msg = f"Exception while fetching minute data: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None, error_msg

def get_technical_indicators(client, symbol):
    """
    Calculate technical indicators for a symbol.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to calculate indicators for
        
    Returns:
        tuple: (technical_indicators_data, error_message)
    """
    logger.info(f"Calculating technical indicators for {symbol}")
    
    try:
        # First, get minute data
        minute_data, error = get_minute_data(client, symbol)
        
        if error:
            return None, error
        
        if not minute_data:
            error_msg = "No minute data available for technical analysis"
            logger.error(error_msg)
            return None, error_msg
        
        # Convert to DataFrame
        df = pd.DataFrame(minute_data)
        df.set_index('timestamp', inplace=True)
        
        # Calculate technical indicators for all timeframes
        multi_tf_indicators = calculate_multi_timeframe_indicators(df, symbol=symbol)
        
        # Flatten the multi-timeframe results into a single table with a timeframe column
        all_indicators = []
        
        for timeframe, tf_df in multi_tf_indicators.items():
            # Reset index to get timestamp as a column
            tf_df_reset = tf_df.reset_index()
            
            # Add timeframe column
            tf_df_reset['timeframe'] = timeframe
            
            # Convert to records
            records = tf_df_reset.to_dict('records')
            all_indicators.extend(records)
        
        logger.info(f"Successfully calculated technical indicators for {symbol} across all timeframes")
        return all_indicators, None
    
    except Exception as e:
        error_msg = f"Exception while calculating technical indicators: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None, error_msg

def get_options_chain_data(client, symbol):
    """
    Fetch options chain data for a symbol.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to fetch options for
        
    Returns:
        tuple: (options_df, expiration_dates, underlying_price, error_message)
    """
    logger.info(f"Fetching options chain for {symbol}")
    
    try:
        # Get options chain
        response = client.option_chains(
            symbol=symbol,
            contractType="ALL",
            strikeCount=20,
            includeUnderlyingQuote=True,
            strategy="SINGLE",
            range="ALL",
            optionType="ALL"
        )
        
        if not response.ok:
            error_msg = f"Error fetching options chain: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return pd.DataFrame(), [], 0, error_msg
        
        options_data = response.json()
        
        # Extract underlying price
        underlying_price = options_data.get("underlyingPrice", 0)
        
        # Initialize lists
        all_options = []
        expiration_dates = []
        
        # Process call options
        call_exp_date_map = options_data.get("callExpDateMap", {})
        for exp_date, strikes in call_exp_date_map.items():
            # Extract expiration date (format: YYYY-MM-DD:DTE)
            exp_date = exp_date.split(":")[0]
            if exp_date not in expiration_dates:
                expiration_dates.append(exp_date)
            
            # Process each strike price
            for strike_price, contracts in strikes.items():
                for contract in contracts:
                    contract["putCall"] = "CALL"
                    contract["expirationDate"] = exp_date
                    contract["strikePrice"] = float(strike_price)
                    
                    # Check for alternative field names that might contain price data
                    if "lastPrice" not in contract and "last" in contract:
                        contract["lastPrice"] = contract["last"]
                    
                    if "bidPrice" not in contract and "bid" in contract:
                        contract["bidPrice"] = contract["bid"]
                    
                    if "askPrice" not in contract and "ask" in contract:
                        contract["askPrice"] = contract["ask"]
                    
                    # Only add default values if fields are completely missing
                    if "lastPrice" not in contract:
                        contract["lastPrice"] = None
                    
                    if "bidPrice" not in contract:
                        contract["bidPrice"] = None
                    
                    if "askPrice" not in contract:
                        contract["askPrice"] = None
                    
                    all_options.append(contract)
        
        # Process put options
        put_exp_date_map = options_data.get("putExpDateMap", {})
        for exp_date, strikes in put_exp_date_map.items():
            # Extract expiration date (format: YYYY-MM-DD:DTE)
            exp_date = exp_date.split(":")[0]
            if exp_date not in expiration_dates:
                expiration_dates.append(exp_date)
            
            # Process each strike price
            for strike_price, contracts in strikes.items():
                for contract in contracts:
                    contract["putCall"] = "PUT"
                    contract["expirationDate"] = exp_date
                    contract["strikePrice"] = float(strike_price)
                    
                    # Check for alternative field names that might contain price data
                    if "lastPrice" not in contract and "last" in contract:
                        contract["lastPrice"] = contract["last"]
                    
                    if "bidPrice" not in contract and "bid" in contract:
                        contract["bidPrice"] = contract["bid"]
                    
                    if "askPrice" not in contract and "ask" in contract:
                        contract["askPrice"] = contract["ask"]
                    
                    # Only add default values if fields are completely missing
                    if "lastPrice" not in contract:
                        contract["lastPrice"] = None
                    
                    if "bidPrice" not in contract:
                        contract["bidPrice"] = None
                    
                    if "askPrice" not in contract:
                        contract["askPrice"] = None
                    
                    all_options.append(contract)
        
        # Convert to DataFrame
        options_df = pd.DataFrame(all_options)
        
        # Sort expiration dates
        expiration_dates.sort()
        
        if not options_df.empty:
            sample_row = options_df.iloc[0]
            logger.info(f"Sample option data - Symbol: {sample_row.get('symbol')}, Last: {sample_row.get('lastPrice')}, Bid: {sample_row.get('bidPrice')}, Ask: {sample_row.get('askPrice')}")
            
            # Count how many contracts have non-None price fields
            non_none_last = options_df['lastPrice'].notna().sum()
            non_none_bid = options_df['bidPrice'].notna().sum()
            non_none_ask = options_df['askPrice'].notna().sum()
            logger.info(f"Price field statistics - Total contracts: {len(options_df)}, With lastPrice: {non_none_last}, With bidPrice: {non_none_bid}, With askPrice: {non_none_ask}")
        
        logger.info(f"Successfully fetched options chain for {symbol} with {len(options_df)} contracts across {len(expiration_dates)} expiration dates")
        return options_df, expiration_dates, underlying_price, None
    
    except Exception as e:
        logger.error(f"Exception while fetching options chain for {symbol}: {e}", exc_info=True)
        return pd.DataFrame(), [], 0, f"Exception while fetching options chain: {str(e)}"

def get_option_contract_keys(client, symbol, expiration_date=None, option_type=None):
    """
    Get a list of option contract keys for a given symbol, optionally filtered by expiration date and option type.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to fetch options for
        expiration_date: Optional expiration date to filter by (format: YYYY-MM-DD)
        option_type: Optional option type to filter by ('CALL' or 'PUT')
        
    Returns:
        List of option contract keys, error message (if any)
    """
    options_df, expiration_dates, underlying_price, error = get_options_chain_data(client, symbol)
    
    if error:
        return [], error
    
    if options_df.empty:
        return [], "No options data available"
    
    # Filter by expiration date if provided
    if expiration_date:
        if expiration_date not in expiration_dates:
            return [], f"Expiration date {expiration_date} not found in available dates: {expiration_dates}"
        options_df = options_df[options_df['expirationDate'] == expiration_date]
    
    # Filter by option type if provided
    if option_type:
        if option_type not in ['CALL', 'PUT']:
            return [], f"Invalid option type: {option_type}. Must be 'CALL' or 'PUT'."
        options_df = options_df[options_df['putCall'] == option_type]
    
    # Extract contract keys (symbols)
    if 'symbol' in options_df.columns:
        contract_keys = options_df['symbol'].tolist()
        return contract_keys, None
    else:
        return [], "Symbol column not found in options data"
